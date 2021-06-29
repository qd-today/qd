#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 19:53:09

import time
import config
from .basedb import BaseDB

class TaskDB(BaseDB):
    '''
    task db

    id, tplid, userid, disabled, init_env, env, session, last_success, success_count, failed_count, last_failed, next, ctime, mtime
    '''
    __tablename__ = 'task'

    def __init__(self, host=config.mysql.host, port=config.mysql.port,
            database=config.mysql.database, user=config.mysql.user, passwd=config.mysql.passwd):
        import mysql.connector
        self.conn = mysql.connector.connect(user=user, password=passwd, host=host, port=port,
                database=database, autocommit=True)

    def add(self, tplid, userid, env):
        now = time.time()

        insert = dict(
                tplid = tplid,
                userid = userid,
                disabled = 0,
                init_env = env,
                last_success = None,
                last_failed = None,
                success_count = 0,
                failed_count = 0,
                next = None,
                ctime = now,
                mtime = now,
                ontime='00:10',
                ontimeflg=0,
                )
        return self._insert(**insert)

    def mod(self, id, **kwargs):
        assert id, 'need id'
        assert 'id' not in kwargs, 'id not modifiable'
        assert 'ctime' not in kwargs, 'ctime not modifiable'

        kwargs['mtime'] = time.time()
        return self._update(where="id=%s" % self.placeholder, where_values=(id, ), **kwargs)

    def get(self, id, fields=None):
        assert id, 'need id'
        for task in self._select2dic(what=fields, where='id=%s' % self.placeholder, where_values=(id, )):
            return task

    def list(self, userid, fields=None, limit=1000):
        return self._select2dic(what=fields, where='userid=%s' % self.placeholder, where_values=(userid, ), limit=limit)

    def delete(self, id):
        self._delete(where="id=%s" % self.placeholder, where_values=(id, ))

    def scan(self, now=None, fields=None):
        if now is None:
            now = time.time()
        return list(self._select2dic(what=fields, where="`next` < %s" % self.placeholder, where_values=(now, )))
