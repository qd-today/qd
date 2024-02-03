#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-06 11:55:41
# pylint: disable=broad-exception-raised

import base64
import json
import random
import re
import time
import traceback
import urllib.parse as urlparse
from datetime import datetime
from io import BytesIO
from typing import Dict, Iterable, Tuple

from jinja2.sandbox import SandboxedEnvironment as Environment
from tornado import httpclient, simple_httpclient
from tornado.escape import native_str
from tornado.httputil import HTTPHeaders

import config
from libs import cookie_utils, utils
from libs.log import Log
from libs.safe_eval import safe_eval

logger_fetcher = Log('QD.Http.Fetcher').getlogger()
if config.use_pycurl:
    try:
        import pycurl  # type: ignore
    except ImportError as e:
        if config.display_import_warning:
            logger_fetcher.warning('Import PyCurl module falied: \"%s\". \nTips: This warning message is only for prompting, it will not affect running of QD framework.', e)
        pycurl = None
else:
    pycurl = None  # pylint: disable=invalid-name
local_host = f'http://{config.bind}:{config.port}'.replace('0.0.0.0', 'localhost')
NOT_RETYR_CODE = config.not_retry_code


class Fetcher(object):
    def __init__(self, download_size_limit=config.download_size_limit):
        if pycurl:
            httpclient.AsyncHTTPClient.configure('tornado.curl_httpclient.CurlAsyncHTTPClient')
        self.client = httpclient.AsyncHTTPClient()
        self.download_size_limit = download_size_limit
        self.jinja_env = Environment()
        self.jinja_env.globals = utils.jinja_globals
        self.jinja_env.globals.update(utils.jinja_inner_globals)
        self.jinja_env.filters.update(utils.jinja_globals)

    def render(self, request, env, session=None):
        if session is None:
            session = []

        request = dict(request)
        if isinstance(session, cookie_utils.CookieSession):
            _cookies = session
        else:
            _cookies = cookie_utils.CookieSession()
            _cookies.from_json(session)

        def _render(obj, key):
            if not obj.get(key):
                return
            try:
                obj[key] = self.jinja_env.from_string(obj[key]).render(_cookies=_cookies, **env)
                return True
            except Exception as e:
                log_error = f'The error occurred when rendering template {key}: {obj[key]} \\r\\n {repr(e)}'
                raise httpclient.HTTPError(500, log_error)

        _render(request, 'method')
        _render(request, 'url')
        for header in request['headers']:
            _render(header, 'name')
            if pycurl and header['name'] and header['name'][0] == ":":
                header['name'] = header['name'][1:]
            _render(header, 'value')
            header['value'] = utils.quote_chinese(header['value'])
        for cookie in request['cookies']:
            _render(cookie, 'name')
            _render(cookie, 'value')
            cookie['value'] = utils.quote_chinese(cookie['value'])
        _render(request, 'data')
        return request

    def build_request(self, obj, download_size_limit=config.download_size_limit, connect_timeout=config.connect_timeout, request_timeout=config.request_timeout,
                      proxy=None, curl_encoding=True, curl_content_length=True):
        if proxy is None:
            proxy = {}
        env = obj['env']
        rule = obj['rule']
        request = self.render(obj['request'], env['variables'], env['session'])

        method = request['method']
        url = request['url']
        if str(url).startswith('api://'):
            url = str(url).replace('api:/', local_host, 1)

        headers = dict((e['name'], e['value']) for e in request['headers'])
        cookies = dict((e['name'], e['value']) for e in request['cookies'])
        data = request.get('data')
        if method == 'GET':
            data = None
        elif method == 'POST':
            data = request.get('data', '')

        def set_curl_callback(curl):
            def size_limit(download_size, downloaded, upload_size, uploaded):  # pylint: disable=unused-argument
                if download_size and download_size > download_size_limit:
                    return 1
                if downloaded > download_size_limit:
                    return 1
                return 0
            if pycurl:
                if not curl_encoding:
                    try:
                        curl.unsetopt(pycurl.ENCODING)
                    except Exception as e:
                        logger_fetcher.debug('unsetopt pycurl.ENCODING failed: %s', e)
                if not curl_content_length:
                    try:
                        if headers.get('content-length'):
                            headers.pop('content-length')
                            curl.setopt(
                                pycurl.HTTPHEADER, [
                                    f"{native_str(k)}: {native_str(v)}"
                                    for k, v in HTTPHeaders(headers).get_all()]
                            )
                    except Exception as e:
                        logger_fetcher.debug('unsetopt pycurl.CONTENT_LENGTH failed: %s', e)
                if config.dns_server:
                    curl.setopt(pycurl.DNS_SERVERS, config.dns_server)
                curl.setopt(pycurl.NOPROGRESS, 0)
                curl.setopt(pycurl.PROGRESSFUNCTION, size_limit)
                curl.setopt(pycurl.CONNECTTIMEOUT, int(connect_timeout))
                curl.setopt(pycurl.TIMEOUT, int(request_timeout))
                if proxy:
                    if proxy.get('scheme', '') == 'socks5':
                        curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
                    elif proxy.get('scheme', '') == 'socks5h':
                        curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5_HOSTNAME)
            return curl

        req = httpclient.HTTPRequest(
            url=url,
            method=method,
            headers=headers,
            body=data,
            follow_redirects=False,
            max_redirects=0,
            decompress_response=True,
            allow_nonstandard_methods=True,
            allow_ipv6=True,
            prepare_curl_callback=set_curl_callback,
            validate_cert=False,
            connect_timeout=connect_timeout,
            request_timeout=request_timeout
        )

        session = cookie_utils.CookieSession()
        if req.headers.get('cookie'):
            req.headers['Cookie'] = req.headers.pop("cookie")
        if req.headers.get('Cookie'):
            session.update(dict(x.strip().split('=', 1)
                                for x in req.headers['Cookie'].split(';')
                                if '=' in x))
        if isinstance(env['session'], cookie_utils.CookieSession):
            session.from_json(env['session'].to_json())
        else:
            session.from_json(env['session'])
        session.update(cookies)
        cookie_header = session.get_cookie_header(req)
        if cookie_header:
            req.headers['Cookie'] = cookie_header

        if proxy and pycurl:
            if not config.proxy_direct_mode:
                for key in proxy:
                    if key != 'scheme':
                        setattr(req, f'proxy_{key}', proxy[key])
            elif config.proxy_direct_mode == 'regexp':
                if not re.compile(config.proxy_direct).search(req.url):
                    for key in proxy:
                        if key != 'scheme':
                            setattr(req, f'proxy_{key}', proxy[key])
            elif config.proxy_direct_mode == 'url':
                if utils.urlmatch(req.url) not in config.proxy_direct.split('|'):
                    for key in proxy:
                        if key != 'scheme':
                            setattr(req, f'proxy_{key}', proxy[key])

        env['session'] = session

        return req, rule, env

    @staticmethod
    def response2har(response):
        request = response.request

        def build_headers(headers):
            result = []
            if headers and isinstance(headers, HTTPHeaders):
                for k, v in headers.get_all():
                    result.append(dict(name=k, value=v))
            return result

        def build_request(request):
            url = urlparse.urlparse(request.url)
            ret = dict(
                method=request.method,
                url=request.url,
                httpVersion='HTTP/1.1',
                headers=build_headers(request.headers),
                queryString=[
                    {'name': n, 'value': v} for n, v in
                    urlparse.parse_qsl(url.query)],
                cookies=[
                    {'name': n, 'value': v} for n, v in
                    urlparse.parse_qsl(request.headers.get('cookie', ''))],
                headersSize=-1,
                bodySize=len(request.body) if request.body else 0,
            )
            if request.body:
                if isinstance(request.body, bytes):
                    request._body = request.body.decode()  # pylint: disable=protected-access
                ret['postData'] = dict(
                    mimeType=request.headers.get('content-type'),
                    text=request.body,
                )
                if ret['postData']['mimeType'] and 'application/x-www-form-urlencoded' in ret['postData']['mimeType']:
                    ret['postData']['params'] = [
                        {'name': n, 'value': v} for n, v in
                        urlparse.parse_qsl(request.body)]
                    try:
                        _ = json.dumps(ret['postData']['params'])
                    except UnicodeDecodeError as e:
                        logger_fetcher.error('params encoding error: %s', e, exc_info=config.traceback_print)
                        del ret['postData']['params']

            return ret

        def build_response(response):
            cookies = cookie_utils.CookieSession()
            cookies.extract_cookies_to_jar(response.request, response)

            encoding = utils.find_encoding(response.body, response.headers)
            if not response.headers.get('content-type'):
                response.headers['content-type'] = 'text/plain'
            if 'charset=' not in response.headers.get('content-type', ''):
                response.headers['content-type'] += '; charset=' + encoding

            return dict(
                status=response.code,
                statusText=response.reason,
                headers=build_headers(response.headers),
                cookies=cookies.to_json(),
                content=dict(
                    size=len(response.body),
                    mimeType=response.headers.get('content-type'),
                    text=base64.b64encode(response.body).decode('ascii'),
                    decoded=utils.decode(response.body, response.headers),
                ),
                redirectURL=response.headers.get('Location'),
                headersSize=-1,
                bodySize=-1,
            )

        entry = dict(
            startedDateTime=datetime.now().isoformat(),
            time=response.request_time,
            request=build_request(request),
            response=build_response(response),
            cache={},
            timings=response.time_info,
            connections="0",
            pageref="page_0",
        )
        if response.body and 'image' in response.headers.get('content-type'):
            entry['response']['content']['decoded'] = base64.b64encode(response.body).decode('ascii')
        return entry

    def run_rule(self, response, rule, env):
        success = True
        msg = ''

        content = [-1, ]

        def getdata(_from):
            if _from == 'content':
                if content[0] == -1:
                    if response.headers and isinstance(response.headers, HTTPHeaders):
                        content[0] = utils.decode(response.body, headers=response.headers)
                    else:
                        content[0] = utils.decode(response.body)
                if 'content-type' in response.headers:
                    if 'image' in response.headers.get('content-type'):
                        return base64.b64encode(response.body).decode('utf8')
                return content[0]
            elif _from == 'status':
                return f'{response.code}'
            elif _from.startswith('header-'):
                _from = _from[7:]
                return response.headers.get(_from, '')
            elif _from == 'header':
                try:
                    if hasattr(response, 'headers') and isinstance(response.headers, HTTPHeaders):
                        return '\n'.join([f'{key}: {value}' for key, value in response.headers.get_all()])
                    return '\n'.join([f'{key}: {value}' for key, value in response.headers._dict.items()])  # pylint: disable=protected-access
                except Exception as e:
                    logger_fetcher.error('Run rule failed: %s', str(e), exc_info=config.traceback_print)
                try:
                    return json.dumps(response.headers._dict)  # pylint: disable=protected-access
                except Exception as e:
                    logger_fetcher.error('Run rule failed: %s', str(e), exc_info=config.traceback_print)
            else:
                return ''

        session = env['session']
        if isinstance(session, cookie_utils.CookieSession):
            _cookies = session
        else:
            _cookies = cookie_utils.CookieSession()
            _cookies.from_json(session)

        def _render(obj, key):
            if not obj.get(key):
                return
            try:
                obj[key] = self.jinja_env.from_string(obj[key]).render(_cookies=_cookies, **env['variables'])
                return True
            except Exception as e:
                log_error = f'The error occurred when rendering template {key}: {obj[key]} \\r\\n {repr(e)}'
                raise httpclient.HTTPError(500, log_error)

        for r in rule.get('success_asserts') or '':
            _render(r, 're')
            if r['re'] and re.search(r['re'], getdata(r['from'])):
                msg = ''
                break
            else:
                msg = f'Fail assert: {json.dumps(r, ensure_ascii=False)} from success_asserts'
        else:
            if rule.get('success_asserts'):
                success = False

        for r in rule.get('failed_asserts') or '':
            _render(r, 're')
            if r['re'] and re.search(r['re'], getdata(r['from'])):
                success = False
                msg = f'Fail assert: {json.dumps(r, ensure_ascii=False)} from failed_asserts'
                break

        if not success and msg and (response.error or (response.reason and str(response.reason) != 'OK')):
            msg += f', \\r\\nResponse Error : {response.error or response.reason}'

        for r in rule.get('extract_variables') or '':
            pattern = r['re']
            flags = 0
            find_all = False

            re_m = re.match(r"^/(.*?)/([gimsu]*)$", r['re'])
            if re_m:
                pattern = re_m.group(1)
                if 'g' in re_m.group(2):
                    find_all = True  # 全局匹配
                if 'i' in re_m.group(2):
                    flags |= re.I  # 使匹配对大小写不敏感
                if 'm' in re_m.group(2):
                    flags |= re.M  # 多行匹配，影响 ^ 和 $
                if 's' in re_m.group(2):
                    flags |= re.S  # 使 . 匹配包括换行在内的所有字符
                if 'u' in re_m.group(2):
                    flags |= re.U  # 根据Unicode字符集解析字符。这个标志影响 \w, \W, \b, \B.
                if 'x' in re_m.group(2):
                    pass  # flags |= re.X # 该标志通过给予你更灵活的格式以便你将正则表达式写得更易于理解。暂不启用

            if find_all:
                try:
                    env['variables'][r['name']] = re.compile(pattern, flags).findall(getdata(r['from']))
                except Exception as e:
                    env['variables'][r['name']] = str(e)
            else:
                try:
                    m = re.compile(pattern, flags).search(getdata(r['from']))
                    if m:
                        if m.groups():
                            m = m.groups()[0]
                        else:
                            m = m.group(0)
                        env['variables'][r['name']] = m
                except Exception as e:
                    env['variables'][r['name']] = str(e)
        return success, msg

    @staticmethod
    def tpl2har(tpl):
        def build_request(en):
            url = urlparse.urlparse(en['request']['url'])
            request = dict(
                method=en['request']['method'],
                url=en['request']['url'],
                httpVersion='HTTP/1.1',
                headers=[
                    {'name': x['name'], 'value': x['value'], 'checked': True} for x in
                    en['request'].get('headers', [])],
                queryString=[
                    {'name': n, 'value': v} for n, v in
                    urlparse.parse_qsl(url.query)],
                cookies=[
                    {'name': x['name'], 'value': x['value'], 'checked': True} for x in
                    en['request'].get('cookies', [])],
                headersSize=-1,
                bodySize=len(en['request'].get('data')) if en['request'].get('data') else 0,


            )
            if en['request'].get('data'):
                request['postData'] = dict(
                    mimeType=en['request'].get('mimeType'),
                    text=en['request'].get('data'),
                )
                if request['postData']['mimeType'] and 'application/x-www-form-urlencoded' in request['postData']['mimeType'] :
                    params = [{'name': x[0], 'value': x[1]}
                              for x in urlparse.parse_qsl(en['request']['data'], True)]
                    request['postData']['params'] = params
                    try:
                        _ = json.dumps(request['postData']['params'])
                    except UnicodeDecodeError as e:
                        logger_fetcher.error('params encoding error: %s', e, exc_info=config.traceback_print)
                        del request['postData']['params']
            return request

        entries = []
        for en in tpl:
            entry = dict(
                checked=True,
                startedDateTime=datetime.now().isoformat(),
                time=1,
                request=build_request(en),
                response={},
                cache={},
                timings={},
                connections="0",
                pageref="page_0",

                success_asserts=en.get('rule', {}).get('success_asserts', []),
                failed_asserts=en.get('rule', {}).get('failed_asserts', []),
                extract_variables=en.get('rule', {}).get('extract_variables', []),
            )
            entries.append(entry)
        return dict(
            log=dict(
                creator=dict(
                    name='binux',
                    version='QD'
                ),
                entries=entries,
                pages=[],
                version='1.2'
            )
        )

    async def build_response(self, obj, proxy=None, curl_encoding=config.curl_encoding, curl_content_length=config.curl_length, empty_retry=config.empty_retry):
        if proxy is None:
            proxy = {}
        try:
            req, rule, env = self.build_request(obj, download_size_limit=self.download_size_limit, proxy=proxy, curl_encoding=curl_encoding, curl_content_length=curl_content_length)
            response = await self.client.fetch(req)
            logger_fetcher.debug("%d %s %s %.2fms",
                                 response.code,
                                 response.request.method,
                                 response.request.url,
                                 1000.0 * response.request_time)
        except httpclient.HTTPError as e:
            try:
                if config.allow_retry and pycurl:
                    if e.__dict__.get('errno', '') == 61:
                        logger_fetcher.warning('%s %s [Warning] %s -> Try to retry!', req.method, req.url, e)
                        req, rule, env = self.build_request(obj, download_size_limit=self.download_size_limit, proxy=proxy, curl_encoding=False, curl_content_length=curl_content_length)
                        e.response = await self.client.fetch(req)
                    elif e.code == 400 and e.message == 'Bad Request' and req and req.headers.get('content-length'):
                        logger_fetcher.warning('%s %s [Warning] %s -> Try to retry!', req.method, req.url, e)
                        req, rule, env = self.build_request(obj, download_size_limit=self.download_size_limit, proxy=proxy, curl_encoding=curl_encoding, curl_content_length=False)
                        e.response = await self.client.fetch(req)
                    elif e.code not in NOT_RETYR_CODE or (empty_retry and not e.response):
                        try:
                            logger_fetcher.warning('%s %s [Warning] %s -> Try to retry!', req.method, req.url, e)
                            client = simple_httpclient.SimpleAsyncHTTPClient()
                            e.response = await client.fetch(req)
                        except Exception as e0:
                            logger_fetcher.error(e.message.replace('\\r\\n', '\r\n') or e.response.replace('\\r\\n', '\r\n') or e0, exc_info=config.traceback_print)
                    else:
                        try:
                            logger_fetcher.warning('%s %s [Warning] %s', req.method, req.url, e)
                        except Exception as e0:
                            logger_fetcher.error(e.message.replace('\\r\\n', '\r\n') or e.response.replace('\\r\\n', '\r\n') or e0, exc_info=config.traceback_print)
                else:
                    logger_fetcher.warning('%s %s [Warning] %s', req.method, req.url, e)
            finally:
                if 'req' not in locals().keys():
                    tmp = {'env': obj['env'], 'rule': obj['rule']}
                    tmp['request'] = {'method': 'GET', 'url': 'api://util/unicode?content=', 'headers': [], 'cookies': []}
                    req, rule, env = self.build_request(tmp)
                    e.response = httpclient.HTTPResponse(request=req, code=e.code, reason=e.message, buffer=BytesIO(str(e).encode()))
                if not e.response:
                    if config.traceback_print:
                        traceback.print_exc()
                    e.response = httpclient.HTTPResponse(request=req, code=e.code, reason=e.message, buffer=BytesIO(str(e).encode()))
                return rule, env, e.response  # TODO # pylint: disable=return-in-finally,lost-exception
        return rule, env, response

    async def fetch(self, obj, proxy=None, curl_encoding=config.curl_encoding, curl_content_length=config.curl_length, empty_retry=config.empty_retry):
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

        rule, env, response = await self.build_response(obj, proxy, curl_encoding, curl_content_length, empty_retry)

        env['session'].extract_cookies_to_jar(response.request, response)
        success, msg = self.run_rule(response, rule, env)

        return {
            'success': success,
            'response': response,
            'env': env,
            'msg': msg,
        }

    FOR_START = re.compile(r'{%\s*for\s+(\w+)\s+in\s+(\w+|list\([\s\S]*\)|range\([\s\S]*\))\s*%}')
    IF_START = re.compile(r'{%\s*if\s+(.+)\s*%}')
    WHILE_START = re.compile(r'{%\s*while\s+(.+)\s*%}')
    ELSE_START = re.compile(r'{%\s*else\s*%}')
    PARSE_END = re.compile(r'{%\s*end(for|if|while)\s*%}')

    def parse(self, tpl):
        stmt_stack = []

        def __append(entry):
            if stmt_stack[-1]['type'] == 'if':
                stmt_stack[-1][stmt_stack[-1]['parse']].append(entry)
            elif stmt_stack[-1]['type'] == 'for' or stmt_stack[-1]['type'] == 'while':
                stmt_stack[-1]['body'].append(entry)

        for i, entry in enumerate(tpl):
            if 'type' in entry:
                yield entry
            elif self.FOR_START.match(entry['request']['url']):
                m = self.FOR_START.match(entry['request']['url'])
                stmt_stack.append({
                    'type': 'for',
                    'target': m.group(1),
                    'from': m.group(2),
                    'body': [],
                    'idx': entry['idx'],
                })
            elif self.WHILE_START.match(entry['request']['url']):
                m = self.WHILE_START.match(entry['request']['url'])
                stmt_stack.append({
                    'type': 'while',
                    'condition': m.group(1),
                    'body': [],
                    'idx': entry['idx'],
                })
            elif self.IF_START.match(entry['request']['url']):
                m = self.IF_START.match(entry['request']['url'])
                stmt_stack.append({
                    'type': 'if',
                    'condition': m.group(1),
                    'parse': 'true',
                    'true': [],
                    'false': [],
                    'idx': entry['idx'],
                })
            elif self.ELSE_START.match(entry['request']['url']):
                stmt_stack[-1]['parse'] = 'false'
            elif self.PARSE_END.match(entry['request']['url']):
                m = self.PARSE_END.match(entry['request']['url'])
                entry_type = stmt_stack and stmt_stack[-1]['type']
                if entry_type == 'for' or entry_type == 'if' or entry_type == 'while':
                    if m.group(1) != entry_type:
                        raise Exception(f"Failed at {i+1}/{len(tpl)} end tag \\r\\nError: End tag should be \"end{stmt_stack[-1]['type']}\", but \"end{m.group(1)}\"")
                    entry = stmt_stack.pop()
                    if stmt_stack:
                        __append(entry)
                    else:
                        yield entry
            elif stmt_stack:
                __append({
                    'type': 'request',
                    'entry': entry,
                })
            else:
                yield {
                    'type': 'request',
                    'entry': entry,
                }

        while stmt_stack:
            yield stmt_stack.pop()

    async def do_fetch(self, tpl, env, proxies=config.proxies, request_limit=config.task_request_limit, tpl_length=0) -> Tuple[Dict, int]:
        """
        do a fetch of hole tpl
        """
        if proxies:
            proxy = random.choice(proxies)
        else:
            proxy = {}

        if tpl_length == 0 and len(tpl) > 0:
            tpl_length = len(tpl)
            for i, entry in enumerate(tpl):
                entry['idx'] = i + 1

        for i, block in enumerate(self.parse(tpl)):
            if request_limit <= 0:
                raise Exception('request limit')
            elif block['type'] == 'for':
                support_enum = False
                _from_var = block['from']
                _from = env['variables'].get(_from_var, [])
                try:
                    if isinstance(_from_var, str) and _from_var.startswith('list(') or _from_var.startswith('range('):
                        _from = safe_eval(_from_var, env['variables'])
                    if not isinstance(_from, Iterable):
                        raise Exception('for循环只支持可迭代类型及变量')
                    support_enum = True
                except Exception as e:
                    if config.debug:
                        logger_fetcher.exception(e)
                if support_enum:
                    env['variables']['loop_length'] = str(len(_from))
                    env['variables']['loop_depth'] = str(int(env['variables'].get('loop_depth', '0')) + 1)
                    env['variables']['loop_depth0'] = str(int(env['variables'].get('loop_depth0', '-1')) + 1)
                    for idx, each in enumerate(_from):
                        env['variables'][block['target']] = each
                        if idx == 0:
                            env['variables']['loop_first'] = 'True'
                            env['variables']['loop_last'] = 'False'
                        elif idx == len(_from) - 1:
                            env['variables']['loop_first'] = 'False'
                            env['variables']['loop_last'] = 'True'
                        else:
                            env['variables']['loop_first'] = 'False'
                            env['variables']['loop_last'] = 'False'
                        env['variables']['loop_index'] = str(idx + 1)
                        env['variables']['loop_index0'] = str(idx)
                        env['variables']['loop_revindex'] = str(len(_from) - idx)
                        env['variables']['loop_revindex0'] = str(len(_from) - idx - 1)
                        env, request_limit = await self.do_fetch(block['body'], env, proxies=[proxy], request_limit=request_limit, tpl_length=tpl_length)
                    env['variables']['loop_depth'] = str(int(env['variables'].get('loop_depth', '0')) - 1)
                    env['variables']['loop_depth0'] = str(int(env['variables'].get('loop_depth0', '-1')) - 1)
                else:
                    for each in _from:
                        env['variables'][block['target']] = each
                        env, request_limit = await self.do_fetch(block['body'], env, proxies=[proxy], request_limit=request_limit, tpl_length=tpl_length)
            elif block['type'] == 'while':
                start_time = time.perf_counter()
                env['variables']['loop_depth'] = str(int(env['variables'].get('loop_depth', '0')) + 1)
                env['variables']['loop_depth0'] = str(int(env['variables'].get('loop_depth0', '-1')) + 1)
                while_idx = 0
                while time.perf_counter() - start_time <= config.task_while_loop_timeout:
                    env['variables']['loop_index'] = str(while_idx + 1)
                    env['variables']['loop_index0'] = str(while_idx)
                    try:
                        condition = safe_eval(block['condition'], env['variables'])
                    except NameError:
                        condition = False
                    except ValueError as e:
                        if len(str(e)) > 20 and str(e)[:20] == "<class 'NameError'>:":
                            condition = False
                        else:
                            str_e = str(e).replace("<class 'ValueError'>", "ValueError")
                            raise Exception(f"Failed at {block['idx']}/{tpl_length} while condition, \\r\\nError: {str_e}, \\r\\nBlock condition: {block['condition']}") from e
                    except Exception as e:
                        raise Exception(f"Failed at {block['idx']}/{tpl_length} while condition, \\r\\nError: {e}, \\r\\nBlock condition: {block['condition']}") from e
                    if condition:
                        env, request_limit = await self.do_fetch(block['body'], env, proxies=[proxy], request_limit=request_limit, tpl_length=tpl_length)
                    else:
                        if config.debug:
                            logger_fetcher.debug('while loop break, time: %ss', time.perf_counter() - start_time)
                        break
                    while_idx += 1
                else:
                    raise Exception(f"Failed at {block['idx']}/{tpl_length} while end, \\r\\nError: while loop timeout, time: {time.perf_counter() - start_time}s \\r\\nBlock condition: {block['condition']}")
                env['variables']['loop_depth'] = str(int(env['variables'].get('loop_depth', '0')) - 1)
                env['variables']['loop_depth0'] = str(int(env['variables'].get('loop_depth0', '-1')) - 1)
            elif block['type'] == 'if':
                try:
                    condition = safe_eval(block['condition'], env['variables'])
                except NameError:
                    condition = False
                except ValueError as e:
                    if len(str(e)) > 20 and str(e)[:20] == "<class 'NameError'>:":
                        condition = False
                    else:
                        str_e = str(e).replace("<class 'ValueError'>", "ValueError")
                        raise Exception(f"Failed at {block['idx']}/{tpl_length} if condition, \\r\\nError: {str_e}, \\r\\nBlock condition: {block['condition']}") from e
                except Exception as e:
                    raise Exception(f"Failed at {block['idx']}/{tpl_length} if condition, \\r\\nError: {e}, \\r\\nBlock condition: {block['condition']}") from e
                if condition:
                    _, request_limit = await self.do_fetch(block['true'], env, proxies=[proxy], request_limit=request_limit, tpl_length=tpl_length)
                else:
                    _, request_limit = await self.do_fetch(block['false'], env, proxies=[proxy], request_limit=request_limit, tpl_length=tpl_length)
            elif block['type'] == 'request':
                entry = block['entry']
                try:
                    request_limit -= 1
                    result = await self.fetch(dict(
                        request=entry['request'],
                        rule=entry['rule'],
                        env=env,
                    ), proxy=proxy)
                    env = result['env']
                except Exception as e:
                    if config.debug:
                        logger_fetcher.exception(e)
                    raise Exception(f"Failed at {entry['idx']}/{tpl_length} request, \\r\\nError: {e}, \\r\\nRequest URL: {entry['request']['url']}") from e
                if not result['success']:
                    raise Exception(f"Failed at {entry['idx']}/{tpl_length} request, \\r\\n{result['msg']}, \\r\\nRequest URL: {entry['request']['url']}")
        return env, request_limit
