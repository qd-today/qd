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

    debug: bool = Field(default=False, alias="qd_debug", description=gettext("Whether to enable QD Framework Debug"))
    level: str = Field(default=None, description=gettext("QD framework log level"), validate_default=True)
    traceback_print: bool = Field(
        default=None,
        description=gettext("Whether to enable printing of TraceBack information for Exception in the console output"),
        validate_default=True,
    )
    display_import_warning: bool = Field(
        default=None,
        description=gettext("Whether to import warning messages in the console output"),
        validate_default=True,
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

    download_size_limit: int = Field(
        default=5242880, description=gettext("Maximum download size allowed for a single user request, default is 5MB")
    )
    request_timeout: float = Field(default=30.0, description=gettext("HTTP request timeout (seconds)"))
    connect_timeout: float = Field(default=30.0, description=gettext("HTTP request connection timeout (seconds)"))
    delay_max_timeout: float = Field(
        default=29.9,
        description=gettext(
            "Delay API Maximum time limit (seconds), "
            "make sure this value is less than the timeout configuration above, "
            "otherwise it may result in 599 error"
        ),
        validate_default=True,
    )
    unsafe_eval_timeout: float = Field(
        default=3.0, description=gettext("Maximum time limit for unsafe_eval execution (seconds)")
    )

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
        default=900,
        description=gettext("Maximum runtime for a single While loop in a task, in seconds, default is 15 minutes"),
    )
    task_request_limit: int = Field(
        default=1500, description=gettext("Maximum number of requests for a single task in a task run, default is 1500")
    )


class CurlSettings(QDBaseSettings):
    """Pycurl 相关设置"""

    use_pycurl: bool = Field(
        default=True,
        description=gettext(
            "Whether to enable the PyCurl module, enabled by default. "
            "This setting has no effect when the running environment is missing the PyCurl module"
        ),
    )

    allow_retry: bool = Field(
        default=True,
        description=gettext(
            "In PyCurl environment, if some requests fail due to some errors, "
            "whether to automatically modify the conflict settings and resend the requests"
        ),
    )

    dns_server: str = Field(
        default="",
        description=gettext(
            "Resolve by using the specified DNS through Curl, which is only supported in PyCurl environment"
        ),
    )

    curl_encoding: bool = Field(
        default=True,
        description=gettext(
            "Whether to allow Encoding operations with Curl. "
            "When an 'Error 61 Unrecognized transfer encoding.' error is encountered, "
            "and `ALLOW_RETRY=True`, this request will disable Content-Encoding in Headers and try again"
        ),
    )

    curl_length: bool = Field(
        default=True,
        alias="CURL_CONTENT_LENGTH",
        description=gettext(
            "Whether Curl is allowed to use the custom Content-Length request in Headers. "
            "When an' HTTP 400 Bad Request' error is encountered and' ALLOW_RETRY=True', "
            "this request will disable the Content-Length in Headers and try again"
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
            "If PyCurl is enabled, HTTP Error Code is not in this list, the task proxy is empty, "
            "and `ALLOW_RETRY=True` is met, PyCurl will be disabled for this request and attempts will be retried"
        ),
    )

    empty_retry: bool = Field(
        default=True,
        description=gettext(
            "If PyCurl is enabled, the returned Response is empty, the task agent is empty, "
            "and `ALLOW_RETRY=True`, this request will disable PyCurl and try again"
        ),
    )


class ProxySettings(QDBaseSettings):
    """代理设置类"""

    # 全局代理域名列表
    # proxies: List[Union[UrlInfo, str, None]] = Field(
    proxies: List[str] = Field(
        default=[],
        description=gettext(
            "Global proxy domain name list, which is empty by default, indicating that global proxy is not enabled. "
            "The proxy format should be 'scheme://username:password@host:port'"
        ),
    )

    proxy_direct_mode: Optional[Literal["regexp", "url"]] = Field(
        default="regexp",
        description=gettext(
            "Matching mode of directly connected address, "
            """default is' regexp'(regular expression matching) to filter local requests, optional input:
- 'regexp': Regular expression matching pattern;
- 'url': the URL exactly matches the pattern;
- None: global proxy blacklist is not enabled"""
        ),
    )

    proxy_direct: Union[List[Union[str, re.Pattern[str]]]] = Field(
        default=r"(?xi)\A([a-z][a-z0-9+\-.]*://)?(0(.0){3}|127(.0){2}.1|localhost|\[::([\d]+)?\])(:[0-9]+)?",
        description=gettext(
            "Depending on the value of `proxy_direct_mode`, this field can be a regular expression string "
            "that satisfies the direct connection rule (when `proxy_direct_mode='regexp'`) "
            "or a list of URLs that are not requested through the proxy (when `proxy_direct_mode='url'`). "
            "Direct rules are not enabled by default"
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
        default=[""],
        description=gettext("Customized ONNX filename list in the config directory (excluding '.onnx' suffix)"),
    )

    # 自定义字符集 JSON 文件名列表
    extra_charsets_name: List[str] = Field(
        default=[""],
        description=gettext(
            "Customized `charsets.json` filename list corresponding to customized ONNX "
            "in the config directory (excluding '.json' suffix)"
        ),
    )


class MailSettings(QDBaseSettings):
    """邮件发送相关配置类"""

    mail_smtp: str = Field(default="", description=gettext("Mailbox SMTP server address"))
    mail_port: int = Field(default=465, description=gettext("Mailbox SMTP server port"))
    mail_ssl: bool = Field(default=True, description=gettext("Whether to use SSL encryption to send and receive mail"))
    mail_starttls: bool = Field(
        default=False,
        description=gettext(
            "Whether to use STARTTLS encryption to send and receive emails. It is not enabled by default"
        ),
    )
    mail_user: str = Field(default="", description=gettext("Mailbox username"))
    mail_password: str = Field(default="", description=gettext("Mailbox password"))
    mail_from: str = Field(
        default="", description=gettext("The mailbox used when sending is the same as MAIL_USER by default")
    )
    mail_domain_https: bool = Field(
        default=False,
        description=gettext(
            "Whether to enable HTTPS for the sent email link, the default is False. "
            "If you need HTTPS, please set the reverse proxy externally"
        ),
    )

    # Mailgun 邮件发送方式配置
    mailgun_key: str = Field(
        default="",
        description=gettext("Mailgun API Key. If it is not empty, Mailgun will be used first to send emails"),
    )
    mailgun_domain: str = Field(
        default="",
        description=gettext("Mailgun Domain, which needs to be replaced with the actual Mailgun domain name"),
    )


class PushSettings(QDBaseSettings):
    """推送设置类"""

    push_pic_url: Url = Field(
        default="https://gitee.com/qd-today/qd/raw/master/web/static/img/push_pic.png",
        description=gettext("Picture URL for push notification"),
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
    log: LogSettings = Field(default_factory=LogSettings, description=gettext("Log settings"))

    client_request: ClientRequestSettings = Field(
        default_factory=ClientRequestSettings, description=gettext("Client requests settings")
    )

    task: TaskSettings = Field(default_factory=TaskSettings, description=gettext("Task settings"))

    curl: CurlSettings = Field(default_factory=CurlSettings, description=gettext("PyCurl settings"))

    proxy: ProxySettings = Field(default_factory=ProxySettings, description=gettext("Proxy settings"))

    ddddocr: DdddOcrSettings = Field(default_factory=DdddOcrSettings, description=gettext("DdddOCR settings"))

    mail: MailSettings = Field(default_factory=MailSettings, description=gettext("Mail settings"))

    push: PushSettings = Field(default_factory=PushSettings, description=gettext("Push settings"))

    i18n: I18nSettings = Field(default_factory=I18nSettings, description=gettext("Multi-language settings"))


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
