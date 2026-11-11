# -*- coding: utf-8 -*-
"""`db/db_converter.py` 的 OIDC 建表逻辑测试（PR #643 评审行内 #3 / #4）。

覆盖两个要求：
1. **建表失败不得静默降级**：`ensure_user_oidc_table()` 失败必须抛出
   `OidcTableError`，而不是只记一条 error 日志后继续。
   背景：调用点 `run.py:62` 是 `loop.run_until_complete(run)`，异常会直接从
   `convert_new_type()` 冒泡并终止 `start_server()`；若不抛，服务会照常启动，
   直到运行期 OIDC 请求才以 `1146 Table '...user_oidc' doesn't exist` 失败。
2. **显式字符集**：表级字符集来自模型 `__table_args__` 的 `mysql_charset='utf8mb4'`，
   编译出的 MySQL DDL 必须自带 `CHARSET=utf8mb4`，且 provider/subject 为
   `utf8mb4_bin`（task-10 的 collation 修复不能被这次改动回退）。

隔离方式：在**临时文件** SQLite 上自建 AsyncEngine，通过临时替换
`db_converter.engine` 把 helper 指向它，不碰 `config.sqlite3.path`。
"""
import asyncio
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_oidc_support import ROOT  # noqa: E402  （确保 sys.path 已装好）


def _converter_available():
    return os.path.exists(os.path.join(ROOT, 'db', 'db_converter.py'))


SKIP_REASON = 'db/db_converter.py 尚未实现（task-1 未完成）'


@unittest.skipUnless(_converter_available(), SKIP_REASON)
class TestEnsureUserOidcTable(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from sqlalchemy.ext.asyncio import create_async_engine

        import db.db_converter as db_converter
        from db.user_oidc import UserOidc

        self.db_converter = db_converter
        self.UserOidc = UserOidc

        fd, self.db_path = tempfile.mkstemp(prefix='qd-oidc-conv-', suffix='.db')
        os.close(fd)
        self.engine = create_async_engine(f'sqlite+aiosqlite:///{self.db_path}')

        # helper 读的是模块级 engine；临时换掉，避免动 config.sqlite3.path。
        self._saved_engine = db_converter.engine
        db_converter.engine = self.engine

    async def asyncTearDown(self):
        self.db_converter.engine = self._saved_engine
        await self.engine.dispose()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    async def _table_names(self):
        async with self.engine.begin() as conn:
            rows = await conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            return {r[0] for r in rows}

    async def test_creates_user_oidc_table(self):
        """正常路径：建表成功，且幂等（重复调用不报错）。"""
        self.assertNotIn('user_oidc', await self._table_names())
        await self.db_converter.ensure_user_oidc_table()
        self.assertIn('user_oidc', await self._table_names())
        # 幂等：checkfirst=True，第二次调用必须静默通过
        await self.db_converter.ensure_user_oidc_table()
        self.assertIn('user_oidc', await self._table_names())

    async def test_failure_raises_oidc_table_error(self):
        """失败路径：必须抛出 OidcTableError，而不是吞掉异常返回。"""
        real_engine = self.db_converter.engine

        class _BoomEngine:
            """最小 fake：只驱动真实产品代码走失败分支。"""

            def begin(self):
                raise RuntimeError("simulated DDL failure")

        self.db_converter.engine = _BoomEngine()
        try:
            with self.assertRaises(self.db_converter.OidcTableError) as ctx:
                await self.db_converter.ensure_user_oidc_table()
        finally:
            self.db_converter.engine = real_engine

        # 错误信息要能点名是哪张表不可用
        self.assertIn('user_oidc', str(ctx.exception))

    async def test_failure_is_chained_to_cause(self):
        """异常链保留原始原因，便于运维在启动日志里看到真实 DDL 报错。"""
        real_engine = self.db_converter.engine

        class _BoomEngine:
            def begin(self):
                raise RuntimeError("Unknown collation: 'utf8mb4_nope'")

        self.db_converter.engine = _BoomEngine()
        try:
            with self.assertRaises(self.db_converter.OidcTableError) as ctx:
                await self.db_converter.ensure_user_oidc_table()
        finally:
            self.db_converter.engine = real_engine

        self.assertIsInstance(ctx.exception.__cause__, RuntimeError)
        self.assertIn('Unknown collation', str(ctx.exception.__cause__))

    async def test_oidc_table_error_is_runtime_error(self):
        """OidcTableError 继承 RuntimeError，符合仓库既有异常风格。"""
        self.assertTrue(issubclass(self.db_converter.OidcTableError, RuntimeError))


@unittest.skipUnless(_converter_available(), SKIP_REASON)
class TestOidcDdlCharset(unittest.TestCase):
    """行内 #4：显式字符集。以模型声明为准，并钉住 DDL 结果。"""

    def setUp(self):
        from db.user_oidc import UserOidc
        self.table = UserOidc.__table__

    def _mysql_ddl(self):
        from sqlalchemy.dialects import mysql
        from sqlalchemy.schema import CreateTable
        return str(CreateTable(self.table).compile(dialect=mysql.dialect()))

    def test_model_declares_utf8mb4_charset(self):
        """表级字符集的权威来源是模型上的 mysql_charset dialect option。"""
        opts = dict(self.table.dialect_options['mysql'])
        self.assertEqual(opts.get('charset'), 'utf8mb4')

    def test_mysql_ddl_has_explicit_charset(self):
        """MySQL DDL 必须自带 CHARSET=utf8mb4（不依赖目标库默认值）。"""
        ddl = self._mysql_ddl()
        self.assertIn('CHARSET=utf8mb4', ddl)
        # 不该依赖 DB 默认的 uca1400_ai_ci
        self.assertNotIn('uca1400', ddl.lower())

    def test_mysql_ddl_keeps_binary_collation_on_identity_columns(self):
        """provider/subject 必须仍是 utf8mb4_bin（task-10 的修复不得回退）。"""
        ddl = self._mysql_ddl()
        self.assertIn('provider VARCHAR(64) COLLATE utf8mb4_bin', ddl)
        self.assertIn('subject VARCHAR(255) COLLATE utf8mb4_bin', ddl)

    def test_create_all_rejects_mysql_charset_kwarg(self):
        """记录设计决定：mysql_charset 不是 create_all 的合法关键字。

        若将来有人试图在调用点再传一次 `mysql_charset=`，会得到 TypeError；
        表级字符集只能在模型上声明一处，避免两处声明不一致。
        """
        with self.assertRaises(TypeError) as ctx:
            self.table.metadata.create_all(
                None, tables=[self.table], checkfirst=True, mysql_charset='utf8mb4'
            )
        self.assertIn('mysql_charset', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
