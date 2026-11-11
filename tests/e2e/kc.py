#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Keycloak admin helper for the QD OIDC E2E harness.

Creates a dedicated realm/client/user in the already-running Keycloak
container `nexus-kc-test` (127.0.0.1:8095, admin/admin).  Only ever touches
the realm named by REALM (default `qd-test`) - existing realms are left alone.

Run directly to (re)create the fixture:

    .venv/bin/python tests/e2e/kc.py setup
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
import urllib.parse
import urllib.request

import requests

KC_BASE = os.environ.get("KC_BASE", "http://127.0.0.1:8095")
KC_ADMIN = os.environ.get("KC_ADMIN", "admin")
KC_ADMIN_PASSWORD = os.environ.get("KC_ADMIN_PASSWORD", "admin")
REALM = os.environ.get("KC_REALM", "qd-test")
CLIENT_ID = os.environ.get("KC_CLIENT_ID", "qd-e2e")
# Fixed so the harness is reproducible; override with KC_CLIENT_SECRET.
CLIENT_SECRET = os.environ.get("KC_CLIENT_SECRET", "qd-e2e-secret-0123456789")
TEST_USER = os.environ.get("KC_USER", "qduser")
TEST_USER_PASSWORD = os.environ.get("KC_USER_PASSWORD", "qd-user-pass-123")
TEST_USER_EMAIL = os.environ.get("KC_USER_EMAIL", "qduser@example.test")

# Fixture for the auto-bind email-trust gate (CONTRACT.md §5.2 / §7.11):
# an IdP identity that is otherwise perfect -- it carries an `email` matching a
# local QD account -- but whose mailbox the IdP has NOT verified.  The gate must
# refuse to auto-bind it.
UNVERIFIED_USER = os.environ.get("KC_UNVERIFIED_USER", "qdunverified")
UNVERIFIED_USER_PASSWORD = os.environ.get(
    "KC_UNVERIFIED_USER_PASSWORD", "qd-unverified-pass-123"
)
UNVERIFIED_USER_EMAIL = os.environ.get(
    "KC_UNVERIFIED_USER_EMAIL", "unverified-target@example.test"
)

# 127.0.0.1 is a loopback address, so Keycloak never requires HTTPS for it.
REDIRECT_URI = os.environ.get(
    "KC_REDIRECT_URI", "http://127.0.0.1:8791/oidc/keycloak/callback"
)


class KcError(RuntimeError):
    pass


def _request(method, url, body=None, headers=None, form=False, expect=None):
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode()
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(body).encode()
            hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=30) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
    if expect is not None and status != expect:
        raise KcError(f"{method} {url} -> {status} (expected {expect}): {raw[:500]!r}")
    if status >= 400:
        raise KcError(f"{method} {url} -> {status}: {raw[:500]!r}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return raw.decode("utf-8", "replace")


def admin_token():
    return _request(
        "POST",
        f"{KC_BASE}/realms/master/protocol/openid-connect/token",
        {
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": KC_ADMIN,
            "password": KC_ADMIN_PASSWORD,
        },
        form=True,
    )["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def realm_exists(token):
    realms = _request("GET", f"{KC_BASE}/admin/realms", headers=_h(token))
    return any(r["realm"] == REALM for r in realms)


def setup_realm(force=False):
    """Create (or recreate) the E2E realm.  Never touches other realms."""
    token = admin_token()
    if realm_exists(token):
        if not force:
            return {"realm": REALM, "created": False}
        _request("DELETE", f"{KC_BASE}/admin/realms/{REALM}", headers=_h(token))
        for _ in range(30):
            if not realm_exists(token):
                break
            time.sleep(0.5)
    _request(
        "POST",
        f"{KC_BASE}/admin/realms",
        {"realm": REALM, "enabled": True, "sslRequired": "none"},
        headers=_h(token),
        expect=201,
    )
    token = admin_token()

    # Keycloak 26 hard-codes `Secure` on its login-session cookies and never
    # accepts HTTPS-less loopback for that attribute.  A same-site `Lax`
    # policy is what a browser needs for the cross-site top-level redirect
    # back to QD; it is also what the harness's manual cookie jar emulates.
    realm = _request("GET", f"{KC_BASE}/admin/realms/{REALM}", headers=_h(token))
    attrs = realm.get("attributes", {})
    attrs["samesite"] = "Lax"
    _request(
        "PUT",
        f"{KC_BASE}/admin/realms/{REALM}",
        {"realm": REALM, "attributes": attrs},
        headers=_h(token),
        expect=204,
    )

    # confidential client, authorization-code flow, PKCE S256
    _request(
        "POST",
        f"{KC_BASE}/admin/realms/{REALM}/clients",
        {
            "clientId": CLIENT_ID,
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "secret": CLIENT_SECRET,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": False,
            "redirectUris": [REDIRECT_URI],
            "webOrigins": [],
            "attributes": {"pkce.code.challenge.method": "S256"},
        },
        headers=_h(token),
        expect=201,
    )

    # test user with known password + email
    _request(
        "POST",
        f"{KC_BASE}/admin/realms/{REALM}/users",
        {
            "username": TEST_USER,
            "enabled": True,
            "email": TEST_USER_EMAIL,
            "emailVerified": True,
            "firstName": "QD",
            "lastName": "E2E",
            "credentials": [
                {"type": "password", "value": TEST_USER_PASSWORD, "temporary": False}
            ],
        },
        headers=_h(token),
        expect=201,
    )
    return {"realm": REALM, "created": True}


def discovery():
    return _request(
        "GET", f"{KC_BASE}/realms/{REALM}/.well-known/openid-configuration"
    )


def ensure_unverified_user(email=UNVERIFIED_USER_EMAIL,
                           username=UNVERIFIED_USER,
                           password=UNVERIFIED_USER_PASSWORD):
    """Idempotently ensure an `emailVerified: false` Keycloak user.

    Idempotent by construction: look the user up first and only POST when it is
    absent, so repeated runs never fail and the realm is never recreated (other
    fixtures live in it).  If the user already exists we *assert* the two
    properties this fixture exists for (email match, unverified mailbox) and
    repair them in place, so a stale realm cannot silently turn the gate test
    into a vacuous one.

    Returns the Keycloak user id.
    """
    token = admin_token()
    url = f"{KC_BASE}/admin/realms/{REALM}/users"
    found = _request("GET", f"{url}?username={urllib.parse.quote(username)}",
                     headers=_h(token))
    if found:
        user = found[0]
        uid = user["id"]
        patch = {}
        if user.get("email") != email:
            patch["email"] = email
        if user.get("emailVerified") is not False:
            patch["emailVerified"] = False
        if not user.get("enabled"):
            patch["enabled"] = True
        if patch:
            _request("PUT", f"{url}/{uid}", patch, headers=_h(token), expect=204)
        return uid

    _request(
        "POST",
        url,
        {
            "username": username,
            "enabled": True,
            "email": email,
            # The whole point of the fixture: the mailbox is NOT verified.
            "emailVerified": False,
            "firstName": "Unverified",
            "lastName": "E2E",
            "credentials": [
                {"type": "password", "value": password, "temporary": False}
            ],
        },
        headers=_h(token),
        expect=201,
    )
    found = _request("GET", f"{url}?username={urllib.parse.quote(username)}",
                     headers=_h(token))
    if not found:
        raise KcError(f"user {username!r} vanished right after creation")
    return found[0]["id"]


def provider_config(provider_id="keycloak", redirect_port=8791):
    """The OIDC_PROVIDERS entry for the QD app under test."""
    global REDIRECT_URI
    if redirect_port != 8791:
        REDIRECT_URI = f"http://127.0.0.1:{redirect_port}/oidc/{provider_id}/callback"
    return {
        "id": provider_id,
        "name": "Keycloak E2E",
        "issuer": f"{KC_BASE}/realms/{REALM}",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }


def new_state():
    return secrets.token_urlsafe(24)


class IdpSession:
    """A requests session with a cookie jar that keeps `Secure` cookies on http.

    Keycloak always sets `Secure` on its auth-session cookies.  `requests`
    (2.34.x) / `http.cookiejar` refuse to *send* such a cookie over plain
    http, so the login POST would be rejected with "Cookie not found".
    Loopback http is not an insecure transport here, so we keep a tiny
    manual jar instead.  The browser-side equivalent of the same fix is the
    realm `samesite=Lax` attribute set in `setup_realm`.
    """

    def __init__(self, timeout=30):
        self._s = requests.Session()
        self._s.trust_env = False  # never use the host http_proxy for loopback
        self._jar = {}
        self.timeout = timeout

    def _absorb(self, resp):
        for key, value in resp.raw.headers.items():
            if key.lower() != "set-cookie":
                continue
            pair = value.split(";", 1)[0]
            name, _, val = pair.partition("=")
            self._jar[name.strip()] = val.strip()

    def _headers(self):
        if not self._jar:
            return {}
        return {"Cookie": "; ".join(f"{k}={v}" for k, v in self._jar.items())}

    def _merge_headers(self, extra):
        headers = self._headers()
        if extra:
            headers.update(extra)
        return headers

    def get(self, url, **kw):
        kw.setdefault("allow_redirects", True)
        kw.setdefault("timeout", self.timeout)
        headers = self._merge_headers(kw.pop("headers", None))
        resp = self._s.get(url, headers=headers, **kw)
        self._absorb(resp)
        return resp

    def post(self, url, data=None, **kw):
        kw.setdefault("allow_redirects", False)
        kw.setdefault("timeout", self.timeout)
        headers = self._merge_headers(kw.pop("headers", None))
        resp = self._s.post(url, data=data, headers=headers, **kw)
        self._absorb(resp)
        return resp

    def login_form_action(self, html_text):
        import html as _html
        import re as _re

        m = _re.search(r'action="([^"]*login-actions/authenticate[^"]*)"', html_text)
        if not m:
            m = _re.search(r'<form[^>]+id="kc-form-login"[^>]+action="([^"]+)"', html_text)
        if not m:
            raise KcError("Keycloak login form action not found")
        return _html.unescape(m.group(1))

    def authorize_and_login(self, auth_url, username, password):
        """Drive authorize -> login form -> POST credentials; return the callback URL.

        If the jar already holds a Keycloak SSO session (or the realm is
        configured with an idle SSO session) the authorize call short-circuits
        with a 302 straight back to the redirect_uri; that is returned as-is.
        """
        page = self.get(auth_url, allow_redirects=False)
        if page.status_code in (302, 303):
            return page.headers.get("Location", "")
        if page.status_code != 200:
            raise KcError(f"authorize GET -> {page.status_code}")
        resp = self.post(
            self.login_form_action(page.text),
            data={"username": username, "password": password, "credentialId": ""},
        )
        if resp.status_code not in (302, 303):
            raise KcError(f"login POST -> {resp.status_code}: {resp.text[:300]!r}")
        return resp.headers.get("Location", "")

    def logout(self):
        """Drop the Keycloak SSO session held by this jar (best effort)."""
        try:
            self.get(f"{KC_BASE}/realms/{REALM}/protocol/openid-connect/logout")
        except Exception:
            pass
        self._jar.clear()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "setup"
    if cmd == "setup":
        force = "--force" in sys.argv
        print(json.dumps(setup_realm(force=force), indent=2))
        d = discovery()
        print(json.dumps({k: d[k] for k in ("issuer", "authorization_endpoint",
                                            "token_endpoint", "jwks_uri")}, indent=2))
    elif cmd == "discovery":
        print(json.dumps(discovery(), indent=2))
    else:
        raise SystemExit(f"unknown command {cmd!r}")
