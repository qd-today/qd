#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import datetime
import time
import urllib
import pytz
from base import *
from tornado import gen


class UtilDelayHandler(BaseHandler):
    @gen.coroutine
    def get(self, seconds):
        seconds = float(seconds)
        if seconds < 0:
            seconds = 0
        elif seconds > 30:
            seconds = 30
        yield gen.sleep(seconds)
        self.write(u'delay %s second.' % seconds)

class TimeStampHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        Rtv = {}
        try:
            ts = self.get_argument("ts", "")
            type = self.get_argument("form", "%Y-%m-%d %H:%M:%S")
            cst_tz = pytz.timezone('Asia/Shanghai')

            if not ts:
                # 当前本机时间戳，本机时间和北京时间
                Rtv[u"时间戳"] = int(time.time())
                Rtv[u"本机时间"] = datetime.datetime.fromtimestamp(Rtv[u"时间戳"]).strftime(type)
                Rtv[u"北京时间"] = datetime.datetime.fromtimestamp(Rtv[u"时间戳"], cst_tz).strftime(type)
            else:
                # 用户时间戳转北京时间
                Rtv[u"时间戳"] = ts
                Rtv[u"北京时间"]  = datetime.datetime.fromtimestamp(int(ts), cst_tz).strftime(type)
            Rtv[u"状态"] = "200"
        except Exception as e:
                Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))


class UniCodeHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        Rtv = {}
        try:
            content = self.get_argument("content", "")
            tmp = ""
            for cr in content:
                if (cr=="u" or cr=="'"):
                    tmp = tmp + cr
                    continue
                tmp = tmp + repr(cr).replace("u'", "").replace("'","").replace("\\\\", "\\")
            Rtv[u"转换后"] = tmp.decode("unicode_escape")
            print ("222222"+ Rtv[u"转换后"])
            Rtv[u"状态"] = "200"
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))


class UrlDecodeHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        Rtv = {}
        try:
            content = self.get_argument("content", "")
            Rtv[u"转换后"] = urllib.unquote(content)
            Rtv[u"状态"] = "200"
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))

class UtilRegexHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        Rtv = {}
        try:
            data = self.get_argument("data", "")
            p = self.get_argument("p", "")
            temp = {}
            ds = re.findall(p, data, re.IGNORECASE)
            for cnt in range (0, len(ds)):
                temp[cnt+1] = ds[cnt]
            Rtv[u"数据"] = temp
            Rtv[u"状态"] = "OK"
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))

class UtilStrReplaceHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        Rtv = {}
        try:
            s = self.get_argument("s", "")
            p = self.get_argument("p", "")
            t = self.get_argument("t", "")
            Rtv[u"原始字符串"] = s
            Rtv[u"处理后字符串"] = re.sub(p, t, s)
            Rtv[u"状态"] = "OK"                
        except Exception as e:
            Rtv["状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))


handlers = [
    ('/util/delay/(\d+)', UtilDelayHandler),
    ('/util/timestamp', TimeStampHandler),
    ('/util/unicode', UniCodeHandler),
    ('/util/urldecode', UrlDecodeHandler),
    ('/util/regex', UtilRegexHandler),
    ('/util/string/replace', UtilStrReplaceHandler),
]
