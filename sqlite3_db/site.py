#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>

import config
from db.site import SiteDB as _SiteDB
from .basedb import BaseDB


class SiteDB(_SiteDB, BaseDB):
    def __init__(self, path=config.sqlite3.path):
        self.path = path
        self._execute('''CREATE TABLE IF NOT EXISTS `%s` (
          `id` INTEGER NOT NULL PRIMARY KEY,
          `regEn` INT UNSIGNED NOT NULL DEFAULT 1,
          `MustVerifyEmailEn` INT UNSIGNED NOT NULL DEFAULT 0,
          `logDay` INT UNSIGNED NOT NULL DEFAULT 365,
          `repos` TEXT NOT NULL DEFAULT '{"repos":[{"reponame":"default","repourl":"https://github.com/qiandao-today/templates","repobranch":"master","repoacc":true}], "lastupdate":0}'
        )''' % self.__tablename__)

        
