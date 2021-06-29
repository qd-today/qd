#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2012-09-12 22:39:57
# form requests&tornado

from collections import MutableMapping as DictMixin
import http.cookiejar as cookielib
from urllib.parse import urlparse
from tornado import httpclient, httputil
from requests.cookies import MockRequest,MockResponse,create_cookie,remove_cookie_by_name

def dump_cookie(cookie):
    result = {}
    for key in ('name', 'value', 'expires', 'secure', 'port', 'domain', 'path',
            'discard', 'comment', 'comment_url', 'rfc2109'):
        result[key] = getattr(cookie, key)
    result['rest'] = cookie._rest
    return result

class CookieSession(cookielib.CookieJar, DictMixin):
    def extract_cookies_to_jar(self, request, response):
        """Extract the cookies from the response into a CookieJar.

        :param jar: cookielib.CookieJar (not necessarily a RequestsCookieJar)
        :param request: our own requests.Request object
        :param response: urllib3.HTTPResponse object
        """
        if not (hasattr(response, '_original_response') and
                response._original_response):
            return
        # the _original_response field is the wrapped httplib.HTTPResponse object,
        req = MockRequest(request)
        # pull out the HTTPMessage with the headers and put it in the mock:
        res = MockResponse(response._original_response.msg)
        self.extract_cookies(res, req)

    def get_cookie_header(self, request):
        """Produce an appropriate Cookie header string to be sent with `request`, or None."""
        r = MockRequest(request)
        self.add_cookie_header(r)
        return r.get_new_headers().get('Cookie')

    def from_json(self, data):
        for cookie in data:
            self.set_cookie(create_cookie(**cookie))

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

    def __setitem__(self, name, value):
        if value is None:
            remove_cookie_by_name(self, name)
        else:
            self.set_cookie(create_cookie(name, value))

    def __delitem__(self, name):
        remove_cookie_by_name(self, name)

    def keys(self):
        result = []
        for cookie in cookielib.CookieJar.__iter__(self):
            result.append(cookie.name)
        return result

    def to_dict(self):
        result = {}
        for key in self.keys():
            result[key] = self.get(key)
        return result

class CookieTracker:
    def __init__(self):
        self.headers = httputil.HTTPHeaders()

    def get_header_callback(self):
        _self = self
        def header_callback(header):
            header = header.strip()
            if header.starswith("HTTP/"):
                return
            if not header:
                return
            _self.headers.parse_line(header)
        return header_callback
