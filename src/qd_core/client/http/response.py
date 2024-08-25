import json
import time
import traceback
from io import BytesIO
from typing import Any, Dict, List, Tuple

from pydantic import AnyUrl, ValidationError
from starlette.routing import Match as StarletteMatch
from tornado import httpclient, simple_httpclient
from tornado.escape import parse_qs_bytes, to_unicode
from tornado.httputil import HTTPFile, parse_body_arguments

from qd_core.client.http.request import RequestBuilder
from qd_core.config import get_settings
from qd_core.plugins.base import router
from qd_core.schemas.har import HAR, Env, Request, Rule
from qd_core.schemas.url import ApiUrl
from qd_core.utils.log import Log
from qd_core.utils.router import match_route_path

logger = Log("QD.Core.Client.Http").getlogger()
NOT_RETYR_CODE = get_settings().curl.not_retry_code


class ResponseBuilder:
    def __init__(self, **kwargs):
        self.request_builder = RequestBuilder(**kwargs)
        self.http_client = httpclient.AsyncHTTPClient()

    async def build_api_response(self, req: httpclient.HTTPRequest):
        start_time = time.time()
        # 提取查询参数
        if req.url is None:
            raise httpclient.HTTPError(400, "API url is required")
        api = ApiUrl(url=AnyUrl(req.url))
        query = api.url.query
        first_path = api.get_first_path()

        if not api.url.path or not first_path:
            raise httpclient.HTTPError(400, "API must have at least one level of path")

        query_dict = {}  # type: Dict[str, str]
        if query:
            arguments = parse_qs_bytes(query, keep_blank_values=True)
            for key, values in arguments.items():
                query_dict[key] = to_unicode(values[-1])

        body_dict: Dict[str, Any] = {}
        if req.body:
            if req.headers.get("Content-Type", "").lower().startswith("application/json"):
                body_dict = json.loads(req.body)
            else:
                body_arguments: Dict[str, List[bytes]] = {}
                file_arguments: Dict[str, List[HTTPFile]] = {}
                parse_body_arguments(
                    req.headers.get("Content-Type", "application/x-www-form-urlencoded"),
                    req.body,
                    body_arguments,
                    file_arguments,
                    req.headers,
                )
                for k, v in body_arguments.items():
                    body_dict[k] = to_unicode(v[-1])

        # 合并查询参数和请求体的数据
        combined_data = {**query_dict, **body_dict}
        match, scope = match_route_path(
            api.url.path,
            req.method,
            router.routes,  # type: ignore
        )

        if match == StarletteMatch.FULL:
            endpoint = scope.get("endpoint")
            path_params = scope.get("path_params", {})
            combined_data.update(path_params)
            if endpoint:
                try:
                    model_data = await endpoint(**combined_data)
                except (ValueError, ValidationError) as e:
                    # 处理数据不符合模型约束的情况
                    message = f"Error parsing data to Pydantic model: {e}"
                    logger.error(message, exc_info=get_settings().log.traceback_print)
                    raise httpclient.HTTPError(406, message=message)
            else:
                raise httpclient.HTTPError(404, message="API endpoint not found")
        elif match == StarletteMatch.PARTIAL:
            raise httpclient.HTTPError(405)
        else:
            raise httpclient.HTTPError(404, message="API not found")

        if isinstance(model_data, dict):
            model_data = json.dumps(model_data, indent=4, ensure_ascii=False)
        return httpclient.HTTPResponse(
            request=req,
            code=200,
            buffer=BytesIO(str(model_data).encode()),
            request_time=time.time() - req.start_time,
            start_time=start_time,
        )

    async def build_response(
        self,
        obj: HAR,
        proxy=None,
        curl_encoding=get_settings().curl.curl_encoding,
        curl_content_length=get_settings().curl.curl_length,
        empty_retry=get_settings().curl.empty_retry,
    ) -> Tuple[Rule, Env, httpclient.HTTPResponse]:
        if proxy is None:
            proxy = {}
        allow_retry = get_settings().curl.allow_retry
        try:
            req, rule, env = self.request_builder.build(
                obj,
                proxy=proxy,
            )
            if req.url.startswith("api://"):
                allow_retry = False
                response = await self.build_api_response(req)
            else:
                response = await self.http_client.fetch(req)
            logger.debug(
                "%d %s %s %.2fms",
                response.code,
                response.request.method,
                response.request.url,
                1000.0 * response.request_time,
            )
        except httpclient.HTTPError as e:
            try:
                if allow_retry and get_settings().curl.use_pycurl:
                    if e.__dict__.get("errno", "") == 61:
                        logger.warning("%s %s [Warning] %s -> Try to retry!", req.method, req.url, e)
                        req, rule, env = self.request_builder.build(
                            obj,
                            proxy=proxy,
                            curl_encoding=False,
                            curl_content_length=curl_content_length,
                        )
                        e.response = await self.http_client.fetch(req)
                    elif e.code == 400 and e.message == "Bad Request" and req and req.headers.get("content-length"):
                        logger.warning("%s %s [Warning] %s -> Try to retry!", req.method, req.url, e)
                        req, rule, env = self.request_builder.build(
                            obj,
                            proxy=proxy,
                            curl_encoding=curl_encoding,
                            curl_content_length=False,
                        )
                        e.response = await self.http_client.fetch(req)
                    elif e.code not in NOT_RETYR_CODE or (empty_retry and not e.response):
                        try:
                            logger.warning("%s %s [Warning] %s -> Try to retry!", req.method, req.url, e)
                            client = simple_httpclient.SimpleAsyncHTTPClient()
                            e.response = await client.fetch(req)
                        except Exception as e0:
                            logger.error(
                                e.message.replace("\\r\\n", "\r\n")
                                or (str(e.response) if e.response else "").replace("\\r\\n", "\r\n")
                                or e0,
                                exc_info=get_settings().log.traceback_print,
                            )
                    else:
                        try:
                            logger.warning("%s %s [Warning] %s", req.method, req.url, e)
                        except Exception as e0:
                            logger.error(
                                e.message.replace("\\r\\n", "\r\n")
                                or (str(e.response) if e.response else "").replace("\\r\\n", "\r\n")
                                or e0,
                                exc_info=get_settings().log.traceback_print,
                            )
                else:
                    logger.warning("%s %s [Warning] %s", req.method, req.url, e)
            finally:
                if "req" not in locals().keys():
                    tmp = HAR(
                        env=obj.env,
                        rule=obj.rule,
                        request=Request(
                            url="api://util/unicode?content=", method="GET", headers=[], cookies=[], data=None
                        ),
                    )
                    req, rule, env = self.request_builder.build(tmp)
                    e.response = httpclient.HTTPResponse(
                        request=req, code=e.code, reason=e.message, buffer=BytesIO(str(e).encode())
                    )
                if not e.response:
                    if get_settings().log.traceback_print:
                        traceback.print_exc()
                    e.response = httpclient.HTTPResponse(
                        request=req, code=e.code, reason=e.message, buffer=BytesIO(str(e).encode())
                    )
                return rule, env, e.response
        return rule, env, response
