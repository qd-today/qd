#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase A probe: drive the Keycloak authorization-code + PKCE flow with raw HTTP.

This validates the IdP side and the harness *before* the QD app exists.
It deliberately does NOT use any QD product code.

    .venv/bin/python tests/e2e/kc_flow_probe.py
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kc  # noqa: E402
from jose import jwt as jose_jwt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE_DIR = os.environ.get(
    "E2E_EVIDENCE", os.path.join(HERE, "..", "..", ".team", "e2e")
)
REDIRECT_URI = kc.REDIRECT_URI
PROVIDER_ID = "keycloak"


def pkce_pair():
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


def build_auth_url(meta, state, nonce, challenge):
    return meta["authorization_endpoint"] + "?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": kc.CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile email",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })


def main():
    evidence = {}
    s = kc.IdpSession()
    meta = kc.discovery()
    evidence["discovery"] = {
        k: meta.get(k)
        for k in ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri",
                  "token_endpoint_auth_methods_supported",
                  "id_token_signing_alg_values_supported")
    }

    state = kc.new_state()
    nonce = kc.new_state()
    verifier, challenge = pkce_pair()
    auth_url = build_auth_url(meta, state, nonce, challenge)

    loc = s.authorize_and_login(auth_url, kc.TEST_USER, kc.TEST_USER_PASSWORD)
    evidence["authorize_and_login"] = {"callback_url": loc}
    assert loc.startswith(REDIRECT_URI), f"unexpected redirect: {loc}"
    q = urllib.parse.parse_qs(urllib.parse.urlparse(loc).query)
    evidence["callback_query"] = {"state_matches": q.get("state", [""])[0] == state,
                                  "has_code": bool(q.get("code"))}
    assert q.get("state", [""])[0] == state
    code = q["code"][0]

    # ---- token exchange (client_secret_post) -------------------------------
    tok = s.post(meta["token_endpoint"], data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": kc.CLIENT_ID,
        "client_secret": kc.CLIENT_SECRET,
        "code_verifier": verifier,
    })
    evidence["token_exchange"] = {"status": tok.status_code}
    assert tok.status_code == 200, (tok.status_code, tok.text[:500])
    tokens = tok.json()
    evidence["token_exchange"]["token_type"] = tokens.get("token_type")
    evidence["token_exchange"]["has_id_token"] = bool(tokens.get("id_token"))

    # ---- token exchange with HTTP Basic (client_secret_basic) --------------
    # proves both auth methods the contract requires are supported by the IdP
    state_b = kc.new_state()
    nonce_b = kc.new_state()
    verifier_b, challenge_b = pkce_pair()
    loc_b = s.authorize_and_login(build_auth_url(meta, state_b, nonce_b, challenge_b),
                                  kc.TEST_USER, kc.TEST_USER_PASSWORD)
    code_b = urllib.parse.parse_qs(urllib.parse.urlparse(loc_b).query)["code"][0]
    basic = base64.b64encode(f"{kc.CLIENT_ID}:{kc.CLIENT_SECRET}".encode()).decode()
    tok_b = s.post(meta["token_endpoint"], data={
        "grant_type": "authorization_code", "code": code_b,
        "redirect_uri": REDIRECT_URI, "code_verifier": verifier_b,
    }, headers={"Authorization": f"Basic {basic}"})
    evidence["token_exchange_basic"] = {"status": tok_b.status_code}
    assert tok_b.status_code == 200, (tok_b.status_code, tok_b.text[:500])

    # ---- verify the id_token against the real JWKS -------------------------
    jwks = s.get(meta["jwks_uri"]).json()
    header = jose_jwt.get_unverified_header(tokens["id_token"])
    key = next((k for k in jwks["keys"] if k.get("kid") == header.get("kid")), None)
    assert key, f"kid {header.get('kid')} not in JWKS"
    claims = jose_jwt.decode(
        tokens["id_token"], key, algorithms=["RS256"], audience=kc.CLIENT_ID,
        issuer=meta["issuer"], access_token=tokens.get("access_token"),
    )
    evidence["id_token"] = {
        "header": header,
        "claims": {k: claims.get(k) for k in
                   ("iss", "aud", "sub", "email", "email_verified", "nonce", "azp", "exp")},
        "nonce_matches": claims.get("nonce") == nonce,
        "sub": claims.get("sub"),
        "email": claims.get("email"),
    }
    assert claims["nonce"] == nonce
    assert claims["iss"] == meta["issuer"]

    # ---- negatives ---------------------------------------------------------
    replay = s.post(meta["token_endpoint"], data={
        "grant_type": "authorization_code", "code": code,
        "redirect_uri": REDIRECT_URI, "client_id": kc.CLIENT_ID,
        "client_secret": kc.CLIENT_SECRET, "code_verifier": verifier})
    evidence["code_replay"] = {"status": replay.status_code}
    assert replay.status_code == 400, replay.status_code

    state2 = kc.new_state()
    nonce2 = kc.new_state()
    _v2, c2 = pkce_pair()
    loc2 = s.authorize_and_login(build_auth_url(meta, state2, nonce2, c2),
                                 kc.TEST_USER, kc.TEST_USER_PASSWORD)
    code2 = urllib.parse.parse_qs(urllib.parse.urlparse(loc2).query)["code"][0]
    bad = s.post(meta["token_endpoint"], data={
        "grant_type": "authorization_code", "code": code2,
        "redirect_uri": REDIRECT_URI, "client_id": kc.CLIENT_ID,
        "client_secret": kc.CLIENT_SECRET, "code_verifier": "wrong-verifier"})
    evidence["pkce_mismatch"] = {"status": bad.status_code}
    assert bad.status_code == 400, bad.status_code

    wrong_secret = s.post(meta["token_endpoint"], data={
        "grant_type": "authorization_code", "code": code2,
        "redirect_uri": REDIRECT_URI, "client_id": kc.CLIENT_ID,
        "client_secret": "not-the-secret", "code_verifier": _v2})
    evidence["bad_client_secret"] = {"status": wrong_secret.status_code}
    assert wrong_secret.status_code in (400, 401), wrong_secret.status_code

    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    out = os.path.join(EVIDENCE_DIR, "01-phaseA-idp-probe.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    print(f"\nPHASE A: GREEN  (evidence -> {out})")


if __name__ == "__main__":
    main()
