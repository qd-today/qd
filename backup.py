#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-09 11:39:25

import json
import time
import datetime
import re

import config
import sqlite3

from sqlite3_db.basedb import BaseDB

class DBnew(BaseDB):
    def __init__(self, path):
        self.path = path        
                
    def new(self, userid, maindb):        
        try:
            conn = sqlite3.connect(self.path)
            c = conn.cursor()

            c.execute('''CREATE TABLE IF NOT EXISTS `user` (
                `id` INTEGER NOT NULL PRIMARY KEY  AUTO_INCREMENT,
                `email` VARCHAR(256) NOT NULL,
                `email_verified` TINYINT(1) NOT NULL DEFAULT 0,
                `password` VARBINARY(128) NOT NULL,
                `userkey` VARBINARY(128) NOT NULL,
                `nickname` VARCHAR(64) NULL,
                `role` VARCHAR(128) NULL,
                `ctime` INT UNSIGNED NOT NULL,
                `mtime` INT UNSIGNED NOT NULL,
                `atime` INT UNSIGNED NOT NULL,
                `cip` INT UNSIGNED NOT NULL,
                `mip` INT UNSIGNED NOT NULL,
                `aip` INT UNSIGNED NOT NULL,
                `skey` VARBINARY(128) NOT NULL DEFAULT '',
                `barkurl` VARBINARY(128) NOT NULL DEFAULT '',
                `wxpusher` VARBINARY(128) NOT NULL DEFAULT '',
                `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1,
                `logtime`  VARBINARY(1024) NOT NULL DEFAULT '{"en":false,"time":"20:00:00","ts":0,"schanEn":false,"WXPEn":false}',
                `status`  VARBINARY(1024) NOT NULL DEFAULT 'Enable'
                );
                CREATE TABLE IF NOT EXISTS `tpl` (
                `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
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
                `updateable` INT UNSIGNED NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS `task` (
                `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
                `tplid` INT UNSIGNED NOT NULL,
                `userid` INT UNSIGNED NOT NULL,
                `disabled` TINYINT(1) NOT NULL DEFAULT 0,
                `init_env` BLOB NULL,
                `env` BLOB NULL,
                `session` BLOB NULL,
                `last_success` INT UNSIGNED NULL,
                `last_failed` INT UNSIGNED NULL,
                `success_count` INT UNSIGNED NOT NULL DEFAULT 0,
                `failed_count` INT UNSIGNED NOT NULL DEFAULT 0,
                `last_failed_count` INT UNSIGNED NOT NULL DEFAULT 0,
                `next` INT UNSIGNED NULL DEFAULT NULL,
                `note` VARCHAR(256) NULL,
                `ctime` INT UNSIGNED NOT NULL,
                `mtime` INT UNSIGNED NOT NULL,
                `ontimeflg` INT UNSIGNED NOT NULL DEFAULT 0,
                `ontime` VARCHAR(256) NOT NULL DEFAULT '00:10:00',
                `_groups` VARCHAR(256) NOT NULL DEFAULT 'None',
                `pushsw`  VARBINARY(128) NOT NULL DEFAULT '{"logen":false,"pushen":true}',
                `newontime`  VARBINARY(256) NOT NULL DEFAULT '{"sw":false,"time":"00:10:10","randsw":false,"tz1":0,"tz2":0}'
                );
                CREATE TABLE IF NOT EXISTS `tasklog` (
                `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
                `taskid` INT UNSIGNED NOT NULL,
                `success` TINYINT(1) NOT NULL,
                `ctime` INT UNSIGNED NOT NULL,
                `msg` TEXT NULL
                );
                CREATE TABLE IF NOT EXISTS `push_request` (
                `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
                `from_tplid` INT UNSIGNED NOT NULL,
                `from_userid` INT UNSIGNED NOT NULL,
                `to_tplid` INT UNSIGNED NULL,
                `to_userid` INT UNSIGNED NULL,
                `status` TINYINT NOT NULL DEFAULT 0,
                `msg` VARCHAR(1024) NULL,
                `ctime` INT UNSIGNED NOT NULL,
                `mtime` INT UNSIGNED NOT NULL,
                `atime` INT UNSIGNED NOT NULL
                );
                CREATE TABLE IF NOT EXISTS `site` (
                `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
                `regEn` INT UNSIGNED NOT NULL DEFAULT 1
                );''' )

            # 获取数据库信息            
            userid = int(userid)
            user = maindb.db.user.get(id=userid, fields=('id', 'role', 'status', 'email','email_verified', 'password', 'nickname', 
                                                        'ctime','mtime','atime','cip', 'mip','aip','skey','barkurl', 'wxpusher', 'noticeflg','logtime'))
            userkey = maindb.db.user.__getuserkey(user['env'])
            tpls = []
            for tpl in maindb.db.tpl.list(fields=('id', 'userid', 'siteurl', 'banner', 'disabled', 'public', 'lock', 'fork', 'har', 'tpl', 'variables', 'interval', 
                                                'note', 'success_count', 'failed_count', 'last_success', 'ctime', 'mtime', 'atime', 'tplurl', 'updateable'), limit=None):
                if tpl['userid'] == userid:
                    tpls.append(tpl)
            tasks = []
            tasklogs = []
            for task in maindb.db.task.list(userid, fields=('id', 'tplid', 'userid', 'note', 'disabled', 'init_env', 'env', 'session', 'last_success', 'success_count', 
                                                        'failed_count', 'last_failed', 'next', 'last_failed_count', 'ctime', 'mtime', 'ontimeflg', 'ontime',  '_groups', 'pushsw', 'newontime'), limit=None):
                if task['userid'] == userid:
                    tasks.append(task)
                    for tasklog in maindb.db.tasklog.list(taskid = task['id'], fields=('id', "taskid", "success", "ctime", "msg")):
                        tasklogs.append(tasklog)

             
        except Exception as e:
            raise Exception("backup database error")
        print("OK")