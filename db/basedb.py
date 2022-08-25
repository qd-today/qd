#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.com>
#         http://binux.me
# Created on 2012-08-30 17:43:49

from asyncio import current_task
import contextlib
import logging
from typing import Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine,async_scoped_session
from sqlalchemy.sql import Select, Update, Delete
from sqlalchemy.dialects.mysql import Insert
from sqlalchemy.engine import Result, ScalarResult, CursorResult
from sqlalchemy.orm import declarative_base,sessionmaker
import config
from libs.log import Log

if config.db_type == 'mysql':
    host=config.mysql.host
    port=config.mysql.port
    database=config.mysql.database
    user=config.mysql.user
    passwd=config.mysql.passwd
    auth_plugin=config.mysql.auth_plugin
    engine = create_async_engine(f"mysql+aiomysql://{user}:{passwd}@{host}:{port}/{database}?auth_plugin={auth_plugin}",
                                logging_name = config.sqlalchemy.logging_name,
                                pool_size = config.sqlalchemy.pool_size,
                                max_overflow = config.sqlalchemy.max_overflow,
                                pool_logging_name = config.sqlalchemy.pool_logging_name,
                                pool_pre_ping = config.sqlalchemy.pool_pre_ping,
                                pool_recycle = config.sqlalchemy.pool_recycle,
                                pool_timeout = config.sqlalchemy.pool_timeout,
                                pool_use_lifo = config.sqlalchemy.pool_use_lifo)
elif config.db_type == 'sqlite3':
    engine = create_async_engine(f"sqlite+aiosqlite:///{config.sqlite3.path}", 
                                logging_name = config.sqlalchemy.logging_name,
                                pool_logging_name = config.sqlalchemy.pool_logging_name,
                                pool_pre_ping = config.sqlalchemy.pool_pre_ping,
                                pool_recycle = config.sqlalchemy.pool_recycle )
    Log('aiosqlite',
        logger_level=config.sqlalchemy.pool_logging_level,
        channel_level=config.sqlalchemy.pool_logging_level).getlogger()
else:
    raise Exception('db_type must be mysql or sqlite3')
logger_DB = Log('sqlalchemy', 
                logger_level=config.sqlalchemy.logging_level,
                channel_level=config.sqlalchemy.logging_level).getlogger()
logger_DB_Engine = Log(engine.engine.logger, 
                logger_level=config.sqlalchemy.logging_level,
                channel_level=config.sqlalchemy.logging_level).getlogger()
if hasattr(engine.pool.logger, 'logger'):
    logger_DB_POOL = Log(engine.pool.logger.logger,
                        logger_level=config.sqlalchemy.pool_logging_level,
                        channel_level=config.sqlalchemy.pool_logging_level).getlogger()
else:
    logger_DB_POOL = Log(engine.pool.logger,
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
    async def transaction(self, sql_session:AsyncSession=None):
        if sql_session is None:
            async with self.sql_session as sql_session:
                async with sql_session.begin():
                    yield sql_session
        elif not sql_session.in_transaction():
            async with sql_session.begin():
                yield sql_session
        else:
            yield sql_session
        
    async def _execute(self, text:Tuple[str,text], sql_session:AsyncSession=None):
        async with self.transaction(sql_session) as sql_session:
            if isinstance(text, str):
                text = text.replace(':', r'\:')
            result = await sql_session.execute(text)
            return result

    async def _get(self, stmt: Select, one_or_none=False, first=False, all=True, sql_session:AsyncSession=None):
        async with self.transaction(sql_session) as sql_session:
            result: Result = await sql_session.execute(stmt)
            if one_or_none:
                return result.scalar_one_or_none()
            elif first:
                return result.first()
            elif all:
                return result.all()
            else:
                return result
    
    async def _insert(self, instance, many=False, sql_session:AsyncSession=None):
        async with self.transaction(sql_session) as sql_session:
            if many:
                sql_session.add_all(instance)
            else:
                sql_session.add(instance)
                await sql_session.flush()
                return instance.id

    async def _update(self, stmt: Update, sql_session:AsyncSession=None):
        async with self.transaction(sql_session) as sql_session:
            result: Result = await sql_session.execute(stmt)
            return result.rowcount

    async def _insert_or_update(self, insert_stmt: Insert, sql_session:AsyncSession=None, **kwargs) -> int:
        async with self.transaction(sql_session) as sql_session:
            on_duplicate_key_stmt = insert_stmt.on_duplicate_key_update(**kwargs)
            result: CursorResult = await sql_session.execute(on_duplicate_key_stmt)
            return result.lastrowid
            
    async def _delete(self, stmt: Delete, sql_session:AsyncSession=None):
        async with self.transaction(sql_session) as sql_session:
            result: Result = await sql_session.execute(stmt)
            return result.rowcount

    @staticmethod
    def to_dict(result,fields=None):
        if result is None:
            return result
        if fields is None:
            return {c.name: getattr(result[0], c.name) for c in result[0].__table__.columns}
        else:
            return dict(result._mapping)
