#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 19:53:09

from sqlalchemy import Column, Integer, Text, delete, select, update

from db.basedb import AlchemyMixin, BaseDB


class Pubtpl(BaseDB, AlchemyMixin):
    '''
    Site db

    regEn
    '''
    __tablename__ = 'pubtpl'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    author = Column(Text)
    comments = Column(Text)
    content = Column(Text)
    filename = Column(Text)
    date = Column(Text)
    version = Column(Text)
    url = Column(Text)
    update = Column(Text)
    reponame = Column(Text)
    repourl = Column(Text)
    repoacc = Column(Text)
    repobranch = Column(Text)
    commenturl = Column(Text)

    def add(self, insert, sql_session=None):
        return self._insert(Pubtpl(**insert), sql_session=sql_session)

    def mod(self, id, sql_session=None, **kwargs):
        assert id, 'need id'
        return self._update(update(Pubtpl).where(Pubtpl.id == id).values(**kwargs), sql_session=sql_session)

    async def get(self, id, fields=None, one_or_none=False, first=True, to_dict=True, sql_session=None):
        assert id, 'need id'
        if fields is None:
            _fields = Pubtpl
        else:
            _fields = (getattr(Pubtpl, field) for field in fields)

        smtm = select(_fields).where(Pubtpl.id == id)

        result = await self._get(smtm, one_or_none=one_or_none, first=first, sql_session=sql_session)
        if to_dict and result is not None:
            return self.to_dict(result, fields)
        return result

    async def list(self, fields=None, limit=1000, to_dict=True, sql_session=None, **kwargs):
        if fields is None:
            _fields = Pubtpl
        else:
            _fields = (getattr(Pubtpl, field) for field in fields)

        smtm = select(_fields)

        for key, value in kwargs.items():
            smtm = smtm.where(getattr(Pubtpl, key) == value)

        if limit:
            smtm = smtm.limit(limit)

        result = await self._get(smtm, sql_session=sql_session)
        if to_dict and result is not None:
            return [self.to_dict(row, fields) for row in result]
        return result

    def delete(self, id, sql_session=None):
        return self._delete(delete(Pubtpl).where(Pubtpl.id == id), sql_session=sql_session)
