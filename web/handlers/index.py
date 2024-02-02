#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-07-30 16:02:08

import json

from web.handlers.base import BaseHandler


class IndexHandlers(BaseHandler):
    async def get(self):
        if self.current_user:
            self.redirect('/my/')
            return

        tplid = self.get_argument('tplid', None)
        fields = ('id', 'sitename', 'success_count')
        tpls = sorted(await self.db.tpl.list(userid=None, fields=fields, limit=None), key=lambda t: -t['success_count'])
        if not tpls:
            return await self.render('index.html', tpls=[], tplid=0, tpl=None, variables=[])

        if not tplid:
            for tpl in tpls:
                if tpl.get('id'):
                    tplid = tpl['id']
                    break
        tplid = int(tplid)
        tpl = self.check_permission(await self.db.tpl.get(tplid, fields=('id', 'userid', 'sitename', 'siteurl', 'note', 'variables', 'init_env')))
        variables = json.loads(tpl['variables'])
        if not tpl['init_env']:
            tpl['init_env'] = '{}'

        return await self.render('index.html', tpls=tpls, tplid=tplid, tpl=tpl, variables=variables, init_env=json.loads(tpl['init_env']))


handlers = [
    ('/', IndexHandlers),
]
