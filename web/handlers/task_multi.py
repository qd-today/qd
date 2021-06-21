#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 11:39:25

import json
import traceback
import datetime
import time
import random

import croniter

from base import *
from funcs import cal

class TaskMultiOperateHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, userid):
        try:
            tasktype = ''
            user = self.current_user
            op = self.request.arguments.get('op', '')
            groups = []
            if (op != ''):
                tasktype = op[0]
            else:
                raise Exception('错误参数')
            if (tasktype == 'setgroup'):
                for task in self.db.task.list(user['id'], fields=('groups'), limit=None):
                    temp = task['groups']
                    if (temp not  in groups):
                        groups.append(temp)

        except Exception:
            traceback.print_exc()
            self.render('utils_run_result.html', log=traceback.format_exc(), title=u'打开失败', flg='danger')
            return

        self.render('taskmulti.html', user=user, tasktype=tasktype, groups=groups)
        return
    
    @tornado.web.authenticated
    def post(self, userid):
        user = self.current_user
        try:
            env = {}
            op = self.request.arguments.get('op', '')
            if (op != ''):
                tasktype = op[0]
            else:
                raise Exception('错误参数')
            pass
            for k, v  in self.request.body_arguments.items():
                env[k] = json.loads(v[0])
            for taskid, selected  in env['selectedtasks'].items():
                if (selected):
                    task = self.db.task.get(taskid, fields=('id',  'note', 'tplid', 'userid'))
                    if (task):
                        if (task['userid']) == int(userid):
                            if (tasktype == 'disable'):
                                self.db.task.mod(taskid, disabled = True)
                            if (tasktype == 'enable'):
                                self.db.task.mod(taskid, disabled = False)
                            if (tasktype == 'delete'):
                                logs = self.db.tasklog.list(taskid = taskid, fields=('id'))
                                for log in logs:
                                    self.db.tasklog.delete(log['id'])
                                self.db.task.delete(taskid)
                            if (tasktype == 'setgroup'):
                                group_env = env['setgroup']
                                New_group = group_env['newgroup'].strip()
                                if New_group != "" :
                                    target_group = New_group.decode("utf-8").encode("utf-8")
                                else:
                                    target_group = group_env['checkgroupname'] or 'None'

                                self.db.task.mod(taskid, groups=target_group)

                            if (tasktype == 'settime'):
                                time_env = env['settime']
                                c = cal()
                                settime_env = {
                                    'sw': True,
                                    'time': time_env['ontime_val'],
                                    'mode': time_env['ontime_method'],
                                    'date': time_env['ontime_run_date'],
                                    'tz1': time_env['randtimezone1'],
                                    'tz2': time_env['randtimezone2'],
                                    'cron_val': time_env['cron_val'],
                                }

                                if (time_env['randtimezone1'] != '') and (time_env['randtimezone1'] != ''):
                                    settime_env['randsw'] = True 
                                if (time_env['cron_sec'] != ''):
                                    settime_env['cron_sec'] = time_env['cron_sec'] 

                                if (len(settime_env['time'].split(':')) == 2):
                                    settime_env['time'] = settime_env['time'] + ':00'

                                tmp = c.calNextTs(settime_env)
                                if (tmp['r'] == 'True'):
                                    self.db.task.mod(taskid, disabled = False, 
                                                            newontime = json.dumps(settime_env), 
                                                            next = tmp['ts'])
                                else:
                                    raise Exception(u'参数错误')
                        else:
                            raise Exception('用户id与任务的用户id不一致')
        except Exception:
            traceback.print_exc()
            self.render('utils_run_result.html', log=traceback.format_exc(), title=u'设置失败', flg='danger')
            return

        self.render('utils_run_result.html', log=u'设置成功，请手动刷新页面查看', title=u'设置成功', flg='success')
        return

class GetTasksInfoHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, userid):
        try:
            user = self.current_user
            tasks = []
            for taskid, selected  in self.request.body_arguments.items():
                if (selected[0] == 'true'):
                    task = self.db.task.get(taskid, fields=('id',  'note', 'tplid'))
                    if (task):
                        sitename = self.db.tpl.get(task['tplid'], fields=('sitename'))['sitename']
                        task['sitename'] = sitename
                        tasks.append(task)
        except Exception:
            traceback.print_exc()
            self.render('utils_run_result.html', log=traceback.format_exc(), title=u'获取信息失败', flg='danger')
            return

        self.render('taskmulti_tasksinfo.html',  tasks=tasks)
        return

handlers = [
        ('/task/(\d+)/multi', TaskMultiOperateHandler),
        ('/task/(\d+)/get_tasksinfo', GetTasksInfoHandler),
        ]
