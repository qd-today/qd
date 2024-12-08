from typing import Optional

from jinja2.sandbox import SandboxedEnvironment as Environment
from tornado import httpclient

from qd_core import filters
from qd_core.client import cookie_utils
from qd_core.config import get_settings
from qd_core.filters.codecs import quote_chinese
from qd_core.schemas.har import Env, Request
from qd_core.utils.i18n import gettext


class Renderer:
    def __init__(self):
        self.jinja_env = Environment()
        self.jinja_env.globals = filters.jinja_globals
        self.jinja_env.globals.update(filters.jinja_inner_globals)
        self.jinja_env.filters.update(filters.jinja_globals)

    def render_string(self, key: str, value: Optional[str], env: Env, _cookies: cookie_utils.CookieSession):
        if not value:
            return value
        try:
            value = self.jinja_env.from_string(value).render(_cookies=_cookies, **env.variables)
            return value
        except Exception as e:
            log_error = gettext("The error occurred when rendering template {key}: {value} \\r\\n {str_e}").format(
                key=key, value=value, str_e=repr(e)
            )
            raise httpclient.HTTPError(500, log_error)

    def render(self, request: Request, env: Env) -> Request:
        if env.session is None:
            env.session = []

        if isinstance(env.session, cookie_utils.CookieSession):
            _cookies = env.session
        else:
            _cookies = cookie_utils.CookieSession()
            _cookies.from_json(env.session)

        request.method = self.render_string("request.method", request.method, env, _cookies)
        request.url = self.render_string("request.url", request.url, env, _cookies)
        for header in request.headers:
            header.name = self.render_string("header.name", header.name, env, _cookies)
            if get_settings().curl.use_pycurl and header.name and header.name[0] == ":":
                header.name = header.name[1:]
            header.value = self.render_string("header.value", header.value, env, _cookies)
            header.value = quote_chinese(header.value)
        for cookie in request.cookies:
            cookie.name = self.render_string("cookie.name", cookie.name, env, _cookies)
            cookie.value = self.render_string("cookie.value", cookie.value, env, _cookies)
            cookie.value = quote_chinese(cookie.value, env, _cookies)
        request.data = self.render_string("request.data", request.data, env, _cookies)
        return request
