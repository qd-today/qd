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
import random
import traceback

from funcs import pusher
from funcs import cal

from base import *

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

        groups = []
        for task in self.db.task.list(user['id'], fields=('groups'), limit=None):
            temp = task['groups']
            if (temp not  in groups):
                groups.append(temp)
        
        self.render('task_new.html', tpls=tpls, tplid=tplid, tpl=tpl, variables=variables, task={}, groups=groups)

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

        if ('New_group' in self.request.body_arguments):
            New_group = self.request.body_arguments['New_group'][0].strip()
            
            if New_group != "" :
                target_group = New_group.decode("utf-8").encode("utf-8")
            else:
                for value in self.request.body_arguments:
                    if self.request.body_arguments[value][0] == 'on':
                        if (value.find("group-select-") > -1):
                            target_group = value.replace("group-select-", "").strip()
                            break
                    else:
                        target_group = 'None'

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
        
        if ('New_group' in self.request.body_arguments):
            self.db.task.mod(taskid, groups=target_group)

        self.redirect('/my/')

class TaskEditHandler(TaskNewHandler):
    @tornado.web.authenticated
    def get(self, taskid):
        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'userid',
            'tplid', 'disabled', 'note')), 'w')
        task['init_env'] = self.db.user.decrypt(user['id'], self.db.task.get(taskid, 'init_env')['init_env'])
        envs = []
        for key, value in task['init_env'].items():
            tmp = {'init_env_name':key}
            tmp['data'] = value
            envs.append(tmp)
        task['init_env'] = envs

        tpl = self.check_permission(self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'note',
            'sitename', 'siteurl', 'variables')))

        variables = json.loads(tpl['variables'])
        self.render('task_new.html', tpls=[tpl, ], tplid=tpl['id'], tpl=tpl, variables=variables, task=task)

class TaskRunHandler(BaseHandler):
    @tornado.web.authenticated
    @gen.coroutine
    def post(self, taskid):
        self.evil(+2)
        start_ts = int(time.time())
        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'init_env',
            'env', 'session', 'last_success', 'last_failed', 'success_count', 'note',
            'failed_count', 'last_failed_count', 'next', 'disabled', 'ontime', 'ontimeflg', 'pushsw','newontime')), 'w')

        tpl = self.check_permission(self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename',
            'siteurl', 'tpl', 'interval', 'last_success')))
        t = 0 if not tpl['userid'] else task['userid'], tpl['tpl']
        fetch_tpl = self.db.user.decrypt(
                0 if not tpl['userid'] else task['userid'], tpl['tpl'])
        env = dict(
                variables = self.db.user.decrypt(task['userid'], task['init_env']),
                session = [],
                )
        
        pushsw = json.loads(task['pushsw'])
        newontime = json.loads(task['newontime'])
        pushertool = pusher()
        caltool = cal()

        try:
            new_env = yield self.fetcher.do_fetch(fetch_tpl, env)
        except Exception as e:
            t = datetime.datetime.now().strftime('%m-%d %H:%M:%S')
            title = u"签到任务 {0}-{1} 失败".format(tpl['sitename'], task['note'])
            logtmp = u"{0} 日志：{1}".format(t, e)
            pushertool.pusher(user['id'], pushsw, 0x4, title, logtmp)

            self.db.tasklog.add(task['id'], success=False, msg=unicode(e))
            self.finish('<h1 class="alert alert-danger text-center">签到失败</h1><div class="showbut well autowrap" id="errmsg">%s<button class="btn hljs-button" data-clipboard-target="#errmsg" >复制</button></div>' % e)
            return

        self.db.tasklog.add(task['id'], success=True, msg=new_env['variables'].get('__log__'))
        if (newontime["sw"]):
            if ('mode' not in newontime):
                newontime['mode'] = 'ontime'

            if (newontime['mode'] == 'ontime'):
                newontime['date'] = (datetime.datetime.now()+datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            nextTime = caltool.calNextTs(newontime)['ts']
        else:
            nextTime = time.time() + (tpl['interval'] if tpl['interval'] else 24 * 60 * 60)
            
        self.db.task.mod(task['id'],
                disabled = False,
                last_success = time.time(),
                last_failed_count = 0,
                success_count = task['success_count'] + 1,
                mtime = time.time(),
                next = nextTime)
        
        t = datetime.datetime.now().strftime('%m-%d %H:%M:%S')
        title = u"签到任务 {0}-{1} 成功".format(tpl['sitename'], task['note'])
        logtmp = new_env['variables'].get('__log__')
        logtmp = u"{0}  日志：{1}".format(title, logtmp)
        pushertool.pusher(user['id'], pushsw, 0x8, title, logtmp)

        self.db.tpl.incr_success(tpl['id'])
        self.finish('<h1 class="alert alert-success text-center">签到成功</h1><div class="showbut well autowrap" id="errmsg"><pre>%s</pre><button class="btn hljs-button" data-clipboard-target="#errmsg" >复制</button></div>' % logtmp)
        logDay = int(self.db.site.get(1, fields=('logDay'))['logDay'])
        for log in self.db.tasklog.list(taskid = taskid, fields=('id', 'ctime')):
            if (time.time() - log['ctime']) > (logDay * 24 * 60 * 60):
                self.db.tasklog.delete(log['id'])
        return

class TaskLogHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, taskid):
        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'disabled')))

        tasklog = self.db.tasklog.list(taskid = taskid, fields=('success', 'ctime', 'msg'))

        self.render('tasklog.html', task=task, tasklog=tasklog)

class TaskLogDelHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, taskid):
        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'disabled')))
        tasklog = self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'))
        for log in tasklog:
            self.db.tasklog.delete(log['id'])
        tasklog = self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'))

        self.redirect("/task/{0}/log".format(taskid))
        return

    @tornado.web.authenticated
    def post(self, taskid):
        user = self.current_user
        body_arguments = self.request.body_arguments
        day = 365
        if ('day' in body_arguments):
            day = int(json.loads(body_arguments['day'][0]))
        tasklog = self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'))
        for log in tasklog:
            if (time.time() - log['ctime']) > (day * 24 * 60 * 60):
                self.db.tasklog.delete(log['id'])
        tasklog = self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'))

        self.redirect("/task/{0}/log".format(taskid))
        return

class TaskDelHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, taskid):
        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'userid', )), 'w')
        logs = self.db.tasklog.list(taskid = taskid, fields=('id'))
        for log in logs:
            self.db.tasklog.delete(log['id'])
        self.db.task.delete(task['id'])
        
        referer = self.request.headers.get('referer', '/my/')
        self.redirect(referer)

class TaskDisableHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, taskid):
        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'userid', )), 'w')
        logs = self.db.tasklog.list(taskid = taskid, fields=('id'))
        self.db.task.mod(task['id'], disabled=1)
        
        referer = self.request.headers.get('referer', '/my/')
        self.redirect(referer)
        
class TaskSetTimeHandler(TaskNewHandler):
    @tornado.web.authenticated
    def get(self, taskid):
        user = self.current_user
        task = self.check_permission(self.db.task.get(taskid, fields=('id', 'userid',
            'tplid', 'disabled', 'note', 'ontime', 'ontimeflg', 'newontime')), 'w')
        
        newontime = json.loads(task['newontime'])
        ontime = newontime
        if ('mode' not in newontime):
            ontime['mode'] = 'ontime'
        else:
            ontime = newontime
        today_date = time.strftime("%Y-%m-%d",time.localtime())

        self.render('task_setTime.html', task=task, ontime=ontime, today_date=today_date)
    
    @tornado.web.authenticated
    def post(self, taskid):
        try:
            envs = self.request.body_arguments
            for env in envs.keys():
                envs[env] = u'{0}'.format(envs[env][0])
            c = cal()
            if ('time' in envs):
                if (len(envs['time'].split(':')) < 3):
                    envs['time'] = envs['time'] + ':00'
                    
            tmp = c.calNextTs(envs)
            if (tmp['r'] == 'True'):
                self.db.task.mod(taskid,
                    disabled = False,
                    newontime = json.dumps(envs),
                    next = tmp['ts'])
            else:
                raise Exception(tmp)
  
        except Exception:
            traceback.print_exc()
            self.render('utils_run_result.html', log=traceback.format_exc(), title=u'设置失败', flg='danger')
            return
        
        self.render('utils_run_result.html', log=u'设置成功，下次执行时间', title=u'设置成功', flg='success')
        return
        
        
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
        
class TasksDelHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, userid):
        try:
            user = self.current_user
            body_arguments = self.request.body_arguments
            if ('taskids' in body_arguments):
                taskids = json.loads(self.request.body_arguments['taskids'][0])
            if (body_arguments['func'][0] == 'Del'):
                for taskid in taskids:
                    task = self.check_permission(self.db.task.get(taskid, fields=('id', 'userid', )), 'w')
                    logs = self.db.tasklog.list(taskid = taskid, fields=('id'))
                    for log in logs:
                        self.db.tasklog.delete(log['id'])
                    self.db.task.delete(taskid)
            elif (body_arguments['func'][0] == 'setGroup'):
                New_group = body_arguments['groupValue'][0].strip().decode("utf-8").encode("utf-8")
                if(New_group == ''):
                    New_group = u'None'
                for taskid in taskids:
                    self.db.task.mod(taskid, groups=New_group)
                    
            self.finish('<h1 class="alert alert-success text-center">操作成功</h1>')
        except Exception as e:
            self.render('tpl_run_failed.html', log=str(e))
            return

class GetGroupHandler(TaskNewHandler):
    @tornado.web.authenticated
    def get(self, taskid):
        user = self.current_user      
        groups = {}
        for task in self.db.task.list(user['id'], fields=('groups'), limit=None):
            groups[task['groups']] = ""
        
        self.write(json.dumps(groups, ensure_ascii=False, indent=4))
        return

handlers = [
        ('/task/new', TaskNewHandler),
        ('/task/(\d+)/edit', TaskEditHandler),
        ('/task/(\d+)/settime', TaskSetTimeHandler),
        ('/task/(\d+)/del', TaskDelHandler), 
        ('/task/(\d+)/disable', TaskDisableHandler),
        ('/task/(\d+)/log', TaskLogHandler),
        ('/task/(\d+)/log/del', TaskLogDelHandler),
        ('/task/(\d+)/run', TaskRunHandler),
        ('/task/(\d+)/group', TaskGroupHandler),
        ('/tasks/(\d+)', TasksDelHandler), 
        ('/getgroups/(\d+)', GetGroupHandler), 
        ]
