#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 21:06:02

import time
import datetime
from base import *
import urllib

import requests
import re
import os
import json

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

class MyHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        user = self.current_user
        adminflg = False
        # 验证用户是否存在
        if (self.db.user.get(user['id'], fields=('id'))):
            if  self.db.user.get(user['id'], fields=('role'))['role'] == 'admin':
                adminflg = True

            hfile = "./tpls_history.json"

            if (True == os.path.isfile(hfile)):
                hjson = json.loads(open(hfile, 'r').read())
            else:
                hjson = {}
            tpls = []

            for tpl in self.db.tpl.list(userid=user['id'], fields=('id', 'siteurl', 'sitename', 'banner', 'note', 'disabled', 'lock', 'last_success', 'ctime', 'mtime', 'fork', 'groups', 'updateable', 'tplurl'), limit=None):
                tplurl = tpl['tplurl']
                if (tpl['updateable'] == 1) and (tplurl in hjson):
                    if (hjson[tplurl]['update']):
                        tpl['tpldata'] = hjson[tplurl]['content']
                tpls.append(tpl)

            tasks = []
            for task in self.db.task.list(user['id'], fields=('id', 'tplid', 'note', 'disabled', 'last_success', 'success_count', 'failed_count', 'last_failed', 'next', 'last_failed_count', 'ctime', 'groups'), limit=None):
                tpl = self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note') )
                task['tpl'] = tpl
                tasks.append(task)

            groups = []
            for task in tasks:
                temp = task['groups']
                if (temp not  in groups):
                    groups.append(temp)

            tplgroups = []
            for tpl in tpls:
                temp = tpl['groups']
                if (temp not  in tplgroups):
                    tplgroups.append(temp)
                    
            self.render('my.html', tpls=tpls, tasks=tasks, my_status=my_status, userid=user['id'], taskgroups=groups,  tplgroups=tplgroups, adminflg=adminflg)
        else:
            return self.redirect('/login')

class CheckUpdateHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        user = self.current_user
        tpls = self.db.tpl.list(userid=user['id'], fields=('id', 'siteurl', 'sitename', 'banner', 'note', 'disabled', 'lock', 'last_success', 'ctime', 'mtime', 'fork', 'tplurl', "updateable",), limit=None)
        
        tasks = []
        for task in self.db.task.list(user['id'], fields=('id', 'tplid', 'note', 'disabled', 'last_success', 'success_count', 'failed_count', 'last_failed', 'next', 'last_failed_count', 'ctime', 'groups'), limit=None):
            tpl = self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note') )
            task['tpl'] = tpl
            tasks.append(task)
        groups = []
        for task in tasks:
            temp = task['groups']
            if (temp not  in groups):
                groups.append(temp)
                
        common_tpls = []
        res = requests.get("https://github.com/qiandao-today/templates", verify=False)
        if (res.status_code == 200):
            content = res.content.decode(res.encoding, 'replace')
            README_content = re.findall(r"<article([\w\W]+?)</article", content)[0]
            tpls_temp = re.findall(r"tr>([\w\W]+?)</tr", README_content)
            
            for cnt in range(1, len(tpls_temp)):
                tpl_temp = re.findall(r"center\">(.+?)</td", tpls_temp[cnt])
                harurl = re.findall(r"href=\"(.+?)\"", tpl_temp[2])[0]
                filename = re.findall(r">(.+?)<", tpl_temp[2])[0]
                update_time_ts = int(time.mktime((datetime.datetime.strptime(tpl_temp[3], "%Y-%m-%d %H:%M:%S").timetuple())))
                
                common_tpls.append ({
                                "name":tpl_temp[0],
                                "author":tpl_temp[1],
                                "filename":filename,
                                "url":harurl,
                                "update_time":tpl_temp[3],
                                "update_time_ts":update_time_ts,
                                "comments":tpl_temp[4]
                            })
                    
        for tpl in tpls:
            HarFileNames = re.findall(r'/master/(.+)', tpl['tplurl'])
            for HarFileName in HarFileNames:
                for common_tpl in common_tpls:
                    if (HarFileName == common_tpl["filename"] ):
                        if (tpl['mtime'] < common_tpl['update_time_ts']):
                            self.db.tpl.mod(tpl["id"], updateable=1)
                            
        tpls = self.db.tpl.list(userid=user['id'], fields=('id', 'siteurl', 'sitename', 'banner', 'note', 'disabled', 'lock', 'last_success', 'ctime', 'mtime', 'fork', 'tplurl', "updateable", 'groups'), limit=None)
        
        tplgroups = []
        for tpl in tpls:
            temp = tpl['groups']
            if (temp not  in tplgroups):
                groups.append(temp)

        self.render('my.html', tpls=tpls, tasks=tasks, my_status=my_status, userid=user['id'], taskgroups=groups, tplgroups=tplgroups)

handlers = [
        ('/my/?', MyHandler),
        ('/my/checkupdate/?', CheckUpdateHandler),
        ]

