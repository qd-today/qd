#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: a76yyyy<q981331502@163.com>
# Created on 2022-08-12 18:41:09

import time
import umsgpack

import config
from libs import utils
from .basedb import BaseDB, logger_DB
class NotePadDB(BaseDB):
    '''
    Site db

    regEn
    '''
    __tablename__ = 'notepad'

    def add(self, insert):
        return self._insert(**insert)

    def mod(self, userid, notepadid, **kwargs):
        assert userid, 'need userid'
        assert notepadid, 'need notepadid'
        return self._update(where="userid=%s and notepadid=%s" % (self.placeholder, self.placeholder) , where_values=(userid, notepadid), **kwargs)

    def get(self, userid, notepadid, fields=None):
        assert userid, 'need userid'
        assert notepadid, 'need notepadid'
        for notepad in self._select2dic(what=fields, where="userid=%s and notepadid=%s" % (self.placeholder, self.placeholder), where_values=(userid, notepadid)):
            return notepad
            
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
    
    def delete(self, userid, notepadid):
        self._delete(where="userid=%s and notepadid=%s" % (self.placeholder, self.placeholder), where_values=(userid, notepadid))