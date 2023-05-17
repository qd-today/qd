import importlib
import json
import os
import pkgutil
import typing
from collections import defaultdict
from dataclasses import dataclass
from html import escape
from typing import Callable, Iterable

from tornado.web import HTTPError

from libs.safe_eval import safe_eval

from ..base import BaseHandler, logger_Web_Handler

URL_PREFIX = "/v1/"

BaseType = typing.Union[str, int, float, bool, None]


class ApiError(HTTPError):
    def __init__(
        self,
        status_code: int,
        reason: str,
        log_message: str | None = None,
        *args,
        **kwargs,
    ):
        # 对于 HTTPError，log_message 是打印到控制台的内容，reason 是返回给用户的内容
        # 我们希望 API 的用户可以直接从 Web 界面看到错误信息，所以将 log_message 和 reason 设置为相同的内容
        if log_message is None:
            log_message = reason
        super().__init__(
            status_code, log_message=log_message, reason=reason, *args, **kwargs
        )


@dataclass()
class ArgumentBase(object):
    name: str
    '''参数名称
    例如："regex"'''
    required: bool
    """参数是否必须
    调用 API 时，缺少必须参数会返回 HTTP 400 错误"""
    description: str
    '''参数描述
    例如："正则表达式"'''
    type: typing.Type = str
    """参数类型，默认为 str
    设置了 multi 时，type 描述的是列表内元素的类型"""
    type_display: str | None = None
    """参数类型在前端的显示值，默认为 self.type.__name__"""
    init: Callable[[str | bytes], typing.Any] = None  # type: ignore
    """参数初始化函数，初始化规则如下：
    如果用户未提供且 self.type Callable，则使用 self.type；
    如果用户未提供且 self.type 不是 Callable，则使用 lambda x: x。
    该初始化函数原型为 init(str) -> self.type，例如 int("123"), float("123.456")等"""
    default: BaseType | Iterable[BaseType] = None
    """参数默认值
    如果设置了 multi，则 default 类型须为 Iterable[str|int|float|bool]（默认为空 tuple）；
    如果设置了 required，则 default 强制为 None；
    其他情况下 default 类型应为 Optionl[str|int|float|bool]。
    
    API 被调用时，用户若为提供该参数，则使用 init(default) 作为参数值。"""
    default_display: str | None = None
    """默认值在前端的显示值，默认为 repr(self.default)"""

    def __post_init__(self):
        if self.init is None:
            self.init = self.type
        if not isinstance(self.init, Callable):
            self.init = lambda x: x

        if self.required:
            self.default = None
            self.default_display = "❎"

        if self.default_display is None:
            self.default_display = repr(self.default)

        if self.type_display is None:
            self.type_display = self.type.__name__

    def get_value(self, api: "ApiBase") -> typing.Any:
        ...


@dataclass()
class Argument(ArgumentBase):
    """URL Query 和 POST form 参数"""

    init: Callable[[str], typing.Any] = None  # type: ignore
    """参数初始化函数，初始化规则如下：
    如果用户未提供且 self.type Callable，则使用 self.type；
    如果用户未提供且 self.type 不是 Callable，则使用 lambda x: x。
    该初始化函数原型为 init(str) -> self.type，例如 int("123"), float("123.456")等"""

    def get_value(self, api: "ApiBase") -> typing.Any:

        value = api.get_argument(self.name, self.default)  # type: ignore
        if value is None and self.required:
            raise ApiError(
                400, f"API {api.api_name}({api.api_url}) 参数 {self.name} 不能为空"
            )
        if value is not None and not isinstance(value, self.type):
            value = self.init(value)
        return value


@dataclass()
class MultiArgument(ArgumentBase):
    """多值参数，比如 ?a=1&a=2&a=3 -> a=[1,2,3]"""

    init: Callable[[str], typing.Any] = None  # type: ignore
    """参数初始化函数，初始化规则如下：
    如果用户未提供且 self.type Callable，则使用 self.type；
    如果用户未提供且 self.type 不是 Callable，则使用 lambda x: x。
    该初始化函数原型为 init(str) -> self.type，例如 int("123"), float("123.456")等"""

    def get_value(self, api: "ApiBase") -> tuple:
        vs = api.get_arguments(self.name)
        if not vs:
            if self.required:
                raise ApiError(
                    400, f"API {api.api_name}({api.api_url}) 参数 {self.name} 不能为空"
                )
            vs: Iterable[str] = self.default  # type: ignore
        r = []
        for v in vs:
            if not isinstance(v, self.type):
                v = self.init(v)
            r.append(v)
        return tuple(r)


@dataclass()
class BodyArgument(ArgumentBase):
    """从 request.body 初始化，比如 POST JSON 情形
    初始化函数原型为 init(bytes) -> self.type"""

    init: Callable[[bytes], typing.Any] = None  # type: ignore
    """参数初始化函数，初始化规则如下：
    如果用户未提供且 self.type Callable，则使用 self.type；
    如果用户未提供且 self.type 不是 Callable，则使用 lambda x: x。
    该初始化函数原型为 init(bytes) -> self.type"""

    def __post_init__(self):
        self.default = ""
        self.default_display = ""

        return super().__post_init__()

    def get_value(self, api: "ApiBase"):
        return self.init(api.request.body)


class ApiMetaclass(type):
    # 用于实现属性值修改和 method 装饰的元类
    def __new__(cls, name, bases, attrs):
        if name == "ApiBase":
            return super().__new__(cls, name, bases, attrs)

        # 设置各种属性
        attrs["api_url"] = URL_PREFIX + attrs["api_url"]

        t = defaultdict(list)
        for method_name in ("get", "post", "put", "delete"):
            if method_name not in attrs:
                continue
            func = attrs[method_name]
            t[func].append(method_name)

        api_frontend = {}
        rowspan = 0
        methods = {}
        for k, v in t.items():
            methods[", ".join(x.upper() for x in v)] = k.api
            if k.api["example"]:
                k.api["example"] = f'{attrs["api_url"]}?{k.api["example"]}'
            else:
                k.api["example"] = attrs["api_url"]
            l = len(k.api["arguments"])
            rowspan += l if l else 1
        api_frontend["rowspan"] = rowspan
        api_frontend["methods"] = methods

        attrs["api_frontend"] = api_frontend
        _cls: ApiBase = super().__new__(cls, name, bases, attrs)  # type: ignore

        # 注册 API，定义即注册
        global apis
        global handlers
        apis.append(_cls)
        handlers.append((attrs["api_url"], _cls))

        return _cls


class ApiBase(BaseHandler, metaclass=ApiMetaclass):
    api_name: str
    '''API 名称
    例如："正则表达式替换"'''
    api_url: str
    """API 的 URL，会自动加上前缀 "/api/"。可以使用正则表达式，但是不建议。
    例如："delay" （加上前缀后为"/api/delay"）"""
    api_description: str
    '''API 功能说明，支持 HTML 标签
    例如："使用正则表达式匹配字符串"'''
    api_frontend: dict
    """API 前端显示的信息，自动生成"""
    api_json_ascii = Argument(
        name="__ascii__",
        type=bool,
        default=False,
        required=False,
        description="返回 JSON 是否强制 ASCII 编码（非 ASCII 字符会被转义为\\uxxxx形式）",
    )
    api_json_indent = Argument(
        name="__indent__",
        type=int,
        default=4,
        required=False,
        description="返回 JSON 缩进空格数，0 表示不缩进但是会换行，-1 表示不缩进也不换行",
    )

    def api_get_arguments(
        self, args_def: Iterable[ArgumentBase]
    ) -> dict[str, typing.Any]:
        """获取 API 的所有参数"""
        args: dict[str, typing.Any] = {}

        for arg in args_def:
            args[arg.name] = arg.get_value(self)

        return args

    def api_write(self, data):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        ascii = self.api_json_ascii.get_value(self)
        indent = self.api_json_indent.get_value(self)
        if indent < 0:
            indent = None
        self.write(
            json.dumps(
                {"code": 200, "message": "ok", "data": data},
                ensure_ascii=ascii,
                indent=indent,
            )
        )


def api_wrap(
    arguments: Iterable[ArgumentBase] = [],
    example: dict[str, BaseType | Iterable[BaseType]] = {},
    example_display: str = "",
):
    """设置 API 参数、示例、说明等的装饰器"""

    def decorate(func: Callable):
        async def wrapper(self: "ApiBase") -> None:
            args: Iterable[ArgumentBase] = wrapper.api["arguments"]
            kwargs = self.api_get_arguments(args)

            ret = await func(self, **kwargs)
            self.api_write(ret)

        # 生成 example url
        nonlocal example_display
        if not example_display and example:
            kv = []
            for arg in arguments:
                arg: ArgumentBase
                k = arg.name
                if k not in example:
                    if arg.required:
                        raise ValueError(f'api example: "{k}" is required')
                    continue
                if isinstance(arg, MultiArgument):
                    e = example[k]
                    if not isinstance(e, (list, tuple)):
                        raise ValueError(f'api example: "{k}" should be list or tuple')
                    for v in e:
                        kv.append(f"{k}={v}")
                else:
                    kv.append(f"{k}={example[k]}")
            example_display = "&".join(kv)

        # 保存 api 信息
        wrapper.api = {
            "arguments": arguments,
            "example": example_display,
        }

        return wrapper

    return decorate


def load_all_api():
    path = os.path.dirname(__file__)
    for finder, name, ispkg in pkgutil.iter_modules([path]):
        module = importlib.import_module("." + name, __name__)
        # 注册 API 的工作交给元类做了，定义即注册


# apis 是给 about.py 看的，用于生成前端页面
# handlers 是给 handlers 看的，用于注册路由
apis: list[ApiBase] = []
handlers: list[tuple[str, ApiBase]] = []
load_all_api()
