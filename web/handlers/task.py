#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 11:39:25

import json
import time
from tornado import gen
import datetime 
import pytz
import send2phone

from base import *

def calNextTimestamp(etime, todayflg):
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.datetime.now()
    now = datetime.datetime(year=now.year, 
                            month=now.month, 
                            day=now.day, 
                            hour=now.hour, 
                            minute=now.minute, 
                            tzinfo=tz)
    temp = etime.split(":")
    if (todayflg):
        eday = now.day
    else:
        eday = now.day+1
    ehour = int(temp[0])
    emin = int(temp[1])
    esecond = int(temp[2])
    pre = datetime.datetime(year=now.year, 
                            month=now.month, 
                            day=eday, 
                            hour=ehour, 
                            minute=emin,
                            second=esecond,
                            tzinfo=tz)
    next = int(time.mktime(pre.timetuple()) + pre.microsecond/1e6)
    return next

class TaskNewHandler(BaseHandler):    
    def get(self):
        user = self.current_user
        tplid = self.get_argument('tplid', None)
        fields = ('id', 'sitename', 'success_count')

        tpls = []
        if user:
            tpls += sorted(self.db.tpl.list(userid=user['id'], fields=fields, limit=None), key=lambda t: -t['id'])
        if tpls:
            tpls.append({'id': 0, 'sitename': u'以下为公共模板'})
        tpls += sorted(self.db.tpl.list(userid=None, fields=fields, limit=None), key=lambda t: -t['success_count'])

        if not tplid:
            for tpl in tpls:
                if tpl.get('id'):
                    tplid = tpl['id']
                    break
        tplid = int(tplid)

        tpl = self.check_permission(self.db.tpl.get(tplid, fields=('id', 'userid', 'note', 'sitename', 'siteurl', 'variables')))
        variables = json.loads(tpl['variables'])
        
        self.render('task_new.html', tpls=tpls, tplid=tplid, tpl=tpl, variables=variables, task={})

    @tornado.web.authenticated
    def post(self, taskid=None):
        user = self.current_user
        tplid = int(self.get_body_argument('_binux_tplid'))
        tested = self.get_body_argument('_binux_tested', False)
        note = self.get_body_argument('_binux_note')

        tpl = self.check_permission(self.db.tpl.get(tplid, fields=('id', 'userid', 'interval')))

        env = {}
        for key, value in self.request.body_arguments.iteritems():
            if key.startswith('_binux_'):
                continue
            if not value:
                continue
            env[key] = self.get_body_argument(key)

        if not taskid:
            env = self.db.user.encrypt(user['id'], env)
            taskid = self.db.task.add(tplid, user['id'], env)

            if tested:
                self.db.task.mod(taskid, note=note, next=time.time() + (tpl['interval'] or 24*60*60))
            else:
                self.db.task.mod(taskid, note=note, next=time.time() + 15)
        else:
            task = self.check_permission(self.db.task.get(taskid, fields=('id', 'userid', 'init_env')), 'w')

            init_env = self.db.user.decrypt(user['id'], task['init_env'])
            init_env.update(env)
            init_env = self.db.user.encrypt(user['id'], init_env)
            self.db.task.mod(taskid, init_env=init_env, env=None, session=None, note=note)

        #referer = self.request.headers.get('referer', '/my/')
        self.redirect('/my/')

class TaskEditHandler(TaskNewHandler):
    @tornado.web.authenticated
    def get(self, taskid):
        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'userid',
            'tplid', 'disabled', 'note')), 'w')

        tpl = self.check_permission(self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'note',
            'sitename', 'siteurl', 'variables')))

        variables = json.loads(tpl['variables'])
        self.render('task_new.html', tpls=[tpl, ], tplid=tpl['id'], tpl=tpl, variables=variables, task=task)

class TaskRunHandler(BaseHandler):
    @tornado.web.authenticated
    @gen.coroutine
    def post(self, taskid):
        self.evil(+2)

        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'init_env',
            'env', 'session', 'last_success', 'last_failed', 'success_count',
            'failed_count', 'last_failed_count', 'next', 'disabled', 'ontime', 'ontimeflg')), 'w')

        tpl = self.check_permission(self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename',
            'siteurl', 'tpl', 'interval', 'last_success')))
        t = 0 if not tpl['userid'] else task['userid'], tpl['tpl']
        fetch_tpl = self.db.user.decrypt(
                0 if not tpl['userid'] else task['userid'], tpl['tpl'])
        env = dict(
                variables = self.db.user.decrypt(task['userid'], task['init_env']),
                session = [],
                )
        
        notice = self.db.user.get(task['userid'], fields=('skey', 'barkurl', 'noticeflg', 'wxpusher'))
        temp = notice['wxpusher'].split(u";")
        wxpusher_token = temp[0] if (len(temp) >= 2) else ""
        wxpusher_uid = temp[1] if (len(temp) >= 2) else "" 
        pushno2b = send2phone.send2phone(barkurl=notice['barkurl'])
        pushno2s = send2phone.send2phone(skey=notice['skey'])
        pushno2w = send2phone.send2phone(wxpusher_token=wxpusher_token, wxpusher_uid=wxpusher_uid)

        try:
            new_env = yield self.fetcher.do_fetch(fetch_tpl, env)
        except Exception as e:
            if (notice['noticeflg'] & 0x4 != 0):
                t = datetime.datetime.now().strftime('%m-%d %H:%M:%S')
                title = u"签到任务 {0} 手动运行失败".format(tpl['sitename'])
                pushno2b.send2bark(title, u"{0} 请排查原因".format(t, e))
                pushno2s.send2s(title, u"{0} 日志：{1}".format(t, e))
                pushno2w.send2wxpusher(title+u"{0} 日志：{1}".format(t, e))
                
            self.db.tasklog.add(task['id'], success=False, msg=unicode(e))
            self.finish('<h1 class="alert alert-danger text-center">签到失败</h1><div class="well">%s</div>' % e)
            return

        self.db.tasklog.add(task['id'], success=True, msg=new_env['variables'].get('__log__'))
        if (task["ontimeflg"] == 1):
            nextTime = calNextTimestamp(task["ontime"], todayflg=False)
        else:
            nextTime = time.time() + (tpl['interval'] if tpl['interval'] else 24 * 60 * 60)
            
        self.db.task.mod(task['id'],
                disabled = False,
                last_success = time.time(),
                last_failed_count = 0,
                success_count = task['success_count'] + 1,
                mtime = time.time(),
                next = nextTime)
        
        if (notice['noticeflg'] & 0x8 != 0):
            t = datetime.datetime.now().strftime('%m-%d %H:%M:%S')
            title = u"签到任务 {0} 手动运行成功".format(tpl['sitename'])
            pushno2b.send2bark(title, u"{0} 成功".format(t))
            pushno2s.send2s(title, u"{0} 成功".format(t))
            pushno2w.send2wxpusher(title+u"{0}".format(t))
        
        self.db.tpl.incr_success(tpl['id'])
        self.finish('<h1 class="alert alert-success text-center">签到成功</h1>')
        return

class TaskLogHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, taskid):
        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'disabled')))

        tasklog = self.db.tasklog.list(taskid = taskid, fields=('success', 'ctime', 'msg'))

        self.render('tasklog.html', task=task, tasklog=tasklog)

class TaskDelHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, taskid):
        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'userid', )), 'w')

        self.db.task.delete(task['id'])
        referer = self.request.headers.get('referer', '/my/')
        self.redirect(referer)
        
class TaskSetTimeHandler(TaskNewHandler):
    @tornado.web.authenticated
    def get(self, taskid):
        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'userid',
            'tplid', 'disabled', 'note', 'ontime', 'ontimeflg')), 'w')

        tpl = self.check_permission(self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'note',
            'sitename', 'siteurl', 'variables')))
        
        variables = json.loads(tpl['variables'])
        todayflg = True if task['ontimeflg'] == 1 else False
        now = datetime.datetime.now().strftime( '%H:%M:%S')
        onetime = task['ontime']
        
        self.render('task_setTime.html', tpls=[tpl, ], tplid=tpl['id'], tpl=tpl, task=task, ontimeflg=todayflg, mintime=now, onetime=onetime)
    
    @tornado.web.authenticated
    def post(self, taskid):
        self.evil(+2)
        
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'init_env',
            'env', 'session', 'last_success', 'last_failed', 'success_count',
            'failed_count', 'last_failed_count', 'next', 'disabled')), 'w')

        tpl = self.check_permission(self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename',
            'siteurl', 'tpl', 'interval', 'last_success')))

        ontime = self.request.body_arguments['timevalue'][0]
        temp = ontime.split(":")
        if (len(temp) < 3):
            ontime = ontime + ":00"     # 没有秒自动补零
        
        if  ('flg' in self.request.body_arguments):
            OntimeFlg = 1
            if  ('todayflg' in self.request.body_arguments):
                next = calNextTimestamp(ontime, todayflg=True)
            else:
                next = calNextTimestamp(ontime, todayflg=False)
        else :
            OntimeFlg = 0
            next = time.time() + (tpl['interval'] if tpl['interval'] else 24 * 60 * 60)
        
        self.db.task.mod(task['id'],
                disabled = False,
                ontime = ontime,
                ontimeflg = OntimeFlg,
                next = next)
                
        self.redirect('/my/')
        
        
class TaskGroupHandler(TaskNewHandler):
    @tornado.web.authenticated
    def get(self, taskid):
        user = self.current_user      
        groupNow = self.db.task.get(taskid, fields=('groups'))['groups']
        tasks = []
        groups = []
        for task in self.db.task.list(user['id'], fields=('groups'), limit=None):
            temp = task['groups']
            if (temp not  in groups):
                groups.append(temp)

        self.render('task_setgroup.html', taskid=taskid, groups=groups, groupNow=groupNow)
    
    @tornado.web.authenticated
    def post(self, taskid):        
        New_group = self.request.body_arguments['New_group'][0].strip()
        
        if New_group != "" :
            target_group = New_group.decode("utf-8").encode("utf-8")
        else:
            for value in self.request.body_arguments:
                if self.request.body_arguments[value][0] == 'on':
                    target_group = value.strip()
                    break
                else:
                    target_group = 'None'
            
        self.db.task.mod(taskid, groups=target_group)
   
        self.redirect('/my/')
        
        
handlers = [
        ('/task/new', TaskNewHandler),
        ('/task/(\d+)/edit', TaskEditHandler),
        ('/task/(\d+)/settime', TaskSetTimeHandler),
        ('/task/(\d+)/del', TaskDelHandler),
        ('/task/(\d+)/log', TaskLogHandler),
        ('/task/(\d+)/run', TaskRunHandler),
        ('/task/(\d+)/group', TaskGroupHandler),
        ]
