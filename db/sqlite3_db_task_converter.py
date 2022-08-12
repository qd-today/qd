#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>

import config
from db.task import TaskDB as _TaskDB
from sqlite3_db.basedb import BaseDB
from db.basedb import BaseDB as myBaseDB
import db.task as task 
import json
import re
from libs import mcrypto as crypto

class DBconverter(_TaskDB, BaseDB):
    def __init__(self, path=config.sqlite3.path):
        self.path = path
            
    def ConvertNewType(self, db=None, path=config.sqlite3.path):
        
        self.db = db
            
        if config.db_type != 'sqlite3':
            self.db.site._execute('''CREATE TABLE IF NOT EXISTS `user` (
            `id` INTEGER NOT NULL PRIMARY KEY  AUTO_INCREMENT,
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
            `logtime`  VARBINARY(1024) NOT NULL DEFAULT '{"en":false,"time":"20:00:00","ts":0,"schanEn":false,"WXPEn":false}',
            `status`  VARBINARY(1024) NOT NULL DEFAULT 'Enable',
            `diypusher` VARBINARY(1024) NOT NULL DEFAULT '',
            `qywx_token` VARBINARY(1024) NOT NULL DEFAULT '',
            `tg_token` VARBINARY(1024) NOT NULL DEFAULT '',
            `dingding_token` VARBINARY(1024) NOT NULL DEFAULT '',
            `push_batch`  VARBINARY(1024) NOT NULL DEFAULT '{"sw":false,"time":0,"delta":86400}'
            );''')
            self.db.site._execute('''CREATE TABLE IF NOT EXISTS `tpl` (
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
            `updateable` INT UNSIGNED NOT NULL DEFAULT 0,
            `_groups` VARCHAR(256) NOT NULL DEFAULT 'None'
            );''')
            self.db.site._execute('''CREATE TABLE IF NOT EXISTS `task` (
            `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `tplid` INT UNSIGNED NOT NULL,
            `userid` INT UNSIGNED NOT NULL,
            `disabled` TINYINT(1) NOT NULL DEFAULT 0,
            `init_env` BLOB NULL,
            `env` BLOB NULL,
            `session` BLOB NULL,
            `retry_count` INT NOT NULL DEFAULT 8,
            `retry_interval` INT UNSIGNED NULL,
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
            );''')
            self.db.site._execute('''CREATE TABLE IF NOT EXISTS `tasklog` (
            `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `taskid` INT UNSIGNED NOT NULL,
            `success` TINYINT(1) NOT NULL,
            `ctime` INT UNSIGNED NOT NULL,
            `msg` TEXT NULL
            );''')
            self.db.site._execute('''CREATE TABLE IF NOT EXISTS `push_request` (
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
            );''')
            self.db.site._execute('''CREATE TABLE IF NOT EXISTS `site` (
            `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `regEn` INT UNSIGNED NOT NULL DEFAULT 1,
            `MustVerifyEmailEn` INT UNSIGNED NOT NULL DEFAULT 0,
            `logDay` INT UNSIGNED NOT NULL DEFAULT 365,
            `repos` TEXT NOT NULL
            );''' ) 

            self.db.site._execute('''CREATE TABLE IF NOT EXISTS `pubtpl` (
                `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
                `name` TEXT ,
                `author` TEXT ,
                `comments` TEXT ,
                `content` TEXT ,
                `filename` TEXT,
                `date` TEXT,
                `version` TEXT,
                `url` TEXT,
                `update` TEXT,
                `reponame` TEXT,
                `repourl`  TEXT,
                `repoacc`  TEXT,
                `repobranch`  TEXT,
                `commenturl`  TEXT
            )''' ) 
            
            self.db.site._execute('''CREATE TABLE IF NOT EXISTS `notepad` (
                `id` INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
                `userid` INTEGER NOT NULL ,
                `notepadid` INTEGER NOT NULL ,
                `content` TEXT NULL
            )''' ) 

        if config.db_type == 'sqlite3': 
            exec_shell = self._execute
        else:
            exec_shell = self.db.task._execute

        try:
            self.db.task.get("1", fields=('retry_count'))
        except :
            exec_shell("ALTER TABLE `task` ADD `retry_count` INT NOT NULL DEFAULT 8 " )

        try:
            self.db.task.get("1", fields=('retry_interval'))
        except :
            exec_shell("ALTER TABLE `task` ADD `retry_interval` INT UNSIGNED NULL " )

        try:
            self.db.task.get("1", fields=('ontimeflg'))
        except:
            exec_shell("ALTER TABLE `task` ADD `ontimeflg` INT UNSIGNED NOT NULL DEFAULT 0 ")

        try:
            self.db.task.get("1", fields=('ontime'))
        except:                
            exec_shell("ALTER TABLE `task` ADD `ontime` VARCHAR(256) NOT NULL DEFAULT '00:10:00' " )
            
        try:
            self.db.user.get("1", fields=('skey'))
        except:
            exec_shell("ALTER TABLE `user` ADD `skey` VARBINARY(128) NOT NULL DEFAULT '' ")
            
        try:
            self.db.user.get("1", fields=('barkurl'))
        except:
            exec_shell("ALTER TABLE `user` ADD `barkurl` VARBINARY(128) NOT NULL DEFAULT '' " )
            
        try:
            self.db.user.get("1", fields=('wxpusher'))
        except:
            exec_shell("ALTER TABLE `user` ADD `wxpusher` VARBINARY(128) NOT NULL DEFAULT '' " )
            
        try:
            self.db.user.get("1", fields=('noticeflg'))
        except :
            exec_shell("ALTER TABLE `user` ADD `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1 " ) 
        
        try:
            self.db.user.get("1", fields=('push_batch'))
        except :
            exec_shell("ALTER TABLE `user` ADD `push_batch` VARBINARY(1024) NOT NULL DEFAULT '{\"sw\":false,\"time\":0,\"delta\":86400}' " ) 

        try:
            for user in self.db.user.list(fields=('id','push_batch')):
                push_batch_i = json.loads(user['push_batch'])
                if not push_batch_i.get('delta'):
                    push_batch_i['delta'] = 86400
                    self.db.user.mod(user['id'], push_batch=json.dumps(push_batch_i))
        except Exception as e:
            raise e

        try:
            self.db.tpl.get("1", fields=('tplurl'))
        except :
            exec_shell("ALTER TABLE `tpl` ADD `tplurl` VARCHAR(1024) NULL DEFAULT '' " )
            
        try:
            self.db.tpl.get("1", fields=('updateable'))
        except :
            exec_shell("ALTER TABLE `tpl` ADD `updateable` INT UNSIGNED NOT NULL DEFAULT 0 " )       

        try:
            self.db.task.get("1", fields=('pushsw'))
        except :
            exec_shell("ALTER TABLE `task` ADD `pushsw` VARBINARY(128) NOT NULL DEFAULT '{\"logen\":false,\"pushen\":true}' " )   
        
        try:
            self.db.task.get("1", fields=('newontime'))
        except :
            exec_shell("ALTER TABLE `task` ADD `newontime`  VARBINARY(256) NOT NULL DEFAULT '{\"sw\":false,\"time\":\"00:10:10\",\"randsw\":false,\"tz1\":0,\"tz2\":0 }' " )   

        try:
            self.db.user.get("1", fields=('logtime'))
        except :
            exec_shell("ALTER TABLE `user` ADD `logtime` VARBINARY(128) NOT NULL DEFAULT '{\"en\":false,\"time\":\"20:00:00\",\"ts\":0,\"schanEn\":false,\"WXPEn\":false}' " )
                        
        try:
            self.db.user.get("1", fields=('status'))
        except :
            exec_shell("ALTER TABLE `user` ADD `status`  VARBINARY(1024) NOT NULL DEFAULT 'Enable' " )  
            
        try:
            temp = self.db.site.get(1, fields=('regEn'))
            if not (temp):
                raise Exception("new")
        except Exception as e:
            insert = dict(regEn = 1, repos='{"repos":[{"reponame":"default","repourl":"https://github.com/qiandao-today/templates","repobranch":"master","repoacc":true}], "lastupdate":0}')
            self.db.site._insert(**insert)
            
        try:
            self.db.site.get("1", fields=('MustVerifyEmailEn'))
        except :
            exec_shell("ALTER TABLE `site` ADD `MustVerifyEmailEn`  INT UNSIGNED NOT NULL DEFAULT 0 " )  

        try:
            groups = self.db.task.get("1", fields=('`groups`'))
            if groups:
                exec_shell("ALTER TABLE `task` RENAME TO `taskold`")
                if config.db_type == 'sqlite3':
                    autokey = 'AUTOINCREMENT'
                else:
                    autokey = 'AUTO_INCREMENT'
                exec_shell('''CREATE TABLE IF NOT EXISTS `task` (
                `id` INTEGER PRIMARY KEY %s,
                `tplid` INT UNSIGNED NOT NULL,
                `userid` INT UNSIGNED NOT NULL,
                `disabled` TINYINT(1) NOT NULL DEFAULT 0,
                `init_env` BLOB NULL,
                `env` BLOB NULL,
                `session` BLOB NULL,
                `retry_count` INT NOT NULL DEFAULT 8,
                `retry_interval` INT UNSIGNED NULL,
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
                `pushsw`  VARBINARY(128) NOT NULL DEFAULT '{\"logen\":false,\"pushen\":true}',
                `newontime`  VARBINARY(256) NOT NULL DEFAULT '{\"sw\":false,\"time\":\"00:10:10\",\"randsw\":false,\"tz1\":0,\"tz2\":0}'
                );'''% autokey)
                exec_shell("INSERT INTO `task` SELECT `id`,`tplid`,`userid`,`disabled`,`init_env`,`env`,`session`,`retry_count`,`retry_interval`,`last_success`,`last_failed`,`success_count`,`failed_count`,`last_failed_count`,`next`,`note`,`ctime`,`mtime`,`ontimeflg`,`ontime`,`groups`,`pushsw`,`newontime` FROM `taskold` ")
                exec_shell("DROP TABLE `taskold` ")
        except :
            pass
        
        try:
            self.db.task.get("1", fields=('_groups'))
        except :
            exec_shell("ALTER TABLE `task` ADD `_groups` VARCHAR(256) NOT NULL DEFAULT 'None' " )

        try:
            groups = self.db.tpl.get("1", fields=('`groups`'))
            if groups:
                exec_shell("ALTER TABLE `tpl` RENAME TO `tplold`")
                if config.db_type == 'sqlite3':
                    autokey = 'AUTOINCREMENT'
                else:
                    autokey = 'AUTO_INCREMENT'
                exec_shell('''CREATE TABLE IF NOT EXISTS `tpl` (
                `id` INTEGER NOT NULL PRIMARY KEY %s,
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
                );'''% autokey)
                exec_shell("INSERT INTO `tpl` SELECT `id`,`userid`,`siteurl`,`sitename`,`banner`,`disabled`,`public`,`lock`,`fork`,`har`,`tpl`,`variables`,`interval`,`note`,`success_count`,`failed_count`,`last_success`,`ctime`,`mtime`,`atime`,`tplurl`,`updateable`,`groups` FROM `tplold` ")
                exec_shell("DROP TABLE `tplold` ")
        except :
            pass

        try:
            self.db.tpl.get("1", fields=('_groups'))
        except :
            exec_shell("ALTER TABLE `tpl` ADD `_groups` VARCHAR(256) NOT NULL DEFAULT 'None' " )
            
        try:
            tmp = self.db.site.get("1", fields=('logDay'))
            tmp = tmp['logDay']
        except Exception as e:
            if (str(e).find('no such column') > -1):
                exec_shell("ALTER TABLE `site` ADD `logDay`  INT UNSIGNED NOT NULL DEFAULT 365 " )
            else:
                if config.db_type == 'sqlite3':
                    autokey = ''
                else:
                    autokey = 'AUTO_INCREMENT'
                exec_shell('''CREATE TABLE IF NOT EXISTS `newsite` (
                            `id` INTEGER NOT NULL PRIMARY KEY {0},
                            `regEn` INT UNSIGNED NOT NULL DEFAULT 1,
                            `MustVerifyEmailEn` INT UNSIGNED NOT NULL DEFAULT 0,
                            `logDay` INT UNSIGNED NOT NULL DEFAULT 365
                            );'''.format(autokey))
                exec_shell('INSERT INTO `newsite` SELECT id,regEn,MustVerifyEmailEn,LogDay FROM `site`')
                exec_shell("DROP TABLE `site`" )
                exec_shell('CREATE TABLE `site` as select * from `newsite`')
                exec_shell("DROP TABLE `newsite`" )
            
        try:
            self.db.user.get("1", fields=('diypusher'))
        except :
            exec_shell("ALTER TABLE `user` ADD `diypusher`  VARCHAR(1024) NOT NULL DEFAULT '' ") 

        try:
            self.db.user.get("1", fields=('qywx_token'))
        except :
            exec_shell("ALTER TABLE `user` ADD `qywx_token`  VARCHAR(1024) NOT NULL DEFAULT '' ") 
        
        try:
            self.db.user.get("1", fields=('tg_token'))
        except :
            exec_shell("ALTER TABLE `user` ADD `tg_token`  VARCHAR(1024) NOT NULL DEFAULT '' ") 

        try:
            self.db.user.get("1", fields=('dingding_token'))
        except :
            exec_shell("ALTER TABLE `user` ADD `dingding_token`  VARCHAR(1024) NOT NULL DEFAULT '' ") 

        try:
            self.db.user.get("1", fields=('password_md5'))
            for user in self.db.user.list(fields=('id', 'password', 'password_md5')):
                if isinstance(user['password_md5'],str) and re.match(r'^[a-z0-9]{32}$',user['password_md5']):
                    self.db.user.mod(user['id'],password_md5=crypto.password_hash(user['password_md5'],self.db.user.decrypt(user['id'], user['password'])))
        except :
            exec_shell("ALTER TABLE `user` ADD  `password_md5` VARBINARY(128) NOT NULL DEFAULT '' ") 

        try:
            if self.db.user.get("1", fields=('cip','mip','aip')) and str.isdigit(str(list(self.db.user.list( fields='cip'))[0]['cip'])):
                exec_shell("ALTER TABLE `user` RENAME TO `userold`")
                if config.db_type == 'sqlite3':
                    autokey = 'AUTOINCREMENT'
                else:
                    autokey = 'AUTO_INCREMENT'
                exec_shell('''CREATE TABLE IF NOT EXISTS `user` (
                    `id` INTEGER NOT NULL PRIMARY KEY  %s,
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
                    `logtime`  VARBINARY(1024) NOT NULL DEFAULT '{"en":false,"time":"20:00:00","ts":0,"schanEn":false,"WXPEn":false}',
                    `status`  VARBINARY(1024) NOT NULL DEFAULT 'Enable',
                    `diypusher` VARBINARY(1024) NOT NULL DEFAULT '',
                    `qywx_token` VARBINARY(1024) NOT NULL DEFAULT '',
                    `tg_token` VARBINARY(1024) NOT NULL DEFAULT '',
                    `dingding_token` VARBINARY(1024) NOT NULL DEFAULT '',
                    `push_batch`  VARBINARY(1024) NOT NULL DEFAULT '{"sw":false,"time":0,"delta":86400}'
                    );''' % autokey)
                exec_shell("INSERT INTO `user` SELECT `id`,`email`,`email_verified`,`password`,`password_md5`,`userkey`,`nickname`,`role`,`ctime`,`mtime`,`atime`,`cip`,`mip`,`aip`,`skey`,`barkurl`,`wxpusher`,`noticeflg`,`logtime`,`status`,`diypusher`,`qywx_token`,`tg_token`,`dingding_token`,`push_batch` FROM `userold` ")
                exec_shell("DROP TABLE `userold` ")
        except :
            pass

        try:
            self.db.site.get("1", fields=('repos'))
        except :
            if config.db_type == 'sqlite3':
                exec_shell('''ALTER TABLE `site` ADD  `repos` TEXT NOT NULL DEFAULT '{"repos":[{"reponame":"default","repourl":"https://github.com/qiandao-today/templates","repobranch":"master","repoacc":true}], "lastupdate":0}' ''')
            else:
                exec_shell('''ALTER TABLE `site` ADD  `repos` TEXT ''')
                exec_shell('''UPDATE `site` SET `repos` = '{"repos":[{"reponame":"default","repourl":"https://github.com/qiandao-today/templates","repobranch":"master","repoacc":true}], "lastupdate":0}' WHERE `site`.`id` = 1 ''')
               
        try:
            tmp = self.db.site.get("1", fields=('repos'))['repos']
            if tmp == None or tmp == '':
                 exec_shell('''UPDATE `site` SET `repos` = '{"repos":[{"reponame":"default","repourl":"https://github.com/qiandao-today/templates","repobranch":"master","repoacc":true}], "lastupdate":0}' WHERE `site`.`id` = 1 ''')
        except :
            pass

        try:
            self.db.pubtpl.get("1", fields=('commenturl'))
        except :
            if config.db_type == 'sqlite3':
                exec_shell('''ALTER TABLE `pubtpl` ADD  `commenturl` TEXT NOT NULL DEFAULT ''; ''') 
            else:
                exec_shell('''ALTER TABLE `pubtpl` ADD  `commenturl` TEXT ''')
                exec_shell('''UPDATE `pubtpl` SET `commenturl` = '' WHERE 1=1 ''')

        try:
            self.db.user.get("1", fields=('notepad'))
            for user in self.db.user.list(fields=('id', 'notepad')):
                self.db.notepad.add(dict(userid=user['id'], notepadid=1, content=user['notepad']))
            exec_shell("ALTER TABLE `user` RENAME TO `userold`")
            if config.db_type == 'sqlite3':
                autokey = 'AUTOINCREMENT'
            else:
                autokey = 'AUTO_INCREMENT'
            exec_shell('''CREATE TABLE IF NOT EXISTS `user` (
                `id` INTEGER NOT NULL PRIMARY KEY %s,
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
                `logtime`  VARBINARY(1024) NOT NULL DEFAULT '{"en":false,"time":"20:00:00","ts":0,"schanEn":false,"WXPEn":false}',
                `status`  VARBINARY(1024) NOT NULL DEFAULT 'Enable',
                `diypusher` VARBINARY(1024) NOT NULL DEFAULT '',
                `qywx_token` VARBINARY(1024) NOT NULL DEFAULT '',
                `tg_token` VARBINARY(1024) NOT NULL DEFAULT '',
                `dingding_token` VARBINARY(1024) NOT NULL DEFAULT '',
                `push_batch`  VARBINARY(1024) NOT NULL DEFAULT '{"sw":false,"time":0,"delta":86400}'
                );'''% autokey)
            exec_shell("INSERT INTO `user` SELECT `id`,`email`,`email_verified`,`password`,`password_md5`,`userkey`,`nickname`,`role`,`ctime`,`mtime`,`atime`,`cip`,`mip`,`aip`,`skey`,`barkurl`,`wxpusher`,`noticeflg`,`logtime`,`status`,`diypusher`,`qywx_token`,`tg_token`,`dingding_token`,`push_batch` FROM `userold`")
            exec_shell("DROP TABLE `userold`")
        except :
            pass
            
        return 