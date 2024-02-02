#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-07 22:27:07

import time

from sqlalchemy import (INTEGER, Column, Integer, String, Text, delete, select,
                        text, update)
from sqlalchemy.dialects.mysql import MEDIUMBLOB, TINYINT

from db.basedb import AlchemyMixin, BaseDB


class Tpl(BaseDB, AlchemyMixin):
    '''
    tpl db

    id, userid, siteurl, sitename, banner, disabled, public, fork, har, tpl, variables, interval, note, ctime, mtime, atime, last_success
    '''
    __tablename__ = 'tpl'

    id = Column(Integer, primary_key=True)
    disabled = Column(TINYINT(1), nullable=False, server_default=text("'0'"))
    public = Column(TINYINT(1), nullable=False, server_default=text("'0'"))
    lock = Column(TINYINT(1), nullable=False, server_default=text("'0'"))
    success_count = Column(INTEGER, nullable=False, server_default=text("'0'"))
    failed_count = Column(INTEGER, nullable=False, server_default=text("'0'"))
    ctime = Column(INTEGER, nullable=False)
    mtime = Column(INTEGER, nullable=False)
    atime = Column(INTEGER, nullable=False)
    updateable = Column(INTEGER, nullable=False, server_default=text("'0'"))
    _groups = Column(String(256), nullable=False, server_default=text("'None'"))
    userid = Column(INTEGER)
    siteurl = Column(String(256))
    sitename = Column(String(128))
    banner = Column(String(1024))
    fork = Column(INTEGER)
    har = Column(MEDIUMBLOB)
    tpl = Column(MEDIUMBLOB)
    variables = Column(Text)
    init_env = Column(Text)
    interval = Column(INTEGER)
    note = Column(String(1024))
    last_success = Column(INTEGER)
    tplurl = Column(String(1024), server_default=text("''"))

    def add(self, userid, har, tpl, variables, init_env, interval=None, sql_session=None):
        now = time.time()

        insert = dict(
            userid=userid,
            siteurl=None,
            sitename=None,
            banner=None,
            disabled=0,
            public=0,
            fork=None,
            har=har,
            tpl=tpl,
            variables=variables,
            init_env=init_env,
            interval=interval,
            ctime=now,
            mtime=now,
            atime=now,
            last_success=None,
        )
        return self._insert(Tpl(**insert), sql_session=sql_session)

    def mod(self, id, sql_session=None, **kwargs):
        return self._update(update(Tpl).where(Tpl.id == id).values(**kwargs), sql_session=sql_session)

    async def get(self, id, fields=None, one_or_none=False, first=True, to_dict=True, sql_session=None):
        assert id, 'need id'
        if fields is None:
            _fields = Tpl
        else:
            _fields = (getattr(Tpl, field) for field in fields)

        smtm = select(_fields).where(Tpl.id == id)

        result = await self._get(smtm, one_or_none=one_or_none, first=first, sql_session=sql_session)
        if to_dict and result is not None:
            return self.to_dict(result, fields)
        return result

    async def incr_success(self, id, sql_session=None):
        result = await self._execute(text('UPDATE tpl SET success_count=success_count+1, last_success=:last_success WHERE id=:id').
                                     bindparams(id=int(id), last_success=int(time.time())), sql_session=sql_session)
        return result.rowcount

    async def incr_failed(self, id, sql_session=None):
        result = await self._execute(text('UPDATE tpl SET failed_count=failed_count+1 WHERE id=:id').
                                     bindparams(id=int(id)), sql_session=sql_session)
        return result.rowcount

    async def list(self, fields=None, limit=None, to_dict=True, sql_session=None, **kwargs):
        if fields is None:
            _fields = Tpl
        else:
            _fields = (getattr(Tpl, field) for field in fields)

        smtm = select(_fields)

        for key, value in kwargs.items():
            smtm = smtm.where(getattr(Tpl, key) == value)

        if limit:
            smtm = smtm.limit(limit)

        result = await self._get(smtm, sql_session=sql_session)
        if to_dict and result is not None:
            return [self.to_dict(row, fields) for row in result]
        return result

    def delete(self, id, sql_session=None):
        return self._delete(delete(Tpl).where(Tpl.id == id), sql_session=sql_session)
