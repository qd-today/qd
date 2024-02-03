#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 20:12:27

import time

from sqlalchemy import INTEGER, Column, Integer, String, select, text, update
from sqlalchemy.dialects.mysql import TINYINT

from db.basedb import AlchemyMixin, BaseDB


class PushRequest(BaseDB, AlchemyMixin):
    '''
    push request db

    id, from_tplid, from_userid, to_tplid, to_userid, status, msg, ctime, mtime, atime
    '''
    __tablename__ = 'push_request'

    id = Column(Integer, primary_key=True)
    from_tplid = Column(INTEGER, nullable=False)
    from_userid = Column(INTEGER, nullable=False)
    status = Column(TINYINT, nullable=False, server_default=text("'0'"))
    ctime = Column(INTEGER, nullable=False)
    mtime = Column(INTEGER, nullable=False)
    atime = Column(INTEGER, nullable=False)
    to_tplid = Column(INTEGER)
    to_userid = Column(INTEGER)
    msg = Column(String(1024))

    PENDING = 0
    CANCEL = 1
    REFUSE = 2
    ACCEPT = 3

    class NOTSET(object):
        pass

    def add(self, from_tplid, from_userid, to_tplid, to_userid, msg='', sql_session=None):
        now = time.time()

        insert = dict(
            from_tplid=from_tplid,
            from_userid=from_userid,
            to_tplid=to_tplid,
            to_userid=to_userid,
            status=PushRequest.PENDING,
            msg=msg,
            ctime=now,
            mtime=now,
            atime=now,
        )
        return self._insert(PushRequest(**insert), sql_session=sql_session)

    def mod(self, id, sql_session=None, **kwargs):
        for each in ('id', 'from_tplid', 'from_userid', 'to_userid', 'ctime'):
            assert each not in kwargs, f'{each} not modifiable'

        kwargs['mtime'] = time.time()
        return self._update(update(PushRequest).where(PushRequest.id == id).values(**kwargs), sql_session=sql_session)

    async def get(self, id, fields=None, one_or_none=False, first=True, to_dict=True, sql_session=None):
        assert id, 'need id'
        if fields is None:
            _fields = PushRequest
        else:
            _fields = (getattr(PushRequest, field) for field in fields)

        smtm = select(_fields).where(PushRequest.id == id)

        result = await self._get(smtm, one_or_none=one_or_none, first=first, sql_session=sql_session)
        if to_dict and result is not None:
            return self.to_dict(result, fields)
        return result

    async def list(self, fields=None, limit=1000, to_dict=True, sql_session=None, **kwargs):
        if fields is None:
            _fields = PushRequest
        else:
            _fields = (getattr(PushRequest, field) for field in fields)

        smtm = select(_fields)

        for key, value in kwargs.items():
            smtm = smtm.where(getattr(PushRequest, key) == value)

        if limit:
            smtm = smtm.limit(limit)

        result = await self._get(smtm.order_by(PushRequest.mtime.desc()), sql_session=sql_session)
        if to_dict and result is not None:
            return [self.to_dict(row, fields) for row in result]
        return result
