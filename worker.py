# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 14:43:13

import asyncio
import datetime
import json
import time
import traceback
from typing import Dict

import tornado.ioloop
import tornado.log
from tornado import gen
from tornado.concurrent import Future

import config
from db import DB
from libs.fetcher import Fetcher
from libs.funcs import Cal, Pusher
from libs.log import Log
from libs.parse_url import parse_url

logger_worker = Log('QD.Worker').getlogger()


class BaseWorker:
    def __init__(self, db: DB):
        self.running = False
        self.db = db
        self.fetcher = Fetcher()

    async def clear_log(self, taskid, sql_session=None):
        log_day = int(
            (await self.db.site.get(
                1,
                fields=('logDay',),
                sql_session=sql_session
            ))['logDay']
        )
        for log in await self.db.tasklog.list(
            taskid=taskid,
            fields=('id', 'ctime'),
            sql_session=sql_session
        ):
            if (time.time() - log['ctime']) > (log_day * 24 * 60 * 60):
                await self.db.tasklog.delete(
                    log['id'],
                    sql_session=sql_session
                )

    async def push_batch(self):
        try:
            async with self.db.transaction() as sql_session:
                userlist = await self.db.user.list(
                    fields=('id', 'email', 'status', 'push_batch'),
                    sql_session=sql_session
                )
                pushtool = Pusher(self.db, sql_session=sql_session)
                if userlist:
                    for user in userlist:
                        userid = user['id']
                        push_batch = json.loads(user['push_batch'])
                        if user['status'] == "Enable" and push_batch.get('sw') and isinstance(push_batch.get('time'), (float, int)) and time.time() >= push_batch['time']:  # noqa: E501
                            logger_worker.debug(
                                'User %d check push_batch task, waiting...',
                                userid
                            )
                            title = "QD任务日志定期推送"
                            delta = push_batch.get("delta", 86400)
                            logtemp = time.strftime(
                                "%Y-%m-%d %H:%M:%S", time.localtime(push_batch['time']))
                            tmpdict = {}
                            tmp = ""
                            numlog = 0
                            task_list = await self.db.task.list(
                                userid=userid,
                                fields=(
                                    'id', 'tplid', 'note', 'disabled',
                                    'last_success', 'last_failed', 'pushsw'
                                ),
                                sql_session=sql_session
                            )
                            for task in task_list:
                                pushsw = json.loads(task['pushsw'])
                                if pushsw["pushen"] and (task["disabled"] == 0 or (task.get("last_success", 0) and task.get("last_success", 0) >= push_batch['time'] - delta) or (task.get("last_failed", 0) and task.get("last_failed", 0) >= push_batch['time'] - delta)):
                                    tmp0 = ""
                                    tasklog_list = await self.db.tasklog.list(taskid=task["id"], fields=('success', 'ctime', 'msg'), sql_session=sql_session)
                                    for log in tasklog_list:
                                        if (push_batch['time'] - delta) < log['ctime'] <= push_batch['time']:
                                            c_time = time.strftime(
                                                "%Y-%m-%d %H:%M:%S", time.localtime(log['ctime']))
                                            tmp0 += f"\\r\\n时间: {c_time}\\r\\n日志: {log['msg']}"
                                            numlog += 1
                                    tmplist = tmpdict.get(task['tplid'], [])
                                    if tmp0:
                                        tmplist.append(
                                            f"\\r\\n-----任务{len(tmplist) + 1}-{task['note']}-----{tmp0}\\r\\n")
                                    else:
                                        tmplist.append(
                                            f"\\r\\n-----任务{len(tmplist) + 1}-{task['note']}-----\\r\\n记录期间未执行定时任务，请检查任务! \\r\\n")
                                    tmpdict[task['tplid']] = tmplist

                            for tmpkey, tmpval in tmpdict.items():
                                tmp_sitename = await self.db.tpl.get(tmpkey, fields=('sitename',), sql_session=sql_session)
                                if tmp_sitename:
                                    tmp = f"\\r\\n\\r\\n=====QD: {tmp_sitename['sitename']}====="
                                    tmp += ''.join(tmpval)
                                    logtemp += tmp
                            push_batch["time"] = push_batch['time'] + delta
                            if tmp and numlog:
                                user_email = user.get('email', 'Unkown')
                                logger_worker.debug(
                                    "Start push batch log for user %s, email:%s", userid, user_email)
                                await pushtool.pusher(userid, {"pushen": bool(push_batch.get("sw", False))}, 4080, title, logtemp)
                                logger_worker.info(
                                    "Complete push batch log for user %s, email:%s", userid, user_email)
                            else:
                                logger_worker.debug(
                                    'User %s does not need to perform push_batch task, stop.', userid)
                            await self.db.user.mod(userid, push_batch=json.dumps(push_batch), sql_session=sql_session)
        except Exception as e:
            logger_worker.error('Push batch task failed: %s', e, exc_info=config.traceback_print)

    @staticmethod
    def failed_count_to_time(last_failed_count, retry_count=config.task_max_retry_count, retry_interval=None, interval=None):
        next = None
        if last_failed_count < retry_count or retry_count == -1:
            if retry_interval:
                next = retry_interval
            else:
                if last_failed_count == 0:
                    next = 10 * 60
                elif last_failed_count == 1:
                    next = 110 * 60
                elif last_failed_count == 2:
                    next = 4 * 60 * 60
                elif last_failed_count == 3:
                    next = 6 * 60 * 60
                elif last_failed_count < retry_count or retry_count == -1:
                    next = 11 * 60 * 60
                else:
                    next = None
        elif retry_count == 0:
            next = None

        if next and not retry_interval:
            if interval is None:
                interval = 12 * 60 * 60
            next = min(next, interval)
        return next

    @staticmethod
    def fix_next_time(next: float, gmt_offset=time.timezone / 60) -> float:
        """
        fix next time to 2:00 - 21:00 (local time), while tpl interval is unset.

        Args:
            next (float): next timestamp
            gmt_offset (float, optional): gmt offset in minutes. Defaults to time.timezone/60.

        Returns:
            next (float): fixed next timestamp
        """
        date = datetime.datetime.utcfromtimestamp(next)
        local_date = date - datetime.timedelta(minutes=gmt_offset)
        if local_date.hour < 2:
            next += 2 * 60 * 60
        if local_date.hour > 21:
            next -= 3 * 60 * 60
        return next

    async def do(self, task):
        is_success = False
        should_push = 0
        userid = None
        title = f"QD 定时任务ID {task['id']}-{task.get('note',None)} 完成"
        content = ""
        pushsw = json.loads(task['pushsw'])
        async with self.db.transaction() as sql_session:
            user = await self.db.user.get(task['userid'], fields=('id', 'email', 'email_verified', 'nickname', 'logtime'), sql_session=sql_session)
            userid = user['id']
            if not user:
                await self.db.tasklog.add(task['id'], False, msg='no such user, disabled.', sql_session=sql_session)
                await self.db.task.mod(task['id'], next=None, disabled=1, sql_session=sql_session)
                return False

            tpl = await self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'tpl', 'interval', 'last_success'), sql_session=sql_session)
            if not tpl:
                await self.db.tasklog.add(task['id'], False, msg='tpl missing, task disabled.', sql_session=sql_session)
                await self.db.task.mod(task['id'], next=None, disabled=1, sql_session=sql_session)
                return False

            if task['disabled']:
                await self.db.tasklog.add(task['id'], False, msg='task disabled.', sql_session=sql_session)
                await self.db.task.mod(task['id'], next=None, disabled=1, sql_session=sql_session)
                return False

            if tpl['userid'] and tpl['userid'] != user['id']:
                await self.db.tasklog.add(task['id'], False, msg='no permission error, task disabled.', sql_session=sql_session)
                await self.db.task.mod(task['id'], next=None, disabled=1, sql_session=sql_session)
                return False

            start = time.perf_counter()
            try:
                fetch_tpl = await self.db.user.decrypt(0 if not tpl['userid'] else task['userid'], tpl['tpl'], sql_session=sql_session)
                env = dict(
                    variables=await self.db.user.decrypt(task['userid'], task['init_env'], sql_session=sql_session),
                    session=[],
                )

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

                variables = await self.db.user.encrypt(task['userid'], new_env['variables'], sql_session=sql_session)
                session = await self.db.user.encrypt(task['userid'],
                                                     new_env['session'].to_json() if hasattr(new_env['session'], 'to_json') else new_env['session'], sql_session=sql_session)

                newontime = json.loads(task["newontime"])
                caltool = Cal()
                if newontime['sw']:
                    if 'mode' not in newontime:
                        newontime['mode'] = 'ontime'
                    if newontime['mode'] == 'ontime':
                        newontime['date'] = (datetime.datetime.now(
                        ) + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                    next = caltool.cal_next_ts(newontime)['ts']
                else:
                    next = time.time() + \
                        max((tpl['interval'] if tpl['interval']
                            else 24 * 60 * 60), 1 * 60)
                    if tpl['interval'] is None:
                        next = self.fix_next_time(next)

                # success feedback
                await self.db.tasklog.add(task['id'], success=True, msg=new_env['variables'].get('__log__'), sql_session=sql_session)
                await self.db.task.mod(task['id'],
                                       last_success=time.time(),
                                       last_failed_count=0,
                                       success_count=task['success_count'] + 1,
                                       env=variables,
                                       session=session,
                                       mtime=time.time(),
                                       next=next,
                                       sql_session=sql_session)

                t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                title = f"QD定时任务 {tpl['sitename']}-{task['note']} 成功"
                content = new_env['variables'].get('__log__')
                content = f"{t} \\r\\n日志：{content}"
                should_push = 0x2

                logger_worker.info('taskid:%d tplid:%d successed! %.5fs',
                                   task['id'], task['tplid'], time.perf_counter() - start)
                # delete log
                await self.clear_log(task['id'], sql_session=sql_session)
                logger_worker.info(
                    'taskid:%d tplid:%d clear log.', task['id'], task['tplid'])
                is_success = True
            except Exception as e:
                # failed feedback
                if config.traceback_print:
                    traceback.print_exc()
                next_time_delta = self.failed_count_to_time(
                    task['last_failed_count'], task['retry_count'], task['retry_interval'], tpl['interval'])

                t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                title = f"QD定时任务 {tpl['sitename']}-{task['note']} 失败"
                content = f"{t} \\r\\n日志：{e}"
                disabled = False
                if next_time_delta:
                    next = time.time() + next_time_delta
                    content = content + \
                        f" \\r\\n下次运行时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next))}"
                    logtime = json.loads(user['logtime'])
                    if 'ErrTolerateCnt' not in logtime:
                        logtime['ErrTolerateCnt'] = 0
                    if logtime['ErrTolerateCnt'] <= task['last_failed_count']:
                        should_push = 0x1
                else:
                    disabled = True
                    next = None
                    content = " \\r\\n任务已禁用"
                    should_push = 0x1

                await self.db.tasklog.add(task['id'], success=False, msg=str(e), sql_session=sql_session)
                await self.db.task.mod(task['id'],
                                       last_failed=time.time(),
                                       failed_count=task['failed_count'] + 1,
                                       last_failed_count=task['last_failed_count'] + 1,
                                       disabled=disabled,
                                       mtime=time.time(),
                                       next=next,
                                       sql_session=sql_session)

                logger_worker.error('taskid:%d tplid:%d failed! %.4fs \r\n%s', task['id'], task['tplid'], time.perf_counter(
                ) - start, str(e).replace('\\r\\n', '\r\n'))

        async with self.db.transaction() as sql_session:
            if tpl and tpl.get('id'):
                if is_success:
                    await self.db.tpl.incr_success(tpl['id'], sql_session=sql_session)
                else:
                    await self.db.tpl.incr_failed(tpl['id'], sql_session=sql_session)

        if should_push:
            try:
                pushtool = Pusher(self.db, sql_session=sql_session)
                await pushtool.pusher(userid, pushsw, should_push, title, content)
            except Exception as e:
                logger_worker.error('taskid:%d push failed! %s', task['id'], str(e), exc_info=config.traceback_print)
        return is_success


class QueueWorker(BaseWorker):
    def __init__(self, db: DB):
        logger_worker.info('Queue Worker start...')
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=config.queue_num)
        self.task_lock: Dict = {}
        self.success = 0
        self.failed = 0
        super().__init__(db)

    async def __call__(self):

        asyncio.create_task(self.producer())
        for i in range(config.queue_num):
            asyncio.create_task(self.runner(i))

        while True:
            sleep = asyncio.sleep(config.push_batch_delta)
            if self.success or self.failed:
                logger_worker.info('Last %d seconds, %d task done. %d success, %d failed' ,
                                   config.push_batch_delta, self.success + self.failed, self.success, self.failed)
                self.success = 0
                self.failed = 0
            if config.push_batch_sw:
                await self.push_batch()
            await sleep

    async def runner(self, id):
        logger_worker.debug('Runner %d started' , id)
        while True:
            sleep = asyncio.sleep(config.check_task_loop / 1000.0)
            task = await self.queue.get()
            logger_worker.debug(
                'Runner %d get task: %s, running...' , id, task['id'])
            done = False
            try:
                done = await self.do(task)
            except Exception as e:
                logger_worker.error(
                    'Runner %d get task: %s, failed! %s' , id, task['id'], str(e), exc_info=config.traceback_print)
            if done:
                self.success += 1
                self.task_lock.pop(task['id'], None)
            else:
                self.failed += 1
                self.task_lock[task['id']] = False
            self.queue.task_done()
            await sleep

    async def producer(self):
        logger_worker.debug('Schedule Producer started')
        while True:
            sleep = asyncio.sleep(config.check_task_loop / 1000.0)
            try:
                tasks = await self.db.task.scan()
                unlock_tasks = 0
                if tasks is not None and len(tasks) > 0:
                    for task in tasks:
                        if not self.task_lock.get(task['id'], False):
                            self.task_lock[task['id']] = True
                            unlock_tasks += 1
                            await self.queue.put(task)
                    if unlock_tasks > 0:
                        logger_worker.debug(
                            'Scaned %d task, put in Queue...', unlock_tasks)
            except Exception as e:
                logger_worker.error(
                    'Schedule Producer get tasks failed! %s', e, exc_info=config.traceback_print)
            await sleep

# 旧版本批量任务定时执行
# 建议仅当新版 Queue 生产者消费者定时执行功能失效时使用


class BatchWorker(BaseWorker):
    def __init__(self, db: DB):
        logger_worker.info('Batch Worker start...')
        super().__init__(db)
        self.running = False

    def __call__(self):
        # self.running = tornado.ioloop.IOLoop.current().spawn_callback(self.run)
        # if self.running:
        #     success, failed = self.running
        #     if success or failed:
        #         logger_worker.info('%d task done. %d success, %d failed' % (success+failed, success, failed))
        if not self.running:
            self.running = gen.convert_yielded(self.run())

        def done(future: Future):
            self.running = False
            success, failed = future.result()
            if success or failed:
                logger_worker.info('%d task done. %d success, %d failed' ,
                                   success + failed, success, failed)
        self.running.add_done_callback(done)

    async def run(self):
        running = []
        success = 0
        failed = 0
        try:
            tasks = await self.db.task.scan()
            if tasks is not None and len(tasks) > 0:
                for task in tasks:
                    running.append(asyncio.ensure_future(self.do(task)))
                    if len(running) >= 50:
                        logger_worker.debug(
                            'scaned %d task, waiting...', len(running))
                        result = await asyncio.gather(*running[:10])
                        for each in result:
                            if each:
                                success += 1
                            else:
                                failed += 1
                        running = running[10:]
                logger_worker.debug('scaned %d task, waiting...', len(running))
                result = await asyncio.gather(*running)
                for each in result:
                    if each:
                        success += 1
                    else:
                        failed += 1
            if config.push_batch_sw:
                await self.push_batch()
        except Exception as e:
            logger_worker.exception(e)
        return (success, failed)


if __name__ == '__main__':
    tornado.log.enable_pretty_logging()
    io_loop = tornado.ioloop.IOLoop.instance()
    if config.worker_method.upper() == 'QUEUE':
        queue_worker = QueueWorker(DB())
        io_loop.add_callback(queue_worker)
    elif config.worker_method.upper() == 'BATCH':
        batch_worker = BatchWorker(DB())
        tornado.ioloop.PeriodicCallback(batch_worker, config.check_task_loop).start()
        # worker()
    else:
        raise RuntimeError('Worker_method must be Queue or Batch')

    io_loop.start()
