#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 11:39:25
# pylint: disable=broad-exception-raised

import base64
import time
import traceback

from tornado import gen
from tornado.web import authenticated

import config
from libs import utils
from web.handlers.base import BaseHandler, logger_web_handler


class SiteManagerHandler(BaseHandler):
    @authenticated
    async def get(self, userid):
        flg = self.get_argument("flg", '')
        title = self.get_argument("title", '')
        log = self.get_argument("log", '')
        adminflg = False
        site = {'regEn': False}
        user = await self.db.user.get(userid, fields=('role',))
        if user and user['role'] == "admin":
            adminflg = True
            site = await self.db.site.get(1, fields=('regEn', 'MustVerifyEmailEn', 'logDay'))
            site['regEn'] = False if site['regEn'] == 1 else True
            site['MustVerifyEmailEn'] = False if site['MustVerifyEmailEn'] == 0 else True

        await self.render("site_manage.html", userid=userid, adminflg=adminflg, site=site, logDay=site['logDay'], flg=flg, title=title, log=log)
        return

    @authenticated
    async def post(self, userid):
        try:
            async with self.db.transaction() as sql_session:
                user = await self.db.user.get(userid, fields=('id', 'email', 'role', 'email_verified'), sql_session=sql_session)
                if user and user['role'] == "admin":
                    envs = {}
                    for key in self.request.body_arguments:
                        envs[key] = self.get_body_arguments(key)
                    mail = envs['adminmail'][0]
                    pwd = envs['adminpwd'][0]
                    if await self.db.user.challenge_md5(mail, pwd, sql_session=sql_session) and (user['email'] == mail):
                        if "site.regEn" in envs:
                            await self.db.site.mod(1, regEn=0, sql_session=sql_session)
                            if (await self.db.site.get(1, fields=('regEn',), sql_session=sql_session))['regEn'] != 0:
                                raise Exception("关闭注册失败")
                        else:
                            await self.db.site.mod(1, regEn=1, sql_session=sql_session)
                            if (await self.db.site.get(1, fields=('regEn',), sql_session=sql_session))['regEn'] != 1:
                                raise Exception("开启注册失败")

                        if "site.MustVerifyEmailEn" in envs:
                            if not config.domain:
                                raise Exception('请先配置 QD 框架域名 domain, 以启用邮箱验证功能!')
                            if user['email_verified'] != 0:
                                await self.db.site.mod(1, MustVerifyEmailEn=1, sql_session=sql_session)
                                if (await self.db.site.get(1, fields=('MustVerifyEmailEn',), sql_session=sql_session))['MustVerifyEmailEn'] != 1:
                                    raise Exception("开启 强制邮箱验证 失败")
                            else:
                                await self.send_verify_mail(user, sql_session=sql_session)
                                raise Exception("必须验证 管理员邮箱 才能开启, 已尝试发送验证邮件, 请查收。")
                        else:
                            await self.db.site.mod(1, MustVerifyEmailEn=0, sql_session=sql_session)
                            if (await self.db.site.get(1, fields=('MustVerifyEmailEn',), sql_session=sql_session))['MustVerifyEmailEn'] != 0:
                                raise Exception("关闭 强制邮箱验证 失败")

                        if "site.logDay" in envs:
                            tmp = int(envs["site.logDay"][0])
                            if tmp != (await self.db.site.get(1, fields=('logDay',), sql_session=sql_session))['logDay']:
                                await self.db.site.mod(1, logDay=tmp, sql_session=sql_session)
                                if (await self.db.site.get(1, fields=('logDay',), sql_session=sql_session))['logDay'] != tmp:
                                    raise Exception("设置日志保留天数失败")
                    else:
                        raise Exception("账号/密码错误")
                else:
                    raise Exception("非管理员，不可操作")
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if str(e).find('get user need id or email') > -1:
                e = '请输入用户名/密码'
            await self.render('utils_run_result.html', log=str(e), title='设置失败', flg='danger')
            logger_web_handler.error('UserID: %s modify Manage_Board failed! Reason: %s', userid, str(e).replace('\\r\\n', '\r\n'))
            return
        await self.render('utils_run_result.html', title='设置成功', flg='success')
        return

    async def send_verify_mail(self, user, sql_session=None):
        verified_code = [user['email'], time.time()]
        verified_code = await self.db.user.encrypt(user['id'], verified_code, sql_session=sql_session)
        verified_code = await self.db.user.encrypt(0, [user['id'], verified_code], sql_session=sql_session)
        verified_code = base64.b64encode(verified_code).decode()
        await gen.convert_yielded(utils.send_mail(to=user['email'], subject="QD平台 验证邮箱", html="""
                <table style="width:99.8%%;height:99.8%%"><tbody><tr><td style=" background:#fafafa url(#) "><div style="border-radius:10px;font-size:13px;color:#555;width:666px;font-family:'Century Gothic','Trebuchet MS','Hiragino Sans GB','微软雅黑','Microsoft Yahei',Tahoma,Helvetica,Arial,SimSun,sans-serif;margin:50px auto;border:1px solid #eee;max-width:100%%;background:#fff repeating-linear-gradient(-45deg,#fff,#fff 1.125rem,transparent 1.125rem,transparent 2.25rem);box-shadow:0 1px 5px rgba(0,0,0,.15)"><div style="width:100%%;background:#49BDAD;color:#fff;border-radius:10px 10px 0 0;background-image:-moz-linear-gradient(0deg,#43c6b8,#ffd1f4);background-image:-webkit-linear-gradient(0deg,#4831ff,#0497ff);height:66px"><p style="font-size:15px;word-break:break-all;padding:23px 32px;margin:0;background-color:hsla(0,0%%,100%%,.4);border-radius:10px 10px 0 0">&nbsp;[QD平台]&nbsp;&nbsp;{http}://{domain}</p></div>
                <div style="margin:40px auto;width:90%%">
                    <p>点击以下链接验证邮箱，当您的QD失败的时候，会自动给您发送通知邮件。</p>
                    <p style="background:#fafafa repeating-linear-gradient(-45deg,#fff,#fff 1.125rem,transparent 1.125rem,transparent 2.25rem);box-shadow:0 2px 5px rgba(0,0,0,.15);margin:20px 0;padding:15px;border-radius:5px;font-size:14px;color:#555"><a href="{http}://{domain}/verify/{code}">{http}://{domain}/verify/{code}</a></p>
                    <p>请注意：此邮件由 <a href="{http}://{domain}/verify/{code}" style="color:#12addb" target="_blank">QD平台</a> 自动发送，请勿直接回复。</p>
                    <p>若此邮件不是您请求的，请忽略并删除！</p>
                </div>
            </div>
        </td>
        </tr>
        </tbody>
        </table>
        """.format(http='https' if config.mail_domain_https else 'http', domain=config.domain, code=verified_code), shark=True))

        return


handlers = [
    (r'/site/(\d+)/manage', SiteManagerHandler),
]
