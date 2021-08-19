#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>
#
# Distributed under terms of the MIT license.


import config
from db.tpl import TPLDB as _TPLDB
from .basedb import BaseDB


class TPLDB(_TPLDB, BaseDB):
    def __init__(self, path=config.sqlite3.path):
        self.path = path
        self._execute('''CREATE TABLE IF NOT EXISTS `%s` (
          `id` INTEGER PRIMARY KEY,
          `userid` INT UNSIGNED NULL,
          `siteurl` VARCHAR(256) NULL,
          `sitename` VARCHAR(128) NULL,
          `banner` VARCHAR(1024) NULL,
          `disabled` TINYINT(1) NOT NULL DEFAULT 0,
          `public` TINYINT(1) NOT NULL DEFAULT 0,
          `lock` TINYINT(1) NOT NULL DEFAULT 0,
          `fork` INT UNSIGNED NULL,
          `har` MEDIUMBLOB NULL,
          `tpl` MEDIUMBLOB NULL,
          `variables` TEXT NULL,
          `interval` INT UNSIGNED NULL,
          `note` VARCHAR(1024) NULL,
          `success_count` INT UNSIGNED NOT NULL DEFAULT 0,
          `failed_count` INT UNSIGNED NOT NULL DEFAULT 0,
          `last_success` INT UNSIGNED NULL,
          `ctime` INT UNSIGNED NOT NULL,
          `mtime` INT UNSIGNED NOT NULL,
          `atime` INT UNSIGNED NOT NULL,
          `tplurl` VARCHAR(1024) NULL DEFAULT '',
          `updateable` INT UNSIGNED NOT NULL DEFAULT 0,
          `_groups` VARCHAR(256) NOT NULL DEFAULT 'None'
        )''' % self.__tablename__)

        for each in ('siteurl', 'sitename', 'public'):
            self._execute('''CREATE INDEX IF NOT EXISTS `ix_%s_%s` ON %s (%s)''' % (
                self.__tablename__, each, self.__tablename__, each))
