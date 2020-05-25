#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>

import config
from db.task import TaskDB as _TaskDB
from sqlite3_db.basedb import BaseDB
import db.task as task 
import os
import json
import time
import datetime
import pytz

import send2phone

def tostr(s):
    if isinstance(s, bytearray):
        return str(s)
    return s
    
class logdaily(_TaskDB, BaseDB):
    def __init__(self, path=config.sqlite3.path):
        self.path = path
        if (os.path.isfile(path)):
            if config.db_type == 'sqlite3':
                import sqlite3_db as db
            else:
                import db
            class DB(object):
                user = db.UserDB()
                tpl = db.TPLDB()
                task = db.TaskDB()
                tasklog = db.TaskLogDB()
            self.db = DB
            
    def logpusher(self, path=config.sqlite3.path):
        users = self._execute("SELECT `id`,`logtime`, `skey`, `wxpusher` FROM `user` WHERE `id` IS NOT NULL")
        userfields = ['id','logtime', 'skey', 'wxpusher']
        for row in users:
            user = (dict(zip(userfields, [tostr(x) for x in row])))
            logtime = json.loads(user['logtime'])
            if (logtime['en']):
                now_ts = int(time.time())
                if (now_ts > logtime['ts']):
                    logs = []
                    for task in self.db.task.list(user['id'], fields=('id', 'tplid', 'ctime', 'note','pushsw'), limit=None):
                        pushsw = json.loads(task['pushsw'])
                        if (pushsw['logen']):
                            tasklogs = []
                            for tasklog in  self.db.tasklog.list(taskid = task["id"], fields=('id', 'msg')):
                                tasklogs.append(tasklog['msg'])   
                            tpl = self.db.tpl.get(task['tplid'], fields=('sitename'))
                            temp = u"{name}-{note} | {msg}\r\n".format(name=tpl['sitename'], note=task["note"], msg=tasklogs[-1])                        
                            logs.append(temp)

                    temp = u"网站|日志\r\n :-: | :-: \r\n"
                    for log in logs:
                        temp = temp + log
                    if (logtime["schanEn"]) and (len(logs) > 0):
                        s = send2phone.send2phone(skey=user['skey'])
                        s.send2s(u"每日定时日志", temp)

                    if (logtime["WXPEn"]) and (len(logs) > 0):
                        wxp_temp = user['wxpusher'].split(";")
                        s = send2phone.send2phone(wxpusher_token=wxp_temp[0], wxpusher_uid=wxp_temp[1])
                        s.send2wxpusher(temp)
                    
                    tz = pytz.timezone('Asia/Shanghai')
                    now = datetime.datetime.now()
                    now = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=now.hour, minute=now.minute, tzinfo=tz)
                    temp = logtime['time'].split(":")
                    ehour = int(temp[0])
                    emin = int(temp[1])
                    esecond = int(temp[2])
                    pre = datetime.datetime(year=now.year, month=now.month, day=now.day, hour=ehour, minute=emin,second=esecond,tzinfo=tz)
                    now_ts = int(time.time())
                    next = int(time.mktime(pre.timetuple()) + pre.microsecond/1e6)
                    if (now_ts > next):
                        pre = datetime.datetime(year=now.year, month=now.month, day=now.day+1, hour=ehour, minute=emin,second=esecond,tzinfo=tz)
                        next = int(time.mktime(pre.timetuple()) + pre.microsecond/1e6)
                    logtime['ts'] = next

                    self.db.user.mod(user['id'], logtime=json.dumps(logtime))

        return 