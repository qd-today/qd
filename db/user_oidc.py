#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Created on 2026-11-07

import time

from sqlalchemy import (
    Column,
    Integer,
    String,
    UniqueConstraint,
    delete,
    select,
    update,
)
from sqlalchemy.dialects import mysql

from db.basedb import AlchemyMixin, BaseDB


class UserOidc(BaseDB, AlchemyMixin):
    '''
    UserOidc db

    OIDC 账号绑定关系: (provider, subject) -> userid
    '''
    __tablename__ = 'user_oidc'
    __table_args__ = (
        UniqueConstraint('provider', 'subject', name='uq_user_oidc_provider_subject'),
        # 显式声明表字符集: 库默认不可依赖 (既有表 utf8mb3/utf8mb4 并存),
        # latin1 库下非 ASCII 的 subject/email 会 1366 Incorrect string value
        {'mysql_charset': 'utf8mb4'},
    )

    id = Column(Integer, primary_key=True)
    userid = Column(Integer, nullable=False, index=True)
    # provider/subject 必须大小写敏感: OIDC Core 1.0 §2 规定 sub 大小写敏感,
    # 库默认 collation (MySQL 常为 *_ai_ci) 会让仅大小写不同的 sub 互相命中,
    # 导致登录到对方账号 (且跳过 email_verified 门禁) 或唯一键误判重复。
    # utf8mb4_bin 兼容 MySQL 5.7/8.x/MariaDB; SQLite 无此 collation 名,
    # 用 BINARY 变体 (SQLite 默认即为 BINARY 比较, 此处显式声明以固定语义)。
    provider = Column(
        String(64, collation='utf8mb4_bin').with_variant(String(64, collation='BINARY'), 'sqlite'),
        nullable=False, index=True,
    )
    subject = Column(
        String(255, collation='utf8mb4_bin').with_variant(String(255, collation='BINARY'), 'sqlite'),
        nullable=False, index=True,
    )
    email = Column(String(256))
    # 对齐仓库既有 DDL 口径 (db/db_converter.py 的 task/tasklog 等表均为 INT UNSIGNED);
    # SQLite 无 unsigned 概念, 用 Integer 变体。
    ctime = Column(mysql.INTEGER(unsigned=True).with_variant(Integer, 'sqlite'), nullable=False)
    mtime = Column(mysql.INTEGER(unsigned=True).with_variant(Integer, 'sqlite'), nullable=False)

    async def add(self, userid, provider, subject, email=None, sql_session=None):
        assert userid, 'need userid'
        assert provider, 'need provider'
        assert subject, 'need subject'
        now = int(time.time())
        insert = dict(
            userid=userid,
            provider=provider,
            subject=subject,
            email=email,
            ctime=now,
            mtime=now,
        )
        return await self._insert(UserOidc(**insert), sql_session=sql_session)

    async def get(self, id=None, userid=None, provider=None, subject=None, fields=None, one_or_none=False, first=True, to_dict=True, sql_session=None):
        assert id or userid or (provider and subject), 'need id or userid or (provider and subject)'

        if fields is None:
            _fields = UserOidc
        else:
            _fields = (getattr(UserOidc, field) for field in fields)

        smtm = select(_fields)
        if id is not None:
            smtm = smtm.where(UserOidc.id == id)
        if userid is not None:
            smtm = smtm.where(UserOidc.userid == userid)
        if provider is not None:
            smtm = smtm.where(UserOidc.provider == provider)
        if subject is not None:
            smtm = smtm.where(UserOidc.subject == subject)

        result = await self._get(smtm, one_or_none=one_or_none, first=first, sql_session=sql_session)
        if to_dict and result is not None:
            return self.to_dict(result, fields)
        return result

    async def list(self, fields=None, limit=None, to_dict=True, sql_session=None, **kwargs):
        if fields is None:
            _fields = UserOidc
        else:
            _fields = (getattr(UserOidc, field) for field in fields)

        smtm = select(_fields)

        for key, value in kwargs.items():
            smtm = smtm.where(getattr(UserOidc, key) == value)

        if limit:
            smtm = smtm.limit(limit)

        result = await self._get(smtm, sql_session=sql_session)
        if to_dict and result is not None:
            return [self.to_dict(row, fields) for row in result]
        return result

    async def mod(self, id, sql_session=None, **kwargs):
        assert id, 'need id'
        for key in ('id', 'userid', 'provider', 'subject'):
            assert key not in kwargs, 'cannot mod %s' % key
        if 'mtime' not in kwargs:
            kwargs['mtime'] = int(time.time())
        return await self._update(update(UserOidc).where(UserOidc.id == id).values(**kwargs), sql_session=sql_session)

    async def delete(self, id, sql_session=None):
        assert id, 'need id'
        return await self._delete(delete(UserOidc).where(UserOidc.id == id), sql_session=sql_session)

    async def delete_by_user_provider(self, userid, provider, sql_session=None):
        assert userid, 'need userid'
        assert provider, 'need provider'
        return await self._delete(delete(UserOidc).where(UserOidc.userid == userid).where(UserOidc.provider == provider), sql_session=sql_session)
