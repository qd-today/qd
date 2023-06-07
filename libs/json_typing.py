import typing
from typing import TypedDict


class Env(TypedDict):
    variables: typing.Dict[str, str]
    "用户设置 Task 变量"
    session: typing.List  # TODO：暂时还没看到list中是什么东西


class _NameVlaue(TypedDict):
    name: str
    value: str


Cookie = _NameVlaue
Header = _NameVlaue


class Request(TypedDict):
    url: str
    method: typing.Literal[
        "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"
    ]  # | str
    headers: typing.List[Header]
    cookies: typing.List[Cookie]


ExtractVariable = TypedDict(  # 内含 from 关键字，所以用这个方式声明
    "ExtractVariable",
    {
        "name": str,
        "re": str,
        "from": typing.Literal["content", "status", "header", "header-location"],
    },
)
FailedAssert = TypedDict(
    "FailedAssert",
    {
        "re": str,
        "from": typing.Literal["content", "status", "header", "header-location"],
    },
)
SuccessAssert = TypedDict(
    "SuccessAssert",
    {
        "re": str,
        "from": typing.Literal["content", "status", "header", "header-location"],
    },
)


class Rule(TypedDict):
    extract_variables: typing.List[ExtractVariable]
    failed_asserts: typing.List[FailedAssert]
    success_asserts: typing.List[SuccessAssert]


class HARTest(TypedDict):  # 可能也被用到了其它地方，暂时命名为 HARTest
    env: Env
    request: Request
    rule: Rule
