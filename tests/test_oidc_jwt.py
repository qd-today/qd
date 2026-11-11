# -*- coding: utf-8 -*-
"""id_token 校验矩阵（契约 §4.4 / §7.2-1）。

全部离线：本地生成 RSA/EC 密钥、自建 JWKS、本地签名。每个拒绝用例都必须抛
`OidcError`；同时必须有一个「完全合法」的 token 被接受——否则拒绝矩阵可能只是
实现整体坏了（假阳性防线）。
"""
import os
import sys
import time
import unittest

# tests/ 不是包：直接跑单个模块时，本目录要自己进 sys.path 才能 import 支撑模块。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_oidc_support import (CLIENT_ID, ISSUER, b64url, claims,  # noqa: E402
                               hs256_confusion_token, jwks_doc, make_ec_key,
                               make_rsa_key, metadata, oidc_module, provider,
                               sign, unsigned_token)

NONCE = 'test-nonce-1'
ACCESS_TOKEN = 'an-access-token-value'

# 哨兵：区分「没传 token（用默认签名）」与「显式传 None（必须被拒）」。
_UNSET = object()


def _at_hash(access_token, algorithm='RS256'):
    """按 OIDC Core 独立实现 at_hash：哈希左半 + base64url 无填充。"""
    import hashlib
    algo = {'256': hashlib.sha256, '384': hashlib.sha384, '512': hashlib.sha512}
    digest = algo[algorithm[-3:]](access_token.encode('utf-8')).digest()
    return b64url(digest[:len(digest) // 2])


class IdTokenTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oidc = oidc_module()
        cls.private_pem, cls.public_jwk = make_rsa_key('test-kid-1')
        cls.other_private_pem, cls.other_public_jwk = make_rsa_key('other-kid')
        cls.ec_private_pem, cls.ec_public_jwk = make_ec_key('test-ec-1')
        cls.jwks = jwks_doc(cls.public_jwk, cls.other_public_jwk, cls.ec_public_jwk)

    def setUp(self):
        self.provider = provider()
        self.metadata = metadata()

    # -- helpers --

    def verify(self, payload, nonce=NONCE, access_token=None, jwks=None,
               metadata=None, provider=None, token=_UNSET):
        """同步包一层 asyncio，返回 claims 或抛出 OidcError。"""
        import asyncio
        if token is _UNSET:
            token = sign(self.private_pem, payload, 'test-kid-1')
        return asyncio.run(self.oidc.verify_id_token(
            provider if provider is not None else self.provider,
            metadata if metadata is not None else self.metadata,
            token,
            self.jwks if jwks is None else jwks,
            nonce,
            access_token,
        ))

    def assert_rejected(self, payload=None, token=_UNSET, **kwargs):
        """断言校验失败且抛的是 OidcError（而不是 KeyError/AttributeError 之类）。"""
        with self.assertRaises(self.oidc.OidcError) as ctx:
            self.verify(claims() if payload is None else payload, token=token, **kwargs)
        return ctx.exception

    # ==================== 正向：合法 token 必须被接受 ====================

    def test_valid_token_is_accepted(self):
        """拒绝矩阵的对照项：完全合法的 id_token 必须通过。"""
        result = self.verify(claims())
        self.assertIsInstance(result, dict)
        self.assertEqual(result['sub'], 'user-subject-1')
        self.assertEqual(result['iss'], ISSUER)
        self.assertEqual(result['aud'], CLIENT_ID)
        self.assertEqual(result['nonce'], NONCE)

    def test_valid_token_with_aud_list_and_matching_azp(self):
        result = self.verify(claims(aud=[CLIENT_ID, 'another-client'], azp=CLIENT_ID))
        self.assertEqual(result['sub'], 'user-subject-1')

    def test_valid_token_with_correct_at_hash(self):
        result = self.verify(
            claims(at_hash=_at_hash(ACCESS_TOKEN)), access_token=ACCESS_TOKEN)
        self.assertEqual(result['sub'], 'user-subject-1')

    def test_valid_token_without_at_hash_claim(self):
        """at_hash 是 OPTIONAL：token 没带就不该强求。"""
        result = self.verify(claims(), access_token=ACCESS_TOKEN)
        self.assertEqual(result['sub'], 'user-subject-1')

    def test_valid_es256_token_is_accepted(self):
        token = sign(self.ec_private_pem, claims(), 'test-ec-1', algorithm='ES256')
        result = self.verify(claims(), token=token)
        self.assertEqual(result['sub'], 'user-subject-1')

    # ==================== 拒绝矩阵 ====================

    def test_wrong_issuer_is_rejected(self):
        e = self.assert_rejected(claims(iss='https://evil.example.test'))
        self.assertEqual(e.code, 'invalid_id_token')

    def test_issuer_with_different_case_is_rejected(self):
        self.assert_rejected(claims(iss=ISSUER.upper()))

    def test_wrong_audience_is_rejected(self):
        e = self.assert_rejected(claims(aud='some-other-client'))
        self.assertEqual(e.code, 'invalid_id_token')

    def test_audience_list_not_containing_client_id_is_rejected(self):
        self.assert_rejected(claims(aud=['a', 'b'], azp=CLIENT_ID))

    def test_multi_aud_without_azp_is_rejected(self):
        """契约 §4.4：aud 多值时 azp 必须等于 client_id。"""
        e = self.assert_rejected(claims(aud=[CLIENT_ID, 'another-client']))
        self.assertEqual(e.code, 'invalid_id_token')

    def test_multi_aud_with_wrong_azp_is_rejected(self):
        self.assert_rejected(claims(aud=[CLIENT_ID, 'another-client'], azp='someone-else'))

    def test_wrong_nonce_is_rejected(self):
        e = self.assert_rejected(claims(nonce='a-different-nonce'))
        self.assertEqual(e.code, 'nonce_mismatch')

    def test_nonce_of_different_length_is_rejected(self):
        """非等长 nonce 也必须拒绝（恒定时间比较不得因此短路放行）。"""
        self.assert_rejected(claims(nonce=NONCE + '-extra'))

    def test_missing_nonce_claim_is_rejected(self):
        payload = claims()
        payload.pop('nonce')
        e = self.assert_rejected(payload)
        self.assertEqual(e.code, 'nonce_mismatch')

    def test_non_string_nonce_is_rejected(self):
        self.assert_rejected(claims(nonce=12345))

    def test_expired_token_is_rejected(self):
        """已过期远超 leeway(60s) 的 token 必须被拒。

        注意偏移量取 360s 而非原来的 60s: 引入 `'leeway': 60` 后,
        `exp == now - 60` 恰好落在容忍边界上(python-jose `if exp < (now - leeway)`
        对相等取假), 那正是新用例 `test_boundary_exp_expired_59s_accepted_61s_rejected`
        专门钉住的边界。本条只负责「明显过期必拒」, 故取远离边界的值。
        """
        e = self.assert_rejected(claims(exp=int(time.time()) - 360))
        self.assertEqual(e.code, 'invalid_id_token')

    def test_missing_exp_is_rejected(self):
        """契约 §4.4：exp 必须存在（require_exp）。"""
        payload = claims()
        payload.pop('exp')
        self.assert_rejected(payload)

    def test_token_expiring_far_in_the_future_is_still_valid(self):
        """对照：只有「已过期」才该拒，未来时间点不能误杀。"""
        self.verify(claims(exp=int(time.time()) + 86400))

    def test_algorithm_confusion_hs256_signed_with_rsa_public_key_is_rejected(self):
        """经典算法混淆：HS256 + RSA 公钥 PEM 当 HMAC 密钥。

        这是 §4.4 白名单存在的唯一理由——若实现把 HS256 放进白名单并把公钥当
        HMAC secret，攻击者即可伪造任意 id_token。
        """
        token = hs256_confusion_token(claims(), self.public_jwk_pem(), 'test-kid-1')
        e = self.assert_rejected(token=token)
        self.assertEqual(e.code, 'invalid_id_token')

    def public_jwk_pem(self):
        """把 RSA 公钥还原成 PEM（攻击者用 JWKS 里的 n/e 即可自行拼出）。"""
        from jose import jwk
        return jwk.construct(dict(self.public_jwk), 'RS256').to_pem().decode('ascii')

    def test_hs256_rejected_even_if_discovery_advertises_it(self):
        """发现文档谎报支持 HS256 时，白名单取交集后仍必须拒绝。"""
        md = metadata(id_token_signing_alg_values_supported=['HS256', 'RS256'])
        token = hs256_confusion_token(claims(), self.public_jwk_pem(), 'test-kid-1')
        e = self.assert_rejected(token=token, metadata=md)
        self.assertEqual(e.code, 'invalid_id_token')

    def test_hs256_with_oct_jwks_key_is_rejected_by_the_allowlist_alone(self):
        """**白名单的隔离用例**：JWKS 里就有一把对称 `oct` 密钥、发现文档也宣称 HS256。

        这条之所以必要：上面那条用 RSA 公钥当 HMAC secret 的混淆用例，即使白名单被
        放宽到包含 HS256，也会因为 python-jose 拒绝用 RSA JWK 构造 HMAC 密钥
        （`Incorrect key type. Expected: 'oct', Received: RSA`）而仍然失败——
        也就是说它无法区分「白名单在拦」和「jose 在拦」。这里给一把类型正确的
        `oct` 密钥，jose 会愉快地验签成功，于是**只有白名单能拦下它**。
        实测：把 HS256 塞进 SUPPORTED_ID_TOKEN_ALGS 后，本用例与
        `test_allowlist_never_contains_hs_or_none` 共 2 条变红；其中本用例是
        **唯一**能证明「拦截确实来自白名单、而非 jose 的密钥类型检查」的那条
        （策略断言只读常量集合，不经过任何 token 验证路径）。
        """
        import hashlib
        import hmac
        import json

        secret = b'a-symmetric-hmac-secret'
        oct_jwk = {
            'kty': 'oct',
            'k': b64url(secret),
            'kid': 'oct-kid',
            'alg': 'HS256',
            'use': 'sig',
        }
        header = {'alg': 'HS256', 'typ': 'JWT', 'kid': 'oct-kid'}
        signing_input = (
            f'{b64url(json.dumps(header).encode())}.'
            f'{b64url(json.dumps(claims()).encode())}'
        ).encode('ascii')
        signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
        token = f'{signing_input.decode("ascii")}.{b64url(signature)}'

        md = metadata(id_token_signing_alg_values_supported=['HS256', 'RS256'])
        e = self.assert_rejected(token=token, jwks={'keys': [oct_jwk]}, metadata=md)
        self.assertEqual(e.code, 'invalid_id_token')
        self.assertIn('alg', str(e.message).lower())

    def test_only_unsupported_algs_advertised_is_rejected(self):
        """发现文档只报 HS*/none 时，白名单为空——必须整体拒绝而不是放行。"""
        md = metadata(id_token_signing_alg_values_supported=['HS256', 'none'])
        e = self.assert_rejected(metadata=md)
        self.assertEqual(e.code, 'invalid_id_token')

    def test_alg_none_is_rejected(self):
        """alg=none 的无签名 token（python-jose 拒签，只能手搓）。"""
        e = self.assert_rejected(token=unsigned_token(claims(), 'test-kid-1'))
        self.assertEqual(e.code, 'invalid_id_token')

    def test_alg_none_rejected_even_when_discovery_advertises_none(self):
        """发现文档宣称支持 `none` 时也必须拒绝——白名单是本地固定策略，
        不能被 IdP 的自述扩大。"""
        md = metadata(id_token_signing_alg_values_supported=['none', 'RS256'])
        e = self.assert_rejected(token=unsigned_token(claims(), 'test-kid-1'), metadata=md)
        self.assertEqual(e.code, 'invalid_id_token')

    def test_allowlist_never_contains_hs_or_none(self):
        """**策略断言**：白名单常量必须恰好是契约 §4.4（修正后）的 6 个算法。

        这条是直接钉住契约声明，而不是靠某个 token 的行为间接推断；即使 jose
        因别的原因（如密钥类型不符）恰好也拦住了，这里仍会独立报警。

        §4.4 修正后移除了 PS256/PS384/PS512：python-jose 3.5.0 的
        `ALGORITHMS.SUPPORTED` 不含任何 PS*（`jws` 预检直接抛
        `JWSError: Algorithm PS256 not supported`），原宣称属过度承诺。
        下面的 PS* 子断言把「不得重新宣称 PS*」单独钉住——即便有人日后把
        白名单整体改回 9 元，也会在这里先炸。
        """
        allowlist = set(self.oidc.SUPPORTED_ID_TOKEN_ALGS)
        self.assertNotIn('none', allowlist)
        self.assertEqual([a for a in allowlist if a.startswith('HS')], [],
                         'HMAC 算法绝不能进入 id_token 白名单（算法混淆）')
        self.assertEqual([a for a in allowlist if a.startswith('PS')], [],
                         'python-jose 3.5.0 的 ALGORITHMS.SUPPORTED 不含 PS*，不得列入白名单')
        self.assertEqual(
            allowlist,
            {'RS256', 'RS384', 'RS512', 'ES256', 'ES384', 'ES512'},
            '白名单必须与契约 §4.4（修正后：移除 PS*）完全一致',
        )

    def test_unknown_kid_is_rejected(self):
        token = sign(self.private_pem, claims(), 'no-such-kid')
        e = self.assert_rejected(token=token)
        self.assertEqual(e.code, 'invalid_id_token')

    def test_kid_absent_with_multiple_keys_is_rejected(self):
        """无 kid 时集合里有多把 key：不能瞎猜，必须拒。"""
        token = sign(self.private_pem, claims(), '')
        self.assert_rejected(token=token)

    def test_signature_from_a_different_key_is_rejected(self):
        """kid 指向集合内的另一把公钥，但用别的私钥签名 —— 签名必须验失败。"""
        token = sign(self.other_private_pem, claims(), 'test-kid-1')
        self.assert_rejected(token=token)

    def test_wrong_at_hash_is_rejected(self):
        e = self.assert_rejected(
            claims(at_hash=_at_hash('a-completely-different-access-token')),
            access_token=ACCESS_TOKEN)
        self.assertEqual(e.code, 'invalid_id_token')

    def test_at_hash_without_access_token_is_rejected(self):
        """token 带 at_hash 但调用方没给 access_token：不能跳过校验。"""
        self.assert_rejected(claims(at_hash=_at_hash(ACCESS_TOKEN)))

    def test_missing_sub_is_rejected(self):
        payload = claims()
        payload.pop('sub')
        e = self.assert_rejected(payload)
        self.assertEqual(e.code, 'invalid_id_token')

    def test_non_string_sub_is_rejected(self):
        self.assert_rejected(claims(sub=12345))

    def test_empty_sub_is_rejected(self):
        e = self.assert_rejected(claims(sub=''))
        self.assertEqual(e.code, 'invalid_id_token')

    def test_sub_with_leading_or_trailing_whitespace_is_rejected(self):
        """utf8mb4_bin 是 PAD SPACE 比较器：'ABC' 与 'ABC ' 在唯一键上会互相冲突
        （真实 MariaDB 实测 1062 Duplicate entry），且会形成两个视觉相同、语义不同的
        绑定身份。因此必须在应用层拒绝任何首尾空白，而不是依赖 DB 层比较器。"""
        for bad in ('user-subject-1 ', ' user-subject-1', 'user-subject-1\t',
                    'user-subject-1\n', '\tuser-subject-1 '):
            with self.subTest(sub=bad):
                e = self.assert_rejected(claims(sub=bad))
                self.assertEqual(e.code, 'invalid_id_token')

    def test_sub_with_inner_whitespace_is_still_accepted(self):
        """只拒绝首尾空白 —— 内部空白是 sub 的合法内容，不得误伤。"""
        result = self.verify(claims(sub='user subject 1'))
        self.assertEqual(result['sub'], 'user subject 1')

    def test_garbage_token_is_rejected(self):
        self.assert_rejected(token='not-a-jwt-at-all')

    def test_empty_token_is_rejected(self):
        self.assert_rejected(token='')

    def test_none_token_is_rejected(self):
        self.assert_rejected(token=None)

    def test_tampered_payload_is_rejected(self):
        """改一位 payload（保留原签名）必须被签名校验拦下。"""
        token = sign(self.private_pem, claims(), 'test-kid-1')
        head, payload, sig = token.split('.')
        tampered = claims(sub='attacker-subject')
        forged = f'{head}.{b64url(__import__("json").dumps(tampered).encode())}.{sig}'
        self.assert_rejected(token=forged)

    # ==================== JWKS 获取路径 ====================

    def test_jwks_none_falls_back_to_network_and_fails_closed(self):
        """jwks=None 时实现会去 jwks_uri 取 —— 夹具把该地址指向必然拒绝连接的端口，
        所以必须快速失败成 OidcError，而不是挂住或静默放行。"""
        import asyncio
        with self.assertRaises(self.oidc.OidcError) as ctx:
            asyncio.run(self.oidc.verify_id_token(
                self.provider, self.metadata,
                sign(self.private_pem, claims(), 'test-kid-1'),
                None, NONCE))
        self.assertIn(ctx.exception.code, ('invalid_id_token', 'invalid_response'))

    def test_empty_jwks_key_set_is_rejected(self):
        e = self.assert_rejected(jwks={'keys': []})
        self.assertEqual(e.code, 'invalid_id_token')

    # ==================== 返回结构 ====================

    def test_returns_claims_verbatim(self):
        result = self.verify(claims(email='alice@example.test', email_verified=True))
        self.assertEqual(result['email'], 'alice@example.test')
        self.assertIs(result['email_verified'], True)


class LeewayTest(unittest.TestCase):
    """时钟偏差容忍窗口（契约 §4.4 / 评论行内 libs/oidc.py:379）。

    python-jose 的 `leeway` **只能**通过 `options` 传入
    （`jose/jwt.py` 里 `leeway = options.get("leeway", 0)`），写成
    `decode(..., leeway=60)` 关键字参数会被直接忽略——实现里已在
    `options` 字典内声明 `'leeway': 60`。它只作用于 `exp`
    （`if exp < (now - leeway)`）与 `nbf`（`if nbf > (now + leeway)`），
    `_validate_iat` 只检查 iat 是整数。

    本类全部驱动**真实的** `libs.oidc.verify_id_token`，不 mock 校验逻辑。
    """

    @classmethod
    def setUpClass(cls):
        cls.oidc = oidc_module()
        cls.private_pem, cls.public_jwk = make_rsa_key('test-kid-1')
        cls.jwks = jwks_doc(cls.public_jwk)

    def setUp(self):
        self.provider = provider()
        self.metadata = metadata()

    def verify(self, payload):
        import asyncio
        token = sign(self.private_pem, payload, 'test-kid-1')
        return asyncio.run(self.oidc.verify_id_token(
            self.provider, self.metadata, token, self.jwks, NONCE))

    def assert_rejected(self, payload):
        with self.assertRaises(self.oidc.OidcError) as ctx:
            self.verify(payload)
        return ctx.exception

    def test_exp_expired_30s_is_accepted_with_leeway(self):
        """(a) 刚过期 30s：在 60s 容忍窗口内，必须接受。"""
        now = int(time.time())
        result = self.verify(claims(exp=now - 30, iat=now - 330))
        self.assertEqual(result['sub'], 'user-subject-1')

    def test_exp_expired_120s_is_rejected_even_with_leeway(self):
        """(b) 过期 120s：超出容忍窗口，必须仍然拒绝。"""
        now = int(time.time())
        e = self.assert_rejected(claims(exp=now - 120, iat=now - 420))
        self.assertEqual(e.code, 'invalid_id_token')

    def test_nbf_30s_in_the_future_is_accepted_with_leeway(self):
        """(c) nbf 在未来 30s：本机时钟偏慢的场景，必须接受。"""
        now = int(time.time())
        result = self.verify(claims(exp=now + 300, iat=now, nbf=now + 30))
        self.assertEqual(result['sub'], 'user-subject-1')

    def test_nbf_120s_in_the_future_is_rejected_even_with_leeway(self):
        """(d) nbf 在未来 120s：超出容忍窗口，必须仍然拒绝。"""
        now = int(time.time())
        e = self.assert_rejected(claims(exp=now + 300, iat=now, nbf=now + 120))
        self.assertEqual(e.code, 'invalid_id_token')

    def test_boundary_exp_expired_59s_accepted_61s_rejected(self):
        """边界对照：窗口内(59s)接受，窗口外(61s)拒绝——证明容忍是 60s 而非无限。"""
        now = int(time.time())
        self.verify(claims(exp=now - 59, iat=now - 359))
        self.assert_rejected(claims(exp=now - 61, iat=now - 361))


if __name__ == '__main__':
    unittest.main()
