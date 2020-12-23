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
import os

import config
from base import *

import sqlite3

import send2phone 
from web.handlers.task import calNextTimestamp

from backup import DBnew

import codecs

def tostr(s):
    if isinstance(s, bytearray):
        return str(s)
    return s

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
                else:
                    log = u"wxpusher 未填写完整\r\n"

                if (skey != ""):
                    self.db.user.mod(userid, skey = skey)
                    if (self.db.user.get(userid, fields=("skey"))["skey"] == skey):
                        log = log+u"注册 S酱 成功\r\n"
                    else:
                        log = log+u"注册 S酱 失败\r\n"
                else:
                    log = log+u"skey 未填写完整\r\n"
                    
                if (barkurl != ""):
                    self.db.user.mod(userid, barkurl = barkurl)
                    if (self.db.user.get(userid, fields=("barkurl"))["barkurl"] == barkurl):
                        log = log+u"注册 Bark 成功\r\n"
                    else:
                        log = log+u"注册 Bark 失败\r\n"
                else:
                    log = log+u"Bark 未填写完整\r\n"

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
                    log = u"wxpusher 已推送\r\n"
                else:
                    log = u"wxpusher 未填写完整\r\n"

                if (skey != ""):
                    push = send2phone.send2phone(skey=skey)
                    push.send2s(u"正在测试S酱", u"{t} 发送测试".format(t=t))
                    log = log+u"S酱 已推送\r\n"
                else:
                    log = log+u"skey 未填写完整\r\n"

                if  (barkurl != ""):
                    push = send2phone.send2phone(barkurl=barkurl)
                    push.send2bark(u"正在测试Bark", u"{t} 发送测试".format(t=t))
                    log = log+u"Bark 已推送\r\n"
                else:
                    log = log+u"Bark 未填写完整\r\n"

            except Exception as e:
                self.render('tpl_run_failed.html', log=e)
                return
            
            self.render('tpl_run_success.html', log=log)
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
        flg['mailpushersw']    = False if ((temp & 0x80) == 0) else True 
        flg['handpush_succ'] = False if ((temp & 0x08) == 0) else True 
        flg['handpush_fail'] = False if ((temp & 0x04) == 0) else True 
        flg['autopush_succ'] = False if ((temp & 0x02) == 0) else True 
        flg['autopush_fail'] = False if ((temp & 0x01) == 0) else True
        logtime = json.loads(self.db.user.get(userid, fields=('logtime'))['logtime'])
        if 'schanEN' not in logtime:logtime['schanEN'] = False
        if 'WXPEn' not in logtime:logtime['WXPEn'] = False
        if 'ErrTolerateCnt' not in logtime:logtime['ErrTolerateCnt'] = 0
        

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

            env = json.loads(self.request.body_arguments['env'][0])
            
            logtime = json.loads(self.db.user.get(userid, fields=('logtime'))['logtime'])
            if 'ErrTolerateCnt' not in logtime:logtime['ErrTolerateCnt'] = 0
            if (logtime['ErrTolerateCnt'] != int(env['ErrTolerateCnt'])):
                logtime['ErrTolerateCnt'] = int(env['ErrTolerateCnt'])
                self.db.user.mod(userid, logtime=json.dumps(logtime))

            barksw_flg        = 1 if ("barksw" in env) else 0 
            schansw_flg       = 1 if ("schansw" in env) else 0 
            wxpushersw_flg    = 1 if ("wxpushersw" in env) else 0
            mailpushersw_flg    = 1 if ("mailpushersw" in env) else 0 
            handpush_succ_flg = 1 if ("handpush_succ" in env) else 0
            handpush_fail_flg = 1 if ("handpush_fail" in env) else 0
            autopush_succ_flg = 1 if ("autopush_succ" in env) else 0
            autopush_fail_flg = 1 if ("autopush_fail" in env) else 0
            
            flg = (mailpushersw_flg << 7) \
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
            self.render('tpl_run_failed.html', log=e)
            return
            
        self.render('tpl_run_success.html', log=u"设置完成")
        return
    
class UserManagerHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, userid):
        adminflg = False
        users = []
        user = self.db.user.get(userid, fields=('role'))
        if user and user['role'] == "admin":
            adminflg = True
            users = []
            for user in self.db.user.list(fields=('id','status', 'role', 'ctime', 'email', 'atime', 'email_verified')):
                if user['role'] != 'admin':
                    if (user['email_verified'] == 0):
                        user['email_verified'] = False
                    else:
                        user['email_verified'] = True
                    users.append(user)

        self.render("user_manage.html", users=users, userid=userid, adminflg=adminflg)
        return

    @tornado.web.authenticated
    def post(self, userid):
        try:
            user = self.db.user.get(userid, fields=('role'))
            if user and user['role'] == "admin":
                envs = self.request.body_arguments
                mail = envs['adminmail'][0]
                pwd = u"{0}".format(envs['adminpwd'][0])
                if self.db.user.challenge(mail, pwd):
                    Target_users = []
                    for key, value in envs.items():
                        if value[0] == "on":
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
            self.render('tpl_run_failed.html', log=e)
            return
            
        self.redirect('/my/')
        return

class UserDBHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, userid):
        adminflg = False
        user = self.db.user.get(userid, fields=('role'))
        if user and user['role'] == "admin":
            adminflg = True 
        self.render("DB_manage.html", userid=userid, adminflg=adminflg)
        return
    
    @tornado.web.authenticated
    def post(self, userid):
        try:
            user = self.db.user.get(userid, fields=('role', 'email'))
            envs = self.request.body_arguments
            mail = envs['adminmail'][0]
            pwd = u"{0}".format(envs['adminpwd'][0])
            now=datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            if self.db.user.challenge(mail, pwd) and (user['email'] == mail):
                if ('backupbtn' in envs):
                    if user and user['role'] == "admin":
                        filename = config.sqlite3.path
                        savename = "database_{now}.db".format(now=now)
                        self.set_header ('Content-Type', 'application/octet-stream')
                        self.set_header ('Content-Disposition', 'attachment; filename='+savename)
                        with open(filename, 'rb') as f:
                            while True:
                                data = f.read(1024)
                                if not data:
                                    break
                                self.write(data)
                        self.finish()
                        return
                    else:
                        raise Exception(u"管理员才能备份数据库") 

                if ('backuptplsbtn' in envs):
                    tpls = []
                    for tpl in self.db.tpl.list(userid=userid, fields=('id', 'siteurl', 'sitename', 'banner', 'note','fork', 'groups', 'har', 'tpl', 'variables'), limit=None):
                        tpl['tpl'] = self.db.user.decrypt(userid, tpl['tpl'])
                        tpl['har'] = self.db.user.decrypt(userid, tpl['har'])
                        tpls.append(tpl)

                    tasks = []
                    for task in self.db.task.list(userid, fields=('id', 'tplid', 'note', 'disabled', 'groups', 'init_env', 'env', 'ontimeflg', 'ontime', 'pushsw', 'newontime'), limit=None):
                        task['init_env'] = self.db.user.decrypt(userid, task['init_env'])
                        task['env'] = self.db.user.decrypt(userid, task['env']) if task['env'] else None
                        tasks.append(task)

                    backupdata = {}
                    backupdata['tpls'] = tpls
                    backupdata['tasks'] = tasks
                    savename = "{mail}_{now}.json".format(mail = user['email'], now=now)
                    fp = codecs.open(savename, 'w', 'utf-8')
                    fp.write(json.dumps(backupdata, ensure_ascii=False, indent=4 ))
                    fp.close()
                    self.set_header ('Content-Type', 'application/octet-stream')
                    self.set_header ('Content-Disposition', 'attachment; filename='+savename)
                    with open(savename, 'rb') as f:
                        while True:
                            data = f.read(1024)
                            if not data:
                                break
                            self.write(data)
                    os.remove(savename)
                    self.finish()
                    return
                    
                if ('recoverytplsbtn' in envs):
                    if ('recfile' in envs):
                        tpls = json.loads(envs['recfile'][0])['tpls']
                        tasks = json.loads(envs['recfile'][0])['tasks']
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
                                                groups = u'备份还原',
                                                banner = newtpl['banner']
                                            )
                            for task in tasks:
                                if (task['tplid'] == newtpl['id']):
                                    task['tplid'] = newid

                        for newtask in tasks:
                            userid2 = int(userid)
                            newtask['init_env'] = self.db.user.encrypt(userid2, newtask['init_env'])
                            newtask['env'] = self.db.user.encrypt(userid2, newtask['env'])
                            taskid = self.db.task.add(newtask['tplid'], userid, newtask['env'])
                            self.db.task.mod(taskid, disabled = newtask['disabled'],
                                                     init_env = newtask['init_env'],
                                                     session = None,
                                                     note = newtask['note'],
                                                     groups = u'备份还原',
                                                     ontimeflg = newtask['ontimeflg'],
                                                     ontime = newtask['ontime'],
                                                     pushsw = newtask['pushsw'],
                                                     newontime = newtask['newontime']
                                            )

                        self.render('tpl_run_success.html', log=u"设置完成")
                        return
                    else:
                        raise Exception(u"请上传文件")
            else:
                raise Exception(u"账号/密码错误")   
        except Exception as e:
            if (str(e).find('get user need id or email') > -1):
                e = u'请输入用户名/密码'
            self.render('tpl_run_failed.html', log=e)
            return
        return
     
handlers = [
        ('/user/(\d+)/pushsw', UserRegPushSw),
        ('/user/(\d+)/regpush', UserRegPush),
        ('/user/(\d+)/manage', UserManagerHandler),
        ('/user/(\d+)/database', UserDBHandler),
        ]
