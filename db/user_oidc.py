#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Created on 2026-11-07

import time

from sqlalchemy import (
    INTEGER,
    Column,
    Integer,
    String,
    UniqueConstraint,
    delete,
    select,
    update,
)

from db.basedb import AlchemyMixin, BaseDB


class UserOidc(BaseDB, AlchemyMixin):
    '''
    UserOidc db

    OIDC 账号绑定关系: (provider, subject) -> userid
    '''
    __tablename__ = 'user_oidc'
    __table_args__ = (
        UniqueConstraint('provider', 'subject', name='uq_user_oidc_provider_subject'),
    )

    id = Column(Integer, primary_key=True)
    userid = Column(Integer, nullable=False, index=True)
    provider = Column(String(64), nullable=False, index=True)
    subject = Column(String(255), nullable=False, index=True)
    email = Column(String(256))
    ctime = Column(INTEGER, nullable=False)
    mtime = Column(INTEGER, nullable=False)

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
