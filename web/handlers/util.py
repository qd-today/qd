#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import datetime
import time
import urllib
import pytz
import traceback
from libs.log import Log

logger_Web_Util = Log('qiandao.Web.Util').getlogger()
try:
    import ddddocr
except ImportError as e:
    logger_Web_Util.warning('Import DdddOCR module falied: %s',e)
    ddddocr = None
import requests
import asyncio
import functools
from .base import *
from tornado import gen
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import  PKCS1_v1_5
from Crypto import Random
from config import delay_max_timeout,strtobool

def request_parse(req_data):
    '''解析请求数据并以json形式返回'''
    if req_data.method == 'POST':
        data = req_data.body_arguments
    elif req_data.method == 'GET':
        data = req_data.arguments
    return data

class UtilDelayParaHandler(BaseHandler):
    async def get(self):
        try:
            seconds = float(self.get_argument("seconds", 0))
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            await gen.sleep(0.0)
            self.write(u'Error, delay 0.0 second.')
            return
        if seconds < 0:
            seconds = 0.0
        elif seconds >= delay_max_timeout:
            seconds = delay_max_timeout
            await gen.sleep(seconds)
            self.write(u'Error, limited by delay_max_timeout, delay {seconds} second.')
            return
        await gen.sleep(seconds)
        self.write(u'delay %s second.' % seconds)
        return

class UtilDelayIntHandler(BaseHandler):
    async def get(self, seconds):
        try:
            seconds = float(seconds)
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            self.write(u'delay %s second.' % seconds)
            return
        if seconds < 0:
            seconds = 0.0
        elif seconds > delay_max_timeout:
            seconds = delay_max_timeout
            await gen.sleep(seconds)
            self.write(u'Error, limited by delay_max_timeout, delay {seconds} second.')
            return
        await gen.sleep(seconds)
        self.write(u'delay %s second.' % seconds)
        return

class UtilDelayHandler(BaseHandler):
    async def get(self, seconds):
        try:
            seconds = float(seconds)
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            self.write(u'delay %s second.' % seconds)
            return
        if seconds < 0:
            seconds = 0.0
        elif seconds >= delay_max_timeout:
            seconds = delay_max_timeout
            await gen.sleep(seconds)
            self.write(u'Error, limited by delay_max_timeout, delay {seconds} second.')
            return
        await gen.sleep(seconds)
        self.write(u'delay %s second.' % seconds)
        return

class TimeStampHandler(BaseHandler):
    async def get(self):
        Rtv = {}
        try:
            ts = self.get_argument("ts", "")
            type = self.get_argument("form", "%Y-%m-%d %H:%M:%S")
            cst_tz = pytz.timezone('Asia/Shanghai')
            utc_tz = pytz.timezone("UTC")
            GMT_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"
            tmp = datetime.datetime.fromtimestamp

            if not ts:
                # 当前本机时间戳，本机时间和北京时间
                Rtv[u"完整时间戳"] = time.time()
                Rtv[u"时间戳"] = int(Rtv[u"完整时间戳"])
                Rtv[u"16位时间戳"] = int(Rtv[u"完整时间戳"]*1000000)
                Rtv[u"本机时间"] = tmp(Rtv[u"完整时间戳"]).strftime(type)
                Rtv[u"周"] = tmp(Rtv[u"完整时间戳"]).strftime("%w/%W")
                Rtv[u"日"] = "/".join([tmp(Rtv[u"完整时间戳"]).strftime("%j"),yearday(tmp(Rtv[u"完整时间戳"]).year)])
                Rtv[u"北京时间"] = tmp(Rtv[u"完整时间戳"], cst_tz).strftime(type)
                Rtv[u"GMT格式"] = tmp(Rtv[u"完整时间戳"], utc_tz).strftime(GMT_FORMAT)
                Rtv[u"ISO格式"] = tmp(Rtv[u"完整时间戳"], utc_tz).isoformat().split("+")[0] + "Z"
            else:
                # 用户时间戳转北京时间
                Rtv[u"时间戳"] = int(ts)
                Rtv[u"周"] = tmp(Rtv[u"时间戳"]).strftime("%w/%W")
                Rtv[u"日"] = "/".join([tmp(Rtv[u"时间戳"]).strftime("%j"),yearday(tmp(Rtv[u"时间戳"]).year)])
                Rtv[u"北京时间"] = tmp(Rtv[u"时间戳"], cst_tz).strftime(type)
                Rtv[u"GMT格式"] = tmp(Rtv[u"时间戳"], utc_tz).strftime(GMT_FORMAT)
                Rtv[u"ISO格式"] = tmp(Rtv[u"时间戳"], utc_tz).isoformat().split("+")[0] + "Z"
            Rtv[u"状态"] = "200"
        except Exception as e:
                Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))

def yearday(year):
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        return '366'
    else:
        return '365'

class UniCodeHandler(BaseHandler):
    async def get(self):
        Rtv = {}
        try:
            content = self.get_argument("content", "")
            tmp = bytes(content,'unicode_escape').decode('utf-8').replace(r'\u',r'\\u').replace(r'\\\u',r'\\u')
            tmp = bytes(tmp,'utf-8').decode('unicode_escape')
            Rtv[u"转换后"] = tmp.encode('utf-8').replace(b'\xc2\xa0',b'\xa0').decode('unicode_escape')
            Rtv[u"状态"] = "200"
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))
        return

    async def post(self):
        Rtv = {}
        try:
            content = self.get_argument("content", "")
            tmp = bytes(content,'unicode_escape').decode('utf-8').replace(r'\u',r'\\u').replace(r'\\\u',r'\\u')
            tmp = bytes(tmp,'utf-8').decode('unicode_escape')
            Rtv[u"转换后"] = tmp.encode('utf-8').replace(b'\xc2\xa0',b'\xa0').decode('unicode_escape')
            Rtv[u"状态"] = "200"
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))
        return

class GB2312Handler(BaseHandler):
    async def get(self):
        Rtv = {}
        try:
            content = self.get_argument("content", "")
            tmp = urllib.parse.quote(content,encoding="gb2312")
            Rtv[u"转换后"] = tmp
            Rtv[u"状态"] = "200"
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))
        return

    async def post(self):
        Rtv = {}
        try:
            content = self.get_argument("content", "")
            tmp = urllib.parse.quote(content,encoding="gb2312")
            Rtv[u"转换后"] = tmp
            Rtv[u"状态"] = "200"
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))
        return

class UrlDecodeHandler(BaseHandler):
    async def get(self):
        Rtv = {}
        try:
            content = self.get_argument("content", "")
            Rtv[u"转换后"] = urllib.parse.unquote(content)
            Rtv[u"状态"] = "200"
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))
        return

    async def post(self):
        Rtv = {}
        try:
            content = self.get_argument("content", "")
            Rtv[u"转换后"] = urllib.parse.unquote(content)
            Rtv[u"状态"] = "200"
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))
        return

class UtilRegexHandler(BaseHandler):
    async def get(self):
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
        return

    async def post(self):
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

        return

class UtilStrReplaceHandler(BaseHandler):
    async def get(self):
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
        return

    async def post(self):
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
        return

class UtilRSAHandler(BaseHandler):
    async def get(self):
        try:
            key = self.get_argument("key", "")
            data = self.get_argument("data", "")
            func = self.get_argument("f", "encode")
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
                    crypt_text = cipher_rsa.encrypt(bytes(data, encoding = "utf8"))
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
                return
        except Exception as e:
            self.write(str(e))
            return

    async def post(self):
        try:
            key = self.get_argument("key", "")
            data = self.get_argument("data", "")
            func = self.get_argument("f", "encode")
            if (key) and (data) and (func):
                lines = ""
                for line in key.split("\n"):
                    if (line.find("--") < 0):
                        line = line.replace(" ", "+")
                    lines = lines+line+"\n"
                data = data.replace(" ", "+")
                
                cipher_rsa = PKCS1_v1_5.new(RSA.import_key(lines))
                if (func.find("encode") > -1):
                    crypt_text = cipher_rsa.encrypt(bytes(data, encoding = "utf8"))
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
                return
        except Exception as e:
            self.write(str(e))
            return

class toolboxHandler(BaseHandler):
    async def get(self, userid):
        user = self.current_user
        await self.render('toolbox.html', userid=userid)

    async def post(self, userid):
        try:
            email = self.get_argument("email", "")
            pwd = self.get_argument("pwd", "")
            f = self.get_argument("f", "")
            if (email) and (pwd) and (f):
                if self.db.user.challenge_MD5(email, pwd) or self.db.user.challenge(email, pwd):
                    userid = self.db.user.get(email=email, fields=('id'))['id']
                    text_data = self.db.user.get(email=email, fields=('notepad'))['notepad']
                    new_data = self.get_argument("data", "")
                    if (f.find('write') > -1 ): 
                        text_data = new_data
                        self.db.user.mod(userid, notepad=text_data)
                    elif (f.find('append') > -1):
                        if text_data is not None:
                            text_data = text_data + '\r\n' + new_data
                        else:
                            text_data = new_data
                        self.db.user.mod(userid, notepad=text_data)
                    self.write(text_data)
                    return
                else:
                    raise Exception(u"账号密码错误")
            else:
                raise Exception(u"参数不完整，请确认")
        except Exception as e:
            self.write(str(e))
            return

class DdddOCRServer(object):
    def __init__(self):
        self.oldocr = ddddocr.DdddOcr(old=True,show_ad=False)
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.det = ddddocr.DdddOcr(det=True,show_ad=False)
        self.extra = {}
        if len(config.extra_onnx_name) == len(config.extra_charsets_name) and config.extra_onnx_name[0] and config.extra_charsets_name[0]:
            for i in range(len(config.extra_onnx_name)):
                self.extra[config.extra_onnx_name[i]]=ddddocr.DdddOcr(show_ad=False,
                                                               import_onnx_path=os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),"config",f"{config.extra_onnx_name[i]}.onnx"),
                                                               charsets_path=os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),"config",f"{config.extra_charsets_name[i]}.json"))
                logger_Web_Util.info(f"成功加载自定义Onnx模型: {config.extra_onnx_name[i]}.onnx")

    def classification(self, img: bytes, old=False, extra_onnx_name=""):
        if extra_onnx_name:
            return self.extra[extra_onnx_name].classification(img)
        if old:
            return self.oldocr.classification(img)
        else:
            return self.ocr.classification(img)

    def detection(self, img: bytes):
        return self.det.detection(img)
if ddddocr:
    DdddOCRServer = DdddOCRServer()
else:
    DdddOCRServer = None

class DdddOcrHandler(BaseHandler):
    async def get(self):
        Rtv = {}
        try:
            if DdddOCRServer:
                img = self.get_argument("img", "")
                imgurl = self.get_argument("imgurl", "")
                old = bool(strtobool(self.get_argument("old", "False"))) 
                extra_onnx_name = self.get_argument("extra_onnx_name", "")
                if img:
                    img = base64.b64decode(img)
                elif imgurl:
                    res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.get, imgurl, verify=False)),timeout=6.0)
                    base64_data = base64.b64encode(res.content).decode()
                    img = base64.b64decode(base64_data)
                else:
                    raise Exception(400)
                Rtv[u"Result"] = DdddOCRServer.classification(img,old=old, extra_onnx_name=extra_onnx_name)
                Rtv[u"状态"] = "OK"
            else:
                raise Exception(404)
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))
        return

    async def post(self):
        Rtv = {}
        try:
            if DdddOCRServer:
                if self.request.headers.get("Content-Type", "").startswith("application/json"):
                    body_dict = json.loads(self.request.body)
                    img = body_dict.get("img", "")
                    imgurl = body_dict.get("imgurl", "")
                    old = bool(strtobool(body_dict.get("old", "False")))
                    extra_onnx_name = body_dict.get("extra_onnx_name", "")
                else:
                    img = self.get_argument("img", "")
                    imgurl = self.get_argument("imgurl", "")
                    old = bool(strtobool(self.get_argument("old", "False"))) 
                    extra_onnx_name = self.get_argument("extra_onnx_name", "")

                if img:
                    img = base64.b64decode(img)
                elif imgurl:
                    res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.get, imgurl, verify=False)),timeout=6.0)
                    base64_data = base64.b64encode(res.content).decode()
                    img = base64.b64decode(base64_data)
                else:
                    raise Exception(400)
                Rtv[u"Result"] = DdddOCRServer.classification(img, old=old, extra_onnx_name=extra_onnx_name)
                Rtv[u"状态"] = "OK"
            else:
                raise Exception(404)
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))
        return

class DdddDetHandler(BaseHandler):
    async def get(self):
        Rtv = {}
        try:
            if DdddOCRServer:
                img = self.get_argument("img", "")
                imgurl = self.get_argument("imgurl", "")
                if img:
                    img = base64.b64decode(img)
                elif imgurl:
                    res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.get, imgurl, verify=False)),timeout=6.0)
                    base64_data = base64.b64encode(res.content).decode()
                    img = base64.b64decode(base64_data)
                else:
                    raise Exception(400)
                Rtv[u"Result"] = DdddOCRServer.detection(img)
                Rtv[u"状态"] = "OK"
            else:
                raise Exception(404)
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=None))
        return

    async def post(self):
        Rtv = {}
        try:
            if DdddOCRServer:
                if self.request.headers.get("Content-Type", "").startswith("application/json"):
                    body_dict = json.loads(self.request.body)
                    img = body_dict.get("img", "")
                    imgurl = body_dict.get("imgurl", "")
                else:
                    img = self.get_argument("img", "")
                    imgurl = self.get_argument("imgurl", "")
                if img:
                    img = base64.b64decode(img)
                elif imgurl:
                    res = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.get, imgurl, verify=False)),timeout=6.0)
                    base64_data = base64.b64encode(res.content).decode()
                    img = base64.b64decode(base64_data)
                else:
                    raise Exception(400)
                Rtv[u"Result"] = DdddOCRServer.detection(img)
                Rtv[u"状态"] = "OK"
            else:
                raise Exception(404)
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=None))
        return

handlers = [
    ('/util/delay', UtilDelayParaHandler),
    ('/util/delay/(\d+)', UtilDelayIntHandler),
    ('/util/delay/(\d+\.\d+)', UtilDelayHandler),
    ('/util/timestamp', TimeStampHandler),
    ('/util/unicode', UniCodeHandler),
    ('/util/urldecode', UrlDecodeHandler),
    ('/util/gb2312', GB2312Handler),
    ('/util/regex', UtilRegexHandler),
    ('/util/string/replace', UtilStrReplaceHandler),
    ('/util/rsa', UtilRSAHandler),
    ('/util/toolbox/(\d+)', toolboxHandler),
    ('/util/dddd/ocr', DdddOcrHandler),
    ('/util/dddd/det', DdddDetHandler),
]
