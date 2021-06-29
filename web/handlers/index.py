#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-07-30 16:02:08

import json
from .base import *

class IndexHandlers(BaseHandler):
    def get(self):
        if self.current_user:
            self.redirect('/my/')
            return

        tplid = self.get_argument('tplid', None)
        fields = ('id', 'sitename', 'success_count')
        tpls = sorted(self.db.tpl.list(userid=None, fields=fields, limit=None), key=lambda t: -t['success_count'])
        if not tpls:
            return self.render('index.html', tpls=[], tplid=0, tpl=None, variables=[])

        if not tplid:
            for tpl in tpls:
                if tpl.get('id'):
                    tplid = tpl['id']
                    break
        tplid = int(tplid)
        tpl = self.check_permission(self.db.tpl.get(tplid, fields=('id', 'userid', 'sitename', 'siteurl', 'note', 'variables')))
        variables = json.loads(tpl['variables'])
        
        return self.render('index.html', tpls=tpls, tplid=tplid, tpl=tpl, variables=variables)

handlers = [
        ('/', IndexHandlers),
        ]
