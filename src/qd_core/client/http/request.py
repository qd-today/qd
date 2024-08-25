import re
from typing import Dict, Optional

from tornado import httpclient
from tornado.escape import native_str
from tornado.httputil import HTTPHeaders

from qd_core.client import cookie_utils
from qd_core.client.render import Renderer
from qd_core.config import get_settings
from qd_core.filters.parse_url import urlmatch
from qd_core.schemas.har import HAR, Request
from qd_core.utils.log import Log

logger = Log("QD.Core.Client.Http").getlogger()
if get_settings().curl.use_pycurl:
    try:
        import pycurl  # type: ignore

        httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    except ImportError as e:
        if get_settings().log.display_import_warning:
            logger.warning(
                'Import PyCurl module falied: "%s". \n'
                "Tips: This warning message is only for prompting, it will not affect running of QD framework.",
                e,
            )
        pycurl = None
else:
    pycurl = None  # pylint: disable=invalid-name


class RequestBuilder:
    def __init__(
        self,
        download_size_limit=get_settings().client_request.download_size_limit,
        connect_timeout=get_settings().client_request.connect_timeout,
        request_timeout=get_settings().client_request.request_timeout,
    ):
        self.download_size_limit = download_size_limit
        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout

        self.renderer = Renderer()

    def _build_curl_request(
        self,
        request: Request,
        http_headers: HTTPHeaders,
        proxy: Optional[Dict] = None,
        curl_encoding=get_settings().curl.curl_encoding,
        curl_content_length=get_settings().curl.curl_length,
    ):
        def set_curl_callback(curl):
            def size_limit(download_size, downloaded, upload_size, uploaded):  # pylint: disable=unused-argument
                if download_size and download_size > self.download_size_limit:
                    return 1
                if downloaded > self.download_size_limit:
                    return 1
                return 0

            if pycurl:
                if not curl_encoding:
                    try:
                        curl.unsetopt(pycurl.ENCODING)
                    except Exception as e:
                        logger.debug("unsetopt pycurl.ENCODING failed: %s", e)
                if not curl_content_length:
                    try:
                        if http_headers.get("content-length"):
                            http_headers.pop("content-length")
                            curl.setopt(
                                pycurl.HTTPHEADER,
                                [f"{native_str(k)}: {native_str(v)}" for k, v in http_headers.get_all()],
                            )
                    except Exception as e:
                        logger.debug("unsetopt pycurl.CONTENT_LENGTH failed: %s", e)
                if get_settings().curl.dns_server:
                    curl.setopt(pycurl.DNS_SERVERS, get_settings().curl.dns_server)
                curl.setopt(pycurl.NOPROGRESS, 0)
                curl.setopt(pycurl.PROGRESSFUNCTION, size_limit)
                curl.setopt(pycurl.CONNECTTIMEOUT, int(self.connect_timeout))
                curl.setopt(pycurl.TIMEOUT, int(self.request_timeout))
                if proxy:
                    if proxy.get("scheme", "") == "socks5":
                        curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
                    elif proxy.get("scheme", "") == "socks5h":
                        curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5_HOSTNAME)
            return curl

        req = httpclient.HTTPRequest(
            url=request.url,
            method=request.method,
            headers=http_headers,
            body=request.data,
            follow_redirects=False,
            max_redirects=0,
            decompress_response=True,
            allow_nonstandard_methods=True,
            allow_ipv6=True,
            prepare_curl_callback=set_curl_callback,
            validate_cert=False,
            connect_timeout=self.connect_timeout,
            request_timeout=self.request_timeout,
        )

        if proxy and pycurl:
            if not get_settings().proxy.proxy_direct_mode:
                for key in proxy:
                    if key != "scheme":
                        setattr(req, f"proxy_{key}", proxy[key])
            elif get_settings().proxy.proxy_direct_mode == "regexp":
                for proxy_direct in get_settings().proxy.proxy_direct:
                    if isinstance(proxy_direct, str):
                        proxy_direct = re.compile(proxy_direct)
                    if isinstance(proxy_direct, re.Pattern) and not proxy_direct.search(req.url):
                        for key in proxy:
                            if key != "scheme":
                                setattr(req, f"proxy_{key}", proxy[key])
            elif get_settings().proxy.proxy_direct_mode == "url":
                if urlmatch(req.url) not in get_settings().proxy.proxy_direct:
                    for key in proxy:
                        if key != "scheme":
                            setattr(req, f"proxy_{key}", proxy[key])
        return req

    def build(
        self,
        obj: HAR,
        proxy: Optional[Dict] = None,
        curl_encoding=get_settings().curl.curl_encoding,
        curl_content_length=get_settings().curl.curl_length,
    ):
        if proxy is None:
            proxy = {}
        env = obj.env
        rule = obj.rule
        request = self.renderer.render(obj.request, env)

        headers = HTTPHeaders(dict((e.name, e.value) for e in request.headers))
        cookies = dict((e.name, e.value) for e in request.cookies)

        if str(request.url).startswith("api://"):
            req = httpclient.HTTPRequest(
                url=request.url,
                method=request.method,
                headers=headers,
                body=request.data,
                follow_redirects=False,
                max_redirects=0,
                decompress_response=True,
                allow_nonstandard_methods=True,
                allow_ipv6=True,
                prepare_curl_callback=None,
                validate_cert=False,
                # connect_timeout=connect_timeout,
                # request_timeout=request_timeout
            )
        else:
            req = self._build_curl_request(request, headers, proxy, curl_encoding, curl_content_length)

        session = cookie_utils.CookieSession()
        if req.headers.get("cookie"):
            req.headers["Cookie"] = req.headers.pop("cookie")
        if req.headers.get("Cookie"):
            session.update(dict(x.strip().split("=", 1) for x in req.headers["Cookie"].split(";") if "=" in x))
        if isinstance(env.session, cookie_utils.CookieSession):
            session.from_json(env.session.to_json())
        else:
            session.from_json(env.session)
        session.update(cookies)
        cookie_header = session.get_cookie_header(req)
        if cookie_header:
            req.headers["Cookie"] = cookie_header

        env.session = session

        return req, rule, env
