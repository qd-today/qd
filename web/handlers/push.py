#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 21:34:01

import json
import time
from urllib.parse import urlparse
from datetime import datetime

from .base import *

class PushListHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, status=None):
        user = self.current_user
        isadmin = user['isadmin']

        @utils.func_cache
        def get_user(userid):
            if not userid:
                return dict(
                        nickname = u'公开',
                        email = None,
                        email_verified = True,
                        )
            if isadmin:
                user = self.db.user.get(userid, fields=('id', 'nickname', 'email', 'email_verified'))
            else:
                user = self.db.user.get(userid, fields=('id', 'nickname'))
            if not user:
                return dict(
                        nickname = u'公开',
                        email = None,
                        email_verified = False,
                        )
            return user

        @utils.func_cache
        def get_tpl(tplid):
            if not tplid:
                return {}
            tpl = self.db.tpl.get(tplid, fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note', 'ctime', 'mtime', 'last_success'))
            return tpl or {}

        def join(pr):
            pr['from_user'] = get_user(pr['from_userid'])
            pr['to_user'] = get_user(pr['to_userid'])
            pr['from_tpl'] = get_tpl(pr['from_tplid'])
            pr['to_tpl'] = get_tpl(pr['to_tplid'])
            return pr

        pushs = []
        _f = {}
        if status is not None:
            _f['status'] = status
        for each in self.db.push_request.list(from_userid = user['id'], **_f):
            pushs.append(join(each))
        if isadmin:
            for each in self.db.push_request.list(from_userid = None, **_f):
                pushs.append(join(each))

        pulls = []
        for each in self.db.push_request.list(to_userid = user['id'], **_f):
            pulls.append(join(each))
        if isadmin:
            for each in self.db.push_request.list(to_userid = None, **_f):
                pulls.append(join(each))

        self.render('push_list.html', pushs=pushs, pulls=pulls)

class PushActionHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, prid, action):
        user = self.current_user
        pr = self.db.push_request.get(prid)
        if not pr:
            raise HTTPError(404)

        if pr['status'] != self.db.push_request.PENDING:
            raise HTTPError(400)

        if action in ('accept', 'refuse'):
            while True:
                if pr['to_userid'] == user['id']:
                    break
                if not pr['to_userid'] and user['isadmin']:
                    break
                self.evil(+5)
                raise HTTPError(401)
        elif action in ('cancel', ):
            while True:
                if pr['from_userid'] == user['id']:
                    break
                if not pr['from_userid'] and user['isadmin']:
                    break
                self.evil(+5)
                raise HTTPError(401)

        getattr(self, action)(pr)

        tpl_lock = len(list(self.db.push_request.list(from_tplid=pr['from_tplid'],
            status=self.db.push_request.PENDING, fields='1')))
        if not tpl_lock:
            self.db.tpl.mod(pr['from_tplid'], lock=False)

        self.redirect('/pushs')

    def accept(self, pr):
        tplobj = self.db.tpl.get(pr['from_tplid'], fields=('id', 'userid', 'tpl', 'variables', 'sitename', 'siteurl', 'note', 'banner', 'interval'))
        if not tplobj:
            self.cancel(pr)
            raise HTTPError(404)

        # re-encrypt
        tpl = self.db.user.decrypt(pr['from_userid'], tplobj['tpl'])
        har = self.db.user.encrypt(pr['to_userid'], self.fetcher.tpl2har(tpl))
        tpl = self.db.user.encrypt(pr['to_userid'], tpl)

        if not pr['to_tplid']:
            tplid = self.db.tpl.add(
                    userid = pr['to_userid'],
                    har = har,
                    tpl = tpl,
                    variables = tplobj['variables'],
                    interval = tplobj['interval']
                    )
            self.db.tpl.mod(tplid,
                    sitename = tplobj['sitename'],
                    siteurl = tplobj['siteurl'],
                    banner = tplobj['banner'],
                    note = tplobj['note'],
                    fork = pr['from_tplid'],
                    )
        else:
            tplid = pr['to_tplid']
            self.db.tpl.mod(tplid,
                    har = har,
                    tpl = tpl,
                    variables = tplobj['variables'],
                    interval = tplobj['interval'],
                    sitename = tplobj['sitename'],
                    siteurl = tplobj['siteurl'],
                    banner = tplobj['banner'],
                    note = tplobj['note'],
                    fork = pr['from_tplid'],
                    mtime = time.time(),
                    )
        self.db.push_request.mod(pr['id'], status=self.db.push_request.ACCEPT)

    def cancel(self, pr):
        self.db.push_request.mod(pr['id'], status=self.db.push_request.CANCEL)

    def refuse(self, pr):
        self.db.push_request.mod(pr['id'], status=self.db.push_request.REFUSE)
        reject_message = self.get_argument('prompt', None)
        if reject_message:
            self.db.push_request.mod(pr['id'], msg=reject_message)

class PushViewHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, prid):
        return self.render('har/editor.html')

    @tornado.web.authenticated
    def post(self, prid):
        user = self.current_user
        pr = self.db.push_request.get(prid, fields=('id', 'from_tplid', 'from_userid', 'to_tplid', 'to_userid', 'status'))
        if not pr:
            self.evil(+1)
            raise HTTPError(404)
        if pr['status'] != self.db.push_request.PENDING:
            self.evil(+5)
            raise HTTPError(401)

        while True:
            if pr['to_userid'] == user['id']:
                break
            if pr['from_userid'] == user['id']:
                break
            if not pr['to_userid'] and user['isadmin']:
                break
            if not pr['from_userid'] and user['isadmin']:
                break
            self.evil(+5)
            raise HTTPError(401)

        tpl = self.db.tpl.get(pr['from_tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note', 'tpl', 'variables'))
        if not tpl:
            self.evil(+1)
            raise HTTPError(404)

        tpl['har'] = self.fetcher.tpl2har(
                self.db.user.decrypt(pr['from_userid'], tpl['tpl']))
        tpl['variables'] = json.loads(tpl['variables'])
        self.finish(dict(
            filename = tpl['sitename'] or '未命名模板',
            har = tpl['har'],
            env = dict((x, '') for x in tpl['variables']),
            setting = dict(
                sitename = tpl['sitename'],
                siteurl = tpl['siteurl'],
                banner = tpl['banner'],
                note = tpl['note'],
                ),
            readonly = True,
            ))

handlers = [
        ('/pushs/?(\d+)?', PushListHandler),
        ('/push/(\d+)/(cancel|accept|refuse)', PushActionHandler),
        ('/push/(\d+)/view', PushViewHandler),
        ]
