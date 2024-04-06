#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 11:39:25
# pylint: disable=broad-exception-raised

import json
import time

from tornado.web import authenticated

import config
from libs.funcs import Cal
from web.handlers.base import BaseHandler, logger_web_handler


class TaskMultiOperateHandler(BaseHandler):
    @authenticated
    async def get(self, userid):
        try:
            tasktype = ''
            user = self.current_user
            op = self.get_argument('op', '')
            _groups = []
            if op != '':
                tasktype = op
                if isinstance(tasktype, bytes):
                    tasktype = tasktype.decode()
            else:
                raise Exception('错误参数')
            if tasktype == 'setgroup':
                for task in await self.db.task.list(user['id'], fields=('_groups',), limit=None):
                    if not isinstance(task['_groups'], str):
                        task['_groups'] = str(task['_groups'])
                    temp = task['_groups']
                    if temp not in _groups:
                        _groups.append(temp)

        except Exception as e:
            logger_web_handler.error('UserID: %s browse Task_Multi failed! Reason: %s', userid, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
            await self.render('utils_run_result.html', log=str(e), title='打开失败', flg='danger')
            return

        await self.render('taskmulti.html', user=user, tasktype=tasktype, _groups=_groups)
        return

    @authenticated
    async def post(self, userid):
        # user = self.current_user
        try:
            envs = {}
            for key in self.request.body_arguments:
                envs[key] = self.get_body_arguments(key)
            env = {}
            op = self.get_argument('op', '')
            if op != '':
                tasktype = op
                if isinstance(tasktype, bytes):
                    tasktype = tasktype.decode()
            else:
                raise Exception('错误参数')
            for k, v in envs.items():
                env[k] = json.loads(v[0])
            if len(env['selectedtasks']) == 0:
                raise Exception('请选择任务')
            for taskid, selected in env['selectedtasks'].items():
                if selected:
                    async with self.db.transaction() as sql_session:
                        task = await self.db.task.get(taskid, fields=('id', 'note', 'tplid', 'userid'), sql_session=sql_session)
                        if task:
                            if task['userid'] == int(userid):
                                if tasktype == 'disable':
                                    await self.db.task.mod(taskid, disabled=True, sql_session=sql_session)
                                if tasktype == 'enable':
                                    await self.db.task.mod(taskid, disabled=False, sql_session=sql_session)
                                if tasktype == 'delete':
                                    logs = await self.db.tasklog.list(taskid=taskid, fields=('id',), sql_session=sql_session)
                                    for log in logs:
                                        await self.db.tasklog.delete(log['id'], sql_session=sql_session)
                                    await self.db.task.delete(taskid, sql_session=sql_session)
                                if tasktype == 'setgroup':
                                    group_env = env['setgroup']
                                    new_group = group_env['newgroup'].strip()
                                    if new_group != "" :
                                        target_group = new_group
                                    else:
                                        target_group = group_env['checkgroupname'] or 'None'

                                    await self.db.task.mod(taskid, _groups=target_group, sql_session=sql_session)

                                if tasktype == 'settime':
                                    time_env = env['settime']
                                    c = Cal()
                                    settime_env = {
                                        'sw': True,
                                        'time': time_env['ontime_val'],
                                        'mode': time_env['ontime_method'],
                                        'date': time_env['ontime_run_date'],
                                        'tz1': time_env['randtimezone1'],
                                        'tz2': time_env['randtimezone2'],
                                        'cron_val': time_env['cron_val'],
                                    }

                                    if time_env['randtimezone1']:
                                        settime_env['randsw'] = True
                                    # if time_env['cron_sec'] != '':
                                    #     settime_env['cron_sec'] = time_env['cron_sec']
                                    if time_env['ontime_method'] == 'ontime':
                                        if time_env['ontime_run_date'] == '':
                                            settime_env['date'] = time.strftime("%Y-%m-%d", time.localtime())
                                        if time_env['ontime_val'] == '':
                                            settime_env['time'] = time.strftime("%H:%M:%S", time.localtime())
                                    if len(settime_env['time'].split(':')) == 2:
                                        settime_env['time'] = settime_env['time'] + ':00'

                                    tmp = c.cal_next_ts(settime_env)
                                    if tmp['r'] == 'True':
                                        await self.db.task.mod(taskid, disabled=False,
                                                               newontime=json.dumps(settime_env),
                                                               next=tmp['ts'],
                                                               sql_session=sql_session)
                                    else:
                                        raise Exception('参数错误')
                            else:
                                raise Exception('用户id与任务的用户id不一致')
        except Exception as e:
            logger_web_handler.error('UserID: %s set Task_Multi failed! Reason: %s', userid, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
            await self.render('utils_run_result.html', log=str(e), title='设置失败', flg='danger')
            return

        await self.render('utils_run_result.html', log='设置成功，请关闭操作对话框或刷新页面查看', title='设置成功', flg='success')
        return


class GetTasksInfoHandler(BaseHandler):
    @authenticated
    async def post(self, userid):
        try:
            envs = {}
            for key in self.request.body_arguments:
                envs[key] = self.get_body_arguments(key)
            # user = self.current_user
            tasks = []
            for taskid, selected in envs.items():
                if isinstance(selected[0], bytes):
                    selected[0] = selected[0].decode()
                if selected[0] == 'true':
                    task = await self.db.task.get(taskid, fields=('id', 'note', 'tplid'))
                    if task:
                        sitename = (await self.db.tpl.get(task['tplid'], fields=('sitename',)))['sitename']
                        task['sitename'] = sitename
                        tasks.append(task)
        except Exception as e:
            logger_web_handler.error('UserID: %s get Tasks_Info failed! Reason: %s', userid, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
            await self.render('utils_run_result.html', log=str(e), title='获取信息失败', flg='danger')
            return

        await self.render('taskmulti_tasksinfo.html', tasks=tasks)
        return


handlers = [
    (r'/task/(\d+)/multi', TaskMultiOperateHandler),
    (r'/task/(\d+)/get_tasksinfo', GetTasksInfoHandler),
]
