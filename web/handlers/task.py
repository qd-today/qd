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

from .base import *
from libs import utils
from libs.parse_url import parse_url
from libs.funcs import pusher
from libs.funcs import cal
from codecs import escape_decode
class TaskNewHandler(BaseHandler):    
    async def get(self):
        user = self.current_user
        tplid = self.get_argument('tplid', None)
        fields = ('id', 'sitename', 'success_count')

        tpls = []
        if user:
            tpls += sorted(await self.db.tpl.list(userid=user['id'], fields=fields, limit=None), key=lambda t: -t['id'])
        if tpls:
            tpls.append({'id': 0, 'sitename': u'-----公开模板-----'})
        tpls += sorted(await self.db.tpl.list(userid=None, public=1, fields=fields, limit=None), key=lambda t: -t['success_count'])

        if not tplid:
            for tpl in tpls:
                if tpl.get('id'):
                    tplid = tpl['id']
                    break
        if tplid:
            tplid = int(tplid)

            tpl = self.check_permission(await self.db.tpl.get(tplid, fields=('id', 'userid', 'note', 'sitename', 'siteurl', 'variables')))
            variables = json.loads(tpl['variables'])

            _groups = []
            if user:
                for task in await self.db.task.list(user['id'], fields=('_groups',), limit=None):
                    if not isinstance(task['_groups'], str):
                        task['_groups'] = str(task['_groups'])
                    temp = task['_groups']
                    if (temp not  in _groups):
                        _groups.append(temp)
            
            await self.render('task_new.html', tpls=tpls, tplid=tplid, tpl=tpl, variables=variables, task={}, _groups=_groups, init_env=tpl['variables'])
        else:
            await self.render('utils_run_result.html', log=u'请先添加模板！', title=u'设置失败', flg='danger')

    @tornado.web.authenticated
    async def post(self, taskid=None):
        user = self.current_user
        tplid = int(self.get_body_argument('_binux_tplid'))
        tested = self.get_body_argument('_binux_tested', False)
        note = self.get_body_argument('_binux_note')
        proxy = self.get_body_argument('_binux_proxy')
        retry_count = self.get_body_argument('_binux_retry_count')
        retry_interval = self.get_body_argument('_binux_retry_interval')

        async with self.db.transaction() as sql_session:
            tpl = self.check_permission(await self.db.tpl.get(tplid, fields=('id', 'userid', 'interval'),sql_session=sql_session))
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

            if ('New_group' in envs):
                New_group = envs['New_group'][0].strip()
                
                if New_group != "" :
                    target_group = New_group
                else:
                    for value in envs:
                        if envs[value][0] == 'on':
                            if (value.find("group-select-") > -1):
                                target_group = escape_decode(value.replace("group-select-", "").strip()[2:-1], "hex-escape")[0].decode('utf-8')
                                break
                        else:
                            target_group = 'None'

            if not taskid:
                env = await self.db.user.encrypt(user['id'], env, sql_session=sql_session)
                taskid = await self.db.task.add(tplid, user['id'], env, sql_session=sql_session)

                if tested:
                    await self.db.task.mod(taskid, note=note, next=time.time() + (tpl['interval'] or 24*60*60), sql_session=sql_session)
                else:
                    await self.db.task.mod(taskid, note=note, next=time.time() + config.new_task_delay, sql_session=sql_session)
            else:
                task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'userid', 'init_env'), sql_session=sql_session), 'w')

                init_env = await self.db.user.decrypt(user['id'], task['init_env'], sql_session=sql_session)
                init_env.update(env)
                init_env = await self.db.user.encrypt(user['id'], init_env, sql_session=sql_session)
                await self.db.task.mod(taskid, init_env=init_env, env=None, session=None, note=note, sql_session=sql_session)
            
            if 'New_group' in envs:
                await self.db.task.mod(taskid, _groups=target_group, sql_session=sql_session)

            if isinstance(retry_count, int) and -1 <= retry_count <= 8:
                await self.db.task.mod(taskid, retry_count=retry_count, sql_session=sql_session)

            if retry_interval:
                await self.db.task.mod(taskid, retry_interval=retry_interval, sql_session=sql_session)

        self.redirect('/my/')

class TaskEditHandler(TaskNewHandler):
    @tornado.web.authenticated
    async def get(self, taskid):
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
            init_env.append({'name':var, 'value':value})

        proxy = task['init_env']['_proxy'] if '_proxy' in task['init_env'] else ''

        await self.render('task_new.html', tpls=[tpl, ], tplid=tpl['id'], tpl=tpl, variables=variables, task=task, init_env=init_env, proxy=proxy, retry_count=task['retry_count'], retry_interval=task['retry_interval'])

class TaskRunHandler(BaseHandler):
    @tornado.web.authenticated
    async def post(self, taskid):
        self.evil(+2)
        start_ts = int(time.time())
        user = self.current_user
        async with self.db.transaction() as sql_session:
            task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'init_env',
                'env', 'session', 'retry_count', 'retry_interval', 'last_success', 'last_failed', 'success_count', 'note',
                'failed_count', 'last_failed_count', 'next', 'disabled', 'ontime', 'ontimeflg', 'pushsw','newontime'), sql_session=sql_session), 'w')

            tpl = self.check_permission(await self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename',
                'siteurl', 'tpl', 'interval', 'last_success'),sql_session=sql_session))

            fetch_tpl = await self.db.user.decrypt(
                    0 if not tpl['userid'] else task['userid'], tpl['tpl'], sql_session=sql_session)
            env = dict(
                    variables = await self.db.user.decrypt(task['userid'], task['init_env'], sql_session=sql_session),
                    session = [],
                    )
            
            pushsw = json.loads(task['pushsw'])
            newontime = json.loads(task['newontime'])
            pushertool = pusher(self.db, sql_session=sql_session)
            caltool = cal()

            try:
                url = parse_url(env['variables'].get('_proxy'))
                if not url:
                    new_env = await self.fetcher.do_fetch(fetch_tpl, env)
                else:
                    proxy = {
                        'scheme': url['scheme'],
                        'host': url['host'],
                        'port': url['port'],
                        'username': url['username'],
                        'password': url['password']
                    }
                    new_env = await self.fetcher.do_fetch(fetch_tpl, env, [proxy])
            except Exception as e:
                logger_Web_Handler.error('taskid:%d tplid:%d failed! %.4fs \r\n%s', task['id'], task['tplid'], time.time()-start_ts, str(e).replace('\\r\\n','\r\n'))
                t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                title = u"签到任务 {0}-{1} 失败".format(tpl['sitename'], task['note'])
                logtmp = u"{0} \\r\\n日志：{1}".format(t, e)

                await self.db.tasklog.add(task['id'], success=False, msg=str(e), sql_session=sql_session)
                await self.db.task.mod(task['id'],
                        last_failed=time.time(),
                        failed_count=task['failed_count']+1,
                        last_failed_count=task['last_failed_count']+1,
                        sql_session=sql_session
                        )
                await self.finish('<h1 class="alert alert-danger text-center">签到失败</h1><div class="showbut well autowrap" id="errmsg">%s<button class="btn hljs-button" data-clipboard-target="#errmsg" >复制</button></div>' % logtmp.replace('\\r\\n', '<br>'))

                await pushertool.pusher(user['id'], pushsw, 0x4, title, logtmp)
                return

            await self.db.tasklog.add(task['id'], success=True, msg=new_env['variables'].get('__log__'), sql_session=sql_session)
            if (newontime["sw"]):
                if ('mode' not in newontime):
                    newontime['mode'] = 'ontime'

                if (newontime['mode'] == 'ontime'):
                    newontime['date'] = (datetime.datetime.now()+datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                nextTime = caltool.calNextTs(newontime)['ts']
            else:
                nextTime = time.time() + (tpl['interval'] if tpl['interval'] else 24 * 60 * 60)
                
            await self.db.task.mod(task['id'],
                    disabled = False,
                    last_success = time.time(),
                    last_failed_count = 0,
                    success_count = task['success_count'] + 1,
                    mtime = time.time(),
                    next = nextTime,
                    sql_session=sql_session)
            
            t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            title = u"签到任务 {0}-{1} 成功".format(tpl['sitename'], task['note'])
            logtmp = new_env['variables'].get('__log__')
            logtmp = u"{0} \\r\\n日志：{1}".format(t, logtmp)

            await self.db.tpl.incr_success(tpl['id'],sql_session=sql_session)
            await self.finish('<h1 class="alert alert-success text-center">签到成功</h1><div class="showbut well autowrap" id="errmsg"><pre>%s</pre><button class="btn hljs-button" data-clipboard-target="#errmsg" >复制</button></div>' % logtmp.replace('\\r\\n', '<br>'))
            
            await pushertool.pusher(user['id'], pushsw, 0x8, title, logtmp)
            logDay = int((await self.db.site.get(1, fields=('logDay',),sql_session=sql_session))['logDay'])
            for log in await self.db.tasklog.list(taskid = taskid, fields=('id', 'ctime'), sql_session=sql_session):
                if (time.time() - log['ctime']) > (logDay * 24 * 60 * 60):
                    await self.db.tasklog.delete(log['id'], sql_session=sql_session)
        return

class TaskLogHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self, taskid):
        user = self.current_user
        task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'disabled')))

        tasklog = await self.db.tasklog.list(taskid = taskid, fields=('success', 'ctime', 'msg'))

        await self.render('tasklog.html', task=task, tasklog=tasklog)

class TotalLogHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self, userid, days):
        tasks = []
        days = int(days)
        user = self.current_user
        if userid == str(user['id']):
            for task in await self.db.task.list(userid, fields=('id', 'tplid', 'note'), limit=None):
                tpl = await self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note') )
                task['tpl'] = tpl
                for log in await self.db.tasklog.list(taskid = task['id'], fields=('id','success', 'ctime', 'msg')):
                    if (time.time() - log['ctime']) <= (days * 24 * 60 * 60):
                        task['log'] = log
                        tasks.append(task.copy())

            await self.render('totalLog.html', userid=userid, tasklog=tasks, days=days)
        else:
            self.evil(+5)
            raise HTTPError(401)

class TaskLogDelHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self, taskid):
        user = self.current_user
        async with self.db.transaction() as sql_session:
            task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'disabled'), sql_session=sql_session))
            tasklog = await self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            for log in tasklog:
                await self.db.tasklog.delete(log['id'], sql_session=sql_session)
            tasklog = await self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            await self.db.task.mod(taskid,
                        success_count=0,
                        failed_count=0,
                        sql_session=sql_session
                        )

        self.redirect("/task/{0}/log".format(taskid))
        return

    @tornado.web.authenticated
    async def post(self, taskid):
        user = self.current_user
        envs = {}
        for key in self.request.body_arguments:
            envs[key] = self.get_body_arguments(key)
        body_arguments = envs
        day = 365
        if ('day' in body_arguments):
            day = int(json.loads(body_arguments['day'][0]))
        
        async with self.db.transaction() as sql_session:
            tasklog = await self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            for log in tasklog:
                if (time.time() - log['ctime']) > (day * 24 * 60 * 60):
                    await self.db.tasklog.delete(log['id'], sql_session=sql_session)
            tasklog = await self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)

        self.redirect("/task/{0}/log".format(taskid))
        return

class TaskLogSuccessDelHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self, taskid):
        user = self.current_user
        async with self.db.transaction() as sql_session:
            task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'disabled'), sql_session=sql_session))
            tasklog = await self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            for log in tasklog:
                if log['success'] == 1:
                    await self.db.tasklog.delete(log['id'], sql_session=sql_session)
            tasklog = await self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            await self.db.task.mod(taskid,
                        success_count=0,
                        sql_session=sql_session
                        )

        referer = self.request.headers.get('referer', '/my/')
        self.redirect(referer)
        return

class TaskLogFailDelHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self, taskid):
        user = self.current_user
        async with self.db.transaction() as sql_session:
            task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'tplid', 'userid', 'disabled'), sql_session=sql_session))
            tasklog = await self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            for log in tasklog:
                if log['success'] == 0:
                    await self.db.tasklog.delete(log['id'], sql_session=sql_session)
            tasklog = await self.db.tasklog.list(taskid = taskid, fields=('id', 'success', 'ctime', 'msg'), sql_session=sql_session)
            await self.db.task.mod(taskid,
                        failed_count=0,
                        sql_session=sql_session
                        )

        referer = self.request.headers.get('referer', '/my/')
        self.redirect(referer)
        return

class TaskDelHandler(BaseHandler):
    @tornado.web.authenticated
    async def post(self, taskid):
        user = self.current_user
        async with self.db.transaction() as sql_session:
            task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'userid', ), sql_session=sql_session), 'w')
            logs = await self.db.tasklog.list(taskid = taskid, fields=('id',), sql_session=sql_session)
            for log in logs:
                await self.db.tasklog.delete(log['id'], sql_session=sql_session)
            await self.db.task.delete(task['id'], sql_session=sql_session)
            
        referer = self.request.headers.get('referer', '/my/')
        self.redirect(referer)

class TaskDisableHandler(BaseHandler):
    @tornado.web.authenticated
    async def post(self, taskid):
        user = self.current_user
        async with self.db.transaction() as sql_session:
            task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'userid', ),sql_session=sql_session), 'w')
            logs = await self.db.tasklog.list(taskid = taskid, fields=('id',),sql_session=sql_session)
            await self.db.task.mod(task['id'], disabled=1, sql_session=sql_session)
            
        referer = self.request.headers.get('referer', '/my/')
        self.redirect(referer)
        
class TaskSetTimeHandler(TaskNewHandler):
    @tornado.web.authenticated
    async def get(self, taskid):
        user = self.current_user
        task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'userid',
            'tplid', 'disabled', 'note', 'ontime', 'ontimeflg', 'newontime')), 'w')
        
        newontime = json.loads(task['newontime'])
        ontime = newontime
        if ('mode' not in newontime):
            ontime['mode'] = 'ontime'
        else:
            ontime = newontime
        today_date = time.strftime("%Y-%m-%d",time.localtime())

        await self.render('task_setTime.html', task=task, ontime=ontime, today_date=today_date)
    
    @tornado.web.authenticated
    async def post(self, taskid):
        log = u'设置成功'
        try:
            envs = {}
            for key in self.request.body_arguments:
                envs[key] = self.get_body_arguments(key)
            for env in envs.keys():
                if (envs[env][0] == u'true' or envs[env][0] == u'false'):
                    envs[env] = True if envs[env][0] == u'true' else False
                else:
                    envs[env] = u'{0}'.format(envs[env][0])
            
            async with self.db.transaction() as sql_session:
                if (envs['sw']):
                    c = cal()
                    if ('time' in envs):
                        if (len(envs['time'].split(':')) < 3):
                            envs['time'] = envs['time'] + ':00'
                    tmp = c.calNextTs(envs)
                    if (tmp['r'] == 'True'):
                        await self.db.task.mod(taskid,
                            disabled = False,
                            newontime = json.dumps(envs),
                            next = tmp['ts'],
                            sql_session=sql_session)

                        log = u'设置成功，下次执行时间：{0}'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tmp['ts'])))
                    else:
                        raise Exception(tmp['r'])
                else:
                    tmp = json.loads((await self.db.task.get(taskid, fields=('newontime',), sql_session=sql_session))['newontime'])
                    tmp['sw'] = False
                    await self.db.task.mod(taskid, newontime = json.dumps(tmp), sql_session=sql_session)

        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            await self.render('utils_run_result.html', log=str(e), title=u'设置失败', flg='danger')
            logger_Web_Handler.error('TaskID: %s set Time failed! Reason: %s', taskid, str(e).replace('\\r\\n','\r\n'))
            return

        await self.render('utils_run_result.html', log=log, title=u'设置成功', flg='success')
        return
        
class TaskGroupHandler(TaskNewHandler):
    @tornado.web.authenticated
    async def get(self, taskid):
        user = self.current_user      
        groupNow = (await self.db.task.get(taskid, fields=('_groups',)))['_groups']
        _groups = []
        for task in await self.db.task.list(user['id'], fields=('_groups',), limit=None):
            if not isinstance(task['_groups'], str):
                task['_groups'] = str(task['_groups'])
            temp = task['_groups']
            if (temp not  in _groups):
                _groups.append(temp)

        await self.render('task_setgroup.html', taskid=taskid, _groups=_groups, groupNow=groupNow)
    
    @tornado.web.authenticated
    async def post(self, taskid):        
        envs = {}
        for key in self.request.body_arguments:
            envs[key] = self.get_body_arguments(key)
        New_group = envs['New_group'][0].strip()
        
        if New_group != "" :
            target_group = New_group
        else:
            for value in envs:
                if envs[value][0] == 'on':
                    target_group = escape_decode(value.strip()[2:-1],"hex-escape")[0].decode('utf-8')
                    break
                else:
                    target_group = 'None'
            
        await self.db.task.mod(taskid, _groups=target_group)

        self.redirect('/my/')
        
class TasksDelHandler(BaseHandler):
    @tornado.web.authenticated
    async def post(self, userid):
        try:
            user = self.current_user
            envs = {}
            for key in self.request.body_arguments:
                envs[key] = self.get_body_arguments(key)
            body_arguments = envs
            if ('taskids' in body_arguments):
                taskids = json.loads(envs['taskids'][0])
            async with self.db.transaction() as sql_session:
                if (body_arguments['func'][0] == 'Del'):
                    for taskid in taskids:
                        task = self.check_permission(await self.db.task.get(taskid, fields=('id', 'userid', ),sql_session=sql_session), 'w')
                        logs = await self.db.tasklog.list(taskid = taskid, fields=('id',),sql_session=sql_session)
                        for log in logs:
                            await self.db.tasklog.delete(log['id'], sql_session=sql_session)
                        await self.db.task.delete(taskid, sql_session=sql_session)
                elif (body_arguments['func'][0] == 'setGroup'):
                    New_group = body_arguments['groupValue'][0].strip()
                    if(New_group == ''):
                        New_group = u'None'
                    for taskid in taskids:
                        await self.db.task.mod(taskid, groups=New_group, sql_session=sql_session)
                    
            await self.finish('<h1 class="alert alert-success text-center">操作成功</h1>')
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            await self.render('tpl_run_failed.html', log=str(e))
            logger_Web_Handler.error('TaskID: %s delete failed! Reason: %s', taskid, str(e).replace('\\r\\n','\r\n'))
            return

class GetGroupHandler(TaskNewHandler):
    @tornado.web.authenticated
    async def get(self, taskid):
        user = self.current_user      
        _groups = {}
        for task in await self.db.task.list(user['id'], fields=('_groups',), limit=None):
            _groups[task['_groups']] = ""
        
        self.write(json.dumps(_groups, ensure_ascii=False, indent=4))
        return

handlers = [
        ('/task/new', TaskNewHandler),
        ('/task/(\d+)/edit', TaskEditHandler),
        ('/task/(\d+)/settime', TaskSetTimeHandler),
        ('/task/(\d+)/del', TaskDelHandler), 
        ('/task/(\d+)/disable', TaskDisableHandler),
        ('/task/(\d+)/log', TaskLogHandler),
        ('/task/(\d+)/log/total/(\d+)', TotalLogHandler),
        ('/task/(\d+)/log/del', TaskLogDelHandler),
        ('/task/(\d+)/log/del/Success', TaskLogSuccessDelHandler),
        ('/task/(\d+)/log/del/Fail', TaskLogFailDelHandler),
        ('/task/(\d+)/run', TaskRunHandler),
        ('/task/(\d+)/group', TaskGroupHandler),
        ('/tasks/(\d+)', TasksDelHandler), 
        ('/getgroups/(\d+)', GetGroupHandler), 
        ]
