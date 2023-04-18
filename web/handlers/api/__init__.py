import os
import json
import pkgutil
import importlib
import typing
from typing import Iterable, Callable
import dataclasses
from dataclasses import dataclass
from functools import partial
from collections import defaultdict

from tornado.web import HTTPError

from ..base import BaseHandler
from libs.safe_eval import safe_eval


URL_PREFIX = "/api/"

BaseType = typing.Union[str, int, float, bool, None]


class ApiError(HTTPError):
    def __init__(self, status_code: int, reason: str, *args, **kwargs):
        # 对于 HTTPError，log_message 是打印到控制台的内容，reason 是返回给用户的内容
        # 我们希望 API 的用户可以直接从 Web 界面看到错误信息，所以将 log_message 和 reason 设置为相同的内容
        super().__init__(status_code, reason, reason=reason, *args, **kwargs)


@dataclass()
class Argument(object):
    name: str
    '''参数名称
    例如："regex"'''
    required: bool
    """参数是否必须
    调用 API 时，缺少必须参数会返回 HTTP 400 错误"""
    description: str
    '''参数描述
    例如："正则表达式"'''
    type: "type" = str
    """参数类型，默认为 str
    设置了 multi 时，type 描述的是列表内元素的类型"""
    type_display: str | None = None
    """参数类型在前端的显示值，默认为 self.type.__name__"""
    init: Callable[[str], typing.Any] = None  # type: ignore
    """参数初始化函数，初始化规则如下：
    如果用户未提供且 self.type Callable，则使用 self.type；
    如果用户未提供且 self.type 不是 Callable，则使用 lambda x: x。
    该初始化函数原型为 init(str) -> self.type，例如 int("123"), float("123.456")等"""
    multi: bool = False
    """是否为多值参数，比如 ?a=1&a=2&a=3 -> a=[1,2,3]"""
    # multi 为 True 时，参数类型为 list[self.type]
    # multi 为 True 时，default 必须为 list 或 tuple（如果 default 为 None，会被自动转换为空 tuple）"""
    default: BaseType | Iterable[BaseType] = None
    """参数默认值
    如果设置了 multi，则 default 类型须为 Iterable[str|int|float|bool]（默认为空 tuple）；
    如果设置了 required，则 default 强制为 None；
    其他情况下 default 类型应为 Optionl[str|int|float|bool]。
    
    API 被调用时，用户若为提供该参数，则使用 init(default) 作为参数值。"""
    default_display: str | None = None
    """默认值在前端的显示值，默认为 repr(self.default)"""
    from_body: bool = False
    """从 request.body 初始化，比如 POST JSON 情形
    与 multi 互斥"""

    def __post_init__(self):
        if self.init is None:
            self.init = self.type
        if not isinstance(self.init, Callable):
            self.init = lambda x: x

        if self.required:
            self.default = None
            self.default_display = "❎"

        if self.multi and self.default is None:
            self.default = tuple()

        if self.default_display is None:
            self.default_display = repr(self.default)
            
        if self.type_display is None:
            self.type_display = self.type.__name__

        if self.multi and self.from_body:
            # multi 和 from_body 互斥
            raise ValueError(f"Argument {self.name} is multi but from_body")


class ApiMetaclass(type):
    # 用于实现属性值修改和 method 装饰的元类
    def __new__(cls, name, bases, attrs):
        if name == "ApiBase":
            return super().__new__(cls, name, bases, attrs)

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

        return super().__new__(cls, name, bases, attrs)


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

    def api_get_arguments(self, args_def: Iterable[Argument]) -> dict[str, typing.Any]:
        """获取 API 的所有参数"""
        args: dict[str, typing.Any] = {}

        for arg in args_def:
            init = arg.init

            if arg.multi:
                vs = self.get_arguments(arg.name)
                if not vs:
                    if arg.required:
                        raise ApiError(400, f"参数 {arg.name} 不能为空")
                    vs: Iterable[str] = arg.default  # type: ignore
                value = []
                for v in vs:
                    if not isinstance(v, arg.type):
                        v = init(v)
                    value.append(v)
            elif arg.from_body:
                value = init(self.request.body.decode())
            else:
                value = self.get_argument(arg.name, arg.default)  # type: ignore
                if value is None and arg.required:
                    log = f"参数 {arg.name} 不能为空"
                    raise ApiError(400, log)
                if value is not None and not isinstance(value, arg.type):
                    value = init(value)
            args[arg.name] = value

        return args

    def api_write(self, data):
        if data is None:
            # 空
            return
        elif isinstance(data, typing.Dict):
            if len(data) == 1:
                # 如果只有一个键值对，直接返回值
                # 不递归处理，默认 API 不会返回过于复杂的类型
                self.write(tuple(data.values())[0])
            else:
                # 如果有多个键值对，返回 JSON
                self.api_write_json(data)
        elif isinstance(data, str):
            # str 类型直接返回
            self.write(data)
        elif isinstance(data, (int, float)):
            # 简单类型转为 str 返回
            self.write(str(data))
        elif isinstance(data, bytes):
            self.set_header("Content-Type", "application/octet-stream")
            self.write(data)
        else:
            # 其他类型转换为 JSON
            self.api_write_json(data)

    def api_write_json(self, data: dict[str, typing.Any], ensure_ascii=False, indent=4):
        """将 json 数据写入响应"""
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(data, ensure_ascii=ensure_ascii, indent=indent))


def api_wrap(
    # func: Callable | None = None,
    # *,
    arguments: Iterable[Argument] = [],
    example: dict[str, BaseType | Iterable[BaseType]] = {},
    example_display: str = "",
    display: bool = True,
):
    """设置 API 参数、示例、说明等"""

    def decorate(func: Callable):
        async def wrapper(self: "ApiBase") -> None:
            args: Iterable[Argument] = wrapper.api["arguments"]
            kwargs = self.api_get_arguments(args)

            ret = await func(self, **kwargs)
            filters = self.get_arguments("__filter__")
            if filters and isinstance(ret, dict):
                filtered = {k: ret[k] for k in filters if k in ret}
            else:
                filtered = ret
            self.api_write(filtered)

        # 生成 example url
        nonlocal example_display
        if not example_display and example:
            kv = []
            for arg in arguments:
                arg: Argument
                k = arg.name
                if k not in example:
                    if arg.required:
                        raise ValueError(f'api example: "{k}" is required')
                    continue
                if arg.multi:
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
            "display": display,
        }

        return wrapper

    return decorate


def load_all_api() -> tuple[list[ApiBase], list[tuple[str, ApiBase]]]:
    handlers: list[tuple[str, ApiBase]] = []
    apis: list[ApiBase] = []

    path = os.path.dirname(__file__)
    for finder, name, ispkg in pkgutil.iter_modules([path]):
        module = importlib.import_module("." + name, __name__)
        if not hasattr(module, "handlers"):
            continue
        apis.extend(module.handlers)
        for handler in module.handlers:
            handlers.append((handler.api_url, handler))

    return apis, handlers


# apis 是给 about.py 看的，用于生成前端页面
# handlers 是给 handlers 看的，用于注册路由
# 其实可以合并
apis, handlers = load_all_api()
