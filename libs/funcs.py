#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:

import os
import sys
import json
import croniter
import traceback
import random
import time
import datetime
import requests
import asyncio
import functools

import config
from db import DB
from libs import utils
from tornado import gen
from libs.fetcher import Fetcher
from .log import Log

logger_Funcs = Log('qiandao.Http.Funcs').getlogger()
class pusher(object):
    def __init__(self,db=DB(),sql_session=None):
        self.db = db
        self.fetcher = Fetcher()
        self.sql_session = sql_session
    
    def judge_res(self,res):
        if (res.status_code == 200):
            r = "True"
        else:
            if res.text:
                try:
                    text = json.loads(res.text)
                except :
                    text = res.text
                raise Exception(text)
            elif res.__dict__.get('reason'):
                raise Exception('Reason: %s' % res.reason)
            else:
                raise Exception('status code: %d' % res.status_code)
        return r
    
    async def pusher(self, userid, pushsw, flg, title, content):
        sql_session = self.sql_session
        notice = await self.db.user.get(userid, fields=('skey', 'barkurl', 'noticeflg', 'wxpusher', 'qywx_token', 'tg_token', 'dingding_token', 'diypusher'), sql_session=sql_session)

        if (notice['noticeflg'] & flg != 0):
            user = await self.db.user.get(userid, fields=('id', 'email', 'email_verified', 'nickname'), sql_session=sql_session)
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

            def nonepush(*args,**kwargs):
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

                await gen.convert_yielded([send2bark(notice['barkurl'], title, content),
                                        send2s(notice['skey'], title, content),
                                        send2wxpusher( notice['wxpusher'], title+u"  "+content),
                                        sendmail( user['email'], title, content, sql_session=sql_session),
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
            # obj = {'request': {'method': 'POST', 'url': link, 'headers': [{'name' : 'Content-Type', 'value': 'application/json; charset=UTF-8'}], 'cookies': [], 'data':json.dumps(d)}, 'rule': {
            #        'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
            # _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
            res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.post, link, json=d, verify=False)),timeout=3.0)
            r = self.judge_res(res)

        except Exception as e:
            r = traceback.format_exc()
            logger_Funcs.error('Sent to Bark error: %s', e)
            return e
        
        return r
        
    async def send2s(self, skey, title, content):
        r = 'False'
        if (skey != ""):
            try:
                link = u"https://sctapi.ftqq.com/{0}.send".format(skey.replace(".send", ""))
                content = content.replace('\\r\\n','\n\n')
                d = {'text': title, 'desp': content}
                # obj = {'request': {'method': 'POST', 'url': link, 'headers': [{'name' : 'Content-Type', 'value': 'application/x-www-form-urlencoded; charset=UTF-8'}], 'cookies': [], 'data':utils.urllib.parse.urlencode(d)}, 'rule': {
                #    'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                # _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
                res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.post, link, data=d, verify=False)),timeout=3.0)
                r = self.judge_res(res)

            except Exception as e:
                r = traceback.format_exc()
                logger_Funcs.error('Sent to ServerChan error: %s', e)
                return e
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
            proxy = tmp[3] if len(tmp) >= 4 else ''
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
                # obj = {'request': {'method': 'POST', 'url': link, 'headers': [{'name' : 'Content-Type', 'value': 'application/json; charset=UTF-8'}], 'cookies': [], 'data':json.dumps(d)}, 'rule': {
                #    'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                if proxy:
                    proxies = {
                        'http': proxy,
                        'https': proxy
                    }
                    # _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj, proxy = proxy))
                    res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.post, link, json=d, proxies=proxies, verify=False)),timeout=3.0)
                else:
                    # _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
                    res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.post, link, json=d, verify=False)),timeout=3.0)
                r = self.judge_res(res)
            except Exception as e:
                r = traceback.format_exc()
                logger_Funcs.error('Sent to Telegram error: %s', e)
                return e
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
                d = {"msgtype": "markdown", "markdown": {"title": title, "text": "![QianDao](" + picurl + ")\n " + "#### " + title + "\n > " + content}}
                # obj = {'request': {'method': 'POST', 'url': link, 'headers': [{'name' : 'Content-Type', 'value': 'application/json; charset=UTF-8'}], 'cookies': [], 'data':json.dumps(d)}, 'rule': {
                #    'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                # _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
                res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.post, link, json=d, verify=False)),timeout=3.0)
                r = self.judge_res(res)
                if res.json().get('errcode', '') != 0:
                    raise Exception(res.json())
            except Exception as e:
                r = traceback.format_exc()
                logger_Funcs.error('Sent to DingDing error: %s', e)
                return e
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
                # obj = {'request': {'method': 'POST', 'url': link, 'headers': [{'name' : 'Content-Type', 'value': 'application/json; charset=UTF-8'}], 'cookies': [], 'data':json.dumps(d)}, 'rule': {
                #    'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                # _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
                res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.post, link, json=d, verify=False)),timeout=3.0)
                r = self.judge_res(res)
                if not res.json().get('success', True):
                    raise Exception(res.json())
            except Exception as e:
                r = traceback.format_exc()
                logger_Funcs.error('Sent to WxPusher error: %s', e)
                return e
        else:
            return Exception("参数不完整! ")

        return  r  


    async def cus_pusher_send(self, diypusher, t, log):
        r = 'False'
        try:
            log = log.replace('"','\\"').replace('\\\\"','\\"')
            curltmp = diypusher['curl'].format(log=log, t=t)
            
            if (diypusher['headers']):
                headerstmp = json.loads(diypusher['headers'].replace('{log}', log).replace("{t}", t))
            else:
                headerstmp = {}

            if (diypusher['mode'] == 'POST'):
                postDatatmp = diypusher['postData'].replace('{log}', log).replace("{t}", t)
                if headerstmp:
                    headerstmp.pop('content-type','')
                    headerstmp.pop('Content-Type','')
                if (diypusher['postMethod'] == 'x-www-form-urlencoded'):
                    headerstmp['Content-Type'] = "application/x-www-form-urlencoded; charset=UTF-8"
                    # headerstmp = [{'name': name, 'value': headerstmp[name]} for name in headerstmp]
                    # obj = {'request': {'method': 'POST', 'url': curltmp, 'headers': headerstmp, 'cookies': [], 'data':utils.urllib.parse.urlencode(postDatatmp)}, 'rule': {
                    #     'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                    if (postDatatmp != ''):
                        try:
                            postDatatmp = json.loads(postDatatmp)
                        except:
                            pass
                    res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.post, curltmp, headers=headerstmp, data=postDatatmp, verify=False)),timeout=3.0)
                else:
                    headerstmp['Content-Type'] = "application/json; charset=UTF-8"
                    if (postDatatmp != ''):
                        postDatatmp = json.loads(postDatatmp)
                    # headerstmp = [{'name': name, 'value': headerstmp[name]} for name in headerstmp]
                    # obj = {'request': {'method': 'POST', 'url': curltmp, 'headers': headerstmp, 'cookies': [], 'data':json.dumps(postDatatmp)}, 'rule': {
                    #     'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                    res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.post, curltmp, headers=headerstmp, json=postDatatmp, verify=False)),timeout=3.0)
            elif (diypusher['mode'] == 'GET'):
                # headerstmp = [{'name': name, 'value': headerstmp[name]} for name in headerstmp]
                # obj = {'request': {'method': 'GET', 'url': curltmp, 'headers': headerstmp, 'cookies': []}, 'rule': {
                #    'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.get, curltmp, headers=headerstmp, verify=False)),timeout=3.0)
            else:
                raise Exception(u'模式未选择')
            # _,_,res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))

            r = self.judge_res(res)

        except Exception as e:
            r = traceback.format_exc()
            logger_Funcs.error('Sent to Cus_Pusher error: %s', e)
            return e
        return r

    # 获取Access_Token
    async def get_access_token(self,qywx):
        access_url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={id}&corpsecret={secret}'.format(id=qywx[u'企业ID'], secret=qywx[u'应用密钥'])
        obj = {'request': {'method': 'GET', 'url': access_url, 'headers': [], 'cookies': []}, 'rule': {
                'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
        _,_,res = await self.fetcher.build_response(obj = obj)
        get_access_token_res = json.loads(res.body)
        return get_access_token_res

    #上传临时素材,返回素材id
    async def get_ShortTimeMedia(self,pic_url,access_token):
        if pic_url == config.push_pic:
            with open(os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'web','static','img','push_pic.png'),'rb') as f:
                res = f.read()
        else:
            obj = {'request': {'method': 'GET', 'url': pic_url, 'headers': {}, 'cookies': []}, 'rule': {
                    'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
            _,_,res = await self.fetcher.build_response(obj = obj)
            res = res.body
        url='https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type=image'.format(access_token = access_token)
        r = await asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.post, url, files={'image':res}, json=True, verify=False))
        return json.loads(r.text)['media_id']

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
                raise Exception(u'企业微信获取AccessToken失败或参数不完整!')

            get_access_token_res = await self.get_access_token(qywx)
            pic_url = config.push_pic if qywx[u'图片'] == '' else qywx[u'图片']
            if (get_access_token_res.get('access_token','') != '' and get_access_token_res['errmsg'] == 'ok'):
                access_token = get_access_token_res["access_token"]
                if utils.urlmatch(pic_url):
                    media_id = await self.get_ShortTimeMedia(pic_url,access_token)
                else:
                    media_id = pic_url
                msgUrl = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={0}'.format(access_token)
                postData = {"touser": "@all",
                            "toparty": "@all",
                            "totag": "@all",
                            "msgtype": "mpnews",
                            "agentid": qywx[u'应用ID'],
                            "mpnews": {
                                "articles": [
                                    {
                                        "title": t,
                                        "digest": log.replace("\\r\\n", "\n"),
                                        "content": log.replace("\\r\\n", "<br>"),
                                        "author": "私有签到框架",
                                        "content_source_url": config.domain,
                                        "thumb_media_id": media_id
                                    }
                                ]
                            },
                            "safe": 0,
                            "enable_id_trans": 0,
                            "enable_duplicate_check": 0,
                            "duplicate_check_interval": 1800
                            }
                # obj = {'request': {'method': 'POST', 'url': msgUrl, 'headers': [{'name' : 'Content-Type', 'value': 'application/json; charset=UTF-8'}], 'cookies': [], 'data':json.dumps(postData)}, 'rule': {
                #    'success_asserts': [], 'failed_asserts': [], 'extract_variables': []}, 'env': {'variables': {}, 'session': []}}
                # _,_,msg_res = await gen.convert_yielded(self.fetcher.build_response(obj = obj))
                # tmp = json.loads(msg_res.body)
                msg_res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.post, msgUrl, json=postData, verify=False)),timeout=3.0)
                r = self.judge_res(msg_res)
                tmp = msg_res.json()
                if (tmp['errmsg'] == 'ok' and tmp['errcode'] == 0):
                    r = 'True'
            else:
                raise Exception("企业微信获取AccessToken失败或参数不完整! ")

        except Exception as e:
            r = traceback.format_exc()
            logger_Funcs.error('Sent to QYWX error: %s', e)
            return e
        return r

    async def sendmail(self, email, title, content, sql_session=None):
        user = await self.db.user.get(email=email, fields=('id', 'email', 'email_verified', 'nickname'), sql_session=sql_session)
        if user['email'] and user['email_verified']:
            try:
                content = content.replace('\\r\\n','\n')
                await utils.send_mail(to = email, 
                                subject = u"在网站{0} {1}".format(config.domain, title),
                                text = content,
                                shark=True)
            except Exception as e:
                logger_Funcs.error('Send mail error: %r', e)

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
        except Exception as e:
            r['r'] = e
            logger_Funcs.error('Calculate Next Timestamp error: %s',r['r'])
        return r
