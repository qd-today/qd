#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-01 10:35:08
# pylint: disable=broad-exception-raised

import json
import re
import time
from io import BytesIO
from typing import Sequence

import tornado
from jinja2 import meta
from jinja2.nodes import Filter, Name
from tornado import httpclient

import config
from libs import json_typing, utils
from libs.fetcher import Fetcher
from libs.parse_url import parse_url
from libs.safe_eval import safe_eval
from web.handlers.base import BaseHandler, logger_web_handler


class HAREditor(BaseHandler):
    async def get(self, id=None):
        tplurl = self.get_argument("tplurl", "|").split("|")
        harname = self.get_argument("name", tplurl[0])
        reponame = self.get_argument("reponame", tplurl[1])

        if (reponame != '') and (harname != ''):
            tpl = await self.db.pubtpl.list(filename=harname,
                                            reponame=reponame,
                                            fields=('id', 'name', 'content', 'comments'))
            if len(tpl) > 0:
                hardata = tpl[0]['content']
                harnote = tpl[0]['comments']
            else:
                await self.render('tpl_run_failed.html', log='此模板不存在')
                return
        else:
            hardata = ''
            harnote = ''

        return await self.render('har/editor.html', tplid=id, harpath=reponame, harname=harname, hardata=hardata, harnote=harnote)

    async def post(self, id):
        user = self.current_user
        taskid = self.get_query_argument('taskid', '')

        async with self.db.transaction() as sql_session:
            tpl = self.check_permission(
                await self.db.tpl.get(id, fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note', 'interval', 'har', 'variables', 'lock', 'init_env'), sql_session=sql_session))

            tpl['har'] = await self.db.user.decrypt(tpl['userid'], tpl['har'], sql_session=sql_session)
            tpl['variables'] = json.loads(tpl['variables'])
            if not tpl['init_env']:
                tpl['init_env'] = '{}'
            envs = json.loads(tpl['init_env'])
            if taskid:
                task = await self.db.task.get(taskid, sql_session=sql_session)
                if task['init_env']:
                    task_envs = await self.db.user.decrypt(user['id'], task['init_env'], sql_session=sql_session)
                    envs.update(task_envs)

            # await self.db.tpl.mod(id, atime=time.time(), sql_session=sql_session)
        await self.finish(dict(
            filename=tpl['sitename'] or '未命名模板',
            har=tpl['har'],
            env=dict((x, envs[x] if x in envs else '') for x in tpl['variables']),
            setting=dict(
                sitename=tpl['sitename'],
                siteurl=tpl['siteurl'],
                note=tpl['note'],
                banner=tpl['banner'],
                interval=tpl['interval'] or '',
            ),
            readonly=not tpl['userid'] or not self.permission(tpl, 'w') or tpl['lock'],
        ))


class HARTest(BaseHandler):
    async def post(self) -> None:
        self.evil(+1)
        try:
            if 'json' in self.request.headers['Content-Type']:
                self.request.body = self.request.body.replace(b'\xc2\xa0', b' ')
        except Exception as e:
            logger_web_handler.debug('HARTest Replace error: %s', e)
        data: json_typing.HARTest = json.loads(self.request.body)
        FOR_START = re.compile(r'{%\s*for\s+(\w+)\s+in\s+(\w+|list\([\s\S]*\)|range\([\s\S]*\))\s*%}').match(data['request']['url'])  # pylint: disable=invalid-name
        WHILE_START = re.compile(r'{%\s*while\s+([\s\S]*)\s*%}').match(data['request']['url'])  # pylint: disable=invalid-name
        IF_START = re.compile(r'{%\s*if\s+(.+)\s*%}').match(data['request']['url'])  # pylint: disable=invalid-name
        ELSE_START = re.compile(r'{%\s*else\s*%}').match(data['request']['url'])  # pylint: disable=invalid-name
        PARSE_END = re.compile(r'{%\s*end(for|if)\s*%}').match(data['request']['url'])  # pylint: disable=invalid-name
        if FOR_START or WHILE_START or IF_START or ELSE_START or PARSE_END:
            tmp = {'env': data['env'], 'rule': data['rule']}
            tmp['request'] = {'method': 'GET', 'url': 'api://util/unicode?content=', 'headers': [], 'cookies': []}  # type: ignore
            req, rule, env = self.fetcher.build_request(tmp)
            if FOR_START:
                _target = FOR_START.group(1)
                _from_var = FOR_START.group(2)
                _from = env['variables'].get(_from_var, [])
                try:
                    if _from_var.startswith(('list(', 'range(')):
                        _from = safe_eval(_from_var, env['variables'])
                    if not isinstance(_from, Sequence):
                        raise Exception('for 循环只支持可迭代类型及变量')
                    env['variables']['loop_index0'] = str(env['variables'].get('loop_index0', 0))
                    env['variables']['loop_index'] = str(env['variables'].get('loop_index', 1))
                    env['variables']['loop_first'] = str(env['variables'].get('loop_first', True))
                    env['variables']['loop_last'] = str(env['variables'].get('loop_last', False))
                    env['variables']['loop_length'] = str(env['variables'].get('loop_length', len(_from)))
                    env['variables']['loop_revindex0'] = str(env['variables'].get('loop_revindex0', len(_from) - 1))
                    env['variables']['loop_revindex'] = str(env['variables'].get('loop_revindex', len(_from)))
                    res = f'循环内赋值变量: {_target}, 循环列表变量: {_from_var}, 循环次数: {len(_from)}, \r\n循环列表内容: {list(_from)}.'
                    code = 200
                except NameError as e:
                    logger_web_handler.debug('for 循环变量错误: %s', e, exc_info=config.traceback_print)
                    res = f'循环变量错误: {e}'
                    code = 500
                except ValueError as e:
                    code = 500
                    if str(e).startswith("<class 'NameError'>:"):
                        e_str = str(e).replace("<class 'NameError'>", "NameError")
                        logger_web_handler.debug('for 循环变量错误: %s', e_str, exc_info=config.traceback_print)
                        res = f'循环变量错误: {e_str}'
                    else:
                        e_str = str(e).replace("<class 'ValueError'>", "ValueError")
                        logger_web_handler.debug('for 循环错误: %s', e_str, exc_info=config.traceback_print)
                        res = f'for 循环错误: {e_str}'
                except Exception as e:
                    logger_web_handler.debug('for 循环错误: %s', e, exc_info=config.traceback_print)
                    res = f'for 循环错误: {e}'
                    code = 500
                res += '\r\n此页面仅用于显示循环信息, 禁止在此页面提取变量'
                response = httpclient.HTTPResponse(request=req, code=code, buffer=BytesIO(str(res).encode()))
            elif WHILE_START:
                try:
                    env['variables']['loop_index0'] = str(env['variables'].get('loop_index0', 0))
                    env['variables']['loop_index'] = str(env['variables'].get('loop_index', 1))
                    condition = safe_eval(WHILE_START.group(1), env['variables'])
                    condition = 'while 循环判断结果: true' if condition else 'while 循环判断结果: false'
                    code = 200
                except NameError as e:
                    logger_web_handler.debug('while 循环判断结果: false, error: %s', e, exc_info=config.traceback_print)
                    condition = 'while 循环判断结果: false'
                    code = 200
                except ValueError as e:
                    if len(str(e)) > 20 and str(e)[:20] == "<class 'NameError'>:":
                        logger_web_handler.debug('while 循环判断结果: false, error: %s', e, exc_info=config.traceback_print)
                        condition = 'while 循环判断结果: false'
                        code = 200
                    else:
                        logger_web_handler.debug('while 循环条件错误: %s, 条件表达式: %s', e, WHILE_START.group(1), exc_info=config.traceback_print)
                        e_str = str(e).replace("<class 'ValueError'>", "ValueError")
                        condition = f'while 循环条件错误: {e_str}\r\n条件表达式: {WHILE_START.group(1)}'
                        code = 500
                except Exception as e:
                    logger_web_handler.debug('while 循环条件错误: %s, 条件表达式: %s', e, WHILE_START.group(1), exc_info=config.traceback_print)
                    condition = f'while 循环条件错误: {e}\r\n条件表达式: {WHILE_START.group(1)}'
                    code = 500
                condition += '\r\n此页面仅用于显示循环判断结果, 禁止在此页面提取变量'
                response = httpclient.HTTPResponse(request=req, code=code, buffer=BytesIO(str(condition).encode()))
            elif IF_START:
                try:
                    condition = safe_eval(IF_START.group(1), env['variables'])
                    condition = '判断结果: true' if condition else '判断结果: false'
                    code = 200
                except NameError as e:
                    logger_web_handler.debug('判断结果: false, error: %s', e, exc_info=config.traceback_print)
                    condition = False
                except ValueError as e:
                    if len(str(e)) > 20 and str(e)[:20] == "<class 'NameError'>:":
                        logger_web_handler.debug('判断结果: false, error: %s', e, exc_info=config.traceback_print)
                        condition = False
                    else:
                        logger_web_handler.debug('判断条件错误: %s, 条件表达式: %s', e, IF_START.group(1), exc_info=config.traceback_print)
                        e_str = str(e).replace("<class 'ValueError'>", "ValueError")
                        condition = f'判断条件错误: {e_str}\r\n条件表达式: {IF_START.group(1)}'
                        code = 500
                except Exception as e:
                    logger_web_handler.debug('判断条件错误: %s, 条件表达式: %s', e, IF_START.group(1), exc_info=config.traceback_print)
                    condition = f'判断条件错误: {e}\r\n条件表达式: {IF_START.group(1)}'
                    code = 500
                condition += '\r\n此页面仅用于显示判断结果, 禁止在此页面提取变量'
                response = httpclient.HTTPResponse(request=req, code=code, buffer=BytesIO(str(condition).encode()))
            else:
                exc = httpclient.HTTPError(405, "结束等控制语句不支持在单条请求中测试")  # type: ignore
                response = httpclient.HTTPResponse(request=req, code=exc.code, reason=exc.message, buffer=BytesIO(str(exc).encode()))
            env['session'].extract_cookies_to_jar(response.request, response)
            success, _ = self.fetcher.run_rule(response, rule, env)
            result = {
                'success': success,
                'har': self.fetcher.response2har(response),
                'env': {
                    'variables': env['variables'],
                    'session': env['session'].to_json(),
                }
            }
        else:
            _proxy = parse_url(data['env']['variables'].get('_proxy', ''))
            if _proxy:
                proxy = {
                    'scheme': _proxy['scheme'],
                    'host': _proxy['host'],
                    'port': _proxy['port'],
                    'username': _proxy['username'],
                    'password': _proxy['password']
                }
                ret = await self.fetcher.fetch(data, proxy=proxy)
            else:
                ret = await self.fetcher.fetch(data)

            result = {
                'success': ret['success'],
                'har': self.fetcher.response2har(ret['response']),
                'env': {
                    'variables': ret['env']['variables'],
                    'session': ret['env']['session'].to_json(),
                }
            }

        await self.finish(result)


class HARSave(BaseHandler):
    env = Fetcher().jinja_env

    @staticmethod
    def get_variables(env, tpl):
        variables = set()
        extracted = set(utils.jinja_globals.keys())
        loop_extracted = set(('loop_index0', 'loop_index', 'loop_first', 'loop_last', 'loop_length', 'loop_revindex0', 'loop_revindex', 'loop_depth', 'loop_depth0'))
        for entry in tpl:
            req = entry['request']
            rule = entry['rule']
            var = set()

            def _get(obj, key):
                if not obj.get(key):
                    return
                try:
                    ast = env.parse(obj[key])
                except Exception as e:
                    logger_web_handler.debug("Parse %s from env failed: %s" , obj[key], e, exc_info=config.traceback_print)
                    return
                var.update(meta.find_undeclared_variables(ast))  # pylint: disable=cell-var-from-loop

            _get(req, 'method')
            _get(req, 'url')
            _get(req, 'data')
            for header in req['headers']:
                _get(header, 'name')
                _get(header, 'value')
            for cookie in req['cookies']:
                _get(cookie, 'name')
                _get(cookie, 'value')

            variables.update(var - extracted - loop_extracted)
            extracted.update(set(x['name'] for x in rule.get('extract_variables', [])))
        return variables

    @tornado.web.authenticated
    async def post(self, id):
        self.evil(+1)
        reponame = self.get_argument("reponame", "")
        harname = self.get_argument("name", "")
        userid = self.current_user['id']
        try:
            if 'json' in self.request.headers['Content-Type']:
                self.request.body = self.request.body.replace(b'\xc2\xa0', b' ')
        except Exception as e:
            logger_web_handler.debug('HARSave Replace error: %s', e, exc_info=config.traceback_print)
        data = json.loads(self.request.body)

        async with self.db.transaction() as sql_session:
            har = await self.db.user.encrypt(userid, data['har'], sql_session=sql_session)
            tpl = await self.db.user.encrypt(userid, data['tpl'], sql_session=sql_session)
            variables = list(self.get_variables(self.env, data['tpl']))
            init_env = {}
            try:
                ast = self.env.parse(data['tpl'])
                for x in ast.find_all(Filter):
                    if x.name == 'default' and isinstance(x.node, Name) and len(x.args) > 0 and x.node.name in variables and x.node.name not in init_env:
                        try:
                            init_env[x.node.name] = x.args[0].as_const()
                        except Exception as e:
                            logger_web_handler.debug('HARSave init_env error: %s', e, exc_info=config.traceback_print)
            except Exception as e:
                logger_web_handler.debug('HARSave ast error: %s', e, exc_info=config.traceback_print)
            variables = json.dumps(variables)
            init_env = json.dumps(init_env)
            group_name = 'None'
            if id:
                _tmp = self.check_permission(await self.db.tpl.get(id, fields=('id', 'userid', 'lock'), sql_session=sql_session), 'w')
                if not _tmp['userid']:
                    self.set_status(403)
                    await self.finish('公开模板不允许编辑')
                    return
                if _tmp['lock']:
                    self.set_status(403)
                    await self.finish('模板已锁定')
                    return

                await self.db.tpl.mod(id, har=har, tpl=tpl, variables=variables, init_env=init_env, sql_session=sql_session)
                group_name = (await self.db.tpl.get(id, fields=('_groups',), sql_session=sql_session))['_groups']
            else:
                try:
                    id = await self.db.tpl.add(userid, har, tpl, variables, init_env=init_env, sql_session=sql_session)
                except Exception as e:
                    if "max_allowed_packet" in str(e):
                        raise Exception('har大小超过MySQL max_allowed_packet 限制; \n' + str(e)) from e
                if not id:
                    raise Exception('create tpl error')

        setting = data.get('setting', {})
        await self.db.tpl.mod(id,
                              tplurl=f'{harname}|{reponame}',
                              sitename=setting.get('sitename'),
                              siteurl=setting.get('siteurl'),
                              note=setting.get('note'),
                              interval=setting.get('interval') or None,
                              mtime=time.time(),
                              updateable=0,
                              _groups=group_name,
                              sql_session=sql_session)
        await self.finish({
            'id': id
        })


handlers = [
    (r'/tpl/(\d+)/edit', HAREditor),
    (r'/tpl/(\d+)/save', HARSave),

    (r'/har/edit', HAREditor),
    (r'/har/save/?(\d+)?', HARSave),

    (r'/har/test', HARTest),
]
