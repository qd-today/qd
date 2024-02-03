#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 19:53:09

import time

from sqlalchemy import (INTEGER, Column, Integer, LargeBinary, String, delete,
                        select, text, update)
from sqlalchemy.dialects.mysql import TINYINT

import config
from db.basedb import AlchemyMixin, BaseDB


class Task(BaseDB, AlchemyMixin):
    '''
    task db

    id, tplid, userid, disabled, init_env, env, session, retry_count, retry_interval, last_success, success_count, failed_count, last_failed, next, ctime, mtime
    '''
    __tablename__ = 'task'
    id = Column(Integer, primary_key=True)
    tplid = Column(INTEGER, nullable=False)
    userid = Column(INTEGER, nullable=False)
    disabled = Column(TINYINT(1), nullable=False, server_default=text("'0'"))
    retry_count = Column(Integer, nullable=False, server_default=text("'8'"))
    success_count = Column(INTEGER, nullable=False, server_default=text("'0'"))
    failed_count = Column(INTEGER, nullable=False, server_default=text("'0'"))
    last_failed_count = Column(INTEGER, nullable=False, server_default=text("'0'"))
    ctime = Column(INTEGER, nullable=False)
    mtime = Column(INTEGER, nullable=False)
    ontimeflg = Column(INTEGER, nullable=False, server_default=text("'0'"))
    ontime = Column(String(256), nullable=False, server_default=text("'00:10:00'"))
    _groups = Column(String(256), nullable=False, server_default=text("'None'"))
    pushsw = Column(String(128), nullable=False, server_default=text('\'{"logen":false,"pushen":true}\''))
    newontime = Column(String(256), nullable=False, server_default=text('\'{"sw":false,"time":"00:10:10","randsw":false,"tz1":0,"tz2":0}\''))
    init_env = Column(LargeBinary)
    env = Column(LargeBinary)
    session = Column(LargeBinary)
    retry_interval = Column(INTEGER)
    last_success = Column(INTEGER)
    last_failed = Column(INTEGER)
    next = Column(INTEGER)
    note = Column(String(256))

    def add(self, tplid, userid, env, sql_session=None):
        now = time.time()

        insert = dict(
            tplid=tplid,
            userid=userid,
            disabled=0,
            init_env=env,
            retry_count=config.task_max_retry_count,
            retry_interval=None,
            last_success=None,
            last_failed=None,
            success_count=0,
            failed_count=0,
            next=None,
            ctime=now,
            mtime=now,
            ontime='00:10',
            ontimeflg=0,
        )
        return self._insert(Task(**insert), sql_session=sql_session)

    def mod(self, id, sql_session=None, **kwargs):
        assert id, 'need id'
        assert 'id' not in kwargs, 'id not modifiable'
        assert 'ctime' not in kwargs, 'ctime not modifiable'

        kwargs['mtime'] = time.time()
        return self._update(update(Task).where(Task.id == id).values(**kwargs), sql_session=sql_session)

    async def get(self, id, fields=None, one_or_none=False, first=True, to_dict=True, sql_session=None):
        assert id, 'need id'
        if fields is None:
            _fields = Task
        else:
            _fields = (getattr(Task, field) for field in fields)

        smtm = select(_fields).where(Task.id == id)

        result = await self._get(smtm, one_or_none=one_or_none, first=first, sql_session=sql_session)
        if to_dict and result is not None:
            return self.to_dict(result, fields)
        return result

    async def list(self, userid=None, fields=None, limit=1000, to_dict=True, scan=False, scan_time=None, sql_session=None, **kwargs):
        if fields is None:
            _fields = Task
        else:
            _fields = (getattr(Task, field) for field in fields)

        smtm = select(_fields)
        if userid is not None:
            smtm = smtm.where(Task.userid == userid)

        if scan and scan_time is not None:
            smtm = smtm.where(Task.next <= scan_time)

        for key, value in kwargs.items():
            smtm = smtm.where(getattr(Task, key) == value)

        if limit:
            smtm = smtm.limit(limit)

        result = await self._get(smtm, sql_session=sql_session)
        if to_dict and result is not None:
            return [self.to_dict(row, fields) for row in result]
        return result

    def delete(self, id, sql_session=None):
        return self._delete(delete(Task).where(Task.id == id), sql_session=sql_session)

    async def scan(self, now=None, fields=None, sql_session=None):
        if now is None:
            now = time.time()
        return await self.list(fields=fields, scan=True, scan_time=now, limit=None, sql_session=sql_session)
