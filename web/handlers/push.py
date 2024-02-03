#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 21:34:01

import json
import time

from tornado.web import HTTPError, authenticated

from web.handlers.base import BaseHandler


class PushListHandler(BaseHandler):
    @authenticated
    async def get(self, status=None):
        user = self.current_user
        isadmin = user['isadmin']

        async def get_user(userid):
            if not userid:
                return dict(
                    nickname='公开',
                    email=None,
                    email_verified=True,
                )
            if isadmin:
                user = await self.db.user.get(userid, fields=('id', 'nickname', 'email', 'email_verified'))
            else:
                user = await self.db.user.get(userid, fields=('id', 'nickname'))
            if not user:
                return dict(
                    nickname='公开',
                    email=None,
                    email_verified=False,
                )
            return user

        async def get_tpl(tplid):
            if not tplid:
                return {}
            tpl = await self.db.tpl.get(tplid, fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note', 'ctime', 'mtime', 'last_success'))
            return tpl or {}

        async def join(pr):
            pr['from_user'] = await get_user(pr['from_userid'])
            pr['to_user'] = await get_user(pr['to_userid'])
            pr['from_tpl'] = await get_tpl(pr['from_tplid'])
            pr['to_tpl'] = await get_tpl(pr['to_tplid'])
            return pr

        pushs = []
        _f = {}
        if status is not None:
            _f['status'] = status
        for each in await self.db.push_request.list(from_userid=user['id'], **_f):
            pushs.append(await join(each))
        if isadmin:
            for each in await self.db.push_request.list(from_userid=None, **_f):
                pushs.append(await join(each))

        pulls = []
        for each in await self.db.push_request.list(to_userid=user['id'], **_f):
            pulls.append(await join(each))
        if isadmin:
            for each in await self.db.push_request.list(to_userid=None, **_f):
                pulls.append(await join(each))

        await self.render('push_list.html', pushs=pushs, pulls=pulls)


class PushActionHandler(BaseHandler):
    @authenticated
    async def post(self, prid, action):
        user = self.current_user
        async with self.db.transaction() as sql_session:
            pr = await self.db.push_request.get(prid, sql_session=sql_session)
            if not pr:
                raise HTTPError(404)

            if pr['status'] != self.db.push_request.PENDING:
                if action != 'cancel':
                    raise HTTPError(400)

            if action in ('accept', 'refuse'):
                while True:
                    if pr['to_userid'] == user['id']:
                        break
                    if not pr['to_userid'] and user['isadmin']:
                        break
                    self.evil(+5)
                    raise HTTPError(401)
            elif action == 'cancel':
                while True:
                    if pr['from_userid'] == user['id']:
                        break
                    if not pr['from_userid'] and user['isadmin']:
                        break
                    self.evil(+5)
                    raise HTTPError(401)

            await getattr(self, action)(pr, sql_session=sql_session)

            if action == 'cancel':
                status = self.db.push_request.CANCEL
            elif pr['status'] == self.db.push_request.PENDING:
                if action == 'refuse':
                    status = self.db.push_request.REFUSE
                elif action == 'accept':
                    status = self.db.push_request.ACCEPT
                else:
                    status = self.db.push_request.PENDING
            tpl_lock = len(list(await self.db.push_request.list(from_tplid=pr['from_tplid'],
                                                                status=status, sql_session=sql_session))) == 0
            if not tpl_lock:
                await self.db.tpl.mod(pr['from_tplid'], lock=False, sql_session=sql_session)

        self.redirect('/pushs')

    async def accept(self, pr, sql_session=None):
        tplobj = await self.db.tpl.get(pr['from_tplid'], fields=('id', 'userid', 'tpl', 'variables', 'sitename', 'siteurl', 'note', 'banner', 'interval', 'init_env'), sql_session=sql_session)
        if not tplobj:
            self.cancel(pr)
            raise HTTPError(404)

        # re-encrypt
        tpl = await self.db.user.decrypt(pr['from_userid'], tplobj['tpl'], sql_session=sql_session)
        har = await self.db.user.encrypt(pr['to_userid'], self.fetcher.tpl2har(tpl), sql_session=sql_session)
        tpl = await self.db.user.encrypt(pr['to_userid'], tpl, sql_session=sql_session)
        tplid = None

        if not pr['to_tplid']:
            tplid = await self.db.tpl.add(
                userid=pr['to_userid'],
                har=har,
                tpl=tpl,
                variables=tplobj['variables'],
                init_env=tplobj['init_env'],
                interval=tplobj['interval'],
                sql_session=sql_session
            )
            await self.db.tpl.mod(tplid,
                                  public=1,
                                  sitename=tplobj['sitename'],
                                  siteurl=tplobj['siteurl'],
                                  banner=tplobj['banner'],
                                  note=tplobj['note'],
                                  fork=pr['from_tplid'],
                                  sql_session=sql_session
                                  )
        else:
            tplid = pr['to_tplid']
            await self.db.tpl.mod(tplid,
                                  har=har,
                                  tpl=tpl,
                                  public=1,
                                  variables=tplobj['variables'],
                                  init_env=tplobj['init_env'],
                                  interval=tplobj['interval'],
                                  sitename=tplobj['sitename'],
                                  siteurl=tplobj['siteurl'],
                                  banner=tplobj['banner'],
                                  note=tplobj['note'],
                                  fork=pr['from_tplid'],
                                  mtime=time.time(),
                                  sql_session=sql_session
                                  )
        if tplid:
            await self.db.push_request.mod(pr['id'], to_tplid=tplid, status=self.db.push_request.ACCEPT, sql_session=sql_session)
        else:
            await self.db.push_request.mod(pr['id'], status=self.db.push_request.ACCEPT, sql_session=sql_session)

    async def cancel(self, pr, sql_session=None):
        if pr['to_tplid'] and pr['status'] == self.db.push_request.ACCEPT:
            await self.db.tpl.mod(pr['to_tplid'], public=2, sql_session=sql_session)
        await self.db.push_request.mod(pr['id'], status=self.db.push_request.CANCEL, sql_session=sql_session)

    async def refuse(self, pr, sql_session=None):
        await self.db.push_request.mod(pr['id'], status=self.db.push_request.REFUSE, sql_session=sql_session)
        reject_message = self.get_argument('prompt', None)
        if reject_message:
            await self.db.push_request.mod(pr['id'], msg=reject_message, sql_session=sql_session)


class PushViewHandler(BaseHandler):
    @authenticated
    async def get(self, prid):  # pylint: disable=unused-argument
        return await self.render('har/editor.html')

    @authenticated
    async def post(self, prid):
        user = self.current_user
        pr = await self.db.push_request.get(prid, fields=('id', 'from_tplid', 'from_userid', 'to_tplid', 'to_userid', 'status'))
        if not pr:
            self.evil(+1)
            raise HTTPError(404)
        if pr['status'] not in (self.db.push_request.PENDING, self.db.push_request.ACCEPT):
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

        tplid = None
        userid = None
        if pr['to_tplid'] and pr['status'] != self.db.push_request.PENDING:
            tplid = pr['to_tplid']
            userid = pr['to_userid']
        else:
            tplid = pr['from_tplid']
            userid = pr['from_userid']
        tpl = await self.db.tpl.get(tplid, fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note', 'tpl', 'variables'))
        if not tpl:
            self.evil(+1)
            raise HTTPError(404)

        tpl['har'] = self.fetcher.tpl2har(
            await self.db.user.decrypt(userid, tpl['tpl']))
        tpl['variables'] = json.loads(tpl['variables'])
        await self.finish(dict(
            filename=tpl['sitename'] or '未命名模板',
            har=tpl['har'],
            env=dict((x, '') for x in tpl['variables']),
            setting=dict(
                sitename=tpl['sitename'],
                siteurl=tpl['siteurl'],
                banner=tpl['banner'],
                note=tpl['note'],
            ),
            readonly=True,
        ))


handlers = [
    (r'/pushs/?(\d+)?', PushListHandler),
    (r'/push/(\d+)/(cancel|accept|refuse)', PushActionHandler),
    (r'/push/(\d+)/view', PushViewHandler),
]
