# -*- coding: utf-8 -*-
"""`db/user_oidc.py` 的 CRUD 与唯一约束测试（契约 §2.1 / §7.2-4）。

隔离方式：在**临时文件** SQLite 上自建一个 AsyncEngine，只建 `user_oidc` 一张表，
把该 Session 通过 `sql_session=` 传进每个方法。这样既不碰 `config.sqlite3.path`，
也不依赖真实 user 表（契约里 `userid` 是普通 Integer + 索引，没有外键）。
"""
import asyncio
import os
import sys
import tempfile
import time
import unittest

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# tests/ 不是包：直接跑单个模块时，本目录要自己进 sys.path 才能 import 支撑模块。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_oidc_support import ROOT  # noqa: E402  （确保 sys.path 已装好）


def _user_oidc_available():
    return os.path.exists(os.path.join(ROOT, 'db', 'user_oidc.py'))


SKIP_REASON = 'db/user_oidc.py 尚未实现（task-1 未完成）'


@unittest.skipUnless(_user_oidc_available(), SKIP_REASON)
class TestUserOidcDB(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from db.user_oidc import UserOidc
        self.UserOidc = UserOidc

        fd, self.db_path = tempfile.mkstemp(prefix='qd-oidc-test-', suffix='.db')
        os.close(fd)
        self.engine = create_async_engine(f'sqlite+aiosqlite:///{self.db_path}')
        async with self.engine.begin() as conn:
            await conn.run_sync(UserOidc.__table__.create, checkfirst=True)
        self.session = AsyncSession(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.session.close()
        await self.engine.dispose()
        for suffix in ('', '-wal', '-shm'):
            path = self.db_path + suffix
            if os.path.exists(path):
                os.unlink(path)

    # ---------- add / get ----------

    async def test_add_returns_id_and_get_reads_it_back(self):
        oidc = self.UserOidc()
        row_id = await oidc.add(7, 'keycloak', 'sub-1', email='a@example.test', sql_session=self.session)
        self.assertIsInstance(row_id, int)
        self.assertGreater(row_id, 0)

        row = await oidc.get(id=row_id, sql_session=self.session)
        self.assertIsInstance(row, dict)
        self.assertEqual(row['userid'], 7)
        self.assertEqual(row['provider'], 'keycloak')
        self.assertEqual(row['subject'], 'sub-1')
        self.assertEqual(row['email'], 'a@example.test')
        self.assertIsInstance(row['ctime'], int)
        self.assertIsInstance(row['mtime'], int)

    async def test_add_without_email(self):
        oidc = self.UserOidc()
        row_id = await oidc.add(7, 'keycloak', 'sub-no-email', sql_session=self.session)
        row = await oidc.get(id=row_id, sql_session=self.session)
        self.assertIsNone(row['email'])

    async def test_get_by_provider_and_subject(self):
        oidc = self.UserOidc()
        await oidc.add(11, 'keycloak', 'sub-a', sql_session=self.session)
        await oidc.add(12, 'keycloak', 'sub-b', sql_session=self.session)

        row = await oidc.get(provider='keycloak', subject='sub-b', sql_session=self.session)
        self.assertEqual(row['userid'], 12)

    async def test_get_by_userid(self):
        oidc = self.UserOidc()
        await oidc.add(21, 'keycloak', 's1', sql_session=self.session)
        await oidc.add(21, 'azure', 's2', sql_session=self.session)

        row = await oidc.get(userid=21, provider='azure', sql_session=self.session)
        self.assertEqual(row['subject'], 's2')

    async def test_get_missing_returns_none(self):
        oidc = self.UserOidc()
        row = await oidc.get(provider='keycloak', subject='does-not-exist', sql_session=self.session)
        self.assertIsNone(row)

    async def test_get_with_fields_projection(self):
        oidc = self.UserOidc()
        row_id = await oidc.add(7, 'keycloak', 'sub-fields', sql_session=self.session)
        row = await oidc.get(id=row_id, fields=('id', 'subject'), sql_session=self.session)
        self.assertEqual(sorted(row.keys()), ['id', 'subject'])

    async def test_get_requires_some_selector(self):
        oidc = self.UserOidc()
        with self.assertRaises(AssertionError):
            await oidc.get(sql_session=self.session)

    # ---------- list ----------

    async def test_list_all_and_filtered(self):
        oidc = self.UserOidc()
        await oidc.add(1, 'keycloak', 'a', sql_session=self.session)
        await oidc.add(2, 'keycloak', 'b', sql_session=self.session)
        await oidc.add(3, 'azure', 'c', sql_session=self.session)

        everything = await oidc.list(sql_session=self.session)
        self.assertEqual(len(everything), 3)

        only_kc = await oidc.list(provider='keycloak', sql_session=self.session)
        self.assertEqual(sorted(r['subject'] for r in only_kc), ['a', 'b'])

        only_user_2 = await oidc.list(userid=2, sql_session=self.session)
        self.assertEqual([r['subject'] for r in only_user_2], ['b'])

    async def test_list_limit(self):
        oidc = self.UserOidc()
        for i in range(5):
            await oidc.add(i + 1, 'keycloak', f's{i}', sql_session=self.session)
        rows = await oidc.list(limit=2, sql_session=self.session)
        self.assertEqual(len(rows), 2)

    async def test_list_empty(self):
        oidc = self.UserOidc()
        self.assertEqual(await oidc.list(sql_session=self.session), [])

    # ---------- mod ----------

    async def test_mod_updates_email_and_mtime(self):
        oidc = self.UserOidc()
        row_id = await oidc.add(7, 'keycloak', 'sub-mod', email='old@example.test', sql_session=self.session)
        before = await oidc.get(id=row_id, sql_session=self.session)

        time.sleep(1.05)  # mtime 是 unix 秒，保证能观察到变化
        affected = await oidc.mod(row_id, email='new@example.test', sql_session=self.session)
        self.assertEqual(affected, 1)

        after = await oidc.get(id=row_id, sql_session=self.session)
        self.assertEqual(after['email'], 'new@example.test')
        self.assertGreater(after['mtime'], before['mtime'])

    async def test_mod_forbids_identity_columns(self):
        oidc = self.UserOidc()
        row_id = await oidc.add(7, 'keycloak', 'sub-immutable', sql_session=self.session)
        for key, value in (
            ('userid', 999),
            ('provider', 'other'),
            ('subject', 'other'),
        ):
            with self.subTest(key=key):
                with self.assertRaises(AssertionError):
                    await oidc.mod(row_id, sql_session=self.session, **{key: value})

        # `id` 是位置参数，作为关键字再传会先在 Python 层撞成 TypeError；
        # 无论哪条路径，都不能让它被静默改写。
        with self.assertRaises(TypeError):
            await oidc.mod(row_id, sql_session=self.session, id=999)

        row = await oidc.get(id=row_id, sql_session=self.session)
        self.assertEqual((row['userid'], row['provider'], row['subject']), (7, 'keycloak', 'sub-immutable'))

    # ---------- delete ----------

    async def test_delete_removes_row(self):
        oidc = self.UserOidc()
        row_id = await oidc.add(7, 'keycloak', 'sub-del', sql_session=self.session)
        affected = await oidc.delete(row_id, sql_session=self.session)
        self.assertEqual(affected, 1)
        self.assertIsNone(await oidc.get(id=row_id, sql_session=self.session))

    async def test_delete_missing_affects_zero(self):
        oidc = self.UserOidc()
        self.assertEqual(await oidc.delete(424242, sql_session=self.session), 0)

    # ---------- delete_by_user_provider ----------

    async def test_delete_by_user_provider_removes_only_that_row(self):
        oidc = self.UserOidc()
        await oidc.add(7, 'keycloak', 'kc-1', sql_session=self.session)
        await oidc.add(7, 'azure', 'az-1', sql_session=self.session)
        await oidc.add(8, 'keycloak', 'kc-other-user', sql_session=self.session)

        affected = await oidc.delete_by_user_provider(7, 'keycloak', sql_session=self.session)
        self.assertEqual(affected, 1)

        remaining = await oidc.list(sql_session=self.session)
        self.assertEqual(
            sorted((r['userid'], r['provider']) for r in remaining),
            [(7, 'azure'), (8, 'keycloak')],
            '只应删除 (userid=7, provider=keycloak) 这一行',
        )

    async def test_delete_by_user_provider_missing_affects_zero(self):
        oidc = self.UserOidc()
        self.assertEqual(await oidc.delete_by_user_provider(7, 'nope', sql_session=self.session), 0)

    # ---------- 唯一约束 ----------

    async def test_duplicate_provider_subject_raises(self):
        """(provider, subject) 唯一：同一 IdP 身份不能绑两个 QD 用户。"""
        oidc = self.UserOidc()
        await oidc.add(7, 'keycloak', 'same-sub', sql_session=self.session)

        with self.assertRaises(IntegrityError):
            await oidc.add(8, 'keycloak', 'same-sub', sql_session=self.session)
        await self.session.rollback()

        rows = await oidc.list(provider='keycloak', subject='same-sub', sql_session=self.session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['userid'], 7)

    async def test_same_subject_different_provider_is_allowed(self):
        """不同 provider 下相同的 sub 是不同身份，必须都能存。"""
        oidc = self.UserOidc()
        await oidc.add(7, 'keycloak', 'shared-sub', sql_session=self.session)
        await oidc.add(7, 'azure', 'shared-sub', sql_session=self.session)
        self.assertEqual(len(await oidc.list(sql_session=self.session)), 2)

    async def test_same_provider_different_subject_same_user_is_allowed(self):
        """契约 §2.1：一个用户对同一 provider 只能有一条绑定 —— 这由业务层
        （§5.3 的 already_bound_self）保证，DB 层唯一约束只管 (provider, subject)，
        因此这里断言 DB 允许、由业务层去拒绝。"""
        oidc = self.UserOidc()
        await oidc.add(7, 'keycloak', 'sub-x', sql_session=self.session)
        await oidc.add(7, 'keycloak', 'sub-y', sql_session=self.session)
        rows = await oidc.list(userid=7, provider='keycloak', sql_session=self.session)
        self.assertEqual(len(rows), 2)

    async def test_unique_constraint_is_declared_on_the_table(self):
        """静态确认唯一约束真的建在 (provider, subject) 上，名字对齐契约。"""
        from db.user_oidc import UserOidc
        names = {
            tuple(sorted(c.name for c in constraint.columns))
            for constraint in UserOidc.__table__.constraints
            if constraint.__class__.__name__ == 'UniqueConstraint'
        }
        self.assertIn(
            ('provider', 'subject'), names,
            f'user_oidc 表缺少 (provider, subject) 唯一约束，现有: {names}',
        )

    async def test_table_name_and_columns(self):
        from db.user_oidc import UserOidc
        self.assertEqual(UserOidc.__tablename__, 'user_oidc')
        self.assertEqual(
            {c.name for c in UserOidc.__table__.columns},
            {'id', 'userid', 'provider', 'subject', 'email', 'ctime', 'mtime'},
        )


if __name__ == '__main__':
    unittest.main()
