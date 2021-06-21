#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>

import config
from db.pubtpl import PubTplDB as _PubTplDB
from .basedb import BaseDB


class PubTplDB(_PubTplDB, BaseDB):
    def __init__(self, path=config.sqlite3.path):
        self.path = path
        self._execute('''CREATE TABLE IF NOT EXISTS `%s` (
          `id` INTEGER NOT NULL PRIMARY KEY,
          `name` TEXT NOT NULL DEFAULT '',
          `author` TEXT NOT NULL DEFAULT '',
          `comments` TEXT NOT NULL DEFAULT '',
          `content` TEXT NOT NULL DEFAULT '',
          `filename` TEXT NOT NULL DEFAULT '',
          `date` TEXT NOT NULL DEFAULT '',
          `version` TEXT NOT NULL DEFAULT '',
          `url` TEXT NOT NULL DEFAULT '',
          `update` TEXT NOT NULL DEFAULT '',
          `reponame` TEXT NOT NULL DEFAULT '',
          `repourl` TEXT NOT NULL DEFAULT '',
          `repoacc` TEXT NOT NULL DEFAULT '',
          `repobranch` TEXT NOT NULL DEFAULT ''
        )''' % self.__tablename__)

        
