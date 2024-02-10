#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 11:39:25
# pylint: disable=broad-exception-raised

import datetime
import json
import time
from codecs import escape_decode

from tornado.iostream import StreamClosedError
from tornado.web import HTTPError, authenticated

import config
from libs.funcs import Cal, Pusher
from libs.parse_url import parse_url
from web.handlers.base import BaseHandler, logger_web_handler


class TaskNewHandler(BaseHandler):
    async def get(self):
        user = self.current_user
        tplid = self.get_argument('tplid', None)
        fields = ('id', 'sitename', 'success_count')

        tpls = []
        if user:
            tpls += sorted(await self.db.tpl.list(userid=user['id'], fields=fields, limit=None), key=lambda t: -t['id'])
        if tpls:
            tpls.append({'id': 0, 'sitename': '-----公开模板-----'})
        tpls += sorted(await self.db.tpl.list(userid=None, public=1, fields=fields, limit=None), key=lambda t: -t['success_count'])

        if not tplid:
            for tpl in tpls:
                if tpl.get('id'):
                    tplid = tpl['id']
                    break
        if tplid:
            tplid = int(tplid)

            tpl = self.check_permission(await self.db.tpl.get(tplid, fields=('id', 'userid', 'note', 'sitename', 'siteurl', 'variables', 'init_env')))
            variables = json.loads(tpl['variables'])
            if not tpl['init_env']:
                tpl['init_env'] = '{}'
            init_env = json.loads(tpl['init_env'])

            _groups = []
            if user:
                for task in await self.db.task.list(user['id'], fields=('_groups',), limit=None):
                    if not isinstance(task['_groups'], str):
                        task['_groups'] = str(task['_groups'])
                    temp = task['_groups']
                    if temp not in _groups:
                        _groups.append(temp)

            await self.render('task_new.html', tpls=tpls, tplid=tplid, tpl=tpl, variables=variables, task={}, _groups=_groups, init_env=init_env, default_retry_count=config.task_max_retry_count)
        else:
            await self.render('utils_run_result.html', log='请先添加模板！', title='设置失败', flg='danger')

    @authenticated
    async def post(self, taskid=None):
        user = self.current_user
        tplid = int(self.get_body_argument('_binux_tplid'))
        tested = self.get_body_argument('_binux_tested', False)
        note = self.get_body_argument('_binux_note')
        proxy = self.get_body_argument('_binux_proxy')
        retry_count = self.get_body_argument('_binux_retry_count')
        retry_interval = self.get_body_argument('_binux_retry_interval')

        async with self.db.transaction() as sql_session:
            tpl = self.check_permission(await self.db.tpl.get(tplid, fields=('id', 'userid', 'interval'), sql_session=sql_session))
            envs = {}
            for key in self.request.body_arguments:
                envs[key] = self.get_body_arguments(key)
            env = {}
            for key, value in envs.items():
                if key.startswith('_binux_'):
                    continue
                if not value:
                    continue
                env[key] = self.get_body_argument(key)
            env['_proxy'] = proxy
            retry_count = int(retry_count) if retry_count else retry_count
            retry_interval = int(retry_interval) if retry_interval else retry_interval
            env['retry_count'] = retry_count
            env['retry_interval'] = retry_interval

            if 'New_group' in envs:
                new_group = envs['New_group'][0].strip()

                if new_group != "" :
                    target_group = new_group
                else:
                    for key, value in envs.items():
                        if value[0] == 'on':
                            if key.find("group-select-") > -1:
                                target_group = escape_decode(key.replace("group-select-", "").strip()[2:-1], "hex-escape")[0].decode('utf-8')
                                break
                        else:
                            target_group = 'None'
            retry_interval_modified = True
            if not taskid:
                env = await self.db.user.encrypt(user['id'], env, sql_session=sql_session)
                taskid = await self.db.task.add(tplid, user['id'], env, sql_session=sql_session)

                if tested:
                    await self.db.task.mod(taskid, note=note, next=time.time() + (tpl['interval'] or 24 * 60 * 60), sql_session=sql_session)
                else:
                    await self.db.task.mod(taskid, note=note, next=time.time() + config.new_task_delay, sql_session=sql_session)
            else:
                task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'userid', 'init_env', 'retry_interval'), sql_session=sql_session), 'w')
                if task['retry_interval'] == retry_interval or (retry_interval == '' and task['retry_interval'] is None):
                    retry_interval_modified = False

                init_env = await self.db.user.decrypt(user['id'], task['init_env'], sql_session=sql_session)
                init_env.update(env)
                init_env = await self.db.user.encrypt(user['id'], init_env, sql_session=sql_session)
                await self.db.task.mod(taskid, init_env=init_env, env=None, session=None, note=note, sql_session=sql_session)

            if 'New_group' in envs:
                await self.db.task.mod(taskid, _groups=target_group, sql_session=sql_session)

            if isinstance(retry_count, int) and -1 <= retry_count:
                await self.db.task.mod(taskid, retry_count=retry_count, sql_session=sql_session)

            if retry_interval_modified:
                if retry_interval:
                    await self.db.task.mod(taskid, retry_interval=retry_interval, sql_session=sql_session)
                else:
                    await self.db.task.mod(taskid, retry_interval=None, sql_session=sql_session)

        self.redirect('/my/')


class TaskEditHandler(TaskNewHandler):
    @authenticated
    async def get(self, taskid):  # pylint: disable=W0221
        user = self.current_user
        task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'userid',
                                                                            'tplid', 'disabled', 'note', 'retry_count', 'retry_interval')), 'w')
        task['init_env'] = (await self.db.user.decrypt(user['id'], (await self.db.task.get(taskid, ('init_env',)))['init_env']))

        tpl = self.check_permission(await self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'note',
                                                                                 'sitename', 'siteurl', 'variables')))
        variables = json.loads(tpl['variables'])

        init_env = []
        for var in variables:
            value = task['init_env'][var] if var in task['init_env'] else ''
            init_env.append({'name': var, 'value': value})

        proxy = task['init_env']['_proxy'] if '_proxy' in task['init_env'] else ''
        if task['retry_interval'] is None:
            task['retry_interval'] = ''

        await self.render('task_new.html', tpls=[tpl, ], tplid=tpl['id'], tpl=tpl, variables=variables, task=task, init_env=init_env, proxy=proxy, retry_count=task['retry_count'], retry_interval=task['retry_interval'], default_retry_count=config.task_max_retry_count, task_title="修改任务")


class TaskRunHandler(BaseHandler):
    @authenticated
    async def post(self, taskid):
        self.evil(+2)
        start_ts = int(time.time())
        user = self.current_user
        pushsw = None
        title = f"QD 任务ID: {taskid} 完成"
        logtmp = ""
        async with self.db.transaction() as sql_session:
            task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'init_env',
                                                                                'env', 'session', 'retry_count', 'retry_interval', 'last_success', 'last_failed', 'success_count', 'note',
                                                                                'failed_count', 'last_failed_count', 'next', 'disabled', 'ontime', 'ontimeflg', 'pushsw', 'newontime'), sql_session=sql_session), 'w')

            tpl = self.check_permission(await self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename',
                                                                                     'siteurl', 'tpl', 'interval', 'last_success'), sql_session=sql_session))

            fetch_tpl = await self.db.user.decrypt(
                0 if not tpl['userid'] else task['userid'], tpl['tpl'], sql_session=sql_session)
            env = dict(
                variables=await self.db.user.decrypt(task['userid'], task['init_env'], sql_session=sql_session),
                session=[],
            )

            pushsw = json.loads(task['pushsw'])
            newontime = json.loads(task['newontime'])
            pushertool = Pusher(self.db, sql_session=sql_session)
            caltool = Cal()

            try:
                url = parse_url(env['variables'].get('_proxy'))
                if not url:
                    new_env, _ = await self.fetcher.do_fetch(fetch_tpl, env)
                else:
                    proxy = {
                        'scheme': url['scheme'],
                        'host': url['host'],
                        'port': url['port'],
                        'username': url['username'],
                        'password': url['password']
                    }
                    new_env, _ = await self.fetcher.do_fetch(fetch_tpl, env, [proxy])
            except Exception as e:
                logger_web_handler.error('taskid:%d tplid:%d failed! %.4fs \r\n%s', task['id'], task['tplid'], time.time() - start_ts, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
                t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                title = f"QD任务 {tpl['sitename']}-{task['note']} 失败"
                logtmp = f"{t} \\r\\n日志：{e}"

                await self.db.tasklog.add(task['id'], success=False, msg=str(e), sql_session=sql_session)
                await self.db.task.mod(task['id'],
                                       last_failed=time.time(),
                                       failed_count=task['failed_count'] + 1,
                                       last_failed_count=task['last_failed_count'] + 1,
                                       sql_session=sql_session
                                       )
                try:
                    await self.finish('<h1 class="alert alert-danger text-center">运行失败</h1><div class="showbut well autowrap" id="errmsg">%s<button class="btn hljs-button" data-clipboard-target="#errmsg" >复制</button></div>' % logtmp.replace('\\r\\n', '<br>'))
                except StreamClosedError as e:
                    logger_web_handler.error('stream closed error: %s', e, exc_info=config.traceback_print)

                await pushertool.pusher(user['id'], pushsw, 0x4, title, logtmp)
                return

            await self.db.tasklog.add(task['id'], success=True, msg=new_env['variables'].get('__log__'), sql_session=sql_session)
            if newontime["sw"]:
                if 'mode' not in newontime:
                    newontime['mode'] = 'ontime'

                if newontime['mode'] == 'ontime':
                    newontime['date'] = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                next_time = caltool.cal_next_ts(newontime)['ts']
            else:
                next_time = time.time() + (tpl['interval'] if tpl['interval'] else 24 * 60 * 60)

            await self.db.task.mod(task['id'],
                                   disabled=False,
                                   last_success=time.time(),
                                   last_failed_count=0,
                                   success_count=task['success_count'] + 1,
                                   mtime=time.time(),
                                   next=next_time,
                                   sql_session=sql_session)

            t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            title = f"QD任务 {tpl['sitename']}-{task['note']} 成功"
            logtmp = new_env['variables'].get('__log__')
            logtmp = f"{t} \\r\\n日志：{logtmp}"

            await self.db.tpl.incr_success(tpl['id'], sql_session=sql_session)
            try:
                await self.finish('<h1 class="alert alert-success text-center">运行成功</h1><div class="showbut well autowrap" id="errmsg"><pre>%s</pre><button class="btn hljs-button" data-clipboard-target="#errmsg" >复制</button></div>' % logtmp.replace('\\r\\n', '<br>'))
            except StreamClosedError as e:
                logger_web_handler.error('stream closed error: %s', e, exc_info=config.traceback_print)

            log_day = int((await self.db.site.get(1, fields=('logDay',), sql_session=sql_session))['logDay'])
            for log in await self.db.tasklog.list(taskid=taskid, fields=('id', 'ctime'), sql_session=sql_session):
                if (time.time() - log['ctime']) > (log_day * 24 * 60 * 60):
                    await self.db.tasklog.delete(log['id'], sql_session=sql_session)
        await pushertool.pusher(user['id'], pushsw, 0x8, title, logtmp)
        return


class TaskLogHandler(BaseHandler):
    @authenticated
    async def get(self, taskid):
        # user = self.current_user
        task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'disabled')))

        tasklog = await self.db.tasklog.list(taskid=taskid, fields=('success', 'ctime', 'msg'))

        await self.render('tasklog.html', task=task, tasklog=tasklog)


class TotalLogHandler(BaseHandler):
    @authenticated
    async def get(self, userid, days):
        tasks = []
        days = int(days)
        user = self.current_user
        if userid == str(user['id']):
            for task in await self.db.task.list(userid, fields=('id', 'tplid', 'note'), limit=None):
                tpl = await self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note'))
                task['tpl'] = tpl
                for log in await self.db.tasklog.list(taskid=task['id'], fields=('id', 'success', 'ctime', 'msg')):
                    if (time.time() - log['ctime']) <= (days * 24 * 60 * 60):
                        task['log'] = log
                        tasks.append(task.copy())

            await self.render('totalLog.html', userid=userid, tasklog=tasks, days=days)
        else:
            self.evil(+5)
            raise HTTPError(401)


class TaskLogDelHandler(BaseHandler):
    @authenticated
    async def get(self, taskid):
        # user = self.current_user
        async with self.db.transaction() as sql_session:
            self.check_permission(await self.db.task.get(taskid, fields=('userid',), sql_session=sql_session))
            tasklog = await self.db.tasklog.list(taskid=taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            for log in tasklog:
                await self.db.tasklog.delete(log['id'], sql_session=sql_session)
            tasklog = await self.db.tasklog.list(taskid=taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            await self.db.task.mod(taskid,
                                   success_count=0,
                                   failed_count=0,
                                   sql_session=sql_session
                                   )

        self.redirect(f"/task/{int(taskid)}/log")
        return

    @authenticated
    async def post(self, taskid):
        # user = self.current_user
        envs = {}
        for key in self.request.body_arguments:
            envs[key] = self.get_body_arguments(key)
        body_arguments = envs
        day = 365
        if 'day' in body_arguments:
            day = int(json.loads(body_arguments['day'][0]))

        async with self.db.transaction() as sql_session:
            tasklog = await self.db.tasklog.list(taskid=taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            for log in tasklog:
                if (time.time() - log['ctime']) > (day * 24 * 60 * 60):
                    await self.db.tasklog.delete(log['id'], sql_session=sql_session)
            tasklog = await self.db.tasklog.list(taskid=taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)

        self.redirect(f"/task/{int(taskid)}/log")
        return


class TaskLogSuccessDelHandler(BaseHandler):
    @authenticated
    async def get(self, taskid):
        # user = self.current_user
        async with self.db.transaction() as sql_session:
            self.check_permission(await self.db.task.get(taskid, fields=('userid',), sql_session=sql_session))
            tasklog = await self.db.tasklog.list(taskid=taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            for log in tasklog:
                if log['success'] == 1:
                    await self.db.tasklog.delete(log['id'], sql_session=sql_session)
            tasklog = await self.db.tasklog.list(taskid=taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            await self.db.task.mod(taskid,
                                   success_count=0,
                                   sql_session=sql_session
                                   )

        self.redirect('/my/')
        return


class TaskLogFailDelHandler(BaseHandler):
    @authenticated
    async def get(self, taskid):
        # user = self.current_user
        async with self.db.transaction() as sql_session:
            self.check_permission(await self.db.task.get(taskid, fields=('userid',), sql_session=sql_session))
            tasklog = await self.db.tasklog.list(taskid=taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            for log in tasklog:
                if log['success'] == 0:
                    await self.db.tasklog.delete(log['id'], sql_session=sql_session)
            tasklog = await self.db.tasklog.list(taskid=taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            await self.db.task.mod(taskid,
                                   failed_count=0,
                                   sql_session=sql_session
                                   )

        self.redirect('/my/')
        return


class TaskDelHandler(BaseHandler):
    @authenticated
    async def post(self, taskid):
        # user = self.current_user
        async with self.db.transaction() as sql_session:
            self.check_permission(await self.db.task.get(taskid, fields=('userid',), sql_session=sql_session), 'w')
            logs = await self.db.tasklog.list(taskid=taskid, fields=('id',), sql_session=sql_session)
            for log in logs:
                await self.db.tasklog.delete(log['id'], sql_session=sql_session)
            await self.db.task.delete(taskid, sql_session=sql_session)

        self.redirect('/my/')


class TaskDisableHandler(BaseHandler):
    @authenticated
    async def post(self, taskid):
        # user = self.current_user
        async with self.db.transaction() as sql_session:
            self.check_permission(await self.db.task.get(taskid, fields=('userid',), sql_session=sql_session), 'w')
            # logs = await self.db.tasklog.list(taskid=taskid, fields=('id',), sql_session=sql_session)
            await self.db.task.mod(taskid, disabled=1, sql_session=sql_session)

        self.redirect('/my/')


class TaskSetTimeHandler(BaseHandler):
    @authenticated
    async def get(self, taskid):
        # user = self.current_user
        task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'userid',
                                                                            'tplid', 'disabled', 'note', 'ontime', 'ontimeflg', 'newontime')), 'w')

        newontime = json.loads(task['newontime'])
        ontime = newontime
        if 'mode' not in newontime:
            ontime['mode'] = 'ontime'
        else:
            ontime = newontime
        today_date = time.strftime("%Y-%m-%d", time.localtime())

        await self.render('task_setTime.html', task=task, ontime=ontime, today_date=today_date)

    @authenticated
    async def post(self, taskid):
        log = '设置成功'
        try:
            envs = {}
            for key in self.request.body_arguments:
                envs[key] = self.get_body_arguments(key)
            for key, value in envs.items():
                if value[0] == 'true' or value[0] == 'false':
                    envs[key] = True if value[0] == 'true' else False
                else:
                    envs[key] = str(value[0])

            async with self.db.transaction() as sql_session:
                if envs['sw']:
                    c = Cal()
                    if 'time' in envs:
                        if len(envs['time'].split(':')) < 3:
                            envs['time'] = envs['time'] + ':00'
                    tmp = c.cal_next_ts(envs)
                    if tmp['r'] == 'True':
                        await self.db.task.mod(taskid,
                                               disabled=False,
                                               newontime=json.dumps(envs),
                                               next=tmp['ts'],
                                               sql_session=sql_session)

                        log = f"设置成功，下次执行时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(tmp['ts']))}"
                    else:
                        raise Exception(tmp['r'])
                else:
                    tmp = json.loads((await self.db.task.get(taskid, fields=('newontime',), sql_session=sql_session))['newontime'])
                    tmp['sw'] = False
                    await self.db.task.mod(taskid, newontime=json.dumps(tmp), sql_session=sql_session)

        except Exception as e:
            logger_web_handler.error('TaskID: %s set Time failed! Reason: %s', taskid, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
            await self.render('utils_run_result.html', log=str(e), title='设置失败', flg='danger')
            return

        await self.render('utils_run_result.html', log=log, title='设置成功', flg='success')
        return


class TaskGroupHandler(BaseHandler):
    @authenticated
    async def get(self, taskid):
        user = self.current_user
        group_now = (await self.db.task.get(taskid, fields=('_groups',)))['_groups']
        _groups = []
        for task in await self.db.task.list(user['id'], fields=('_groups',), limit=None):
            if not isinstance(task['_groups'], str):
                task['_groups'] = str(task['_groups'])
            temp = task['_groups']
            if temp not in _groups:
                _groups.append(temp)

        await self.render('task_setgroup.html', taskid=taskid, _groups=_groups, groupNow=group_now)

    @authenticated
    async def post(self, taskid):
        envs = {}
        for key in self.request.body_arguments:
            envs[key] = self.get_body_arguments(key)
        new_group = envs['New_group'][0].strip()

        if new_group != "" :
            target_group = new_group
        else:
            for key, value in envs.items():
                if value[0] == 'on':
                    target_group = escape_decode(key.strip()[2:-1], "hex-escape")[0].decode('utf-8')
                    break
                else:
                    target_group = 'None'

        await self.db.task.mod(taskid, _groups=target_group)

        self.redirect('/my/')


class TasksDelHandler(BaseHandler):
    @authenticated
    async def post(self, userid):  # pylint: disable=unused-argument
        try:
            # user = self.current_user
            envs = {}
            for key in self.request.body_arguments:
                envs[key] = self.get_body_arguments(key)
            body_arguments = envs
            if 'taskids' in body_arguments:
                taskids = json.loads(envs['taskids'][0])
                async with self.db.transaction() as sql_session:
                    if body_arguments['func'][0] == 'Del':
                        for taskid in taskids:
                            self.check_permission(await self.db.task.get(taskid, fields=('id', 'userid', ), sql_session=sql_session), 'w')
                            logs = await self.db.tasklog.list(taskid=taskid, fields=('id',), sql_session=sql_session)
                            for log in logs:
                                await self.db.tasklog.delete(log['id'], sql_session=sql_session)
                            await self.db.task.delete(taskid, sql_session=sql_session)
                    elif body_arguments['func'][0] == 'setGroup':
                        new_group = body_arguments['groupValue'][0].strip()
                        if new_group == '':
                            new_group = 'None'
                        for taskid in taskids:
                            await self.db.task.mod(taskid, groups=new_group, sql_session=sql_session)

                await self.finish('<h1 class="alert alert-success text-center">操作成功</h1>')
            raise Exception('taskids not found!')
        except Exception as e:
            logger_web_handler.error('TaskID: %s delete failed! Reason: %s', taskid, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
            await self.render('tpl_run_failed.html', log=str(e))
            return


class GetGroupHandler(BaseHandler):
    @authenticated
    async def get(self, taskid):  # pylint: disable=unused-argument
        user = self.current_user
        _groups = {}
        for task in await self.db.task.list(user['id'], fields=('_groups',), limit=None):
            _groups[task['_groups']] = ""

        self.write(json.dumps(_groups, ensure_ascii=False, indent=4))
        return


handlers = [
    (r'/task/new', TaskNewHandler),
    (r'/task/(\d+)/edit', TaskEditHandler),
    (r'/task/(\d+)/settime', TaskSetTimeHandler),
    (r'/task/(\d+)/del', TaskDelHandler),
    (r'/task/(\d+)/disable', TaskDisableHandler),
    (r'/task/(\d+)/log', TaskLogHandler),
    (r'/task/(\d+)/log/total/(\d+)', TotalLogHandler),
    (r'/task/(\d+)/log/del', TaskLogDelHandler),
    (r'/task/(\d+)/log/del/Success', TaskLogSuccessDelHandler),
    (r'/task/(\d+)/log/del/Fail', TaskLogFailDelHandler),
    (r'/task/(\d+)/run', TaskRunHandler),
    (r'/task/(\d+)/group', TaskGroupHandler),
    (r'/tasks/(\d+)', TasksDelHandler),
    (r'/getgroups/(\d+)', GetGroupHandler),
]
