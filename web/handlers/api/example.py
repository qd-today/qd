import json
import traceback
import typing

import config

from . import ApiBase, Argument, api_wrap, ApiError


# API 插件设计准则：
# - 路径为 /api/name（旧版保持原先的 /util/name）
# - 使用 HTTP 状态码标示状态，而不是 Rtv["状态"] = "200"
#   - 调用 API 时，缺少必须参数会自动返回 HTTP 400 错误
#   - 处理请求时，未被处理的异常会自动返回 HTTP 500 错误
#   - 访问未实现的 API method 会自动返回 HTTP 405 错误。如只实现了 GET 时访问 POST。
#       如果 POST 和 GET 实现完全相同，可以在 get 函数后写上 post = get
#   - 建议使用 `raise ApiError(status_code, reason)` 设置异常代码和原因（见 ExampleErrorHandler）
# - 允许 URL 传参（url?key=value）和 POST form 传参，不允许 /delay/value 形式传参（即不允许在 URL 中使用正则），
#   不建议使用 POST JSON 传参（见 JSONHandler）
# - 参数尽量使用简单类型，参数的初始化函数尽量使用内置函数，使用 safe_eval 代替 eval，避免使用 safe_eval
# - 所有的 key 都使用 ASCII 字符，而不是中英文混用
# - 返回值：简单类型直接返回（str、int、float）；
#         dict 只有一对键值对的直接返回值，多条返回值的转为 JSON 格式；
#         bytes 类型会设置 Content-Type: application/octet-stream 头，然后直接返回；
#         其他情形都转为 JSON 格式。
#         如果希望避免不可控，可以将返回值处理为 str 类型。
#     支持传参 `__filter__` 对返回 dict 进行过滤，过滤后只剩一对的，直接返回值。
#     例：
#     ```
#     > api://api/timestamp
#     < {"timestamp": 1625068800, "weak": "4/26", day: "182/165", ...}
#
#     > api://api/timestamp?__fileter__=timestamp
#     < 1625068800
#
#     > api://api/timestamp?__fileter__=timestamp&__fileter__=weak
#     < {"timestamp": 1625068800, "weak": "4/26"}
#     ```
# - 其他规范见 ApiBase 和 Argument 源码


# 最简单的 API 示例
class Echo1(ApiBase):
    api_name = "回声"
    api_description = "输出 = 输入"  # 支持 HTML 标签，比如 <br/>
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
            Argument(name="text", description="输入的文字", required=True, from_body=True),
        ),
    )
    async def post(self, text: str):
        return text


# __filter__ 和 直接设置 example_display 的示例
class Echon(ApiBase):
    api_name = "回声 n"
    api_description = "输出 = 输入*n"
    api_url = "echon"

    @api_wrap(
        arguments=(
            Argument(name="text", required=True, description="输入", type=str),
            Argument(name="n", required=True, description="n", type=int),
        ),
        example_display="text=测试输入&n=3&__filter__=text_0",
    )
    async def get(self, text: str, n: int):
        d = {f"text_{i}": text for i in range(n)}
        return d


# 用于演示 multi 的示例
class Concat(ApiBase):
    api_name = "连接"
    api_description = "输出 = sep.join(text)"
    api_url = "concat"

    @api_wrap(
        arguments=(
            Argument(
                name="texts", required=True, description="输入", type=str, multi=True
            ),
            Argument(name="sep", required=True, description="n", type=str),
        ),
        example={"texts": ["1", "2", "9"], "sep": ","},
    )
    async def get(self, texts: list[str], sep: str):
        return sep.join(texts)


# 用于演示 multi 的示例 API：Sum
class Sum(ApiBase):
    api_name = "累加"
    api_description = "输出 = sum(输入)"
    api_url = "sum"

    @api_wrap(
        arguments=(
            Argument(
                name="input", required=True, description="输入", type=int, multi=True
            ),
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
class Error(ApiBase):
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
        if code == 999:
            eee = 9 / 0  # 会直接返回 500，前端不显示详细报错原因，控制台打印完整报错信息
        elif code == 998:
            try:
                eee = 9 / 0
            except ZeroDivisionError as e:
                if config.traceback_print:
                    traceback.print_exc()  # 根据全局设置决定是否在控制台打印完整报错信息
                raise ApiError(500, str(e))  # 还是返回 500，但是前端有报错原因，控制台打印简短信息
        else:
            raise ApiError(code, reason)


# from_body 和 api_write_json 的示例
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
        # example={"data": {"a": 1, "b": 2}}, # 直接传 dict 的话，Python 将其转化为 str 时，会优先使用单引号，和 JSON 不兼容
        example={"data": '{"a": 1, "b": 2}'},
    )
    async def get(self, data: dict):
        return data

    @api_wrap(
        arguments=(
            Argument(
                name="data",
                required=True,
                description="输入 JSON",
                type=typing.Union[dict, list, int, float, bool, None],
                type_display="json",
                init=json.loads,
                from_body=True,
            ),
            Argument(
                name="indent", required=False, description="缩进", type=int, default=4
            ),
        ),
        example={"data": '{"a": 1, "b": 2}', "indent": 2},
    )
    async def post(self, data: dict, indent: int):
        self.api_write_json(
            data, indent=indent
        )  # 使用 self.api_write_json() 不会受到 __filter__ 影响


# 如何使用传统方法实现 API（不建议使用
class Echo0(ApiBase):
    api_name = "回声"
    api_description = "输出 = 输入"  # 支持 HTML 标签，比如 <br/>
    api_url = "echo0"  # 框架会自动添加前缀 /api/

    async def get(self):
        # 使用原生 tornado API，详细参考 tornado 文档
        text = self.get_argument("text", '')
        self.write(text)
    
    # 此处的声明只用于生成前端文档
    get.api = {
        'arguments': (Argument(name="text", description="输入的文字", required=True),),
        'example': 'text=hello world',
    }

    post = get


handlers = (Echo1, Echo2, Echon, Concat, Sum, Example, Json, Echo0)
