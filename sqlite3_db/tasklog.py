#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>
#

import config
from db.tasklog import TaskLogDB as _TaskLogDB
from .basedb import BaseDB


class TaskLogDB(_TaskLogDB, BaseDB):
    def __init__(self, path=config.sqlite3.path):
        self.path = path
        self._execute('''CREATE TABLE IF NOT EXISTS `%s` (
          `id` INTEGER PRIMARY KEY,
          `taskid` INT UNSIGNED NOT NULL,
          `success` TINYINT(1) NOT NULL,
          `ctime` INT UNSIGNED NOT NULL,
          `msg` TEXT NULL
        )''' % self.__tablename__)
