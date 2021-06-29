#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 19:53:09

import config
from .basedb import BaseDB

class SiteDB(BaseDB):
    '''
    Site db

    regEn
    '''
    __tablename__ = 'site'

    def __init__(self, host=config.mysql.host, port=config.mysql.port,
            database=config.mysql.database, user=config.mysql.user, passwd=config.mysql.passwd):
        import mysql.connector
        self.conn = mysql.connector.connect(user=user, password=passwd, host=host, port=port,
                database=database, autocommit=True)

    def add(self):
        insert = dict(regEn = 1)
        return self._insert(**insert)

    def mod(self, id, **kwargs):
        assert id, 'need id'
        return self._update(where="id=%s" % self.placeholder, where_values=(id, ), **kwargs)

    def get(self, id, fields=None):
        assert id, 'need id'
        for task in self._select2dic(what=fields, where='id=%s' % self.placeholder, where_values=(id, )):
            return task
