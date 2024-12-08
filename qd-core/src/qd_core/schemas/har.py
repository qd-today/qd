from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field, InstanceOf
from tornado.httpclient import HTTPResponse

from qd_core.client import cookie_utils
from qd_core.utils.i18n import gettext


class Cookie(BaseModel):
    name: str
    value: str


class Header(BaseModel):
    name: str
    value: str


class Request(BaseModel):
    url: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    headers: List[Header]
    cookies: List[Cookie]
    data: Optional[str] = None


class ExtractVariable(BaseModel):
    name: str
    re: str
    from_: Literal["content", "status", "header", "header-location"] = Field(
        ..., alias="from"
    )  # 使用 Field 的 alias 参数处理关键字冲突


class FailedAssert(BaseModel):
    re: str
    from_: Literal["content", "status", "header", "header-location"] = Field(..., alias="from")


class SuccessAssert(BaseModel):
    re: str
    from_: Literal["content", "status", "header", "header-location"] = Field(..., alias="from")


class Rule(BaseModel):
    extract_variables: List[ExtractVariable]
    failed_asserts: List[FailedAssert]
    success_asserts: List[SuccessAssert]


class Env(BaseModel):
    variables: dict[str, Any] = Field(description=gettext("用户设置 Task 变量"))
    session: Union[List, InstanceOf[cookie_utils.CookieSession]]


class HAR(BaseModel):  # 命名为 HARTest 或根据实际用途调整
    env: Env
    request: Request
    rule: Rule


class Result(BaseModel):
    success: bool
    msg: str
    env: Env
    response: InstanceOf[HTTPResponse]
