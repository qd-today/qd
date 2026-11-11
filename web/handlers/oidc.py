#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Created on 2026-11-07

'''
OIDC 登录 / 绑定 / 解绑 / 管理 路由

流程状态 (state / nonce / code_verifier / mode) 全部存放在 Tornado 签名 Cookie 中,
不落服务端存储、不出现在 URL 上; 回调时校验签名与 state 并一次性删除。
'''

import secrets
import time

import tornado.web
import umsgpack
from tornado.web import authenticated

import config
from libs import oidc
from libs.log import Log
from web.handlers.base import BaseHandler, session_version

logger_web_oidc = Log('QD.Web.OIDC').getlogger()

# 流程 Cookie 有效期 (秒)
OIDC_FLOW_TTL = 600
# 会话 Cookie 有效期沿用 config.cookie_days


def _flow_cookie_name(provider):
    return 'oidc_flow_%s' % provider


class _OidcBaseHandler(BaseHandler):
    '''OIDC 路由公共逻辑。'''

    # ---- provider ----

    def get_provider(self, provider_id):
        provider = config.get_oidc_provider(provider_id)
        if provider is None or not provider.get('enabled', True):
            raise oidc.OidcError('provider_not_found')
        return provider

    def redirect_uri(self, provider_id):
        if not config.domain:
            logger_web_oidc.error(
                'OIDC 未配置 DOMAIN, 无法生成 redirect_uri (provider=%s)', provider_id
            )
            raise oidc.OidcError('not_configured')
        scheme = 'https' if config.mail_domain_https else 'http'
        return '%s://%s/oidc/%s/callback' % (scheme, config.domain, provider_id)

    # ---- 流程 Cookie ----

    def save_flow(self, provider_id, flow):
        name = _flow_cookie_name(provider_id)
        signed = tornado.web.create_signed_value(
            config.cookie_secret, name, umsgpack.packb(flow)
        )
        setcookie = dict(
            expires=flow['exp'],
            httponly=True,
        )
        if config.cookie_secure_mode:
            setcookie['secure'] = True
        self.set_cookie(name, signed, **setcookie)

    def load_flow(self, provider_id):
        name = _flow_cookie_name(provider_id)
        raw = self.get_cookie(name)
        if not raw:
            raise oidc.OidcError('state_mismatch', 'flow cookie missing')
        value = tornado.web.decode_signed_value(
            config.cookie_secret, name, raw, max_age_days=config.cookie_days
        )
        if not value:
            raise oidc.OidcError('state_mismatch', 'flow cookie signature invalid')
        try:
            flow = umsgpack.unpackb(value)
        except Exception as e:
            raise oidc.OidcError('state_mismatch', 'flow cookie unparsable') from e
        if not isinstance(flow, dict):
            raise oidc.OidcError('state_mismatch', 'flow cookie payload invalid')
        if flow.get('provider') != provider_id:
            raise oidc.OidcError('state_mismatch', 'flow cookie provider mismatch')
        if int(flow.get('exp') or 0) < int(time.time()):
            raise oidc.OidcError('state_mismatch', 'flow cookie expired')
        return flow

    def clear_flow(self, provider_id):
        self.clear_cookie(_flow_cookie_name(provider_id))

    # ---- 会话 ----

    def establish_session(self, user):
        '''复用 LoginHandler 的会话建立方式, 不引入新的会话格式。'''
        setcookie = dict(
            expires_days=config.cookie_days,
            httponly=True,
        )
        if config.cookie_secure_mode:
            setcookie['secure'] = True
        self.set_secure_cookie(
            'user',
            umsgpack.packb({'id': user['id'], 'v': session_version(user['password'])}),
            **setcookie,
        )

    @staticmethod
    def _account_usable(user):
        return (user['status'] == 'Enable') or (user['role'] == 'admin')


class OidcLoginHandler(_OidcBaseHandler):
    '''GET /oidc/<provider>/login: 跳转到 IdP 授权端点。'''

    async def get(self, provider):
        try:
            provider_conf = self.get_provider(provider)
            redirect_uri = self.redirect_uri(provider)
            metadata = await oidc.get_provider_metadata(provider_conf)
        except oidc.OidcError as e:
            logger_web_oidc.warning('OIDC login 失败 (provider=%s): %s', provider, e)
            return self.redirect('/login?oidc_error=%s' % e.code)

        code_verifier, code_challenge = oidc.generate_pkce_pair()
        flow = {
            'provider': provider,
            'state': oidc.generate_state(),
            'nonce': oidc.generate_nonce(),
            'code_verifier': code_verifier,
            'mode': 'login',
            'userid': None,
            'exp': int(time.time()) + OIDC_FLOW_TTL,
        }
        self.save_flow(provider, flow)

        url = oidc.build_authorize_url(
            provider_conf,
            metadata,
            flow['state'],
            flow['nonce'],
            redirect_uri,
            code_challenge,
        )
        return self.redirect(url)


class OidcBindHandler(_OidcBaseHandler):
    '''GET /oidc/<provider>/bind: 已登录用户发起绑定。'''

    @authenticated
    async def get(self, provider):
        try:
            provider_conf = self.get_provider(provider)
            redirect_uri = self.redirect_uri(provider)
            metadata = await oidc.get_provider_metadata(provider_conf)
        except oidc.OidcError as e:
            logger_web_oidc.warning('OIDC bind 失败 (provider=%s): %s', provider, e)
            return self.redirect('/oidc/manage?oidc_error=%s' % e.code)

        code_verifier, code_challenge = oidc.generate_pkce_pair()
        flow = {
            'provider': provider,
            'state': oidc.generate_state(),
            'nonce': oidc.generate_nonce(),
            'code_verifier': code_verifier,
            'mode': 'bind',
            'userid': self.current_user['id'],
            'exp': int(time.time()) + OIDC_FLOW_TTL,
        }
        self.save_flow(provider, flow)

        url = oidc.build_authorize_url(
            provider_conf,
            metadata,
            flow['state'],
            flow['nonce'],
            redirect_uri,
            code_challenge,
        )
        return self.redirect(url)


class OidcCallbackHandler(_OidcBaseHandler):
    '''GET /oidc/<provider>/callback: 统一处理登录与绑定回调。'''

    async def get(self, provider):
        error_target = '/login'
        try:
            provider_conf = self.get_provider(provider)
            flow = self.load_flow(provider)
            if flow.get('mode') == 'bind':
                error_target = '/oidc/manage'

            # IdP 直接返回错误
            upstream_error = self.get_argument('error', '')
            if upstream_error:
                raise oidc.OidcError('upstream_error', upstream_error)

            # state 恒定时间比较
            state = self.get_argument('state', '')
            if not state or not secrets.compare_digest(flow.get('state') or '', state):
                raise oidc.OidcError('state_mismatch')

            # 一次性: 校验通过后立即失效流程 Cookie
            self.clear_flow(provider)

            code = self.get_argument('code', '')
            redirect_uri = self.redirect_uri(provider)
            metadata = await oidc.get_provider_metadata(provider_conf)

            token = await oidc.exchange_code(
                provider_conf, metadata, code, redirect_uri, flow['code_verifier']
            )
            claims = await oidc.verify_id_token(
                provider_conf,
                metadata,
                token.get('id_token'),
                None,
                flow['nonce'],
                access_token=token.get('access_token'),
            )
            subject = claims['sub']
            email = claims.get('email')
            email_verified = claims.get('email_verified')
        except oidc.OidcError as e:
            logger_web_oidc.warning('OIDC callback 失败 (provider=%s): %s', provider, e)
            # 计入限流, 与密码登录失败同权重 (+5, 见 web/handlers/login.py:81)。
            # 该分支只覆盖流程/令牌校验失败 (state_mismatch、交换失败、id_token 校验失败
            # 等), 不包含 _handle_login 内部的 email_unverified / no_account 等
            # 正常业务回绝 (那些在 try 之外, 走 redirect 分支), 故不会误伤正常用户。
            self.evil(+5)
            self.clear_flow(provider)
            return self.redirect('%s?oidc_error=%s' % (error_target, e.code))
        except Exception as e:  # pylint: disable=broad-except
            logger_web_oidc.error(
                'OIDC callback 异常 (provider=%s): %s', provider, e, exc_info=config.traceback_print
            )
            self.clear_flow(provider)
            return self.redirect('%s?oidc_error=internal_error' % error_target)

        if flow.get('mode') == 'bind':
            return await self._handle_bind(provider, subject, email, flow)
        return await self._handle_login(provider, subject, email, email_verified)

    async def _handle_login(self, provider, subject, email, email_verified):
        # 1. 已有绑定 -> 直接登录
        binding = await self.db.user_oidc.get(provider=provider, subject=subject)
        if binding is not None:
            user = await self.db.user.get(
                binding['userid'],
                fields=('id', 'email', 'nickname', 'role', 'status', 'password'),
            )
            if user is None:
                return self.redirect('/login?oidc_error=no_account')
            if not self._account_usable(user):
                return self.redirect('/login?oidc_error=user_disabled')
            if email and email != binding.get('email'):
                await self.db.user_oidc.mod(binding['id'], email=email)
            # 与密码登录 (web/handlers/login.py:71) 同口径: 记录最后登录时间与 IP
            await self.db.user.mod(user['id'], atime=time.time(), aip=self.ip2varbinary)
            self.establish_session(user)
            return self.redirect('/my/')

        # 2. 无绑定 -> 按 id_token 中的 email 匹配既有账号, 绝不自动注册
        if not email:
            return self.redirect('/login?oidc_error=email_missing')
        # 自动绑定等于把既有账号的登录权交给 IdP 单方面声明的 email, 故要求
        # IdP 明确标记邮箱已验证 (严格布尔真; 字符串 "true" 视为未验证, fail-safe)。
        # 未通过者仍可用密码登录后手动绑定 (见 /oidc/<provider>/bind)。
        if email_verified is not True:
            return self.redirect('/login?oidc_error=email_unverified')
        user = await self.db.user.get(
            email=email,
            fields=('id', 'email', 'nickname', 'role', 'status', 'password'),
        )
        if user is None:
            return self.redirect('/login?oidc_error=no_account')
        if not self._account_usable(user):
            return self.redirect('/login?oidc_error=user_disabled')

        existing = await self.db.user_oidc.get(userid=user['id'], provider=provider)
        if existing is not None:
            # 同一用户在本 provider 上已绑定其它 subject
            return self.redirect('/login?oidc_error=already_bound_other')

        try:
            async with self.db.transaction() as sql_session:
                await self.db.user_oidc.add(
                    user['id'], provider, subject, email=email, sql_session=sql_session
                )
        except Exception as e:  # pylint: disable=broad-except
            # 并发下可能已被其它请求写入, 复查后按已绑定处理
            logger_web_oidc.warning('OIDC 自动绑定冲突 (provider=%s): %s', provider, e)
            binding = await self.db.user_oidc.get(provider=provider, subject=subject)
            if binding is None or binding['userid'] != user['id']:
                return self.redirect('/login?oidc_error=already_bound_other')

        # 与密码登录 (web/handlers/login.py:71) 同口径: 记录最后登录时间与 IP
        await self.db.user.mod(user['id'], atime=time.time(), aip=self.ip2varbinary)
        self.establish_session(user)
        return self.redirect('/my/')

    async def _handle_bind(self, provider, subject, email, flow):
        current_user = self.current_user
        userid = flow.get('userid')
        if not current_user or not userid or current_user['id'] != userid:
            return self.redirect('/oidc/manage?oidc_error=state_mismatch')

        binding = await self.db.user_oidc.get(provider=provider, subject=subject)
        if binding is not None:
            if binding['userid'] != userid:
                return self.redirect('/oidc/manage?oidc_error=bound_by_other')
            # 幂等: 已是自己的绑定
            return self.redirect('/oidc/manage')

        existing = await self.db.user_oidc.get(userid=userid, provider=provider)
        if existing is not None:
            return self.redirect('/oidc/manage?oidc_error=already_bound_self')

        try:
            async with self.db.transaction() as sql_session:
                await self.db.user_oidc.add(
                    userid, provider, subject, email=email, sql_session=sql_session
                )
                await self.db.user.mod(userid, mtime=time.time(), sql_session=sql_session)
        except Exception as e:  # pylint: disable=broad-except
            logger_web_oidc.warning('OIDC 绑定冲突 (provider=%s): %s', provider, e)
            binding = await self.db.user_oidc.get(provider=provider, subject=subject)
            if binding is not None and binding['userid'] != userid:
                return self.redirect('/oidc/manage?oidc_error=bound_by_other')
            return self.redirect('/oidc/manage?oidc_error=already_bound_self')

        return self.redirect('/oidc/manage')


class OidcUnbindHandler(_OidcBaseHandler):
    '''POST /oidc/<provider>/unbind: 解绑当前用户在该 provider 上的绑定。'''

    @authenticated
    async def post(self, provider):
        # 解绑会移除一条登录凭据, 属于状态变更, 必须校验 CSRF token。
        # 用 tornado 自带的 check_xsrf_cookie() (成熟实现): 它读取 _xsrf 参数或
        # X-Xsrftoken 头, 与 _xsrf Cookie 做恒定时间比较, 缺失/不符一律 403。
        # 本应用未开 xsrf_cookies 应用设置, 但该方法不依赖它 (见 tornado/web.py
        # check_xsrf_cookie); 页面通过 base.render_string 注入的 xsrf_form_html()
        # 下发隐藏字段, 故只影响本端点, 其它路由行为不变。
        self.check_xsrf_cookie()

        provider_conf = config.get_oidc_provider(provider)
        if provider_conf is None:
            return self.redirect('/oidc/manage?oidc_error=provider_not_found')

        userid = self.current_user['id']
        user = await self.db.user.get(userid, fields=('id', 'password'))
        if user is None:
            return self.redirect('/oidc/manage?oidc_error=no_account')

        bindings = await self.db.user_oidc.list(userid=userid)
        if not any(binding['provider'] == provider for binding in bindings):
            return self.redirect('/oidc/manage?oidc_error=not_bound')

        remaining = [
            binding for binding in bindings if binding['provider'] != provider
        ]
        # 无可用密码且解绑后没有任何 OIDC 绑定 -> 拒绝, 避免用户失去全部登录方式
        if not user.get('password') and not remaining:
            return self.redirect('/oidc/manage?oidc_error=last_credential')

        await self.db.user_oidc.delete_by_user_provider(userid, provider)
        return self.redirect('/oidc/manage')


class OidcManageHandler(_OidcBaseHandler):
    '''GET /oidc/manage: OIDC 绑定管理页。'''

    @authenticated
    async def get(self):
        userid = self.current_user['id']
        bindings = await self.db.user_oidc.list(userid=userid)
        bound = {binding['provider']: binding for binding in bindings}

        providers = []
        for provider in config.get_enabled_providers():
            item = dict(provider)
            item['binding'] = bound.get(provider['id'])
            providers.append(item)

        return await self.render(
            'oidc_manage.html',
            providers=providers,
            oidc_error=self.get_argument('oidc_error', ''),
        )


handlers = [
    ('/oidc/manage/?', OidcManageHandler),
    (r'/oidc/([a-zA-Z0-9_-]{1,64})/login/?', OidcLoginHandler),
    (r'/oidc/([a-zA-Z0-9_-]{1,64})/bind/?', OidcBindHandler),
    (r'/oidc/([a-zA-Z0-9_-]{1,64})/unbind/?', OidcUnbindHandler),
    (r'/oidc/([a-zA-Z0-9_-]{1,64})/callback/?', OidcCallbackHandler),
]
