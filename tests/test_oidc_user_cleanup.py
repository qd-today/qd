# -*- coding: utf-8 -*-
"""task-11: 删除用户时清理 user_oidc 绑定 —— 行为级测试。

驱动方式：**真实 `UserManagerHandler.post` 逻辑 + 真 SQLAlchemy async engine**
（SQLite 临时文件库），只用最小替身补上 Tornado HTTP 层。

关键设计：删用户的业务逻辑一行都不复制 —— `post` 直接取真实函数对象，
`self.db` 是真实 `db.DB()`，`self.db.sql_session` 被替换为指向本测试的
Session，因此所有 `sql_session=sql_session` 的清理都真的落在测试库上。
这样测试对产品代码的变异是敏感的（见报告中的变异 RED 证据），不是自证。
"""
import hashlib
import os
import sys
import tempfile
import unittest
import unittest.mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sqlalchemy import text  # noqa: E402
from sqlalchemy.dialects import sqlite  # noqa: E402
from sqlalchemy.dialects.mysql import (MEDIUMBLOB, TINYINT,  # noqa: E402
                                       VARBINARY)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402

from db import DB  # noqa: E402
from db.notepad import Notepad  # noqa: E402
from db.task import Task  # noqa: E402
from db.tasklog import Tasklog  # noqa: E402
from db.tpl import Tpl  # noqa: E402
from db.user import User  # noqa: E402
from db.user_oidc import UserOidc  # noqa: E402
from web.handlers.user import UserManagerHandler  # noqa: E402

# 真实 handler 逻辑：不做任何复制/重写。
user_manager_post = UserManagerHandler.post

ALL_TABLES = [User, Tpl, Task, Tasklog, Notepad, UserOidc]
TABLES_WITHOUT_USER_OIDC = [User, Tpl, Task, Tasklog, Notepad]

# --- SQLite 类型适配 -------------------------------------------------------
# 这些表的模型用了 MySQL 方言类型（TINYINT / VARBINARY / MEDIUMBLOB），
# SQLite 方言无法渲染。仓库自己的建表路径（db/db_converter.py）在 sqlite3 下
# 也是手写 DDL 把 TINYINT 落成 INTEGER、BLOB 落成 VARBINARY 的，故这里用
# 编译期适配把同一语义映射过去——只影响本测试进程，不碰产品代码。
@compiles(TINYINT, 'sqlite')
def _sqlite_tinyint(type_, compiler, **kw):  # noqa: ARG001
    return 'INTEGER'


@compiles(VARBINARY, 'sqlite')
def _sqlite_varbinary(type_, compiler, **kw):  # noqa: ARG001
    return 'BLOB'


@compiles(MEDIUMBLOB, 'sqlite')
def _sqlite_mediumblob(type_, compiler, **kw):  # noqa: ARG001
    return 'BLOB'

ADMIN_EMAIL = 'admin@cleanup.test'
ADMIN_PWD = 'admin-pwd-123'
TARGET_EMAIL = 'victim@cleanup.test'
TARGET_PWD = 'victim-pwd-123'
OTHER_EMAIL = 'bystander@cleanup.test'
OTHER_PWD = 'bystander-pwd-123'

PROVIDER = 'keycloak'
TARGET_SUBJECT = 'sub-target-1'
OTHER_SUBJECT = 'sub-bystander-1'

SUCCESS_TITLE = '操作成功'
FAILURE_TITLE = '设置失败'


class FakeRequest:
    """只承载 `post` 用到的 `body_arguments`。"""

    def __init__(self, body_arguments):
        self.body_arguments = body_arguments
        self.files = {}


class FakeHandler:
    """只实现 `UserManagerHandler.post` 用到的 Tornado 接口。

    权限判定（`require_admin`）被替换为记录调用的桩：本用例聚焦删用户清理，
    鉴权路径不是被测对象（且 `require_admin` 是既有行为，未被本任务改动）。
    """

    def __init__(self, db, body_arguments, user):
        self.db = db
        self.request = FakeRequest(body_arguments)
        self.current_user = user
        self.rendered = []
        self.require_admin_calls = 0

    def require_admin(self):
        self.require_admin_calls += 1
        return self.current_user

    def get_body_argument(self, name, default=None):
        value = self.request.body_arguments.get(name, default)
        if isinstance(value, list):
            return value[-1]
        return value

    async def render(self, template_name, **kwargs):
        self.rendered.append((template_name, kwargs))
        return ''


class TestDeleteUserOidcCleanup(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix='qd-cleanup-test-', suffix='.db')
        os.close(fd)
        self.engine = create_async_engine(f'sqlite+aiosqlite:///{self.db_path}')
        self.session = AsyncSession(self.engine, expire_on_commit=False)
        self.db = DB()

        # 把 DB 实例上的 sql_session 指向本测试的 Session：
        # handler 的 `async with self.db.transaction() as sql_session` 由此落到测试库。
        patcher = unittest.mock.patch.object(
            DB, 'sql_session', new_callable=unittest.mock.PropertyMock
        )
        self.sql_session_prop = patcher.start()
        self.sql_session_prop.return_value = self.session
        self.addCleanup(patcher.stop)

        await self._create_tables(ALL_TABLES)

    async def asyncTearDown(self):
        await self.session.close()
        await self.engine.dispose()
        for suffix in ('', '-wal', '-shm'):
            path = self.db_path + suffix
            if os.path.exists(path):
                os.unlink(path)

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    async def _create_tables(self, models):
        async with self.engine.begin() as conn:
            for model in models:
                await conn.run_sync(model.__table__.create, checkfirst=True)

    async def _scalar(self, sql, **params):
        """用独立连接查询，避免与 handler 的 Session 互相干扰。"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text(sql), params)
            return result.scalar()

    async def _seed_user(self, email, password, role=None):
        await self.db.user.add(email, password, '127.0.0.1', sql_session=self.session)
        row = await self.db.user.get(email=email, fields=('id',), sql_session=self.session)
        userid = row['id']
        if role is not None:
            await self.db.user.mod(userid, role=role, sql_session=self.session)
        return userid

    async def _seed_target_payload(self):
        """给 target 用户造齐 task/tasklog/tpl/notepad/user_oidc 五类数据。"""
        task_id = await self.db.task.add(
            tplid=1, userid=self.target_id, env=b'', sql_session=self.session
        )
        await self.db.tasklog.add(
            taskid=task_id, success=1, msg='log-1', sql_session=self.session
        )
        await self.db.tpl.add(
            userid=self.target_id, har=b'', tpl=b'', variables='', init_env='',
            sql_session=self.session,
        )
        await self.db.notepad.add(
            dict(userid=self.target_id, notepadid=1, content='note-1'),
            sql_session=self.session,
        )
        binding_id = await self.db.user_oidc.add(
            self.target_id, PROVIDER, TARGET_SUBJECT, email=TARGET_EMAIL,
            sql_session=self.session,
        )
        return task_id, binding_id

    def _delete_body(self):
        # 与 web/tpl/user_manage.html 的真实提交逐字对齐（第 86/88 行）：
        #   env[el.name] = 'on'        # 勾选的用户 checkbox
        #   env[this.name] = ''        # 被点击的按钮（值就是空串）
        return {
            'adminmail': ADMIN_EMAIL,
            'adminpwd': hashlib.md5(ADMIN_PWD.encode('utf-8')).hexdigest(),
            'delbtn': '',
            str(self.target_id): 'on',
        }

    async def _run_delete(self):
        handler = FakeHandler(
            self.db, self._delete_body(),
            {'id': self.admin_id, 'isadmin': True, 'email': ADMIN_EMAIL},
        )
        await user_manager_post(handler, str(self.admin_id))
        return handler

    # ------------------------------------------------------------------
    # 正向：真实删除路径 + 逐条断言既有清理行为
    # ------------------------------------------------------------------

    async def test_delete_user_removes_oidc_binding_and_keeps_existing_cleanup(self):
        self.admin_id = await self._seed_user(ADMIN_EMAIL, ADMIN_PWD, role='admin')
        self.target_id = await self._seed_user(TARGET_EMAIL, TARGET_PWD)
        # 旁观者：有自己的 OIDC 绑定，删除 target 后必须原样保留（证明按 userid 限定）
        self.other_id = await self._seed_user(OTHER_EMAIL, OTHER_PWD)
        await self.db.user_oidc.add(
            self.other_id, PROVIDER, OTHER_SUBJECT, email=OTHER_EMAIL,
            sql_session=self.session,
        )
        task_id, binding_id = await self._seed_target_payload()

        # 前置：五类数据各就位
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM user_oidc WHERE userid=:u', u=self.target_id), 1
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM task WHERE userid=:u', u=self.target_id), 1
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM tasklog WHERE taskid=:t', t=task_id), 1
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM tpl WHERE userid=:u', u=self.target_id), 1
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM notepad WHERE userid=:u', u=self.target_id), 1
        )

        handler = await self._run_delete()

        # 删用户整体成功（没有被 user_oidc 清理炸掉）
        self.assertEqual(handler.rendered[-1][0], 'utils_run_result.html')
        self.assertEqual(handler.rendered[-1][1].get('title'), SUCCESS_TITLE)

        # 本任务修复点：绑定被清干净
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM user_oidc WHERE userid=:u', u=self.target_id), 0
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM user_oidc WHERE id=:i', i=binding_id), 0
        )
        # 既有清理行为逐条不变
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM task WHERE userid=:u', u=self.target_id), 0
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM tasklog WHERE taskid=:t', t=task_id), 0
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM tpl WHERE userid=:u', u=self.target_id), 0
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM notepad WHERE userid=:u', u=self.target_id), 0
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM user WHERE id=:u', u=self.target_id), 0
        )
        # 旁观者未受波及
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM user_oidc WHERE userid=:u', u=self.other_id), 1
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM user WHERE id=:u', u=self.other_id), 1
        )

    # ------------------------------------------------------------------
    # 容错：user_oidc 表不存在时，删用户仍必须完成
    # ------------------------------------------------------------------

    async def test_delete_user_succeeds_when_user_oidc_table_missing(self):
        self.admin_id = await self._seed_user(ADMIN_EMAIL, ADMIN_PWD, role='admin')
        self.target_id = await self._seed_user(TARGET_EMAIL, TARGET_PWD)
        task_id, _ = await self._seed_target_payload()

        # 制造「老库升级中间态」：把 user_oidc 表整个删掉
        async with self.engine.begin() as conn:
            await conn.execute(text('DROP TABLE user_oidc'))
        self.assertEqual(
            await self._scalar(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='user_oidc'"
            ),
            0,
        )

        with unittest.mock.patch('web.handlers.user.logger_web_handler') as mock_logger:
            handler = await self._run_delete()

        # 关键：删用户没有失败
        self.assertEqual(handler.rendered[-1][0], 'utils_run_result.html')
        self.assertEqual(handler.rendered[-1][1].get('title'), SUCCESS_TITLE)
        # 容错信号被记录（点名 user_oidc，便于运维定位）
        warning_calls = [c for c in mock_logger.warning.call_args_list]
        self.assertTrue(warning_calls, '表缺失时必须留下 warning 日志')
        self.assertIn('user_oidc', str(warning_calls[0][0][0]))

        # 删除仍然彻底完成
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM user WHERE id=:u', u=self.target_id), 0
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM task WHERE userid=:u', u=self.target_id), 0
        )
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM tasklog WHERE taskid=:t', t=task_id), 0
        )

    async def test_delete_user_succeeds_without_user_oidc_cleanup_block(self):
        """对照：只有 5 张表（无 user_oidc 依赖）时，删用户本来就应成功。

        与上一条的区别是这里连 `db.user_oidc` 都不可用（模拟模块级缺失），
        确保删除路径不因 OIDC 功能整体缺席而回归。
        """
        self.admin_id = await self._seed_user(ADMIN_EMAIL, ADMIN_PWD, role='admin')
        self.target_id = await self._seed_user(TARGET_EMAIL, TARGET_PWD)

        broken = unittest.mock.Mock()
        broken.list = unittest.mock.AsyncMock(side_effect=RuntimeError('no user_oidc module'))
        with unittest.mock.patch.object(self.db, 'user_oidc', broken):
            handler = await self._run_delete()

        self.assertEqual(handler.rendered[-1][0], 'utils_run_result.html')
        self.assertEqual(handler.rendered[-1][1].get('title'), SUCCESS_TITLE)
        self.assertEqual(
            await self._scalar('SELECT COUNT(*) FROM user WHERE id=:u', u=self.target_id), 0
        )


if __name__ == '__main__':
    unittest.main()
