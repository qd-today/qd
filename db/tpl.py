#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-07 22:27:07

import time
import config
from .basedb import BaseDB

class TPLDB(BaseDB):
    '''
    tpl db

    id, userid, siteurl, sitename, banner, disabled, public, fork, har, tpl, variables, interval, note, ctime, mtime, atime, last_success
    '''
    __tablename__ = 'tpl'

    def __init__(self, host=config.mysql.host, port=config.mysql.port,
            database=config.mysql.database, user=config.mysql.user, passwd=config.mysql.passwd):
        import mysql.connector
        self.conn = mysql.connector.connect(user=user, password=passwd, host=host, port=port,
                database=database, autocommit=True)

    def add(self, userid, har, tpl, variables, interval=None):
        now = time.time()

        insert = dict(
                userid = userid,
                siteurl = None,
                sitename = None,
                banner = None,
                disabled = 0,
                public = 0,
                fork = None,
                har = har,
                tpl = tpl,
                variables = variables,
                interval = interval,
                ctime = now,
                mtime = now,
                atime = now,
                last_success = None,
                )
        return self._insert(**insert)

    def mod(self, id, **kwargs):
        return self._update(where="id=%s" % self.placeholder, where_values=(id, ), **kwargs)

    def get(self, id, fields=None):
        for tpl in self._select2dic(what=fields, where='id=%s' % self.placeholder, where_values=(id, )):
            return tpl

    def delete(self, id):
        self._delete(where="id=%s" % self.placeholder, where_values=(id, ))

    def incr_success(self, id):
        self._execute('UPDATE %s SET success_count=success_count+1, last_success=%d WHERE `id`=%d' % (
            self.escape(self.__tablename__), time.time(), int(id)))

    def incr_failed(self, id):
        self._execute('UPDATE %s SET failed_count=failed_count+1 WHERE `id`=%d' % (
            self.escape(self.__tablename__), int(id)))

    def list(self, fields=None, limit=None, **kwargs):
        where = '1=1'
        where_values = []
        for key, value in kwargs.items():
            if value is None:
                where += ' and %s is %s' % (self.escape(key), self.placeholder)
            else:
                where += ' and %s = %s' % (self.escape(key), self.placeholder)
            where_values.append(value)
        for tpl in self._select2dic(what=fields, where=where, where_values=where_values, limit=limit):
            yield tpl
