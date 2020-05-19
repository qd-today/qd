#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 21:06:02

import time
from base import *

import requests
import re

def my_status(task):
    if task['disabled']:
        return u'停止'
    if task['last_failed_count']:
        return u'已失败%d次，重试中...' % task['last_failed_count']
    if task['last_failed'] > task['last_success']:
        return u'失败'
    if task['success_count'] == 0 and task['failed_count'] == 0 and task['next'] and (task['next'] - time.time() < 60):
        return u'正在准备为您签到'
    return u'正常'

class SubscribeHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        user = self.current_user
        tpls = []
        url = "https://github.com/qiandao-today/templates"
        
        res = requests.get(url, verify=False)
        if (res.status_code == 200):
            content = res.content.decode(res.encoding, 'replace')
            README_content = re.findall(r"<article([\w\W]+?)</article", content)[0]
            tpls_temp = re.findall(r"tr>([\w\W]+?)</tr", README_content)
            
            for cnt in range(1, len(tpls_temp)):
                tpl_temp = re.findall(r"center\">(.+?)</td", tpls_temp[cnt])
                harurl = re.findall(r"href=\"(.+?)\"", tpl_temp[2])[0]
                filename = re.findall(r">(.+?)<", tpl_temp[2])[0]
                
                tpls.append ({
                                "name":tpl_temp[0],
                                "author":tpl_temp[1],
                                "filename":filename,
                                "url":harurl,
                                "vars":tpl_temp[3],
                                "comments":tpl_temp[4]
                            })
                
        self.render('tpl_subscribe.html', tpls=tpls, userid=user['id'])

handlers = [
        ('/subscribe/?', SubscribeHandler),
        ]

