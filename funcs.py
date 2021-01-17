#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:

import sys
import json
import logging
import datetime
import time
import requests
import traceback
import urllib

class tools(object):
    def __init__(self):
        pass

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