#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2012-09-12 22:39:57
# form requests&tornado

import http.cookiejar as cookielib
import time
from http.cookiejar import _warn_unhandled_exception  # type:ignore
from http.cookiejar import parse_ns_headers  # type:ignore
from http.cookiejar import split_header_words  # type:ignore

from requests.cookies import (MockRequest, MockResponse, RequestsCookieJar,
                              get_cookie_header)
from tornado import httpclient

import config
from libs.log import Log

logger_CookieJar = Log('QD.Http.CookieJar').getlogger()


def _debug(*args):
    if not config.debug:
        return None
    return logger_CookieJar.debug(*args, stacklevel=2)


setattr(cookielib, '_debug', _debug)


def dump_cookie(cookie: cookielib.Cookie):
    result = {}
    for key in ('name', 'value', 'expires', 'secure', 'port', 'domain', 'path',
                'discard', 'comment', 'comment_url', 'rfc2109'):
        result[key] = getattr(cookie, key)
    result['rest'] = cookie._rest  # type: ignore # pylint:disable=protected-access
    return result


class CookieSession(RequestsCookieJar):
    def extract_cookies_to_jar(self,
                               request: httpclient.HTTPRequest,
                               response: httpclient.HTTPResponse):
        """Extract the cookies from the response into a CookieJar.

        :param jar: cookielib.CookieJar (not necessarily a RequestsCookieJar)
        :param request: our own requests.Request object
        :param response: tornado.httpclient.HTTPResponse object
        """
        # if not (hasattr(response, '_original_response') and
        #         response._original_response):
        #     return
        # the _original_response field is the wrapped httplib.HTTPResponse object,
        req = MockRequest(request)
        # pull out the HTTPMessage with the headers and put it in the mock:
        # res = MockResponse(response._original_response.msg)
        headers = response
        if not hasattr(headers, "keys"):
            headers = headers.headers
        headers.getheaders = headers.get_list
        res = MockResponse(headers)
        self.extract_cookies(res, req)

    def make_cookies(self, response, request):
        """Return sequence of Cookie objects extracted from response object."""
        # get cookie-attributes for RFC 2965 and Netscape protocols
        headers = response.info()
        rfc2965_hdrs = headers.get_list("Set-Cookie2")
        ns_hdrs = headers.get_list("Set-Cookie")
        self._policy._now = self._now = int(time.time())

        rfc2965 = self._policy.rfc2965
        netscape = self._policy.netscape

        if ((not rfc2965_hdrs and not ns_hdrs)
            or (not ns_hdrs and not rfc2965)
            or (not rfc2965_hdrs and not netscape)
                or (not netscape and not rfc2965)):
            return []  # no relevant cookie headers: quick exit

        try:
            cookies = self._cookies_from_attrs_set(
                split_header_words(rfc2965_hdrs), request)
        except Exception:
            _warn_unhandled_exception()
            cookies = []

        if ns_hdrs and netscape:
            try:
                # RFC 2109 and Netscape cookies
                ns_cookies = self._cookies_from_attrs_set(
                    parse_ns_headers(ns_hdrs), request)
            except Exception:
                _warn_unhandled_exception()
                ns_cookies = []
            self._process_rfc2109_cookies(ns_cookies)

            # Look for Netscape cookies (from Set-Cookie headers) that match
            # corresponding RFC 2965 cookies (from Set-Cookie2 headers).
            # For each match, keep the RFC 2965 cookie and ignore the Netscape
            # cookie (RFC 2965 section 9.1).  Actually, RFC 2109 cookies are
            # bundled in with the Netscape cookies for this purpose, which is
            # reasonable behaviour.
            if rfc2965:
                lookup = {}
                for cookie in cookies:
                    lookup[(cookie.domain, cookie.path, cookie.name)] = None

                def no_matching_rfc2965(ns_cookie, lookup=lookup):
                    key = ns_cookie.domain, ns_cookie.path, ns_cookie.name
                    return key not in lookup
                ns_cookies = filter(no_matching_rfc2965, ns_cookies)

            if ns_cookies:
                cookies.extend(ns_cookies)

        return cookies

    def from_json(self, data):
        for cookie in data:
            self.set(**cookie)

    def to_json(self):
        result = []
        for cookie in cookielib.CookieJar.__iter__(self):
            result.append(dump_cookie(cookie))
        return result

    def __getitem__(self, name):
        if isinstance(name, cookielib.Cookie):
            return name.value
        for cookie in cookielib.CookieJar.__iter__(self):
            if cookie.name == name:
                return cookie.value
        raise KeyError(name)

    def to_dict(self):
        result = {}
        for key in self.keys():
            result[key] = self.get(key)
        return result

    def get_cookie_header(self, req):
        return get_cookie_header(self, req)
