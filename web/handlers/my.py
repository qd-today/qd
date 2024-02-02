#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 21:06:02

import time

from tornado.web import addslash, authenticated

from web.handlers.base import BaseHandler


def my_status(task):
    if task['disabled']:
        return u'停止'
    if task['last_failed_count']:
        return u'已失败%d次，重试中...' % task['last_failed_count']
    if (task['last_failed'] or 0) > (task['last_success'] or 0):
        return u'失败'
    if task['success_count'] == 0 and task['failed_count'] == 0 and task['next'] and (task['next'] - time.time() < 60):
        return u'正在准备执行任务'
    return u'正常'


class MyHandler(BaseHandler):
    @addslash
    @authenticated
    async def get(self):
        user = self.current_user
        adminflg = False
        # 验证用户是否存在
        if (await self.db.user.get(user['id'], fields=('id',))):
            if (await self.db.user.get(user['id'], fields=('role',)))['role'] == 'admin':
                adminflg = True

            tpls = await self.db.tpl.list(userid=user['id'], fields=('id', 'siteurl', 'sitename', 'banner', 'note', 'disabled', 'lock', 'last_success', 'ctime', 'mtime', 'fork', '_groups', 'updateable', 'tplurl'), limit=None)

            tasks = await self.db.task.list(user['id'], fields=('id', 'tplid', 'note', 'disabled', 'last_success', 'success_count', 'failed_count', 'last_failed', 'next', 'last_failed_count', 'ctime', '_groups'), limit=None)
            for task in tasks:
                tpl = await self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note'))
                task['tpl'] = tpl

            _groups = []
            for task in tasks:
                if not isinstance(task['_groups'], str):
                    task['_groups'] = str(task['_groups'])
                temp = task['_groups']
                if (temp not in _groups):
                    _groups.append(temp)

            tplgroups = []
            for tpl in tpls:
                temp = tpl['_groups']
                if (temp not in tplgroups):
                    tplgroups.append(temp)

            await self.render('my.html', tpls=tpls, tasks=tasks, my_status=my_status, userid=user['id'], taskgroups=_groups, tplgroups=tplgroups, adminflg=adminflg)
        else:
            return self.redirect('/login')


class CheckUpdateHandler(BaseHandler):
    @addslash
    @authenticated
    async def get(self):
        user = self.current_user
        async with self.db.transaction() as sql_session:
            tpls = await self.db.tpl.list(userid=user['id'], fields=('id', 'mtime', 'tplurl'), limit=None, sql_session=sql_session)

            hjson = {}
            for h in await self.db.pubtpl.list(fields=('id', 'filename', 'reponame', 'date', 'update'), sql_session=sql_session):
                hjson[f'{h["filename"]}|{h["reponame"]}'] = h

            for tpl in tpls:
                if tpl["tplurl"] in hjson and hjson[tpl["tplurl"]]["update"] and tpl['mtime'] < time.mktime(time.strptime(hjson[tpl["tplurl"]]['date'], "%Y-%m-%d %H:%M:%S")):
                    await self.db.tpl.mod(tpl["id"], updateable=1, sql_session=sql_session)

        self.redirect('/my/')


handlers = [
    ('/my/?', MyHandler),
    ('/my/checkupdate/?', CheckUpdateHandler),
]
