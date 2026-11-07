# -*- coding: utf-8 -*-
"""provider 配置校验与前端暴露子集的测试（契约 §3.1 / §3.2 / §7.2-3）。

`config.py` 的校验发生在**导入期**，而本测试进程里 `config` 早被别的模块导入过，
`importlib.reload` 会连带污染其它模块持有的旧引用。所以这里一律用**子进程**探测
（`test_oidc_support.config_probe`）：每个用例给一份 OIDC_PROVIDERS，重新导入
config，读回 `config.oidc_providers` 与 `config.get_enabled_providers()`。

判据：非法项必须被**跳过**且不影响合法项，进程必须**照常启动**（rc=0）。
"""
import json
import os
import sys
import unittest

# tests/ 不是包：直接跑单个模块时，本目录要自己进 sys.path 才能 import 支撑模块。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_oidc_support import ROOT, config_probe  # noqa: E402

CONFIG_PY = os.path.join(ROOT, 'config.py')


def _config_has_oidc_support():
    """feature 标记：config.py 里出现 oidc_providers 才认为 task-1 已落地。

    只按「文件里有没有这个符号」决定跳过，避免在实现未落地时把
    AttributeError 误报成产品缺陷；一旦符号存在，后续断言全部从严。
    """
    try:
        with open(CONFIG_PY, encoding='utf-8') as fh:
            source = fh.read()
    except OSError:
        return False
    return 'oidc_providers' in source and 'get_enabled_providers' in source


IMPLEMENTED = _config_has_oidc_support()
SKIP_REASON = 'config.py 尚未实现 oidc_providers / get_enabled_providers（task-1 未完成）'

GOOD = {
    'id': 'keycloak',
    'name': 'Keycloak',
    'issuer': 'https://idp.example.test/realms/qd',
    'client_id': 'qd-client',
    'client_secret': 'super-secret-value',
}


def _good(**overrides):
    item = dict(GOOD)
    item.update(overrides)
    return item


@unittest.skipUnless(IMPLEMENTED, SKIP_REASON)
class TestOidcProviderConfig(unittest.TestCase):
    maxDiff = None

    def probe(self, providers, expect_rc=0, extra_env=None):
        payload = None if providers is None else json.dumps(providers)
        rc, parsed, stderr = config_probe(payload, extra_env=extra_env)
        self.assertEqual(
            rc, expect_rc,
            f'导入 config 失败（rc={rc}），provider 配置不应让进程起不来。stderr:\n{stderr}',
        )
        return parsed

    def test_valid_provider_passes(self):
        result = self.probe([_good()])
        self.assertEqual([p['id'] for p in result['oidc_providers']], ['keycloak'])
        self.assertEqual([p['id'] for p in result['enabled']], ['keycloak'])

    def test_missing_required_fields_are_skipped(self):
        providers = [
            _good(id='no-issuer', issuer=None),
            _good(id='no-client-id', client_id=None),
            _good(id='no-client-secret', client_secret=None),
            _good(id='ok-one'),
        ]
        # 去掉值为 None 的键，模拟「字段直接缺失」而非「字段为 null」
        providers = [
            {k: v for k, v in p.items() if v is not None} for p in providers
        ]
        result = self.probe(providers)
        self.assertEqual(
            [p['id'] for p in result['oidc_providers']], ['ok-one'],
            '缺 issuer/client_id/client_secret 的项必须被跳过，且不影响合法项',
        )

    def test_missing_id_is_skipped(self):
        bad = {k: v for k, v in GOOD.items() if k != 'id'}
        result = self.probe([bad, _good(id='survivor')])
        self.assertEqual([p['id'] for p in result['oidc_providers']], ['survivor'])

    def test_illegal_id_is_skipped(self):
        for bad_id in ('bad id', 'bad/id', 'bad.id', 'bad:id', 'bad*id', 'x' * 65):
            with self.subTest(id=bad_id):
                result = self.probe([_good(id=bad_id), _good(id='survivor')])
                self.assertEqual(
                    [p['id'] for p in result['oidc_providers']], ['survivor'],
                    f'非法 id {bad_id!r} 必须被跳过',
                )

    def test_legal_id_charset_is_accepted(self):
        for good_id in ('a', 'A1', 'a-b_c', 'x' * 64):
            with self.subTest(id=good_id):
                result = self.probe([_good(id=good_id)])
                self.assertEqual([p['id'] for p in result['oidc_providers']], [good_id])

    def test_enabled_false_excluded_from_enabled_list(self):
        result = self.probe([_good(id='on', enabled=True), _good(id='off', enabled=False)])
        self.assertEqual(
            sorted(p['id'] for p in result['oidc_providers']), ['off', 'on'],
            'enabled:false 仍留在 oidc_providers 里，但不出现在 get_enabled_providers()',
        )
        self.assertEqual([p['id'] for p in result['enabled']], ['on'])

    def test_enabled_providers_exposes_only_safe_subset(self):
        result = self.probe([_good()])
        self.assertEqual(len(result['enabled']), 1)
        exposed = result['enabled'][0]
        self.assertEqual(sorted(exposed.keys()), ['icon', 'id', 'name'])
        self.assertNotIn('client_secret', exposed)
        self.assertNotIn('client_id', exposed)
        self.assertNotIn('issuer', exposed)

    def test_secret_never_appears_in_probe_output(self):
        """前端子集里绝不能带出 secret 值。"""
        result = self.probe([_good()])
        self.assertNotIn(GOOD['client_secret'], json.dumps(result['enabled']))

    def test_empty_env_means_no_providers(self):
        result = self.probe(None)
        self.assertEqual(result['oidc_providers'], [])
        self.assertEqual(result['enabled'], [])

    def test_malformed_json_does_not_kill_process(self):
        rc, parsed, stderr = config_probe('{not json at all')
        self.assertEqual(rc, 0, f'非法 OIDC_PROVIDERS 不应让进程起不来。stderr:\n{stderr}')
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['oidc_providers'], [])
        self.assertEqual(parsed['enabled'], [])

    def test_json_object_instead_of_array_is_rejected_gracefully(self):
        rc, parsed, stderr = config_probe(json.dumps(GOOD))
        self.assertEqual(rc, 0, f'OIDC_PROVIDERS 不是数组时不应让进程起不来。stderr:\n{stderr}')
        self.assertEqual(parsed['oidc_providers'], [])

    def test_array_of_non_objects_is_rejected_gracefully(self):
        rc, parsed, stderr = config_probe(json.dumps(['nope', 42, None]))
        self.assertEqual(rc, 0, f'数组元素不是对象时不应让进程起不来。stderr:\n{stderr}')
        self.assertEqual(parsed['oidc_providers'], [])

    def test_all_invalid_still_starts(self):
        rc, parsed, stderr = config_probe(json.dumps([{'id': 'x'}, {'nope': 1}]))
        self.assertEqual(rc, 0, f'全部非法时进程仍须启动。stderr:\n{stderr}')
        self.assertEqual(parsed['oidc_providers'], [])
        self.assertEqual(parsed['enabled'], [])

    def test_duplicate_ids_are_handled(self):
        """重复 id 不应让进程崩溃；至少保证暴露给前端的子集里 id 唯一。"""
        rc, parsed, stderr = config_probe(json.dumps([_good(), _good()]))
        self.assertEqual(rc, 0, f'重复 id 不应让进程起不来。stderr:\n{stderr}')
        ids = [p['id'] for p in parsed['enabled']]
        self.assertEqual(len(ids), len(set(ids)), f'get_enabled_providers() 返回了重复 id: {ids}')

    def test_local_config_guard_exists(self):
        """契约 §3.1-1：local_config.py 若已定义 oidc_providers 应被尊重。

        这里只做静态确认——守卫必须在 `from local_config import *` 之后生效。
        """
        with open(CONFIG_PY, encoding='utf-8') as fh:
            source = fh.read()
        guard = 'if "oidc_providers" not in globals():'
        self.assertIn(guard, source, 'config.py 缺少 local_config 覆盖守卫')


if __name__ == '__main__':
    unittest.main()
