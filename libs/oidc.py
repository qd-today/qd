#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Created on 2026-11-07

'''
OIDC (OpenID Connect) 核心逻辑

- 发现文档 / JWKS 获取与进程内缓存
- 授权 URL 构造 (强制 PKCE S256)
- 授权码换 token (client_secret_post / client_secret_basic)
- id_token 校验 (python-jose, 显式算法白名单)

本模块不处理任何 Web 路由与 Cookie, 由 web/handlers/oidc.py 负责。
'''

import asyncio
import base64
import hashlib
import json
import secrets
import time
from urllib.parse import urlencode

import aiohttp
from jose import jwk as jose_jwk
from jose import jwt as jose_jwt
from jose.exceptions import JOSEError

import config
from libs.log import Log

logger_oidc = Log('QD.OIDC').getlogger()

# 允许的 id_token 签名算法白名单: 只接受非对称签名, 明确排除 none / HS* / PS*。
# 排除 PS* 的原因: python-jose 3.5.0 的 ALGORITHMS.SUPPORTED 不含 PS* (RSA_DS 只有
# RS256/RS384/RS512), jws 预检直接抛 JWSError: Algorithm PS256 not supported ——
# 换任何 backend 都一样; 而绕过 jose 用底层 pycryptodome 自建 PSS 校验属于手搓,
# 换成支持 PS* 的库则必然拉入 cryptography (见 pyproject.toml 的架构约束)。
SUPPORTED_ID_TOKEN_ALGS = frozenset(
    (
        'RS256', 'RS384', 'RS512',
        'ES256', 'ES384', 'ES512',
    )
)

# 发现文档 / JWKS 缓存 TTL (秒)
METADATA_CACHE_TTL = 3600
JWKS_CACHE_TTL = 3600

DEFAULT_TIMEOUT = 15.0
MAX_RESPONSE_BYTES = 1024 * 1024


class OidcError(Exception):
    '''
    OIDC 流程错误

    code 取值:
        provider_not_found / discovery_failed / metadata_invalid /
        token_exchange_failed / invalid_id_token / nonce_mismatch /
        email_missing / invalid_response / state_mismatch ...
    '''

    def __init__(self, code, message=None):
        self.code = code
        self.message = message or code
        super().__init__(self.message)

    def __str__(self):
        return '%s: %s' % (self.code, self.message)


# ===================== PKCE =====================


def _b64url_nopad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def generate_pkce_pair():
    '''生成 PKCE (code_verifier, code_challenge), 使用 S256 方式。'''
    code_verifier = _b64url_nopad(secrets.token_bytes(32))
    return code_verifier, pkce_challenge(code_verifier)


def pkce_challenge(code_verifier: str) -> str:
    '''按 RFC 7636 S256 计算 code_challenge。'''
    if not code_verifier:
        raise OidcError('invalid_request', 'code_verifier is empty')
    digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
    return _b64url_nopad(digest)


def generate_state():
    return _b64url_nopad(secrets.token_bytes(24))


def generate_nonce():
    return _b64url_nopad(secrets.token_bytes(24))


# ===================== 进程内缓存 =====================

_metadata_cache = {}  # provider_id -> {'data': dict, 'ts': float}
_metadata_locks = {}  # provider_id -> asyncio.Lock
_jwks_cache = {}  # jwks_uri -> {'data': dict, 'ts': float}
_jwks_locks = {}  # jwks_uri -> asyncio.Lock


def _cache_get(cache, key, ttl):
    entry = cache.get(key)
    if not entry:
        return None
    if (time.time() - entry['ts']) >= ttl:
        return None
    return entry['data']


def _cache_put(cache, key, data):
    cache[key] = {'data': data, 'ts': time.time()}


def _get_lock(locks, key):
    lock = locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        locks[key] = lock
    return lock


async def _http_get_json(url):
    '''GET 一个 JSON 文档, 失败抛 OidcError(invalid_response), 不泄漏上游正文。'''
    timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise OidcError(
                        'invalid_response',
                        'unexpected status %s from %s' % (resp.status, url),
                    )
                raw = await resp.content.read(MAX_RESPONSE_BYTES + 1)
    except OidcError:
        raise
    except Exception as e:
        raise OidcError('invalid_response', '%s: %s' % (url, e)) from e

    if len(raw) > MAX_RESPONSE_BYTES:
        raise OidcError('invalid_response', 'response too large from %s' % url)
    try:
        data = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as e:
        raise OidcError('invalid_response', 'invalid JSON from %s: %s' % (url, e)) from e
    if not isinstance(data, dict):
        raise OidcError('invalid_response', 'JSON body from %s is not an object' % url)
    return data


async def _http_post_form_json(url, data, auth=None):
    '''POST application/x-www-form-urlencoded, 返回 JSON; 不泄漏上游正文。'''
    timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, data=data, auth=auth) as resp:
                raw = await resp.content.read(MAX_RESPONSE_BYTES + 1)
                status = resp.status
    except Exception as e:
        raise OidcError('token_exchange_failed', '%s: %s' % (url, e)) from e

    if len(raw) > MAX_RESPONSE_BYTES:
        raise OidcError('token_exchange_failed', 'response too large from %s' % url)
    try:
        payload = json.loads(raw.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        raise OidcError(
            'token_exchange_failed',
            'non-JSON token response (status %s)' % status,
        )
    if not isinstance(payload, dict):
        raise OidcError('token_exchange_failed', 'token response is not an object')
    if status != 200 or 'error' in payload:
        # 只回传 error / error_description, 不透传完整正文
        err = payload.get('error') or ('http_%s' % status)
        desc = payload.get('error_description') or ''
        raise OidcError('token_exchange_failed', '%s %s' % (err, desc))
    return payload


# ===================== 发现文档 =====================


def _validate_metadata(provider, metadata):
    issuer = metadata.get('issuer')
    if not isinstance(issuer, str) or not issuer:
        raise OidcError('metadata_invalid', 'discovery document has no issuer')
    expected_issuer = (provider.get('issuer') or '').rstrip('/')
    if issuer.rstrip('/') != expected_issuer:
        raise OidcError(
            'metadata_invalid',
            'discovery issuer mismatch (expected %s)' % expected_issuer,
        )
    for key in ('authorization_endpoint', 'token_endpoint', 'jwks_uri'):
        value = metadata.get(key)
        if not isinstance(value, str) or not value:
            raise OidcError('metadata_invalid', 'discovery document has no %s' % key)
    return metadata


async def get_provider_metadata(provider, force=False):
    '''获取并缓存 OIDC 发现文档 (进程内缓存, TTL 见 METADATA_CACHE_TTL)。'''
    provider_id = provider['id']
    if not force:
        cached = _cache_get(_metadata_cache, provider_id, METADATA_CACHE_TTL)
        if cached is not None:
            return cached

    async with _get_lock(_metadata_locks, provider_id):
        if not force:
            cached = _cache_get(_metadata_cache, provider_id, METADATA_CACHE_TTL)
            if cached is not None:
                return cached
        issuer = (provider.get('issuer') or '').rstrip('/')
        if not issuer:
            raise OidcError('provider_not_found', 'provider %s has no issuer' % provider_id)
        url = issuer + '/.well-known/openid-configuration'
        try:
            metadata = await _http_get_json(url)
        except OidcError as e:
            raise OidcError('discovery_failed', 'discovery of %s failed: %s' % (provider_id, e.message)) from e
        _validate_metadata(provider, metadata)
        _cache_put(_metadata_cache, provider_id, metadata)
        return metadata


# ===================== JWKS =====================


async def _get_jwks(metadata, force=False):
    jwks_uri = metadata['jwks_uri']
    if not force:
        cached = _cache_get(_jwks_cache, jwks_uri, JWKS_CACHE_TTL)
        if cached is not None:
            return cached

    async with _get_lock(_jwks_locks, jwks_uri):
        if not force:
            cached = _cache_get(_jwks_cache, jwks_uri, JWKS_CACHE_TTL)
            if cached is not None:
                return cached
        jwks = await _http_get_json(jwks_uri)
        if not isinstance(jwks.get('keys'), list) or not jwks['keys']:
            raise OidcError('invalid_id_token', 'jwks_uri returned no keys')
        _cache_put(_jwks_cache, jwks_uri, jwks)
        return jwks


def _select_key(jwks, kid):
    keys = jwks.get('keys') or []
    if kid:
        for key in keys:
            if key.get('kid') == kid:
                return key
        return None
    # 无 kid: 仅当集合中只有一个 key 时才可用
    if len(keys) == 1:
        return keys[0]
    return None


# ===================== 授权 URL =====================


def build_authorize_url(provider, metadata, state, nonce, redirect_uri, code_challenge):
    '''构造授权端点 URL, 强制 PKCE S256。'''
    params = {
        'response_type': 'code',
        'client_id': provider['client_id'],
        'redirect_uri': redirect_uri,
        'scope': provider.get('scopes') or 'openid profile email',
        'state': state,
        'nonce': nonce,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }
    return metadata['authorization_endpoint'] + '?' + urlencode(params)


# ===================== 授权码换 token =====================


async def exchange_code(provider, metadata, code, redirect_uri, code_verifier):
    '''用授权码换取 token, 返回 token 响应 dict。'''
    if not code:
        raise OidcError('invalid_request', 'authorization code is empty')

    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': provider['client_id'],
        'client_secret': provider['client_secret'],
        'code_verifier': code_verifier,
    }

    supported = metadata.get('token_endpoint_auth_methods_supported')
    use_basic = False
    if isinstance(supported, list) and supported:
        # 只有明确不支持 client_secret_post 时才退化到 HTTP Basic
        if 'client_secret_post' not in supported and 'client_secret_basic' in supported:
            use_basic = True

    if use_basic:
        auth = aiohttp.BasicAuth(provider['client_id'], provider['client_secret'])
        data.pop('client_id', None)
        data.pop('client_secret', None)
        return await _http_post_form_json(metadata['token_endpoint'], data, auth=auth)

    return await _http_post_form_json(metadata['token_endpoint'], data)


# ===================== id_token 校验 =====================


def _resolve_algorithms(provider, metadata):
    supported = metadata.get('id_token_signing_alg_values_supported')
    if isinstance(supported, list) and supported:
        allowlist = [alg for alg in supported if alg in SUPPORTED_ID_TOKEN_ALGS]
    else:
        allowlist = sorted(SUPPORTED_ID_TOKEN_ALGS)
    if not allowlist:
        raise OidcError('invalid_id_token', 'no supported id_token signing algorithm')
    return allowlist


async def verify_id_token(provider, metadata, id_token, jwks, nonce, access_token=None):
    '''
    校验 id_token 并返回 claims。

    - jwks 非 None 时直接使用 (不做网络请求), 否则按 metadata['jwks_uri'] 获取
    - 未知 kid 时强制刷新一次 JWKS 再试
    - 任何失败抛 OidcError
    '''
    if not isinstance(id_token, str) or not id_token:
        raise OidcError('invalid_id_token', 'missing id_token')

    try:
        header = jose_jwt.get_unverified_header(id_token)
    except JOSEError as e:
        raise OidcError('invalid_id_token', 'unparsable id_token header: %s' % e) from e

    alg = header.get('alg')
    kid = header.get('kid')
    allowlist = _resolve_algorithms(provider, metadata)
    if alg not in allowlist:
        raise OidcError('invalid_id_token', 'disallowed id_token alg: %s' % alg)

    if jwks is not None:
        jwks_sets = [jwks]
    else:
        jwks_sets = [await _get_jwks(metadata)]
        if _select_key(jwks_sets[0], kid) is None:
            # 未知 kid: 强制刷新一次
            jwks_sets.append(await _get_jwks(metadata, force=True))

    key_data = None
    for jwks_set in jwks_sets:
        key_data = _select_key(jwks_set, kid)
        if key_data is not None:
            break
    if key_data is None:
        raise OidcError('invalid_id_token', 'no matching JWKS key for kid')

    try:
        key = jose_jwk.construct(key_data, alg)
    except JOSEError as e:
        raise OidcError('invalid_id_token', 'cannot construct JWKS key: %s' % e) from e

    options = {
        'require_exp': True,
        'require_iat': False,
        'require_nbf': False,
        # 允许 60s 时钟偏差: python-jose 的 leeway 只能通过 options 传入
        # (jose/jwt.py `leeway = options.get("leeway", 0)`), 写成
        # decode(..., leeway=60) 关键字参数会被忽略。仅作用于 exp/nbf。
        'leeway': 60,
        'verify_aud': True,
        'verify_iat': True,
        'verify_exp': True,
        'verify_nbf': True,
        'verify_iss': True,
        'verify_at_hash': True,
    }
    try:
        claims = jose_jwt.decode(
            id_token,
            key,
            algorithms=allowlist,
            options=options,
            audience=provider['client_id'],
            issuer=(provider.get('issuer') or '').rstrip('/'),
            access_token=access_token,
        )
    except JOSEError as e:
        raise OidcError('invalid_id_token', 'id_token verification failed: %s' % e) from e

    # nonce: 恒定时间比较
    token_nonce = claims.get('nonce')
    if not isinstance(token_nonce, str) or not secrets.compare_digest(token_nonce, nonce or ''):
        raise OidcError('nonce_mismatch', 'nonce does not match')

    # aud 多值时必须校验 azp == client_id
    aud = claims.get('aud')
    if isinstance(aud, list) and len(aud) > 1:
        if claims.get('azp') != provider['client_id']:
            raise OidcError('invalid_id_token', 'azp does not match client_id')

    sub = claims.get('sub')
    if not isinstance(sub, str) or not sub:
        raise OidcError('invalid_id_token', 'sub is missing or not a string')
    # 规范化: utf8mb4_bin 是 PAD SPACE 比较器, 'ABC' 与 'ABC ' 在唯一键上仍会冲突,
    # 且尾随空格会形成两个视觉相同、语义不同的绑定身份。拒绝任何首尾空白。
    if sub != sub.strip():
        raise OidcError('invalid_id_token', 'sub has leading/trailing whitespace')

    return claims
