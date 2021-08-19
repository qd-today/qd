#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 20:12:27

import time
import config
from .basedb import BaseDB

class PRDB(BaseDB):
    '''
    push request db

    id, from_tplid, from_userid, to_tplid, to_userid, status, msg, ctime, mtime, atime
    '''
    __tablename__ = 'push_request'

    PENDING = 0
    CANCEL = 1
    REFUSE = 2
    ACCEPT = 3

    class NOTSET(object): pass

    def __init__(self, host=config.mysql.host, port=config.mysql.port,
            database=config.mysql.database, user=config.mysql.user, passwd=config.mysql.passwd):
        import mysql.connector
        self.conn = mysql.connector.connect(user=user, password=passwd, host=host, port=port,
                database=database, autocommit=True)

    def add(self, from_tplid, from_userid, to_tplid, to_userid, msg=''):
        now = time.time()

        insert = dict(
                from_tplid = from_tplid,
                from_userid = from_userid,
                to_tplid = to_tplid,
                to_userid = to_userid,
                status = PRDB.PENDING,
                msg = msg,
                ctime = now,
                mtime = now,
                atime = now,
                )
        return self._insert(**insert)

    def mod(self, id, **kwargs):
        for each in ('id', 'from_tplid', 'from_userid', 'to_tplid', 'to_userid', 'ctime'):
            assert each not in kwargs, '%s not modifiable' % each

        kwargs['mtime'] = time.time()
        return self._update(where="id=%s" % self.placeholder, where_values=(id, ), **kwargs)

    def get(self, id, fields=None):
        for pr in self._select2dic(what=fields, where='id=%s' % self.placeholder, where_values=(id, )):
            return pr

    def list(self, fields=None, limit=1000, **kwargs):
        where = '1=1'
        where_values = []
        for key, value in kwargs.items():
            if value is None:
                where += ' and %s is %s' % (self.escape(key), self.placeholder)
            else:
                where += ' and %s = %s' % (self.escape(key), self.placeholder)
            where_values.append(value)
        where +=' ORDER BY mtime DESC'
        return self._select2dic(what=fields, where=where, where_values=where_values, limit=limit)
