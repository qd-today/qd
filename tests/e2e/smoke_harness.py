#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Smoke test for the E2E harness itself (no Keycloak needed).

Verifies:
  1. the app starts on a free port with an isolated SQLite DB;
  2. the DB really is the throwaway file (tables created there, and the
     repo's own config/database.db is NOT touched);
  3. the login page renders and carries the OIDC button when a provider is
     configured, and none when it is not (contract §7 item 7);
  4. unauthenticated /oidc/manage -> 302 /login (contract §7 item 4);
  5. unknown provider -> 302 /login?oidc_error=provider_not_found (§7 item 5).
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qd_runner import QdApp  # noqa: E402
from kc import provider_config  # noqa: E402

import urllib.error  # noqa: E402
import urllib.request  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_DB = os.path.join(REPO, "config", "database.db")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}), NoRedirect()
)


def http(url, method="GET", data=None, headers=None):
    req = urllib.request.Request(url, method=method, data=data,
                                 headers=headers or {})
    try:
        with OPENER.open(req, timeout=15) as resp:
            return resp.status, dict(resp.headers), resp.read().decode(
                "utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")


def main():
    results = []
    repo_db_mtime = os.path.getmtime(REPO_DB) if os.path.exists(REPO_DB) else None
    repo_db_size = os.path.getsize(REPO_DB) if os.path.exists(REPO_DB) else None

    prov = provider_config(redirect_port=8799)
    prov["id"] = "keycloak"

    with QdApp(port=8799, providers=[prov], domain="127.0.0.1:8799") as app:
        print(f"[ok] app up at {app.base}")
        print(f"[ok] db path   {app.db_path}")
        print(f"[ok] log path  {app.log_path}")

        rows = app.sqlite_rows(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r["name"] for r in rows]
        print(f"[info] tables ({len(tables)}): {tables}")
        assert "user_oidc" in tables, "user_oidc table missing!"
        assert "user" in tables, "user table missing!"
        results.append(("isolated DB has user_oidc + user", True, tables))

        # --- §7.4 unauthenticated /oidc/manage ---
        st, hd, _ = http(app.base + "/oidc/manage")
        loc = hd.get("Location", "")
        print(f"[info] GET /oidc/manage -> {st} Location={loc!r}")
        results.append(("/oidc/manage anon -> 302 /login",
                        st == 302 and loc.split("?")[0].endswith("/login"),
                        (st, loc)))

        # --- §7.4 unauthenticated /oidc/keycloak/bind ---
        st, hd, _ = http(app.base + "/oidc/keycloak/bind")
        loc = hd.get("Location", "")
        print(f"[info] GET /oidc/keycloak/bind -> {st} Location={loc!r}")
        results.append(("/oidc/keycloak/bind anon -> 302 /login",
                        st == 302 and loc.split("?")[0].endswith("/login"),
                        (st, loc)))

        # --- §7.5 unknown provider ---
        st, hd, _ = http(app.base + "/oidc/nope/login")
        loc = hd.get("Location", "")
        print(f"[info] GET /oidc/nope/login -> {st} Location={loc!r}")
        results.append(("unknown provider -> provider_not_found",
                        st == 302 and "oidc_error=provider_not_found" in loc,
                        (st, loc)))

        # --- §7.7 login page with provider ---
        st, hd, body = http(app.base + "/login")
        has_btn = "/oidc/keycloak/login" in body
        print(f"[info] GET /login -> {st}, oidc button present={has_btn}")
        results.append(("login page shows OIDC button when provider set",
                        st == 200 and has_btn, st))

    # --- §7.7 login page with NO provider ---
    with QdApp(providers=[]) as app:
        st, hd, body = http(app.base + "/login")
        has_btn = "/oidc/" in body and "/login" in body and "oidc" in body.lower()
        # more precise: no /oidc/<provider>/login link
        import re
        links = re.findall(r'/oidc/[a-zA-Z0-9_-]+/login', body)
        print(f"[info] GET /login (no provider) -> {st}, oidc links={links}")
        results.append(("login page has NO OIDC UI without providers",
                        st == 200 and not links, links))

    # --- repo DB untouched ---
    if repo_db_mtime is not None:
        now_mtime = os.path.getmtime(REPO_DB)
        now_size = os.path.getsize(REPO_DB)
        untouched = (now_mtime == repo_db_mtime and now_size == repo_db_size)
        print(f"[info] repo config/database.db mtime {repo_db_mtime} -> {now_mtime}")
        results.append(("repo config/database.db untouched", untouched,
                        (repo_db_mtime, now_mtime)))
    else:
        print("[info] repo config/database.db does not exist (nothing to touch)")
        results.append(("repo config/database.db untouched", True, "absent"))

    print("\n===== SMOKE RESULTS =====")
    ok = True
    for name, passed, detail in results:
        print(f"{'PASS' if passed else 'FAIL'}  {name}  {detail}")
        ok = ok and passed
    print("===== SMOKE", "GREEN" if ok else "RED", "=====")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
