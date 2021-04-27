#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 17:52:49

import json
from tornado import gen
from base import *
from libs import utils

class TPLPushHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, tplid):
        user = self.current_user
        tpl = self.db.tpl.get(tplid, fields=('id', 'userid', 'sitename'))
        if not self.permission(tpl, 'w'):
            self.evil(+5)
            self.finish(u'<span class="alert alert-danger">没有权限</span>')
            return
        tpls = self.db.tpl.list(userid=None, limit=None, fields=('id', 'sitename'))
        self.render('tpl_push.html', tpl=tpl, tpls=tpls)

    @tornado.web.authenticated
    def post(self, tplid):
        user = self.current_user
        tplid = int(tplid)
        tpl = self.db.tpl.get(tplid, fields=('id', 'userid', ))
        if not self.permission(tpl, 'w'):
            self.evil(+5)
            self.finish(u'<span class="alert alert-danger">没有权限</span>')
            return

        to_tplid = int(self.get_argument('totpl'))
        msg = self.get_argument('msg')
        if to_tplid == 0:
            to_tplid = None
            to_userid = None
        else:
            totpl = self.db.tpl.get(to_tplid, fields=('id', 'userid', ))
            if not totpl:
                self.evil(+1)
                self.finish(u'<span class="alert alert-danger">模板不存在</span>')
                return
            to_userid = totpl['userid']

        self.db.push_request.add(from_tplid=tpl['id'], from_userid=user['id'],
                to_tplid=to_tplid, to_userid=to_userid, msg=msg)
        self.db.tpl.mod(tpl['id'], lock=True)

        #referer = self.request.headers.get('referer', '/my/')
        self.redirect('/pushs')

class TPLVarHandler(BaseHandler):
    def get(self, tplid):
        user = self.current_user
        tpl = self.db.tpl.get(tplid, fields=('id', 'note', 'userid', 'sitename', 'siteurl', 'variables'))
        if not self.permission(tpl):
            self.evil(+5)
            self.finish('<span class="alert alert-danger">没有权限</span>')
            return
        self.render('task_new_var.html', tpl=tpl, variables=json.loads(tpl['variables']))

class TPLDelHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, tplid):
        user = self.current_user
        tpl = self.check_permission(self.db.tpl.get(tplid, fields=('id', 'userid')), 'w')

        self.db.tpl.delete(tplid)
        referer = self.request.headers.get('referer', '/my/')
        self.redirect(referer)

class TPLRunHandler(BaseHandler):
    @gen.coroutine
    def post(self, tplid):
        self.evil(+5)
        user = self.current_user
        data = {}
        if 'json' in self.request.headers['Content-Type']:
            data = json.loads(self.request.body)

        tplid = tplid or data.get('tplid') or self.get_argument('_binux_tplid', None)
        tpl = dict()
        fetch_tpl = None
        if tplid:
            tpl = self.check_permission(self.db.tpl.get(tplid, fields=('id', 'userid', 'sitename',
                'siteurl', 'tpl', 'interval', 'last_success')))
            fetch_tpl = self.db.user.decrypt(tpl['userid'], tpl['tpl'])

        if not fetch_tpl:
            fetch_tpl = data.get('tpl')

        if not fetch_tpl:
            try:
                fetch_tpl = json.loads(self.get_argument('tpl'))
            except:
                raise HTTPError(400)

        env = data.get('env')
        if not env:
            try:
                env = dict(
                    variables = json.loads(self.get_argument('env')),
                    session = []
                    )
            except:
                raise HTTPError(400)

        try:
            url = utils.parse_url(env['variables'].get('_binux_proxy'))
            if url:
                proxy = {
                    'host': url['host'],
                    'port': url['port'],
                }
                result = yield self.fetcher.do_fetch(fetch_tpl, env, [proxy])
            elif self.current_user:
                result = yield self.fetcher.do_fetch(fetch_tpl, env)
            else:
                result = yield self.fetcher.do_fetch(fetch_tpl, env, proxies=[])
        except Exception as e:
            self.render('tpl_run_failed.html', log=e)
            return

        if tpl:
            self.db.tpl.incr_success(tpl['id'])
        self.render('tpl_run_success.html', log = result.get('variables', {}).get('__log__'))
        return

class PublicTPLHandler(BaseHandler):
    def get(self):
        tpls = self.db.tpl.list(userid=None, limit=None, fields=('id', 'siteurl', 'sitename', 'banner', 'note', 'disabled', 'lock', 'last_success', 'ctime', 'mtime', 'fork', 'success_count'))
        tpls = sorted(tpls, key=lambda t: -t['success_count'])

        self.render('tpls_public.html', tpls=tpls)

class TPLGroupHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, tplid):
        user = self.current_user      
        groupNow = self.db.tpl.get(tplid, fields=('groups'))['groups']
        tasks = []
        groups = []
        tpls = self.db.tpl.list(userid=user['id'], fields=('groups'), limit=None)
        for tpl in tpls:
            temp = tpl['groups']
            if (temp not  in groups):
                groups.append(temp)

        self.render('tpl_setgroup.html', tplid=tplid, groups=groups, groupNow=groupNow)
    
    @tornado.web.authenticated
    def post(self, tplid):        
        New_group = self.request.body_arguments['New_group'][0].strip()
        
        if New_group != "" :
            target_group = New_group.decode("utf-8").encode("utf-8")
        else:
            for value in self.request.body_arguments:
                if self.request.body_arguments[value][0] == 'on':
                    target_group = value.strip()
                    break
                else:
                    target_group = 'None'
            
        self.db.tpl.mod(tplid, groups=target_group)
   
        self.redirect('/my/')

handlers = [
        ('/tpl/(\d+)/push', TPLPushHandler),
        ('/tpl/(\d+)/var', TPLVarHandler),
        ('/tpl/(\d+)/del', TPLDelHandler),
        ('/tpl/?(\d+)?/run', TPLRunHandler),
        ('/tpls/public', PublicTPLHandler),
        ('/tpl/(\d+)/group', TPLGroupHandler),
        ]
