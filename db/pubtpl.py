#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 19:53:09

import time
import logging
import umsgpack

import config
from libs import utils
from .basedb import BaseDB

class PubTplDB(BaseDB):
    '''
    Site db

    regEn
    '''
    __tablename__ = 'pubtpl'

    def __init__(self, host=config.mysql.host, port=config.mysql.port,
            database=config.mysql.database, user=config.mysql.user, passwd=config.mysql.passwd):
        import mysql.connector
        self.conn = mysql.connector.connect(user=user, password=passwd, host=host, port=port,
                database=database, autocommit=True)

    def add(self, insert):
        return self._insert(**insert)

    def mod(self, id, **kwargs):
        assert id, 'need id'
        return self._update(where="id=%s" % self.placeholder, where_values=(id, ), **kwargs)

    def get(self, id, fields=None):
        assert id, 'need id'
        for task in self._select2dic(what=fields, where='id=%s' % self.placeholder, where_values=(id, )):
            return task
            
    def list(self, fields=None, limit=1000, **kwargs):
        where = '1=1'
        where_values = []
        for key, value in kwargs.items():
            if value is None:
                where += ' and %s is %s' % (self.escape(key), self.placeholder)
            else:
                where += ' and %s = %s' % (self.escape(key), self.placeholder)
            where_values.append(value)
        
        return self._select2dic(tablename=self.__tablename__, what=fields, where=where, where_values=where_values, limit=limit)
    
    def delete(self, id):
        self._delete(where="id=%s" % self.placeholder, where_values=(id, ))