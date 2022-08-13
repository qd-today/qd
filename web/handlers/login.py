#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 20:38:51

import re
import time
import base64
import umsgpack
from tornado import gen
from tornado.ioloop import IOLoop
from Crypto.Hash import MD5
from libs import mcrypto as crypto

import config
from .base import *
from libs import utils

class ForbiddenHandler(BaseHandler):
    async def get(self):
        return await self.render('Forbidden.html')

class LoginHandler(BaseHandler):
    async def get(self):
        if (self.current_user) and (self.db.user.get(self.current_user['id'], fields=('id'))):
            self.redirect('/my/')
            return
        regFlg = False if  self.db.site.get(1, fields=('regEn'))['regEn'] == 0 else True
        
        return await self.render('login.html', regFlg=regFlg)

    async def post(self):
        email = self.get_argument('email')
        password = self.get_argument('password')
        siteconfig = self.db.site.get(1, fields=('MustVerifyEmailEn'))
        regFlg = False if  self.db.site.get(1, fields=('regEn'))['regEn'] == 0 else True
        if not email or not password:
            await self.render('login.html', password_error=u'请输入用户名和密码', email=email, regFlg=regFlg)
            return

        user_try = self.db.user.get(email=email, fields=('id', 'role', 'status'))
        if (user_try):
            if (user_try['status'] != 'Enable') and (user_try['role'] != 'admin'):
                await self.render('login.html', password_error=u'账号已被禁用，请联系管理员', email=email, regFlg=regFlg)
                return
        else:
            await self.render('login.html', password_error=u'不存在此邮箱或密码错误', email=email, regFlg=regFlg)
            return

        if self.db.user.challenge(email, password):
            user = self.db.user.get(email=email, fields=('id', 'email', 'nickname', 'role', 'email_verified'))
            if not user:
                await self.render('login.html', password_error=u'不存在此邮箱或密码错误', email=email, regFlg=regFlg)
                return
            
            if (siteconfig['MustVerifyEmailEn'] != 0) and (user['email_verified'] == 0):
                await self.render('login.html', password_error=u'未验证邮箱，请点击注册重新验证邮箱', email=email, regFlg=regFlg)
                return

            setcookie = dict(
                    expires_days=config.cookie_days,
                    httponly=True,
                    )
            if config.https:
                setcookie['secure'] = True
            self.set_secure_cookie('user', umsgpack.packb(user), **setcookie)
            self.db.user.mod(user['id'], atime=time.time(), aip=self.ip2varbinary)
            
            # 如果用户MD5不一致就更新MD5
            user = self.db.user.get(email=email, fields=('id', 'password', 'password_md5'))
            hash = MD5.new()
            hash.update(password.encode('utf-8'))
            tmp = crypto.password_hash(hash.hexdigest(),self.db.user.decrypt(user['id'], user['password']))
            if (user['password_md5'] != tmp):
                self.db.user.mod(user['id'], password_md5=tmp)

            next = self.get_argument('next', '/my/')
            self.redirect(next)
        else:
            self.evil(+5)
            await self.render('login.html', password_error=u'不存在此邮箱或密码错误', email=email, regFlg=regFlg)

class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect('/')

class RegisterHandler(BaseHandler):
    async def get(self):
        if self.current_user:
            self.redirect('/my/')
            return

        regFlg = False if  self.db.site.get(1, fields=('regEn'))['regEn'] == 0 else True
        return await self.render('register.html', regFlg=regFlg)

    async def post(self):
        siteconfig = self.db.site.get(1, fields=('regEn', 'MustVerifyEmailEn'))
        regEn = siteconfig['regEn']
        regFlg = False if regEn == 0 else True
        MustVerifyEmailEn = siteconfig['MustVerifyEmailEn']
        email = self.get_argument('email')
        password = self.get_argument('password')
        
        if not email:
            await self.render('register.html', email_error=u'请输入邮箱', regFlg=regFlg)
            return
        if email.count('@') != 1 or email.count('.') == 0:
            await self.render('register.html', email_error=u'邮箱格式不正确', regFlg=regFlg)
            return
        if len(password) < 6:
            await self.render('register.html', password_error=u'密码需要大于6位', email=email, regFlg=regFlg)
            return

        user = self.db.user.get(email = email, fields=('id', 'email', 'email_verified', 'nickname', 'role'))
        if (user == None):
            if (regEn == 1):
                self.evil(+5)
                try:
                    self.db.user.add(email=email, password=password, ip=self.ip2varbinary)
                except self.db.user.DeplicateUser as e:
                    self.evil(+3)
                    await self.render('register.html', email_error=u'email地址已注册', regFlg=regFlg)
                    return
                user = self.db.user.get(email=email, fields=('id', 'email', 'nickname', 'role'))
                self.db.notepad.add(dict(userid=user['id'], notepadid=1, content=user['notepad']))
                setcookie = dict(
                        expires_days=config.cookie_days,
                        httponly=True,
                        )
                if config.https:
                    setcookie['secure'] = True
                self.set_secure_cookie('user', umsgpack.packb(user), **setcookie)
                usertmp = self.db.user.list()
                if len(usertmp) == 1 and config.user0isadmin:
                    if (usertmp[0]['email'] == email):
                        self.db.user.mod(usertmp[0]['id'], role='admin')

                if siteconfig['MustVerifyEmailEn'] != 1:
                    next = self.get_argument('next', '/my/')
                    self.redirect(next)
                else:
                    await self.render('register.html', email_error=u'请验证邮箱后再登陆', regFlg=regFlg)
                await gen.convert_yielded(self.send_mail(user))
                
            else:
                await self.render('register.html', email_error=u'管理员关闭注册', regFlg=regFlg)
            return
        else:
            if (MustVerifyEmailEn == 1):
                if (user['email_verified'] != 1):
                    await self.render('register.html', email_error=u'email地址未验证，邮件已发送，请验证邮件后登陆')
                    await gen.convert_yielded(self.send_mail(user))
                else:
                    await self.render('register.html', email_error=u'email地址已注册', regFlg=regFlg)
            else:
                await self.render('register.html', email_error=u'email地址已注册', regFlg=regFlg)
        return

    async def send_mail(self, user):
        verified_code = [user['email'], time.time()]
        verified_code = self.db.user.encrypt(user['id'], verified_code)
        verified_code = self.db.user.encrypt(0, [user['id'], verified_code])
        verified_code = base64.b64encode(verified_code).decode()
        await gen.convert_yielded(utils.send_mail(to=user['email'], subject=u"欢迎注册 签到平台", html=u"""
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

class VerifyHandler(BaseHandler):
    async def get(self, code):
        userid=None
        try:
            verified_code = base64.b64decode(code)
            userid, verified_code = self.db.user.decrypt(0, verified_code)
            user = self.db.user.get(userid, fields=('id', 'email', 'email_verified'))
            assert user
            assert not user['email_verified']
            email, time_time = self.db.user.decrypt(userid, verified_code)
            assert time.time() - time_time < 30 * 24 * 60 * 60
            assert user['email'] == email

            self.db.user.mod(userid,
                    email_verified=True,
                    mtime=time.time()
                    )
            await self.finish('验证成功')
        except Exception as e:
            self.evil(+5)
            logger_Web_Handler.error('UserID: %s verify email failed! Reason: %s', userid or '-1', e)
            self.set_status(400)
            await self.finish('验证失败')


class PasswordResetHandler(BaseHandler):
    async def get(self, code):
        if not code:
            return await self.render('password_reset_email.html')

        try:
            verified_code = base64.b64decode(code)
            userid, verified_code = self.db.user.decrypt(0, verified_code)
            user = self.db.user.get(userid, fields=('id', 'email', 'mtime'))
            assert user
            mtime, time_time = self.db.user.decrypt(userid, verified_code)
            assert mtime == user['mtime']
            assert time.time() - time_time < 60 * 60
        except Exception as e:
            self.evil(+10)
            logger_Web_Handler.error('%r',e)
            self.set_status(400)
            await self.finish('Bad Request')
            return

        return await self.render('password_reset.html')

    async def post(self, code):
        if not code:
            self.evil(+5)

            email = self.get_argument('email')
            if not email:
                return await self.render('password_reset_email.html',
                                   email_error=u'请输入邮箱')
            if email.count('@') != 1 or email.count('.') == 0:
                return await self.render('password_reset_email.html',
                                   email_error=u'邮箱格式不正确')

            user = self.db.user.get(email=email, fields=('id', 'email', 'mtime', 'nickname', 'role'))
            if user:
                logger_Web_Handler.info('password reset: userid=%(id)s email=%(email)s', user)
                await gen.convert_yielded(self.send_mail(user))


            return await self.finish("如果用户存在，会将发送密码重置邮件到您的邮箱，请注意查收。（如果您没有收到过激活邮件，可能无法也无法收到密码重置邮件）")
        else:
            password = self.get_argument('password')
            if len(password) < 6:
                return await self.render('password_reset.html', password_error=u'密码需要大于6位')

            try:
                verified_code = base64.b64decode(code)
                userid, verified_code = self.db.user.decrypt(0, verified_code)
                user = self.db.user.get(userid, fields=('id', 'email', 'mtime', 'email_verified'))
                assert user
                mtime, time_time = self.db.user.decrypt(userid, verified_code)
                assert mtime == user['mtime']
                assert time.time() - time_time < 60 * 60
            except Exception as e:
                self.evil(+10)
                logger_Web_Handler.error('%r',e)
                self.set_status(400)
                await self.finish('Bad Request')
                return

            self.db.user.mod(userid,
                             password=password,
                             mtime=time.time(),
                             )
            return self.finish("""密码重置成功! 请<a href="{http}://{domain}/login" >点击此处</a>返回登录页面。""".format(http='https' if config.https else 'http', domain=config.domain))

    async def send_mail(self, user):
        verified_code = [user['mtime'], time.time()]
        verified_code = self.db.user.encrypt(user['id'], verified_code)
        verified_code = self.db.user.encrypt(0, [user['id'], verified_code])
        verified_code = base64.b64encode(verified_code).decode()

        await gen.convert_yielded(utils.send_mail(to=user['email'], subject=u"签到平台(%s) 密码重置" % (config.domain), html=u"""

        <table style="width:99.8%%;height:99.8%%"><tbody><tr><td style=" background:#fafafa url(#) "><div style="border-radius:10px;font-size:13px;color:#555;width:666px;font-family:'Century Gothic','Trebuchet MS','Hiragino Sans GB','微软雅黑','Microsoft Yahei',Tahoma,Helvetica,Arial,SimSun,sans-serif;margin:50px auto;border:1px solid #eee;max-width:100%%;background:#fff repeating-linear-gradient(-45deg,#fff,#fff 1.125rem,transparent 1.125rem,transparent 2.25rem);box-shadow:0 1px 5px rgba(0,0,0,.15)"><div style="width:100%%;background:#49BDAD;color:#fff;border-radius:10px 10px 0 0;background-image:-moz-linear-gradient(0deg,#43c6b8,#ffd1f4);background-image:-webkit-linear-gradient(0deg,#4831ff,#0497ff);height:66px"><p style="font-size:15px;word-break:break-all;padding:23px 32px;margin:0;background-color:hsla(0,0%%,100%%,.4);border-radius:10px 10px 0 0">&nbsp;[签到平台]&nbsp;&nbsp;{http}://{domain}</p></div>
                <div style="margin:40px auto;width:90%%">
                    <p>点击以下链接完成您的密码重置（一小时内有效）。</p>
                    <p style="background:#fafafa repeating-linear-gradient(-45deg,#fff,#fff 1.125rem,transparent 1.125rem,transparent 2.25rem);box-shadow:0 2px 5px rgba(0,0,0,.15);margin:20px 0;padding:15px;border-radius:5px;font-size:14px;color:#555"><a href="{http}://{domain}/password_reset/{code}">{http}://{domain}/password_reset/{code}</a></p>
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
        ('/login', LoginHandler),
        ('/logout', LogoutHandler),
        ('/register', RegisterHandler),
        ('/verify/(.*)', VerifyHandler),
        ('/password_reset/?(.*)', PasswordResetHandler),
        ('/forbidden', ForbiddenHandler),
        ]
