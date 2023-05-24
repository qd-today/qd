import json
import traceback
import typing
from html import escape

import config

from ..base import logger_Web_Handler
from . import ApiBase, ApiError, Argument, BodyArgument, MultiArgument, api_wrap

# API 插件设计准则：
# - 路径为 /v1/name（旧版保持原先的 /util/name）
# - 返回内容强制为 JSON 格式，格式为：{"code": 200, "message": "ok", "data": "xxx"}
#   一些常见错误对应的 code：
#   - 调用 API 时，缺少必须参数会自动返回 400 错误
#   - 未被处理的异常会自动返回 500 错误
#   - 访问未实现的 API method 会自动返回 405 错误。如只实现了 GET 时访问 POST。
#       如果 POST 和 GET 实现完全相同，可以在 get 函数后写上 post = get
#   - 建议使用 `raise ApiError(status_code, reason)` 设置异常代码和原因
# - 允许 URL 传参（url?key=value）和 POST form 传参，不允许 /delay/value 形式传参（即不允许在 URL 中使用正则），
# - 参数尽量使用简单类型，参数的初始化函数尽量使用内置函数，使用 safe_eval 代替 eval，避免使用 safe_eval
# - 普通参数类型默认为 str，multi 参数类型默认为 list[str]，
#   Body 参数默认为 bytes|str，框架会尝试根据 Content-Type 进行解码，但不保证一定成功，所以建议在 init 中手动检查类型
# - 所有的 key 都使用 ASCII 字符，而不是中英文混用


if config.debug:
    # 示例 API，仅在 debug 模式下可见

    # 最简单的 API 示例
    class Echo1(ApiBase):
        api_name = "回声"
        api_description = "输出 = 输入"  # 不支持 HTML 标签，比如 <br/>
        api_url = "echo1"  # 框架会自动添加前缀 /api/

        @api_wrap(
            arguments=(Argument(name="text", description="输入的文字", required=True),),
            example={"text": "hello world"},
        )
        async def get(self, text: str):
            return text

        post = get

    # get 和 post 使用不同参数的示例
    class Echo2(ApiBase):
        api_name = "回声 2"
        api_description = "输出 = 输入"
        api_url = "echo2"

        @api_wrap(
            arguments=(Argument(name="text", description="输入的文字", required=True),),
            example={"text": "hello world"},
        )
        async def get(self, text: str):
            return text

        # 不提供 example 的示例
        @api_wrap(
            arguments=(
                BodyArgument(
                    name="text", description="输入的文字", required=True, init=lambda x: x
                ),
            ),
        )
        async def post(self, text: bytes):
            return text

    # 直接设置 example_display 的示例
    class Echon(ApiBase):
        api_name = "回声 n"
        api_description = "输出 = 输入*n"
        api_url = "echon"

        @api_wrap(
            arguments=(
                Argument(name="text", required=True, description="输入", type=str),
                Argument(name="n", required=True, description="n", type=int),
            ),
            example_display="text=测试输入&n=3",
        )
        async def get(self, text: str, n: int):
            d = {f"text_{i}": text for i in range(n)}
            return d

    # 用于演示 MultiArgument 的示例
    class Concat(ApiBase):
        api_name = "连接"
        api_description = "输出 = sep.join(text)"
        api_url = "concat"

        @api_wrap(
            arguments=(
                MultiArgument(name="texts", required=True, description="输入", type=str),
                Argument(name="sep", required=True, description="n", type=str),
            ),
            example={"texts": ["1", "2", "9"], "sep": ","},
        )
        async def get(self, texts: list[str], sep: str):
            return sep.join(texts)

    # 用于演示 MultiArgument 的示例 API：Sum
    class Sum(ApiBase):
        api_name = "累加"
        api_description = "输出 = sum(输入)"
        api_url = "sum"

        @api_wrap(
            arguments=(
                MultiArgument(name="input", required=True, description="输入", type=int),
            ),
            example={"input": [1, 2, 9]},
        )
        async def get(self, input: list[int]):
            return sum(input)

    # 复杂类型的示例
    class Example(ApiBase):
        class ArgType(object):
            def __init__(self, s: str):  # 构造函数参数必须是一个 str
                ss = s.split(",")[-1]
                self.v = int(ss)

        api_name = "复杂参数类型"
        api_description = "输出 = class(obj)"
        api_url = "exam2"

        @api_wrap(
            arguments=(
                Argument(name="obj", required=True, description="输入", type=ArgType),
            ),
            example={"obj": "1,2,3,4,5,6,7,8,9"},
        )
        async def get(self, obj: ArgType):
            return obj.v

    # 异常示例
    class ErrorCode(ApiBase):
        api_name = "异常"
        api_description = "引发异常的示例"
        api_url = "error"

        @api_wrap(
            arguments=(
                Argument("code", False, "错误代码", int, default=400),
                Argument("reason", False, "错误原因", str, default="测试错误"),
            ),
            example={"code": 400, "reason": "测试错误"},
        )
        async def get(self, code: int, reason: str):
            raise ApiError(code, reason)

    # 自动异常示例
    class Error2(ApiBase):
        api_name = "异常"
        api_description = "引发异常的示例"
        api_url = "error2"

        @api_wrap(
            arguments=(Argument("index", False, "索引，", int, default=0),),
            example={"index": 0},
        )
        async def get(self, index: int):
            match index:
                case 0:
                    x = 0 / 0
                case 1:
                    try:
                        x = 0 / 0
                    except ZeroDivisionError as e:
                        raise ApiError(500, str(e))
                case 2:
                    x = [0, 1, 2][9]
                case 3:
                    x = {0: 9}[9]
                case 4:
                    return bytes("JSON 无法处理 bytes", "utf-8")
                case _:
                    raise ApiError(418, "I'm a teapot")

    # BodyArgument 和 api_write_json 的示例
    class Json(ApiBase):
        api_name = "json echo"
        api_description = "POST JSON 传参示例"
        api_url = "json"

        @api_wrap(
            arguments=(
                Argument(
                    name="data",
                    required=True,
                    description="输入 JSON",
                    type=typing.Union[dict, list, int, float, bool, None],
                    type_display="json",
                    init=json.loads,
                ),
            ),
            example={
                "data": '{"a": 1, "b": 2}',# {"a": 1, "b": 2}}, # 直接传 dict 的话，Python 将其转化为 str 时，会优先使用单引号，和 JSON 不兼容
                '__ascii__': True, # 每个 API 都会自动添加的参数，用于指示返回的 JSON 是否强制 ASCII 编码（非ASCII字符会被转为 \uXXXX 形式）
                '__indent__': 2}, # 每个 API 都会自动添加的参数，用于指示返回的 JSON 的缩进，0 表示不缩进但是会换行，-1 表示不缩进也不换行
        )
        async def get(self, data: dict):
            return data

        @api_wrap(
            arguments=(
                BodyArgument(
                    name="data",
                    required=True,
                    description="输入 JSON",
                    type=typing.Union[dict, list, int, float, bool, None],
                    type_display="json",
                    init=lambda x: json.loads(x.decode()),
                ),
            ),
            example={"data": '{"a": 1, "b": 2}'},
        )
        async def post(self, data: dict):
            return data

    # 如何使用传统方法实现 API（不建议使用
    class Echo0(ApiBase):
        api_name = "回声"
        api_description = "输出 = 输入"  # 支持 HTML 标签，比如 <br/>
        api_url = "echo0"  # 框架会自动添加前缀 /api/

        async def get(self):
            # 使用原生 tornado API，详细参考 tornado 文档
            text = self.get_argument("text", "")
            self.write(
                escape(text)
            )  # 传统方法，框架没有帮忙设置 Content-Type，需要手动 escape，以避免 XSS 攻击

        # 此处的声明只用于生成前端文档
        get.api = {
            "arguments": (Argument(name="text", description="输入的文字", required=True),),
            "example": "text=hello world",
        }

        post = get
