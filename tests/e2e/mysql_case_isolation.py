#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A2: real-MariaDB proof that OIDC subjects are case-sensitive.

Why a separate script instead of a step inside phase_b_matrix.py:
    phase_b_matrix.py is deliberately hermetic -- it runs the app on an
    isolated SQLite file.  SQLite has no collation names, so it *cannot*
    observe the bug this round fixed: on MySQL/MariaDB the library default
    collation (`utf8mb4_uca1400_ai_ci` here) is case-INSENSITIVE, which makes
    two subjects differing only in case collide on the unique key and match
    each other on lookup.  Proving the fix therefore needs a real MariaDB
    server, which is a heavier, stateful dependency; keeping it out of the
    SQLite matrix keeps that matrix reproducible without a database server.

What it proves (all against a real MariaDB container + real Keycloak):
    1. the app boots on DB_TYPE=mysql and creates user_oidc with
       per-column COLLATE utf8mb4_bin;
    2. a real Keycloak subject is stored byte-identically (case preserved);
    3. two subjects differing only in case COEXIST under the unique key;
    4. a lookup by the other case does NOT return the other row;
    5. decisive, product-path: with ONLY a case-variant row present for user
       B, a real OIDC login by the Keycloak user whose email matches user A
       must establish A's session -- a case-insensitive collation would have
       matched B's row and handed the session to B (account takeover).

Run:
    .venv/bin/python tests/e2e/mysql_case_isolation.py

Environment overrides:
    E2E_MYSQL_URL   default mysql://root:proot@127.0.0.1:13316/qde2e?auth_plugin=
    E2E_MYSQL_DB    default qde2e   (DROPPED and recreated -- dedicated DB only)
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymysql  # noqa: E402

import kc  # noqa: E402
import phase_b_matrix as pbm  # noqa: E402  (reuse the HTTP helpers: same port)
from qd_runner import QdApp  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVIDENCE = os.path.join(REPO, ".team", "e2e", "06-mysql-case-isolation.json")

MYSQL_URL = os.environ.get(
    "E2E_MYSQL_URL", "mysql://root:proot@127.0.0.1:13316/qde2e?auth_plugin="
)
MYSQL_DB = os.environ.get("E2E_MYSQL_DB", "qde2e")

PORT = pbm.PORT          # 8791 -- must match the Keycloak client's redirect URI
DOMAIN = pbm.DOMAIN

A_EMAIL = pbm.U1_EMAIL       # matches the Keycloak user's email
A_PASSWORD = pbm.U1_PASSWORD
B_EMAIL = pbm.U2_EMAIL       # ordinary local account, different email
B_PASSWORD = pbm.U2_PASSWORD


def _url_parts(url):
    p = urllib.parse.urlparse(url)
    return {
        "host": p.hostname or "127.0.0.1",
        "port": p.port or 3306,
        "user": p.username or "root",
        "password": p.password or "",
        "database": (p.path or "/").lstrip("/") or MYSQL_DB,
    }


def mysql_connect(parts, database=None):
    return pymysql.connect(
        host=parts["host"], port=parts["port"], user=parts["user"],
        password=parts["password"],
        database=database if database is not None else parts["database"],
        charset="utf8mb4", autocommit=True,
    )


def q1(conn, sql, params=()):
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def x(conn, sql, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


class Report:
    def __init__(self):
        self.steps = []
        self.started = time.time()

    def add(self, name, ok, evidence, note=""):
        s = {"check": name, "ok": bool(ok), "evidence": evidence, "note": note}
        self.steps.append(s)
        print(f"{'PASS' if ok else 'FAIL'}  {name}"
              + (f"   -- {note}" if note else ""))
        return s

    def dump(self, extra=None):
        doc = {
            "phase": "A2-mysql-case-isolation",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "duration_sec": round(time.time() - self.started, 2),
            "mysql": {"url": MYSQL_URL, "database": MYSQL_DB},
            "app": {"base": f"http://{DOMAIN}", "port": PORT},
            "keycloak": {"base": kc.KC_BASE, "realm": kc.REALM},
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


def main():
    rep = Report()
    parts = _url_parts(MYSQL_URL)
    print(f"[mysql] {parts['user']}@{parts['host']}:{parts['port']} "
          f"db={MYSQL_DB}")

    # ---- 0. dedicated, freshly recreated database -------------------------
    admin = mysql_connect(parts, database=None)
    srv = q1(admin, "SELECT VERSION() AS v, "
                    "@@character_set_server AS cs, "
                    "@@collation_server AS coll")
    x(admin, f"DROP DATABASE IF EXISTS `{MYSQL_DB}`")
    x(admin, f"CREATE DATABASE `{MYSQL_DB}` CHARACTER SET utf8mb4")
    dbinfo = q1(admin, "SELECT DEFAULT_CHARACTER_SET_NAME AS cs, "
                       "DEFAULT_COLLATION_NAME AS coll "
                       "FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s",
                (MYSQL_DB,))
    rep.add("mysql: real MariaDB reachable and dedicated DB recreated",
            bool(srv) and bool(dbinfo),
            {"server": srv[0] if srv else None, "database": dbinfo[0] if dbinfo else None},
            "DROP+CREATE of the dedicated e2e database only")

    # ---- 1. negative control: the server default IS case-insensitive ------
    # Without this, a green result could just mean "this server happens to be
    # case-sensitive anyway", i.e. the test would be vacuous.
    x(admin, f"USE `{MYSQL_DB}`")
    x(admin, "DROP TABLE IF EXISTS ctl_ai_ci")
    x(admin, "CREATE TABLE ctl_ai_ci (subject VARCHAR(255) "
             "COLLATE utf8mb4_uca1400_ai_ci NOT NULL, UNIQUE KEY uq (subject))")
    x(admin, "INSERT INTO ctl_ai_ci VALUES ('9dde2e44-045c-449b-82e6-075aef3a1159')")
    dup_err = None
    try:
        x(admin, "INSERT INTO ctl_ai_ci VALUES ('9DDE2E44-045C-449B-82E6-075AEF3A1159')")
    except pymysql.err.IntegrityError as e:
        dup_err = str(e)
    rep.add("control: server-default collation collides case-variants (1062)",
            dup_err is not None and "1062" in dup_err,
            {"duplicate_error": dup_err},
            "proves the discriminator is live: a case-insensitive unique key "
            "REJECTS the case-variant, so green below is not vacuous")
    x(admin, "DROP TABLE ctl_ai_ci")

    # The IdP's authoritative subject, read straight from the Keycloak admin
    # API -- NOT from the app under test, so the comparison below is a real
    # cross-check rather than the app agreeing with itself.
    _tok = kc.admin_token()
    _u = kc._request("GET", f"{kc.KC_BASE}/admin/realms/{kc.REALM}/users"
                            f"?username={kc.TEST_USER}&exact=true",
                     headers=kc._h(_tok))
    idp_sub = _u[0]["id"] if isinstance(_u, list) and _u else None
    pbm.ensure_second_kc_user()

    with QdApp(port=PORT, domain=DOMAIN,
               providers=[kc.provider_config("keycloak", PORT)],
               extra_env={"DB_TYPE": "mysql", "JAWSDB_MARIA_URL": MYSQL_URL}) as app:
        print(f"[app] {app.base}  db_type=mysql")

        conn = mysql_connect(parts)

        # ---- 2. schema: per-column binary collation ----------------------
        ddl = q1(conn, "SHOW CREATE TABLE user_oidc")
        ddl_text = (ddl[0].get("Create Table") or "") if ddl else ""
        cols = q1(conn, "SELECT COLUMN_NAME, COLLATION_NAME "
                        "FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='user_oidc' "
                        "AND COLUMN_NAME IN ('provider','subject') "
                        "ORDER BY COLUMN_NAME", (MYSQL_DB,))
        coll_map = {c["COLUMN_NAME"]: c["COLLATION_NAME"] for c in cols}
        rep.add("schema: user_oidc.provider/subject COLLATE utf8mb4_bin",
                coll_map.get("provider") == "utf8mb4_bin"
                and coll_map.get("subject") == "utf8mb4_bin",
                {"columns": coll_map,
                 "table_default_collation": dbinfo[0]["coll"] if dbinfo else None},
                "table default stays *_ai_ci; the per-column override is the fix")

        # ---- 3. two local accounts ---------------------------------------
        s_a = pbm.app_session()
        r = pbm.register(s_a, A_EMAIL, A_PASSWORD)
        s_b = pbm.app_session()
        r_b = pbm.register(s_b, B_EMAIL, B_PASSWORD)
        row_a = q1(conn, "SELECT id,email FROM user WHERE email=%s", (A_EMAIL,))
        row_b = q1(conn, "SELECT id,email FROM user WHERE email=%s", (B_EMAIL,))
        rep.add("setup: two local accounts exist in MariaDB",
                r.status_code == 302 and r_b.status_code == 302
                and len(row_a) == 1 and len(row_b) == 1,
                {"A": row_a, "B": row_b,
                 "status_a": r.status_code, "status_b": r_b.status_code})
        a_id = row_a[0]["id"]
        b_id = row_b[0]["id"]

        # ---- 4. real OIDC login -> subject stored case-preserved ----------
        idp = kc.IdpSession()
        s_login = pbm.app_session()
        authorize, cb_url, cb = pbm.oidc_roundtrip(
            s_login, idp, "keycloak", "login", kc.TEST_USER, kc.TEST_USER_PASSWORD)
        stored = q1(conn, "SELECT id,userid,provider,subject,email FROM user_oidc "
                          "WHERE provider='keycloak'")
        rep.add("login: real Keycloak login auto-binds and stores subject",
                cb is not None and cb.status_code == 302 and len(stored) == 1,
                {"callback_status": cb.status_code if cb else None,
                 "location": cb.headers.get("Location") if cb else None,
                 "rows": stored})

        kc_sub = stored[0]["subject"] if stored else None
        rep.add("login: stored subject is byte-identical to Keycloak's sub "
                "(case preserved, not folded)",
                kc_sub is not None and idp_sub is not None and kc_sub == idp_sub,
                {"idp_sub_from_admin_api": idp_sub, "stored_subject": kc_sub,
                 "keycloak_email": kc.TEST_USER_EMAIL,
                 "note": "compared against the admin API's user id, not the "
                         "app's own output"})
        rep.add("login: the binding belongs to the email-matching account A",
                stored and stored[0]["userid"] == a_id,
                {"stored_userid": stored[0]["userid"] if stored else None,
                 "a_id": a_id})

        # ---- 5. case-variant rows coexist ---------------------------------
        sub_upper = kc_sub.upper()
        rep.add("precondition: the case-variant subject really differs",
                sub_upper != kc_sub, {"lower": kc_sub, "upper": sub_upper})

        coex = None
        coex_err = None
        try:
            x(conn, "INSERT INTO user_oidc (userid,provider,subject,email,ctime,mtime)"
                    " VALUES (%s,'keycloak',%s,%s,1,1)", (b_id, sub_upper, B_EMAIL))
            coex = q1(conn, "SELECT userid,subject FROM user_oidc "
                            "WHERE provider='keycloak' ORDER BY userid")
        except pymysql.err.IntegrityError as e:
            coex_err = str(e)
        rep.add("case: case-variant subject coexists under the unique key "
                "(no false duplicate)",
                coex_err is None and coex is not None and len(coex) == 2,
                {"error": coex_err, "rows": coex},
                "utf8mb4_bin treats the two subjects as distinct keys")

        # ---- 6. lookup by the other case does not match -------------------
        got_lower = q1(conn, "SELECT userid,subject FROM user_oidc "
                             "WHERE provider='keycloak' AND subject=%s", (kc_sub,))
        got_upper = q1(conn, "SELECT userid,subject FROM user_oidc "
                             "WHERE provider='keycloak' AND subject=%s", (sub_upper,))
        rep.add("case: lookup by exact case returns ONLY its own row",
                len(got_lower) == 1 and got_lower[0]["userid"] == a_id
                and len(got_upper) == 1 and got_upper[0]["userid"] == b_id,
                {"lookup_lower": got_lower, "lookup_upper": got_upper},
                "the predicate the ORM emits for user_oidc.get(provider, subject)")

        # ---- 7. decisive: product path, no cross-account session ----------
        # Leave ONLY the case-variant row (belonging to B).  A case-insensitive
        # collation would make A's login find B's row and hand the session to B.
        x(conn, "DELETE FROM user_oidc WHERE subject=%s", (kc_sub,))
        before = q1(conn, "SELECT userid,subject FROM user_oidc "
                          "WHERE provider='keycloak' ORDER BY userid")
        rep.add("attack-setup: only B's case-variant row remains",
                len(before) == 1 and before[0]["userid"] == b_id,
                {"rows_before": before})

        idp2 = kc.IdpSession()
        s_victim = pbm.app_session()
        authorize2, cb_url2, cb2 = pbm.oidc_roundtrip(
            s_victim, idp2, "keycloak", "login", kc.TEST_USER,
            kc.TEST_USER_PASSWORD, force_reauth=True)
        loc2 = cb2.headers.get("Location", "") if cb2 else None
        after = q1(conn, "SELECT userid,provider,subject,email FROM user_oidc "
                         "WHERE provider='keycloak' ORDER BY userid")

        # Which account did the session actually land on?  Decode the signed
        # session cookie -- it carries the userid the server authenticated.
        import tornado.web  # noqa: PLC0415
        import umsgpack  # noqa: PLC0415
        raw_cookie = s_victim.cookies.get("user")
        session_uid = None
        if raw_cookie:
            dec = tornado.web.decode_signed_value(
                pbm.COOKIE_SECRET, "user", raw_cookie)
            if dec:
                session_uid = umsgpack.unpackb(dec).get("id")
        my = s_victim.get(f"http://{DOMAIN}/my/", allow_redirects=False, timeout=20)

        rep.add("attack: login did NOT match the case-variant row "
                "(no account takeover)",
                cb2 is not None and cb2.status_code == 302
                and loc2.endswith("/my/") and my.status_code == 200
                and session_uid == a_id and session_uid != b_id
                and len(after) == 2
                and any(r0["userid"] == a_id and r0["subject"] == kc_sub
                        for r0 in after),
                {"callback_status": cb2.status_code if cb2 else None,
                 "location": loc2,
                 "session_userid": session_uid,
                 "a_id": a_id, "b_id": b_id,
                 "my_status": my.status_code,
                 "rows_after": after},
                "with an ai_ci collation B's row would have matched -> session "
                "for B; utf8mb4_bin correctly binds a fresh row to A")

        # the product query path, in the same process, for completeness
        got = q1(conn, "SELECT userid FROM user_oidc WHERE provider=%s AND subject=%s",
                 ("keycloak", kc_sub))
        rep.add("attack: post-login lookup resolves to A, never to B",
                len(got) == 1 and got[0]["userid"] == a_id,
                {"lookup": got, "a_id": a_id, "b_id": b_id})

        conn.close()
        admin.close()

        doc = rep.dump({
            "final_user_oidc_rows": after,
            "subject_lower": kc_sub,
            "subject_upper": sub_upper,
        })
        print(f"\n===== A2 MYSQL CASE ISOLATION: "
              f"{doc['summary']['passed']}/{doc['summary']['total']} passed =====")
        print(f"evidence -> {EVIDENCE}")
        return 0 if doc["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
