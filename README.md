# qiandao

__操作前请一定要记得备份数据库__<br>
__操作前请一定要记得备份数据库__<br>
__操作前请一定要记得备份数据库__<br>

## 2020.5.19 更新
1. 添加手动检查模板更新的按钮；
2. 支持取消已注册的推送。

## 2020.5.18 更新
1. 定时的 "今日是否运行" 修改 为 "今日运行"
2. 添加模板订阅功能，仓库地址在[https://github.com/qiandao-today/templates](https://github.com/qiandao-today/templates)
   主页打开公共模板按钮，点击订阅后自动导入模板，需要自己确认保存
3. 模板上传指定格式为.har

## 2020.5.16 更新
1. 添加任务分类功能

如果使用mysql 请使用以下命令：
```
ALTER TABLE `task` ADD `groups` VARBINARY(128) NOT NULL DEFAULT 'None' 
```
2. 定时功能显示之前的定时值

## 初始版本
基于quchaonet的蓝调主题签到增加了:


1. 设置任务最低间隔时间及任务request最高100限制 (by 戏如人生)

http://cordimax.f3322.net:5558/381.html

2. 增加了server酱、bark推送，WXPusher推送，并可以设置推送开关（by AragonSnow）
需要推送的：登录账号以后点击注册bark/s酱/WXPusher，测试推送没有问题以后,再点击提交


3. 增加定时功能，在新建任务以后会出现定时按钮，设置每天的定时时间。<br>
__不兼容旧版的数据库， 旧版数据库导入会自动转换，旧版将无法使用__<br>
__使用SQLite3的，默认路径改为config文件夹里面，方便挂载后备份__<br>
__使用Mysq的,请使用一下命令更新数据库：__<br>
```
ALTER TABLE `task` ADD `ontimeflg` INT UNSIGNED NOT NULL DEFAULT 0
ALTER TABLE `task` ADD `ontime` VARCHAR(256) NOT NULL DEFAULT '00:10:00'
ALTER TABLE `user` ADD `skey` VARBINARY(128) NOT NULL DEFAULT '' 
ALTER TABLE `user` ADD `barkurl` VARBINARY(128) NOT NULL DEFAULT '' 
ALTER TABLE `user` ADD `wxpusher` VARBINARY(128) NOT NULL DEFAULT '' 
ALTER TABLE `user` ADD `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1
```


## 以下为原镜像说明：

签到 —— 一个自动签到框架 base on an HAR editor

HAR editor 使用指南：https://github.com/binux/qiandao/blob/master/docs/har-howto.md

Web
===

需要 python2.7, 虚拟主机无法安装

```
apt-get install python-dev autoconf g++ python-pbkdf2
pip install tornado u-msgpack-python jinja2 chardet requests pbkdf2 pycrypto
```

可选 redis, Mysql

```
mysql < qiandao.sql
```

启动

```
./run.py
```

数据不随项目分发，去 [https://qiandao.today/tpls/public](https://qiandao.today/tpls/public) 查看你需要的模板，点击下载。
在你自己的主页中 「我的模板+」 点击 + 上传。模板需要发布才会在「公开模板」中展示，你需要管理员权限在「我的发布请求」中审批通过。


设置管理员

```
./chrole.py your@email.address admin
```

使用Docker部署站点
==========

可参考 Wiki [Docker部署签到站教程](https://github.com/binux/qiandao/wiki/Docker%E9%83%A8%E7%BD%B2%E7%AD%BE%E5%88%B0%E7%AB%99%E6%95%99%E7%A8%8B)

qiandao.py
==========

```
pip install tornado u-msgpack-python jinja2 chardet requests
./qiandao.py tpl.har [--key=value]* [env.json]
```

config.py
=========
优先用`mailgun`方式发送邮件，如果要用smtp方式发送邮件，请填写mail_smtp, mail_user, mail_password
```python
mail_smtp = ""     # 邮件smtp 地址
mail_user = ""    # 邮件账户
mail_passowrd = ""   # 邮件密码
mail_domain = "mail.qiandao.today"
mailgun_key = ""
```

鸣谢
====

[Mark  https://www.quchao.net/](https://www.quchao.net/) 

[戏如人生 https://49594425.xyz/](https://49594425.xyz/)

[AragonSnow https://hexo.aragon.wang/](https://hexo.aragon.wang/)

许可
====

MIT
