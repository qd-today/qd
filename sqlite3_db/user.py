#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>

import config
from db.user import UserDB as _UserDB
from .basedb import BaseDB


class UserDB(_UserDB, BaseDB):
    def __init__(self, path=config.sqlite3.path):
        self.path = path
        self._execute('''CREATE TABLE IF NOT EXISTS `%s` (
          `id` INTEGER PRIMARY KEY,
          `email` VARCHAR(256) NOT NULL,
          `email_verified` TINYINT(1) NOT NULL DEFAULT 0,
          `password` VARBINARY(128) NOT NULL,
          `password_md5` VARBINARY(128) NOT NULL DEFAULT '',
          `userkey` VARBINARY(128) NOT NULL,
          `nickname` VARCHAR(64) NULL,
          `role` VARCHAR(128) NULL,
          `ctime` INT UNSIGNED NOT NULL,
          `mtime` INT UNSIGNED NOT NULL,
          `atime` INT UNSIGNED NOT NULL,
          `cip` VARBINARY(16) NOT NULL,
          `mip` VARBINARY(16) NOT NULL,
          `aip` VARBINARY(16) NOT NULL,
          `skey` VARBINARY(128) NOT NULL DEFAULT '',
          `barkurl` VARBINARY(128) NOT NULL DEFAULT '',
          `wxpusher` VARBINARY(128) NOT NULL DEFAULT '',
          `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1,
          `logtime`  VARBINARY(1024) NOT NULL DEFAULT '{\"en\":false,\"time\":\"20:00:00\",\"ts\":0,\"schanEn\":false,\"WXPEn\":false}',
          `status`  VARBINARY(1024) NOT NULL DEFAULT 'Enable',
          `notepad` TEXT NOT NULL DEFAULT '',
          `diypisher` VARBINARY(1024) NOT NULL DEFAULT '',
          `qywx_token` VARBINARY(1024) NOT NULL DEFAULT '',
          `tg_token` VARBINARY(1024) NOT NULL DEFAULT '',
          `dingding_token` VARBINARY(1024) NOT NULL DEFAULT '',
          `push_batch`  VARBINARY(1024) NOT NULL DEFAULT '{\"sw\":false,\"time\":0,\"delta\":86400}'
        )''' % self.__tablename__)

        for each in ('email', 'nickname'):
            self._execute('''CREATE UNIQUE INDEX IF NOT EXISTS `ix_%s_%s` ON %s (%s)''' % (
                self.__tablename__, each, self.__tablename__, each))
