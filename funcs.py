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