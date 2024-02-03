#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 20:18:29

import time

from sqlalchemy import INTEGER, Column, Integer, Text, delete, select
from sqlalchemy.dialects.mysql import TINYINT

from db.basedb import AlchemyMixin, BaseDB


class Tasklog(BaseDB, AlchemyMixin):
    '''
    task log db

    id, taskid, success, ctime, msg
    '''
    __tablename__ = 'tasklog'

    id = Column(Integer, primary_key=True)
    taskid = Column(INTEGER, nullable=False)
    success = Column(TINYINT(1), nullable=False)
    ctime = Column(INTEGER, nullable=False)
    msg = Column(Text)

    def add(self, taskid, success, msg='', sql_session=None):
        now = time.time()

        insert = dict(
            taskid=taskid,
            success=success,
            msg=msg,
            ctime=now,
        )
        return self._insert(Tasklog(**insert), sql_session=sql_session)

    async def list(self, fields=None, limit=1000, to_dict=True, sql_session=None, **kwargs):
        if fields is None:
            _fields = Tasklog
        else:
            _fields = (getattr(Tasklog, field) for field in fields)

        smtm = select(_fields)

        for key, value in kwargs.items():
            smtm = smtm.where(getattr(Tasklog, key) == value)

        if limit:
            smtm = smtm.limit(limit)

        result = await self._get(smtm.order_by(Tasklog.ctime.desc()), sql_session=sql_session)
        if to_dict and result is not None:
            return [self.to_dict(row, fields) for row in result]
        return result

    def delete(self, id, sql_session=None):
        return self._delete(delete(Tasklog).where(Tasklog.id == id), sql_session=sql_session)
