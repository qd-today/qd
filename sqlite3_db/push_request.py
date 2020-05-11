#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>

import config
from db.push_request import PRDB as _PRDB
from .basedb import BaseDB


class PRDB(_PRDB, BaseDB):
    def __init__(self, path=config.sqlite3.path):
        self.path = path
        self._execute('''CREATE TABLE IF NOT EXISTS `%s` (
          `id` INTEGER PRIMARY KEY,
          `from_tplid` INT UNSIGNED NOT NULL,
          `from_userid` INT UNSIGNED NOT NULL,
          `to_tplid` INT UNSIGNED NULL,
          `to_userid` INT UNSIGNED NULL,
          `status` TINYINT NOT NULL DEFAULT 0,
          `msg` VARCHAR(1024) NULL,
          `ctime` INT UNSIGNED NOT NULL,
          `mtime` INT UNSIGNED NOT NULL,
          `atime` INT UNSIGNED NOT NULL
        )''' % self.__tablename__)

        for each in ('to_userid', 'status'):
            self._execute('''CREATE INDEX IF NOT EXISTS `ix_%s_%s` ON %s (%s)''' % (
                self.__tablename__, each, self.__tablename__, each))
