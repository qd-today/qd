#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 20:38:51

import base64
import time

import umsgpack
from Crypto.Hash import MD5
from tornado import gen

import config
from libs import mcrypto as crypto
from libs import utils
from web.handlers.base import BaseHandler, logger_web_handler


class ForbiddenHandler(BaseHandler):
    async def get(self):
        return await self.render('Forbidden.html')


class LoginHandler(BaseHandler):
    async def get(self):
        if (self.current_user) and (await self.db.user.get(self.current_user['id'], fields=('id',))):
            self.redirect('/my/')
            return
        reg_flg = False if (await self.db.site.get(1, fields=('regEn',)))['regEn'] == 0 else True

        return await self.render('login.html', regFlg=reg_flg)

    async def post(self):
        email = self.get_argument('email')
        password = self.get_argument('password')
        async with self.db.transaction() as sql_session:
            siteconfig = await self.db.site.get(1, fields=('MustVerifyEmailEn',), sql_session=sql_session)
            reg_flg = False if (await self.db.site.get(1, fields=('regEn',), sql_session=sql_session))['regEn'] == 0 else True
            if not email or not password:
                await self.render('login.html', password_error='请输入用户名和密码', email=email, regFlg=reg_flg)
                return

            user_try = await self.db.user.get(email=email, fields=('id', 'role', 'status'), sql_session=sql_session)
            if user_try:
                if (user_try['status'] != 'Enable') and (user_try['role'] != 'admin'):
                    await self.render('login.html', password_error='账号已被禁用，请联系管理员', email=email, regFlg=reg_flg)
                    return
            else:
                await self.render('login.html', password_error='不存在此邮箱或密码错误', email=email, regFlg=reg_flg)
                return

            if await self.db.user.challenge(email, password, sql_session=sql_session):
                user = await self.db.user.get(email=email, fields=('id', 'email', 'nickname', 'role', 'email_verified'), sql_session=sql_session)
                if not user:
                    await self.render('login.html', password_error='不存在此邮箱或密码错误', email=email, regFlg=reg_flg)
                    return

                if (siteconfig['MustVerifyEmailEn'] != 0) and (user['email_verified'] == 0):
                    await self.render('login.html', password_error='未验证邮箱，请点击注册重新验证邮箱', email=email, regFlg=reg_flg)
                    return

                setcookie = dict(
                    expires_days=config.cookie_days,
                    httponly=True,
                )
                if config.cookie_secure_mode:
                    setcookie['secure'] = True
                self.set_secure_cookie('user', umsgpack.packb(user), **setcookie)
                await self.db.user.mod(user['id'], atime=time.time(), aip=self.ip2varbinary, sql_session=sql_session)

                # 如果用户MD5不一致就更新MD5
                user = await self.db.user.get(email=email, fields=('id', 'password', 'password_md5'), sql_session=sql_session)
                hash = MD5.new()
                hash.update(password.encode('utf-8'))
                tmp = crypto.password_hash(hash.hexdigest(), await self.db.user.decrypt(user['id'], user['password'], sql_session=sql_session))
                if user['password_md5'] != tmp:
                    await self.db.user.mod(user['id'], password_md5=tmp, sql_session=sql_session)
            else:
                self.evil(+5)
                await self.render('login.html', password_error='不存在此邮箱或密码错误', email=email, regFlg=reg_flg)
                return

        if user:
            self.redirect('/my/')


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect('/')


class RegisterHandler(BaseHandler):
    async def get(self):
        if self.current_user:
            self.redirect('/my/')
            return

        reg_flg = False if (await self.db.site.get(1, fields=('regEn',)))['regEn'] == 0 else True
        return await self.render('register.html', regFlg=reg_flg)

    async def post(self):
        async with self.db.transaction() as sql_session:
            siteconfig = await self.db.site.get(1, fields=('regEn', 'MustVerifyEmailEn'), sql_session=sql_session)
            reg_en = siteconfig['regEn']
            reg_flg = False if reg_en == 0 else True
            must_verify_email_en = siteconfig['MustVerifyEmailEn']
            email = self.get_argument('email')
            password = self.get_argument('password')

            if not email:
                await self.render('register.html', email_error='请输入邮箱', regFlg=reg_flg)
                return
            if email.count('@') != 1 or email.count('.') == 0:
                await self.render('register.html', email_error='邮箱格式不正确', regFlg=reg_flg)
                return
            if len(password) < 6:
                await self.render('register.html', password_error='密码需要大于6位', email=email, regFlg=reg_flg)
                return

            user = await self.db.user.get(email=email, fields=('id', 'email', 'email_verified', 'nickname', 'role'), sql_session=sql_session)
            if user is None:
                if reg_en == 1:
                    self.evil(+5)
                    try:
                        await self.db.user.add(email=email, password=password, ip=self.ip2varbinary, sql_session=sql_session)
                    except self.db.user.DeplicateUser as e:
                        logger_web_handler.error("email地址 %s 已注册, error: %s", email, e, exc_info=config.traceback_print)
                        self.evil(+3)
                        await self.render('register.html', email_error='email地址已注册', regFlg=reg_flg)
                        return
                    user = await self.db.user.get(email=email, fields=('id', 'email', 'nickname', 'role'), sql_session=sql_session)
                    await self.db.notepad.add(dict(userid=user['id'], notepadid=1), sql_session=sql_session)
                    setcookie = dict(
                        expires_days=config.cookie_days,
                        httponly=True,
                    )
                    if config.cookie_secure_mode:
                        setcookie['secure'] = True
                    self.set_secure_cookie('user', umsgpack.packb(user), **setcookie)
                    usertmp = await self.db.user.list(sql_session=sql_session, fields=('id', 'email', 'nickname', 'role', 'email_verified'))
                    if len(usertmp) == 1 and config.user0isadmin:
                        if usertmp[0]['email'] == email:
                            await self.db.user.mod(usertmp[0]['id'], role='admin', sql_session=sql_session)

                    if siteconfig['MustVerifyEmailEn'] == 1:
                        if not config.domain:
                            await self.render('register.html', email_error='请联系 QD 框架管理员配置框架域名 domain, 以启用邮箱验证功能!', regFlg=reg_flg)
                        else:
                            await self.render('register.html', email_error='请验证邮箱后再登陆', regFlg=reg_flg)
                    if config.domain:
                        await self.send_mail(user, sql_session=sql_session)
                    else:
                        logger_web_handler.warning('请配置框架域名 domain, 以启用邮箱验证功能!')
                else:
                    await self.render('register.html', email_error='管理员关闭注册', regFlg=reg_flg)
                    return
            else:
                if must_verify_email_en == 1:
                    if user['email_verified'] != 1:
                        if not config.domain:
                            await self.render('register.html', email_error='请联系 QD 框架管理员配置框架域名 domain, 以启用邮箱验证功能!', regFlg=reg_flg)
                            return
                        await self.render('register.html', email_error='email地址未验证, 邮件已发送, 请验证邮件后登陆')
                        await self.send_mail(user, sql_session=sql_session)
                    else:
                        await self.render('register.html', email_error='email地址已注册', regFlg=reg_flg)
                else:
                    await self.render('register.html', email_error='email地址已注册', regFlg=reg_flg)
                return
        if user:
            self.redirect('/my/')

    async def send_mail(self, user, sql_session=None):
        verified_code = [user['email'], time.time()]
        verified_code = await self.db.user.encrypt(user['id'], verified_code, sql_session=sql_session)
        verified_code = await self.db.user.encrypt(0, [user['id'], verified_code], sql_session=sql_session)
        verified_code = base64.b64encode(verified_code).decode()
        await gen.convert_yielded(utils.send_mail(to=user['email'], subject="欢迎注册 QD 平台", html="""
                <table style="width:99.8%%;height:99.8%%"><tbody><tr><td style=" background:#fafafa url(#) "><div style="border-radius:10px;font-size:13px;color:#555;width:666px;font-family:'Century Gothic','Trebuchet MS','Hiragino Sans GB','微软雅黑','Microsoft Yahei',Tahoma,Helvetica,Arial,SimSun,sans-serif;margin:50px auto;border:1px solid #eee;max-width:100%%;background:#fff repeating-linear-gradient(-45deg,#fff,#fff 1.125rem,transparent 1.125rem,transparent 2.25rem);box-shadow:0 1px 5px rgba(0,0,0,.15)"><div style="width:100%%;background:#49BDAD;color:#fff;border-radius:10px 10px 0 0;background-image:-moz-linear-gradient(0deg,#43c6b8,#ffd1f4);background-image:-webkit-linear-gradient(0deg,#4831ff,#0497ff);height:66px"><p style="font-size:15px;word-break:break-all;padding:23px 32px;margin:0;background-color:hsla(0,0%%,100%%,.4);border-radius:10px 10px 0 0">&nbsp;[QD平台]&nbsp;&nbsp;{http}://{domain}</p></div>
                <div style="margin:40px auto;width:90%%">
                    <p>点击以下链接验证邮箱，当您的定时任务执行失败的时候，会自动给您发送通知邮件。</p>
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


class VerifyHandler(BaseHandler):
    async def get(self, code):
        userid = None
        try:
            async with self.db.transaction() as sql_session:
                verified_code = base64.b64decode(code)
                userid, verified_code = await self.db.user.decrypt(0, verified_code, sql_session=sql_session)
                user = await self.db.user.get(userid, fields=('id', 'email', 'email_verified'), sql_session=sql_session)
                assert user
                assert not user['email_verified']
                email, time_time = await self.db.user.decrypt(userid, verified_code, sql_session=sql_session)
                assert time.time() - time_time < 30 * 24 * 60 * 60
                assert user['email'] == email

                await self.db.user.mod(userid,
                                       email_verified=True,
                                       mtime=time.time(),
                                       sql_session=sql_session
                                       )
            await self.finish('验证成功')
        except Exception as e:
            self.evil(+5)
            logger_web_handler.error('UserID: %s verify email failed! Reason: %s', userid or '-1', e, exc_info=config.traceback_print)
            self.set_status(400)
            await self.finish('验证失败')


class PasswordResetHandler(BaseHandler):
    async def get(self, code):
        if not code:
            return await self.render('password_reset_email.html')

        try:
            verified_code = base64.b64decode(code)
            userid, verified_code = await self.db.user.decrypt(0, verified_code)
            user = await self.db.user.get(userid, fields=('id', 'email', 'mtime'))
            assert user
            mtime, time_time = await self.db.user.decrypt(userid, verified_code)
            assert mtime == user['mtime']
            assert time.time() - time_time < 60 * 60
        except Exception as e:
            self.evil(+10)
            logger_web_handler.error('%r', e, exc_info=config.traceback_print)
            self.set_status(400)
            await self.finish('Bad Request')
            return

        return await self.render('password_reset.html')

    async def post(self, code):
        if not config.domain:
            await self.finish('请联系 QD 框架管理员配置框架域名 domain, 以启用密码重置功能!')
            return
        if not code:
            self.evil(+5)

            email = self.get_argument('email')
            if not email:
                return await self.render('password_reset_email.html',
                                         email_error='请输入邮箱')
            if email.count('@') != 1 or email.count('.') == 0:
                return await self.render('password_reset_email.html',
                                         email_error='邮箱格式不正确')

            user = await self.db.user.get(email=email, fields=('id', 'email', 'mtime', 'nickname', 'role'))
            await self.finish("如果用户存在，会将发送密码重置邮件到您的邮箱，请注意查收。（如果您没有收到过激活邮件，可能无法也无法收到密码重置邮件）")
            if user:
                logger_web_handler.info('password reset: userid=%(id)s email=%(email)s', user)
                await self.send_mail(user)

            return
        else:
            password = self.get_argument('password')
            if len(password) < 6:
                return await self.render('password_reset.html', password_error='密码需要大于6位')

            async with self.db.transaction() as sql_session:
                try:
                    verified_code = base64.b64decode(code)
                    userid, verified_code = await self.db.user.decrypt(0, verified_code, sql_session=sql_session)
                    user = await self.db.user.get(userid, fields=('id', 'email', 'mtime', 'email_verified'), sql_session=sql_session)
                    assert user
                    mtime, time_time = await self.db.user.decrypt(userid, verified_code, sql_session=sql_session)
                    assert mtime == user['mtime']
                    assert time.time() - time_time < 60 * 60
                except Exception as e:
                    self.evil(+10)
                    logger_web_handler.error('%r', e, exc_info=config.traceback_print)
                    self.set_status(400)
                    await self.finish('Bad Request')
                    return

                await self.db.user.mod(userid,
                                       password=password,
                                       mtime=time.time(),
                                       sql_session=sql_session
                                       )
            return self.finish(f'密码重置成功! 请<a href="{"https" if config.mail_domain_https else "http"}://{config.domain}/login" >点击此处</a>返回登录页面。')

    async def send_mail(self, user):
        verified_code = [user['mtime'], time.time()]
        verified_code = await self.db.user.encrypt(user['id'], verified_code)
        verified_code = await self.db.user.encrypt(0, [user['id'], verified_code])
        verified_code = base64.b64encode(verified_code).decode()

        await gen.convert_yielded(utils.send_mail(to=user['email'], subject=f"QD平台({config.domain}) 密码重置", html="""

        <table style="width:99.8%%;height:99.8%%"><tbody><tr><td style=" background:#fafafa url(#) "><div style="border-radius:10px;font-size:13px;color:#555;width:666px;font-family:'Century Gothic','Trebuchet MS','Hiragino Sans GB','微软雅黑','Microsoft Yahei',Tahoma,Helvetica,Arial,SimSun,sans-serif;margin:50px auto;border:1px solid #eee;max-width:100%%;background:#fff repeating-linear-gradient(-45deg,#fff,#fff 1.125rem,transparent 1.125rem,transparent 2.25rem);box-shadow:0 1px 5px rgba(0,0,0,.15)"><div style="width:100%%;background:#49BDAD;color:#fff;border-radius:10px 10px 0 0;background-image:-moz-linear-gradient(0deg,#43c6b8,#ffd1f4);background-image:-webkit-linear-gradient(0deg,#4831ff,#0497ff);height:66px"><p style="font-size:15px;word-break:break-all;padding:23px 32px;margin:0;background-color:hsla(0,0%%,100%%,.4);border-radius:10px 10px 0 0">&nbsp;[QD平台]&nbsp;&nbsp;{http}://{domain}</p></div>
                <div style="margin:40px auto;width:90%%">
                    <p>点击以下链接完成您的密码重置（一小时内有效）。</p>
                    <p style="background:#fafafa repeating-linear-gradient(-45deg,#fff,#fff 1.125rem,transparent 1.125rem,transparent 2.25rem);box-shadow:0 2px 5px rgba(0,0,0,.15);margin:20px 0;padding:15px;border-radius:5px;font-size:14px;color:#555"><a href="{http}://{domain}/password_reset/{code}">{http}://{domain}/password_reset/{code}</a></p>
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
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    ('/register', RegisterHandler),
    ('/verify/(.*)', VerifyHandler),
    ('/password_reset/?(.*)', PasswordResetHandler),
    ('/forbidden', ForbiddenHandler),
]
