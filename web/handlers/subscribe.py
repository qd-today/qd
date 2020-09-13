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
import base64
import json
import os
import codecs
import urllib

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
        tpls2 = []
        for tpl in  self.db.tpl.list(userid=user['id'], fields=('id', 'tplurl', "updateable"), limit=None):
            tpls2.append(tpl)

        url = "https://gitee.com/api/v5/repos/qiandao-today/templates/readme"
        
        res = requests.get(url, verify=False)
        if (res.status_code == 200):            
            content = json.loads(res.content)['content']
            content = base64.b64decode(content)
            README_content = re.findall(r":-: \| :-: \| :-: \| :-: \|:-:([\w\W]*)", content)[0]
            tpls_temp = re.findall(r"(.*?)\n", README_content)
            old_hjson = {}
            hfile = "./tpls_history.json"

            if (True == os.path.isfile(hfile)):
                hjson = json.loads(open(hfile, 'r').read())
            else:
                hjson = {}

            old_hjson = hjson.copy() 
            
            for cnt in range(1, len(tpls_temp)):
                temp = tpls_temp[cnt].split("|")
                author = re.findall("\[(.*?)\]", temp[1])[0]
                filename = re.findall("\[(.*?)\]", temp[2])[0]
                harurl = re.findall("\]\((.*)\)", temp[2])[0]
                tpl = {
                                "name":temp[0],
                                "author":author,
                                "filename":filename,
                                "url":harurl,
                                "date":temp[3],
                                "comments":temp[4],
                                "update":False
                        }
                if (harurl in hjson):
                    if (tpl["date"] == hjson[harurl]["date"]):
                        pass
                    else:
                        tpl["date"] = hjson[harurl]["date"]
                        tpl['content'] = base64.b64encode(requests.get(harurl, verify=False).content.decode('utf-8', 'replace'))
                        tpl["update"] = True
                        hjson[harurl] = tpl

                        for tpl_temp in tpls2:
                            if (tpl_temp['tplurl'] == harurl) and (tpl_temp['updateable'] != 1):
                                self.db.tpl.mod(tpl_temp['id'],updateable=1)
                else:
                    tmp = requests.get(harurl, verify=False).content.decode('utf-8', 'replace')
                    tpl['content'] = base64.b64encode(tmp)
                    hjson[harurl] = tpl
                
            for key in hjson:
                tpls.append(hjson[key])
                
            if (cmp(old_hjson, hjson) == 0):
                pass
            else:
                fp = codecs.open(hfile, 'w', 'utf-8')
                fp.write(json.dumps(hjson, ensure_ascii=False, indent=4 ))
                fp.close()

        self.render('tpl_subscribe.html', tpls=tpls, userid=user['id'])

handlers = [
        ('/subscribe/?', SubscribeHandler),
        ]

