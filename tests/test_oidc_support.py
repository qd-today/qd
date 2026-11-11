# -*- coding: utf-8 -*-
"""OIDC 单元测试的共享夹具（供 tests/test_oidc_*.py 导入）。

本模块同时也承载**针对 `libs/oidc.py` 内部纯函数**的测试（见文件末尾的
`TestValidateMetadataIssuer`），因为这类私有函数没有更合适的归属文件。

设计要点：
- 全部离线：自己用 `rsa` 生成 RSA 密钥、用 `python-jose` 构造本地 JWKS 与签名
  id_token，绝不访问真实 IdP（那是 e2e 的活）。这样 claim 校验矩阵可以确定性复现。
- provider / metadata / jwks 都是**普通 dict**（契约 §4.4 的入参形态），
  所以测试不需要网络、不需要真实 discovery。
- provider 配置校验发生在 `config.py` 导入期，本进程内的 `config` 已经被
  别的模块导入过、无法安全重载，因此用**子进程**探测（见 `config_probe`）。
"""
import base64
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import rsa  # noqa: E402
from jose import jwk, jwt  # noqa: E402

# 测试用常量
ISSUER = 'https://idp.example.test/realms/qd'
CLIENT_ID = 'qd-test-client'
CLIENT_SECRET = 'qd-test-secret'
REDIRECT_URI = 'http://qd.example.test/oidc/keycloak/callback'
JWKS_URI = 'http://127.0.0.1:1/jwks'  # 故意指向必然拒绝连接的端口：若实现尝试联网刷新会立刻失败而不是挂住


def b64url(raw: bytes) -> str:
    """base64url 无填充编码（JWT / PKCE 都用它）。"""
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def s256(verifier: str) -> str:
    """独立实现的 PKCE S256：base64url(sha256(ascii(verifier)))，无填充。"""
    return b64url(hashlib.sha256(verifier.encode('ascii')).digest())


def make_rsa_key(kid: str = 'test-kid-1'):
    """生成一把 2048 位 RSA 私钥，返回 (private_pem, public_jwk_dict)。"""
    _pub, priv = rsa.newkeys(2048)
    key = jwk.construct(priv.save_pkcs1(), algorithm='RS256')
    public = key.public_key().to_dict()
    public.update({'kid': kid, 'use': 'sig', 'alg': 'RS256'})
    return priv.save_pkcs1().decode('ascii'), public


def make_ec_key(kid: str = 'test-ec-1'):
    """生成一把 P-256 EC 私钥，返回 (private_pem, public_jwk_dict)。"""
    from ecdsa import NIST256p, SigningKey
    sk = SigningKey.generate(curve=NIST256p)
    pem = sk.to_pem().decode('ascii')
    key = jwk.construct(pem, algorithm='ES256')
    public = key.public_key().to_dict()
    public.update({'kid': kid, 'use': 'sig', 'alg': 'ES256'})
    return pem, public


def jwks_doc(*public_keys) -> dict:
    return {'keys': [dict(k) for k in public_keys]}


def provider(**overrides) -> dict:
    """契约 §3.1 的 provider 配置字典。"""
    data = {
        'id': 'keycloak',
        'name': 'Keycloak',
        'issuer': ISSUER,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scopes': 'openid profile email',
        'icon': '',
        'enabled': True,
    }
    data.update(overrides)
    return data


def metadata(**overrides) -> dict:
    """契约 §4.1 的 discovery 元数据（已校验通过的形态）。"""
    data = {
        'issuer': ISSUER,
        'authorization_endpoint': f'{ISSUER}/protocol/openid-connect/auth',
        'token_endpoint': f'{ISSUER}/protocol/openid-connect/token',
        'jwks_uri': JWKS_URI,
        'id_token_signing_alg_values_supported': ['RS256', 'ES256'],
        'token_endpoint_auth_methods_supported': ['client_secret_post', 'client_secret_basic'],
    }
    data.update(overrides)
    return data


def claims(**overrides) -> dict:
    """一份「全部合法」的 id_token claim 集合。"""
    now = int(time.time())
    data = {
        'iss': ISSUER,
        'aud': CLIENT_ID,
        'sub': 'user-subject-1',
        'nonce': 'test-nonce-1',
        'exp': now + 300,
        'iat': now,
        'email': 'alice@example.test',
        'email_verified': True,
    }
    data.update(overrides)
    return data


def sign(private_pem: str, payload: dict, kid: str = 'test-kid-1', algorithm: str = 'RS256') -> str:
    return jwt.encode(payload, private_pem, algorithm=algorithm, headers={'kid': kid})


def unsigned_token(payload: dict, kid: str = 'test-kid-1') -> str:
    """手工构造 alg=none 的 token（python-jose 拒绝签发它，只能手搓）。"""
    header = {'alg': 'none', 'typ': 'JWT', 'kid': kid}
    return f'{b64url(json.dumps(header).encode())}.{b64url(json.dumps(payload).encode())}.'


def hs256_confusion_token(payload: dict, rsa_public_pem: str, kid: str = 'test-kid-1') -> str:
    """经典算法混淆攻击：header 声称 HS256，用 RSA **公钥 PEM** 当 HMAC 密钥签名。

    python-jose 在签发侧就拒绝把非对称 PEM 当 HMAC secret（JWKError），
    所以这里手工按 JWS 规范算 HMAC——这正是攻击者会做的事。
    若被测实现把公钥当 HMAC secret 且把 HS256 放进白名单，这个 token 会被验通过。
    """
    header = {'alg': 'HS256', 'typ': 'JWT', 'kid': kid}
    signing_input = (
        f'{b64url(json.dumps(header).encode())}.{b64url(json.dumps(payload).encode())}'
    ).encode('ascii')
    signature = hmac.new(rsa_public_pem.encode('ascii'), signing_input, hashlib.sha256).digest()
    return f'{signing_input.decode("ascii")}.{b64url(signature)}'


def config_probe(oidc_providers_env, extra_env=None, timeout=120):
    """在**子进程**里以给定 OIDC_PROVIDERS 导入 config，回报实际取值。

    返回 (returncode, parsed_json_or_None, stderr_text)。
    必须用子进程：config 的 provider 校验发生在导入期，本进程里 config 已被
    其他测试模块导入，reload 会污染全局状态。
    """
    snippet = (
        'import json, sys;'
        'sys.path.insert(0, %r);'
        'import config;'
        'print("__PROBE__" + json.dumps({'
        '"oidc_providers": list(getattr(config, "oidc_providers", [])),'
        '"enabled": list(config.get_enabled_providers()),'
        '}, ensure_ascii=False, default=str))'
    ) % ROOT
    env = dict(os.environ)
    env.pop('OIDC_PROVIDERS', None)
    if oidc_providers_env is not None:
        env['OIDC_PROVIDERS'] = oidc_providers_env
    env.update(extra_env or {})
    proc = subprocess.run(
        [sys.executable, '-c', snippet],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout,
    )
    parsed = None
    for line in proc.stdout.splitlines():
        if line.startswith('__PROBE__'):
            parsed = json.loads(line[len('__PROBE__'):])
            break
    return proc.returncode, parsed, proc.stderr


def repo_file(relative_path: str) -> str:
    return os.path.join(ROOT, relative_path)


def oidc_module():
    """导入 libs/oidc.py；若文件尚不存在则让调用方 skip。

    注意：**只**在文件缺失时跳过。文件存在但导入失败（缺依赖/语法错）必须
    以 ImportError 暴露出来，绝不能被 skip 掩盖。
    """
    import unittest
    if not os.path.exists(repo_file('libs/oidc.py')):
        raise unittest.SkipTest('libs/oidc.py 尚未实现（task-1 未完成）')
    from libs import oidc
    return oidc


# ===================== 发现文档 issuer 校验 =====================
#
# 独立 reviewer 的 LOW-1：`libs/oidc.py` 的 `_validate_metadata` 此前零覆盖
# ——把 issuer 校验那一行变异成 `if False:`，全量测试仍 GREEN。
#
# 这条校验的安全含义：发现文档是从 `provider['issuer'] + '/.well-known/...'`
# 抓来的，若不核对文档里自称的 `issuer`，一个被劫持/配错的 discovery 端点
# 就能让后续所有 claim 校验以**攻击者选定的 issuer** 为基准，iss 校验形同虚设。


class TestValidateMetadataIssuer(unittest.TestCase):
    """`_validate_metadata` 的 issuer 核对（含尾斜杠正常化）。"""

    def setUp(self):
        self.oidc = oidc_module()

    def test_matching_issuer_passes(self):
        """负例对照：issuer 一致时必须通过，证明下面不是「一律拒绝」。"""
        md = self.oidc._validate_metadata(provider(), metadata())
        self.assertEqual(md['issuer'], ISSUER)

    def test_trailing_slash_on_metadata_issuer_is_normalized(self):
        """metadata issuer 多一个尾斜杠 → 正常化后一致，必须通过。"""
        self.oidc._validate_metadata(provider(), metadata(issuer=ISSUER + '/'))

    def test_trailing_slash_on_provider_issuer_is_normalized(self):
        """provider 配置里的 issuer 带尾斜杠 → 也必须能匹配无斜杠的文档 issuer。"""
        self.oidc._validate_metadata(provider(issuer=ISSUER + '/'), metadata())

    def test_mismatched_issuer_is_rejected(self):
        """文档自称的 issuer 与配置不一致 → metadata_invalid。"""
        with self.assertRaises(self.oidc.OidcError) as ctx:
            self.oidc._validate_metadata(
                provider(), metadata(issuer='https://evil.example.test/realms/qd')
            )
        self.assertEqual(ctx.exception.code, 'metadata_invalid')

    def test_issuer_prefix_extension_is_rejected(self):
        """前缀相同但更长（`.../qd-extra`）也必须拒绝，不能靠前缀匹配放行。"""
        with self.assertRaises(self.oidc.OidcError) as ctx:
            self.oidc._validate_metadata(provider(), metadata(issuer=ISSUER + '-extra'))
        self.assertEqual(ctx.exception.code, 'metadata_invalid')

    def test_issuer_case_difference_is_rejected(self):
        """issuer 大小写不同不算一致（不做大小写折叠）。"""
        with self.assertRaises(self.oidc.OidcError) as ctx:
            self.oidc._validate_metadata(
                provider(), metadata(issuer=ISSUER.replace('idp', 'IDP'))
            )
        self.assertEqual(ctx.exception.code, 'metadata_invalid')

    def test_missing_issuer_is_rejected(self):
        md = metadata()
        del md['issuer']
        with self.assertRaises(self.oidc.OidcError) as ctx:
            self.oidc._validate_metadata(provider(), md)
        self.assertEqual(ctx.exception.code, 'metadata_invalid')

    def test_empty_issuer_is_rejected(self):
        with self.assertRaises(self.oidc.OidcError) as ctx:
            self.oidc._validate_metadata(provider(), metadata(issuer=''))
        self.assertEqual(ctx.exception.code, 'metadata_invalid')

    def test_non_string_issuer_is_rejected(self):
        for bad in (None, 123, ['https://idp.example.test/realms/qd']):
            with self.subTest(issuer=bad):
                with self.assertRaises(self.oidc.OidcError) as ctx:
                    self.oidc._validate_metadata(provider(), metadata(issuer=bad))
                self.assertEqual(ctx.exception.code, 'metadata_invalid')

    def test_missing_required_endpoint_is_rejected(self):
        """issuer 通过后仍要校验三个必需端点——issuer 校验不是唯一的把关。"""
        for key in ('authorization_endpoint', 'token_endpoint', 'jwks_uri'):
            with self.subTest(missing=key):
                md = metadata()
                del md[key]
                with self.assertRaises(self.oidc.OidcError) as ctx:
                    self.oidc._validate_metadata(provider(), md)
                self.assertEqual(ctx.exception.code, 'metadata_invalid')


if __name__ == '__main__':
    unittest.main()
