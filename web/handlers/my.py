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
        tpls = self.db.tpl.list(userid=user['id'], fields=('id', 'siteurl', 'sitename', 'banner', 'note', 'disabled', 'lock', 'last_success', 'ctime', 'mtime', 'fork'), limit=None)

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
                
        self.render('my.html', tpls=tpls, tasks=tasks, my_status=my_status, userid=user['id'], taskgroups=groups)

class CheckUpdateHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        user = self.current_user
        tpls = self.db.tpl.list(userid=user['id'], fields=('id', 'siteurl', 'sitename', 'banner', 'note', 'disabled', 'lock', 'last_success', 'ctime', 'mtime', 'fork', 'tplurl', "updateable"), limit=None)
        
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
                
        res = requests.get("https://github.com/qiandao-today/templates", verify=False)
        if (res.status_code == 200):
            content = res.content.decode(res.encoding, 'replace')
            Files_content = re.findall(r"data-pjax>([\w\W]+?)</table", content)[0]
            Files_temp = re.findall(r"<td class=\"content\">([\w\W]+?)</td", Files_content)
            ages_temp =  re.findall(r"<td class=\"age\"([\w\W]+?)</td", Files_content)
            common_tpls = []
            for cnt in range(1, len(Files_temp)):
                filename = re.findall(r"title=\"(.+?)\"", Files_temp[cnt])[0]
                file_age = re.findall(r"datetime=\"(.+?)\"", ages_temp[cnt])[0]
                file_age_ts = time.mktime(datetime.datetime.strptime(file_age, u'%Y-%m-%dT%H:%M:%SZ').timetuple())
                common_tpls.append({
                    "filename":filename,
                    "age":file_age_ts
                })
                    
        for tpl in tpls:
            HarFileNames = re.findall(r'/master/(.+)', tpl['tplurl'])
            for HarFileName in HarFileNames:
                for common_tpl in common_tpls:
                    if (HarFileName == common_tpl["filename"] ):
                        if (tpl['mtime'] < common_tpl['age']):
                            self.db.tpl.mod(tpl["id"], updateable=1)
                            
        tpls = self.db.tpl.list(userid=user['id'], fields=('id', 'siteurl', 'sitename', 'banner', 'note', 'disabled', 'lock', 'last_success', 'ctime', 'mtime', 'fork', 'tplurl', "updateable"), limit=None)
            
        self.render('my.html', tpls=tpls, tasks=tasks, my_status=my_status, userid=user['id'], taskgroups=groups)

handlers = [
        ('/my/?', MyHandler),
        ('/my/checkupdate/?', CheckUpdateHandler),
        ]

