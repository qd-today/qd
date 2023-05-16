# 常见问题

## 如何备份和恢复数据库?

QD 默认使用 **sqlite3** 作为框架数据库，`database.db` 文件保存在 `config` 目录下。使用 Docker 容器部署时，可以使用 `docker cp` 命令备份数据库文件，然后使用 `docker cp` 命令在新容器中恢复数据库文件。

``` sh
# 数据库备份
docker cp container_name:/usr/src/app/config/database.db .
# 数据库恢复
docker cp database.db container_name:/usr/src/app/config/
```

## 如何在 Docker 中配置邮箱服务器?

``` sh
docker run -d --name qd -p 8923:80 -v $(pwd)/qd/config:/usr/src/app/config --env MAIL_SMTP=STMP服务器 --env MAIL_PORT=邮箱服务器端口 --env MAIL_USER=用户名 --env MAIL_PASSWORD=密码  --env DOMAIN=域名 a76yyyy/qiandao
```

## 如何在 Docker 中使用 MySQL?

``` sh
docker run -d --name qd -p 8923:80 -v $(pwd)/qd/config:/usr/src/app/config --ENV DB_TYPE=mysql --ENV JAWSDB_MARIA_URL=mysql://用户名:密码@hostname:port/数据库名 a76yyyy/qiandao
```

## 如何自己搭建 Docker 镜像?

请参考此镜像的构建文件 [Dockerfile](https://github.com/qd-today/qd/blob/master/Dockerfile)。

## 如何查看当前框架支持的 API 和 Jinja2 模板变量?

请进入框架首页，然后点击左上角的 `常用 API/过滤器` 按钮，可以查看当前框架支持的API和Jinja2模板变量。

## 如何提交 bug 问题?

请在遇到问题后开启 `Debug` 模式，然后将详细的错误日志提交至 [Issue](https://github.com/qd-today/qd/issues)。

## QD 模板一般需要哪些请求?

根据经验，以下请求是必要的：

- 登录页面
- 发布到登录页面
- 发起 用户名、密码 请求
- 发送后导致页面跳转的页面
- 翻页前后的第一个网页

## 我的用户名和密码会被泄露吗?

为了帮助用户发起请求，终究需要记录用户名和密码。这只能靠服务器维护人员的自律来保证后端数据的安全。但在框架设计中，每个用户在存储时都使用安全密钥进行加密。使用密钥对用户数据进行加密，可以保证仅获取数据库就无法解密用户数据。（加密的用户数据包括用户上传的模板、用户为任务设置的变量等）

如果还是不放心，可以自己搭建QD框架，下载模板在自己的服务器上运行。

## 提示警告信息: `Connect Redis falied: Error 10061`

QD 使用 `redis` 作为限流工具，如果没有安装 `redis` 服务，框架会提示以下警告信息。

``` sh
[W xxxxxx xx:xx:xx QD.RedisDB redisdb:28] Connect Redis falied: Error 10061 connecting to localhost:6379. 由于目标计算机积极拒绝，无法连接。
```

然而，`redis` 在框架中并不是必须的，如果你不需要使用 `限流` 功能，可以忽略该警告信息。

> 建议使用 `Docker compose` 部署 QD 框架, Docker compose 配置已默认安装 redis 容器。

## 提示警告信息: `Import PyCurl module falied`

QD 使用 `pycurl` 模块来发送 HTTP Proxy 请求。如果没有安装 `pycurl` 模块，框架会提示以下警告信息。

``` sh
[W xxxxxx xx:xx:xx QD.Http.Fetcher fetcher:34] Import PyCurl module falied: No module named 'pycurl'
```

然而，`pycurl` 在框架中并不是必须的，如果你不需要使用 `Proxy` 功能，可以忽略该警告信息。

> `pycurl` 模块在 Windows 系统上安装比较麻烦，需要安装 `libcurl` 库，具体安装方法请参考 [pycurl官方文档](http://pycurl.io/docs/latest/install.html)。
>
> 建议使用容器或 linux 系统部署 QD 框架, Docker 容器已预装Curl环境, 默认安装pycurl模组。

## 如何注册推送方式

你可以在`工具箱`->`推送注册`中注册不同的推送工具，以便在发生特定事件（例如定时任务执行失败）时向你推送通知

### TgBot

假设你已经创建了一个具有自定义域名的 Telegram bot API:

`https://tg.mydomain.com/bot1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/sendMessage?chat_id=222222222&text=HelloWorld`

上面这个请求将会向`222222222`这个聊天发送一条`HelloWorld`消息。那么在注册TgBot作为推送方式时：

- `TG_TOKEN` 应当填写bot的ID以及对应的key的组合，但是不包括`bot`，即申请TgBot时BotFather提供的token：`1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` 
- `TG_USERID` 应当填写telegram API中的`chat_id`字段，即 `222222222`
- `TG_HOST` 填`tg.mydomain.com`，也可以带上`http://`或者`https://`前缀

因此最终填写形式形如：

`1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA;222222222;tg.mydomain.com`
