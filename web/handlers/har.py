#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-01 10:35:08

import time
import json
import os

import umsgpack
from tornado import gen
from jinja2 import Environment, meta
from libs import utils

from .base import *

class HAREditor(BaseHandler):
    def get(self, id=None):
        reponame = self.get_argument("reponame", "")
        harname = self.get_argument("name", "")

        if (reponame != '') and (harname != ''):
            tpl = self.db.pubtpl.list(filename = harname, 
                                      reponame = reponame,
                                      fields=('id', 'name', 'content'))
            if (len(tpl) > 0):
                hardata = tpl[0]['content']
            else:
                self.render('tpl_run_failed.html', log=u'此模板不存在')
                return
        else:
            hardata = ''

        return self.render('har/editor.html', tplid=id, harpath=reponame, harname=harname, hardata=hardata)

    def post(self, id):
        user = self.current_user

        tpl = self.check_permission(
                self.db.tpl.get(id, fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note', 'interval',
                    'har', 'variables', 'lock')))

        tpl['har'] = self.db.user.decrypt(tpl['userid'], tpl['har'])
        tpl['variables'] = json.loads(tpl['variables'])

        #self.db.tpl.mod(id, atime=time.time())
        self.finish(dict(
            filename = tpl['sitename'] or '未命名模板',
            har = tpl['har'],
            env = dict((x, '') for x in tpl['variables']),
            setting = dict(
                sitename = tpl['sitename'],
                siteurl = tpl['siteurl'],
                note = tpl['note'],
                banner = tpl['banner'],
                interval = tpl['interval'] or '',
                ),
            readonly = not tpl['userid'] or not self.permission(tpl, 'w') or tpl['lock'],
            ))

class HARTest(BaseHandler):
    @gen.coroutine
    def post(self):
        self.evil(+1)
        try:
            if 'json' in self.request.headers['Content-Type']:
                self.request.body = self.request.body.replace(b'\xc2\xa0', b' ')
        except :
            pass
        data = json.loads(self.request.body)
        ret = yield self.fetcher.fetch(data)

        result = {
                'success': ret['success'],
                'har': self.fetcher.response2har(ret['response']),
                'env': {
                    'variables': ret['env']['variables'],
                    'session': ret['env']['session'].to_json(),
                    }
                }

        self.finish(result)

class HARSave(BaseHandler):
    @staticmethod
    def get_variables(tpl):
        variables = set()
        extracted = set(utils.jinja_globals.keys())
        env = Environment()
        for entry in tpl:
            req = entry['request']
            rule = entry['rule']
            var = set()

            def _get(obj, key):
                if not obj.get(key):
                    return
                try:
                    ast = env.parse(obj[key])
                except:
                    return
                var.update(meta.find_undeclared_variables(ast))

            _get(req, 'method')
            _get(req, 'url')
            _get(req, 'data')
            for header in req['headers']:
                _get(header, 'name')
                _get(header, 'value')
            for cookie in req['cookies']:
                _get(cookie, 'name')
                _get(cookie, 'value')

            variables.update(var - extracted)
            extracted.update(set(x['name'] for x in rule.get('extract_variables', [])))
        return variables

    @tornado.web.authenticated
    def post(self, id):
        self.evil(+1)
        reponame = self.get_argument("reponame", "")
        harname = self.get_argument("name", "")
        userid = self.current_user['id']
        try:
            if 'json' in self.request.headers['Content-Type']:
                self.request.body = self.request.body.replace(b'\xc2\xa0', b' ')
        except :
            pass
        data = json.loads(self.request.body)

        har = self.db.user.encrypt(userid, data['har'])
        tpl = self.db.user.encrypt(userid, data['tpl'])
        variables = json.dumps(list(self.get_variables(data['tpl'])))
        groupName = 'None'
        if id:
            _tmp = self.check_permission(self.db.tpl.get(id, fields=('id', 'userid', 'lock')), 'w')
            if not _tmp['userid']:
                self.set_status(403)
                self.finish(u'公开模板不允许编辑')
                return
            if _tmp['lock']:
                self.set_status(403)
                self.finish(u'模板已锁定')
                return

            self.db.tpl.mod(id, har=har, tpl=tpl, variables=variables)
            groupName = self.db.tpl.get(id, fields=('_groups'))['_groups']
        else:
            try:
                id = self.db.tpl.add(userid, har, tpl, variables)
            except Exception as e:
                if "max_allowed_packet" in str(e):
                    raise Exception('har大小超过MySQL max_allowed_packet 限制; \n'+str(e))
            if not id:
                raise Exception('create tpl error')

        setting = data.get('setting', {})
        self.db.tpl.mod(id,
                tplurl = '{0}|{1}'.format(harname, reponame),
                sitename=setting.get('sitename'),
                siteurl=setting.get('siteurl'),
                note=setting.get('note'),
                interval=setting.get('interval') or None,
                mtime=time.time(),
                updateable=0,
                _groups=groupName)
        self.finish({
            'id': id
            })

handlers = [
        (r'/tpl/(\d+)/edit', HAREditor),
        (r'/tpl/(\d+)/save', HARSave),

        (r'/har/edit', HAREditor),
        (r'/har/save/?(\d+)?', HARSave),

        (r'/har/test', HARTest),
        ]
