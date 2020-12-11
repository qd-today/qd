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

from base import *

from sqlite3_db.basedb import BaseDB
    
class SiteManagerHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, userid):
        adminflg = False
        site = {'regEn': False}
        user = self.db.user.get(userid, fields=('role'))
        if user and user['role'] == "admin":
            adminflg = True
            site = self.db.site.get(1, fields=('regEn', 'MustVerifyEmailEn', 'logDay'))
            site['regEn'] = False if site['regEn'] == 1 else True
            site['MustVerifyEmailEn'] = False if site['MustVerifyEmailEn'] == 0 else True

        self.render("site_manage.html", userid=userid, adminflg=adminflg, site=site, logDay=site['logDay'])
        return

    @tornado.web.authenticated
    def post(self, userid):
        try:
            user = self.db.user.get(userid, fields=('role'))
            if user and user['role'] == "admin":
                envs = self.request.body_arguments
                mail = envs['adminmail'][0]
                pwd = u"{0}".format(envs['adminpwd'][0])
                if self.db.user.challenge(mail, pwd):
                    if ("site.regEn" in envs):
                        self.db.site.mod(1, regEn=0)
                        if (self.db.site.get(1, fields=('regEn'))['regEn'] != 0):
                            raise Exception(u"关闭注册失败")
                    else:
                        self.db.site.mod(1, regEn=1)
                        if (self.db.site.get(1, fields=('regEn'))['regEn'] != 1):
                            raise Exception(u"开启注册失败")
                    
                    if ("site.MustVerifyEmailEn" in envs):
                        self.db.site.mod(1, MustVerifyEmailEn=1)
                        if (self.db.site.get(1, fields=('MustVerifyEmailEn'))['MustVerifyEmailEn'] != 1):
                            raise Exception(u"开启 强制邮箱验证 失败")
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
            if (str(e).find('get user need id or email') > -1):
                e = u'请输入用户名/密码'
            self.render('tpl_run_failed.html', log=e)
            return
            
        self.redirect('/my/')
        return
     
handlers = [
        ('/site/(\d+)/manage', SiteManagerHandler),
        ]
