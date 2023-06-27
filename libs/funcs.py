#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:

import datetime
import json
import os
import random
import time
import traceback

import aiohttp
import croniter
from tornado import gen

import config
from db import DB
from libs import utils

from .log import Log

logger_Funcs = Log('QD.Http.Funcs').getlogger()
class pusher(object):
    def __init__(self,db:DB,sql_session=None):
        self.db = db
        self.sql_session = sql_session

    async def judge_res(self,res:aiohttp.ClientResponse):
        if (res.status == 200):
            return "True"
        else:
            text = await res.text()
            if text:
                try:
                    text = await res.json()
                except:
                    pass
                raise Exception(text)
            elif res.reason:
                raise Exception('Reason: %s' % res.reason)
            else:
                raise Exception('status code: %d' % res.status)

    async def pusher(self, userid, pushsw, flg, title, content):
        sql_session = self.sql_session
        notice = await self.db.user.get(userid, fields=('skey', 'barkurl', 'noticeflg', 'wxpusher', 'qywx_token', 'tg_token', 'dingding_token', 'qywx_webhook', 'diypusher'), sql_session=sql_session)

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
            pusher["qywxwebhooksw"] = False if (notice['noticeflg'] & 0x1000) == 0 else True

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
                qywx_webhook_send = self.qywx_webhook_send if (pusher["qywxwebhooksw"]) else nonepush

                await gen.convert_yielded([send2bark(notice['barkurl'], title, content),
                                        send2s(notice['skey'], title, content),
                                        send2wxpusher( notice['wxpusher'], title+u"  "+content),
                                        sendmail( user['email'], title, content, sql_session=sql_session),
                                        cus_pusher_send( diypusher, title, content),
                                        qywx_pusher_send( notice['qywx_token'], title, content),
                                        send2tg( notice['tg_token'], title, content),
                                        send2dingding(notice['dingding_token'], title, content),
                                        qywx_webhook_send(notice['qywx_webhook'], title, content)
                                        ])

    async def send2bark(self, barklink, title, content):
        r = 'False'
        try:
            link = barklink
            if (link[-1] != '/'): link=link+'/'
            content = content.replace('\\r\\n','\n')
            d = {"title":title,"body":content}
            async with aiohttp.ClientSession(conn_timeout=config.connect_timeout) as session:
                    async with session.post(link, json=d, verify_ssl=False, timeout=config.request_timeout) as res:
                        r = await self.judge_res(res)

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
                async with aiohttp.ClientSession(conn_timeout=config.connect_timeout) as session:
                    async with session.post(link, json=d, verify_ssl=False, timeout=config.request_timeout) as res:
                        r = await self.judge_res(res)

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

                # 匹配标题"QD[定时]任务 {0}-{1} 成功|失败" 的 {0} 部分, 获取 hashtag
                title_sp = title.split(' ')
                if len(title_sp) >= 3:
                    title1 = title_sp[1].split('-')
                    if len(title1) == 2:
                        title1[0] = '#' + title1[0] + ' '
                    title_sp[1] = '-'.join(title1)
                title = ' '.join(title_sp)

                content = content.replace('\\r\\n','</pre>\n<pre>')
                d = {'chat_id': str(chat_id), 'text': '<b>' + title + '</b>' + '\n<pre>' + content + '</pre>\n' + '------<a href="' + picurl + '">QD提醒</a>------', 'disable_web_page_preview':'false', 'parse_mode': 'HTML'}
                if proxy:
                    async with aiohttp.ClientSession(conn_timeout=config.connect_timeout) as session:
                        async with session.post(link, json=d, verify_ssl=False, proxy=proxy, timeout=config.request_timeout) as res:
                            r = await self.judge_res(res)
                else:
                    async with aiohttp.ClientSession(conn_timeout=config.connect_timeout) as session:
                        async with session.post(link, json=d, verify_ssl=False, timeout=config.request_timeout) as res:
                            r = await self.judge_res(res)
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
                d = {"msgtype": "markdown", "markdown": {"title": title, "text": "![QD](" + picurl + ")\n " + "#### " + title + "\n > " + content}}
                async with aiohttp.ClientSession(conn_timeout=config.connect_timeout) as session:
                    async with session.post(link, json=d, verify_ssl=False, timeout=config.request_timeout) as res:
                        r = await self.judge_res(res)
                        _json = await res.json()
                        if _json.get('errcode', '') != 0:
                            raise Exception(_json)
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
                async with aiohttp.ClientSession(conn_timeout=config.connect_timeout) as session:
                    async with session.post(link, json=d, verify_ssl=False, timeout=config.request_timeout) as res:
                        r = await self.judge_res(res)
                        _json = await res.json()
                        if not _json.get('success', True):
                            raise Exception(_json)
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
                    if (postDatatmp != ''):
                        try:
                            postDatatmp = json.loads(postDatatmp)
                        except:
                            if isinstance(postDatatmp, str):
                                postDatatmp = postDatatmp.encode('utf-8')
                    async with aiohttp.ClientSession(headers=headerstmp, conn_timeout=config.connect_timeout) as session:
                        async with session.post(curltmp, data=postDatatmp, verify_ssl=False, timeout=config.request_timeout) as res:
                            r = await self.judge_res(res)
                else:
                    headerstmp['Content-Type'] = "application/json; charset=UTF-8"
                    if (postDatatmp != ''):
                        postDatatmp = json.loads(postDatatmp)
                    async with aiohttp.ClientSession(headers=headerstmp, conn_timeout=config.connect_timeout) as session:
                        async with session.post(curltmp, json=postDatatmp, verify_ssl=False, timeout=config.request_timeout) as res:
                            r = await self.judge_res(res)
            elif (diypusher['mode'] == 'GET'):
                async with aiohttp.ClientSession(headers=headerstmp, conn_timeout=config.connect_timeout) as session:
                    async with session.get(curltmp, verify_ssl=False, timeout=config.request_timeout) as res:
                        r = await self.judge_res(res)
            else:
                raise Exception(u'模式未选择')

        except Exception as e:
            r = traceback.format_exc()
            logger_Funcs.error('Sent to Cus_Pusher error: %s', e)
            return e
        return r

    # 获取Access_Token
    async def get_access_token(self, qywx:dict):
        access_url = '{qywxProxy}cgi-bin/gettoken?corpid={id}&corpsecret={secret}'.format(qywxProxy=qywx[u'代理'], id=qywx[u'企业ID'], secret=qywx[u'应用密钥'])
        async with aiohttp.ClientSession(conn_timeout=config.connect_timeout) as session:
            async with session.get(access_url, verify_ssl=False, timeout=config.request_timeout) as res:
                get_access_token_res = await res.json()
        return get_access_token_res

    #上传临时素材,返回素材id
    async def get_ShortTimeMedia(self,pic_url,access_token,qywxProxy):
        async with aiohttp.ClientSession(conn_timeout=config.connect_timeout) as session:
            if pic_url == config.push_pic:
                with open(os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'web','static','img','push_pic.png'),'rb') as f:
                    img = f.read()
            else:
                async with session.get(pic_url, verify_ssl=False, timeout=config.request_timeout) as res:
                    img = await res.read()
            url=f'{qywxProxy}cgi-bin/media/upload?access_token={access_token}&type=image'
            async with session.post(url, data={'image':img}, verify_ssl=False, timeout=config.request_timeout) as res:
                await self.judge_res(res)
                _json = await res.json()
                return _json['media_id']

    async def qywx_pusher_send(self, qywx_token, title:str, log:str):
        r = 'False'
        try:
            qywx = {}
            tmp = qywx_token.split(';')
            if len(tmp) >= 3:
                qywx[u'企业ID'] = tmp[0]
                qywx[u'应用ID'] = tmp[1]
                qywx[u'应用密钥'] = tmp[2]
                qywx[u'图片'] = tmp[3] if len(tmp) >= 4 else ''
                qywx[u'代理'] = tmp[4] if len(tmp) >= 5 else 'https://qyapi.weixin.qq.com/'
            else:
                raise Exception(u'企业微信Pusher获取AccessToken失败或参数不完整!')

            if qywx[u'代理'][-1]!='/':
                qywx[u'代理'] = qywx[u'代理'] + '/'
            if 'http://' in qywx[u'代理'] or 'https://' in qywx[u'代理']:
                qywx[u'代理'] = u'https://{0}'.format(qywx[u'代理'])
            get_access_token_res = await self.get_access_token(qywx)
            pic_url = config.push_pic if qywx[u'图片'] == '' else qywx[u'图片']
            if (get_access_token_res.get('access_token','') != '' and get_access_token_res['errmsg'] == 'ok'):
                access_token = get_access_token_res["access_token"]
                if utils.urlMatchWithLimit(pic_url) or utils.domainMatch(pic_url.split('/')[0]):
                    media_id = await self.get_ShortTimeMedia(pic_url,access_token,qywx[u'代理'])
                else:
                    media_id = pic_url
                msgUrl = '{0}cgi-bin/message/send?access_token={1}'.format(qywx[u'代理'], access_token)
                postData = {"touser": "@all",
                            "toparty": "@all",
                            "totag": "@all",
                            "msgtype": "mpnews",
                            "agentid": qywx[u'应用ID'],
                            "mpnews": {
                                "articles": [
                                    {
                                        "title": title,
                                        "digest": log.replace("\\r\\n", "\n"),
                                        "content": log.replace("\\r\\n", "<br>"),
                                        "author": "QD框架",
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
                async with aiohttp.ClientSession(conn_timeout=config.connect_timeout) as session:
                    async with session.post(msgUrl, json=postData, verify_ssl=False, timeout=config.request_timeout) as res:
                        r = await self.judge_res(res)
                        _json = await res.json()
                        if _json.get('errmsg','') == 'ok' and _json.get('errcode',0) == 0:
                            r = 'True'
                        elif _json.get('errmsg','') != '':
                            raise Exception(_json['errmsg'])
            else:
                raise Exception("企业微信Pusher获取AccessToken失败或参数不完整! ")

        except Exception as e:
            r = traceback.format_exc()
            logger_Funcs.error('Sent to QYWX Pusher error: %s', e)
            return e
        return r

    async def qywx_webhook_send(self, qywx_webhook, title:str, log:str):
        r = 'False'
        try:
            qywx = {}
            tmp = qywx_webhook.split(';')
            if len(tmp) >= 1:
                qywx[u'Webhook'] = tmp[0]
            else:
                raise Exception(u'企业微信WebHook获取AccessToken失败或参数不完整!')

            log = log.replace("\\r\\n", "\n")

            msgUrl = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={0}".format(qywx[u'Webhook'])
            postData = {"msgtype": "text",
                        "text": {
                            "content": f"{title}\n{log}"
                        }
                        }
            async with aiohttp.ClientSession(conn_timeout=config.connect_timeout) as session:
                async with session.post(msgUrl, json=postData, verify_ssl=False, timeout=config.request_timeout) as res:
                    r = await self.judge_res(res)
                    _json = await res.json()
                    if _json.get('errmsg','') == 'ok' and _json.get('errcode',0) == 0:
                        r = 'True'
                    elif _json.get('errmsg','') != '':
                        raise Exception(_json['errmsg'])
        except Exception as e:
            r = traceback.format_exc()
            logger_Funcs.error('Sent to QYWX WebHook error: %s', e)
            return e
        return r

    async def sendmail(self, email, title, content:str, sql_session=None):
        if not config.domain:
            r = '请配置框架域名 domain, 以启用邮箱推送功能!'
            logger_Funcs.error('Send mail error: %s', r)
            return Exception(r)
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
