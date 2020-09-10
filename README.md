# qiandao

__操作前请一定要记得备份数据库__<br>
__操作前请一定要记得备份数据库__<br>
__操作前请一定要记得备份数据库__<br>

个人项目精力有限，仅保证对Chrome浏览器的支持。如果测试了其他浏览器可以pull request让我修改。

因为需要测试，docker镜像会晚于gitHub几天更新

docker地址：[https://hub.docker.com/r/asdaragon/qiandao](https://hub.docker.com/r/asdaragon/qiandao)

docker部署命令：``` docker run -d --name qiandao -p 12345:80 -v $(pwd)/qiandao/config:/usr/src/app/config   asdaragon/qiandao ```

数据库备份指令：```docker cp 容器名:/usr/src/app/config/database.db . ```

数据库恢复指令：```docker cp database.db 容器名:/usr/src/app/config/ ```

## 2020.09.10 更新
1. 鉴于github 污染严重，使用gitee代替作为订阅源，地址：[https://gitee.com/qiandao-today/templates](https://gitee.com/qiandao-today/templates)
2. 首页的检查模板更新取消，打开公共模板仓库会自动检查更新
3. 修复邮箱验证，注册后未验证可以再次点击注册验证
4. 修改任务时显示前值

本次更新有js脚本更新，请开启chrome 的 “disable cache”功能更新js脚本

## 2020.09.07 更新
1. 在数据库管理中增加一键备份/恢复所有模板的功能

## 2020.09.01 更新
1. 正则提取支持post方式
2. 取消getcookie插件提示(By powersee)
3. 管理员可以查看用户是否验证邮箱，可以设置不验证邮箱无法登陆
4. 支持任务分组
5. 推送带上任务备注

## 2020.07.19更新
1. 修改按钮“推送通知开关”为“推送设置”
2. 添加错误提醒容忍。在自动签到到一定次数错误后，才推送提醒。

## 2020.07.17更新
1. 使报错显示中文，添加点击复制错误日志按钮(by [liubei121212](https://github.com/liubei121212/qiandao))
2. 主页版本从alpha修改为20200717

## 2020.07.09更新
1. 添加 管理员 备份数据库功能
2. 添加任务日志清空功能
3. 修复定时的随机延时取消失败的BUG
4. 添加任务禁用功能
5. 为了提高兼容性，请求不验证SSL

## 2020.6.22 更新
1. 修复检查公共模板更新功能；
2. 美化左侧三按钮(By 十六君)
3. 修复插入RSA加密实际是字符串替换的BUG
4. 修改请求为不验证SSL，提升兼容性
   
## 2020.6.14 更新
1. 添加RSA加密/解密
2. 用户管理页面添加用户最后登陆时间
3. 字符串替换功能可以返回纯文本，避免有转义'\\'的出现,需要替换参数r=text

## 2020.6.12 更新
1. 定时日志BUG太多，修不过来，取消此功能
2. 修复用户不存在时登录500错误

## 2020.6.11 更新
1. 修复MySQL的支持，不需要手动更新Mysql数据库

## 2020.6.10 更新
1. 添加管理员管理用户功能，可以将用户禁用/开启/删除
2. 添加关闭/开启注册功能
3. 修改主页的'检查更新'为'检查模板更新'

使用前需要进入容器，将对应已注册邮箱设置为管理员：
```
docker exec -it 容器名 /bin/bash
python ./chrole.py 邮箱 admin
```
被禁用的账户将不能登录网站,所有任务将被禁用。
被删除的账户，会删除该用户的所有任务，模板和日志

如果使用mysql 在 20200604 请使用以下命令：
```
ALTER TABLE `user` ADD `status`  VARBINARY(1024) NOT NULL DEFAULT 'Enable';
CREATE TABLE IF NOT EXISTS `site` (
          `id` INTEGER NOT NULL PRIMARY KEY,
          `regEn` INT UNSIGNED NOT NULL DEFAULT 1
        );
INSERT INTO `site` VALUES(1,1);
```

## 2020.6.6 更新
1. 修复用户不存在依然能登陆的BUG(具体表现为：新用户新建模板保存时500错误，注册推送时提示NoneType) 
2. 完善注册推送的注册消息
3. 修复自动完成不推送的bug
4. 添加定时 “今日已签过” 选项，可以直接定时第二天
5. 修复公共模板的HAR订阅功能

## 2020.6.5 更新
1. 修复 sqlite3 数据库初始值错误的问题，仅影响新建数据库的用户 

## 2020.6.4 更新
1. 根据反馈，HAR编辑里插入链接修改默认地址为localhost
2. 修复2020601版，插入请求后修改为localhost地址, 点击测试的500错误的问题
3. 支持定时后 随机延时

__本次更新会把之前的定时设置全部取消，介意请勿更新__

如果使用mysql 在 20200601 请使用以下命令：
```
ALTER TABLE  `task` ADD `newontime`  VARBINARY(256) NOT NULL DEFAULT '{\"sw\":false,\"time\":\"00:10:10\",\"randsw\":false,\"tz1\":0,\"tz2\":0 }'
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
ALTER TABLE `task` ADD `pushsw` VARBINARY(128) NOT NULL DEFAULT '{\"logen\":false,\"pushen\":true}';
ALTER TABLE `user` ADD `logtime` VARBINARY(128) NOT NULL DEFAULT '{\"en\":false,\"time\":\"20:00:00\",\"ts\":0,\"schanEn\":false,\"WXPEn\":false}';
```

## 2020.5.22 更新
1. 分组增加折叠/展开功能
2. 左侧增加新建模板按钮，“↑”回到顶部， “↓”表示跳转到模板页面
3. 修复删除任务时日志不删除bug

## 2020.5.19 更新
1. 添加手动检查模板更新的按钮。

如果使用mysql 在 5.18 请使用以下命令：
```
ALTER TABLE `tpl` ADD `tplurl` VARCHAR(1024) NULL DEFAULT '' ;
ALTER TABLE `tpl` ADD `updateable` INT UNSIGNED NOT NULL DEFAULT 0;
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
ALTER TABLE `task` ADD `groups` VARBINARY(128) NOT NULL DEFAULT 'None' ;
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
ALTER TABLE `task` ADD `ontimeflg` INT UNSIGNED NOT NULL DEFAULT 0;
ALTER TABLE `task` ADD `ontime` VARCHAR(256) NOT NULL DEFAULT '00:10:00';
ALTER TABLE `user` ADD `skey` VARBINARY(128) NOT NULL DEFAULT '' ;
ALTER TABLE `user` ADD `barkurl` VARBINARY(128) NOT NULL DEFAULT '' ;
ALTER TABLE `user` ADD `wxpusher` VARBINARY(128) NOT NULL DEFAULT '' ;
ALTER TABLE `user` ADD `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1;
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
