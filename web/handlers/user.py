#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 11:39:25
# pylint: disable=broad-exception-raised

import base64
import datetime
import json
import os
import re
import sqlite3
import time
import traceback

from Crypto.Hash import MD5
from tornado import gen, iostream
from tornado.web import authenticated

import config
from libs import mcrypto as crypto
from libs.funcs import Pusher
from web.handlers.base import BaseHandler, logger_web_handler

try:
    import aiofiles
    AIO_IMPORT = True
except ImportError:
    AIO_IMPORT = False


def tostr(s):
    if isinstance(s, (bytes, bytearray)):
        try:
            return s.decode()
        except Exception as e:
            logger_web_handler.debug('decode error: %s', e, exc_info=config.traceback_print)
            return s
    return s


class UserRegPush(BaseHandler):
    @authenticated
    async def get(self, userid):
        await self.render('user_register_pusher.html', userid=userid)

    @authenticated
    async def post(self, userid):
        envs = {}
        for key in self.request.body_arguments:
            envs[key] = self.get_body_arguments(key)
        env = json.loads(envs['env'][0])
        wxpusher_token = env["wxpusher_token"]
        skey = env["skey"]
        barkurl = env["barkurl"]
        qywx_token = env["qywx_token"]
        tg_token = env["tg_token"]
        dingding_token = env["dingding_token"]
        qywx_webhook = env["qywx_webhook"]
        log = ""
        if "reg" == self.get_body_argument('func'):
            try:
                async with self.db.transaction() as sql_session:
                    if barkurl != "":
                        if barkurl[-1] != '/':
                            barkurl = barkurl + '/'
                        await self.db.user.mod(userid, barkurl=barkurl, sql_session=sql_session)
                        if (await self.db.user.get(userid, fields=('barkurl',), sql_session=sql_session))["barkurl"] == barkurl:
                            log = "注册 Bark 成功\r\n"
                        else:
                            log = "注册 Bark 失败\r\n"
                    else:
                        log = "BarkUrl 未填写完整\r\n"

                    if skey != "":
                        await self.db.user.mod(userid, skey=skey, sql_session=sql_session)
                        if (await self.db.user.get(userid, fields=('skey',), sql_session=sql_session))["skey"] == skey:
                            log = log + "注册 S酱 成功\r\n"
                        else:
                            log = log + "注册 S酱 失败\r\n"
                    else:
                        log = log + "Sendkey 未填写完整\r\n"

                    if wxpusher_token != "":
                        await self.db.user.mod(userid, wxpusher=wxpusher_token, sql_session=sql_session)
                        if (await self.db.user.get(userid, fields=('wxpusher',), sql_session=sql_session))["wxpusher"] == wxpusher_token:
                            log = log + "注册 WxPusher 成功\r\n"
                        else:
                            log = log + "注册 WxPusher 失败\r\n"
                    else:
                        log = log + "WxPusher 未填写完整\r\n"

                    if qywx_token != "":
                        await self.db.user.mod(userid, qywx_token=qywx_token, sql_session=sql_session)
                        if (await self.db.user.get(userid, fields=('qywx_token',), sql_session=sql_session))["qywx_token"] == qywx_token:
                            log = log + "注册 企业微信 Pusher 成功\r\n"
                        else:
                            log = log + "注册 企业微信 Pusher 失败\r\n"
                    else:
                        log = log + "企业微信 未填写完整\r\n"

                    if tg_token != "":
                        await self.db.user.mod(userid, tg_token=tg_token, sql_session=sql_session)
                        if (await self.db.user.get(userid, fields=('tg_token',), sql_session=sql_session))["tg_token"] == tg_token:
                            log = log + "注册 Tg Bot 成功\r\n"
                        else:
                            log = log + "注册 Tg Bot 失败\r\n"
                    else:
                        log = log + "Tg Bot 未填写完整\r\n"

                    if dingding_token != "":
                        await self.db.user.mod(userid, dingding_token=dingding_token, sql_session=sql_session)
                        if (await self.db.user.get(userid, fields=('dingding_token',), sql_session=sql_session))["dingding_token"] == dingding_token:
                            log = log + "注册 DingDing Bot 成功\r\n"
                        else:
                            log = log + "注册 DingDing Bot 失败\r\n"
                    else:
                        log = log + "DingDing Bot 未填写完整\r\n"

                    if qywx_webhook != "":
                        await self.db.user.mod(userid, qywx_webhook=qywx_webhook, sql_session=sql_session)
                        if (await self.db.user.get(userid, fields=('qywx_webhook',), sql_session=sql_session))["qywx_webhook"] == qywx_webhook:
                            log = log + "注册 企业微信 Webhook 成功\r\n"
                        else:
                            log = log + "注册 企业微信 Webhook 失败\r\n"
                    else:
                        log = log + "企业微信 Webhook 未填写完整\r\n"

            except Exception as e:
                logger_web_handler.error('UserID: %s register Pusher_info failed! Reason: %s', userid or '-1', str(e), exc_info=config.traceback_print)
                await self.render('tpl_run_failed.html', log=str(e))
                return

            await self.render('utils_run_result.html', log=log, title='设置成功', flg='success')
            return

        else:
            try:
                f = Pusher(self.db)
                t = datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S')

                if barkurl != "":
                    r = await f.send2bark(barkurl, "正在测试Bark", f"{t} 发送测试")
                    if r == 'True':
                        log = "Bark 已推送, 请检查是否收到\r\n"
                    else:
                        log = "Bark 推送失败, 失败原因: {r}\r\n"
                else:
                    log = "BarkUrl 未填写完整\r\n"

                if skey != "":
                    r = await f.send2s(skey, "正在测试S酱", f"{t} 发送测试")
                    if r == 'True':
                        log = log + "S酱 已推送, 请检查是否收到\r\n"
                    else:
                        log = log + f"S酱 推送失败, 失败原因: {r}\r\n"
                else:
                    log = log + "Sendkey 未填写完整\r\n"

                if wxpusher_token != "":
                    r = await f.send2wxpusher(str(wxpusher_token), f"{t} 发送测试")
                    if r == 'True':
                        log = log + "WxPusher 已推送, 请检查是否收到\r\n"
                    else:
                        log = log + f"WxPusher 推送失败, 失败原因: {r}\r\n"
                else:
                    log = log + "WxPusher 未填写完整\r\n"

                if qywx_token != "":
                    r = await f.qywx_pusher_send(qywx_token, "正在测试企业微信 Pusher", f"{t} 发送测试")
                    if r == 'True':
                        log = log + "企业微信 Pusher 已推送, 请检查是否收到\r\n"
                    else:
                        log = log + f"企业微信 Pusher 推送失败, 失败原因: {r}\r\n"
                else:
                    log = log + "企业微信 未填写完整\r\n"

                if tg_token != "":
                    r = await f.send2tg(tg_token, "正在测试Tg Bot", f"{t} 发送测试")
                    if r == 'True':
                        log = log + "Tg Bot 已推送, 请检查是否收到\r\n"
                    else:
                        log = log + f"Tg Bot 推送失败, 失败原因: {r}\r\n"
                else:
                    log = log + "Tg Bot 未填写完整\r\n"

                if dingding_token != "":
                    r = await f.send2dingding(dingding_token, "正在测试DingDing Bot", f"{t} 发送测试")
                    if r == 'True':
                        log = log + "DingDing Bot 已推送, 请检查是否收到\r\n"
                    else:
                        log = log + f"DingDing Bot 推送失败, 失败原因: {r}\r\n"
                else:
                    log = log + "DingDing Bot 未填写完整\r\n"

                if qywx_webhook != "":
                    r = await f.qywx_webhook_send(qywx_webhook, "正在测试企业微信 Webhook", f"{t} 发送测试")
                    if r == 'True':
                        log = log + "企业微信 Webhook 已推送, 请检查是否收到\r\n"
                    else:
                        log = log + f"企业微信 Webhook 推送失败, 失败原因: {r}\r\n"

            except Exception as e:
                logger_web_handler.error('UserID: %s test Pusher_info failed! Reason: %s', userid or '-1', str(e), exc_info=config.traceback_print)
                await self.render('tpl_run_failed.html', log=str(e))
                return

            await self.render('utils_run_result.html', log=log, title='设置成功', flg='success')
            return


class UserRegPushSw(BaseHandler):
    @authenticated
    async def get(self, userid):
        tasks = []
        for task in await self.db.task.list(userid, fields=('id', 'tplid', 'note', 'disabled', 'ctime', 'pushsw'), limit=None):
            tpl = await self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note'))
            task['tpl'] = tpl
            task['pushsw'] = json.loads(task['pushsw'])
            tasks.append(task)
        temp = await self.db.user.get(userid, fields=('noticeflg', 'push_batch'))
        push_batch = json.loads(temp['push_batch'])
        push_batch['time'] = time.strftime("%H:%M:%S", time.localtime(int(push_batch['time'])))
        temp = temp['noticeflg']
        flg = {}
        flg['handpush_succ'] = False if ((temp & 0x008) == 0) else True
        flg['handpush_fail'] = False if ((temp & 0x004) == 0) else True
        flg['autopush_succ'] = False if ((temp & 0x002) == 0) else True
        flg['autopush_fail'] = False if ((temp & 0x001) == 0) else True

        flg['barksw'] = False if ((temp & 0x040) == 0) else True
        flg['schansw'] = False if ((temp & 0x020) == 0) else True
        flg['wxpushersw'] = False if ((temp & 0x010) == 0) else True
        flg['mailpushersw'] = False if ((temp & 0x080) == 0) else True
        flg['cuspushersw'] = False if ((temp & 0x100) == 0) else True
        flg['qywxpushersw'] = False if ((temp & 0x200) == 0) else True
        flg['tgpushersw'] = False if ((temp & 0x400) == 0) else True
        flg['dingdingpushersw'] = False if ((temp & 0x800) == 0) else True
        flg['qywxwebhooksw'] = False if ((temp & 0x1000) == 0) else True
        logtime = json.loads((await self.db.user.get(userid, fields=('logtime',)))['logtime'])
        if 'schanEN' not in logtime:
            logtime['schanEN'] = False
        if 'WXPEn' not in logtime:
            logtime['WXPEn'] = False
        if 'ErrTolerateCnt' not in logtime:
            logtime['ErrTolerateCnt'] = 0

        await self.render('user_register_pushsw.html', userid=userid, flg=flg, tasks=tasks, logtime=logtime, push_batch=push_batch)

    @authenticated
    async def post(self, userid):
        try:
            async with self.db.transaction() as sql_session:
                tasks = []
                for task in await self.db.task.list(userid, fields=('id', 'tplid', 'note', 'disabled', 'ctime', 'pushsw'), limit=None, sql_session=sql_session):
                    tpl = await self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note'), sql_session=sql_session)
                    task['tpl'] = tpl
                    task['pushsw'] = json.loads(task['pushsw'])
                    task['pushsw']["logen"] = False
                    task['pushsw']["pushen"] = False
                    tasks.append(task)
                temp = await self.db.user.get(userid, fields=('noticeflg', 'push_batch'), sql_session=sql_session)
                envs = {}
                for key in self.request.body_arguments:
                    envs[key] = self.get_body_arguments(key)
                env = json.loads(envs['env'][0])

                logtime = json.loads((await self.db.user.get(userid, fields=('logtime',), sql_session=sql_session))['logtime'])
                if 'ErrTolerateCnt' not in logtime:
                    logtime['ErrTolerateCnt'] = 0
                if logtime['ErrTolerateCnt'] != int(env['ErrTolerateCnt']):
                    logtime['ErrTolerateCnt'] = int(env['ErrTolerateCnt'])
                    await self.db.user.mod(userid, logtime=json.dumps(logtime), sql_session=sql_session)

                push_batch = json.loads(temp['push_batch'])
                if env.get("push_batch_sw") == "on":
                    push_batch["sw"] = True
                else:
                    push_batch["sw"] = False
                if env.get("push_batch_value"):
                    push_batch["time"] = time.mktime(time.strptime(time.strftime("%Y-%m-%d", time.localtime(time.time())) + env["push_batch_value"], "%Y-%m-%d%H:%M:%S"))
                if env.get("push_batch_delta"):
                    push_batch["delta"] = int(env["push_batch_delta"])
                else:
                    push_batch["delta"] = 86400
                await self.db.user.mod(userid, push_batch=json.dumps(push_batch), sql_session=sql_session)

                barksw_flg = 1 if ("barksw" in env) else 0
                schansw_flg = 1 if ("schansw" in env) else 0
                wxpushersw_flg = 1 if ("wxpushersw" in env) else 0
                mailpushersw_flg = 1 if ("mailpushersw" in env) else 0
                cuspushersw_flg = 1 if ("cuspushersw" in env) else 0
                qywxpushersw_flg = 1 if ("qywxpushersw" in env) else 0
                tgpushersw_flg = 1 if ("tgpushersw" in env) else 0
                dingdingpushersw_flg = 1 if ("dingdingpushersw" in env) else 0
                qywxwebhooksw_flg = 1 if ("qywxwebhooksw" in env) else 0
                handpush_succ_flg = 1 if ("handpush_succ" in env) else 0
                handpush_fail_flg = 1 if ("handpush_fail" in env) else 0
                autopush_succ_flg = 1 if ("autopush_succ" in env) else 0
                autopush_fail_flg = 1 if ("autopush_fail" in env) else 0

                flg = (qywxwebhooksw_flg << 12) \
                    | (dingdingpushersw_flg << 11) \
                    | (tgpushersw_flg << 10) \
                    | (qywxpushersw_flg << 9) \
                    | (cuspushersw_flg << 8) \
                    | (mailpushersw_flg << 7) \
                    | (barksw_flg << 6) \
                    | (schansw_flg << 5) \
                    | (wxpushersw_flg << 4) \
                    | (handpush_succ_flg << 3) \
                    | (handpush_fail_flg << 2) \
                    | (autopush_succ_flg << 1) \
                    | (autopush_fail_flg)

                for e in env:
                    temp = re.findall(r"(.+?)pushen", e)
                    if len(temp) > 0:
                        taskid = int(temp[0])
                        for task in tasks:
                            if taskid == task["id"]:
                                task['pushsw']["pushen"] = True

                await self.db.user.mod(userid, noticeflg=flg, sql_session=sql_session)
                for task in tasks:
                    await self.db.task.mod(task["id"], pushsw=json.dumps(task['pushsw']), sql_session=sql_session)

        except Exception as e:
            logger_web_handler.error('UserID: %s modify Push_settings failed! Reason: %s', userid or '-1', str(e), exc_info=config.traceback_print)
            await self.render('tpl_run_failed.html', log=str(e))
            return
        await self.render('utils_run_result.html', log="设置完成", title='设置成功', flg='success')
        return


class UserManagerHandler(BaseHandler):
    @authenticated
    async def get(self, userid):
        flg = self.get_argument("flg", '')
        title = self.get_argument("title", '')
        log = self.get_argument("log", '')
        adminflg = False
        users = []
        user = await self.db.user.get(userid, fields=('role',))
        if user and user['role'] == "admin":
            adminflg = True
            users = []
            for user in await self.db.user.list(fields=('id', 'status', 'role', 'ctime', 'email', 'atime', 'email_verified', 'aip')):
                if user['email_verified'] == 0:
                    user['email_verified'] = False
                else:
                    user['email_verified'] = True
                users.append(user)

        await self.render("user_manage.html", users=users, userid=userid, adminflg=adminflg, flg=flg, title=title, log=log)
        return

    @authenticated
    async def post(self, userid):
        try:
            async with self.db.transaction() as sql_session:
                user = await self.db.user.get(userid, fields=('role',), sql_session=sql_session)
                if user and user['role'] == "admin":
                    envs = {}
                    for k, _ in self.request.body_arguments.items():
                        envs[k] = self.get_body_argument(k)
                    mail = envs['adminmail']
                    pwd = envs['adminpwd']
                    if await self.db.user.challenge_md5(mail, pwd, sql_session=sql_session):
                        target_users = []
                        for key, value in envs.items():
                            if value == "on":
                                target_users.append(key)

                        for sub_user in target_users:
                            if await self.db.user.get(sub_user, fields=('role',), sql_session=sql_session) != 'admin':
                                if 'banbtn' in envs:
                                    await self.db.user.mod(sub_user, status='Disable', sql_session=sql_session)
                                    for task in await self.db.task.list(sub_user, fields=('id',), limit=None, sql_session=sql_session):
                                        await self.db.task.mod(task['id'], disabled=True, sql_session=sql_session)

                                if 'activatebtn' in envs:
                                    await self.db.user.mod(sub_user, status='Enable', sql_session=sql_session)
                                    for task in await self.db.task.list(sub_user, fields=('id',), limit=None, sql_session=sql_session):
                                        await self.db.task.mod(task['id'], disabled=False, sql_session=sql_session)

                                if 'verifybtn' in envs:
                                    await self.db.user.mod(sub_user, email_verified=True, mtime=time.time(), sql_session=sql_session)

                                if 'delbtn' in envs:
                                    for task in await self.db.task.list(sub_user, fields=('id',), limit=None, sql_session=sql_session):
                                        await self.db.task.delete(task['id'], sql_session=sql_session)
                                        logs = await self.db.tasklog.list(taskid=task['id'], fields=('id',), sql_session=sql_session)
                                        for log in logs:
                                            await self.db.tasklog.delete(log['id'], sql_session=sql_session)

                                    for tpl in await self.db.tpl.list(fields=('id', 'userid'), limit=None, sql_session=sql_session):
                                        if tpl['userid'] == int(sub_user):
                                            await self.db.tpl.delete(tpl['id'], sql_session=sql_session)

                                    for notepad in await self.db.notepad.list(fields=('userid', 'notepadid'), limit=None, userid=sub_user, sql_session=sql_session):
                                        await self.db.notepad.delete(sub_user, notepad['notepadid'], sql_session=sql_session)

                                    await self.db.user.delete(sub_user, sql_session=sql_session)
                    else:
                        raise Exception("账号/密码错误")
                else:
                    raise Exception("非管理员，不可操作")
        except Exception as e:
            if str(e).find('get user need id or email') > -1:
                e = '请输入用户名/密码'
            await self.render('utils_run_result.html', log=str(e), title='设置失败', flg='danger')
            logger_web_handler.error('UserID: %s manage User failed! Reason: %s', userid or '-1', str(e), exc_info=config.traceback_print)
            return
        await self.render('utils_run_result.html', title='操作成功', flg='success')
        return


class UserDBHandler(BaseHandler):
    @authenticated
    async def get(self, userid):
        adminflg = False
        user = await self.db.user.get(userid, fields=('role',))
        if user and user['role'] == "admin":
            adminflg = True
        await self.render("DB_manage.html", userid=userid, adminflg=adminflg)
        return

    @authenticated
    async def post(self, userid):
        def backup_progress(status, remaining, total):
            logger_web_handler.info('Sqlite_Backup:(%s) Copied %s of %s pages...', status, total - remaining, total)

        def restore_progress(status, remaining, total):
            logger_web_handler.info('Sqlite_Restore:(%s) Copied %s of %s pages...', status, total - remaining, total)
        try:
            async with self.db.transaction() as sql_session:
                user = await self.db.user.get(userid, fields=('role', 'email'), sql_session=sql_session)
                envs = {}
                for k, _ in self.request.body_arguments.items():
                    envs[k] = self.get_body_argument(k)
                mail = envs['adminmail']
                pwd = envs['adminpwd']
                now = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

                if user and await self.db.user.challenge_md5(mail, pwd, sql_session=sql_session) and (user['email'] == mail):
                    if 'backupbtn' in envs:
                        if user['role'] == "admin":
                            if config.db_type != "sqlite3":
                                raise Exception("抱歉，暂不支持通过本页面备份MySQL数据！ﾍ(;´Д｀ﾍ)")
                            filename = config.sqlite3.path
                            savename = f"database_{now}.db"
                            if not AIO_IMPORT:
                                raise Exception("更新容器后请先重启容器!")

                            conn_src = sqlite3.connect(filename, check_same_thread=False)
                            conn_target = sqlite3.connect(savename, check_same_thread=False)

                            conn_src.backup(conn_target, progress=backup_progress)
                            conn_target.commit()
                            conn_src.close()
                            conn_target.close()
                            try:
                                self.set_header('Content-Type', 'application/octet-stream; charset=UTF-8')
                                self.set_header('Content-Disposition', ('attachment; filename=' + savename).encode('utf-8'))
                                content_length = os.stat(savename).st_size
                                self.set_header("Content-Length", content_length)

                                async with aiofiles.open(savename, 'rb') as f:
                                    self.set_header('Content-Type', 'application/octet-stream')
                                    self.set_header('Content-Disposition', ('attachment; filename=' + savename).encode('utf-8'))

                                    chunk_size = 1024 * 1024 * 1  # 1MB
                                    while True:
                                        chunk = await f.read(chunk_size)
                                        if not chunk:
                                            break
                                        try:
                                            self.write(chunk)  # write the chunk to response
                                            await self.flush()  # send the chunk to client
                                        except iostream.StreamClosedError as e:
                                            # this means the client has closed the connection
                                            # so break the loop
                                            raise Exception("Stream closed") from e
                                        finally:
                                            # deleting the chunk is very important because
                                            # if many clients are downloading files at the
                                            # same time, the chunks in memory will keep
                                            # increasing and will eat up the RAM
                                            del chunk
                                await self.finish()
                            finally:
                                await gen.sleep(3)
                                os.remove(savename)
                        else:
                            raise Exception("管理员才能备份数据库")

                    if 'backuptplsbtn' in envs:
                        tpls = []
                        for tpl in await self.db.tpl.list(userid=userid, fields=('id', 'siteurl', 'sitename', 'banner', 'note', 'fork', '_groups', 'har', 'tpl', 'variables', 'init_env'), limit=None, sql_session=sql_session):
                            tpl['tpl'] = await self.db.user.decrypt(userid, tpl['tpl'], sql_session=sql_session)
                            tpl['har'] = await self.db.user.decrypt(userid, tpl['har'], sql_session=sql_session)
                            tpls.append(tpl)

                        tasks = []
                        for task in await self.db.task.list(userid, fields=('id', 'tplid', 'retry_count', 'retry_interval', 'note', 'disabled', '_groups', 'init_env', 'env', 'ontimeflg', 'ontime', 'pushsw', 'newontime'), limit=None, sql_session=sql_session):
                            task['init_env'] = await self.db.user.decrypt(userid, task['init_env'], sql_session=sql_session)
                            task['env'] = await self.db.user.decrypt(userid, task['env'], sql_session=sql_session) if task['env'] else None
                            tasks.append(task)

                        backupdata = {}
                        backupdata['tpls'] = tpls
                        backupdata['tasks'] = tasks
                        savename = f"{user['email']}_{now}.json"
                        if not AIO_IMPORT:
                            raise Exception("更新容器后请先重启容器!")
                        async with aiofiles.open(savename, 'w', encoding='utf-8') as fp:
                            await fp.write(json.dumps(backupdata, ensure_ascii=False, indent=4))
                            fp.close()
                        self.set_header('Content-Type', 'application/octet-stream; charset=UTF-8')
                        self.set_header('Content-Disposition', ('attachment; filename=' + savename).encode('utf-8'))
                        async with aiofiles.open(savename, 'rb') as f:
                            chunk_size = 1024 * 1024 * 1  # 1MB
                            while True:
                                data = await f.read(chunk_size)
                                if not data:
                                    break
                                self.write(data)
                                await self.flush()
                        os.remove(savename)
                        await self.finish()
                        return

                    if 'recoverytplsbtn' in envs:
                        if 'recfile' in self.request.files:
                            envs['recfile'] = self.request.files['recfile'][0]['body']
                            if envs['recfile'][:6] == b'SQLite':
                                if user['role'] != "admin":
                                    raise Exception("管理员才能操作数据库")
                                db_dir = os.path.dirname(config.sqlite3.path)
                                db_restore = os.path.join(db_dir, 'database_restore.db')
                                with open(db_restore, 'wb') as f:
                                    f.write(envs['recfile'])
                                db_backup = os.path.join(db_dir, 'database_backup.db')
                                db_now = os.path.join(db_dir, 'database.db')
                                # 先备份 database.db 到 database_backup.db
                                conn_src = sqlite3.connect(db_now, check_same_thread=False)
                                conn_target = sqlite3.connect(db_backup, check_same_thread=False)

                                conn_src.backup(conn_target, progress=backup_progress)
                                conn_target.commit()
                                conn_src.close()
                                conn_target.close()

                                # 再还原 database_restore.db 到 database.db
                                conn_src = sqlite3.connect(db_restore, check_same_thread=False)
                                conn_target = sqlite3.connect(db_now, check_same_thread=False)

                                conn_src.backup(conn_target, progress=restore_progress)
                                conn_target.commit()
                                conn_src.close()
                                conn_target.close()
                                await self.render('utils_run_result.html', log="恢复完成, 请务必重启QD程序或容器!!!\r\nPS: 原始 database.db 文件已备份为 database_backup.db 文件!!!\r\n如还原失败, 请手动恢复 database_backup.db 文件!!!", title='设置成功', flg='success')
                                # raise Exception("抱歉，暂不支持通过本页面还原SQLite3数据库文件！(╥╯^╰╥)")
                                return
                            else:
                                try:
                                    tpls = json.loads(envs['recfile'])['tpls']
                                    tasks = json.loads(envs['recfile'])['tasks']
                                except Exception as e:
                                    raise Exception("抱歉，暂不支持通过本页面还原该备份文件！(ノ￣▽￣) \\r\\n \
                                    请确认该文件来自于该页面\"备份\"按钮 (๑*◡*๑)。") from e
                            # ids = []
                            for newtpl in tpls:
                                userid2 = int(userid)
                                har = await self.db.user.encrypt(userid2, newtpl['har'], sql_session=sql_session)
                                tpl = await self.db.user.encrypt(userid2, newtpl['tpl'], sql_session=sql_session)
                                variables = newtpl['variables']
                                init_env = newtpl.get('init_env', "{}")
                                newid = await self.db.tpl.add(userid2, har, tpl, variables, init_env=init_env, sql_session=sql_session)
                                await self.db.tpl.mod(newid, fork=newtpl['fork'],
                                                      siteurl=newtpl['siteurl'],
                                                      sitename=newtpl['sitename'],
                                                      note=newtpl['note'],
                                                      _groups='备份还原',
                                                      banner=newtpl['banner'],
                                                      sql_session=sql_session
                                                      )
                                for task in tasks:
                                    if task['tplid'] == newtpl['id']:
                                        task['tplid'] = newid

                            for newtask in tasks:
                                userid2 = int(userid)
                                newtask['init_env'] = await self.db.user.encrypt(userid2, newtask['init_env'], sql_session=sql_session)
                                newtask['env'] = await self.db.user.encrypt(userid2, newtask['env'], sql_session=sql_session)
                                newtask['retry_count'] = newtask.get('retry_count', config.task_max_retry_count)
                                newtask['retry_interval'] = newtask.get('retry_interval')
                                taskid = await self.db.task.add(newtask['tplid'], userid, newtask['env'], sql_session=sql_session)
                                await self.db.task.mod(taskid, disabled=newtask['disabled'],
                                                       init_env=newtask['init_env'],
                                                       session=None,
                                                       retry_count=newtask['retry_count'],
                                                       retry_interval=newtask['retry_interval'],
                                                       note=newtask['note'],
                                                       _groups='备份还原',
                                                       ontimeflg=newtask['ontimeflg'],
                                                       ontime=newtask['ontime'],
                                                       pushsw=newtask['pushsw'],
                                                       newontime=newtask['newontime'],
                                                       sql_session=sql_session
                                                       )
                            await self.render('utils_run_result.html', log="设置完成", title='设置成功', flg='success')
                            return
                        else:
                            raise Exception("请上传文件")
                else:
                    raise Exception("账号/密码错误")
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if str(e).find('get user need id or email') > -1:
                e = '请输入用户名/密码'
            self.set_status(400)
            self.set_header('Error-Message', base64.b64encode(str(e).encode('utf-8')))
            await self.render('utils_run_result.html', log=str(e), title='设置失败', flg='danger')
            logger_web_handler.error('UserID: %s backup or restore Database failed! Reason: %s', userid or '-1', str(e))
            return
        return


class UserPushShowPvar(BaseHandler):
    @authenticated
    async def post(self, userid):
        try:
            user = await self.db.user.get(userid, fields=('role', 'email'))
            envs = {}
            for k, _ in self.request.body_arguments.items():
                envs[k] = self.get_body_argument(k)
            mail = envs['adminmail']
            pwd = envs['adminpwd']
            if await self.db.user.challenge_md5(mail, pwd) and (user['email'] == mail):
                key = await self.db.user.get(userid, fields=("barkurl", 'skey', 'wxpusher', 'qywx_token', 'tg_token', 'dingding_token', 'qywx_webhook'))
                log = f"""BarkUrl 前值：{key['barkurl']}\r\nSendkey 前值：{key['skey']}\r\nWxPusher 前值：{key['wxpusher']}\r\n企业微信 Pusher 前值：{key['qywx_token']}\r\nTg Bot 前值：{key['tg_token']}\r\nDingDing Bot 前值：{key['dingding_token']}\r\n企业微信 WebHook 前值: {key['qywx_webhook']}"""

                await self.render('utils_run_result.html', log=log, title='设置成功', flg='success')
                return
            raise Exception("账号/密码错误")
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if str(e).find('get user need id or email') > -1:
                e = '请输入用户名/密码'
            await self.render('tpl_run_failed.html', log=str(e))
            logger_web_handler.error('UserID: %s show Push_settings failed! Reason: %s', userid or '-1', str(e))
            return


class CustomPusherHandler(BaseHandler):
    @authenticated
    async def get(self, userid):
        diypusher = (await self.db.user.get(userid, fields=('diypusher',)))['diypusher']
        diypusher = json.loads(diypusher) if (diypusher != '') else {'mode': 'GET'}
        await self.render('user_register_cus_pusher.html', userid=userid, diypusher=diypusher)
        return

    @authenticated
    async def post(self, userid):
        try:
            envs = {}
            for k, _ in self.request.body_arguments.items():
                envs[k] = self.get_body_argument(k)
            req = Pusher(self.db)
            log = ''
            now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            tmp = await req.cus_pusher_send(envs , '推送测试', now)
            if 'True' == tmp:
                if envs['btn'] == 'regbtn':
                    await self.db.user.mod(userid, diypusher=json.dumps(envs))
            else:
                raise Exception(tmp)

            log = '运行成功，请检查是否收到推送'
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if str(e).find('get user need id or email') > -1:
                e = '请输入用户名/密码'
            await self.render('utils_run_result.html', log=str(e), title='设置失败', flg='danger')
            logger_web_handler.error('UserID: %s register or tes Cus_Pusher failed! Reason: %s', userid or '-1', str(e))
            return

        await self.render('utils_run_result.html', log=log, title='设置成功', flg='success')
        return


class UserSetNewPWDHandler(BaseHandler):
    @authenticated
    async def get(self, userid):
        email = (await self.db.user.get(userid, fields=('email',)))['email']
        await self.render('user_setnewpwd.html', userid=userid, usermail=email)
        return

    @authenticated
    async def post(self, userid):
        try:
            log = '设置成功'
            envs = {}
            for k, _ in self.request.body_arguments.items():
                envs[k] = self.get_body_argument(k)

            async with self.db.transaction() as sql_session:
                adminuser = await self.db.user.get(email=envs['adminmail'], fields=('role', 'email'), sql_session=sql_session)
                new_pwd = envs['newpwd']
                if await self.db.user.challenge_md5(envs['adminmail'], envs['adminpwd'], sql_session=sql_session) and (adminuser['role'] == 'admin'):
                    if len(new_pwd) >= 6:
                        await self.db.user.mod(userid, password=new_pwd, sql_session=sql_session)
                        user = await self.db.user.get(userid, fields=('email', 'password', 'password_md5'), sql_session=sql_session)
                        hash = MD5.new()
                        hash.update(new_pwd.encode('utf-8'))
                        tmp = crypto.password_hash(hash.hexdigest(), await self.db.user.decrypt(userid, user['password'], sql_session=sql_session))
                        if user['password_md5'] != tmp:
                            await self.db.user.mod(userid, password_md5=tmp, sql_session=sql_session)
                        if not await self.db.user.challenge(envs['usermail'], new_pwd, sql_session=sql_session):
                            raise Exception('修改失败')
                    else:
                        raise Exception('密码长度要大于6位')
                else:
                    raise Exception('管理员用户名/密码错误')
        except Exception as e:
            logger_web_handler.error('UserID: %s set New_Password failed! Reason: %s', userid or '-1', str(e), exc_info=config.traceback_print)
            await self.render('utils_run_result.html', log=str(e), title='设置失败', flg='danger')
            return

        await self.render('utils_run_result.html', log=log, title='设置成功', flg='success')
        return


handlers = [
    (r'/user/(\d+)/pushsw', UserRegPushSw),
    (r'/user/(\d+)/regpush', UserRegPush),
    (r'/user/(\d+)/UserPushShowPvar', UserPushShowPvar),
    (r'/user/(\d+)/manage', UserManagerHandler),
    (r'/user/(\d+)/database', UserDBHandler),
    (r'/util/custom/(\d+)/pusher', CustomPusherHandler),
    (r'/user/(\d+)/setnewpwd', UserSetNewPWDHandler),
]
