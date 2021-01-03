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
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import  PKCS1_v1_5
from Crypto import Random


def request_parse(req_data):
    '''解析请求数据并以json形式返回'''
    if req_data.method == 'POST':
            data = req_data.body_arguments
    elif req_data.method == 'GET':
        data = req_data.arguments
    return data


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
            utc_tz = pytz.timezone("UTC")
            GMT_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"

            if not ts:
                # 当前本机时间戳，本机时间和北京时间
                Rtv[u"时间戳"] = int(time.time())
                Rtv[u"本机时间"] = datetime.datetime.fromtimestamp(Rtv[u"时间戳"]).strftime(type)
                Rtv[u"北京时间"] = datetime.datetime.fromtimestamp(Rtv[u"时间戳"], cst_tz).strftime(type)
                Rtv[u"GMT格式"] = datetime.datetime.fromtimestamp(Rtv[u"时间戳"], utc_tz).strftime(GMT_FORMAT)
                Rtv[u"ISO格式"] = datetime.datetime.fromtimestamp(Rtv[u"时间戳"], utc_tz).isoformat().split("+")[0] + "Z"
            else:
                # 用户时间戳转北京时间
                Rtv[u"时间戳"] = ts
                Rtv[u"北京时间"]  = datetime.datetime.fromtimestamp(int(ts), cst_tz).strftime(type)
                Rtv[u"GMT格式"] = datetime.datetime.fromtimestamp(int(ts), utc_tz).strftime(GMT_FORMAT)
                Rtv[u"ISO格式"] = datetime.datetime.fromtimestamp(int(ts), utc_tz).isoformat().split("+")[0] + "Z"
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

    @gen.coroutine
    def post(self):
        Rtv = {}
        try:
            res_data = request_parse(self.request)
            p = res_data["p"][0].decode('utf8') if 'p' in  res_data else None
            data = res_data["data"][0].decode('utf8') if "data" in  res_data else None 
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

        return

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
            if self.get_argument("r", "")  == "text":
                self.write(Rtv[u"处理后字符串"])
                return
            else:
                self.set_header('Content-Type', 'application/json; charset=UTF-8')
                self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))
                return
        except Exception as e:
            Rtv["状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))

class UtilRSAHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        try:
            res_data = request_parse(self.request)
            key = res_data["key"][0] if "key" in  res_data else None
            data = res_data["data"][0] if "data" in  res_data else None 
            func = res_data["f"][0] if "f" in  res_data else None 
            if (key) and (data) and (func):
                lines = ""
                temp = key
                temp = re.findall("-----.*?-----", temp)
                if (len(temp) == 2):
                    keytemp = key
                    for t in temp:
                        keytemp = keytemp.replace(t, "")

                    while(keytemp):
                        line = keytemp[0:63]
                        lines = lines+line+"\n"
                        keytemp = keytemp.replace(line, "")
                    
                    lines = temp[0]+"\n" + lines + temp[1]

                else:
                    self.write(u"证书格式错误")
                    return 

                cipher_rsa = PKCS1_v1_5.new(RSA.import_key(lines))
                if (func.find("encode") > -1):
                    crypt_text = cipher_rsa.encrypt(bytes(data))
                    crypt_text = base64.b64encode(crypt_text).decode('utf8')
                    self.write(crypt_text)
                    return
                elif (func.find("decode") > -1): 
                    t1 = base64.b64decode(data)
                    decrypt_text = cipher_rsa.decrypt(t1, Random.new().read)
                    decrypt_text = decrypt_text.decode('utf8')
                    self.write(decrypt_text)
                    return
                else:
                    self.write(u"功能选择错误")
                    return
            else:
                self.write(u"参数不完整，请确认")
        except Exception as e:
            self.write(str(e))
            return

    @gen.coroutine
    def post(self):
        try:
            res_data = request_parse(self.request)
            key = res_data["key"][0] if "key" in  res_data else None
            data = res_data["data"][0] if "data" in  res_data else None 
            func = res_data["f"][0] if "f" in  res_data else None 
            if (key) and (data) and (func):
                lines = ""
                for line in key.split("\n"):
                    if (line.find("--") < 0):
                        line = line.replace(" ", "+")
                    lines = lines+line+"\n"
                data = data.replace(" ", "+")
                
                cipher_rsa = PKCS1_v1_5.new(RSA.import_key(lines))
                if (func.find("encode") > -1):
                    crypt_text = cipher_rsa.encrypt(bytes(data))
                    crypt_text = base64.b64encode(crypt_text).decode('utf8')
                    self.write(crypt_text)
                    return
                elif (func.find("decode") > -1): 
                    decrypt_text = cipher_rsa.decrypt(base64.b64decode(data), Random.new().read)
                    decrypt_text = decrypt_text.decode('utf8')
                    self.write(decrypt_text)
                    return
                else:
                    self.write(u"功能选择错误")
                    return
            else:
                self.write(u"参数不完整，请确认")
        except Exception as e:
            self.write(str(e))
            return

        


handlers = [
    ('/util/delay/(\d+)', UtilDelayHandler),
    ('/util/timestamp', TimeStampHandler),
    ('/util/unicode', UniCodeHandler),
    ('/util/urldecode', UrlDecodeHandler),
    ('/util/regex', UtilRegexHandler),
    ('/util/string/replace', UtilStrReplaceHandler),
    ('/util/rsa', UtilRSAHandler),
]
