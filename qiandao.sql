CREATE TABLE IF NOT EXISTS `user` (
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
          `id` INTEGER NOT NULL PRIMARY KEY,
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
          `groups` VARCHAR(256) NOT NULL DEFAULT 'None',
          `pushsw`  VARBINARY(128) NOT NULL DEFAULT '{"logen":false,"pushen":true}',
          `newontime`  VARBINARY(256) NOT NULL DEFAULT '{"sw":false,"time":"00:10:10","randsw":false,"tz1":0,"tz2":0}'
        );
CREATE TABLE IF NOT EXISTS `tasklog` (
          `id` INTEGER NOT NULL PRIMARY KEY,
          `taskid` INT UNSIGNED NOT NULL,
          `success` TINYINT(1) NOT NULL,
          `ctime` INT UNSIGNED NOT NULL,
          `msg` TEXT NULL
        );
CREATE TABLE IF NOT EXISTS `push_request` (
          `id` INTEGER NOT NULL PRIMARY KEY,
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
          `id` INTEGER NOT NULL PRIMARY KEY,
          `regEn` INT UNSIGNED NOT NULL DEFAULT 1
        );
INSERT INTO site VALUES(1,1);
CREATE UNIQUE INDEX `ix_user_email` ON user (email);
CREATE UNIQUE INDEX `ix_user_nickname` ON user (nickname);
CREATE INDEX `ix_tpl_siteurl` ON tpl (siteurl);
CREATE INDEX `ix_tpl_sitename` ON tpl (sitename);
CREATE INDEX `ix_tpl_public` ON tpl (public);
CREATE INDEX `ix_task_userid` ON task (userid);
CREATE INDEX `ix_task_tplid` ON task (tplid);
CREATE INDEX `ix_push_request_to_userid` ON push_request (to_userid);
CREATE INDEX `ix_push_request_status` ON push_request (status);
