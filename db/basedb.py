#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.com>
#         http://binux.me
# Created on 2012-08-30 17:43:49

import contextlib
from asyncio import current_task
from typing import AsyncIterator, Optional, Union

from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.engine import Result, Row
from sqlalchemy.ext.asyncio import (AsyncSession, async_scoped_session,
                                    create_async_engine)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import Delete, Select, Update
from sqlalchemy.sql.elements import TextClause

import config
from libs.log import Log

if config.db_type == 'mysql':
    host = config.mysql.host
    port = config.mysql.port
    database = config.mysql.database
    user = config.mysql.user
    passwd = config.mysql.passwd
    auth_plugin = config.mysql.auth_plugin
    engine_url = f"mysql+aiomysql://{user}:{passwd}@{host}:{port}/{database}?auth_plugin={auth_plugin}"
    engine = create_async_engine(engine_url,
                                 logging_name=config.sqlalchemy.logging_name,
                                 pool_size=config.sqlalchemy.pool_size,
                                 max_overflow=config.sqlalchemy.max_overflow,
                                 pool_logging_name=config.sqlalchemy.pool_logging_name,
                                 pool_pre_ping=config.sqlalchemy.pool_pre_ping,
                                 pool_recycle=config.sqlalchemy.pool_recycle,
                                 pool_timeout=config.sqlalchemy.pool_timeout,
                                 pool_use_lifo=config.sqlalchemy.pool_use_lifo)
elif config.db_type == 'sqlite3':
    engine_url = f"sqlite+aiosqlite:///{config.sqlite3.path}"
    engine = create_async_engine(engine_url,
                                 logging_name=config.sqlalchemy.logging_name,
                                 pool_logging_name=config.sqlalchemy.pool_logging_name,
                                 pool_pre_ping=config.sqlalchemy.pool_pre_ping,
                                 pool_recycle=config.sqlalchemy.pool_recycle)
    Log('aiosqlite',
        logger_level=config.sqlalchemy.pool_logging_level,
        channel_level=config.sqlalchemy.pool_logging_level).getlogger()
else:
    raise Exception('db_type must be mysql or sqlite3')
logger_db = Log('sqlalchemy',
                logger_level=config.sqlalchemy.logging_level,
                channel_level=config.sqlalchemy.logging_level).getlogger()
logger_db_engine = Log(getattr(engine.sync_engine, 'logger', f'sqlalchemy.engine.Engine.{config.sqlalchemy.logging_name}'),
                       logger_level=config.sqlalchemy.logging_level,
                       channel_level=config.sqlalchemy.logging_level).getlogger()
if hasattr(engine.sync_engine.pool, 'logger'):
    if hasattr(getattr(engine.sync_engine.pool, 'logger'), 'logger'):
        logger_db_pool = Log(engine.sync_engine.pool.logger.logger,
                             logger_level=config.sqlalchemy.pool_logging_level,
                             channel_level=config.sqlalchemy.pool_logging_level).getlogger()
    else:
        logger_db_pool = Log(engine.sync_engine.pool.logger,
                             logger_level=config.sqlalchemy.pool_logging_level,
                             channel_level=config.sqlalchemy.pool_logging_level).getlogger()
async_session = async_scoped_session(sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
                                     scopefunc=current_task)
BaseDB = declarative_base(bind=engine, name="BaseDB")


class AlchemyMixin:
    @property
    def sql_session(self) -> AsyncSession:
        return async_session()

    @contextlib.asynccontextmanager
    async def transaction(self, sql_session: Optional[AsyncSession] = None) -> AsyncIterator[AsyncSession]:
        if sql_session is None:
            async with self.sql_session as sql_session:
                # deepcode ignore AttributeLoadOnNone: sql_session is not None
                async with sql_session.begin():
                    yield sql_session
        elif not sql_session.in_transaction():
            async with sql_session.begin():
                yield sql_session
        else:
            yield sql_session

    async def _execute(self, text: Union[str, TextClause], sql_session: Optional[AsyncSession] = None):
        async with self.transaction(sql_session) as sql_session:
            if isinstance(text, str):
                text = text.replace(':', r'\:')  # 如果text原本是个字符串，则转义冒号
                text = TextClause(text)  # 将其转换为TextClause对象
            result = await sql_session.execute(text)
            return result

    async def _get(self, stmt: Select, one_or_none=False, first=False, sql_session: Optional[AsyncSession] = None):
        async with self.transaction(sql_session) as sql_session:
            result: Result = await sql_session.execute(stmt)
            if one_or_none:
                return result.scalar_one_or_none()
            if first:
                return result.first()
            return result.all()

    async def _insert(self, instance, many=False, sql_session: Optional[AsyncSession] = None):
        async with self.transaction(sql_session) as sql_session:
            if many:
                sql_session.add_all(instance)
            else:
                sql_session.add(instance)
                await sql_session.flush()
                return instance.id

    async def _update(self, stmt: Update, sql_session: Optional[AsyncSession] = None):
        async with self.transaction(sql_session) as sql_session:
            result: Result = await sql_session.execute(stmt)
            return result.rowcount if hasattr(result, 'rowcount') else -1

    async def _insert_or_update(self, insert_stmt: Insert, sql_session: Optional[AsyncSession] = None, **kwargs) -> int:
        async with self.transaction(sql_session) as sql_session:
            insert_stmt.on_duplicate_key_update(**kwargs)
            result: Result = await sql_session.execute(insert_stmt)
            return result.lastrowid if hasattr(result, 'lastrowid') else -1

    async def _delete(self, stmt: Delete, sql_session: Optional[AsyncSession] = None):
        async with self.transaction(sql_session) as sql_session:
            result: Result = await sql_session.execute(stmt)
            return result.rowcount if hasattr(result, 'rowcount') else -1

    @staticmethod
    def to_dict(result: Row, fields=None):
        if result is None:
            return result
        if fields is None:
            return {c.name: getattr(result[0], c.name) for c in result[0].__table__.columns}
        return dict(result._mapping)  # pylint: disable=protected-access
