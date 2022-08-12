#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>

import config
from db.notepad import NotePadDB as _NotePadDB
from .basedb import BaseDB


class NotePadDB(_NotePadDB, BaseDB):
    def __init__(self, path=config.sqlite3.path):
        self.path = path
        self._execute('''CREATE TABLE IF NOT EXISTS `%s` (
          `id` INTEGER NOT NULL PRIMARY KEY,
          `userid` INTEGER NOT NULL ,
          `notepadid` INTEGER NOT NULL ,
          `content` TEXT NULL
        )''' % self.__tablename__)
