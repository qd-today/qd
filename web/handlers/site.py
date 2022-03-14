#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 11:39:25

import json
import time
import datetime
from tornado import gen
import re
import traceback
from .base import *

from sqlite3_db.basedb import BaseDB
import base64
    
class SiteManagerHandler(BaseHandler):
    @tornado.web.authenticated
    async def get(self, userid):
        adminflg = False
        site = {'regEn': False}
        user = self.db.user.get(userid, fields=('role'))
        if user and user['role'] == "admin":
            adminflg = True
            site = self.db.site.get(1, fields=('regEn', 'MustVerifyEmailEn', 'logDay'))
            site['regEn'] = False if site['regEn'] == 1 else True
            site['MustVerifyEmailEn'] = False if site['MustVerifyEmailEn'] == 0 else True

        await self.render("site_manage.html", userid=userid, adminflg=adminflg, site=site, logDay=site['logDay'])
        return

    @tornado.web.authenticated
    async def post(self, userid):
        try:
            user = self.db.user.get(userid, fields=('id','email', 'role', 'email_verified'))
            if user and user['role'] == "admin":
                envs = {}
                for key in self.request.body_arguments:
                    envs[key] = self.get_body_arguments(key)
                mail = envs['adminmail'][0]
                pwd = envs['adminpwd'][0]
                if self.db.user.challenge_MD5(mail, pwd) and (user['email'] == mail):
                    if ("site.regEn" in envs):
                        self.db.site.mod(1, regEn=0)
                        if (self.db.site.get(1, fields=('regEn'))['regEn'] != 0):
                            raise Exception(u"关闭注册失败")
                    else:
                        self.db.site.mod(1, regEn=1)
                        if (self.db.site.get(1, fields=('regEn'))['regEn'] != 1):
                            raise Exception(u"开启注册失败")
                    
                    if ("site.MustVerifyEmailEn" in envs):
                        if (user['email_verified'] != 0):
                            self.db.site.mod(1, MustVerifyEmailEn=1)
                            if (self.db.site.get(1, fields=('MustVerifyEmailEn'))['MustVerifyEmailEn'] != 1):
                                raise Exception(u"开启 强制邮箱验证 失败")
                        else:
                            await gen.convert_yielded(self.send_verify_mail(user))
                            raise Exception(u"必须验证 管理员邮箱 才能开启, 已尝试发送验证邮件, 请查收。")
                    else:
                        self.db.site.mod(1, MustVerifyEmailEn=0)
                        if (self.db.site.get(1, fields=('MustVerifyEmailEn'))['MustVerifyEmailEn'] != 0):
                            raise Exception(u"关闭 强制邮箱验证 失败")
                        
                    if ("site.logDay" in envs):
                        tmp = int(envs["site.logDay"][0])
                        if (tmp != self.db.site.get(1, fields=('logDay'))['logDay']):
                            self.db.site.mod(1, logDay=tmp)
                            if (self.db.site.get(1, fields=('logDay'))['logDay'] != tmp):
                                raise Exception(u"设置日志保留天数失败")
                else:
                    raise Exception(u"账号/密码错误")
            else:
                raise Exception(u"非管理员，不可操作")
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            if (str(e).find('get user need id or email') > -1):
                e = u'请输入用户名/密码'
            await self.render('tpl_run_failed.html', log=str(e))
            logger_Web_Handler.error('UserID: %s modify Manage_Board failed! Reason: %s', userid, str(e).replace('\\r\\n','\r\n'))
            return
            
        self.redirect('/my/')
        return

    async def send_verify_mail(self, user):
        verified_code = [user['email'], time.time()]
        verified_code = self.db.user.encrypt(user['id'], verified_code)
        verified_code = self.db.user.encrypt(0, [user['id'], verified_code])
        verified_code = base64.b64encode(verified_code).decode()
        await gen.convert_yielded(utils.send_mail(to=user['email'], subject=u"签到平台 验证邮箱", html=u"""
                <table style="width:99.8%%;height:99.8%%"><tbody><tr><td style=" background:#fafafa url(#) "><div style="border-radius:10px;font-size:13px;color:#555;width:666px;font-family:'Century Gothic','Trebuchet MS','Hiragino Sans GB','微软雅黑','Microsoft Yahei',Tahoma,Helvetica,Arial,SimSun,sans-serif;margin:50px auto;border:1px solid #eee;max-width:100%%;background:#fff repeating-linear-gradient(-45deg,#fff,#fff 1.125rem,transparent 1.125rem,transparent 2.25rem);box-shadow:0 1px 5px rgba(0,0,0,.15)"><div style="width:100%%;background:#49BDAD;color:#fff;border-radius:10px 10px 0 0;background-image:-moz-linear-gradient(0deg,#43c6b8,#ffd1f4);background-image:-webkit-linear-gradient(0deg,#4831ff,#0497ff);height:66px"><p style="font-size:15px;word-break:break-all;padding:23px 32px;margin:0;background-color:hsla(0,0%%,100%%,.4);border-radius:10px 10px 0 0">&nbsp;[签到平台]&nbsp;&nbsp;{http}://{domain}</p></div>
                <div style="margin:40px auto;width:90%%">
                    <p>点击以下链接验证邮箱，当您的签到失败的时候，会自动给您发送通知邮件。</p>
                    <p style="background:#fafafa repeating-linear-gradient(-45deg,#fff,#fff 1.125rem,transparent 1.125rem,transparent 2.25rem);box-shadow:0 2px 5px rgba(0,0,0,.15);margin:20px 0;padding:15px;border-radius:5px;font-size:14px;color:#555"><a href="{http}://{domain}/verify/{code}">{http}://{domain}/verify/{code}</a></p>
                    <p>请注意：此邮件由 <a href="{http}://{domain}/verify/{code}" style="color:#12addb" target="_blank">签到平台</a> 自动发送，请勿直接回复。</p>
                    <p>若此邮件不是您请求的，请忽略并删除！</p>
                </div>
            </div>
        </td>
        </tr>
        </tbody>
        </table>
        """.format(http='https' if config.https else 'http', domain=config.domain, code=verified_code), shark=True))

        return
     
handlers = [
        ('/site/(\d+)/manage', SiteManagerHandler),
        ]
