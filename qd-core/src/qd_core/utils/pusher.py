#!/usr/bin/env python
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# pylint: disable=broad-exception-raised

import json
import os
from typing import Optional

import aiohttp

from qd_core.config import get_settings
from qd_core.filters.parse_url import domain_match, url_match_with_limit
from qd_core.utils.decorator import log_and_raise_error
from qd_core.utils.i18n import gettext
from qd_core.utils.log import Log
from qd_core.utils.mail import send_mail

logger_pusher = Log("QD.Core.Utils").getlogger()


def error_message_format(provider: str) -> str:
    return gettext("Push Message to {provider} error: %s").format(provider=provider)


class Pusher:
    async def judge_res(self, res: aiohttp.ClientResponse):
        if res.status == 200:
            return gettext("Push Message Success")

        text = await res.text()
        if text:
            _json = {}
            try:
                _json = await res.json()
            except Exception as e:
                logger_pusher.debug(e, exc_info=get_settings().log.traceback_print)
            if _json:
                raise Exception(_json)
            raise Exception(text)
        if res.reason:
            raise Exception(gettext("Reason: {res_reason}").format(res_reason=res.reason))
        raise Exception(gettext("status code: {res_status}").format(res_status=res.status))

    @log_and_raise_error(logger_pusher, error_message_format("Bark"))
    async def send2bark(self, barklink, title, content):
        link = barklink
        if link[-1] != "/":
            link = link + "/"
        content = content.replace("\\r\\n", "\n")
        d = {"title": title, "body": content}
        async with aiohttp.ClientSession(conn_timeout=get_settings().client_request.connect_timeout) as session:
            async with session.post(
                link, json=d, verify_ssl=False, timeout=get_settings().client_request.request_timeout
            ) as res:
                return await self.judge_res(res)

    @log_and_raise_error(logger_pusher, error_message_format("ServerChan"))
    async def send2s(self, skey: str, title: str, content: str):
        if skey:
            link = f"https://sctapi.ftqq.com/{skey.replace('.send', '')}.send"
            content = content.replace("\\r\\n", "\n\n")
            d = {"text": title, "desp": content}
            async with aiohttp.ClientSession(conn_timeout=get_settings().client_request.connect_timeout) as session:
                async with session.post(
                    link, json=d, verify_ssl=False, timeout=get_settings().client_request.request_timeout
                ) as res:
                    return await self.judge_res(res)
        raise Exception(gettext("skey is empty"))

    @log_and_raise_error(logger_pusher, error_message_format("Telegram"))
    async def send2tg(self, tg_token, title, content):
        tmp = tg_token.split(";")
        tg_token = ""
        tg_user_id = ""
        if len(tmp) >= 2:
            tg_token = tmp[0]
            tg_user_id = tmp[1]
            tg_host = tmp[2] if len(tmp) >= 3 else ""
            proxy = tmp[3] if len(tmp) >= 4 else ""
            pic = tmp[4] if len(tmp) >= 5 else ""
        if tg_token and tg_user_id:
            token = tg_token
            chat_id = tg_user_id
            # TG_BOT的token
            # token = os.environ.get('TG_TOKEN')
            # 用户的ID
            # chat_id = os.environ.get('TG_USERID')
            if not tg_host:
                link = f"https://api.telegram.org/bot{token}/sendMessage"
            else:
                if tg_host[-1] != "/":
                    tg_host = tg_host + "/"
                if "http://" in tg_host or "https://" in tg_host:
                    link = f"{tg_host}bot{token}/sendMessage"
                else:
                    link = f"https://{tg_host}bot{token}/sendMessage"
            picurl = get_settings().push.push_pic_url if pic == "" else pic

            # 匹配标题"QD[定时]任务 {0}-{1} 成功|失败" 的 {0} 部分, 获取 hashtag
            title_sp = title.split(" ")
            if len(title_sp) >= 3:
                title1 = title_sp[1].split("-")
                if len(title1) == 2:
                    title1[0] = "#" + title1[0] + " "
                title_sp[1] = "-".join(title1)
            title = " ".join(title_sp)

            content = content.replace("\\r\\n", "\n")
            d = {
                "chat_id": str(chat_id),
                "text": "<b>"
                + title
                + "</b>"
                + "\n"
                + content
                + "\n"
                + '------<a href="'
                + picurl
                + gettext('">QD提醒</a>------'),
                "disable_web_page_preview": "true",
                "parse_mode": "HTML",
            }

            async with aiohttp.ClientSession(conn_timeout=get_settings().client_request.connect_timeout) as session:
                async with session.post(
                    link,
                    json=d,
                    verify_ssl=False,
                    proxy=proxy if proxy else None,
                    timeout=get_settings().client_request.request_timeout,
                ) as res:
                    return await self.judge_res(res)
        raise Exception(gettext("TG_TOKEN or TG_USERID is empty"))

    @log_and_raise_error(logger_pusher, error_message_format("DingDing"))
    async def send2dingding(self, dingding_token, title, content):
        tmp = dingding_token.split(";")
        if len(tmp) >= 1:
            dingding_token = tmp[0]
            pic = tmp[1] if len(tmp) >= 2 else ""
        if dingding_token != "":
            link = f"https://oapi.dingtalk.com/robot/send?access_token={dingding_token}"
            picurl = get_settings().push.push_pic_url if pic == "" else pic
            content = content.replace("\\r\\n", "\n\n > ")
            d = {
                "msgtype": "markdown",
                "markdown": {"title": title, "text": "![QD](" + picurl + ")\n " + "#### " + title + "\n > " + content},
            }
            async with aiohttp.ClientSession(conn_timeout=get_settings().client_request.connect_timeout) as session:
                async with session.post(
                    link, json=d, verify_ssl=False, timeout=get_settings().client_request.request_timeout
                ) as res:
                    r = await self.judge_res(res)
                    _json = await res.json()
                    if _json.get("errcode", "") != 0:
                        raise Exception(_json)
                    return r
        raise Exception(gettext("DINGDING_TOKEN  is empty"))

    @log_and_raise_error(logger_pusher, error_message_format("WxPusher"))
    async def send2wxpusher(self, wxpusher, content):
        temp = wxpusher.split(";")
        wxpusher_token = temp[0] if (len(temp) >= 2) else ""
        wxpusher_uid = temp[1] if (len(temp) >= 2) else ""
        if (wxpusher_token != "") and (wxpusher_uid != ""):
            link = "http://wxpusher.zjiecode.com/api/send/message"
            content = content.replace("\\r\\n", "\n")
            d = {"appToken": wxpusher_token, "content": content, "contentType": 3, "uids": [wxpusher_uid]}
            async with aiohttp.ClientSession(conn_timeout=get_settings().client_request.connect_timeout) as session:
                async with session.post(
                    link, json=d, verify_ssl=False, timeout=get_settings().client_request.request_timeout
                ) as res:
                    r = await self.judge_res(res)
                    _json = await res.json()
                    if not _json.get("success", True):
                        raise Exception(_json)
                    return r
        raise Exception(gettext("wxpusher_token or wxpusher_uid is empty"))

    @log_and_raise_error(logger_pusher, error_message_format("DIY"))
    async def cus_pusher_send(self, diypusher, t, log):
        log = log.replace('"', '\\"').replace('\\\\"', '\\"')
        curltmp = diypusher["curl"].format(log=log, t=t)

        if diypusher["headers"]:
            headerstmp = json.loads(diypusher["headers"].replace("{log}", log).replace("{t}", t))
        else:
            headerstmp = {}

        if diypusher["mode"] == "POST":
            post_data_tmp = diypusher["postData"].replace("{log}", log).replace("{t}", t)
            if headerstmp:
                headerstmp.pop("content-type", "")
                headerstmp.pop("Content-Type", "")
            if diypusher["postMethod"] == "x-www-form-urlencoded":
                headerstmp["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
                if post_data_tmp != "":
                    try:
                        post_data_tmp = json.loads(post_data_tmp)
                    except Exception as e:
                        logger_pusher.debug(e, exc_info=get_settings().log.traceback_print)
                        if isinstance(post_data_tmp, str):
                            post_data_tmp = post_data_tmp.encode("utf-8")
                async with aiohttp.ClientSession(
                    headers=headerstmp, conn_timeout=get_settings().client_request.connect_timeout
                ) as session:
                    async with session.post(
                        curltmp,
                        data=post_data_tmp,
                        verify_ssl=False,
                        timeout=get_settings().client_request.request_timeout,
                    ) as res:
                        return await self.judge_res(res)
            headerstmp["Content-Type"] = "application/json; charset=UTF-8"
            if post_data_tmp != "":
                post_data_tmp = json.loads(post_data_tmp)
            async with aiohttp.ClientSession(
                headers=headerstmp, conn_timeout=get_settings().client_request.connect_timeout
            ) as session:
                async with session.post(
                    curltmp, json=post_data_tmp, verify_ssl=False, timeout=get_settings().client_request.request_timeout
                ) as res:
                    return await self.judge_res(res)
        if diypusher["mode"] == "GET":
            async with aiohttp.ClientSession(
                headers=headerstmp, conn_timeout=get_settings().client_request.connect_timeout
            ) as session:
                async with session.get(
                    curltmp, verify_ssl=False, timeout=get_settings().client_request.request_timeout
                ) as res:
                    return await self.judge_res(res)
        raise Exception(gettext("模式未选择"))

    # 获取Access_Token
    async def get_access_token(self, qywx: dict):
        access_url = f"{qywx['代理']}cgi-bin/gettoken?corpid={qywx['企业ID']}&corpsecret={qywx['应用密钥']}"
        async with aiohttp.ClientSession(conn_timeout=get_settings().client_request.connect_timeout) as session:
            async with session.get(
                access_url, verify_ssl=False, timeout=get_settings().client_request.request_timeout
            ) as res:
                get_access_token_res = await res.json()
        return get_access_token_res

    # 上传临时素材,返回素材id
    async def get_short_time_media(self, pic_url, access_token, qywx_proxy):
        async with aiohttp.ClientSession(conn_timeout=get_settings().client_request.connect_timeout) as session:
            if pic_url == get_settings().push.push_pic_url:
                with open(
                    os.path.join(
                        os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "web",
                        "static",
                        "img",
                        "push_pic.png",
                    ),
                    "rb",
                ) as f:
                    img = f.read()
            else:
                async with session.get(
                    pic_url, verify_ssl=False, timeout=get_settings().client_request.request_timeout
                ) as res:
                    img = await res.read()
            url = f"{qywx_proxy}cgi-bin/media/upload?access_token={access_token}&type=image"
            async with session.post(
                url, data={"image": img}, verify_ssl=False, timeout=get_settings().client_request.request_timeout
            ) as res:
                await self.judge_res(res)
                _json = await res.json()
                if _json.get("errcode", 0) > 0:
                    raise Exception(_json.get("errmsg", ""))
                return _json["media_id"]

    @log_and_raise_error(logger_pusher, error_message_format("QYWX"))
    async def qywx_pusher_send(self, qywx_token, title: str, log: str, domain: str):
        qywx = {}
        tmp = qywx_token.split(";")
        if len(tmp) >= 3:
            qywx["企业ID"] = tmp[0]
            qywx["应用ID"] = tmp[1]
            qywx["应用密钥"] = tmp[2]
            qywx["图片"] = tmp[3] if len(tmp) >= 4 else ""
            qywx["代理"] = tmp[4] if len(tmp) >= 5 else "https://qyapi.weixin.qq.com/"
        else:
            raise Exception(gettext("企业微信Pusher获取AccessToken失败或参数不完整!"))

        if qywx["代理"][-1] != "/":
            qywx["代理"] = qywx["代理"] + "/"
        if qywx["代理"][:4] != "http":
            if qywx["代理"] == "qyapi.weixin.qq.com/":
                qywx["代理"] = f"https://{qywx['代理']}"
            else:
                qywx["代理"] = f"http://{qywx['代理']}"
        get_access_token_res = await self.get_access_token(qywx)
        pic_url = get_settings().push.push_pic_url if qywx["图片"] == "" else qywx["图片"]
        if get_access_token_res.get("access_token", "") != "" and get_access_token_res["errmsg"] == "ok":
            access_token = get_access_token_res["access_token"]
            if url_match_with_limit(pic_url) or domain_match(pic_url.split("/")[0]):
                media_id = await self.get_short_time_media(pic_url, access_token, qywx["代理"])
            else:
                media_id = pic_url
            msg_url = f"{qywx['代理']}cgi-bin/message/send?access_token={access_token}"
            post_data = {
                "touser": "@all",
                "toparty": "@all",
                "totag": "@all",
                "msgtype": "mpnews",
                "agentid": qywx["应用ID"],
                "mpnews": {
                    "articles": [
                        {
                            "title": title,
                            "digest": log.replace("\\r\\n", "\n"),
                            "content": log.replace("\\r\\n", "<br>"),
                            "author": gettext("QD框架"),
                            "content_source_url": domain,
                            "thumb_media_id": media_id,
                        }
                    ]
                },
                "safe": 0,
                "enable_id_trans": 0,
                "enable_duplicate_check": 0,
                "duplicate_check_interval": 1800,
            }
            async with aiohttp.ClientSession(conn_timeout=get_settings().client_request.connect_timeout) as session:
                async with session.post(
                    msg_url, json=post_data, verify_ssl=False, timeout=get_settings().client_request.request_timeout
                ) as res:
                    r = await self.judge_res(res)
                    _json = await res.json()
                    if _json.get("errmsg", "") != "ok" and _json.get("errcode", 0) != 0:
                        raise Exception(_json["errmsg"])
                    return r
        raise Exception(gettext("企业微信Pusher获取AccessToken失败或参数不完整!"))

    @log_and_raise_error(logger_pusher, error_message_format("QYWX_WebHook"))
    async def qywx_webhook_send(self, qywx_webhook, title: str, log: str):
        qywx = {}
        tmp = qywx_webhook.split(";")
        if len(tmp) >= 1:
            qywx["Webhook"] = tmp[0]
        else:
            raise Exception(gettext("企业微信WebHook获取AccessToken失败或参数不完整!"))

        log = log.replace("\\r\\n", "\n")

        msg_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={qywx['Webhook']}"
        post_data = {"msgtype": "text", "text": {"content": f"{title}\n{log}"}}
        async with aiohttp.ClientSession(conn_timeout=get_settings().client_request.connect_timeout) as session:
            async with session.post(
                msg_url, json=post_data, verify_ssl=False, timeout=get_settings().client_request.request_timeout
            ) as res:
                r = await self.judge_res(res)
                _json = await res.json()
                if _json.get("errmsg", "") != "ok" and _json.get("errcode", 0) != 0:
                    raise Exception(_json["errmsg"])
                return r

    @log_and_raise_error(logger_pusher, error_message_format("Mail"))
    async def mail_send(self, email, title, content: str, domain: Optional[str] = None, check_domain=True):
        if check_domain and not domain:
            r = gettext("请配置框架域名 domain, 以启用邮箱推送功能!")
            logger_pusher.error("Send mail error: %s", r)
            return Exception(r)

        content = content.replace("\\r\\n", "\n")
        if domain:
            title = f"{title} - {domain}"
        await send_mail(to=email, subject=title, text=content, shark=True)
        return gettext("Send Mail Success")
