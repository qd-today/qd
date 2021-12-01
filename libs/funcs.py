#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:

import sys
import json
import logging
import croniter
import traceback
import random
import time
import datetime

import config
from libs import utils
from tornado import gen
from libs.fetcher import Fetcher

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
            pubtpl = db.PubTplDB()
        self.db = DB
        self.fetcher = Fetcher()
    
    async def pusher(self, userid, pushsw, flg, title, content):
        notice = self.db.user.get(userid, fields=('skey', 'barkurl', 'noticeflg', 'wxpusher', 'qywx_token', 'tg_token', 'dingding_token', 'diypusher'))

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
            pusher["tgpushersw"] = False if (notice['noticeflg'] & 0x400) == 0 else True
            pusher["dingdingpushersw"] = False if (notice['noticeflg'] & 0x800) == 0 else True

            def nonepush(*args):
                return 

            if (pushsw['pushen']):
                send2bark = self.send2bark if (pusher["barksw"]) else nonepush
                send2s = self.send2s if (pusher["schansw"]) else nonepush 
                send2wxpusher = self.send2wxpusher if (pusher["wxpushersw"]) else nonepush 
                sendmail = self.sendmail if (pusher["mailpushersw"]) else nonepush 
                cus_pusher_send = self.cus_pusher_send if (pusher["cuspushersw"]) else nonepush 
                qywx_pusher_send = self.qywx_pusher_send if (pusher["qywxpushersw"]) else nonepush 
                send2tg = self.send2tg if (pusher["tgpushersw"]) else nonepush 
                send2dingding = self.send2dingding if (pusher["dingdingpushersw"]) else nonepush 


            if (pushsw['pushen']):
                await gen.convert_yielded([send2bark(notice['barkurl'], title, content),
                                           send2s(notice['skey'], title, content),
                                           send2wxpusher( notice['wxpusher'], title+u"  "+content),
                                           sendmail( user['email'], title, content),
                                           cus_pusher_send( diypusher, title, content),
                                           qywx_pusher_send( notice['qywx_token'], title, content),
                                           send2tg( notice['tg_token'], title, content),
                                           send2dingding(notice['dingding_token'], title, content)])

    async def send2bark(self, barklink, title, content):
        r = 'False'
        try:
            link = barklink
            if (link[-1] != '/'): link=link+'/'
            content = content.replace('\\r\\n','\n')
            d = {"title":title,"body":content}
            obj = {'request': {'method': 'POST', 'url': link, 'headers': [{'name' : 'Content-Type', 'value': 'application/json; charset=UTF-8'}], 'cookies': [], 'data':json.dumps(d)}, 'rule': {
                   'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
            _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
            r = 'True'
        except Exception as e:
            r = traceback.format_exc()
            print(r)
        
        return r
        
    async def send2s(self, skey, title, content):
        r = 'False'
        if (skey != ""):
            try:
                link = u"https://sctapi.ftqq.com/{0}.send".format(skey.replace(".send", ""))
                content = content.replace('\\r\\n','\n\n')
                d = {'text': title, 'desp': content}
                obj = {'request': {'method': 'POST', 'url': link, 'headers': [{'name' : 'Content-Type', 'value': 'application/x-www-form-urlencoded; charset=UTF-8'}], 'cookies': [], 'data':utils.urllib.parse.urlencode(d)}, 'rule': {
                   'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
                r = 'True'
            except Exception as e:
                r = traceback.format_exc()
                print(r)
        return r   
    
    async def send2tg(self, tg_token, title, content):
        r = 'False'
        tmp = tg_token.split(';')
        tgToken = ''
        tgUserId = ''
        if len(tmp) >= 2:
            tgToken = tmp[0]
            tgUserId = tmp[1]
            tgHost = tmp[2] if len(tmp) >= 3 else ''
            proxy = utils.parse_url(tmp[3]) if len(tmp) >= 4 else ''
            pic = tmp[4] if len(tmp) >= 5 else ''
        if tgToken and tgUserId:
            try:
                token = tgToken
                chat_id = tgUserId
                #TG_BOT的token
                #token = os.environ.get('TG_TOKEN')
                #用户的ID
                #chat_id = os.environ.get('TG_USERID')
                if not tgHost:
                    link = u'https://api.telegram.org/bot{0}/sendMessage'.format(token)
                else:
                    if tgHost[-1]!='/':
                        tgHost = tgHost + '/'
                    if 'http://' in tgHost or 'https://' in tgHost:
                        link = u'{0}bot{1}/sendMessage'.format(tgHost,token)
                    else:
                        link = u'https://{0}bot{1}/sendMessage'.format(tgHost,token)
                picurl = config.push_pic if pic == '' else pic
                content = content.replace('\\r\\n','</pre>\n<pre>')
                d = {'chat_id': str(chat_id), 'text': '<b>' + title + '</b>' + '\n<pre>' + content + '</pre>\n' + '------<a href="' + picurl + '">QianDao提醒</a>------', 'disable_web_page_preview':'false', 'parse_mode': 'HTML'}
                obj = {'request': {'method': 'POST', 'url': link, 'headers': [{'name' : 'Content-Type', 'value': 'application/json; charset=UTF-8'}], 'cookies': [], 'data':json.dumps(d)}, 'rule': {
                   'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                if proxy:
                    _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj, proxy = proxy))
                else:
                    _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
                r = 'True'
            except Exception as e:
                r = traceback.format_exc()
                print(r)
        return r

    async def send2dingding(self, dingding_token, title, content):
        r = 'False'
        tmp = dingding_token.split(';')
        if len(tmp) >= 1:
            dingding_token = tmp[0]
            pic = tmp[1] if len(tmp) >= 2 else ''
        if (dingding_token != ""):
            try:
                link = u"https://oapi.dingtalk.com/robot/send?access_token={0}".format(dingding_token)
                picurl = config.push_pic if pic == '' else pic
                content = content.replace('\\r\\n','\n\n > ')
                d = {"msgtype":"markdown","markdown":{"title":title,"text":"![QianDao](" + picurl + ")\n " + "#### "+ title + "\n > " +content}}
                obj = {'request': {'method': 'POST', 'url': link, 'headers': [{'name' : 'Content-Type', 'value': 'application/json; charset=UTF-8'}], 'cookies': [], 'data':json.dumps(d)}, 'rule': {
                   'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
                r = 'True'
            except Exception as e:
                r = traceback.format_exc()
                print(r)
        return r   

    async def send2wxpusher(self, wxpusher, content):
        r = 'False'
        temp = wxpusher.split(";")
        wxpusher_token = temp[0] if (len(temp) >= 2) else ""
        wxpusher_uid = temp[1] if (len(temp) >= 2) else "" 
        if (wxpusher_token != "") and (wxpusher_uid != ""):
            try:
                link = "http://wxpusher.zjiecode.com/api/send/message"
                content = content.replace('\\r\\n','\n')
                d = {
                        "appToken":wxpusher_token,
                        "content":content,
                        "contentType":3,
                        "uids":[
                            wxpusher_uid
                        ]
                    }
                obj = {'request': {'method': 'POST', 'url': link, 'headers': [{'name' : 'Content-Type', 'value': 'application/json; charset=UTF-8'}], 'cookies': [], 'data':json.dumps(d)}, 'rule': {
                   'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
                r = 'True'
            except Exception as e:
                r = traceback.format_exc()
                print(r)

        return  r  


    async def cus_pusher_send(self, diypusher, t, log):
        r = 'False'
        try:
            curltmp = diypusher['curl'].format(log=log, t=t)
            
            if (diypusher['headers']):
                headerstmp = json.loads(diypusher['headers'].replace('{log}', log).replace("{t}", t))
            else:
                headerstmp = {}

            if (diypusher['mode'] == 'POST'):
                postDatatmp = diypusher['postData'].replace('{log}', log).replace("{t}", t)
                if (postDatatmp != ''):
                    postDatatmp = json.loads(postDatatmp)
                if headerstmp:
                    headerstmp.pop('content-type','')
                    headerstmp.pop('Content-Type','')
                if (diypusher['postMethod'] == 'x-www-form-urlencoded'):
                    headerstmp['Content-Type'] = "application/x-www-form-urlencoded; charset=UTF-8"
                    headerstmp = [{'name': name, 'value': headerstmp[name]} for name in headerstmp]
                    obj = {'request': {'method': 'POST', 'url': curltmp, 'headers': headerstmp, 'cookies': [], 'data':utils.urllib.parse.urlencode(postDatatmp)}, 'rule': {
                        'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                else:
                    headerstmp['Content-Type'] = "application/json; charset=UTF-8"
                    headerstmp = [{'name': name, 'value': headerstmp[name]} for name in headerstmp]
                    obj = {'request': {'method': 'POST', 'url': curltmp, 'headers': headerstmp, 'cookies': [], 'data':json.dumps(postDatatmp)}, 'rule': {
                        'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
            elif (diypusher['mode'] == 'GET'):
                headerstmp = [{'name': name, 'value': headerstmp[name]} for name in headerstmp]
                obj = {'request': {'method': 'GET', 'url': curltmp, 'headers': headerstmp, 'cookies': []}, 'rule': {
                   'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
            else:
                raise Exception(u'模式未选择')
            _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))

            if (res.code == 200):
                r = "True"

        except Exception as e:
            r = traceback.format_exc()
        return r

    async def qywx_pusher_send(self, qywx_token, t, log):
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
            
            access_url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={id}&corpsecret={secret}'.format(id=qywx[u'企业ID'], secret=qywx[u'应用密钥'])
            obj = {'request': {'method': 'GET', 'url': access_url, 'headers': [], 'cookies': []}, 'rule': {
                   'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
            _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
            get_access_token_res = json.loads(res.body)
            if (get_access_token_res['access_token'] != '' and get_access_token_res['errmsg'] == 'ok'):
                msgUrl = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={0}'.format(get_access_token_res['access_token'])
                postData = {"touser" : "@all",
                            "msgtype" : "news",
                            "agentid" : qywx[u'应用ID'],
                            "news" : {
                                "articles" : [
                                        {
                                            "title" : t,
                                            "description" : log.replace("\\r\\n","\n" ),
                                            "url" : "",
                                            "picurl" : config.push_pic if qywx[u'图片'] == '' else qywx[u'图片']
                                        }
                                    ]
                            }
                }
                obj = {'request': {'method': 'POST', 'url': msgUrl, 'headers': [{'name' : 'Content-Type', 'value': 'application/json; charset=UTF-8'}], 'cookies': [], 'data':json.dumps(postData)}, 'rule': {
                   'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                _,_,msg_res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
                tmp = json.loads(msg_res.body)
                if (tmp['errmsg'] == 'ok' and tmp['errcode'] == 0):
                    r = 'True'

        except Exception as e:
            r = traceback.format_exc()
            print(r)
        return r

    async def sendmail(self, email, title, content):
        user = self.db.user.get(email=email, fields=('id', 'email', 'email_verified', 'nickname'))
        if user['email'] and user['email_verified']:
            try:
                content = content.replace('\\r\\n','\n')
                await gen.convert_yielded(utils.send_mail(to = email, 
                                subject = u"在网站{0} {1}".format(config.domain, title),
                                text = content,
                                shark=True))
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
