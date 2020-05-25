#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>

import config
from db.task import TaskDB as _TaskDB
from sqlite3_db.basedb import BaseDB
import db.task as task 
import os

class DBconverter(_TaskDB, BaseDB):
    def __init__(self, path=config.sqlite3.path):
        self.path = path
            
    def ConvertNewType(self, path=config.sqlite3.path):
        self.path = path
        if (os.path.isfile(path)):
            if config.db_type == 'sqlite3':
                import sqlite3_db as db
            else:
                import db
            class DB(object):
                user = db.UserDB()
                tpl = db.TPLDB()
                task = db.TaskDB()
                tasklog = db.TaskLogDB()
            self.db = DB
            try:
                self.db.task.get("1", fields=('ontimeflg'))
            except:                
                self._execute("ALTER TABLE `task` ADD `ontimeflg` INT UNSIGNED NOT NULL DEFAULT 0 ")
                
            try:
                self.db.task.get("1", fields=('ontime'))
            except:                
                self._execute("ALTER TABLE `task` ADD `ontime` VARCHAR(256) NOT NULL DEFAULT '00:10:00' " )
                
            try:
                self.db.user.get("1", fields=('skey'))
            except:
                self._execute("ALTER TABLE `user` ADD `skey` VARBINARY(128) NOT NULL DEFAULT '' ")
                
            try:
                self.db.user.get("1", fields=('barkurl'))
            except:
                self._execute("ALTER TABLE `user` ADD `barkurl` VARBINARY(128) NOT NULL DEFAULT '' " )
                
            try:
                self.db.user.get("1", fields=('wxpusher'))
            except:
                self._execute("ALTER TABLE `user` ADD `wxpusher` VARBINARY(128) NOT NULL DEFAULT '' " )
                
            try:
                self.db.user.get("1", fields=('noticeflg'))
            except :
                self._execute("ALTER TABLE `user` ADD `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1 " ) 
                
            try:
                self.db.task.get("1", fields=('groups'))
            except :
                self._execute("ALTER TABLE `task` ADD `groups` VARBINARY(128) NOT NULL DEFAULT 'None' " )
                
            try:
                self.db.tpl.get("1", fields=('tplurl'))
            except :
                self._execute("ALTER TABLE `tpl` ADD `tplurl` VARCHAR(1024) NULL DEFAULT '' " )
                
            try:
                self.db.tpl.get("1", fields=('updateable'))
            except :
                self._execute("ALTER TABLE `tpl` ADD `updateable` INT UNSIGNED NOT NULL DEFAULT 0 " )       

            try:
                self.db.task.get("1", fields=('pushsw'))
            except :
                self._execute("ALTER TABLE `task` ADD `pushsw` VARBINARY(128) NOT NULL DEFAULT '{\"logen\":false,\"pushen\":true}' " )   

            try:
                self.db.user.get("1", fields=('logtime'))
            except :
                self._execute("ALTER TABLE `user` ADD `logtime` VARBINARY(128) NOT NULL DEFAULT '{\"en\":false,\"time\":\"20:00:00\",\"ts\":0,\"schanEn\":false,\"WXPEn\":false}' " )                             
        return 