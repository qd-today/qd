# -*- coding: utf-8 -*-
"""PKCE 与授权 URL 的测试（契约 §4.2 / §4.3 / §7.2-2）。

判据：
- `code_challenge` 必须等于**测试里独立实现**的 S256 值，而不是与实现互证。
- 必须是 S256（不是 plain，也不是缺省）。
- verifier 必须高熵、每次调用都不同。
"""
import base64
import hashlib
import os
import sys
import unittest
from urllib.parse import parse_qs, urlparse

# tests/ 不是包：直接跑单个模块时，本目录要自己进 sys.path 才能 import 支撑模块。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_oidc_support import (ISSUER, REDIRECT_URI, metadata, oidc_module,  # noqa: E402
                               provider, s256)


def _oidc():
    return oidc_module()


class TestPkce(unittest.TestCase):
    def setUp(self):
        self.oidc = _oidc()

    def test_s256_matches_independent_implementation(self):
        verifier = 'dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'  # RFC 7636 附录 B 的样例
        expected = 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM'
        self.assertEqual(s256(verifier), expected, '测试自身的 S256 实现有误')
        self.assertEqual(self.oidc.pkce_challenge(verifier), expected)

    def test_s256_random_verifiers(self):
        for _ in range(50):
            verifier, challenge = self.oidc.generate_pkce_pair()
            with self.subTest(verifier=verifier):
                self.assertEqual(
                    challenge, s256(verifier),
                    'code_challenge 必须等于 base64url(sha256(verifier))',
                )

    def test_challenge_has_no_padding_and_is_base64url(self):
        _, challenge = self.oidc.generate_pkce_pair()
        self.assertNotIn('=', challenge, 'PKCE challenge 不得带 base64 填充')
        self.assertRegex(challenge, r'^[A-Za-z0-9_-]+$', 'challenge 必须是 base64url 字符集')
        self.assertEqual(len(challenge), 43, 'sha256 摘要的 base64url 长度固定 43')

    def test_challenge_is_sha256_length(self):
        verifier, challenge = self.oidc.generate_pkce_pair()
        decoded = base64.urlsafe_b64decode(challenge + '=' * (-len(challenge) % 4))
        self.assertEqual(len(decoded), 32)
        self.assertEqual(decoded, hashlib.sha256(verifier.encode('ascii')).digest())

    def test_verifier_meets_rfc7636_entropy(self):
        """RFC 7636: verifier 长度 43-128，字符集 unreserved。"""
        seen = set()
        for _ in range(100):
            verifier, _ = self.oidc.generate_pkce_pair()
            with self.subTest(verifier=verifier):
                self.assertGreaterEqual(len(verifier), 43)
                self.assertLessEqual(len(verifier), 128)
                self.assertRegex(verifier, r'^[A-Za-z0-9\-._~]+$')
            seen.add(verifier)
        self.assertEqual(len(seen), 100, 'code_verifier 必须每次调用都唯一')

    def test_verifier_is_high_entropy(self):
        verifiers = [self.oidc.generate_pkce_pair()[0] for _ in range(200)]
        unique_chars = set(''.join(verifiers))
        self.assertGreater(len(unique_chars), 40, 'verifier 熵过低，字符分布过窄')

    def test_empty_verifier_is_rejected(self):
        with self.assertRaises(self.oidc.OidcError):
            self.oidc.pkce_challenge('')

    def test_challenge_differs_from_verifier(self):
        verifier, challenge = self.oidc.generate_pkce_pair()
        self.assertNotEqual(challenge, verifier, '不得退化成 plain 方式')


class TestAuthorizeUrl(unittest.TestCase):
    def setUp(self):
        self.oidc = _oidc()
        self.provider = provider()
        self.metadata = metadata()

    def _params(self, url):
        return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}

    def test_url_targets_authorization_endpoint(self):
        url = self.oidc.build_authorize_url(
            self.provider, self.metadata, 'state-1', 'nonce-1', REDIRECT_URI, 'challenge-1')
        parsed = urlparse(url)
        base = urlparse(self.metadata['authorization_endpoint'])
        self.assertEqual((parsed.scheme, parsed.netloc, parsed.path),
                         (base.scheme, base.netloc, base.path))

    def test_required_params(self):
        url = self.oidc.build_authorize_url(
            self.provider, self.metadata, 'state-1', 'nonce-1', REDIRECT_URI, 'challenge-1')
        params = self._params(url)
        self.assertEqual(params['response_type'], 'code')
        self.assertEqual(params['client_id'], self.provider['client_id'])
        self.assertEqual(params['redirect_uri'], REDIRECT_URI)
        self.assertEqual(params['state'], 'state-1')
        self.assertEqual(params['nonce'], 'nonce-1')
        self.assertEqual(params['scope'], 'openid profile email')
        self.assertEqual(params['code_challenge'], 'challenge-1')
        self.assertEqual(params['code_challenge_method'], 'S256')

    def test_code_challenge_equals_s256_of_generated_verifier(self):
        verifier, challenge = self.oidc.generate_pkce_pair()
        url = self.oidc.build_authorize_url(
            self.provider, self.metadata, 's', 'n', REDIRECT_URI, challenge)
        params = self._params(url)
        self.assertEqual(params['code_challenge'], s256(verifier))
        self.assertEqual(params['code_challenge_method'], 'S256')

    def test_never_uses_plain_method(self):
        url = self.oidc.build_authorize_url(
            self.provider, self.metadata, 's', 'n', REDIRECT_URI, 'c')
        self.assertNotEqual(self._params(url).get('code_challenge_method'), 'plain')

    def test_client_secret_is_not_in_the_url(self):
        url = self.oidc.build_authorize_url(
            self.provider, self.metadata, 's', 'n', REDIRECT_URI, 'c')
        self.assertNotIn(self.provider['client_secret'], url)

    def test_scope_defaults_when_provider_has_none(self):
        bare = provider()
        bare.pop('scopes')
        url = self.oidc.build_authorize_url(bare, self.metadata, 's', 'n', REDIRECT_URI, 'c')
        self.assertEqual(self._params(url)['scope'], 'openid profile email')

    def test_custom_scope_is_respected(self):
        custom = provider(scopes='openid email')
        url = self.oidc.build_authorize_url(custom, self.metadata, 's', 'n', REDIRECT_URI, 'c')
        self.assertEqual(self._params(url)['scope'], 'openid email')

    def test_state_and_nonce_are_unique_per_call(self):
        states = {self.oidc.generate_state() for _ in range(100)}
        nonces = {self.oidc.generate_nonce() for _ in range(100)}
        self.assertEqual(len(states), 100)
        self.assertEqual(len(nonces), 100)
        self.assertRegex(next(iter(states)), r'^[A-Za-z0-9_-]+$')

    def test_authorization_endpoint_issuer_matches_config(self):
        """授权端点必须来自 metadata，且 metadata 的 issuer 与配置一致（防混淆）。"""
        self.assertEqual(self.metadata['issuer'], ISSUER)
        self.assertTrue(self.metadata['authorization_endpoint'].startswith(ISSUER))


if __name__ == '__main__':
    unittest.main()
