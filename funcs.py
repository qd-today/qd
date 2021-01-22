#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:

import sys
import json
import logging
import croniter
import requests
import traceback
import random
import time
import datetime

import config
from libs import utils


class pusher(object):
    def __init__(self):
        if config.db_type == 'sqlite3':
            import sqlite3_db as db
        else:
            import db
            
        class DB(object):
            user = db.UserDB()
            tpl = db.TPLDB()
            task = db.TaskDB()
            tasklog = db.TaskLogDB()
            site = db.SiteDB()

        self.db = DB
    
    def pusher(self, userid, pushsw, flg, title, content):
        notice = self.db.user.get(userid, fields=('skey', 'barkurl', 'noticeflg', 'wxpusher', 'qywx_token', 'diypusher'))

        if (notice['noticeflg'] & flg != 0):
            user = self.db.user.get(userid, fields=('id', 'email', 'email_verified', 'nickname'))
            diypusher = notice['diypusher']
            if (diypusher != ''):diypusher = json.loads(diypusher)
            self.barklink =  notice['barkurl']
            pusher =  {}
            pusher["mailpushersw"] = False if (notice['noticeflg'] & 0x80) == 0 else True
            pusher["barksw"] = False if (notice['noticeflg'] & 0x40) == 0 else True 
            pusher["schansw"] = False if (notice['noticeflg'] & 0x20) == 0 else True 
            pusher["wxpushersw"] = False if (notice['noticeflg'] & 0x10) == 0 else True
            pusher["cuspushersw"] = False if (notice['noticeflg'] & 0x100) == 0 else True
            pusher["qywxpushersw"] = False if (notice['noticeflg'] & 0x200) == 0 else True
        
            if (pushsw['pushen']):
                if (pusher["barksw"]):
                    self.send2bark(notice['barkurl'], title, content)
                if (pusher["schansw"]):
                    self.send2s(notice['skey'], title, content)
                if (pusher["wxpushersw"]):
                    self.send2wxpusher(notice['wxpusher'], title+u"  "+content)
                if (pusher["mailpushersw"]):
                        self.sendmail(user['email'], title, content)
                if (pusher["cuspushersw"]):
                    self.cus_pusher_send(diypusher, title, content)
                if (pusher["qywxpushersw"]):
                    self.qywx_pusher_send(notice['qywx_token'], title, content)


    def send2bark(self, barklink, title, content):
        r = 'False'
        try:
            msg = {"title":title,"body":content}
            res = requests.post(barklink, data=msg, verify=False)
            r = 'True'
        except Exception as e:
            r = traceback.format_exc()
            print(r)
        
        return r
        
    def send2s(self, skey, title, content):
        r = 'False'
        if (skey != ""):
            try:
                link = u"https://sc.ftqq.com/{0}.send".format(skey.replace(".send", ""))
                d = {'text': title, 'desp': content}
                res = requests.post(link, data=d , verify=False)
                r = 'True'
            except Exception as e:
                r = traceback.format_exc()
                print(r)
        return r   
    
    def send2wxpusher(self, wxpusher, content):
        r = 'False'
        temp = wxpusher.split(";")
        wxpusher_token = temp[0] if (len(temp) >= 2) else ""
        wxpusher_uid = temp[1] if (len(temp) >= 2) else "" 
        if (wxpusher_token != "") and (wxpusher_uid != ""):
            try:
                link = "http://wxpusher.zjiecode.com/api/send/message"
                d = {
                        "appToken":wxpusher_token,
                        "content":content,
                        "contentType":3,
                        "uids":[
                            wxpusher_uid
                        ]
                    }
                res = requests.post(link, json=d , verify=False)
                r = 'True'
            except Exception as e:
                r = traceback.format_exc()
                print(r)

        return  r  


    def cus_pusher_send(self, diypusher, t, log):
        r = 'False'
        try:
            curltmp = diypusher['curl'].format(log=log, t=t)
            
            if (diypusher['headers']):
                headerstmp = diypusher['headers'].replace('{log}', log).replace("{t}", t)
                res = requests.get(curltmp, headers=headerstmp, verify=False)
            else:
                headerstmp = ''

            if (diypusher['mode'] == 'POST'):
                postDatatmp = diypusher['postData'].replace('{log}', log).replace("{t}", t)
                if (postDatatmp != ''):
                    postDatatmp = json.loads(postDatatmp)
                if (diypusher['postMethod'] == 'x-www-form-urlencoded'):
                    res = requests.post(curltmp, headers=headerstmp, data=postDatatmp, verify=False)
                else:
                    res = requests.post(curltmp, headers=headerstmp, json=postDatatmp, verify=False)
            elif (diypusher['mode'] == 'GET'):
                res = requests.get(curltmp, headers=headerstmp, verify=False)
            else:
                raise Exception(u'模式未选择')

            if (res.status_code == 200):
                r = "True"

        except Exception as e:
            r = traceback.format_exc()
        return r

    def qywx_pusher_send(self, qywx_token, t, log):
        r = 'False'
        try:
            qywx = {}
            tmp = qywx_token.split(';')
            if len(tmp) >= 3:
                qywx[u'企业ID'] = tmp[0]
                qywx[u'应用ID'] = tmp[1]
                qywx[u'应用密钥'] = tmp[2]
                qywx[u'图片'] = tmp[3] if len(tmp) >= 4 else ''
            else:
                raise Exception(u'企业微信token错误')
            
            get_access_token_res = requests.get('https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={id}&corpsecret={secret}'.format(id=qywx[u'企业ID'], secret=qywx[u'应用密钥']), 
                                verify=False).json()
            if (get_access_token_res['access_token'] != '' and get_access_token_res['errmsg'] == 'ok'):
                msgUrl = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={0}'.format(get_access_token_res['access_token'])
                postData = {"touser" : "@all",
                            "msgtype" : "news",
                            "agentid" : qywx[u'应用ID'],
                            "news" : {
                                "articles" : [
                                        {
                                            "title" : t,
                                            "description" : log,
                                            "url" : "URL",
                                            "picurl" : "https://i.loli.net/2021/01/17/m15J86CEZnqKF9U.png" if qywx[u'图片'] == '' else qywx[u'图片']
                                        }
                                    ]
                            }
                }
                msg_res = requests.post(msgUrl, data=json.dumps(postData), verify=False)
                tmp = msg_res.json()
                if (tmp['errmsg'] == 'ok' and tmp['errcode'] == 0):
                    r = 'True'

        except Exception as e:
            r = traceback.format_exc()
            print(r)
        return r

    def sendmail(self, email, title, content):
        user = self.db.user.get(email=email, fields=('id', 'email', 'email_verified', 'nickname'))
        if user['email'] and user['email_verified']:
            try:
                utils.send_mail(to = email, 
                                subject = u"在网站{0} {1}".format(config.domain, title),
                                text = content,
                                async=True)
            except Exception as e:
                logging.error('tasend mail error: %r', e)

class cal(object):
    def __init__(self):
        pass
    
    def calNextTs(self, envs):
        r = {"r":"True"}
        try:
            if (envs['mode'] == 'ontime'): 
                t = '{0} {1}'.format(envs['date'], envs['time'])
            elif (envs['mode'] == 'cron'):
                cron = croniter.croniter(envs['cron_val'], datetime.datetime.now())
                t = cron.get_next(datetime.datetime).strftime("%Y-%m-%d %H:%M:%S")
            else:
                raise Exception(u'参数错误')

            d = datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S").timetuple()
            ts = int(time.mktime(d))

            if ('randsw' in envs):
                if (envs['sw'] and envs['randsw']):
                    r_ts = random.randint(int(envs['tz1']), int(envs['tz2']))
                    ts = ts + r_ts

            if ('cron_sec' in envs):
                r_ts = 0 if (envs['cron_sec'] == '') else int(envs['cron_sec'])
                ts = ts + r_ts
                
            r['ts'] = ts
        except Exception :
            r['r'] = traceback.format_exc()
            print(r['r'] )
        return r