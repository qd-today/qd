#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.com>
#         http://binux.me
# Created on 2012-08-30 17:43:49

import logging
logger = logging.getLogger('qiandao.basedb')

import os
import sqlite3
import threading
from db.basedb import BaseDB as _BaseDB


def to_unicode(string):
    if isinstance(string, str):
        return string
    try:
        return string.decode('utf8')
    except UnicodeDecodeError:
        return string


class BaseDB(_BaseDB):
    '''
    BaseDB

    dbcur should be overwirte
    '''
    placeholder = '?'
    conn = None
    last_pid = 0

    @staticmethod
    def escape(string):
        return '`%s`' % string

    @property
    def dbcur(self):
        pid = (os.getpid(), threading.current_thread().ident)
        if not (self.conn and pid == self.last_pid):
            self.last_pid = pid
            self.conn = sqlite3.connect(self.path, isolation_level=None)
            self.conn.text_factory = to_unicode
        return self.conn.cursor()
