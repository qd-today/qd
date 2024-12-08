import base64
import json
import urllib.parse as urlparse
from datetime import datetime

from tornado import httpclient
from tornado.httputil import HTTPHeaders

from qd_core.client import cookie_utils
from qd_core.client.fetcher import logger_fetcher
from qd_core.config import get_settings
from qd_core.filters.codecs import decode, find_encoding
from qd_core.utils.i18n import gettext


class Response:
    def __init__(self, response: httpclient.HTTPResponse):
        self.response = response
        self.request = response.request

    def build_headers(self, headers):
        result = []
        if headers and isinstance(headers, HTTPHeaders):
            for k, v in headers.get_all():
                result.append(dict(name=k, value=v))
        return result

    def build_request(self, request: httpclient.HTTPRequest):
        url = urlparse.urlparse(request.url)
        ret = dict(
            method=request.method,
            url=request.url,
            httpVersion="HTTP/1.1",
            headers=self.build_headers(request.headers),
            queryString=[{"name": n, "value": v} for n, v in urlparse.parse_qsl(url.query)],
            cookies=[{"name": n, "value": v} for n, v in urlparse.parse_qsl(request.headers.get("cookie", ""))],
            headersSize=-1,
            bodySize=len(request.body) if request.body else 0,
        )
        if request.body:
            # if isinstance(request.body, bytes):
            #     request._body = request.body.decode()  # pylint: disable=protected-access
            ret["postData"] = dict(
                mimeType=request.headers.get("content-type"),
                text=request.body,
            )
            if ret["postData"]["mimeType"] and "application/x-www-form-urlencoded" in ret["postData"]["mimeType"]:
                ret["postData"]["params"] = [{"name": n, "value": v} for n, v in urlparse.parse_qsl(request.body)]
                try:
                    _ = json.dumps(ret["postData"]["params"])
                except UnicodeDecodeError as e:
                    logger_fetcher.error(
                        gettext("params encoding error: %s"), e, exc_info=get_settings().log.traceback_print
                    )
                    del ret["postData"]["params"]

        return ret

    def build_response(self, response: httpclient.HTTPResponse):
        cookies = cookie_utils.CookieSession()
        cookies.extract_cookies_to_jar(response.request, response)

        encoding = find_encoding(response.body, response.headers)
        if not response.headers.get("content-type"):
            response.headers["content-type"] = "text/plain"
        if "charset=" not in response.headers.get("content-type", ""):
            response.headers["content-type"] += "; charset=" + encoding

        return dict(
            status=response.code,
            statusText=response.reason,
            headers=self.build_headers(response.headers),
            cookies=cookies.to_json(),
            content=dict(
                size=len(response.body),
                mimeType=response.headers.get("content-type"),
                text=base64.b64encode(response.body).decode("ascii"),
                decoded=decode(response.body, response.headers),
            ),
            redirectURL=response.headers.get("Location"),
            headersSize=-1,
            bodySize=-1,
        )

    def response2har(self):
        entry = dict(
            startedDateTime=datetime.now().isoformat(),
            time=self.response.request_time,
            request=self.build_request(self.request),
            response=self.build_response(self.response),
            cache={},
            timings=self.response.time_info,
            connections="0",
            pageref="page_0",
        )
        if self.response.body and "image" in self.response.headers.get("content-type"):
            entry["response"]["content"]["decoded"] = base64.b64encode(self.response.body).decode("ascii")
        return entry


class Template:
    def build_request(self, en):
        url = urlparse.urlparse(en["request"]["url"])
        request = dict(
            method=en["request"]["method"],
            url=en["request"]["url"],
            httpVersion="HTTP/1.1",
            headers=[
                {"name": x["name"], "value": x["value"], "checked": True} for x in en["request"].get("headers", [])
            ],
            queryString=[{"name": n, "value": v} for n, v in urlparse.parse_qsl(url.query)],
            cookies=[
                {"name": x["name"], "value": x["value"], "checked": True} for x in en["request"].get("cookies", [])
            ],
            headersSize=-1,
            bodySize=len(en["request"].get("data")) if en["request"].get("data") else 0,
        )
        if en["request"].get("data"):
            request["postData"] = dict(
                mimeType=en["request"].get("mimeType"),
                text=en["request"].get("data"),
            )
            if (
                request["postData"]["mimeType"]
                and "application/x-www-form-urlencoded" in request["postData"]["mimeType"]
            ):
                params = [{"name": x[0], "value": x[1]} for x in urlparse.parse_qsl(en["request"]["data"], True)]
                request["postData"]["params"] = params
                try:
                    _ = json.dumps(request["postData"]["params"])
                except UnicodeDecodeError as e:
                    logger_fetcher.error(
                        gettext("params encoding error: %s"), e, exc_info=get_settings().log.traceback_print
                    )
                    del request["postData"]["params"]
        return request

    def tpl2har(self, tpl):
        entries = []
        for en in tpl:
            entry = dict(
                checked=True,
                startedDateTime=datetime.now().isoformat(),
                time=1,
                request=self.build_request(en),
                response={},
                cache={},
                timings={},
                connections="0",
                pageref="page_0",
                success_asserts=en.get("rule", {}).get("success_asserts", []),
                failed_asserts=en.get("rule", {}).get("failed_asserts", []),
                extract_variables=en.get("rule", {}).get("extract_variables", []),
            )
            entries.append(entry)
        return dict(log=dict(creator=dict(name="binux", version="QD"), entries=entries, pages=[], version="1.2"))
