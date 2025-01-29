#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-raised

import base64
import datetime
import html
import json
import os
import re
import time
import traceback
import urllib
from typing import Optional
from zoneinfo import ZoneInfo

import aiohttp
from Crypto import Random
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from tornado import gen
from tornado.web import HTTPError, authenticated

import config
from config import delay_max_timeout, strtobool
from libs.log import Log
from web.handlers.base import BaseHandler, logger_web_handler

logger_web_util = Log("QD.Web.Util").getlogger()
try:
    import ddddocr  # type: ignore
except ImportError as e:
    if config.display_import_warning:
        logger_web_util.warning(
            'Import DdddOCR module falied: "%s". \nTips: This warning message is only for prompting, it will not affect running of QD framework.',
            e,
        )
    ddddocr = None


def request_parse(req_data):
    """解析请求数据并以json形式返回"""
    if req_data.method == "POST":
        data = req_data.body_arguments
    elif req_data.method == "GET":
        data = req_data.arguments
    return data


class UtilDelayParaHandler(BaseHandler):
    async def get(self):
        try:
            seconds = float(self.get_argument("seconds", 0))
        except Exception as e:
            logger_web_handler.debug(
                "Error, delay 0.0 second: %s", e, exc_info=config.traceback_print
            )
            self.write("Error, delay 0.0 second.")
            return
        if seconds < 0:
            seconds = 0.0
        elif seconds >= delay_max_timeout:
            seconds = delay_max_timeout
            await gen.sleep(seconds)
            self.write("Error, limited by delay_max_timeout, delay {seconds} second.")
            return
        await gen.sleep(seconds)
        self.write(f"delay {seconds} second.")
        return


class UtilDelayIntHandler(BaseHandler):
    async def get(self, seconds):
        try:
            seconds = float(seconds)
        except Exception as e:
            logger_web_handler.debug(
                "Error, delay 0.0 second: %s", e, exc_info=config.traceback_print
            )
            self.write("Error, delay 0.0 second.")
            return
        if seconds < 0:
            seconds = 0.0
        elif seconds > delay_max_timeout:
            seconds = delay_max_timeout
            await gen.sleep(seconds)
            self.write("Error, limited by delay_max_timeout, delay {seconds} second.")
            return
        await gen.sleep(seconds)
        self.write(f"delay {seconds} second.")
        return


class UtilDelayHandler(BaseHandler):
    async def get(self, seconds):
        try:
            seconds = float(seconds)
        except Exception as e:
            logger_web_handler.debug(
                "Error, delay 0.0 second: %s", e, exc_info=config.traceback_print
            )
            self.write("Error, delay 0.0 second.")
            return
        if seconds < 0:
            seconds = 0.0
        elif seconds >= delay_max_timeout:
            seconds = delay_max_timeout
            await gen.sleep(seconds)
            self.write(
                f"Error, limited by {delay_max_timeout}, delay {seconds} second."
            )
            return
        await gen.sleep(seconds)
        self.write(f"delay {seconds} second.")
        return


GMT_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


class TimeStampHandler(BaseHandler):
    async def get(self):
        rtv = {}
        try:
            ts = self.get_argument("ts", "")
            dt = self.get_argument("dt", "")
            time_format = self.get_argument("form", "%Y-%m-%d %H:%M:%S")
            if not time_format:
                time_format = "%Y-%m-%d %H:%M:%S"
            cst_tz = ZoneInfo("Asia/Shanghai")
            utc_tz = ZoneInfo("UTC")
            tmp = datetime.datetime.fromtimestamp

            if dt:
                ts = datetime.datetime.strptime(dt, time_format).timestamp()

            if ts:
                # 用户时间戳转北京时间
                rtv["完整时间戳"] = float(ts)
                rtv["时间戳"] = int(rtv["完整时间戳"])
                rtv["16位时间戳"] = int(rtv["完整时间戳"] * 1000000)
                rtv["周"] = tmp(rtv["完整时间戳"]).strftime("%w/%W")
                rtv["日"] = "/".join(
                    [
                        tmp(rtv["完整时间戳"]).strftime("%j"),
                        yearday(tmp(rtv["完整时间戳"]).year),
                    ]
                )
                rtv["北京时间"] = tmp(rtv["完整时间戳"], cst_tz).strftime(time_format)
                rtv["GMT格式"] = tmp(rtv["完整时间戳"], utc_tz).strftime(GMT_FORMAT)
                rtv["ISO格式"] = (
                    tmp(rtv["完整时间戳"], utc_tz).isoformat().split("+")[0] + "Z"
                )
            else:
                # 当前本机时间戳, 本机时间和北京时间
                rtv["完整时间戳"] = time.time()
                rtv["时间戳"] = int(rtv["完整时间戳"])
                rtv["16位时间戳"] = int(rtv["完整时间戳"] * 1000000)
                rtv["本机时间"] = tmp(rtv["完整时间戳"]).strftime(time_format)
                rtv["周"] = tmp(rtv["完整时间戳"]).strftime("%w/%W")
                rtv["日"] = "/".join(
                    [
                        tmp(rtv["完整时间戳"]).strftime("%j"),
                        yearday(tmp(rtv["完整时间戳"]).year),
                    ]
                )
                rtv["北京时间"] = tmp(rtv["完整时间戳"], cst_tz).strftime(time_format)
                rtv["GMT格式"] = tmp(rtv["完整时间戳"], utc_tz).strftime(GMT_FORMAT)
                rtv["ISO格式"] = (
                    tmp(rtv["完整时间戳"], utc_tz).isoformat().split("+")[0] + "Z"
                )
            rtv["状态"] = "200"
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))

    async def post(self):
        await self.get()


def yearday(year):
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        return "366"
    else:
        return "365"


class UniCodeHandler(BaseHandler):
    async def get(self):
        rtv = {}
        try:
            content = self.get_argument("content", "")
            html_unescape = self.get_argument("html_unescape", "false")
            tmp = (
                bytes(content, "unicode_escape")
                .decode("utf-8")
                .replace(r"\u", r"\\u")
                .replace(r"\\\u", r"\\u")
            )
            tmp = bytes(tmp, "utf-8").decode("unicode_escape")
            tmp = (
                tmp.encode("utf-8")
                .replace(b"\xc2\xa0", b"\xa0")
                .decode("unicode_escape")
            )
            if strtobool(html_unescape):
                tmp = html.unescape(tmp)
            rtv["转换后"] = tmp
            rtv["状态"] = "200"
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
        return

    async def post(self):
        rtv = {}
        try:
            content = self.get_argument("content", "")
            html_unescape = self.get_argument("html_unescape", "false")
            tmp = (
                bytes(content, "unicode_escape")
                .decode("utf-8")
                .replace(r"\u", r"\\u")
                .replace(r"\\\u", r"\\u")
            )
            tmp = bytes(tmp, "utf-8").decode("unicode_escape")
            tmp = (
                tmp.encode("utf-8")
                .replace(b"\xc2\xa0", b"\xa0")
                .decode("unicode_escape")
            )
            if strtobool(html_unescape):
                tmp = html.unescape(tmp)
            rtv["转换后"] = tmp
            rtv["状态"] = "200"
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
        return


class GB2312Handler(BaseHandler):
    async def get(self):
        rtv = {}
        try:
            content = self.get_argument("content", "")
            tmp = urllib.parse.quote(content, encoding="gb2312")
            rtv["转换后"] = tmp
            rtv["状态"] = "200"
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
        return

    async def post(self):
        rtv = {}
        try:
            content = self.get_argument("content", "")
            tmp = urllib.parse.quote(content, encoding="gb2312")
            rtv["转换后"] = tmp
            rtv["状态"] = "200"
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
        return


class UrlDecodeHandler(BaseHandler):
    async def get(self):
        rtv = {}
        try:
            content = self.get_argument("content", "")
            encoding = self.get_argument("encoding", "utf-8")
            unquote_plus = self.get_argument("unquote_plus", "false")
            if strtobool(unquote_plus):
                rtv["转换后"] = urllib.parse.unquote_plus(content, encoding=encoding)
            else:
                rtv["转换后"] = urllib.parse.unquote(content, encoding=encoding)
            rtv["状态"] = "200"
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
        return

    async def post(self):
        rtv = {}
        try:
            content = self.get_argument("content", "")
            encoding = self.get_argument("encoding", "utf-8")
            unquote_plus = self.get_argument("unquote_plus", "false")
            if strtobool(unquote_plus):
                rtv["转换后"] = urllib.parse.unquote_plus(content, encoding=encoding)
            else:
                rtv["转换后"] = urllib.parse.unquote(content, encoding=encoding)
            rtv["状态"] = "200"
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
        return


class UtilRegexHandler(BaseHandler):
    async def get(self):
        rtv = {}
        try:
            data = self.get_argument("data", "")
            p = self.get_argument("p", "")
            temp = {}
            ds = re.findall(p, data, re.IGNORECASE)
            for cnt, d in enumerate(ds):
                temp[cnt + 1] = d
            rtv["数据"] = temp
            rtv["状态"] = "OK"
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
        return

    async def post(self):
        rtv = {}
        try:
            data = self.get_argument("data", "")
            p = self.get_argument("p", "")
            temp = {}
            ds = re.findall(p, data, re.IGNORECASE)
            for cnt, d in enumerate(ds):
                temp[cnt + 1] = d
            rtv["数据"] = temp
            rtv["状态"] = "OK"
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))

        return


class UtilStrReplaceHandler(BaseHandler):
    async def get(self):
        rtv = {}
        try:
            s = self.get_argument("s", "")
            p = self.get_argument("p", "")
            t = self.get_argument("t", "")
            rtv["原始字符串"] = s
            rtv["处理后字符串"] = re.sub(p, t, s)
            rtv["状态"] = "OK"
            if self.get_argument("r", "") == "text":
                self.write(html.escape(rtv["处理后字符串"]))
                return
            else:
                self.set_header("Content-Type", "application/json; charset=UTF-8")
                self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
                return
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
        return

    async def post(self):
        rtv = {}
        try:
            s = self.get_argument("s", "")
            p = self.get_argument("p", "")
            t = self.get_argument("t", "")
            rtv["原始字符串"] = s
            rtv["处理后字符串"] = re.sub(p, t, s)
            rtv["状态"] = "OK"
            if self.get_argument("r", "") == "text":
                self.write(html.escape(rtv["处理后字符串"]))
                return
            else:
                self.set_header("Content-Type", "application/json; charset=UTF-8")
                self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
                return
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
        return


class UtilRSAHandler(BaseHandler):
    async def get(self):
        try:
            key = self.get_argument("key", "")
            data = self.get_argument("data", "")
            func = self.get_argument("f", "encode")
            if key and data and func:
                lines = ""
                temp = key
                temp = re.findall("-----.*?-----", temp)
                if len(temp) == 2:
                    keytemp = key
                    for t in temp:
                        keytemp = keytemp.replace(t, "")

                    while keytemp:
                        line = keytemp[0:63]
                        lines = lines + line + "\n"
                        keytemp = keytemp.replace(line, "")

                    lines = temp[0] + "\n" + lines + temp[1]

                else:
                    self.write("证书格式错误")
                    return

                cipher_rsa = PKCS1_v1_5.new(RSA.import_key(lines))
                if func.find("encode") > -1:
                    crypt_text = cipher_rsa.encrypt(bytes(data, encoding="utf8"))
                    crypt_text = base64.b64encode(crypt_text).decode("utf8")
                    self.write(crypt_text)
                    return
                elif func.find("decode") > -1:
                    t1 = base64.b64decode(data)
                    decrypt_text = cipher_rsa.decrypt(t1, Random.new().read)
                    decrypt_text = decrypt_text.decode("utf8")
                    self.write(decrypt_text)
                    return
                else:
                    self.write("功能选择错误")
                    return
            else:
                self.write("参数不完整，请确认")
                return
        except Exception as e:
            self.write(str(e))
            return

    async def post(self):
        try:
            key = self.get_argument("key", "")
            data = self.get_argument("data", "")
            func = self.get_argument("f", "encode")
            if key and data and func:
                lines = ""
                for line in key.split("\n"):
                    if line.find("--") < 0:
                        line = line.replace(" ", "+")
                    lines = lines + line + "\n"
                data = data.replace(" ", "+")

                cipher_rsa = PKCS1_v1_5.new(RSA.import_key(lines))
                if func.find("encode") > -1:
                    crypt_text = cipher_rsa.encrypt(bytes(data, encoding="utf8"))
                    crypt_text = base64.b64encode(crypt_text).decode("utf8")
                    self.write(crypt_text)
                    return
                elif func.find("decode") > -1:
                    decrypt_text = cipher_rsa.decrypt(
                        base64.b64decode(data), Random.new().read
                    )
                    decrypt_text = decrypt_text.decode("utf8")
                    self.write(decrypt_text)
                    return
                else:
                    self.write("功能选择错误")
                    return
            else:
                self.write("参数不完整，请确认")
                return
        except Exception as e:
            self.write(str(e))
            return


class ToolboxHandler(BaseHandler):
    async def get(self, userid):
        if self.current_user["isadmin"] or self.check_permission(
            {"userid": int(userid)}, "r"
        ):
            await self.render("toolbox.html", userid=userid)

    async def post(self, userid):
        try:
            email = self.get_argument("email", "")
            pwd = self.get_argument("pwd", "")
            f = self.get_argument("f", "")
            if email and pwd and f:
                async with self.db.transaction() as sql_session:
                    if await self.db.user.challenge_md5(
                        email, pwd, sql_session=sql_session
                    ) or await self.db.user.challenge(
                        email, pwd, sql_session=sql_session
                    ):
                        notepadid = self.get_argument("id_notepad", 1)
                        userid = (
                            await self.db.user.get(
                                email=email, fields=("id",), sql_session=sql_session
                            )
                        )["id"]
                        text_data = (
                            await self.db.notepad.get(
                                userid,
                                notepadid,
                                fields=("content",),
                                sql_session=sql_session,
                            )
                        )["content"]
                        new_data = self.get_argument("data", "")
                        if f.find("write") > -1:
                            text_data = new_data
                            await self.db.notepad.mod(
                                userid,
                                notepadid,
                                content=text_data,
                                sql_session=sql_session,
                            )
                        elif f.find("append") > -1:
                            if text_data is not None:
                                text_data = text_data + "\r\n" + new_data
                            else:
                                text_data = new_data
                            await self.db.notepad.mod(
                                userid,
                                notepadid,
                                content=text_data,
                                sql_session=sql_session,
                            )
                        self.write(text_data)
                        return
                    else:
                        raise Exception("账号密码错误")
            else:
                raise Exception("参数不完整，请确认")
        except Exception as e:
            self.write(str(e))
            return


class ToolboxNotepadHandler(BaseHandler):
    @authenticated
    async def get(self, userid=None, notepadid=1):
        if userid is None:
            raise HTTPError(405)
        if self.current_user["isadmin"] or self.check_permission(
            {"userid": int(userid)}, "r"
        ):
            notepadlist = await self.db.notepad.list(
                fields=("notepadid", "content"),
                limit=config.notepad_limit,
                userid=userid,
            )
            notepadlist.sort(key=lambda x: x["notepadid"])
            if len(notepadlist) == 0:
                if await self.db.user.get(id=userid, fields=("id",)) is not None:
                    await self.db.notepad.add(dict(userid=userid, notepadid=1))
                    notepadlist = await self.db.notepad.list(
                        fields=("notepadid", "content"),
                        limit=config.notepad_limit,
                        userid=userid,
                    )
                else:
                    raise HTTPError(
                        404,
                        log_message="用户不存在或未创建记事本",
                        reason="用户不存在或未创建记事本",
                    )
            if int(notepadid) == 0:
                notepadid = notepadlist[-1]["notepadid"]
            await self.render(
                "toolbox-notepad.html",
                notepad_id=int(notepadid),
                notepad_list=notepadlist,
                userid=userid,
            )
        return

    # @authenticated
    async def post(self, userid=None):
        try:
            email = self.get_argument("email", "")
            pwd = self.get_argument("pwd", "")
            f = self.get_argument("f", "")
            if email and pwd and f:
                async with self.db.transaction() as sql_session:
                    if await self.db.user.challenge_md5(
                        email, pwd, sql_session=sql_session
                    ) or await self.db.user.challenge(
                        email, pwd, sql_session=sql_session
                    ):
                        notepadid = int(self.get_argument("id_notepad", 1))
                        userid = (
                            await self.db.user.get(
                                email=email, fields=("id",), sql_session=sql_session
                            )
                        )["id"]
                        notepad = await self.db.notepad.get(
                            userid,
                            notepadid,
                            fields=("content",),
                            sql_session=sql_session,
                        )
                        if not notepad:
                            if notepadid == 1:
                                await self.db.notepad.add(
                                    dict(userid=userid, notepadid=notepadid),
                                    sql_session=sql_session,
                                )
                            else:
                                raise Exception("记事本不存在")
                        text_data = notepad["content"]
                        new_data = self.get_argument("data", "")
                        if f.find("write") > -1:
                            text_data = new_data
                            await self.db.notepad.mod(
                                userid,
                                notepadid,
                                content=text_data,
                                sql_session=sql_session,
                            )
                        elif f.find("append") > -1:
                            if text_data is not None:
                                text_data = text_data + "\r\n" + new_data
                            else:
                                text_data = new_data
                            await self.db.notepad.mod(
                                userid,
                                notepadid,
                                content=text_data,
                                sql_session=sql_session,
                            )
                        self.write(text_data)
                        return
                    else:
                        raise Exception("账号密码错误")
            else:
                raise Exception("参数不完整，请确认")
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if str(e).find("get user need id or email") > -1:
                e = "请输入用户名/密码"
            self.write(str(e))
            self.set_status(400)
            logger_web_handler.error(
                "UserID: %s modify Notepad_Toolbox failed! Reason: %s",
                userid or "-1",
                str(e),
            )
            return


class ToolboxNotepadListHandler(BaseHandler):
    async def get(self, userid=None, notepadid=1):
        if userid is None:
            raise HTTPError(405)
        if self.current_user["isadmin"] or self.check_permission(
            {"userid": int(userid)}, "r"
        ):
            notepadlist = await self.db.notepad.list(
                fields=("notepadid", "content"),
                limit=config.notepad_limit,
                userid=userid,
            )
            notepadlist.sort(key=lambda x: x["notepadid"])
            if len(notepadlist) == 0:
                if await self.db.user.get(id=userid, fields=("id",)) is not None:
                    await self.db.notepad.add(dict(userid=userid, notepadid=1))
                    notepadlist = await self.db.notepad.list(
                        fields=("notepadid", "content"),
                        limit=config.notepad_limit,
                        userid=userid,
                    )
                else:
                    raise HTTPError(
                        404,
                        log_message="用户不存在或未创建记事本",
                        reason="用户不存在或未创建记事本",
                    )
            if int(notepadid) == 0:
                notepadid = notepadlist[-1]["notepadid"]
            await self.render(
                "toolbox-notepad.html",
                notepad_id=notepadid,
                notepad_list=notepadlist,
                userid=userid,
            )
        return

    async def post(self, userid=None):
        try:
            email = self.get_argument("email", "")
            pwd = self.get_argument("pwd", "")
            f = self.get_argument("f", "list")
            if email and pwd and f:
                async with self.db.transaction() as sql_session:
                    if await self.db.user.challenge_md5(
                        email, pwd, sql_session=sql_session
                    ) or await self.db.user.challenge(
                        email, pwd, sql_session=sql_session
                    ):
                        userid = (
                            await self.db.user.get(
                                email=email, fields=("id",), sql_session=sql_session
                            )
                        )["id"]
                        notepadid = self.get_argument("id_notepad", "-1")
                        if not notepadid:
                            notepadid = -1
                        else:
                            notepadid = int(notepadid)
                        notepadlist = await self.db.notepad.list(
                            fields=("notepadid",),
                            limit=config.notepad_limit,
                            userid=userid,
                            sql_session=sql_session,
                        )
                        notepadlist = [x["notepadid"] for x in notepadlist]
                        notepadlist.sort()
                        if len(notepadlist) == 0:
                            raise Exception("无法获取该用户记事本编号")
                        if f.find("add") > -1:
                            if len(notepadlist) >= config.notepad_limit:
                                raise Exception(
                                    f"记事本数量超过上限, limit: {config.notepad_limit}"
                                )
                            new_data = self.get_argument("data", "")
                            if new_data == "":
                                new_data = None
                            if notepadid == -1:
                                notepadid = notepadlist[-1] + 1
                            elif notepadid in notepadlist:
                                raise Exception(
                                    f"记事本编号已存在, id_notepad: {notepadid}"
                                )
                            await self.db.notepad.add(
                                dict(
                                    userid=userid, notepadid=notepadid, content=new_data
                                ),
                                sql_session=sql_session,
                            )
                            self.write(f"添加成功, id_notepad: {notepadid}")
                            return
                        elif f.find("delete") > -1:
                            if notepadid > 0:
                                if notepadid not in notepadlist:
                                    raise Exception(
                                        f"记事本编号不存在, id_notepad: {notepadid}"
                                    )
                                if notepadid == 1:
                                    raise Exception("默认记事本不能删除")
                                await self.db.notepad.delete(
                                    userid, notepadid, sql_session=sql_session
                                )
                                self.write(f"删除成功, id_notepad: {notepadid}")
                                return
                            else:
                                raise Exception("id_notepad参数不完整, 请确认")
                        elif f.find("list") > -1:
                            self.write(notepadlist)
                            return
                        else:
                            raise Exception("参数不完整, 请确认")
                    else:
                        raise Exception("账号密码错误")
            else:
                raise Exception("参数不完整, 请确认")
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if str(e).find("get user need id or email") > -1:
                e = "请输入用户名/密码"
            self.write(str(e))
            self.set_status(400)
            logger_web_handler.error(
                "UserID: %s %s Notepad_Toolbox failed! Reason: %s",
                userid or "-1",
                f,
                str(e),
            )
            return


class DdddOcrServer:
    def __init__(self):
        if ddddocr is not None and hasattr(ddddocr, "DdddOcr"):
            self.oldocr = ddddocr.DdddOcr(old=True, show_ad=False)
            self.ocr = ddddocr.DdddOcr(show_ad=False)
            self.det = ddddocr.DdddOcr(det=True, show_ad=False)
            self.slide = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
            self.extra = {}
            if (
                len(config.extra_onnx_name) == len(config.extra_charsets_name)
                and config.extra_onnx_name[0]
                and config.extra_charsets_name[0]
            ):
                for onnx_name in config.extra_onnx_name:
                    self.extra[onnx_name] = ddddocr.DdddOcr(
                        show_ad=False,
                        import_onnx_path=os.path.join(
                            os.path.abspath(
                                os.path.dirname(
                                    os.path.dirname(os.path.dirname(__file__))
                                )
                            ),
                            "config",
                            f"{onnx_name}.onnx",
                        ),
                        charsets_path=os.path.join(
                            os.path.abspath(
                                os.path.dirname(
                                    os.path.dirname(os.path.dirname(__file__))
                                )
                            ),
                            "config",
                            f"{onnx_name}.json",
                        ),
                    )
                    logger_web_util.info("成功加载自定义Onnx模型: %s.onnx", onnx_name)

    def classification(self, img: bytes, old=False, extra_onnx_name=""):
        if extra_onnx_name:
            return self.extra[extra_onnx_name].classification(img)
        if old:
            return self.oldocr.classification(img)
        else:
            return self.ocr.classification(img)

    def detection(self, img: bytes):
        return self.det.detection(img)

    def slide_match(
        self, imgtarget: bytes, imgbg: bytes, comparison=False, simple_target=False
    ):
        if comparison:
            return self.slide.slide_comparison(imgtarget, imgbg)
        if not simple_target:
            try:
                return self.slide.slide_match(imgtarget, imgbg)
            except Exception as e:
                logger_web_handler.debug(
                    "slide_match error: %s", e, exc_info=config.traceback_print
                )
        return self.slide.slide_match(imgtarget, imgbg, simple_target=True)


if ddddocr:
    DDDDOCR_SERVER: Optional[DdddOcrServer] = DdddOcrServer()
else:
    DDDDOCR_SERVER = None


async def get_img_from_url(imgurl):
    async with aiohttp.ClientSession(conn_timeout=config.connect_timeout) as session:
        async with session.get(
            imgurl, verify_ssl=False, timeout=config.request_timeout
        ) as res:
            content = await res.read()
            base64_data = base64.b64encode(content).decode()
            return base64.b64decode(base64_data)


async def get_img(
    img="",
    imgurl="",
):
    if img:
        # 判断是否为URL
        if img.startswith("http"):
            try:
                return await get_img_from_url(img)
            except Exception as e:
                logger_web_handler.debug(
                    "get_img_from_url error: %s", e, exc_info=config.traceback_print
                )
                return base64.b64decode(img)
        return base64.b64decode(img)
    elif imgurl:
        return await get_img_from_url(imgurl)
    else:
        raise HTTPError(415)


class DdddOcrHandler(BaseHandler):
    async def get(self):
        rtv = {}
        try:
            if DDDDOCR_SERVER:
                img = self.get_argument("img", "")
                imgurl = self.get_argument("imgurl", "")
                old = bool(strtobool(self.get_argument("old", "False")))
                extra_onnx_name = self.get_argument("extra_onnx_name", "")
                img = await get_img(img, imgurl)
                rtv["Result"] = DDDDOCR_SERVER.classification(
                    img, old=old, extra_onnx_name=extra_onnx_name
                )
                rtv["状态"] = "OK"
            else:
                raise HTTPError(406)
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
        return

    async def post(self):
        rtv = {}
        try:
            if DDDDOCR_SERVER:
                if self.request.headers.get("Content-Type", "").startswith(
                    "application/json"
                ):
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
                rtv["Result"] = DDDDOCR_SERVER.classification(
                    img, old=old, extra_onnx_name=extra_onnx_name
                )
                rtv["状态"] = "OK"
            else:
                raise HTTPError(406)
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=4))
        return


class DdddDetHandler(BaseHandler):
    async def get(self):
        rtv = {}
        try:
            if DDDDOCR_SERVER:
                img = self.get_argument("img", "")
                imgurl = self.get_argument("imgurl", "")
                img = await get_img(img, imgurl)
                rtv["Result"] = DDDDOCR_SERVER.detection(img)
                rtv["状态"] = "OK"
            else:
                raise HTTPError(406)
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=None))
        return

    async def post(self):
        rtv = {}
        try:
            if DDDDOCR_SERVER:
                if self.request.headers.get("Content-Type", "").startswith(
                    "application/json"
                ):
                    body_dict = json.loads(self.request.body)
                    img = body_dict.get("img", "")
                    imgurl = body_dict.get("imgurl", "")
                else:
                    img = self.get_argument("img", "")
                    imgurl = self.get_argument("imgurl", "")
                img = await get_img(img, imgurl)
                rtv["Result"] = DDDDOCR_SERVER.detection(img)
                rtv["状态"] = "OK"
            else:
                raise Exception(404)
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=None))
        return


class DdddSlideHandler(BaseHandler):
    async def get(self):
        rtv = {}
        try:
            if DDDDOCR_SERVER:
                imgtarget = self.get_argument("imgtarget", "")
                imgbg = self.get_argument("imgbg", "")
                simple_target = bool(
                    strtobool(self.get_argument("simple_target", "False"))
                )
                comparison = bool(strtobool(self.get_argument("comparison", "False")))
                imgtarget = await get_img(imgtarget, "")
                imgbg = await get_img(imgbg, "")
                rtv["Result"] = DDDDOCR_SERVER.slide_match(
                    imgtarget, imgbg, comparison=comparison, simple_target=simple_target
                )
                rtv["状态"] = "OK"
            else:
                raise HTTPError(406)
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=None))
        return

    async def post(self):
        rtv = {}
        try:
            if DDDDOCR_SERVER:
                if self.request.headers.get("Content-Type", "").startswith(
                    "application/json"
                ):
                    body_dict = json.loads(self.request.body)
                    imgtarget = body_dict.get("imgtarget", "")
                    imgbg = body_dict.get("imgbg", "")
                    simple_target = bool(
                        strtobool(body_dict.get("simple_target", "False"))
                    )
                    comparison = bool(strtobool(body_dict.get("comparison", "False")))
                else:
                    imgtarget = self.get_argument("imgtarget", "")
                    imgbg = self.get_argument("imgbg", "")
                    simple_target = bool(
                        strtobool(self.get_argument("simple_target", "False"))
                    )
                    comparison = bool(
                        strtobool(self.get_argument("comparison", "False"))
                    )

                imgtarget = await get_img(imgtarget, "")
                imgbg = await get_img(imgbg, "")
                rtv["Result"] = DDDDOCR_SERVER.slide_match(
                    imgtarget, imgbg, comparison=comparison, simple_target=simple_target
                )
                rtv["状态"] = "OK"
            else:
                raise HTTPError(406)
        except Exception as e:
            rtv["状态"] = str(e)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(rtv, ensure_ascii=False, indent=None))
        return


handlers = [
    (r"/util/delay", UtilDelayParaHandler),
    (r"/util/delay/(\d+)", UtilDelayIntHandler),
    (r"/util/delay/(\d+\.\d+)", UtilDelayHandler),
    (r"/util/timestamp", TimeStampHandler),
    (r"/util/unicode", UniCodeHandler),
    (r"/util/urldecode", UrlDecodeHandler),
    (r"/util/gb2312", GB2312Handler),
    (r"/util/regex", UtilRegexHandler),
    (r"/util/string/replace", UtilStrReplaceHandler),
    (r"/util/rsa", UtilRSAHandler),
    (r"/util/toolbox/(\d+)", ToolboxHandler),
    (r"/util/toolbox/notepad", ToolboxNotepadHandler),
    (r"/util/toolbox/(\d+)/notepad", ToolboxNotepadHandler),
    (r"/util/toolbox/(\d+)/notepad/(\d+)", ToolboxNotepadHandler),
    (r"/util/toolbox/notepad/list", ToolboxNotepadListHandler),
    (r"/util/toolbox/(\d+)/notepad/list", ToolboxNotepadListHandler),
    (r"/util/toolbox/(\d+)/notepad/list/(\d+)", ToolboxNotepadListHandler),
    (r"/util/dddd/ocr", DdddOcrHandler),
    (r"/util/dddd/det", DdddDetHandler),
    (r"/util/dddd/slide", DdddSlideHandler),
]
