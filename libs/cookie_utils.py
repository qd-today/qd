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
from requests.cookies import MockRequest,create_cookie,remove_cookie_by_name

debug = False   # set to True to enable debugging via the logging module
logger = None
def _debug(*args):
    if not debug:
        return
    global logger
    if not logger:
        import logging
        logger = logging.getLogger("http.cookiejar")
    return logger.debug(*args)

def dump_cookie(cookie):
    result = {}
    for key in ('name', 'value', 'expires', 'secure', 'port', 'domain', 'path',
            'discard', 'comment', 'comment_url', 'rfc2109'):
        result[key] = getattr(cookie, key)
    result['rest'] = cookie._rest
    return result

class MockResponse(object):
    """Wraps a `tornado.httputil.HTTPHeaders` to mimic a `urllib.addinfourl`.
    ...what? Basically, expose the parsed HTTP headers from the server response
    the way `cookielib` expects to see them.
    """

    def __init__(self, headers):
        """Make a MockResponse for `cookielib` to read.
        :param headers: a httplib.HTTPMessage or analogous carrying the headers
        """
        self._headers = headers

    def info(self):
        return self._headers

    def getheaders(self, name):
        self._headers.get_list(name)

class CookieSession(cookielib.CookieJar, DictMixin):
    def extract_cookies_to_jar(self, request, response):
        """Extract the cookies from the response into a CookieJar.

        :param jar: cookielib.CookieJar (not necessarily a RequestsCookieJar)
        :param request: our own requests.Request object
        :param response: urllib3.HTTPResponse object
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

    def extract_cookies(self, response, request):
        """Extract cookies from response, where allowable given the request."""
        _debug("extract_cookies: %s", response.info())
        self._cookies_lock.acquire()
        try:
            for cookie in self.make_cookies(response, request):
                if self._policy.set_ok(cookie, request):
                    _debug(" setting cookie: %s", cookie)
                    self.set_cookie(cookie)
        finally:
            self._cookies_lock.release()

    def make_cookies(self, response, request):
        import time
        from http.cookiejar import split_header_words,_warn_unhandled_exception,parse_ns_headers
        """Return sequence of Cookie objects extracted from response object."""
        # get cookie-attributes for RFC 2965 and Netscape protocols
        headers = response.info()
        rfc2965_hdrs = headers.get_list("Set-Cookie2")
        ns_hdrs = headers.get_list("Set-Cookie")
        self._policy._now = self._now = int(time.time())

        rfc2965 = self._policy.rfc2965
        netscape = self._policy.netscape

        if ((not rfc2965_hdrs and not ns_hdrs) or
            (not ns_hdrs and not rfc2965) or
            (not rfc2965_hdrs and not netscape) or
            (not netscape and not rfc2965)):
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
