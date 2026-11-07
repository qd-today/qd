# Keycloak fixture for the QD OIDC E2E (Phase A)

Container: **`nexus-kc-test`** (Keycloak 26.0, `quay.io/keycloak/keycloak:26.0`)
already running on `127.0.0.1:8095`, admin `admin`/`admin`.
The harness **only** creates/uses realm `qd-test`; the pre-existing
`nexus-test` and `master` realms are never touched.

## Reproduce from scratch

```bash
cd /home/zheng/temp/qd-oidc
# (re)create realm qd-test + confidential client qd-e2e + user qduser
.venv/bin/python tests/e2e/kc.py setup          # add --force to recreate the realm
```

That single command is idempotent: without `--force` it leaves an existing
`qd-test` realm alone and just prints the discovery document.

## What it creates

| Item | Value |
|---|---|
| Realm | `qd-test` (`sslRequired: none`, `attributes.samesite: Lax`) |
| Client | `qd-e2e`, confidential, standard flow, PKCE **S256** required |
| Client secret | `qd-e2e-secret-0123456789` |
| Redirect URI | `http://127.0.0.1:8791/oidc/keycloak/callback` |
| Test user | `qduser` / `qd-user-pass-123` |
| Test email | `qduser@example.test` |
| Issuer | `http://127.0.0.1:8095/realms/qd-test` |

All of these are overridable via env vars (`KC_REALM`, `KC_CLIENT_ID`,
`KC_CLIENT_SECRET`, `KC_USER`, `KC_USER_PASSWORD`, `KC_USER_EMAIL`,
`KC_REDIRECT_URI`, `KC_BASE`). See `tests/e2e/kc.py`.

## Raw equivalent (what `kc.py` does over the Admin REST API)

```bash
KC=http://127.0.0.1:8095
TOK=$(curl -s --noproxy '*' -X POST \
  $KC/realms/master/protocol/openid-connect/token \
  -d 'grant_type=password&client_id=admin-cli&username=admin&password=admin' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s --noproxy '*' -X POST $KC/admin/realms -H "Authorization: Bearer $TOK" \
  -H 'Content-Type: application/json' \
  -d '{"realm":"qd-test","enabled":true,"sslRequired":"none"}'

curl -s --noproxy '*' -X POST $KC/admin/realms/qd-test/clients \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"clientId":"qd-e2e","enabled":true,"protocol":"openid-connect",
       "publicClient":false,"secret":"qd-e2e-secret-0123456789",
       "standardFlowEnabled":true,"directAccessGrantsEnabled":false,
       "redirectUris":["http://127.0.0.1:8791/oidc/keycloak/callback"],
       "attributes":{"pkce.code.challenge.method":"S256"}}'

curl -s --noproxy '*' -X POST $KC/admin/realms/qd-test/users \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"username":"qduser","enabled":true,"email":"qduser@example.test",
       "emailVerified":true,
       "credentials":[{"type":"password","value":"qd-user-pass-123","temporary":false}]}'
```

## Two environment quirks that shaped the harness (measured, not guessed)

1. **Keycloak 26 hard-codes `Secure` on its auth-session cookies.**
   Measured `Set-Cookie`:
   `AUTH_SESSION_ID=...;Version=1;Path=/realms/qd-test/;Secure;HttpOnly;SameSite=None`
   — even with `sslRequired: none`, and even after setting the realm
   attribute `samesite=Lax`. `requests` 2.34.2 / `http.cookiejar` then
   *refuse to send* that cookie over plain `http`, so the login POST came
   back `400 Cookie not found. Please make sure cookies are enabled in your
   browser.` (`http.cookiejar.CookieJar._cookies_for_request` filters on
   `secure` before the header is built; patching the policy's
   `return_ok_secure` did not help because the filter runs earlier.)
   → The harness keeps its own tiny cookie jar (`kc.IdpSession`) that ignores
   the `Secure` attribute for loopback http. Loopback http is not an insecure
   transport here, so this is a test-harness accommodation, **not** a
   relaxation of any product assertion.
2. **`samesite=Lax` is still set on the realm** because a real browser
   performing the cross-site top-level redirect from Keycloak back to
   `127.0.0.1:8791` would otherwise drop the cookie under the Keycloak 26
   default of `SameSite=None` without `Secure`. `kc.py setup` sets it.

## Phase A evidence

`tests/e2e/kc_flow_probe.py` drives the whole authorization-code + PKCE flow
with raw HTTP (no QD product code) and asserts:

- discovery doc + login form + credential POST → 302 back to `redirect_uri`
  with the exact `state` we sent
- token exchange via `client_secret_post` → 200, **and** via HTTP Basic
  (`client_secret_basic`) → 200
- `id_token` decoded against the live JWKS: `iss`/`aud`/`nonce`/`sub`/`email`
  all correct
- negatives: authorization code replay → 400; wrong `code_verifier` → 400;
  wrong client secret → 401

Evidence JSON: `.team/e2e/01-phaseA-idp-probe.json`.

```bash
cd /home/zheng/temp/qd-oidc && .venv/bin/python tests/e2e/kc_flow_probe.py
```
