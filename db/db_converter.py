#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>

import warnings
import config
from db import DB,Site
from db.basedb import BaseDB
import json
import re
from libs import mcrypto as crypto

class DBconverter():
    def __init__(self, path=config.sqlite3.path):
        self.path = path
            
    async def ConvertNewType(self, db=DB(), path=config.sqlite3.path):
        
        self.db = db
        exec_shell = self.db._execute
            
        if config.db_type == 'sqlite3':
            autokey = 'AUTOINCREMENT'
        else:
            autokey = 'AUTO_INCREMENT'
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            await exec_shell('''CREATE TABLE IF NOT EXISTS `user` (
            `id` INTEGER NOT NULL PRIMARY KEY %s,
            `email` VARCHAR(256) NOT NULL,
            `email_verified` TINYINT NOT NULL DEFAULT 0,
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
            `skey` VARCHAR(128) NOT NULL DEFAULT '',
            `barkurl` VARCHAR(128) NOT NULL DEFAULT '',
            `wxpusher` VARCHAR(128) NOT NULL DEFAULT '',
            `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1,
            `logtime`  VARCHAR(1024) NOT NULL DEFAULT '{"en":false,"time":"20:00:00","ts":0,"schanEn":false,"WXPEn":false}',
            `status`  VARCHAR(1024) NOT NULL DEFAULT 'Enable',
            `diypusher` VARCHAR(1024) NOT NULL DEFAULT '',
            `qywx_token` VARCHAR(1024) NOT NULL DEFAULT '',
            `tg_token` VARCHAR(1024) NOT NULL DEFAULT '',
            `dingding_token` VARCHAR(1024) NOT NULL DEFAULT '',
            `push_batch` VARCHAR(1024) NOT NULL DEFAULT '{"sw":false,"time":0,"delta":86400}'
            );'''% autokey)
            await exec_shell('''CREATE TABLE IF NOT EXISTS `tpl` (
            `id` INTEGER NOT NULL PRIMARY KEY %s,
            `userid` INT UNSIGNED NULL,
            `siteurl` VARCHAR(256) NULL,
            `sitename` VARCHAR(128) NULL,
            `banner` VARCHAR(1024) NULL,
            `disabled` TINYINT NOT NULL DEFAULT 0,
            `public` TINYINT NOT NULL DEFAULT 0,
            `lock` TINYINT NOT NULL DEFAULT 0,
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
            await exec_shell('''CREATE TABLE IF NOT EXISTS `task` (
            `id` INTEGER NOT NULL PRIMARY KEY %s,
            `tplid` INT UNSIGNED NOT NULL,
            `userid` INT UNSIGNED NOT NULL,
            `disabled` TINYINT NOT NULL DEFAULT 0,
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
            `pushsw`  VARCHAR(128) NOT NULL DEFAULT '{"logen":false,"pushen":true}',
            `newontime`  VARCHAR(256) NOT NULL DEFAULT '{"sw":false,"time":"00:10:10","randsw":false,"tz1":0,"tz2":0}'
            );'''% autokey)
            await exec_shell('''CREATE TABLE IF NOT EXISTS `tasklog` (
            `id` INTEGER NOT NULL PRIMARY KEY %s,
            `taskid` INT UNSIGNED NOT NULL,
            `success` TINYINT NOT NULL,
            `ctime` INT UNSIGNED NOT NULL,
            `msg` TEXT NULL
            );'''% autokey)
            await exec_shell('''CREATE TABLE IF NOT EXISTS `push_request` (
            `id` INTEGER NOT NULL PRIMARY KEY %s,
            `from_tplid` INT UNSIGNED NOT NULL,
            `from_userid` INT UNSIGNED NOT NULL,
            `to_tplid` INT UNSIGNED NULL,
            `to_userid` INT UNSIGNED NULL,
            `status` TINYINT NOT NULL DEFAULT 0,
            `msg` VARCHAR(1024) NULL,
            `ctime` INT UNSIGNED NOT NULL,
            `mtime` INT UNSIGNED NOT NULL,
            `atime` INT UNSIGNED NOT NULL
            );'''% autokey)
            await exec_shell('''CREATE TABLE IF NOT EXISTS `site` (
            `id` INTEGER NOT NULL PRIMARY KEY %s,
            `regEn` INT UNSIGNED NOT NULL DEFAULT 1,
            `MustVerifyEmailEn` INT UNSIGNED NOT NULL DEFAULT 0,
            `logDay` INT UNSIGNED NOT NULL DEFAULT 365,
            `repos` TEXT NOT NULL 
            );'''% autokey)
            await exec_shell('''CREATE TABLE IF NOT EXISTS `pubtpl` (
                `id` INTEGER NOT NULL PRIMARY KEY %s,
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
                `repourl` TEXT,
                `repoacc` TEXT,
                `repobranch` TEXT,
                `commenturl` TEXT
            );'''% autokey)
            await exec_shell('''CREATE TABLE IF NOT EXISTS `notepad` (
                `id` INTEGER NOT NULL PRIMARY KEY %s,
                `userid` INTEGER NOT NULL ,
                `notepadid` INTEGER NOT NULL ,
                `content` TEXT NULL
            );'''% autokey)

        if config.db_type == 'sqlite':
            for each in ('email', 'nickname'):
                await exec_shell('''CREATE UNIQUE INDEX IF NOT EXISTS `ix_%s_%s` ON %s (%s)''' % (
                    self.db.user.__tablename__, each, self.db.user.__tablename__, each))
        else:
            for each in ('email', 'nickname'):
                try:
                    await exec_shell('''ALTER TABLE `%s` ADD UNIQUE INDEX `ix_%s_%s` (%s)''' % (
                        self.db.user.__tablename__,  self.db.user.__tablename__, each, each))
                except Exception as e:
                    pass

        try:
            await self.db.task.list(limit=1, fields=('retry_count',))
        except :
            await exec_shell("ALTER TABLE `task` ADD `retry_count` INT NOT NULL DEFAULT 8 " )

        try:
            await self.db.task.list(limit=1, fields=('retry_interval',))
        except :
            await exec_shell("ALTER TABLE `task` ADD `retry_interval` INT UNSIGNED NULL " )

        try:
            await self.db.task.list(limit=1, fields=('ontimeflg',))
        except:
            await exec_shell("ALTER TABLE `task` ADD `ontimeflg` INT UNSIGNED NOT NULL DEFAULT 0 ")

        try:
            await self.db.task.list(limit=1, fields=('ontime',))
        except:                
            await exec_shell("ALTER TABLE `task` ADD `ontime` VARCHAR(256) NOT NULL DEFAULT '00:10:00' " )
            
        try:
            await self.db.user.list(limit=1, fields=('skey',))
        except:
            await exec_shell("ALTER TABLE `user` ADD `skey` VARBINARY(128) NOT NULL DEFAULT '' ")
            
        try:
            await self.db.user.list(limit=1, fields=('barkurl',))
        except:
            await exec_shell("ALTER TABLE `user` ADD `barkurl` VARBINARY(128) NOT NULL DEFAULT '' " )
            
        try:
            await self.db.user.list(limit=1, fields=('wxpusher',))
        except:
            await exec_shell("ALTER TABLE `user` ADD `wxpusher` VARBINARY(128) NOT NULL DEFAULT '' " )
            
        try:
            await self.db.user.list(limit=1, fields=('noticeflg',))
        except :
            await exec_shell("ALTER TABLE `user` ADD `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1 " ) 
        
        try:
            await self.db.user.list(limit=1, fields=('push_batch',))
        except :
            await exec_shell("ALTER TABLE `user` ADD `push_batch` VARBINARY(1024) NOT NULL DEFAULT '{\"sw\":false,\"time\":0,\"delta\":86400}' " ) 

        for user in await self.db.user.list(fields=('id','push_batch')):
            push_batch_i = json.loads(user['push_batch'])
            if not push_batch_i.get('delta'):
                push_batch_i['delta'] = 86400
                await self.db.user.mod(user['id'], push_batch=json.dumps(push_batch_i))

        try:
            await self.db.tpl.list(limit=1, fields=('tplurl',))
        except :
            await exec_shell("ALTER TABLE `tpl` ADD `tplurl` VARCHAR(1024) NULL DEFAULT '' " )
            
        try:
            await self.db.tpl.list(limit=1, fields=('updateable',))
        except :
            await exec_shell("ALTER TABLE `tpl` ADD `updateable` INT UNSIGNED NOT NULL DEFAULT 0 " )       

        try:
            await self.db.task.list(limit=1, fields=('pushsw',))
        except :
            await exec_shell("ALTER TABLE `task` ADD `pushsw` VARBINARY(128) NOT NULL DEFAULT '{\"logen\":false,\"pushen\":true}' " )   
        
        try:
            await self.db.task.list(limit=1, fields=('newontime',))
        except :
            await exec_shell("ALTER TABLE `task` ADD `newontime`  VARBINARY(256) NOT NULL DEFAULT '{\"sw\":false,\"time\":\"00:10:10\",\"randsw\":false,\"tz1\":0,\"tz2\":0 }' " )   

        try:
            await self.db.user.list(limit=1, fields=('logtime',))
        except :
            await exec_shell("ALTER TABLE `user` ADD `logtime` VARBINARY(128) NOT NULL DEFAULT '{\"en\":false,\"time\":\"20:00:00\",\"ts\":0,\"schanEn\":false,\"WXPEn\":false}' " )
                        
        try:
            await self.db.user.list(limit=1, fields=('status',))
        except :
            await exec_shell("ALTER TABLE `user` ADD `status`  VARBINARY(1024) NOT NULL DEFAULT 'Enable' " )  
            
        try:
            temp = await self.db.site.get("1", fields=('regEn',))
            if not (temp):
                raise Exception("new")
        except Exception as e:
            insert = dict(regEn = 1, repos='{"repos":[{"reponame":"default","repourl":"https://github.com/qiandao-today/templates","repobranch":"master","repoacc":true}], "lastupdate":0}')
            await self.db.site._insert(Site(**insert))
            
        try:
            await self.db.site.get("1", fields=('MustVerifyEmailEn',))
        except :
            await exec_shell("ALTER TABLE `site` ADD `MustVerifyEmailEn`  INT UNSIGNED NOT NULL DEFAULT 0 " )  

        try:
            groups = await self.db.task.list(limit=1, fields=('`groups`',))
            if groups:
                await exec_shell("ALTER TABLE `task` RENAME TO `taskold`")
                if config.db_type == 'sqlite3':
                    autokey = 'AUTOINCREMENT'
                else:
                    autokey = 'AUTO_INCREMENT'
                await exec_shell('''CREATE TABLE IF NOT EXISTS `task` (
                `id` INTEGER PRIMARY KEY %s,
                `tplid` INT UNSIGNED NOT NULL,
                `userid` INT UNSIGNED NOT NULL,
                `disabled` TINYINT NOT NULL DEFAULT 0,
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
                `pushsw`  VARCHAR(128) NOT NULL DEFAULT '{\"logen\":false,\"pushen\":true}',
                `newontime`  VARCHAR(256) NOT NULL DEFAULT '{\"sw\":false,\"time\":\"00:10:10\",\"randsw\":false,\"tz1\":0,\"tz2\":0}'
                );'''% autokey)
                await exec_shell("INSERT INTO `task` SELECT `id`,`tplid`,`userid`,`disabled`,`init_env`,`env`,`session`,`retry_count`,`retry_interval`,`last_success`,`last_failed`,`success_count`,`failed_count`,`last_failed_count`,`next`,`note`,`ctime`,`mtime`,`ontimeflg`,`ontime`,`groups`,`pushsw`,`newontime` FROM `taskold` ")
                await exec_shell("DROP TABLE `taskold` ")
        except :
            pass
        
        try:
            await self.db.task.list(limit=1, fields=('_groups',))
        except :
            await exec_shell("ALTER TABLE `task` ADD `_groups` VARCHAR(256) NOT NULL DEFAULT 'None' " )

        try:
            groups = await self.db.tpl.list(limit=1, fields=('`groups`',))
            if groups:
                await exec_shell("ALTER TABLE `tpl` RENAME TO `tplold`")
                if config.db_type == 'sqlite3':
                    autokey = 'AUTOINCREMENT'
                else:
                    autokey = 'AUTO_INCREMENT'
                await exec_shell('''CREATE TABLE IF NOT EXISTS `tpl` (
                `id` INTEGER NOT NULL PRIMARY KEY %s,
                `userid` INT UNSIGNED NULL,
                `siteurl` VARCHAR(256) NULL,
                `sitename` VARCHAR(128) NULL,
                `banner` VARCHAR(1024) NULL,
                `disabled` TINYINT NOT NULL DEFAULT 0,
                `public` TINYINT NOT NULL DEFAULT 0,
                `lock` TINYINT NOT NULL DEFAULT 0,
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
                await exec_shell("INSERT INTO `tpl` SELECT `id`,`userid`,`siteurl`,`sitename`,`banner`,`disabled`,`public`,`lock`,`fork`,`har`,`tpl`,`variables`,`interval`,`note`,`success_count`,`failed_count`,`last_success`,`ctime`,`mtime`,`atime`,`tplurl`,`updateable`,`groups` FROM `tplold` ")
                await exec_shell("DROP TABLE `tplold` ")
        except :
            pass

        try:
            await self.db.tpl.list(limit=1, fields=('_groups',))
        except :
            await exec_shell("ALTER TABLE `tpl` ADD `_groups` VARCHAR(256) NOT NULL DEFAULT 'None' " )
            
        try:
            tmp = await self.db.site.get("1", fields=('logDay',))
            tmp = tmp['logDay']
        except Exception as e:
            if (str(e).find('no such column') > -1):
                await exec_shell("ALTER TABLE `site` ADD `logDay`  INT UNSIGNED NOT NULL DEFAULT 365 " )
            else:
                if config.db_type == 'sqlite3':
                    autokey = ''
                else:
                    autokey = 'AUTO_INCREMENT'
                await exec_shell('''CREATE TABLE IF NOT EXISTS `newsite` (
                            `id` INTEGER NOT NULL PRIMARY KEY {0},
                            `regEn` INT UNSIGNED NOT NULL DEFAULT 1,
                            `MustVerifyEmailEn` INT UNSIGNED NOT NULL DEFAULT 0,
                            `logDay` INT UNSIGNED NOT NULL DEFAULT 365
                            );'''.format(autokey))
                await exec_shell('INSERT INTO `newsite` SELECT id,regEn,MustVerifyEmailEn,LogDay FROM `site`')
                await exec_shell("DROP TABLE `site`" )
                await exec_shell('CREATE TABLE `site` as select * from `newsite`')
                await exec_shell("DROP TABLE `newsite`" )
            
        try:
            await self.db.user.list(limit=1, fields=('diypusher',))
        except :
            await exec_shell("ALTER TABLE `user` ADD `diypusher`  VARCHAR(1024) NOT NULL DEFAULT '' ") 

        try:
            await self.db.user.list(limit=1, fields=('qywx_token',))
        except :
            await exec_shell("ALTER TABLE `user` ADD `qywx_token`  VARCHAR(1024) NOT NULL DEFAULT '' ") 
        
        try:
            await self.db.user.list(limit=1, fields=('tg_token',))
        except :
            await exec_shell("ALTER TABLE `user` ADD `tg_token`  VARCHAR(1024) NOT NULL DEFAULT '' ") 

        try:
            await self.db.user.list(limit=1, fields=('dingding_token',))
        except :
            await exec_shell("ALTER TABLE `user` ADD `dingding_token`  VARCHAR(1024) NOT NULL DEFAULT '' ") 

        if config.db_type == 'sqlite3':
            try:
                import aiosqlite
                from sqlalchemy import update
                from db import User
                conn = await aiosqlite.connect(f"{config.sqlite3.path}")
                conn.text_factory = bytes
                cursor = await conn.execute('SELECT id, password, userkey FROM user')
                for row in await cursor.fetchall():
                    result = await self.db._update(update(User).where(User.id == row[0]).values(password=row[1],userkey=row[2]))
            except Exception as e:
                raise e

        try:
            await self.db.user.list(limit=1, fields=('password_md5',))
            for user in await self.db.user.list(fields=('id', 'password_md5')):
                if isinstance(user['password_md5'],str) and re.match(r'^[a-z0-9]{32}$',user['password_md5']):
                    password = (await self.db.user.get(user['id'], fields=('password',)))['password']
                    await self.db.user.mod(user['id'],password_md5=crypto.password_hash(user['password_md5'],await self.db.user.decrypt(user['id'], password)))
        except Exception as e:
            await exec_shell("ALTER TABLE `user` ADD  `password_md5` VARBINARY(128) NOT NULL DEFAULT '' ") 

        try:
            await self.db.user.list(limit=1, fields=('notepad',))
            for user in await self.db.user.list(fields=('id', 'notepad')):
                await self.db.notepad.add(dict(userid=user['id'], notepadid=1, content=user['notepad']))
            await exec_shell("ALTER TABLE `user` RENAME TO `userold`")
            if config.db_type == 'sqlite3':
                autokey = 'AUTOINCREMENT'
            else:
                autokey = 'AUTO_INCREMENT'
            await exec_shell('''CREATE TABLE IF NOT EXISTS `user` (
                `id` INTEGER NOT NULL PRIMARY KEY %s,
                `email` VARCHAR(256) NOT NULL,
                `email_verified` TINYINT NOT NULL DEFAULT 0,
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
                `skey` VARCHAR(128) NOT NULL DEFAULT '',
                `barkurl` VARCHAR(128) NOT NULL DEFAULT '',
                `wxpusher` VARCHAR(128) NOT NULL DEFAULT '',
                `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1,
                `logtime`  VARCHAR(1024) NOT NULL DEFAULT '{"en":false,"time":"20:00:00","ts":0,"schanEn":false,"WXPEn":false}',
                `status`  VARCHAR(1024) NOT NULL DEFAULT 'Enable',
                `diypusher` VARCHAR(1024) NOT NULL DEFAULT '',
                `qywx_token` VARCHAR(1024) NOT NULL DEFAULT '',
                `tg_token` VARCHAR(1024) NOT NULL DEFAULT '',
                `dingding_token` VARCHAR(1024) NOT NULL DEFAULT '',
                `push_batch` VARCHAR(1024) NOT NULL DEFAULT '{"sw":false,"time":0,"delta":86400}'
                );'''% autokey)
            await exec_shell("INSERT INTO `user` SELECT `id`,`email`,`email_verified`,`password`,`password_md5`,`userkey`,`nickname`,`role`,`ctime`,`mtime`,`atime`,`cip`,`mip`,`aip`,`skey`,`barkurl`,`wxpusher`,`noticeflg`,`logtime`,`status`,`diypusher`,`qywx_token`,`tg_token`,`dingding_token`,`push_batch` FROM `userold`")
            await exec_shell("DROP TABLE `userold`")
        except :
            pass
        
        try:
            await self.db.user.list(limit=1, fields=('cip','mip','aip'))
            cip_is_num = False
            for row in await self.db.user.list(fields=('id','cip')):
                cip = row['cip']
                if len(cip) > 16:
                    cip = bytes()
                    await self.db.user.mod(id=row['id'], cip=cip)
                if str.isdigit(str(cip)):
                    cip_is_num = True
            if cip_is_num:
                await exec_shell("ALTER TABLE `user` RENAME TO `userold`")
                if config.db_type == 'sqlite3':
                    autokey = 'AUTOINCREMENT'
                else:
                    autokey = 'AUTO_INCREMENT'
                await exec_shell('''CREATE TABLE IF NOT EXISTS `user` (
                    `id` INTEGER NOT NULL PRIMARY KEY  %s,
                    `email` VARCHAR(256) NOT NULL,
                    `email_verified` TINYINT NOT NULL DEFAULT 0,
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
                    `skey` VARCHAR(128) NOT NULL DEFAULT '',
                    `barkurl` VARCHAR(128) NOT NULL DEFAULT '',
                    `wxpusher` VARCHAR(128) NOT NULL DEFAULT '',
                    `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1,
                    `logtime`  VARCHAR(1024) NOT NULL DEFAULT '{"en":false,"time":"20:00:00","ts":0,"schanEn":false,"WXPEn":false}',
                    `status`  VARCHAR(1024) NOT NULL DEFAULT 'Enable',
                    `diypusher` VARCHAR(1024) NOT NULL DEFAULT '',
                    `qywx_token` VARCHAR(1024) NOT NULL DEFAULT '',
                    `tg_token` VARCHAR(1024) NOT NULL DEFAULT '',
                    `dingding_token` VARCHAR(1024) NOT NULL DEFAULT '',
                    `push_batch` VARCHAR(1024) NOT NULL DEFAULT '{"sw":false,"time":0,"delta":86400}'
                    );''' % autokey)
                await exec_shell("INSERT INTO `user` SELECT `id`,`email`,`email_verified`,`password`,`password_md5`,`userkey`,`nickname`,`role`,`ctime`,`mtime`,`atime`,`cip`,`mip`,`aip`,`skey`,`barkurl`,`wxpusher`,`noticeflg`,`logtime`,`status`,`diypusher`,`qywx_token`,`tg_token`,`dingding_token`,`push_batch` FROM `userold` ")
                await exec_shell("DROP TABLE `userold` ")
        except Exception as e:
            pass

        try:
            await self.db.site.get("1", fields=('repos',))
        except :
            if config.db_type == 'sqlite3':
                await exec_shell('''ALTER TABLE `site` ADD  `repos` TEXT NOT NULL DEFAULT '{"repos":[{"reponame":"default","repourl":"https://github.com/qiandao-today/templates","repobranch":"master","repoacc":true}], "lastupdate":0}' ''')
            else:
                await exec_shell('''ALTER TABLE `site` ADD  `repos` TEXT ''')
                await exec_shell('''UPDATE `site` SET `repos` = '{"repos":[{"reponame":"default","repourl":"https://github.com/qiandao-today/templates","repobranch":"master","repoacc":true}], "lastupdate":0}' WHERE `site`.`id` = 1 ''')
               
        try:
            tmp = (await self.db.site.get("1", fields=('repos',)))['repos']
            if tmp == None or tmp == '':
                 await exec_shell('''UPDATE `site` SET `repos` = '{"repos":[{"reponame":"default","repourl":"https://github.com/qiandao-today/templates","repobranch":"master","repoacc":true}], "lastupdate":0}' WHERE `site`.`id` = 1 ''')
        except Exception as e:
            pass

        try:
            await self.db.pubtpl.list(limit=1, fields=('commenturl',))
        except :
            if config.db_type == 'sqlite3':
                await exec_shell('''ALTER TABLE `pubtpl` ADD  `commenturl` TEXT NOT NULL DEFAULT ''; ''') 
            else:
                await exec_shell('''ALTER TABLE `pubtpl` ADD  `commenturl` TEXT ''')
                await exec_shell('''UPDATE `pubtpl` SET `commenturl` = '' WHERE 1=1 ''')

        try:
            async with self.db.transaction() as sql_session:
                await exec_shell("ALTER TABLE `user` RENAME TO `userold`", sql_session=sql_session)
                if config.db_type == 'sqlite3':
                    autokey = 'AUTOINCREMENT'
                else:
                    autokey = 'AUTO_INCREMENT'
                await exec_shell('''CREATE TABLE IF NOT EXISTS `user` (
                    `id` INTEGER NOT NULL PRIMARY KEY  %s,
                    `email` VARCHAR(256) NOT NULL,
                    `email_verified` TINYINT NOT NULL DEFAULT 0,
                    `password` BLOB(128) NOT NULL,
                    `password_md5` VARBINARY(128) NOT NULL DEFAULT '',
                    `userkey` BLOB(128) NOT NULL,
                    `nickname` VARCHAR(64) NULL,
                    `role` VARCHAR(128) NULL,
                    `ctime` INT UNSIGNED NOT NULL,
                    `mtime` INT UNSIGNED NOT NULL,
                    `atime` INT UNSIGNED NOT NULL,
                    `cip` VARBINARY(16) NOT NULL,
                    `mip` VARBINARY(16) NOT NULL,
                    `aip` VARBINARY(16) NOT NULL,
                    `skey` VARCHAR(128) NOT NULL DEFAULT '',
                    `barkurl` VARCHAR(128) NOT NULL DEFAULT '',
                    `wxpusher` VARCHAR(128) NOT NULL DEFAULT '',
                    `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1,
                    `logtime`  VARCHAR(1024) NOT NULL DEFAULT '{"en":false,"time":"20:00:00","ts":0,"schanEn":false,"WXPEn":false}',
                    `status`  VARCHAR(1024) NOT NULL DEFAULT 'Enable',
                    `diypusher` VARCHAR(1024) NOT NULL DEFAULT '',
                    `qywx_token` VARCHAR(1024) NOT NULL DEFAULT '',
                    `tg_token` VARCHAR(1024) NOT NULL DEFAULT '',
                    `dingding_token` VARCHAR(1024) NOT NULL DEFAULT '',
                    `push_batch` VARCHAR(1024) NOT NULL DEFAULT '{"sw":false,"time":0,"delta":86400}'
                    );''' % autokey, sql_session=sql_session)
                await exec_shell("INSERT INTO `user` SELECT `id`,`email`,`email_verified`,`password`,`password_md5`,`userkey`,`nickname`,`role`,`ctime`,`mtime`,`atime`,`cip`,`mip`,`aip`,`skey`,`barkurl`,`wxpusher`,`noticeflg`,`logtime`,`status`,`diypusher`,`qywx_token`,`tg_token`,`dingding_token`,`push_batch` FROM `userold` ", sql_session=sql_session)
                await exec_shell("DROP TABLE `userold` ", sql_session=sql_session)
        except Exception as e:
            pass
            
        try:
            async with self.db.transaction() as sql_session:
                await exec_shell("ALTER TABLE `task` RENAME TO `taskold`", sql_session=sql_session)
                if config.db_type == 'sqlite3':
                    autokey = 'AUTOINCREMENT'
                else:
                    autokey = 'AUTO_INCREMENT'
                await exec_shell('''CREATE TABLE IF NOT EXISTS `task` (
                `id` INTEGER PRIMARY KEY %s,
                `tplid` INT UNSIGNED NOT NULL,
                `userid` INT UNSIGNED NOT NULL,
                `disabled` TINYINT NOT NULL DEFAULT 0,
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
                `pushsw`  VARCHAR(128) NOT NULL DEFAULT '{\"logen\":false,\"pushen\":true}',
                `newontime`  VARCHAR(256) NOT NULL DEFAULT '{\"sw\":false,\"time\":\"00:10:10\",\"randsw\":false,\"tz1\":0,\"tz2\":0}'
                );'''% autokey, sql_session=sql_session)
                await exec_shell("INSERT INTO `task` SELECT `id`,`tplid`,`userid`,`disabled`,`init_env`,`env`,`session`,`retry_count`,`retry_interval`,`last_success`,`last_failed`,`success_count`,`failed_count`,`last_failed_count`,`next`,`note`,`ctime`,`mtime`,`ontimeflg`,`ontime`,`_groups`,`pushsw`,`newontime` FROM `taskold` ", sql_session=sql_session)
                await exec_shell("DROP TABLE `taskold` ", sql_session=sql_session)
        except Exception as e:
            pass
        return 