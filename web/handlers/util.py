#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import datetime
import html
import json
import os
import re
import time
import traceback
import urllib
from zoneinfo import ZoneInfo

import aiohttp
from Crypto import Random
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from tornado import gen

from config import delay_max_timeout, strtobool
from libs.log import Log

from .base import *

logger_web_util = Log('QD.Web.Util').getlogger()
try:
    import ddddocr
except ImportError as e:
    if config.display_import_warning:
        logger_web_util.warning('Import DdddOCR module falied: \"%s\". \nTips: This warning message is only for prompting, it will not affect running of QD framework.', e)
    ddddocr = None


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
        except Exception:
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
            self.write(
                u'Error, limited by delay_max_timeout, delay {seconds} second.'
            )
            return
        await gen.sleep(seconds)
        self.write(u'delay %s second.' % seconds)
        return


class UtilDelayIntHandler(BaseHandler):

    async def get(self, seconds):
        try:
            seconds = float(seconds)
        except Exception:
            if config.traceback_print:
                traceback.print_exc()
            self.write(u'delay %s second.' % seconds)
            return
        if seconds < 0:
            seconds = 0.0
        elif seconds > delay_max_timeout:
            seconds = delay_max_timeout
            await gen.sleep(seconds)
            self.write(
                u'Error, limited by delay_max_timeout, delay {seconds} second.'
            )
            return
        await gen.sleep(seconds)
        self.write(u'delay %s second.' % seconds)
        return


class UtilDelayHandler(BaseHandler):

    async def get(self, seconds):
        try:
            seconds = float(seconds)
        except Exception:
            if config.traceback_print:
                traceback.print_exc()
            self.write(u'delay %s second.' % seconds)
            return
        if seconds < 0:
            seconds = 0.0
        elif seconds >= delay_max_timeout:
            seconds = delay_max_timeout
            await gen.sleep(seconds)
            self.write(
                u'Error, limited by delay_max_timeout, delay {seconds} second.'
            )
            return
        await gen.sleep(seconds)
        self.write(u'delay %s second.' % seconds)
        return


class TimeStampHandler(BaseHandler):

    async def get(self):
        Rtv = {}
        try:
            ts = self.get_argument("ts", "")
            dt = self.get_argument("dt", "")
            time_format = self.get_argument("form", "%Y-%m-%d %H:%M:%S")
            if not time_format:
                time_format = "%Y-%m-%d %H:%M:%S"
            cst_tz = ZoneInfo('Asia/Shanghai')
            utc_tz = ZoneInfo("UTC")
            GMT_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"
            tmp = datetime.datetime.fromtimestamp

            if dt:
                ts = datetime.datetime.strptime(dt, time_format).timestamp()

            if ts:
                # 用户时间戳转北京时间
                Rtv[u"完整时间戳"] = float(ts)
                Rtv[u"时间戳"] = int(Rtv[u"完整时间戳"])
                Rtv[u"16位时间戳"] = int(Rtv[u"完整时间戳"] * 1000000)
                Rtv[u"周"] = tmp(Rtv[u"完整时间戳"]).strftime("%w/%W")
                Rtv[u"日"] = "/".join([
                    tmp(Rtv[u"完整时间戳"]).strftime("%j"),
                    yearday(tmp(Rtv[u"完整时间戳"]).year)
                ])
                Rtv[u"北京时间"] = tmp(Rtv[u"完整时间戳"], cst_tz).strftime(time_format)
                Rtv[u"GMT格式"] = tmp(Rtv[u"完整时间戳"], utc_tz).strftime(GMT_FORMAT)
                Rtv[u"ISO格式"] = tmp(Rtv[u"完整时间戳"],
                                    utc_tz).isoformat().split("+")[0] + "Z"
            else:
                # 当前本机时间戳, 本机时间和北京时间
                Rtv[u"完整时间戳"] = time.time()
                Rtv[u"时间戳"] = int(Rtv[u"完整时间戳"])
                Rtv[u"16位时间戳"] = int(Rtv[u"完整时间戳"] * 1000000)
                Rtv[u"本机时间"] = tmp(Rtv[u"完整时间戳"]).strftime(time_format)
                Rtv[u"周"] = tmp(Rtv[u"完整时间戳"]).strftime("%w/%W")
                Rtv[u"日"] = "/".join([
                    tmp(Rtv[u"完整时间戳"]).strftime("%j"),
                    yearday(tmp(Rtv[u"完整时间戳"]).year)
                ])
                Rtv[u"北京时间"] = tmp(Rtv[u"完整时间戳"], cst_tz).strftime(time_format)
                Rtv[u"GMT格式"] = tmp(Rtv[u"完整时间戳"], utc_tz).strftime(GMT_FORMAT)
                Rtv[u"ISO格式"] = tmp(Rtv[u"完整时间戳"],
                                    utc_tz).isoformat().split("+")[0] + "Z"
            Rtv[u"状态"] = "200"
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))

    async def post(self):
        await self.get()


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
            html_unescape = self.get_argument("html_unescape", "false")
            tmp = bytes(content, 'unicode_escape').decode('utf-8').replace(
                r'\u', r'\\u').replace(r'\\\u', r'\\u')
            tmp = bytes(tmp, 'utf-8').decode('unicode_escape')
            tmp = tmp.encode('utf-8').replace(
                b'\xc2\xa0', b'\xa0').decode('unicode_escape')
            if strtobool(html_unescape):
                tmp = html.unescape(tmp)
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
            html_unescape = self.get_argument("html_unescape", "false")
            tmp = bytes(content, 'unicode_escape').decode('utf-8').replace(
                r'\u', r'\\u').replace(r'\\\u', r'\\u')
            tmp = bytes(tmp, 'utf-8').decode('unicode_escape')
            tmp = tmp.encode('utf-8').replace(
                b'\xc2\xa0', b'\xa0').decode('unicode_escape')
            if strtobool(html_unescape):
                tmp = html.unescape(tmp)
            Rtv[u"转换后"] = tmp
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
            tmp = urllib.parse.quote(content, encoding="gb2312")
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
            tmp = urllib.parse.quote(content, encoding="gb2312")
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
            encoding = self.get_argument("encoding", "utf-8")
            unquote_plus = self.get_argument("unquote_plus", "false")
            if strtobool(unquote_plus):
                Rtv[u"转换后"] = urllib.parse.unquote_plus(content, encoding=encoding)
            else:
                Rtv[u"转换后"] = urllib.parse.unquote(content, encoding=encoding)
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
            encoding = self.get_argument("encoding", "utf-8")
            unquote_plus = self.get_argument("unquote_plus", "false")
            if strtobool(unquote_plus):
                Rtv[u"转换后"] = urllib.parse.unquote_plus(content, encoding=encoding)
            else:
                Rtv[u"转换后"] = urllib.parse.unquote(content, encoding=encoding)
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
            for cnt in range(0, len(ds)):
                temp[cnt + 1] = ds[cnt]
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
            for cnt in range(0, len(ds)):
                temp[cnt + 1] = ds[cnt]
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
            if self.get_argument("r", "") == "text":
                self.write(Rtv[u"处理后字符串"])
                return
            else:
                self.set_header('Content-Type',
                                'application/json; charset=UTF-8')
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
            if self.get_argument("r", "") == "text":
                self.write(Rtv[u"处理后字符串"])
                return
            else:
                self.set_header('Content-Type',
                                'application/json; charset=UTF-8')
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

                    while (keytemp):
                        line = keytemp[0:63]
                        lines = lines + line + "\n"
                        keytemp = keytemp.replace(line, "")

                    lines = temp[0] + "\n" + lines + temp[1]

                else:
                    self.write(u"证书格式错误")
                    return

                cipher_rsa = PKCS1_v1_5.new(RSA.import_key(lines))
                if (func.find("encode") > -1):
                    crypt_text = cipher_rsa.encrypt(
                        bytes(data, encoding="utf8"))
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
                    lines = lines + line + "\n"
                data = data.replace(" ", "+")

                cipher_rsa = PKCS1_v1_5.new(RSA.import_key(lines))
                if (func.find("encode") > -1):
                    crypt_text = cipher_rsa.encrypt(
                        bytes(data, encoding="utf8"))
                    crypt_text = base64.b64encode(crypt_text).decode('utf8')
                    self.write(crypt_text)
                    return
                elif (func.find("decode") > -1):
                    decrypt_text = cipher_rsa.decrypt(base64.b64decode(data),
                                                      Random.new().read)
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
        self.current_user["isadmin"] or self.check_permission(
            {"userid": int(userid)}, 'r')
        await self.render('toolbox.html', userid=userid)

    async def post(self, userid):
        try:
            email = self.get_argument("email", "")
            pwd = self.get_argument("pwd", "")
            f = self.get_argument("f", "")
            if (email) and (pwd) and (f):
                async with self.db.transaction() as sql_session:
                    if await self.db.user.challenge_MD5(
                            email, pwd, sql_session=sql_session
                    ) or await self.db.user.challenge(
                            email, pwd, sql_session=sql_session):
                        notepadid = self.get_argument("id_notepad", 1)
                        userid = (await self.db.user.get(
                            email=email,
                            fields=('id', ),
                            sql_session=sql_session))['id']
                        text_data = (await self.db.notepad.get(
                            userid,
                            notepadid,
                            fields=('content', ),
                            sql_session=sql_session))['content']
                        new_data = self.get_argument("data", "")
                        if (f.find('write') > -1):
                            text_data = new_data
                            await self.db.notepad.mod(userid,
                                                      notepadid,
                                                      content=text_data,
                                                      sql_session=sql_session)
                        elif (f.find('append') > -1):
                            if text_data is not None:
                                text_data = text_data + '\r\n' + new_data
                            else:
                                text_data = new_data
                            await self.db.notepad.mod(userid,
                                                      notepadid,
                                                      content=text_data,
                                                      sql_session=sql_session)
                        self.write(text_data)
                        return
                    else:
                        raise Exception(u"账号密码错误")
            else:
                raise Exception(u"参数不完整，请确认")
        except Exception as e:
            self.write(str(e))
            return


class toolbox_notepad_Handler(BaseHandler):

    @tornado.web.authenticated
    async def get(self, userid=None, notepadid=1):
        if userid is None:
            raise HTTPError(405)
        self.current_user["isadmin"] or self.check_permission(
            {"userid": int(userid)}, 'r')
        notepadlist = await self.db.notepad.list(fields=('notepadid',
                                                         'content'),
                                                 limit=20,
                                                 userid=userid)
        notepadlist.sort(key=lambda x: x['notepadid'])
        if len(notepadlist) == 0:
            if await self.db.user.get(id=userid, fields=('id', )) is not None:
                await self.db.notepad.add(dict(userid=userid, notepadid=1))
                notepadlist = await self.db.notepad.list(fields=('notepadid',
                                                                 'content'),
                                                         limit=20,
                                                         userid=userid)
            else:
                raise HTTPError(404,
                                log_message=u"用户不存在或未创建记事本",
                                reason=u"用户不存在或未创建记事本")
        if int(notepadid) == 0:
            notepadid = notepadlist[-1]['notepadid']
        await self.render('toolbox-notepad.html',
                          notepad_id=int(notepadid),
                          notepad_list=notepadlist,
                          userid=userid)
        return

    # @tornado.web.authenticated
    async def post(self, userid=None):
        try:
            email = self.get_argument("email", "")
            pwd = self.get_argument("pwd", "")
            f = self.get_argument("f", "")
            if (email) and (pwd) and (f):
                async with self.db.transaction() as sql_session:
                    if await self.db.user.challenge_MD5(
                            email, pwd, sql_session=sql_session
                    ) or await self.db.user.challenge(
                            email, pwd, sql_session=sql_session):
                        notepadid = int(self.get_argument("id_notepad", 1))
                        userid = (await self.db.user.get(
                            email=email,
                            fields=('id', ),
                            sql_session=sql_session))['id']
                        notepad = await self.db.notepad.get(
                            userid,
                            notepadid,
                            fields=('content', ),
                            sql_session=sql_session)
                        if not notepad:
                            if notepadid == 1:
                                await self.db.notepad.add(
                                    dict(userid=userid, notepadid=notepadid),
                                    sql_session=sql_session)
                            else:
                                raise Exception(u"记事本不存在")
                        text_data = notepad['content']
                        new_data = self.get_argument("data", "")
                        if (f.find('write') > -1):
                            text_data = new_data
                            await self.db.notepad.mod(userid,
                                                      notepadid,
                                                      content=text_data,
                                                      sql_session=sql_session)
                        elif (f.find('append') > -1):
                            if text_data is not None:
                                text_data = text_data + '\r\n' + new_data
                            else:
                                text_data = new_data
                            await self.db.notepad.mod(userid,
                                                      notepadid,
                                                      content=text_data,
                                                      sql_session=sql_session)
                        self.write(text_data)
                        return
                    else:
                        raise Exception(u"账号密码错误")
            else:
                raise Exception(u"参数不完整，请确认")
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if (str(e).find('get user need id or email') > -1):
                e = u'请输入用户名/密码'
            self.write(str(e))
            self.set_status(400)
            logger_web_handler.error(
                'UserID: %s modify Notepad_Toolbox failed! Reason: %s', userid
                or '-1', str(e))
            return


class toolbox_notepad_list_Handler(BaseHandler):

    async def get(self, userid=None, notepadid=1):
        if userid is None:
            raise HTTPError(405)
        self.current_user["isadmin"] or self.check_permission(
            {"userid": int(userid)}, 'r')
        notepadlist = await self.db.notepad.list(fields=('notepadid',
                                                         'content'),
                                                 limit=20,
                                                 userid=userid)
        notepadlist.sort(key=lambda x: x['notepadid'])
        if len(notepadlist) == 0:
            if await self.db.user.get(id=userid, fields=('id', )) is not None:
                await self.db.notepad.add(dict(userid=userid, notepadid=1))
                notepadlist = await self.db.notepad.list(fields=('notepadid',
                                                                 'content'),
                                                         limit=20,
                                                         userid=userid)
            else:
                raise HTTPError(404,
                                log_message=u"用户不存在或未创建记事本",
                                reason=u"用户不存在或未创建记事本")
        if int(notepadid) == 0:
            notepadid = notepadlist[-1]['notepadid']
        await self.render('toolbox-notepad.html',
                          notepad_id=notepadid,
                          notepad_list=notepadlist,
                          userid=userid)
        return

    async def post(self, userid=None):
        try:
            email = self.get_argument("email", "")
            pwd = self.get_argument("pwd", "")
            f = self.get_argument("f", "list")
            if (email) and (pwd) and (f):
                async with self.db.transaction() as sql_session:
                    if await self.db.user.challenge_MD5(
                            email, pwd, sql_session=sql_session
                    ) or await self.db.user.challenge(
                            email, pwd, sql_session=sql_session):
                        userid = (await self.db.user.get(
                            email=email,
                            fields=('id', ),
                            sql_session=sql_session))['id']
                        notepadid = self.get_argument("id_notepad", "-1")
                        if not notepadid:
                            notepadid = -1
                        else:
                            notepadid = int(notepadid)
                        notepadlist = await self.db.notepad.list(
                            fields=('notepadid', ),
                            limit=20,
                            userid=userid,
                            sql_session=sql_session)
                        notepadlist = [x['notepadid'] for x in notepadlist]
                        notepadlist.sort()
                        if len(notepadlist) == 0:
                            raise Exception(u"无法获取该用户记事本编号")
                        if f.find('add') > -1:
                            if len(notepadlist) >= 20:
                                raise Exception(u"记事本数量超过上限, limit: 20")
                            new_data = self.get_argument("data", '')
                            if new_data == '':
                                new_data = None
                            if notepadid == -1:
                                notepadid = notepadlist[-1] + 1
                            elif notepadid in notepadlist:
                                raise Exception(u"记事本编号已存在, id_notepad: %s" %
                                                notepadid)
                            await self.db.notepad.add(dict(userid=userid,
                                                           notepadid=notepadid,
                                                           content=new_data),
                                                      sql_session=sql_session)
                            self.write(u"添加成功, id_notepad: %s" % (notepadid))
                            return
                        elif f.find('delete') > -1:
                            if notepadid > 0:
                                if notepadid not in notepadlist:
                                    raise Exception(
                                        u"记事本编号不存在, id_notepad: %s" %
                                        notepadid)
                                if notepadid == 1:
                                    raise Exception(u"默认记事本不能删除")
                                await self.db.notepad.delete(
                                    userid, notepadid, sql_session=sql_session)
                                self.write(u"删除成功, id_notepad: %s" %
                                           (notepadid))
                                return
                            else:
                                raise Exception(u"id_notepad参数不完整, 请确认")
                        elif f.find('list') > -1:
                            self.write(notepadlist)
                            return
                        else:
                            raise Exception(u"参数不完整, 请确认")
                    else:
                        raise Exception(u"账号密码错误")
            else:
                raise Exception(u"参数不完整, 请确认")
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if (str(e).find('get user need id or email') > -1):
                e = u'请输入用户名/密码'
            self.write(str(e))
            self.set_status(400)
            logger_web_handler.error(
                'UserID: %s %s Notepad_Toolbox failed! Reason: %s', userid
                or '-1', f, str(e))
            return


class DdddOCRServer(object):

    def __init__(self):
        if ddddocr is not None and hasattr(ddddocr, "DdddOcr"):
            self.oldocr = ddddocr.DdddOcr(old=True, show_ad=False)
            self.ocr = ddddocr.DdddOcr(show_ad=False)
            self.det = ddddocr.DdddOcr(det=True, show_ad=False)
            self.slide = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
            self.extra = {}
            if len(config.extra_onnx_name) == len(
                    config.extra_charsets_name
            ) and config.extra_onnx_name[0] and config.extra_charsets_name[0]:
                for i in range(len(config.extra_onnx_name)):
                    self.extra[config.extra_onnx_name[i]] = ddddocr.DdddOcr(
                        show_ad=False,
                        import_onnx_path=os.path.join(
                            os.path.abspath(
                                os.path.dirname(
                                    os.path.dirname(os.path.dirname(__file__)))),
                            "config", f"{config.extra_onnx_name[i]}.onnx"),
                        charsets_path=os.path.join(
                            os.path.abspath(
                                os.path.dirname(
                                    os.path.dirname(os.path.dirname(__file__)))),
                            "config", f"{config.extra_charsets_name[i]}.json"))
                    logger_web_util.info(
                        f"成功加载自定义Onnx模型: {config.extra_onnx_name[i]}.onnx")

    def classification(self, img: bytes, old=False, extra_onnx_name=""):
        if extra_onnx_name:
            return self.extra[extra_onnx_name].classification(img)
        if old:
            return self.oldocr.classification(img)
        else:
            return self.ocr.classification(img)

    def detection(self, img: bytes):
        return self.det.detection(img)

    def slide_match(self, imgtarget: bytes, imgbg: bytes, comparison=False, simple_target=False):
        if comparison:
            return self.slide.slide_comparison(imgtarget, imgbg)
        if not simple_target:
            try:
                return self.slide.slide_match(imgtarget, imgbg)
            except:
                pass
        return self.slide.slide_match(imgtarget, imgbg, simple_target=True)


if ddddocr:
    DdddOCRServer = DdddOCRServer()
else:
    DdddOCRServer = None


async def get_img_from_url(imgurl):
    async with aiohttp.ClientSession(
            conn_timeout=config.connect_timeout) as session:
        async with session.get(imgurl,
                               verify_ssl=False,
                               timeout=config.request_timeout) as res:
            content = await res.read()
            base64_data = base64.b64encode(content).decode()
            return base64.b64decode(base64_data)


async def get_img(img="", imgurl="",):
    if img:
        # 判断是否为URL
        if img.startswith("http"):
            try:
                return await get_img_from_url(img)
            except:
                return base64.b64decode(img)
        return base64.b64decode(img)
    elif imgurl:
        return await get_img_from_url(imgurl)
    else:
        raise HTTPError(415)


class DdddOcrHandler(BaseHandler):

    async def get(self):
        Rtv = {}
        try:
            if DdddOCRServer:
                img = self.get_argument("img", "")
                imgurl = self.get_argument("imgurl", "")
                old = bool(strtobool(self.get_argument("old", "False")))
                extra_onnx_name = self.get_argument("extra_onnx_name", "")
                img = await get_img(img, imgurl)
                Rtv[u"Result"] = DdddOCRServer.classification(
                    img, old=old, extra_onnx_name=extra_onnx_name)
                Rtv[u"状态"] = "OK"
            else:
                raise HTTPError(406)
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=4))
        return

    async def post(self):
        Rtv = {}
        try:
            if DdddOCRServer:
                if self.request.headers.get("Content-Type",
                                            "").startswith("application/json"):
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

                img = await get_img(img, imgurl)
                Rtv[u"Result"] = DdddOCRServer.classification(
                    img, old=old, extra_onnx_name=extra_onnx_name)
                Rtv[u"状态"] = "OK"
            else:
                raise HTTPError(406)
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
                img = await get_img(img, imgurl)
                Rtv[u"Result"] = DdddOCRServer.detection(img)
                Rtv[u"状态"] = "OK"
            else:
                raise HTTPError(406)
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=None))
        return

    async def post(self):
        Rtv = {}
        try:
            if DdddOCRServer:
                if self.request.headers.get("Content-Type",
                                            "").startswith("application/json"):
                    body_dict = json.loads(self.request.body)
                    img = body_dict.get("img", "")
                    imgurl = body_dict.get("imgurl", "")
                else:
                    img = self.get_argument("img", "")
                    imgurl = self.get_argument("imgurl", "")
                img = await get_img(img, imgurl)
                Rtv[u"Result"] = DdddOCRServer.detection(img)
                Rtv[u"状态"] = "OK"
            else:
                raise Exception(404)
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=None))
        return


class DdddSlideHandler(BaseHandler):

    async def get(self):
        Rtv = {}
        try:
            if DdddOCRServer:
                imgtarget = self.get_argument("imgtarget", "")
                imgbg = self.get_argument("imgbg", "")
                simple_target = bool(strtobool(self.get_argument("simple_target", "False")))
                comparison = bool(strtobool(self.get_argument("comparison", "False")))
                imgtarget = await get_img(imgtarget, "")
                imgbg = await get_img(imgbg, "")
                Rtv[u"Result"] = DdddOCRServer.slide_match(imgtarget, imgbg, comparison=comparison, simple_target=simple_target)
                Rtv[u"状态"] = "OK"
            else:
                raise HTTPError(406)
        except Exception as e:
            Rtv[u"状态"] = str(e)

        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json.dumps(Rtv, ensure_ascii=False, indent=None))
        return

    async def post(self):
        Rtv = {}
        try:
            if DdddOCRServer:
                if self.request.headers.get("Content-Type",
                                            "").startswith("application/json"):
                    body_dict = json.loads(self.request.body)
                    imgtarget = body_dict.get("imgtarget", "")
                    imgbg = body_dict.get("imgbg", "")
                    simple_target = bool(strtobool(body_dict.get("simple_target", "False")))
                    comparison = bool(strtobool(body_dict.get("comparison", "False")))
                else:
                    imgtarget = self.get_argument("imgtarget", "")
                    imgbg = self.get_argument("imgbg", "")
                    simple_target = bool(strtobool(self.get_argument("simple_target", "False")))
                    comparison = bool(strtobool(self.get_argument("comparison", "False")))

                imgtarget = await get_img(imgtarget, "")
                imgbg = await get_img(imgbg, "")
                Rtv[u"Result"] = DdddOCRServer.slide_match(imgtarget, imgbg, comparison=comparison, simple_target=simple_target)
                Rtv[u"状态"] = "OK"
            else:
                raise HTTPError(406)
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
    ('/util/toolbox/notepad', toolbox_notepad_Handler),
    ('/util/toolbox/(\d+)/notepad', toolbox_notepad_Handler),
    ('/util/toolbox/(\d+)/notepad/(\d+)', toolbox_notepad_Handler),
    ('/util/toolbox/notepad/list', toolbox_notepad_list_Handler),
    ('/util/toolbox/(\d+)/notepad/list', toolbox_notepad_list_Handler),
    ('/util/toolbox/(\d+)/notepad/list/(\d+)', toolbox_notepad_list_Handler),
    ('/util/dddd/ocr', DdddOcrHandler),
    ('/util/dddd/det', DdddDetHandler),
    ('/util/dddd/slide', DdddSlideHandler),
]
