#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase B: run the CONTRACT.md §7.3 acceptance matrix against the real app.

Drives the real Tornado app (isolated SQLite DB, port 8791 so the redirect URI
matches what is registered in Keycloak) against the real Keycloak 26 container.
No mocks: the authorization-code + PKCE round trip is executed for real.

Run:
    .venv/bin/python tests/e2e/phase_b_matrix.py

Evidence is written to `.team/e2e/02-phaseB-matrix.json`.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402

import kc  # noqa: E402
from qd_runner import QdApp  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVIDENCE = os.path.join(REPO, ".team", "e2e", "02-phaseB-matrix.json")

# The session-cookie version string must match what the server computes, so we
# call the product's own helper instead of re-implementing its hash here.  This
# also keeps a weak-hash sink out of the test file (CodeQL alert on the former
# local copy).  Importing it has no side effect: `config/database.db` is not
# created and the process exits 0 (verified).
sys.path.insert(0, REPO)
from web.handlers.base import session_version as _product_session_version  # noqa: E402

# The admin user-management form posts `md5(plaintext)` as `adminpwd` (see
# web/tpl/user_manage.html:90).  Use the product's own helper rather than a
# fresh hashlib.md5 sink in this file -- same reasoning as the session_version
# delegation above.  This is a protocol artifact the server re-hashes with
# PBKDF2 before comparing (db/user.py:121 challenge_md5), not stored as-is.
from libs.utils import md5string as _md5string  # noqa: E402

PORT = 8791
DOMAIN = f"127.0.0.1:{PORT}"
COOKIE_SECRET = "e2e-cookie-sign-secret"

U1_EMAIL = "qduser@example.test"          # matches the Keycloak user's email
U2_EMAIL = "local-only@example.test"      # local account, NOT the IdP email
U2B_EMAIL = "unregistered@example.test"   # Keycloak-only, no local account
U1_PASSWORD = "u1-password-123"
U2_PASSWORD = "u2-password-123"
U2B_PASSWORD = "u2b-password-123"
NOPASS_EMAIL = "nopass@example.test"      # seeded fixture, no usable password
# §7.11: local account whose email the *unverified* Keycloak identity claims.
# It is a perfectly ordinary local account -- the only thing that makes the
# attack interesting is that the IdP never verified the mailbox.
U3_EMAIL = kc.UNVERIFIED_USER_EMAIL       # "unverified-target@example.test"
U3_PASSWORD = "u3-password-123"

# §7.3 (10) deleting a user must clean up its OIDC bindings, and the freed
# identity must be able to auto-bind again (must-fix #2).  A dedicated account
# keeps the deletion from disturbing the fixtures the other sections rely on.
U4_EMAIL = "delete-me@example.test"
U4_PASSWORD = "u4-password-123"


def admin_delete_user(sess, admin_userid, target_userid, admin_email,
                      admin_password):
    """Drive the real admin delete path.

    Two details that are easy to get wrong (both cost a RED run):
      * the URL segment is the ADMIN's own userid -- web/tpl/user_manage.html:2
        is rendered at /user/<current user>/manage and the form posts back to
        that same path; the *target* is carried in the body keyed by its id.
      * `adminpwd` is md5(plaintext) (user_manage.html:90), which the server
        re-hashes with PBKDF2 before comparing (db/user.py:121).
    """
    r = sess.post(f"http://{DOMAIN}/user/{admin_userid}/manage",
                  data={"adminmail": admin_email,
                        "adminpwd": _md5string(admin_password),
                        str(target_userid): "on",
                        "delbtn": ""},
                  allow_redirects=False, timeout=20)
    return r


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def session_version(password) -> str:
    """Local alias so call sites read unchanged.

    Deliberately delegates to the product helper (imported above): the version
    string is derived from an *already encrypted* password column, is never
    stored or compared against a plaintext secret, and must stay byte-identical
    to the server's computation.  Re-implementing the hash here duplicated a
    weak-hash sink for no benefit.
    """
    return _product_session_version(password)


def app_session():
    """A cookie-keeping session for the app under test (bypasses host proxy)."""
    s = requests.Session()
    s.trust_env = False
    return s


# Tornado renders xsrf_form_html() as a hidden input whose value is the same
# signed string that it also sets as the `_xsrf` cookie.
_XSRF_INPUT_RE = re.compile(r'name="_xsrf"\s+value="([^"]+)"')


def xsrf_token(sess):
    """Return a valid `_xsrf` form token for an authenticated session.

    GET /oidc/manage renders the real unbind <form>, which embeds
    `xsrf_form_html()`.  Fetching it both sets the `_xsrf` cookie and yields
    the matching form value -- exactly what a browser submits.  Returns None
    if the page did not render a token (so callers can assert on that).
    """
    r = sess.get(f"http://{DOMAIN}/oidc/manage",
                 allow_redirects=False, timeout=20)
    if r.status_code != 200:
        return None
    m = _XSRF_INPUT_RE.search(r.text)
    return m.group(1) if m else None


def post_unbind(sess, provider, token):
    """POST an unbind with (or, when token is None, without) the `_xsrf` field."""
    data = {"_xsrf": token} if token is not None else {}
    return sess.post(f"http://{DOMAIN}/oidc/{provider}/unbind",
                     data=data, allow_redirects=False, timeout=20)


def rec(status=None, location=None, body=None, **extra):
    d = {}
    if status is not None:
        d["status"] = status
    if location is not None:
        d["location"] = location
    if body is not None:
        d["body_snippet"] = body[:400]
    d.update(extra)
    return d


def step(name, ok, evidence, note=""):
    return {"check": name, "ok": bool(ok), "evidence": evidence, "note": note}


class Report:
    def __init__(self):
        self.steps = []
        self.started = time.time()

    def add(self, name, ok, evidence, note=""):
        s = step(name, ok, evidence, note)
        self.steps.append(s)
        print(f"{'PASS' if ok else 'FAIL'}  {name}"
              + (f"   -- {note}" if note else ""))
        return s

    def dump(self, extra=None):
        doc = {
            "phase": "B",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "duration_sec": round(time.time() - self.started, 2),
            "app": {"base": f"http://{DOMAIN}", "port": PORT, "domain": DOMAIN},
            "keycloak": {"base": kc.KC_BASE, "realm": kc.REALM,
                         "client_id": kc.CLIENT_ID, "redirect_uri": kc.REDIRECT_URI},
            "summary": {
                "total": len(self.steps),
                "passed": sum(1 for s in self.steps if s["ok"]),
                "failed": sum(1 for s in self.steps if not s["ok"]),
            },
            "steps": self.steps,
        }
        if extra:
            doc.update(extra)
        os.makedirs(os.path.dirname(EVIDENCE), exist_ok=True)
        with open(EVIDENCE, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False, default=str)
        return doc


def register(sess, email, password):
    r = sess.post(f"http://{DOMAIN}/register",
                  data={"email": email, "password": password},
                  allow_redirects=False, timeout=20)
    return r


def login_password(sess, email, password):
    r = sess.post(f"http://{DOMAIN}/login",
                  data={"email": email, "password": password},
                  allow_redirects=False, timeout=20)
    return r


def oidc_roundtrip(app_sess, idp_sess, provider, path, username, password,
                   force_reauth=False):
    """GET /oidc/<provider>/<path> on the app, authenticate at the IdP,
    then deliver the callback to the app.  Returns (authorize_resp,
    callback_url, callback_resp)."""
    if force_reauth:
        idp_sess.logout()
    authorize = app_sess.get(f"http://{DOMAIN}/oidc/{provider}/{path}",
                             allow_redirects=False, timeout=20)
    auth_url = authorize.headers.get("Location", "")
    if authorize.status_code != 302 or not auth_url.startswith(kc.KC_BASE):
        return authorize, None, None
    callback_url = idp_sess.authorize_and_login(auth_url, username, password)
    if not callback_url:
        return authorize, None, None
    # The IdP returns the app's redirect_uri; normalise its host so we talk to
    # the app we actually started.
    callback = app_sess.get(callback_url, allow_redirects=False, timeout=20)
    return authorize, callback_url, callback


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

def ensure_second_kc_user():
    """Create a Keycloak user whose email has no local account."""
    token = kc.admin_token()
    uid = kc._request(  # noqa: SLF001
        "GET",
        f"{kc.KC_BASE}/admin/realms/{kc.REALM}/users?username={U2B_EMAIL.split('@')[0]}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if uid:
        return uid[0]["id"]
    created = kc._request(  # noqa: SLF001
        "POST",
        f"{kc.KC_BASE}/admin/realms/{kc.REALM}/users",
        body={
            "username": U2B_EMAIL.split("@")[0],
            "email": U2B_EMAIL,
            "firstName": "No",
            "lastName": "Account",
            "enabled": True,
            "emailVerified": True,
            "credentials": [{"type": "password", "value": U2B_PASSWORD,
                             "temporary": False}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    del created
    uid = kc._request(  # noqa: SLF001
        "GET",
        f"{kc.KC_BASE}/admin/realms/{kc.REALM}/users?username={U2B_EMAIL.split('@')[0]}",
        headers={"Authorization": f"Bearer {token}"},
    )
    return uid[0]["id"]


def ensure_kc_user(username, email, password):
    """Idempotently create a Keycloak user with a verified email; returns its
    subject (Keycloak user id).  Used by the §7.3 (10) deletion fixture."""
    token = kc.admin_token()
    hdr = {"Authorization": f"Bearer {token}"}
    found = kc._request(  # noqa: SLF001
        "GET",
        f"{kc.KC_BASE}/admin/realms/{kc.REALM}/users?username={username}&exact=true",
        headers=hdr,
    )
    if found:
        # Repair a user created before the name fix: Keycloak raises
        # VERIFY_PROFILE at login while firstName/lastName are missing, which
        # would make the binding silently never happen.
        if not found[0].get("firstName") or not found[0].get("lastName"):
            kc._request(  # noqa: SLF001
                "PUT",
                f"{kc.KC_BASE}/admin/realms/{kc.REALM}/users/{found[0]['id']}",
                body={"firstName": "Delete", "lastName": "Me"},
                headers=hdr, expect=204)
        return found[0]["id"]
    kc._request(  # noqa: SLF001
        "POST",
        f"{kc.KC_BASE}/admin/realms/{kc.REALM}/users",
        body={"username": username, "email": email,
              # firstName/lastName are REQUIRED: without them Keycloak raises
              # the VERIFY_PROFILE required action at login, so the browser
              # never reaches the callback and the binding silently never
              # happens (cost me one RED run).
              "firstName": "Delete", "lastName": "Me",
              "enabled": True, "emailVerified": True,
              "credentials": [{"type": "password", "value": password,
                               "temporary": False}]},
        headers=hdr,
    )
    found = kc._request(  # noqa: SLF001
        "GET",
        f"{kc.KC_BASE}/admin/realms/{kc.REALM}/users?username={username}&exact=true",
        headers=hdr,
    )
    return found[0]["id"]


def seed_passwordless_user(app):
    """Seed a user with no usable password plus one OIDC binding.

    The product has no UI that creates a passwordless account, so the
    last-credential guard can only be exercised with a seeded row.  This is a
    fixture, not a product-reachable state -- labelled as such in the report.
    """
    now = int(time.time())
    ip = b"\x7f\x00\x00\x01"
    app.sqlite_exec(
        "INSERT INTO user (email, password, userkey, ctime, mtime, atime,"
        " cip, mip, aip, status) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (NOPASS_EMAIL, b"", b"", now, now, now, ip, ip, ip, "Enable"),
    )
    uid = app.sqlite_rows("SELECT id FROM user WHERE email=?", (NOPASS_EMAIL,))[0]["id"]
    return uid


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    rep = Report()
    prov = kc.provider_config(provider_id="keycloak", redirect_port=PORT)
    prov2 = kc.provider_config(provider_id="keycloak2", redirect_port=PORT)

    ensure_second_kc_user()
    print(f"[fixture] second Keycloak user ready: {U2B_EMAIL}")

    # §7.11 fixture: an IdP identity whose email matches a local account but
    # whose mailbox Keycloak has NOT verified.  Idempotent -- never recreates
    # the realm, which holds the other fixtures.
    uv_subject = kc.ensure_unverified_user()
    print(f"[fixture] unverified-email Keycloak user ready: "
          f"{kc.UNVERIFIED_USER} <{U3_EMAIL}> sub={uv_subject}")

    with QdApp(port=PORT, domain=DOMAIN, providers=[prov, prov2]) as app:
        print(f"[app] {app.base}  db={app.db_path}")

        # ------------------------------------------------------------------
        # setup: register two local accounts
        # ------------------------------------------------------------------
        s_u1 = app_session()
        r = register(s_u1, U1_EMAIL, U1_PASSWORD)
        rep.add("setup: register U1 (email == IdP email)",
                r.status_code == 302 and r.headers.get("Location", "").endswith("/my/"),
                rec(r.status_code, r.headers.get("Location")),
                f"U1={U1_EMAIL}")

        s_u2 = app_session()
        r = register(s_u2, U2_EMAIL, U2_PASSWORD)
        rep.add("setup: register U2 (email != IdP email)",
                r.status_code == 302,
                rec(r.status_code, r.headers.get("Location")),
                f"U2={U2_EMAIL}")

        u1 = app.sqlite_rows("SELECT id,email FROM user WHERE email=?", (U1_EMAIL,))[0]
        u2 = app.sqlite_rows("SELECT id,email FROM user WHERE email=?", (U2_EMAIL,))[0]

        # §7.11 fixture: a normal local account whose email the unverified
        # Keycloak identity will claim.  Nothing special about it -- that is
        # exactly what makes the gate meaningful.
        s_u3 = app_session()
        r = register(s_u3, U3_EMAIL, U3_PASSWORD)
        rep.add("setup: register U3 (email == UNVERIFIED IdP email)",
                r.status_code == 302,
                rec(r.status_code, r.headers.get("Location")),
                f"U3={U3_EMAIL}")
        u3 = app.sqlite_rows("SELECT id,email FROM user WHERE email=?", (U3_EMAIL,))[0]

        # ------------------------------------------------------------------
        # §7.3 (1) OIDC login -> 302 Keycloak -> auth -> callback -> session -> /my/
        # ------------------------------------------------------------------
        idp = kc.IdpSession()
        app_sess = app_session()
        authorize, cb_url, cb = oidc_roundtrip(
            app_sess, idp, "keycloak", "login", kc.TEST_USER, kc.TEST_USER_PASSWORD)

        auth_url = authorize.headers.get("Location", "")
        rep.add("login: GET /oidc/keycloak/login -> 302 to Keycloak authorize",
                authorize.status_code == 302
                and auth_url.startswith(f"{kc.KC_BASE}/realms/{kc.REALM}/protocol/openid-connect/auth")
                and "code_challenge=" in auth_url
                and "code_challenge_method=S256" in auth_url,
                rec(authorize.status_code, auth_url),
                "PKCE S256 present in authorize URL")

        rep.add("login: IdP authenticated and returned callback with code+state",
                bool(cb_url) and "code=" in (cb_url or "") and "state=" in (cb_url or ""),
                rec(location=cb_url))

        rep.add("login: GET callback -> 302 /my/ (session established)",
                cb is not None and cb.status_code == 302
                and cb.headers.get("Location", "").endswith("/my/")
                and "user" in app_sess.cookies,
                rec(cb.status_code if cb else None,
                    cb.headers.get("Location") if cb else None,
                    cookies=sorted(app_sess.cookies.keys())))

        r = app_sess.get(f"http://{DOMAIN}/my/", allow_redirects=False, timeout=20)
        rep.add("login: GET /my/ with session -> 200",
                r.status_code == 200, rec(r.status_code, body=r.text))

        rows = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE provider='keycloak' AND userid=?", (u1["id"],))
        rep.add("login: auto-bind created user_oidc row for U1",
                len(rows) == 1 and rows[0]["subject"] and rows[0]["email"] == U1_EMAIL,
                {"rows": rows}, f"userid={u1['id']}")
        u1_subject = rows[0]["subject"] if rows else None

        # ------------------------------------------------------------------
        # §7.3 (2) bind while logged in with a password session
        #
        # NOTE: the identity used here must NOT already be bound to anyone.
        # U1 auto-bound the `qduser` subject above, so we bind a *different*
        # Keycloak identity (`unregistered`) to U2.  Trying to bind U1's
        # identity here is asserted separately as the `bound_by_other` case.
        # ------------------------------------------------------------------
        idp2 = kc.IdpSession()
        authorize, cb_url, cb = oidc_roundtrip(
            s_u2, idp2, "keycloak", "bind", "unregistered", U2B_PASSWORD)
        rep.add("bind: GET /oidc/keycloak/bind -> 302 to Keycloak",
                authorize.status_code == 302
                and authorize.headers.get("Location", "").startswith(kc.KC_BASE),
                rec(authorize.status_code, authorize.headers.get("Location")))
        rep.add("bind: callback -> 302 /oidc/manage",
                cb is not None and cb.status_code == 302
                and cb.headers.get("Location", "").rstrip("/").endswith("/oidc/manage"),
                rec(cb.status_code if cb else None,
                    cb.headers.get("Location") if cb else None))

        rows = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE provider='keycloak' AND userid=?", (u2["id"],))
        u2_subject = rows[0]["subject"] if rows else None
        rep.add("bind: user_oidc row created for U2 (distinct subject)",
                len(rows) == 1 and u2_subject and u2_subject != u1_subject,
                {"rows": rows},
                f"userid={u2['id']}, u1_subject={u1_subject}, u2_subject={u2_subject}")

        r = s_u2.get(f"http://{DOMAIN}/oidc/manage", allow_redirects=False, timeout=20)
        rep.add("bind: GET /oidc/manage -> 200 and shows the binding",
                r.status_code == 200 and "keycloak" in r.text.lower(),
                rec(r.status_code, body=r.text))

        # §5.3 negative: an identity already bound to somebody else
        idp_dup = kc.IdpSession()
        authorize, cb_url, cb = oidc_roundtrip(
            s_u2, idp_dup, "keycloak", "bind", kc.TEST_USER, kc.TEST_USER_PASSWORD)
        loc = cb.headers.get("Location", "") if cb else None
        rep.add("bind-neg: binding U1's identity as U2 -> bound_by_other",
                cb is not None and cb.status_code == 302
                and "oidc_error=bound_by_other" in (loc or ""),
                rec(cb.status_code if cb else None, loc))

        # ------------------------------------------------------------------
        # §7.3 (3) unbind (POST) -> row removed
        # ------------------------------------------------------------------
        # lead's request: GET must NOT delete (handler only implements post())
        r = s_u2.get(f"http://{DOMAIN}/oidc/keycloak/unbind",
                     allow_redirects=False, timeout=20)
        after_get = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE userid=?", (u2["id"],))
        rep.add("unbind: GET /oidc/keycloak/unbind -> 405 and deletes nothing",
                r.status_code == 405 and len(after_get) == 1,
                rec(r.status_code, r.headers.get("Location"),
                    rows_after=after_get),
                "handler implements post() only")

        # §7.3 (3) unbind is CSRF-protected: POST without `_xsrf` must be
        # rejected and must NOT delete the row.  This is a real browser-level
        # protection added in this round, so it is asserted before the happy
        # path -- otherwise a missing token would silently look like success.
        tok_u2 = xsrf_token(s_u2)
        rep.add("unbind-csrf: GET /oidc/manage exposes an _xsrf form token",
                tok_u2 is not None, {"token_present": tok_u2 is not None},
                "tornado xsrf_form_html() embedded in the unbind <form>")

        r = post_unbind(s_u2, "keycloak", None)
        after_no_token = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE userid=?", (u2["id"],))
        rep.add("unbind-csrf: POST without _xsrf -> 403 and row kept",
                r.status_code == 403 and len(after_no_token) == 1,
                rec(r.status_code, r.headers.get("Location"),
                    rows_after=after_no_token),
                "check_xsrf_cookie() rejects a forged cross-site POST")

        r = post_unbind(s_u2, "keycloak", tok_u2)
        rep.add("unbind: POST /oidc/keycloak/unbind -> 302 /oidc/manage",
                r.status_code == 302
                and r.headers.get("Location", "").rstrip("/").endswith("/oidc/manage"),
                rec(r.status_code, r.headers.get("Location")))
        left = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE userid=?", (u2["id"],))
        rep.add("unbind: user_oidc row removed for U2",
                left == [], {"rows": left})

        # ------------------------------------------------------------------
        # §7.3 (4) last-credential guard (seeded passwordless fixture)
        # ------------------------------------------------------------------
        nopass_id = seed_passwordless_user(app)
        now = int(time.time())
        app.sqlite_exec(
            "INSERT INTO user_oidc (userid, provider, subject, email, ctime, mtime)"
            " VALUES (?,?,?,?,?,?)",
            (nopass_id, "keycloak", "seeded-subject", NOPASS_EMAIL, now, now),
        )
        # a second binding so the positive control has a remaining credential
        app.sqlite_exec(
            "INSERT INTO user_oidc (userid, provider, subject, email, ctime, mtime)"
            " VALUES (?,?,?,?,?,?)",
            (nopass_id, "keycloak2", "seeded-subject-2", NOPASS_EMAIL, now, now),
        )

        import tornado.web  # noqa: PLC0415
        import umsgpack  # noqa: PLC0415
        signed = tornado.web.create_signed_value(
            COOKIE_SECRET, "user",
            umsgpack.packb({"id": nopass_id, "v": session_version(b"")}),
        )
        cookie_val = signed.decode() if isinstance(signed, bytes) else signed

        s_np = app_session()
        s_np.cookies.set("user", cookie_val, domain="127.0.0.1", path="/")
        r = s_np.get(f"http://{DOMAIN}/oidc/manage", allow_redirects=False, timeout=20)
        rep.add("last-credential: seeded passwordless user session is accepted",
                r.status_code == 200, rec(r.status_code),
                "fixture: password column = b'' (product has no UI for this)")
        m = _XSRF_INPUT_RE.search(r.text)
        tok_np = m.group(1) if m else None

        # positive control: another binding remains -> unbind allowed
        r = post_unbind(s_np, "keycloak", tok_np)
        still = app.sqlite_rows(
            "SELECT provider FROM user_oidc WHERE userid=?", (nopass_id,))
        rep.add("last-credential: unbind ALLOWED when another binding remains",
                r.status_code == 302
                and "oidc_error" not in r.headers.get("Location", "")
                and [x["provider"] for x in still] == ["keycloak2"],
                rec(r.status_code, r.headers.get("Location"),
                    remaining=[x["provider"] for x in still]))

        # now the real guard: only one binding left, no password
        r = post_unbind(s_np, "keycloak2", tok_np)
        loc = r.headers.get("Location", "")
        still = app.sqlite_rows(
            "SELECT provider FROM user_oidc WHERE userid=?", (nopass_id,))
        rep.add("last-credential: unbind REFUSED (last_credential), row kept",
                r.status_code == 302 and "oidc_error=last_credential" in loc
                and [x["provider"] for x in still] == ["keycloak2"],
                rec(r.status_code, loc, remaining=[x["provider"] for x in still]))

        # ------------------------------------------------------------------
        # §7.3 (5) an IdP identity with no local account cannot log in
        # ------------------------------------------------------------------
        idp3 = kc.IdpSession()
        s_fresh = app_session()
        authorize, cb_url, cb = oidc_roundtrip(
            s_fresh, idp3, "keycloak", "login", "unregistered", U2B_PASSWORD,
            force_reauth=True)
        loc = cb.headers.get("Location", "") if cb else None
        rep.add("no_account: OIDC identity without a local account is rejected",
                cb is not None and cb.status_code == 302
                and "oidc_error=no_account" in (loc or ""),
                rec(cb.status_code if cb else None, loc))
        rep.add("no_account: no session cookie was established",
                "user" not in s_fresh.cookies,
                {"cookies": sorted(s_fresh.cookies.keys())})

        # ------------------------------------------------------------------
        # §7.11 auto-bind email-trust gate: an IdP identity whose email matches
        # a local account, but whose mailbox the IdP has NOT verified, must NOT
        # auto-bind.  This is the account-takeover vector: a provider that lets
        # anyone self-register and set an arbitrary unverified email would
        # otherwise hand over the local account.
        # ------------------------------------------------------------------
        bindings_before = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE userid=?", (u3["id"],))
        subject_before = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE provider='keycloak' AND subject=?",
            (uv_subject,))

        idp_uv = kc.IdpSession()
        s_uv = app_session()
        authorize, cb_url, cb = oidc_roundtrip(
            s_uv, idp_uv, "keycloak", "login", kc.UNVERIFIED_USER,
            kc.UNVERIFIED_USER_PASSWORD, force_reauth=True)
        loc = cb.headers.get("Location", "") if cb else None

        rep.add("email_unverified: GET /oidc/keycloak/login -> 302 to Keycloak",
                authorize.status_code == 302
                and authorize.headers.get("Location", "").startswith(kc.KC_BASE),
                rec(authorize.status_code, authorize.headers.get("Location")))

        rep.add("email_unverified: IdP returned callback with code+state",
                bool(cb_url) and "code=" in (cb_url or ""),
                rec(location=cb_url),
                f"id_token email={U3_EMAIL} email_verified=false")

        # (a) the gate itself
        rep.add("email_unverified: callback -> 302 /login?oidc_error=email_unverified",
                cb is not None and cb.status_code == 302
                and "oidc_error=email_unverified" in (loc or ""),
                rec(cb.status_code if cb else None, loc),
                "strict-boolean gate rejected the unverified mailbox")

        # (b) no session
        rep.add("email_unverified: NO session cookie was established",
                "user" not in s_uv.cookies,
                {"cookies": sorted(s_uv.cookies.keys())})
        r = s_uv.get(f"http://{DOMAIN}/my/", allow_redirects=False, timeout=20)
        rep.add("email_unverified: GET /my/ without a session -> 302 /login",
                r.status_code == 302
                and r.headers.get("Location", "").split("?")[0].endswith("/login"),
                rec(r.status_code, r.headers.get("Location")))

        # (c) the crucial one: nothing was written
        bindings_after = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE userid=?", (u3["id"],))
        subject_after = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE provider='keycloak' AND subject=?",
            (uv_subject,))
        rep.add("email_unverified: NO user_oidc row for (keycloak, unverified-subject)",
                subject_after == [] and subject_before == [],
                {"before": subject_before, "after": subject_after},
                f"subject={uv_subject}")
        rep.add("email_unverified: U3 binding count unchanged (no auto-bind)",
                bindings_before == [] and bindings_after == [],
                {"before": bindings_before, "after": bindings_after},
                f"userid={u3['id']}")

        # (d) control: the account is still usable, and manual binding still works
        r = login_password(s_u3, U3_EMAIL, U3_PASSWORD)
        rep.add("email_unverified-control: U3 can still log in with its password",
                r.status_code == 302
                and r.headers.get("Location", "").endswith("/my/"),
                rec(r.status_code, r.headers.get("Location")),
                "gate narrows auto-bind only; it does not lock the account")

        idp_uv2 = kc.IdpSession()
        authorize, cb_url, cb = oidc_roundtrip(
            s_u3, idp_uv2, "keycloak", "bind", kc.UNVERIFIED_USER,
            kc.UNVERIFIED_USER_PASSWORD, force_reauth=True)
        loc_b = cb.headers.get("Location", "") if cb else None
        rows_uv = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE userid=? AND provider='keycloak'",
            (u3["id"],))
        rep.add("email_unverified-control: manual /oidc/keycloak/bind SUCCEEDS",
                cb is not None and cb.status_code == 302
                and "oidc_error" not in (loc_b or "")
                and len(rows_uv) == 1 and rows_uv[0]["subject"] == uv_subject,
                rec(cb.status_code if cb else None, loc_b, rows=rows_uv),
                "explicit, authenticated binding is still allowed")

        # tear the control binding down again so later assertions see a clean
        # slate.  Must carry `_xsrf` now that unbind is CSRF-protected.
        tok_u3 = xsrf_token(s_u3)
        r_teardown = post_unbind(s_u3, "keycloak", tok_u3)
        rep.add("email_unverified-control: teardown unbind succeeds (CSRF token)",
                r_teardown.status_code == 302
                and app.sqlite_rows(
                    "SELECT * FROM user_oidc WHERE userid=?", (u3["id"],)) == [],
                rec(r_teardown.status_code, r_teardown.headers.get("Location"),
                    token_present=tok_u3 is not None),
                "keeps the §7.11 fixture reusable across runs")

        # ------------------------------------------------------------------
        # §7.3 (6) after unbinding, the identity's binding is really gone
        # ------------------------------------------------------------------
        rows = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE userid=?", (u2["id"],))
        rep.add("unbind-persistence: U2 has no binding after unbind",
                rows == [], {"rows": rows})

        # control: an email-matching identity re-auto-binds (contract §5.2)
        idp4 = kc.IdpSession()
        s_re = app_session()
        authorize, cb_url, cb = oidc_roundtrip(
            s_re, idp4, "keycloak", "login", kc.TEST_USER, kc.TEST_USER_PASSWORD,
            force_reauth=True)
        loc = cb.headers.get("Location", "") if cb else None
        rows = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE provider='keycloak' AND subject=?",
            (u1_subject,))
        rep.add("control: email-matching identity logs in (auto-bind, §5.2)",
                cb is not None and cb.status_code == 302
                and loc.endswith("/my/") and len(rows) == 1,
                rec(cb.status_code if cb else None, loc, rows=rows),
                "contract-conformant: email match re-establishes the binding")

        # ------------------------------------------------------------------
        # §7.3 (7) negative: tampered / forged state
        # ------------------------------------------------------------------
        s_bad = app_session()
        r0 = s_bad.get(f"http://{DOMAIN}/oidc/keycloak/login",
                       allow_redirects=False, timeout=20)
        flow_cookies = [c for c in s_bad.cookies.keys() if c.startswith("oidc_flow_")]
        rep.add("neg-state: /oidc/keycloak/login set a flow cookie",
                r0.status_code == 302 and flow_cookies == ["oidc_flow_keycloak"],
                rec(r0.status_code, cookies=sorted(s_bad.cookies.keys())))

        r = s_bad.get(f"http://{DOMAIN}/oidc/keycloak/callback"
                      f"?state=forged-state&code=whatever",
                      allow_redirects=False, timeout=20)
        loc = r.headers.get("Location", "")
        rep.add("neg-state: tampered state -> 302 /login?oidc_error=state_mismatch",
                r.status_code == 302 and "oidc_error=state_mismatch" in loc,
                rec(r.status_code, loc))
        rep.add("neg-state: tampered state did NOT establish a session",
                "user" not in s_bad.cookies,
                {"cookies": sorted(s_bad.cookies.keys())})

        # forged (unsigned) flow cookie
        s_forged = app_session()
        s_forged.cookies.set("oidc_flow_keycloak", "not-a-signed-value",
                             domain="127.0.0.1", path="/")
        r = s_forged.get(f"http://{DOMAIN}/oidc/keycloak/callback"
                         f"?state=whatever&code=whatever",
                         allow_redirects=False, timeout=20)
        loc = r.headers.get("Location", "")
        rep.add("neg-state: forged flow cookie -> state_mismatch, no session",
                r.status_code == 302 and "oidc_error=state_mismatch" in loc
                and "user" not in s_forged.cookies,
                rec(r.status_code, loc, cookies=sorted(s_forged.cookies.keys())))

        # callback with no flow cookie at all
        s_none = app_session()
        r = s_none.get(f"http://{DOMAIN}/oidc/keycloak/callback"
                       f"?state=x&code=y", allow_redirects=False, timeout=20)
        loc = r.headers.get("Location", "")
        rep.add("neg-state: callback without flow cookie -> state_mismatch",
                r.status_code == 302 and "oidc_error=state_mismatch" in loc,
                rec(r.status_code, loc))

        # ------------------------------------------------------------------
        # §7.3 (8) negative: unauthenticated access
        # ------------------------------------------------------------------
        s_anon = app_session()
        for path, label in (("/oidc/manage", "manage"),
                            ("/oidc/keycloak/bind", "bind")):
            r = s_anon.get(f"http://{DOMAIN}{path}", allow_redirects=False, timeout=20)
            loc = r.headers.get("Location", "")
            rep.add(f"neg-auth: anon GET {path} -> 302 /login",
                    r.status_code == 302 and loc.split("?")[0].endswith("/login"),
                    rec(r.status_code, loc),
                    "tornado @authenticated appends ?next=")

        # unauthenticated unbind POST.  Tornado's @authenticated raises 403
        # for non-GET/HEAD (it only redirects GET); that is framework-standard
        # and NOT a contract deviation -- §7.4 covers the GET paths.
        r = s_anon.post(f"http://{DOMAIN}/oidc/keycloak/unbind",
                        allow_redirects=False, timeout=20)
        rep.add("neg-auth: anon POST /oidc/keycloak/unbind -> 403 (tornado @authenticated)",
                r.status_code == 403,
                rec(r.status_code, r.headers.get("Location")),
                "framework-standard: @authenticated only redirects GET/HEAD")

        # ------------------------------------------------------------------
        # §7.3 (9) negative: unknown provider
        # ------------------------------------------------------------------
        r = s_anon.get(f"http://{DOMAIN}/oidc/nope/login", allow_redirects=False,
                       timeout=20)
        loc = r.headers.get("Location", "")
        rep.add("neg-provider: unknown provider -> provider_not_found",
                r.status_code == 302 and "oidc_error=provider_not_found" in loc,
                rec(r.status_code, loc))

        # ------------------------------------------------------------------
        # §7.3 (10) deleting a user cleans up its OIDC bindings, and the freed
        # identity can auto-bind again (must-fix #2).
        #
        # The failure mode this guards: if the binding row survived the user
        # deletion, a *new* account with the same email could never auto-bind
        # -- `user_oidc.get(userid=new_id)` is empty, so the insert would hit
        # the UNIQUE(provider, subject) key and fall through to
        # `already_bound_other` against a userid that no longer exists.
        # ------------------------------------------------------------------
        admin = app.sqlite_rows("SELECT id,role FROM user WHERE email=?", (U1_EMAIL,))[0]
        rep.add("delete-cleanup: U1 is the admin able to drive /user/<id>/manage",
                admin["role"] == "admin",
                {"admin": admin}, "USER0ISADMIN promotes the first account")

        # an admin *session*: U1's OIDC session above, or a plain password
        # login (U1 registered with a password).  Use the password login so the
        # admin session is independent of the OIDC flows under test.
        s_admin = app_session()
        r_admin = login_password(s_admin, U1_EMAIL, U1_PASSWORD)
        rep.add("delete-cleanup: admin password session established",
                r_admin.status_code == 302,
                rec(r_admin.status_code, r_admin.headers.get("Location")))

        s_u4 = app_session()
        r = register(s_u4, U4_EMAIL, U4_PASSWORD)
        u4 = app.sqlite_rows("SELECT id,email FROM user WHERE email=?", (U4_EMAIL,))[0]
        rep.add("delete-cleanup: register U4 and bind its Keycloak identity",
                r.status_code == 302, rec(r.status_code, r.headers.get("Location")),
                f"U4={U4_EMAIL} userid={u4['id']}")

        u4_subject = ensure_kc_user("deleteme", U4_EMAIL, U4_PASSWORD)
        idp_u4 = kc.IdpSession()
        authorize, cb_url, cb = oidc_roundtrip(
            s_u4, idp_u4, "keycloak", "login", "deleteme", U4_PASSWORD)
        rows_u4 = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE userid=?", (u4["id"],))
        rep.add("delete-cleanup: U4 auto-bound before deletion",
                cb is not None and cb.status_code == 302
                and len(rows_u4) == 1 and rows_u4[0]["subject"] == u4_subject,
                rec(cb.status_code if cb else None,
                    cb.headers.get("Location") if cb else None, rows=rows_u4),
                f"subject={u4_subject}")

        r_del = admin_delete_user(s_admin, admin["id"], u4["id"], U1_EMAIL, U1_PASSWORD)
        gone = app.sqlite_rows("SELECT id FROM user WHERE id=?", (u4["id"],))
        left = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE userid=?", (u4["id"],))
        rep.add("delete-cleanup: admin delete removed the user row",
                gone == [], {"user_rows_left": gone, "status": r_del.status_code},
                "real admin path: POST /user/<id>/manage with delbtn")
        rep.add("delete-cleanup: user_oidc bindings removed with the user",
                left == [], {"bindings_left": left},
                "must-fix #2: the delete path clears OIDC bindings")

        # The decisive step: a fresh account with the same email must be able
        # to auto-bind the very same IdP identity.
        s_u4b = app_session()
        r = register(s_u4b, U4_EMAIL, U4_PASSWORD)
        u4b = app.sqlite_rows("SELECT id,email FROM user WHERE email=?", (U4_EMAIL,))[0]
        idp_u4b = kc.IdpSession()
        authorize, cb_url, cb = oidc_roundtrip(
            s_u4b, idp_u4b, "keycloak", "login", "deleteme", U4_PASSWORD,
            force_reauth=True)
        loc = cb.headers.get("Location", "") if cb else None
        rows_u4b = app.sqlite_rows(
            "SELECT * FROM user_oidc WHERE userid=?", (u4b["id"],))
        rep.add("delete-cleanup: re-registered account auto-binds the SAME "
                "identity (not already_bound_other)",
                r.status_code == 302 and cb is not None and cb.status_code == 302
                and loc.endswith("/my/") and "oidc_error" not in (loc or "")
                and len(rows_u4b) == 1
                and rows_u4b[0]["subject"] == u4_subject
                and u4b["id"] != u4["id"],
                rec(cb.status_code if cb else None, loc, rows=rows_u4b,
                    old_userid=u4["id"], new_userid=u4b["id"]),
                "a stale binding row would have produced already_bound_other")

        # leave a clean slate for the final dump
        tok_u4 = xsrf_token(s_u4b)
        post_unbind(s_u4b, "keycloak", tok_u4)
        admin_delete_user(s_admin, admin["id"], u4b["id"], U1_EMAIL, U1_PASSWORD)

        final_rows = app.sqlite_rows(
            "SELECT userid,provider,subject,email FROM user_oidc ORDER BY id")
        print("\n[final user_oidc rows]")
        for row in final_rows:
            print("   ", row)

        doc = rep.dump({"final_user_oidc_rows": final_rows})
        print(f"\n===== PHASE B: {doc['summary']['passed']}/{doc['summary']['total']} "
              f"passed =====")
        print(f"evidence -> {EVIDENCE}")
        return 0 if doc["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
