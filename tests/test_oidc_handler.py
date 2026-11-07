# -*- coding: utf-8 -*-
"""web/handlers/oidc.py 的真实单元测试。

设计：**假请求层 + 真 handler 逻辑**。

  * `FakeRequest` 只实现 tornado `RequestHandler` 中本模块真正用到的那几个接口
    （`get_cookie` / `set_cookie` / `clear_cookie` / `set_secure_cookie` /
    `redirect` / `current_user` / `db`）；
  * 所有被验的业务逻辑（`save_flow` / `load_flow` / `clear_flow` /
    `establish_session` / `_handle_login` / `_handle_bind`）都**直接绑定真实实现**，
    不做任何复制或重写。这一点很关键：如果这里照抄一份「等价」逻辑，测试对产品
    代码的变异就会失去敏感性，变成自证。

覆盖的是独立 reviewer 点名的四个缺口（H1 回归 + H2/H3/H4 三个盲区）：
  (a) `email_unverified` 门禁（Lead 修复的 MEDIUM-1）；
  (b) flow 过期；
  (c) flow 的 provider 绑定；
  (d) bind flow 的 userid 绑定。

注意：import 本模块会打印 QD 启动告警（stdout/stderr），断言一律不依赖输出。
"""
import asyncio
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import umsgpack  # noqa: E402

import config  # noqa: E402
import test_oidc_support as support  # noqa: E402
from web.handlers.oidc import (  # noqa: E402
    OIDC_FLOW_TTL,
    OidcCallbackHandler,
    _flow_cookie_name,
    _OidcBaseHandler,
)

PROVIDER_A = 'provider-a'
PROVIDER_B = 'provider-b'


def run(coro):
    """跑一个协程并返回结果（测试里不共享事件循环）。"""
    return asyncio.run(coro)


# --------------------------------------------------------------------------
# 假 DB
# --------------------------------------------------------------------------


class _FakeTransaction:
    """`db.transaction()` 的 async context manager 替身。"""

    def __init__(self, owner):
        self.owner = owner
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        self.owner.transactions.append(self)
        return object()  # 假的 sql_session 哨兵

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        return False


class FakeUserDB:
    """`db.user` 的最小替身：按 id / email 查。"""

    def __init__(self, users=()):
        self.users = [dict(u) for u in users]

    async def get(self, id=None, email=None, fields=None, sql_session=None, **kw):
        for user in self.users:
            if id is not None and user.get('id') != id:
                continue
            if email is not None and user.get('email') != email:
                continue
            if id is None and email is None:
                continue
            return dict(user)
        return None

    async def mod(self, id, **kw):
        self.mods = getattr(self, 'mods', [])
        self.mods.append((id, kw))
        return 1


class FakeUserOidcDB:
    """`db.user_oidc` 的最小替身：记录 add 调用，支持按选择器查。"""

    def __init__(self, rows=()):
        self.rows = [dict(r) for r in rows]
        self.added = []
        self.mods = []

    async def get(self, id=None, provider=None, subject=None, userid=None,
                  fields=None, sql_session=None, **kw):
        for row in self.rows:
            if id is not None and row.get('id') != id:
                continue
            if provider is not None and row.get('provider') != provider:
                continue
            if subject is not None and row.get('subject') != subject:
                continue
            if userid is not None and row.get('userid') != userid:
                continue
            return dict(row)
        return None

    async def list(self, userid=None, provider=None, fields=None, limit=None,
                   sql_session=None, **kw):
        out = []
        for row in self.rows:
            if userid is not None and row.get('userid') != userid:
                continue
            if provider is not None and row.get('provider') != provider:
                continue
            out.append(dict(row))
        return out[:limit] if limit else out

    async def add(self, userid, provider, subject, email=None, sql_session=None):
        self.added.append({
            'userid': userid, 'provider': provider, 'subject': subject, 'email': email,
        })
        return len(self.added)

    async def mod(self, id, **kw):
        self.mods.append((id, kw))
        return 1


class FakeDB:
    def __init__(self, users=(), bindings=()):
        self.user = FakeUserDB(users)
        self.user_oidc = FakeUserOidcDB(bindings)
        self.transactions = []

    def transaction(self):
        return _FakeTransaction(self)


# --------------------------------------------------------------------------
# 假请求层（业务逻辑全部绑定真实实现）
# --------------------------------------------------------------------------


class FakeRequest:
    """假 RequestHandler：只提供 cookie / redirect / current_user / db。

    `save_flow` / `load_flow` / `clear_flow` / `establish_session` /
    `_handle_login` / `_handle_bind` 全部**直接引用产品代码里的函数对象**。
    """

    save_flow = _OidcBaseHandler.save_flow
    load_flow = _OidcBaseHandler.load_flow
    clear_flow = _OidcBaseHandler.clear_flow
    establish_session = _OidcBaseHandler.establish_session
    _account_usable = staticmethod(_OidcBaseHandler._account_usable)
    _handle_login = OidcCallbackHandler._handle_login
    _handle_bind = OidcCallbackHandler._handle_bind

    def __init__(self, cookies=None, current_user=None, db=None):
        self._cookies = dict(cookies or {})
        self.current_user = current_user
        self.db = db if db is not None else FakeDB()
        self.redirects = []
        self.secure_cookies = {}
        self.cleared = []

    # ---- tornado cookie API 的最小子集 ----

    def get_cookie(self, name, default=None):
        return self._cookies.get(name, default)

    def set_cookie(self, name, value, **kwargs):
        self._cookies[name] = value

    def clear_cookie(self, name, **kwargs):
        self.cleared.append(name)
        self._cookies.pop(name, None)

    def set_secure_cookie(self, name, value, **kwargs):
        self.secure_cookies[name] = value

    def redirect(self, url, *args, **kwargs):
        self.redirects.append(url)
        return url

    # ---- 便利断言辅助 ----

    @property
    def last_redirect(self):
        return self.redirects[-1] if self.redirects else None


# --------------------------------------------------------------------------
# 夹具
# --------------------------------------------------------------------------


def make_user(uid=1, email='alice@example.test', status='Enable', role='user',
              password='hashed-password'):
    return {
        'id': uid, 'email': email, 'nickname': 'Alice', 'role': role,
        'status': status, 'password': password,
    }


def fresh_flow(provider=PROVIDER_A, mode='login', userid=None, exp_delta=OIDC_FLOW_TTL):
    return {
        'provider': provider,
        'state': 'state-1',
        'nonce': 'nonce-1',
        'code_verifier': 'verifier-1',
        'mode': mode,
        'userid': userid,
        'exp': int(time.time()) + exp_delta,
    }


# --------------------------------------------------------------------------
# (b) H2 —— flow 过期
# --------------------------------------------------------------------------


class TestFlowCookie(unittest.TestCase):
    """load_flow 的健壮性：过期、缺 cookie、坏签名、payload 非法。"""

    def test_expired_flow_is_rejected(self):
        """已过期的 flow 必须抛 state_mismatch，不能因为签名有效就放行。"""
        req = FakeRequest()
        flow = fresh_flow(exp_delta=-10)  # 10 秒前就过期了
        req.save_flow(PROVIDER_A, flow)
        with self.assertRaises(Exception) as ctx:
            req.load_flow(PROVIDER_A)
        self.assertEqual(getattr(ctx.exception, 'code', None), 'state_mismatch')

    def test_exp_just_expired_by_one_second_is_rejected(self):
        """边界：exp 比当前时间早 1 秒也必须拒绝（不是「过期很久才算」）。"""
        req = FakeRequest()
        req.save_flow(PROVIDER_A, fresh_flow(exp_delta=-1))
        with self.assertRaises(Exception) as ctx:
            req.load_flow(PROVIDER_A)
        self.assertEqual(getattr(ctx.exception, 'code', None), 'state_mismatch')

    def test_not_yet_expired_flow_loads(self):
        """未过期的 flow 必须正常返回——否则上面的拒绝可能是「什么都拒绝」的假阳性。"""
        req = FakeRequest()
        flow = fresh_flow()
        req.save_flow(PROVIDER_A, flow)
        loaded = req.load_flow(PROVIDER_A)
        self.assertEqual(loaded['state'], 'state-1')
        self.assertEqual(loaded['provider'], PROVIDER_A)

    def test_missing_cookie_is_rejected(self):
        req = FakeRequest()
        with self.assertRaises(Exception) as ctx:
            req.load_flow(PROVIDER_A)
        self.assertEqual(getattr(ctx.exception, 'code', None), 'state_mismatch')

    def test_tampered_cookie_signature_is_rejected(self):
        req = FakeRequest()
        req.save_flow(PROVIDER_A, fresh_flow())
        name = _flow_cookie_name(PROVIDER_A)
        # create_signed_value 返回 bytes；篡改签名部分（追加一个字节）
        raw = req._cookies[name]
        self.assertIsInstance(raw, (bytes, bytearray))
        req._cookies[name] = bytes(raw) + b'x'
        with self.assertRaises(Exception) as ctx:
            req.load_flow(PROVIDER_A)
        self.assertEqual(getattr(ctx.exception, 'code', None), 'state_mismatch')


# --------------------------------------------------------------------------
# (c) H3 —— flow 的 provider 绑定
# --------------------------------------------------------------------------


class TestFlowProviderBinding(unittest.TestCase):
    """为 provider A 存下的 flow，绝不能在 provider B 的回调里被接受。

    这里有两道**互相独立**的防线，测试必须分别钉住，不能混为一谈：
      1. tornado 的签名值把 **cookie 名**也绑进了签名——A 的 cookie 值拿到 B 的
         名字下解码会直接失败。这是 tornado 提供的，**不是**本模块的逻辑。
      2. `load_flow` 里 `flow['provider'] != provider_id` 的显式核对——即使签名
         校验通过（值本来就是在 B 名下签的），payload 自称的 provider 也必须匹配。

    实测教训：最初只写了「A 的值塞到 B 名下」这一条，它在把第 2 道防线变异掉
    （`if False:`）之后**依然通过**——因为拦它的是第 1 道防线。这种「因为别的原因
    通过」的用例是假阳性，故拆成下面两条各自定向的用例。
    """

    def test_cookie_signature_is_bound_to_the_cookie_name(self):
        """防线 1（tornado 提供）：A 的签名值放到 B 的 cookie 名下必须解码失败。

        注意：本条**不是** `flow['provider']` 那行的守卫——把它变异掉本条仍会
        通过。它钉住的是「不同 provider 的 cookie 互不通用」这一性质本身。
        """
        req = FakeRequest()
        req.save_flow(PROVIDER_A, fresh_flow(provider=PROVIDER_A))
        req._cookies[_flow_cookie_name(PROVIDER_B)] = req._cookies[_flow_cookie_name(PROVIDER_A)]

        with self.assertRaises(Exception) as ctx:
            req.load_flow(PROVIDER_B)
        self.assertEqual(getattr(ctx.exception, 'code', None), 'state_mismatch')

    def test_flow_provider_field_mismatch_is_rejected(self):
        """防线 2（本模块逻辑）：payload 自称的 provider 与请求的 provider 不符 → 拒绝。

        cookie 是在 **B 的名下**签发的，所以签名校验会正常通过；此时唯一能拦下
        它的就是 `flow['provider'] != provider_id`。把那一行变异成 `if False:`
        后本条会变红（已实测）——它才是该防线的守卫。
        """
        req = FakeRequest()
        flow = fresh_flow(provider=PROVIDER_A)
        req.save_flow(PROVIDER_B, flow)  # 存在 B 名下，但 payload 写着 A
        with self.assertRaises(Exception) as ctx:
            req.load_flow(PROVIDER_B)
        self.assertEqual(getattr(ctx.exception, 'code', None), 'state_mismatch')

    def test_flow_for_same_provider_still_loads(self):
        """负例对照：provider 一致时必须能加载，证明上面不是「一律拒绝」。"""
        req = FakeRequest()
        req.save_flow(PROVIDER_B, fresh_flow(provider=PROVIDER_B))
        self.assertEqual(req.load_flow(PROVIDER_B)['provider'], PROVIDER_B)


# --------------------------------------------------------------------------
# (a) H1 回归 —— email_unverified 门禁
# --------------------------------------------------------------------------


class TestEmailVerifiedGate(unittest.TestCase):
    """无既有绑定时，只有 `email_verified is True` 才允许自动绑定。

    门禁位置：`OidcCallbackHandler._handle_login` 的
    `if email_verified is not True: return redirect('/login?oidc_error=email_unverified')`。
    """

    def _setup(self):
        """一个「一切就绪、只差 email_verified」的世界。

        用户 alice 的 email 与 id_token 里的 email 一致，因此**一旦门禁被绕过，
        自动绑定就会真的发生**（redirect 到 /my/ 且写入 user_oidc）——门禁的
        有无有可观察的行为差异，而不是都落到某个无关分支。
        """
        db = FakeDB(users=[make_user()])
        req = FakeRequest(current_user=None, db=db)
        return req, db

    def _assert_gated(self, req, db, email_verified):
        run(req._handle_login(PROVIDER_A, 'sub-1', 'alice@example.test', email_verified))
        self.assertEqual(
            req.last_redirect, '/login?oidc_error=email_unverified',
            'email_verified 非严格布尔真时必须被门禁拦下',
        )
        self.assertEqual(db.user_oidc.added, [], '被门禁拦下时绝不能写 user_oidc')
        self.assertEqual(req.secure_cookies, {}, '被门禁拦下时绝不能建立会话')
        self.assertEqual(db.transactions, [], '被门禁拦下时绝不能开启绑定事务')

    def test_false_is_rejected(self):
        req, db = self._setup()
        self._assert_gated(req, db, False)

    def test_missing_claim_is_rejected(self):
        """claim 缺失时 `claims.get('email_verified')` 返回 None → 必须拒绝。"""
        req, db = self._setup()
        self._assert_gated(req, db, None)

    def test_string_true_is_rejected(self):
        """字符串 `'true'` 不是布尔真，fail-safe 拒绝。"""
        req, db = self._setup()
        self._assert_gated(req, db, 'true')

    def test_int_one_is_rejected(self):
        """整数 1 也不是布尔真（`1 is not True`）——同样 fail-safe 拒绝。"""
        req, db = self._setup()
        self._assert_gated(req, db, 1)

    def test_boolean_true_proceeds_to_auto_bind(self):
        """布尔真才继续：按 email 匹配既有账号并建立绑定 + 会话。"""
        req, db = self._setup()
        run(req._handle_login(PROVIDER_A, 'sub-1', 'alice@example.test', True))
        self.assertEqual(req.last_redirect, '/my/')
        self.assertEqual(len(db.user_oidc.added), 1)
        added = db.user_oidc.added[0]
        self.assertEqual(added['userid'], 1)
        self.assertEqual(added['provider'], PROVIDER_A)
        self.assertEqual(added['subject'], 'sub-1')
        self.assertEqual(added['email'], 'alice@example.test')
        self.assertIn('user', req.secure_cookies, '通过门禁后必须建立会话')

    def test_gate_is_reached_before_user_lookup(self):
        """门禁必须在「按 email 查账号」之前生效。

        用一个 email 根本不存在于本地的场景做对照：若门禁在前，错误码是
        `email_unverified`；若门禁被移到查账号之后，错误码会变成 `no_account`。
        这条断言把门禁的**位置**也钉住了，而不只是它的存在。
        """
        db = FakeDB(users=[])  # 本地没有任何账号
        req = FakeRequest(current_user=None, db=db)
        run(req._handle_login(PROVIDER_A, 'sub-1', 'nobody@example.test', False))
        self.assertEqual(req.last_redirect, '/login?oidc_error=email_unverified')

    def test_email_missing_is_reported_before_the_verified_gate(self):
        """email 缺失优先报 email_missing（契约 §5.2 的顺序）。"""
        db = FakeDB(users=[make_user()])
        req = FakeRequest(current_user=None, db=db)
        run(req._handle_login(PROVIDER_A, 'sub-1', None, True))
        self.assertEqual(req.last_redirect, '/login?oidc_error=email_missing')
        self.assertEqual(db.user_oidc.added, [])


# --------------------------------------------------------------------------
# (d) H4 —— bind flow 的 userid 绑定
# --------------------------------------------------------------------------


class TestBindUseridBinding(unittest.TestCase):
    """mode='bind' 的 flow 里 userid 必须与会话用户一致。"""

    def test_mismatched_userid_is_rejected(self):
        """会话用户 id=2，flow 里 userid=1 → 必须拒绝，且不写任何绑定。"""
        db = FakeDB(users=[make_user(uid=1), make_user(uid=2, email='bob@example.test')])
        req = FakeRequest(current_user=make_user(uid=2, email='bob@example.test'), db=db)
        flow = fresh_flow(provider=PROVIDER_A, mode='bind', userid=1)

        run(req._handle_bind(PROVIDER_A, 'sub-bob', 'bob@example.test', flow))

        self.assertEqual(req.last_redirect, '/oidc/manage?oidc_error=state_mismatch')
        self.assertEqual(db.user_oidc.added, [], 'userid 不匹配时绝不能写 user_oidc')
        self.assertEqual(db.transactions, [], 'userid 不匹配时绝不能开启事务')

    def test_missing_session_user_is_rejected(self):
        """未登录（current_user 为 None）时即使 flow 带 userid 也必须拒绝。"""
        db = FakeDB(users=[make_user(uid=1)])
        req = FakeRequest(current_user=None, db=db)
        flow = fresh_flow(provider=PROVIDER_A, mode='bind', userid=1)

        run(req._handle_bind(PROVIDER_A, 'sub-1', 'alice@example.test', flow))

        self.assertEqual(req.last_redirect, '/oidc/manage?oidc_error=state_mismatch')
        self.assertEqual(db.user_oidc.added, [])

    def test_flow_without_userid_is_rejected(self):
        """flow 里 userid 为 None → 拒绝。"""
        db = FakeDB(users=[make_user(uid=1)])
        req = FakeRequest(current_user=make_user(uid=1), db=db)
        flow = fresh_flow(provider=PROVIDER_A, mode='bind', userid=None)

        run(req._handle_bind(PROVIDER_A, 'sub-1', 'alice@example.test', flow))

        self.assertEqual(req.last_redirect, '/oidc/manage?oidc_error=state_mismatch')
        self.assertEqual(db.user_oidc.added, [])

    def test_matching_userid_binds_successfully(self):
        """负例对照：userid 一致时必须真的绑定成功，证明上面不是「一律拒绝」。"""
        db = FakeDB(users=[make_user(uid=1)])
        req = FakeRequest(current_user=make_user(uid=1), db=db)
        flow = fresh_flow(provider=PROVIDER_A, mode='bind', userid=1)

        run(req._handle_bind(PROVIDER_A, 'sub-1', 'alice@example.test', flow))

        self.assertEqual(req.last_redirect, '/oidc/manage')
        self.assertEqual(len(db.user_oidc.added), 1)
        self.assertEqual(db.user_oidc.added[0]['userid'], 1)
        self.assertEqual(db.user_oidc.added[0]['subject'], 'sub-1')

    def test_binding_owned_by_other_user_is_rejected(self):
        """subject 已被别人绑走 → bound_by_other（与 userid 绑定是两条独立防线）。"""
        db = FakeDB(
            users=[make_user(uid=1), make_user(uid=2, email='bob@example.test')],
            bindings=[{'id': 9, 'userid': 1, 'provider': PROVIDER_A, 'subject': 'sub-bob'}],
        )
        req = FakeRequest(current_user=make_user(uid=2, email='bob@example.test'), db=db)
        flow = fresh_flow(provider=PROVIDER_A, mode='bind', userid=2)

        run(req._handle_bind(PROVIDER_A, 'sub-bob', 'bob@example.test', flow))

        self.assertEqual(req.last_redirect, '/oidc/manage?oidc_error=bound_by_other')
        self.assertEqual(db.user_oidc.added, [])


class TestSupportFixtureSanity(unittest.TestCase):
    """夹具自检：确认 support 模块的 provider/claims 形态没变。"""

    def test_support_provider_shape(self):
        p = support.provider()
        self.assertEqual(p['id'], 'keycloak')
        self.assertEqual(p['issuer'], support.ISSUER)

    def test_flow_ttl_is_positive(self):
        self.assertGreater(OIDC_FLOW_TTL, 0)


if __name__ == '__main__':
    unittest.main()
