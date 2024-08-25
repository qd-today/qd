import base64
import json
import re

from tornado import httpclient
from tornado.httputil import HTTPHeaders

from qd_core.client import cookie_utils
from qd_core.client.http.response import ResponseBuilder
from qd_core.client.render import Renderer
from qd_core.config import get_settings
from qd_core.filters.codecs import decode
from qd_core.schemas.har import HAR, Env, Result, Rule
from qd_core.utils.log import Log

logger = Log("QD.Core.Client.Http").getlogger()


class HttpHandler:
    def __init__(
        self,
        **kwargs,
    ):
        self.http_response_builder = ResponseBuilder(**kwargs)
        self.renderer = Renderer()

    def run_rule(self, response: httpclient.HTTPResponse, rule: Rule, env: Env):
        success = True
        msg = ""

        content = [
            -1,
        ]

        def getdata(_from):
            if _from == "content":
                if content[0] == -1:
                    if response.headers and isinstance(response.headers, HTTPHeaders):
                        content[0] = decode(response.body, headers=response.headers)
                    else:
                        content[0] = decode(response.body)
                if "content-type" in response.headers:
                    if "image" in response.headers.get("content-type"):
                        return base64.b64encode(response.body).decode("utf8")
                return content[0]
            elif _from == "status":
                return f"{response.code}"
            elif _from.startswith("header-"):
                _from = _from[7:]
                return response.headers.get(_from, "")
            elif _from == "header":
                try:
                    if hasattr(response, "headers") and isinstance(response.headers, HTTPHeaders):
                        return "\n".join([f"{key}: {value}" for key, value in response.headers.get_all()])
                    return "\n".join([f"{key}: {value}" for key, value in response.headers._dict.items()])  # pylint: disable=protected-access
                except Exception as e:
                    logger.error("Run rule failed: %s", str(e), exc_info=get_settings().log.traceback_print)
                try:
                    return json.dumps(response.headers._dict)  # pylint: disable=protected-access
                except Exception as e:
                    logger.error("Run rule failed: %s", str(e), exc_info=get_settings().log.traceback_print)
            else:
                return ""

        session = env.session
        if isinstance(session, cookie_utils.CookieSession):
            _cookies = session
        else:
            _cookies = cookie_utils.CookieSession()
            _cookies.from_json(session)

        for success_assert in rule.success_asserts:
            self.renderer.render_string("rule.success_asserts.re", success_assert.re, env, _cookies)
            if success_assert.re and re.search(success_assert.re, getdata(success_assert.from_)):
                msg = ""
                break
            else:
                msg = f"Fail assert: {success_assert.model_dump_json()} from success_asserts"
        else:
            if rule.success_asserts:
                success = False

        for failed_assert in rule.failed_asserts:
            self.renderer.render_string("rule.failed_asserts.re", failed_assert.re, env, _cookies)
            if failed_assert.re and re.search(failed_assert.re, getdata(failed_assert.from_)):
                success = False
                msg = f"Fail assert: {failed_assert.model_dump_json()} from failed_asserts"
                break

        if not success and msg and (response.error or (response.reason and str(response.reason) != "OK")):
            msg += f", \\r\\nResponse Error : {response.error or response.reason}"

        for extract_variable in rule.extract_variables:
            pattern = extract_variable.re
            flags = 0
            find_all = False

            re_m = re.match(r"^/(.*?)/([gimsu]*)$", extract_variable.re)
            if re_m:
                pattern = re_m.group(1)
                if "g" in re_m.group(2):
                    find_all = True  # 全局匹配
                if "i" in re_m.group(2):
                    flags |= re.I  # 使匹配对大小写不敏感
                if "m" in re_m.group(2):
                    flags |= re.M  # 多行匹配，影响 ^ 和 $
                if "s" in re_m.group(2):
                    flags |= re.S  # 使 . 匹配包括换行在内的所有字符
                if "u" in re_m.group(2):
                    flags |= re.U  # 根据Unicode字符集解析字符。这个标志影响 \w, \W, \b, \B.
                if "x" in re_m.group(2):
                    pass  # flags |= re.X # 该标志通过给予你更灵活的格式以便你将正则表达式写得更易于理解。暂不启用

            if find_all:
                try:
                    env.variables[extract_variable.name] = re.compile(pattern, flags).findall(
                        getdata(extract_variable.from_)
                    )
                except Exception as e:
                    env.variables[extract_variable.name] = str(e)
            else:
                try:
                    m = re.compile(pattern, flags).search(getdata(extract_variable.from_))
                    if m:
                        if m.groups():
                            match_result = m.groups()[0]
                        else:
                            match_result = m.group(0)
                        env.variables[extract_variable.name] = match_result
                except Exception as e:
                    env.variables[extract_variable.name] = str(e)
        return success, msg

    async def do_request(
        self,
        obj: HAR,
        proxy=None,
        curl_encoding=get_settings().curl.curl_encoding,
        curl_content_length=get_settings().curl.curl_length,
        empty_retry=get_settings().curl.empty_retry,
    ):
        """
        obj = {
          request: {
            method:
            url:
            headers: [{name: , value: }, ]
            cookies: [{name: , value: }, ]
            data:
          }
          rule: {
            success_asserts: [{re: , from: 'content'}, ]
            failed_asserts: [{re: , from: 'content'}, ]
            extract_variables: [{name: , re:, from: 'content'}, ]
          }
          env: {
            variables: {
              name: value
            }
            session: [
            ]
          }
        }
        """
        if proxy is None:
            proxy = {}

        rule, env, response = await self.http_response_builder.build_response(
            obj, proxy, curl_encoding, curl_content_length, empty_retry
        )

        if isinstance(env.session, cookie_utils.CookieSession):
            env.session.extract_cookies_to_jar(response.request, response)
        success, msg = self.run_rule(response, rule, env)

        return Result(success=success, msg=msg, response=response, env=env)
