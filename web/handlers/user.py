#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 11:39:25

import json
import time
import datetime
from tornado import gen
try:
    import aiofiles
    aio_import = True
except:
    aio_import = False
import re
import os

import config
from .base import *

from Crypto.Hash import MD5

from backup import DBnew

import traceback
from libs.funcs import pusher
from libs import mcrypto as crypto

def tostr(s):
    if isinstance(s, bytes):
        try:
            return s.decode()
        except :
            return s
    return s

class UserRegPush(BaseHandler):
    @tornado.web.authenticated
    async def get(self, userid):
        await self.render('user_register_pusher.html', userid=userid)
    
    @tornado.web.authenticated
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
        log = ""
        if  ("reg" == self.get_body_argument('func')):
            try:
                if (barkurl != ""):
                    if (barkurl[-1] != '/'): 
                        barkurl=barkurl+'/'
                    self.db.user.mod(userid, barkurl = barkurl)
                    if (self.db.user.get(userid, fields=("barkurl"))["barkurl"] == barkurl):
                        log = u"注册 Bark 成功\r\n"
                    else:
                        log = u"注册 Bark 失败\r\n"
                else:
                    log = u"BarkUrl 未填写完整\r\n"

                if (skey != ""):
                    self.db.user.mod(userid, skey = skey)
                    if (self.db.user.get(userid, fields=("skey"))["skey"] == skey):
                        log = log+u"注册 S酱 成功\r\n"
                    else:
                        log = log+u"注册 S酱 失败\r\n"
                else:
                    log = log+u"Sendkey 未填写完整\r\n"
                    
                if  (wxpusher_token != ""):
                    self.db.user.mod(userid, wxpusher = wxpusher_token)
                    if (self.db.user.get(userid, fields=("wxpusher"))["wxpusher"] == wxpusher_token):
                        log = log+u"注册 WxPusher 成功\r\n"
                    else:
                        log = log+u"注册 WxPusher 失败\r\n"
                else:
                    log = log+u"WxPusher 未填写完整\r\n"

                if (qywx_token != ""):
                    self.db.user.mod(userid, qywx_token = qywx_token)
                    if (self.db.user.get(userid, fields=("qywx_token"))["qywx_token"] == qywx_token):
                        log = log+u"注册 企业微信 成功\r\n"
                    else:
                        log = log+u"注册 企业微信 失败\r\n"
                else:
                    log = log+u"企业微信 未填写完整\r\n"

                if (tg_token != ""):
                    self.db.user.mod(userid, tg_token = tg_token)
                    if (self.db.user.get(userid, fields=("tg_token"))["tg_token"] == tg_token):
                        log = log+u"注册 Tg Bot 成功\r\n"
                    else:
                        log = log+u"注册 Tg Bot 失败\r\n"
                else:
                    log = log+u"Tg Bot 未填写完整\r\n"

                if (dingding_token != ""):
                    self.db.user.mod(userid, dingding_token = dingding_token)
                    if (self.db.user.get(userid, fields=("dingding_token"))["dingding_token"] == dingding_token):
                        log = log+u"注册 DingDing Bot 成功\r\n"
                    else:
                        log = log+u"注册 DingDing Bot 失败\r\n"
                else:
                    log = log+u"DingDing Bot 未填写完整\r\n"

            except Exception as e:
                if config.traceback_print:
                    traceback.print_exc()
                await self.render('tpl_run_failed.html', log=str(e))
                logger_Web_Handler.error('UserID: %s register Pusher_info failed! Reason: %s', userid or '-1', str(e))
                return
            
            await self.render('utils_run_result.html', log=log, title=u'设置成功', flg='success')
            return

        else:
            try:
                f = pusher()
                t = datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S')

                if (barkurl != ""):
                    r = await f.send2bark(barkurl, u"正在测试Bark", u"{t} 发送测试".format(t=t))
                    if r == 'True':
                        log = u"Bark 已推送,请检查是否收到\r\n"
                    else:
                        log = u"Bark 推送失败, 失败原因: {}\r\n".format(r)
                else:
                    log = u"BarkUrl 未填写完整\r\n"

                if (skey != ""):
                    r = await f.send2s(skey, u"正在测试S酱", u"{t} 发送测试".format(t=t))
                    if r == 'True':
                        log = log+u"S酱 已推送,请检查是否收到\r\n"
                    else:
                        log = log+u"S酱 推送失败, 失败原因: {}\r\n".format(r)
                else:
                    log = log+u"Sendkey 未填写完整\r\n"

                if (wxpusher_token != ""):
                    r = await f.send2wxpusher("{0}".format(wxpusher_token),u"{t} 发送测试".format(t=t))
                    if r == 'True':
                        log = log+u"WxPusher 已推送,请检查是否收到\r\n"
                    else:
                        log = log+u"WxPusher 推送失败, 失败原因: {}\r\n".format(r)
                else:
                    log = log+u"WxPusher 未填写完整\r\n"
                
                if (qywx_token != ""):
                    r = await f.qywx_pusher_send(qywx_token, "正在测试企业微信", u"{t} 发送测试".format(t=t))
                    if r == 'True':
                        log = log+u"企业微信 已推送,请检查是否收到\r\n"
                    else:
                        log = log+u"企业微信 推送失败, 失败原因: {}\r\n".format(r)
                else:
                    log = log+u"企业微信 未填写完整\r\n"

                if (tg_token != ""):
                    r = await f.send2tg(tg_token, "正在测试Tg Bot", u"{t} 发送测试".format(t=t))
                    if r == 'True':
                        log = log+u"Tg Bot 已推送,请检查是否收到\r\n"
                    else:
                        log = log+u"Tg Bot 推送失败, 失败原因: {}\r\n".format(r)
                else:
                    log = log+u"Tg Bot 未填写完整\r\n"

                if (dingding_token != ""):
                    r = await f.send2dingding(dingding_token, "正在测试DingDing Bot", u"{t} 发送测试".format(t=t))
                    if r == 'True':
                        log = log+u"DingDing Bot 已推送,请检查是否收到\r\n"
                    else:
                        log = log+u"DingDing Bot 推送失败, 失败原因: {}\r\n".format(r)
                else:
                    log = log+u"DingDing Bot 未填写完整\r\n"

            except Exception as e:
                if config.traceback_print:
                    traceback.print_exc()
                await self.render('tpl_run_failed.html', log=str(e))
                logger_Web_Handler.error('UserID: %s test Pusher_info failed! Reason: %s', userid or '-1', str(e))
                return

            await self.render('utils_run_result.html', log=log, title=u'设置成功', flg='success')
            return

class UserRegPushSw(BaseHandler):
    @tornado.web.authenticated
    async def get(self, userid):
        tasks = []
        for task in self.db.task.list(userid, fields=('id', 'tplid', 'note', 'disabled', 'ctime', 'pushsw'), limit=None):
            tpl = self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note') )
            task['tpl'] = tpl
            task['pushsw'] = json.loads(task['pushsw'])
            tasks.append(task)
        temp = self.db.user.get(userid, fields=('noticeflg','push_batch'))
        push_batch = json.loads(temp['push_batch'])
        push_batch['time']=time.strftime("%H:%M:%S",time.localtime(int(push_batch['time'])))
        temp = temp['noticeflg']
        flg = {}
        flg['barksw']        = False if ((temp & 0x040) == 0) else True 
        flg['schansw']       = False if ((temp & 0x020) == 0) else True 
        flg['wxpushersw']    = False if ((temp & 0x010) == 0) else True
        flg['mailpushersw']  = False if ((temp & 0x080) == 0) else True
        flg['cuspushersw']   = False if ((temp & 0x100) == 0) else True
        flg['qywxpushersw']   = False if ((temp & 0x200) == 0) else True
        flg['tgpushersw']   = False if ((temp & 0x400) == 0) else True
        flg['dingdingpushersw']   = False if ((temp & 0x800) == 0) else True
        flg['handpush_succ'] = False if ((temp & 0x008) == 0) else True 
        flg['handpush_fail'] = False if ((temp & 0x004) == 0) else True 
        flg['autopush_succ'] = False if ((temp & 0x002) == 0) else True 
        flg['autopush_fail'] = False if ((temp & 0x001) == 0) else True
        logtime = json.loads(self.db.user.get(userid, fields=('logtime'))['logtime'])
        if 'schanEN' not in logtime:logtime['schanEN'] = False
        if 'WXPEn' not in logtime:logtime['WXPEn'] = False
        if 'ErrTolerateCnt' not in logtime:logtime['ErrTolerateCnt'] = 0
        

        await self.render('user_register_pushsw.html', userid=userid, flg=flg, tasks=tasks, logtime=logtime, push_batch=push_batch)

    @tornado.web.authenticated
    async def post(self, userid):
        try:
            tasks = []
            for task in self.db.task.list(userid, fields=('id', 'tplid', 'note', 'disabled', 'ctime', 'pushsw'), limit=None):
                tpl = self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note') )
                task['tpl'] = tpl
                task['pushsw'] = json.loads(task['pushsw'])
                task['pushsw']["logen"] = False
                task['pushsw']["pushen"] = False
                tasks.append(task)
            temp = self.db.user.get(userid, fields=('noticeflg','push_batch'))
            envs = {}
            for key in self.request.body_arguments:
                envs[key] = self.get_body_arguments(key)
            env = json.loads(envs['env'][0])
            
            logtime = json.loads(self.db.user.get(userid, fields=('logtime'))['logtime'])
            if 'ErrTolerateCnt' not in logtime:logtime['ErrTolerateCnt'] = 0
            if (logtime['ErrTolerateCnt'] != int(env['ErrTolerateCnt'])):
                logtime['ErrTolerateCnt'] = int(env['ErrTolerateCnt'])
                self.db.user.mod(userid, logtime=json.dumps(logtime))

            push_batch = json.loads(temp['push_batch'])
            if env.get("push_batch_sw") == "on":
                push_batch["sw"] = True
            else:
                push_batch["sw"] = False
            if env.get("push_batch_value"):
                push_batch["time"] = time.mktime(time.strptime(time.strftime("%Y-%m-%d",time.localtime(time.time()))+env["push_batch_value"],"%Y-%m-%d%H:%M:%S"))
            if env.get("push_batch_delta"):
                push_batch["delta"] = int(env["push_batch_delta"])
            else:
                push_batch["delta"] = 86400
            self.db.user.mod(userid, push_batch=json.dumps(push_batch))

            barksw_flg        = 1 if ("barksw" in env) else 0 
            schansw_flg       = 1 if ("schansw" in env) else 0 
            wxpushersw_flg    = 1 if ("wxpushersw" in env) else 0
            mailpushersw_flg  = 1 if ("mailpushersw" in env) else 0
            cuspushersw_flg  = 1 if ("cuspushersw" in env) else 0
            qywxpushersw_flg  = 1 if ("qywxpushersw" in env) else 0 
            tgpushersw_flg  = 1 if ("tgpushersw" in env) else 0 
            dingdingpushersw_flg  = 1 if ("dingdingpushersw" in env) else 0 
            handpush_succ_flg = 1 if ("handpush_succ" in env) else 0
            handpush_fail_flg = 1 if ("handpush_fail" in env) else 0
            autopush_succ_flg = 1 if ("autopush_succ" in env) else 0
            autopush_fail_flg = 1 if ("autopush_fail" in env) else 0
            
            flg =(dingdingpushersw_flg << 11) \
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
                        if (taskid == task["id"]):
                            task['pushsw']["pushen"] = True
                            
            self.db.user.mod(userid, noticeflg=flg)
            for task in tasks:
                self.db.task.mod(task["id"], pushsw=json.dumps(task['pushsw']))
                
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            await self.render('tpl_run_failed.html', log=str(e))
            logger_Web_Handler.error('UserID: %s modify Push_settings failed! Reason: %s', userid or '-1', str(e))
            return
        await self.render('utils_run_result.html', log=u"设置完成", title=u'设置成功', flg='success')
        return
    
class UserManagerHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self, userid):
        flg = self.get_argument("flg", '')
        title = self.get_argument("title", '')
        log = self.get_argument("log", '')
        adminflg = False
        users = []
        user = self.db.user.get(userid, fields=('role'))
        if user and user['role'] == "admin":
            adminflg = True
            users = []
            for user in self.db.user.list(fields=('id','status', 'role', 'ctime', 'email', 'atime', 'email_verified', 'aip')):
                if (user['email_verified'] == 0):
                    user['email_verified'] = False
                else:
                    user['email_verified'] = True
                users.append(user)

        await self.render("user_manage.html", users=users, userid=userid, adminflg=adminflg, flg=flg, title=title,log=log)
        return

    @tornado.web.authenticated
    async def post(self, userid):
        try:
            user = self.db.user.get(userid, fields=('role'))
            if user and user['role'] == "admin":
                envs = {}
                for k, _  in self.request.body_arguments.items():
                    envs[k] = self.get_body_argument(k)
                mail = envs['adminmail']
                pwd = envs['adminpwd']
                if self.db.user.challenge_MD5(mail, pwd):
                    Target_users = []
                    for key, value in envs.items():
                        if value == "on":
                            Target_users.append(key)

                    for sub_user in Target_users:
                        if (self.db.user.get(sub_user, fields=('role')) != 'admin'):
                            if 'banbtn' in envs:
                                self.db.user.mod(sub_user, status='Disable')
                                for task in self.db.task.list(sub_user, fields=('id'), limit=None):
                                    self.db.task.mod(task['id'], disabled=True)

                            if 'activatebtn' in envs:
                                self.db.user.mod(sub_user, status='Enable')
                                for task in self.db.task.list(sub_user, fields=('id'), limit=None):
                                    self.db.task.mod(task['id'], disabled=False)

                            if 'verifybtn' in envs:
                                self.db.user.mod(sub_user, email_verified=True, mtime=time.time())

                            if 'delbtn' in envs:
                                for task in self.db.task.list(sub_user, fields=('id'), limit=None):
                                    self.db.task.delete(task['id'])
                                    logs = self.db.tasklog.list(taskid = task['id'], fields=('id'))
                                    for log in logs:
                                        self.db.tasklog.delete(log['id'])

                                for tpl in self.db.tpl.list(fields=('id', 'userid'), limit=None):
                                    if tpl['userid'] == int(sub_user):
                                        self.db.tpl.delete(tpl['id'])
                                self.db.user.delete(sub_user)
                else:
                    raise Exception(u"账号/密码错误")
            else:
                raise Exception(u"非管理员，不可操作")
        except Exception as e:
            if (str(e).find('get user need id or email') > -1):
                e = u'请输入用户名/密码'
            await self.render('utils_run_result.html', log=str(e), title='设置失败', flg='danger')
            logger_Web_Handler.error('UserID: %s manage User failed! Reason: %s', userid or '-1', str(e))
            return
        await self.render('utils_run_result.html', title='操作成功', flg='success')
        return

class UserDBHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self, userid):
        adminflg = False
        user = self.db.user.get(userid, fields=('role'))
        if user and user['role'] == "admin":
            adminflg = True 
        await self.render("DB_manage.html", userid=userid, adminflg=adminflg)
        return
    
    @tornado.web.authenticated
    async def post(self, userid):
        try:
            user = self.db.user.get(userid, fields=('role', 'email'))
            envs = {}
            for k, _  in self.request.body_arguments.items():
                envs[k] = self.get_body_argument(k)
            mail = envs['adminmail']
            pwd = envs['adminpwd']
            now=datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

            if ('backupbtn' in envs):
                if self.db.user.challenge_MD5(mail, pwd) and (user['email'] == mail):
                    if user and user['role'] == "admin":
                        if config.db_type != "sqlite3":
                            raise Exception(u"抱歉，暂不支持通过本页面备份MySQL数据！ﾍ(;´Д｀ﾍ)")
                        filename = config.sqlite3.path
                        savename = "database_{now}.db".format(now=now)
                        self.set_header ('Content-Type', 'application/octet-stream')
                        self.set_header ('Content-Disposition', 'attachment; filename='+savename)
                        if not aio_import:
                            raise Exception(u"更新容器后请先重启容器!") 
                        async with aiofiles.open(filename, 'rb') as f:
                            while True:
                                data = await f.read(1024)
                                if not data:
                                    break
                                self.write(data)
                                self.flush()
                        await self.finish()
                    else:
                        raise Exception(u"管理员才能备份数据库") 
                else:
                    raise Exception(u"账号/密码错误")
 
            if self.db.user.challenge_MD5(mail, pwd) and (user['email'] == mail):
                if ('backuptplsbtn' in envs):
                    tpls = []
                    for tpl in self.db.tpl.list(userid=userid, fields=('id', 'siteurl', 'sitename', 'banner', 'note','fork', '_groups', 'har', 'tpl', 'variables'), limit=None):
                        tpl['tpl'] = self.db.user.decrypt(userid, tpl['tpl'])
                        tpl['har'] = self.db.user.decrypt(userid, tpl['har'])
                        tpls.append(tpl)

                    tasks = []
                    for task in self.db.task.list(userid, fields=('id', 'tplid', 'retry_count', 'retry_interval','note', 'disabled', '_groups', 'init_env', 'env', 'ontimeflg', 'ontime', 'pushsw', 'newontime'), limit=None):
                        task['init_env'] = self.db.user.decrypt(userid, task['init_env'])
                        task['env'] = self.db.user.decrypt(userid, task['env']) if task['env'] else None
                        tasks.append(task)

                    backupdata = {}
                    backupdata['tpls'] = tpls
                    backupdata['tasks'] = tasks
                    savename = "{mail}_{now}.json".format(mail = user['email'], now=now)
                    if not aio_import:
                        raise Exception(u"更新容器后请先重启容器!") 
                    async with aiofiles.open(savename, 'w', encoding='utf-8') as fp:
                        await fp.write(json.dumps(backupdata, ensure_ascii=False, indent=4 ))
                        fp.close()
                    self.set_header ('Content-Type', 'application/octet-stream')
                    self.set_header ('Content-Disposition', 'attachment; filename='+savename)
                    async with aiofiles.open(savename, 'rb') as f:
                        while True:
                            data = await f.read(1024)
                            if not data:
                                break
                            self.write(data)
                            self.flush()
                    os.remove(savename)
                    await self.finish()
                    return
                    
                if ('recoverytplsbtn' in envs):
                    if ('recfile' in envs):
                        if envs['recfile'][:6] == 'SQLite':
                            raise Exception(u"抱歉，暂不支持通过本页面还原SQLite3数据库文件！(╥╯^╰╥)")
                        else:
                            try:
                                tpls = json.loads(envs['recfile'])['tpls']
                                tasks = json.loads(envs['recfile'])['tasks']
                            except:
                                raise Exception(u"抱歉，暂不支持通过本页面还原该备份文件！(ノ￣▽￣) \\r\\n \
                                请确认该文件来自于该页面\"备份\"按钮 (๑*◡*๑)。")
                        ids = []
                        for newtpl in tpls:
                            userid2 = int(userid)
                            har = self.db.user.encrypt(userid2, newtpl['har'])
                            tpl = self.db.user.encrypt(userid2, newtpl['tpl'])
                            variables = newtpl['variables']
                            newid = self.db.tpl.add(userid2, har, tpl, variables)
                            self.db.tpl.mod(newid, fork = newtpl['fork'],
                                                siteurl = newtpl['siteurl'],
                                                sitename = newtpl['sitename'],
                                                note = newtpl['note'],
                                                _groups = u'备份还原',
                                                banner = newtpl['banner']
                                            )
                            for task in tasks:
                                if (task['tplid'] == newtpl['id']):
                                    task['tplid'] = newid

                        for newtask in tasks:
                            userid2 = int(userid)
                            newtask['init_env'] = self.db.user.encrypt(userid2, newtask['init_env'])
                            newtask['env'] = self.db.user.encrypt(userid2, newtask['env'])
                            newtask['retry_count'] = newtask.get('retry_count',8)
                            newtask['retry_interval'] = newtask.get('retry_interval')
                            taskid = self.db.task.add(newtask['tplid'], userid, newtask['env'])
                            self.db.task.mod(taskid, disabled = newtask['disabled'],
                                                     init_env = newtask['init_env'],
                                                     session = None,
                                                     retry_count = newtask['retry_count'],
                                                     retry_interval = newtask['retry_interval'],
                                                     note = newtask['note'],
                                                     _groups = u'备份还原',
                                                     ontimeflg = newtask['ontimeflg'],
                                                     ontime = newtask['ontime'],
                                                     pushsw = newtask['pushsw'],
                                                     newontime = newtask['newontime']
                                            )
                        await self.render('utils_run_result.html', log=u"设置完成", title=u'设置成功', flg='success')
                        return
                    else:
                        raise Exception(u"请上传文件")
            else:
                raise Exception(u"账号/密码错误")   
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if (str(e).find('get user need id or email') > -1):
                e = u'请输入用户名/密码'
            await self.render('utils_run_result.html', log=str(e), title=u'设置失败', flg='danger')
            logger_Web_Handler.error('UserID: %s backup or restore Database failed! Reason: %s', userid or '-1', str(e))
            return
        return 
     
class toolbox_notpad_Handler(BaseHandler):
    @tornado.web.authenticated
    async def get(self,userid):
        user = self.current_user
        text_data = self.db.user.get(userid, fields=('notepad'))['notepad']
        await self.render('toolbox-notepad.html', text_data = text_data, userid=userid)
        return

    @tornado.web.authenticated
    async def post(self,userid):
        try:
            user = self.db.user.get(userid, fields=('role', 'email'))
            envs = {}
            for k, _  in self.request.body_arguments.items():
                envs[k] = self.get_body_argument(k)
            mail = envs['adminmail']
            pwd = envs['adminpwd']
            if self.db.user.challenge_MD5(mail, pwd) and (user['email'] == mail):
                if ('mode' in envs) and ('content' in envs):
                    if (envs['mode'] == 'write'):
                        new_data =  envs['content']
                    else:
                        data = self.db.user.get(userid, fields=('notepad'))['notepad']
                        if data is not None:
                            new_data = data + "\r\n" + envs['content']
                        else:
                            new_data = envs['content']

                    self.db.user.mod(userid, notepad=new_data)

                else:
                    raise Exception(u"参数错误")   
            else:
                raise Exception(u"账号/密码错误")   
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if (str(e).find('get user need id or email') > -1):
                e = u'请输入用户名/密码'
            await self.render('tpl_run_failed.html', log=str(e))
            logger_Web_Handler.error('UserID: %s modify Notepad_Toolbox failed! Reason: %s', userid or '-1', str(e))
            return
        return

class UserPushShowPvar(BaseHandler):
    @tornado.web.authenticated
    async def post(self,userid):
        try:
            user = self.db.user.get(userid, fields=('role', 'email'))
            envs = {}
            for k, _  in self.request.body_arguments.items():
                envs[k] = self.get_body_argument(k)
            mail = envs['adminmail']
            pwd = envs['adminpwd']
            if self.db.user.challenge_MD5(mail, pwd) and (user['email'] == mail):
                key = self.db.user.get(userid, fields=("barkurl", 'skey', 'wxpusher', 'qywx_token', 'tg_token', 'dingding_token'))
                log = u"""BarkUrl 前值：{bark}\r\nSendkey 前值：{skey}\r\nWxPusher 前值：{wxpusher}\r\n企业微信 前值：{qywx_token}\r\nTg Bot 前值：{tg_token}\r\nDingDing Bot 前值：{dingding_token}""".format(
                          bark = key['barkurl'],
                          skey = key['skey'],
                          wxpusher = key['wxpusher'],
                          qywx_token = key['qywx_token'],
                          tg_token = key['tg_token'],
                          dingding_token = key['dingding_token'])
                await self.render('utils_run_result.html', log=log, title=u'设置成功', flg='success')
                return
            else:
                raise Exception(u"账号/密码错误")   
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if (str(e).find('get user need id or email') > -1):
                e = u'请输入用户名/密码'
            await self.render('tpl_run_failed.html', log=str(e))
            logger_Web_Handler.error('UserID: %s show Push_settings failed! Reason: %s', userid or '-1', str(e))
            return

class custom_pusher_Handler(BaseHandler):
    @tornado.web.authenticated
    async def get(self,userid):
        diypusher = self.db.user.get(userid, fields=('diypusher'))['diypusher']
        diypusher = json.loads(diypusher) if (diypusher != '') else {'mode':'GET'}
        await self.render('user_register_cus_pusher.html', userid=userid, diypusher=diypusher)
        return
        
    @tornado.web.authenticated
    async def post(self,userid):
        try:
            envs = {}
            for k, _  in self.request.body_arguments.items():
                envs[k] = self.get_body_argument(k)
            req = pusher()
            log = ''
            now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            tmp = await gen.convert_yielded(req.cus_pusher_send(envs ,u'推送测试', now))
            if ('True' == tmp):
                if (envs['btn'] == 'regbtn'):
                    self.db.user.mod(userid, diypusher=json.dumps(envs))
            else:
                raise Exception(tmp)
            
            log = u'运行成功，请检查是否收到推送'
        except Exception as e:
            if (str(e).find('get user need id or email') > -1):
                e = u'请输入用户名/密码'
            await self.render('utils_run_result.html', log=str(e), title=u'设置失败', flg='danger')
            logger_Web_Handler.error('UserID: %s register or tes Cus_Pusher failed! Reason: %s', userid or '-1', str(e))
            if config.traceback_print:
                traceback.print_exc()
            return

        await self.render('utils_run_result.html', log=log, title=u'设置成功', flg='success')
        return

class UserSetNewPWDHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self,userid):
        email = self.db.user.get(userid, fields=('email'))['email']
        await self.render('user_setnewpwd.html', userid=userid, usermail=email)
        return
        
    @tornado.web.authenticated
    async def post(self,userid):
        try:
            log = u'设置成功'
            envs = {}
            for k, _  in self.request.body_arguments.items():
                envs[k] = self.get_body_argument(k)

            adminuser = self.db.user.get(email=envs['adminmail'], fields=('role', 'email'))
            newPWD = envs['newpwd']
            if self.db.user.challenge_MD5(envs['adminmail'], envs['adminpwd']) and (adminuser['role'] == 'admin'):
                if (len(newPWD) >= 6):
                    self.db.user.mod(userid, password=newPWD)
                    user = self.db.user.get(userid, fields=('email','password','password_md5'))
                    hash = MD5.new()
                    hash.update(newPWD.encode('utf-8'))
                    tmp = crypto.password_hash(hash.hexdigest(), self.db.user.decrypt(userid, user['password']))
                    if (user['password_md5'] != tmp):
                        self.db.user.mod(userid, password_md5=tmp)
                    if not (self.db.user.challenge(envs['usermail'], newPWD)):
                        raise Exception(u'修改失败')
                else:
                    raise Exception(u'密码长度要大于6位')    
            else:
                raise Exception(u'管理员用户名/密码错误')
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            await self.render('utils_run_result.html', log=str(e), title=u'设置失败', flg='danger')
            logger_Web_Handler.error('UserID: %s set New_Password failed! Reason: %s', userid or '-1', str(e))
            return

        await self.render('utils_run_result.html', log=log, title=u'设置成功', flg='success')
        return

handlers = [
        ('/user/(\d+)/pushsw', UserRegPushSw),
        ('/user/(\d+)/regpush', UserRegPush),
        ('/user/(\d+)/UserPushShowPvar', UserPushShowPvar),
        ('/user/(\d+)/manage', UserManagerHandler),
        ('/user/(\d+)/database', UserDBHandler),
        ('/util/toolbox/(\d+)/notepad', toolbox_notpad_Handler),
        ('/util/custom/(\d+)/pusher', custom_pusher_Handler),
        ('/user/(\d+)/setnewpwd', UserSetNewPWDHandler),
        ]
