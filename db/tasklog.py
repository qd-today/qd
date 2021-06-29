#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 20:18:29

import time
import logging

import config
from libs import utils
from .basedb import BaseDB

class TaskLogDB(BaseDB):
    '''
    task log db

    id, taskid, success, ctime, msg
    '''
    __tablename__ = 'tasklog'

    def __init__(self, host=config.mysql.host, port=config.mysql.port,
            database=config.mysql.database, user=config.mysql.user, passwd=config.mysql.passwd):
        import mysql.connector
        self.conn = mysql.connector.connect(user=user, password=passwd, host=host, port=port,
                database=database, autocommit=True)

    def add(self, taskid, success, msg=''):
        now = time.time()

        insert = dict(
                taskid = taskid,
                success = success,
                msg = msg,
                ctime = now,
                )
        return self._insert(**insert)

    def list(self, fields=None, limit=1000, **kwargs):
        where = '1=1'
        where_values = []
        for key, value in kwargs.items():
            if value is None:
                where += ' and %s is %s ORDER BY ctime DESC' % (self.escape(key), self.placeholder)
            else:
                where += ' and %s = %s ORDER BY ctime DESC' % (self.escape(key), self.placeholder)
            where_values.append(value)
        for tasklog in self._select2dic(what=fields, where=where, where_values=where_values, limit=limit):
            yield tasklog
    
    def delete(self, id):
        self._delete(where="id=%s" % self.placeholder, where_values=(id, ))