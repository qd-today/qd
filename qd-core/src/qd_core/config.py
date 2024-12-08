#!/usr/bin/env python
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux <i@binux.me>
#         http://binux.me
# Created on 2014-07-30 12:21:48
# Modified on 2023-06-13 18:12:35
# pylint: disable=invalid-name, wildcard-import
# flake8: noqa: F401,F403

import json
import os
import re
from functools import lru_cache
from gettext import gettext
from pathlib import Path
from typing import List, Literal, Optional, Union

from pydantic import Field, ValidationInfo, field_validator
from pydantic_core import Url
from pydantic_settings import BaseSettings, JsonConfigSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict

# from qd_core.filters.parse_url import UrlInfo, parse_url
DEFAULT_JSON_FILE = "config/settings.json"
DEFAULT_JSON_ENCODING = "utf-8"
DEFAULT_ENV_FILE = "config/.env"
DEFAULT_ENV_ENCODING = "utf-8"


class QDBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        # env_ignore_empty=True,
        env_file=Path(DEFAULT_ENV_FILE),
        env_file_encoding=DEFAULT_ENV_ENCODING,
        json_file=Path(DEFAULT_JSON_FILE),
        json_file_encoding=DEFAULT_JSON_ENCODING,
        str_strip_whitespace=True,
        extra="allow",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            JsonConfigSettingsSource(
                settings_cls,
                json_file=cls.model_config.get("json_file") or DEFAULT_JSON_FILE,
                json_file_encoding=cls.model_config.get("json_file_encoding") or DEFAULT_JSON_ENCODING,
            ),
        )


class LogSettings(QDBaseSettings):
    """日志设置类"""

    debug: bool = Field(default=False, alias="qd_debug", description=gettext("是否启用 QD 框架 Debug"))
    level: str = Field(default=None, description=gettext("QD 框架日志等级"), validate_default=True)
    traceback_print: bool = Field(
        default=None,
        description=gettext("是否启用在控制台日志中打印 Exception 的 TraceBack 信息"),
        validate_default=True,
    )
    display_import_warning: bool = Field(
        default=None, description=gettext("是否在控制台输出导入警告信息"), validate_default=True
    )

    @field_validator("level", mode="before")
    @classmethod
    def validate_level(cls, value: Optional[str], info: ValidationInfo):
        if value is None:
            if info.data["debug"]:
                value = "DEBUG"
            else:
                value = "INFO"
        return value

    @field_validator("traceback_print", mode="before")
    @classmethod
    def validate_traceback_print(cls, value: Optional[bool], info: ValidationInfo):
        value = bool(info.data["debug"]) if value is None else value
        return value

    @field_validator("display_import_warning", mode="before")
    @classmethod
    def validate_display_import_warning(cls, value: Optional[bool], info: ValidationInfo):
        value = bool(info.data["debug"]) if value is None else value
        return value


class ClientRequestSettings(QDBaseSettings):
    """客户端请求设置类"""

    download_size_limit: int = Field(default=5242880, description=gettext("允许用户单次请求下载的最大值，默认为 5MB"))
    request_timeout: float = Field(default=30.0, description=gettext("HTTP Request 请求超时时间（秒）"))
    connect_timeout: float = Field(default=30.0, description=gettext("HTTP Request 连接超时时间（秒）"))
    delay_max_timeout: float = Field(
        default=29.9,
        description=gettext("延时API 最大时间限制（秒），请确保此值小于上述 timeout 配置，否则可能会导致 599 错误"),
        validate_default=True,
    )
    unsafe_eval_timeout: float = Field(default=3.0, description=gettext("unsafe_eval 执行最大时间限制（秒）"))

    @field_validator("delay_max_timeout", mode="after")
    @classmethod
    def validate_delay_timeout(cls, value: float, info: ValidationInfo):
        """验证延时API超时时间是否小于其他timeout配置"""
        if value >= info.data["request_timeout"] or value >= info.data["connect_timeout"]:
            raise ValueError(
                gettext(
                    "delay_max_timeout must be less than both request_timeout={request_timeout} "
                    "and connect_timeout={connect_timeout}."
                ).format(request_timeout=info.data["request_timeout"], connect_timeout=info.data["connect_timeout"])
            )
        return value


class TaskSettings(QDBaseSettings):
    """任务设置类"""

    task_while_loop_timeout: int = Field(
        default=900, description=gettext("任务运行中单个 While 循环最大运行时间, 单位为秒, 默认为15分钟")
    )
    task_request_limit: int = Field(default=1500, description=gettext("任务运行中单个任务最大请求次数, 默认为 1500 次"))


class CurlSettings(QDBaseSettings):
    """Pycurl 相关设置"""

    use_pycurl: bool = Field(
        default=True, description=gettext("是否启用 Pycurl 模块，默认启用。当运行环境缺少 PyCurl 模块时，此设置无效")
    )

    allow_retry: bool = Field(
        default=True,
        description=gettext("在 Pycurl 环境下，若部分请求因某些错误导致失败时，是否自动修改冲突设置并重发请求"),
    )

    dns_server: str = Field(
        default="", description=gettext("通过 Curl 使用指定的 DNS 进行解析，仅在 Pycurl 环境下支持")
    )

    curl_encoding: bool = Field(
        default=True,
        description=gettext(
            "是否允许使用 Curl 进行 Encoding 操作。当遇到 'Error 61 Unrecognized transfer encoding.' 错误，"
            "并且 `ALLOW_RETRY=True` 时，本次请求将禁用 Headers 中的 Content-Encoding 并尝试重试"
        ),
    )

    curl_length: bool = Field(
        default=True,
        alias="CURL_CONTENT_LENGTH",
        description=gettext(
            "是否允许 Curl 使用 Headers 中自定义的 Content-Length 请求。当遇到 'HTTP 400 Bad Request' 错误，"
            "并且 `ALLOW_RETRY=True` 时，本次请求将禁用 Headers 中的 Content-Length 并尝试重试"
        ),
    )

    not_retry_code: list[int] = Field(
        default=[
            301,
            302,
            303,
            304,
            305,
            307,
            400,
            401,
            403,
            404,
            405,
            407,
            408,
            409,
            410,
            412,
            415,
            413,
            414,
            500,
            501,
            502,
            503,
            504,
            599,
        ],
        description=gettext(
            "当满足启用 PyCurl、HTTP Error Code 不在这个列表中、任务代理为空，"
            "并且 `ALLOW_RETRY=True` 时，本次请求将禁用 Pycurl 并尝试重试"
        ),
    )

    empty_retry: bool = Field(
        default=True,
        description=gettext(
            "启用后，在满足启用 PyCurl、返回 Response 为空、任务代理为空，"
            "并且 `ALLOW_RETRY=True` 的情况下，本次请求将禁用 Pycurl 并尝试重试"
        ),
    )


class ProxySettings(QDBaseSettings):
    """代理设置类"""

    # 全局代理域名列表
    # proxies: List[Union[UrlInfo, str, None]] = Field(
    proxies: List[str] = Field(
        default=[],
        description=gettext(
            "全局代理域名列表，默认为空，表示不启用全局代理。代理格式应为 'scheme://username:password@host:port'"
        ),
    )

    proxy_direct_mode: Optional[Literal["regexp", "url"]] = Field(
        default="regexp",
        description=gettext("""直连地址的匹配模式，默认为 'regexp'（正则表达式匹配）以过滤本地请求，可选输入：
- 'regexp': 正则表达式匹配模式；
- 'url': 网址完全匹配模式；
- None : 不启用全局代理黑名单"""),
    )

    proxy_direct: Union[List[Union[str, re.Pattern[str]]]] = Field(
        default=r"(?xi)\A([a-z][a-z0-9+\-.]*://)?(0(.0){3}|127(.0){2}.1|localhost|\[::([\d]+)?\])(:[0-9]+)?",
        description=gettext(
            "根据 `proxy_direct_mode` 的值，此字段可以是满足直连规则的正则表达式字符串"
            "（当 `proxy_direct_mode='regexp'`）或不通过代理请求的 URL 列表（当 `proxy_direct_mode='url'`）。"
            "默认不启用直连规则"
        ),
        validate_default=True,
    )

    # @field_validator('proxies', pre=True, always=True)
    # def convert_proxies_to_urlinfo(cls, v: List[Union[UrlInfo, str, None]]):
    #     return [parse_url(proxy) if isinstance(proxy, str) else proxy for proxy in v]

    @field_validator("proxy_direct", mode="before")
    @classmethod
    def validate_and_compile_proxy_direct(
        cls, v: Optional[Union[str, List[Union[str, re.Pattern[str]]]]], info: ValidationInfo
    ):
        if info.data.get("proxy_direct_mode") == "regexp":
            if isinstance(v, str):
                return [re.compile(v)]
            if isinstance(v, list):
                return [re.compile(pattern) if isinstance(pattern, str) else pattern for pattern in v]
            raise ValueError(
                gettext("When proxy_direct_mode is 'regexp', proxy_direct should be a string or a list of strings.")
            )
        if info.data.get("proxy_direct_mode") == "url":
            if isinstance(v, str):
                return [v]
            if isinstance(v, list) and all(isinstance(url, str) for url in v):
                return v
            raise ValueError(
                gettext("When proxy_direct_mode is 'url', proxy_direct should be a string or a list of URLs.")
            )
        return []


class DdddOcrSettings(QDBaseSettings):
    """DdddOCR 设置类"""

    # 自定义 ONNX 文件名列表
    extra_onnx_name: List[str] = Field(
        default=[""], description=gettext("config 目录下自定义 ONNX 文件名列表（不含 '.onnx' 后缀）")
    )

    # 自定义字符集 JSON 文件名列表
    extra_charsets_name: List[str] = Field(
        default=[""],
        description=gettext("config 目录下自定义 ONNX 对应的自定义 `charsets.json` 文件名列表（不含 '.json' 后缀）"),
    )


class MailSettings(QDBaseSettings):
    """邮件发送相关配置类"""

    mail_smtp: str = Field(default="", description=gettext("邮箱 SMTP 服务器地址"))
    mail_port: int = Field(default=465, description=gettext("邮箱 SMTP 服务器端口"))
    mail_ssl: bool = Field(default=True, description=gettext("是否使用 SSL 加密方式收发邮件"))
    mail_starttls: bool = Field(default=False, description=gettext("是否使用 STARTTLS 加密方式收发邮件，默认不启用"))
    mail_user: str = Field(default="", description=gettext("邮箱用户名"))
    mail_password: str = Field(default="", description=gettext("邮箱密码"))
    mail_from: str = Field(default="", description=gettext("发送时使用的邮箱，默认与 MAIL_USER 相同"))
    mail_domain_https: bool = Field(
        default=False, description=gettext("发送的邮件链接启用 HTTPS，默认为 False，若需要 HTTPS，请在外部设置反向代理")
    )

    # Mailgun 邮件发送方式配置
    mailgun_key: str = Field(
        default="", description=gettext("Mailgun API Key，若不为空则优先使用 Mailgun 方式发送邮件")
    )
    mailgun_domain: str = Field(default="", description=gettext("Mailgun Domain，需要替换为实际的 Mailgun 域名"))


class PushSettings(QDBaseSettings):
    """推送设置类"""

    push_pic_url: Url = Field(
        default="https://gitee.com/qd-today/qd/raw/master/web/static/img/push_pic.png",
        description=gettext("推送图片 URL"),
    )


class I18nSettings(QDBaseSettings):
    """多语言设置类"""

    locale_dir: str = Field(
        default_factory=lambda: os.path.join(os.path.dirname(__file__), "locale"),
        description=gettext("Multi-language directory, default is {locale_dir}").format(
            locale_dir=os.path.join(os.path.dirname(__file__), "locale")
        ),
    )
    locale: str = Field(
        default="zh_CN",
        description=gettext("Locale, default is zh_CN"),
    )
    fallback_locale: str = Field(
        default="en_US",
        description=gettext("Default locale, default is en_US"),
    )
    domain: str = Field(
        default="messages",
        description=gettext("Multilingual domain, default is messages"),
    )


class QDCoreSettings(QDBaseSettings):
    log: LogSettings = Field(default_factory=LogSettings, description=gettext("日志配置"))

    client_request: ClientRequestSettings = Field(
        default_factory=ClientRequestSettings, description=gettext("客户端请求配置")
    )

    task: TaskSettings = Field(default_factory=TaskSettings, description=gettext("任务配置"))

    curl: CurlSettings = Field(default_factory=CurlSettings, description=gettext("pycurl 配置"))

    proxy: ProxySettings = Field(default_factory=ProxySettings, description=gettext("代理配置"))

    ddddocr: DdddOcrSettings = Field(default_factory=DdddOcrSettings, description=gettext("dddocr 配置"))

    mail: MailSettings = Field(default_factory=MailSettings, description=gettext("邮件配置"))

    push: PushSettings = Field(default_factory=PushSettings, description=gettext("推送配置"))

    i18n: I18nSettings = Field(default_factory=I18nSettings, description=gettext("多语言配置"))


@lru_cache
def get_settings() -> QDCoreSettings:
    return QDCoreSettings()


def export_settings_to_json() -> None:
    settings = get_settings()
    json_file = settings.model_config.get("json_file") or DEFAULT_JSON_FILE
    json_file_encoding = settings.model_config.get("json_file_encoding") or DEFAULT_JSON_ENCODING
    if isinstance(json_file, Path):
        json_file = json_file.resolve()
    if not isinstance(json_file, Path):
        raise TypeError(f"json_file must be a Path object, not {type(json_file)}")
    json_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(
        json.dumps(settings.model_dump(mode="json", by_alias=True), indent=4), encoding=json_file_encoding
    )


if __name__ == "__main__":
    export_settings_to_json()
