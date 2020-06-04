# qiandao

__操作前请一定要记得备份数据库__<br>
__操作前请一定要记得备份数据库__<br>
__操作前请一定要记得备份数据库__<br>

个人项目精力有限，仅保证对Chrome浏览器的支持。如果测试了其他浏览器可以pull request让我修改。

因为需要测试，docker镜像会晚于gitHub几天更新

docker地址：[https://hub.docker.com/r/asdaragon/qiandao](https://hub.docker.com/r/asdaragon/qiandao)

docker部署命令：``` docker run -d --name qiandao -p 12345:80 -v $(pwd)/qiandao/config:/usr/src/app/config   asdaragon/qiandao ```

## 2020.6.4 更新
1. 根据反馈，HAR编辑里插入链接修改默认地址为localhost
2. 修复2020601版，插入请求后修改为localhost地址, 点击测试的500错误的问题
3. 支持定时后 随机延时

__本次更新会把之前的定时设置全部取消，介意请勿更新__

如果使用mysql 在 20200601 请使用以下命令：
```
ALTER TABLE  `task` ADD `newontime`  VARBINARY(256) NOT NULL DEFAULT '{\"sw\":false,\"time\":\"00:10:10\",\"randsw\":false,\"tz1\":0,\"tz2\":0 }
```
延时的另一种用法，间隔定时运行：如果要实现每1周定时运行一次，设置最大最小值都是604800，即可

## 2020.6.1 更新
1. 时间显示修改为具体时间，取消之前的 "1小时后"等模糊显示(By 戏如人生)
2. 新建任务时可以选择分组
3. Bark推送支持保存历史信息，需要升级APP。
4. HAR编辑里添加添加插入unicode解码，url解码，正则表达式，字符串替换的功能

## 2020.5.31 更新
1. 修复定时 ‘day out of month’ 的BUG
2. 取消定时界面的今日运行选项，自动判断当前时间是今天还是第二天
3. 集成了时间戳获取、unicode转换、url转换功能(By [gxitm](https://github.com/gxitm))
4. 集成了正则表达式、字符串替换功能。

## 2020.5.30 更新
1. 修改 任务失败时 推送的消息内容为 任务日志；
2. 因浏览器支持不好，取消 2020.5.18更新的 ‘模板上传指定格式为.har’；
3. 新增模板编辑 追加HAR 的功能；
4. 新增模板请求删除功能。

## 2020.5.26 更新
1. 修复定时日志发送的最后一条日志的bug
2. 修复定时日志出错影响程序运行的bug

## 2020.5.25 更新
1. Bark, S酱, WXPusher 注册合并为一个按钮
2. 任务推送支持注册后也能关闭
3. 支持分任务开/关推送
4. 新增每日日志功能，可以将每日定时前的最后一个日志推送到S酱和WXPusher
5. 修复“↓”按钮定位不准的bug

如果使用mysql 在 5.22 请使用以下命令：
```
ALTER TABLE `task` ADD `pushsw` VARBINARY(128) NOT NULL DEFAULT '{\"logen\":false,\"pushen\":true}'
ALTER TABLE `user` ADD `logtime` VARBINARY(128) NOT NULL DEFAULT '{\"en\":false,\"time\":\"20:00:00\",\"ts\":0,\"schanEn\":false,\"WXPEn\":false}'
```

## 2020.5.22 更新
1. 分组增加折叠/展开功能
2. 左侧增加新建模板按钮，“↑”回到顶部， “↓”表示跳转到模板页面
3. 修复删除任务时日志不删除bug

## 2020.5.19 更新
1. 添加手动检查模板更新的按钮。

如果使用mysql 在 5.18 请使用以下命令：
```
ALTER TABLE `tpl` ADD `tplurl` VARCHAR(1024) NULL DEFAULT '' 
ALTER TABLE `tpl` ADD `updateable` INT UNSIGNED NOT NULL DEFAULT 0
```

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
