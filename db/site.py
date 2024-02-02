#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 19:53:09

from sqlalchemy import INTEGER, Column, Integer, Text, select, text, update

from db.basedb import AlchemyMixin, BaseDB


class Site(BaseDB, AlchemyMixin):
    '''
    Site db

    regEn
    '''
    __tablename__ = 'site'

    id = Column(Integer, primary_key=True)
    regEn = Column(INTEGER, nullable=False, server_default=text("'1'"))
    MustVerifyEmailEn = Column(INTEGER, nullable=False, server_default=text("'0'"))
    logDay = Column(INTEGER, nullable=False, server_default=text("'365'"))
    repos = Column(Text, nullable=False)

    def add(self, sql_session=None):
        insert = dict(regEn=1)
        return self._insert(Site(**insert), sql_session=sql_session)

    def mod(self, id, sql_session=None, **kwargs):
        assert id, 'need id'
        return self._update(update(Site).where(Site.id == id).values(**kwargs), sql_session=sql_session)

    async def get(self, id, fields=None, one_or_none=False, first=True, to_dict=True, sql_session=None):
        assert id, 'need id'
        if fields is None:
            _fields = Site
        else:
            _fields = (getattr(Site, field) for field in fields)

        smtm = select(_fields).where(Site.id == id)

        result = await self._get(smtm, one_or_none=one_or_none, first=first, sql_session=sql_session)
        if to_dict and result is not None:
            return self.to_dict(result, fields)
        return result
