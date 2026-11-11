# 安全政策

## 获得安全更新支持的版本

使用这部分来告诉人们 项目的哪些版本 目前得到了安全更新的支持。

| 版本 | 是否获得支持 |
|------- | ------------------ |
| 202110xx | :white_check_mark: |
| 20230524 | :x:                |

## 报告漏洞

使用本节来告诉人们如何报告漏洞。

告诉他们在哪里, 多长时间可以得到一个报告的漏洞的更新;

如果漏洞被接受或被拒绝, 会有什么结果, 等等。
## 已知依赖风险

### CVE-2026-85394（python-jose，暂无可升级的修复版本）

| 项目 | 内容 |
| ------- | ------------------ |
| CVE 编号 | CVE-2026-85394 |
| 受影响组件 | `python-jose` |
| 影响版本 | `<= 3.5.0`（3.5.0 为撰写时的最新版，**上游尚未发布修复版本**） |
| CVSS | 3.1 = 9.1 / 4.0 = 9.3（critical） |
| 本仓库当前版本 | `python-jose>=3.5.0`（见 `pyproject.toml` 依赖列表） |

**漏洞成因**：python-jose 在初始化 HMAC 校验路径时未正确校验「传入的是不是非对称密钥」，
会接受缺少 PEM armor / SSH 前缀的 DER 编码公钥。攻击者在**已持有服务方公钥**（JWKS 本身
是公开的）的前提下，可用该公钥作为 HMAC 密钥伪造 HS256 签名的 JWT，从而绕过签名校验。

**利用前提**：应用未显式限制可接受的算法集合——即把发现文档/密钥声明里的 `HS*`、`none`
一并放进了 `jose.jwt.decode(algorithms=...)` 的允许列表。这是该 CVE 成立的必要条件。

#### 本项目的处置：该利用前提在本仓库不成立

本项目在算法选择上做了显式白名单，`HS*` 与 `none` 从未进入允许列表：

- 白名单常量：`libs/oidc.py` 的 `SUPPORTED_ID_TOKEN_ALGS`（`libs/oidc.py:40`），
  内容仅为非对称算法 `RS256/RS384/RS512` 与 `ES256/ES384/ES512`，不含任何 `HS*` 或 `none`。
- 生效路径：`libs/oidc.py` 的 `_resolve_algorithms()`（`libs/oidc.py:325`）取发现文档
  `id_token_signing_alg_values_supported` 与上述白名单的**交集**；交集为空时直接抛
  `OidcError('invalid_id_token', 'no supported id_token signing algorithm')`，
  绝不回退到「不加限制」。
- 该结果作为 `algorithms=` 传入 `jose.jwt.decode(...)`，因此即便发现文档里声明了
  `HS256`/`HS512`/`none`，也不会被采纳。

对应的拒绝用例（`tests/test_oidc_jwt.py`，全部离线自签，不依赖外部 IdP）：

- `tests/test_oidc_jwt.py:157` `test_algorithm_confusion_hs256_signed_with_rsa_public_key_is_rejected`
  —— 直接用 RSA 公钥签 HS256 的算法混淆攻击；
- `tests/test_oidc_jwt.py:172` `test_hs256_rejected_even_if_discovery_advertises_it`
  —— 发现文档声明 HS256 时仍拒绝；
- `tests/test_oidc_jwt.py:179` `test_hs256_with_oct_jwks_key_is_rejected_by_the_allowlist_alone`
  —— 仅靠白名单即拒绝 oct 密钥；
- `tests/test_oidc_jwt.py:223` `test_alg_none_is_rejected`、
  `tests/test_oidc_jwt.py:228` `test_alg_none_rejected_even_when_discovery_advertises_none`
  —— `alg=none` 的拒绝；
- `tests/test_oidc_jwt.py:235` `test_allowlist_never_contains_hs_or_none`
  —— 策略断言：白名单常量本身不得出现 `HS*`/`none`。

因此本项目的结论是：**CVE-2026-85394 的利用前提（未限制算法集合）在本仓库不成立**，
而非「本项目不受任何影响」。依赖扫描器仍会因版本号持续命中该 critical，本节的用途即是
为该告警提供可核验的处置依据。

#### 后续跟踪动作

- 持续跟踪 python-jose 上游修复；一旦发布 `> 3.5.0` 的版本，立即升级并复跑
  `tests/test_oidc_jwt.py`。
- 若上游长期不修复，届时评估迁移到 `joserfc` 等替代实现（属依赖取舍，
  需同步评估构建体系影响，参见 `pyproject.toml` 中 python-jose 的注释）。

<!--
# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 5.1.x   | :white_check_mark: |
| 5.0.x   | :x:                |
| 4.0.x   | :white_check_mark: |
| < 4.0   | :x:                |

## Reporting a Vulnerability

Use this section to tell people how to report a vulnerability.

Tell them where to go, how often they can expect to get an update on a
reported vulnerability, what to expect if the vulnerability is accepted or
declined, etc. -->
