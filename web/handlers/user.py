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
import re

from base import *

import send2phone 
from web.handlers.task import calNextTimestamp

class UserRegPush(BaseHandler):
    @tornado.web.authenticated
    def get(self, userid):
        self.render('user_register_pusher.html', userid=userid)
    
    @tornado.web.authenticated
    def post(self, userid):
        env = json.loads(self.request.body_arguments['env'][0])
        token = env["wxpusher_token"]
        uid = env["wxpusher_uid"]
        skey = env["skey"]
        barkurl = env["barkurl"]
        log = ""
        if  ("reg" == self.request.body_arguments['func'][0]):
            try:
                if  (token != "") and (uid != ""):
                    temp = token + ";" + uid
                    self.db.user.mod(userid, wxpusher = temp)
                    if (self.db.user.get(userid, fields=("wxpusher"))["wxpusher"] == temp):
                        log = u"注册 wxpusher 成功\r\n"
                    else:
                        log = u"注册 wxpusher 失败\r\n"

                if (skey != ""):
                    self.db.user.mod(userid, skey = skey)
                    if (self.db.user.get(userid, fields=("skey"))["skey"] == skey):
                        log = log+u"注册 S酱 成功\r\n"
                    else:
                        log = log+u"注册 S酱 失败\r\n"
                    
                if  (barkurl != ""):
                    self.db.user.mod(userid, barkurl = barkurl)
                    if (self.db.user.get(userid, fields=("barkurl"))["barkurl"] == barkurl):
                        log = log+u"注册 Bark 成功\r\n"
                    else:
                        log = log+u"注册 Bark 失败\r\n"
            except Exception as e:
                self.render('tpl_run_failed.html', log=e)
                return
            
            self.render('tpl_run_success.html', log=log)
            return

        else:
            try:
                t = datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S')

                if  (token != "") and (uid != ""):
                    push = send2phone.send2phone(wxpusher_token=token, wxpusher_uid=uid)
                    push.send2wxpusher(u"{t} 发送测试".format(t=t))

                if (skey != ""):
                    push = send2phone.send2phone(skey=skey)
                    push.send2s(u"正在测试S酱", u"{t} 发送测试".format(t=t))

                if  (barkurl != ""):
                    push = send2phone.send2phone(barkurl=barkurl)
                    push.send2bark(u"正在测试Bark", u"{t} 发送测试".format(t=t))

            except Exception as e:
                self.render('tpl_run_failed.html', log=e)
                return
            
            self.render('tpl_run_success.html', log=u"请检查是否受到推送")
            return

class UserRegPushSw(BaseHandler):
    @tornado.web.authenticated
    def get(self, userid):
        tasks = []
        for task in self.db.task.list(userid, fields=('id', 'tplid', 'note', 'disabled', 'ctime', 'pushsw'), limit=None):
            tpl = self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note') )
            task['tpl'] = tpl
            task['pushsw'] = json.loads(task['pushsw'])
            tasks.append(task)
        temp = self.db.user.get(userid, fields=('noticeflg'))
        temp = temp['noticeflg']
        flg = {}
        flg['barksw']        = False if ((temp & 0x40) == 0) else True 
        flg['schansw']       = False if ((temp & 0x20) == 0) else True 
        flg['wxpushersw']    = False if ((temp & 0x10) == 0) else True 
        flg['handpush_succ'] = False if ((temp & 0x08) == 0) else True 
        flg['handpush_fail'] = False if ((temp & 0x04) == 0) else True 
        flg['autopush_succ'] = False if ((temp & 0x02) == 0) else True 
        flg['autopush_fail'] = False if ((temp & 0x01) == 0) else True
        logtime = json.loads(self.db.user.get(userid, fields=('logtime'))['logtime'])
        if 'schanEN' not in logtime:logtime['schanEN'] = False
        if 'WXPEn' not in logtime:logtime['WXPEn'] = False

        self.render('user_register_pushsw.html', userid=userid, flg=flg, tasks=tasks, logtime=logtime)

    @tornado.web.authenticated
    def post(self, userid):
        try:
            tasks = []
            for task in self.db.task.list(userid, fields=('id', 'tplid', 'note', 'disabled', 'ctime', 'pushsw'), limit=None):
                tpl = self.db.tpl.get(task['tplid'], fields=('id', 'userid', 'sitename', 'siteurl', 'banner', 'note') )
                task['tpl'] = tpl
                task['pushsw'] = json.loads(task['pushsw'])
                task['pushsw']["logen"] = False
                task['pushsw']["pushen"] = False
                tasks.append(task)
            temp = self.db.user.get(userid, fields=('noticeflg'))
            logtime = json.loads(self.db.user.get(userid, fields=('logtime'))['logtime'])
            env = json.loads(self.request.body_arguments['env'][0])

            barksw_flg        = 1 if ("barksw" in env) else 0 
            schansw_flg       = 1 if ("schansw" in env) else 0 
            wxpushersw_flg    = 1 if ("wxpushersw" in env) else 0 
            handpush_succ_flg = 1 if ("handpush_succ" in env) else 0
            handpush_fail_flg = 1 if ("handpush_fail" in env) else 0
            autopush_succ_flg = 1 if ("autopush_succ" in env) else 0
            autopush_fail_flg = 1 if ("autopush_fail" in env) else 0
            
            flg = (barksw_flg << 6) \
                | (schansw_flg << 5) \
                | (wxpushersw_flg << 4) \
                | (handpush_succ_flg << 3) \
                | (handpush_fail_flg << 2) \
                | (autopush_succ_flg << 1) \
                | (autopush_fail_flg)
            logtime['en'] = True if ('logensw' in env) else False
            logtime['time'] = env['timevalue']
            logtime['schanEn'] = True if ('schanlogsw' in env) else False
            logtime['WXPEn'] = True if ('wxpusherlogsw' in env) else False

            next_ts = calNextTimestamp(logtime['time'])
            logtime['ts'] = next_ts

            for e in env:
                temp = re.findall(r"(.+?)logen", e)
                if len(temp) > 0:
                    taskid = int(temp[0])
                    for task in tasks:
                        if (taskid == task["id"]):
                            task['pushsw']["logen"] = True
                            
                temp = re.findall(r"(.+?)pushen", e)
                if len(temp) > 0:
                    taskid = int(temp[0])
                    for task in tasks:
                        if (taskid == task["id"]):
                            task['pushsw']["pushen"] = True
                            
            self.db.user.mod(userid, noticeflg=flg, logtime=json.dumps(logtime))
            for task in tasks:
                self.db.task.mod(task["id"], pushsw=json.dumps(task['pushsw']))
        except Exception as e:
            self.render('tpl_run_failed.html', log=e)
            return
            
        self.render('tpl_run_success.html', log=u"设置完成")
        return

class UserRegPush(BaseHandler):
    @tornado.web.authenticated
    def get(self, userid):
        self.render('user_register_pusher.html', userid=userid)
    
    @tornado.web.authenticated
    def post(self, userid):
        env = json.loads(self.request.body_arguments['env'][0])
        token = env["wxpusher_token"]
        uid = env["wxpusher_uid"]
        skey = env["skey"]
        barkurl = env["barkurl"]
        log = ""
        if  ("reg" == self.request.body_arguments['func'][0]):
            try:
                if  (token != "") and (uid != ""):
                    temp = token + ";" + uid
                    self.db.user.mod(userid, wxpusher = temp)
                    if (self.db.user.get(userid, fields=("wxpusher"))["wxpusher"] == temp):
                        log = u"注册 wxpusher 成功\r\n"
                    else:
                        log = u"注册 wxpusher 失败\r\n"

                if (skey != ""):
                    self.db.user.mod(userid, skey = skey)
                    if (self.db.user.get(userid, fields=("skey"))["skey"] == skey):
                        log = log+u"注册 S酱 成功\r\n"
                    else:
                        log = log+u"注册 S酱 失败\r\n"
                    
                if  (barkurl != ""):
                    self.db.user.mod(userid, barkurl = barkurl)
                    if (self.db.user.get(userid, fields=("barkurl"))["barkurl"] == barkurl):
                        log = log+u"注册 Bark 成功\r\n"
                    else:
                        log = log+u"注册 Bark 失败\r\n"
            except Exception as e:
                self.render('tpl_run_failed.html', log=e)
                return
            
            self.render('tpl_run_success.html', log=log)
            return

        else:
            try:
                t = datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S')

                if  (token != "") and (uid != ""):
                    push = send2phone.send2phone(wxpusher_token=token, wxpusher_uid=uid)
                    push.send2wxpusher(u"{t} 发送测试".format(t=t))

                if (skey != ""):
                    push = send2phone.send2phone(skey=skey)
                    push.send2s(u"正在测试S酱", u"{t} 发送测试".format(t=t))

                if  (barkurl != ""):
                    push = send2phone.send2phone(barkurl=barkurl)
                    push.send2bark(u"正在测试Bark", u"{t} 发送测试".format(t=t))

            except Exception as e:
                self.render('tpl_run_failed.html', log=e)
                return
            
            self.render('tpl_run_success.html', log=u"请检查是否受到推送")
            return
     
handlers = [
        ('/user/(\d+)/pushsw', UserRegPushSw),
        ('/user/(\d+)/regpush', UserRegPush),
        ]
