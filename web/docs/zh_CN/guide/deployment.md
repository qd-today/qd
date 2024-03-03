# 部署

## Docker 容器部署

Docker 容器部署是部署 QD 的最简单方式。

> 操作前请一定要记得备份数据库!!!

### 容器

**DockerHub 网址**：[https://hub.docker.com/r/qdtoday/qd](https://hub.docker.com/r/qdtoday/qd)

> Tag 含义:
>
> - `latest`: 最新 Release 版本
> - `lite-latest`: 去除 OCR 相关功能的最新 Release 版本
> - `ja3-latest`: 集成 curl-impersonate 解决 ja3 指纹被识别为 curl 的问题, 不支持 http3 和 Quic 连接
> - `20xxxxxx`: 指定 Release 版本, 版本号表示为 Release 发布日期
> - `dev`: 最新开发版, 同步最新源码, 不保证稳定性

### 部署方法

#### 1. Docker Compose（推荐）

``` sh
# 创建并切换到 QD 目录。
mkdir -p $(pwd)/qd/config && cd $(pwd)/qd
# 下载 docker-compose.yml
wget https://fastly.jsdelivr.net/gh/qd-today/qd@master/docker-compose.yml
# 根据需求和配置说明修改配置环境变量
vi ./docker-compose.yml
# 执行 Docker Compose 命令
docker-compose up -d
```

> 配置描述见下文 [Configuration](#配置环境变量)
>
> 如不需要`OCR功能`或者`硬盘空间不大于600M`, 请使用 **`qdtoday/qd:lite-latest`** 镜像, **该镜像仅去除了OCR相关功能, 其他与主线版本保持一致**。
>
> **请勿使用 阿里云镜像源 拉取 Docker 容器, 会导致无法拉取最新镜像**

#### 2. 1Panel 部署

2.1. 在 1Panel 中创建一个新的应用

   ![点击安装](../../public/panel1.png)

   > 不同 1Panel 版本显示 QD 框架名称可能不同, 但均为 `QD` 图标.

2.2. 配置相关设置

   ![安装配置](../../public/panel2.png)

   > 如需设置环境变量请点击 `编辑 Compose 文件`
   >
   > 配置描述见下文 [Configuration](#配置环境变量)
   >
   > 如不需要`OCR功能`或者`硬盘空间不大于600M`, 请使用 **`qdtoday/qd:lite-latest`** 镜像, **该镜像仅去除了OCR相关功能, 其他与主线版本保持一致**。

2.3. 点击 `确认` 即可通过 1Panel 安装 QD

#### 3. Docker 运行

``` sh
docker run -d --name qd -p 8923:80 -v $(pwd)/qd/config:/usr/src/app/config qdtoday/qd
```

容器内部无法连通外部网络时尝试该命令:

``` sh
# 使用 Host 网络模式创建容器, 端口号: 8923
docker run -d --name qd --env PORT=8923 --net=host -v $(pwd)/qd/config:/usr/src/app/config qdtoday/qd
```

> 注意: 使用该命令创建容器后, 请将模板里 `http://localhost/` 形式的 api 请求, 手动改成 `api://` 或 `http://localhost:8923/` 后, 才能正常完成相关API请求。
>
> **请勿同时运行新旧版 QD 框架, 或将不同运行中的 QD 容器数据库映射为同一文件。**

## 源码部署

1. **Version >= python3.9**

   ``` sh
   # 请先cd到框架源码根目录
   pip3 install -r requirements.txt
   ```

2. **修改相关设置**

   ``` sh
   # 执行以下命令复制配置文件
   # 修改 local_config.py 文件的内容不受通过 git 更新源码的影响
   cp config.py local_config.py
   # 根据需求和配置说明修改配置文件或环境变量值
   vi local_config.py
   ```

3. **启动**

   ``` sh
   python ./run.py
   ```

4. **访问**

   ``` sh
   # 访问网页
   http://localhost:8923/
   ```

   > 如果您使用的是源码部署方式，请手动将模板中 `http://localhost/` 形式的 api 请求改为 `api://` 或 `http://localhost:8923/` ，以便正确完成相关API 请求。
   >
   > 模板需要发布才会在「公开模板」中展示, 你需要管理员权限在「我的发布请求」中审批通过。

## 设置管理员

``` sh
python ./chrole.py your@email.address admin
```

> 首位注册用户默认为管理员, 需要先登出再登陆后才能获得完整管理员权限

## 配置环境变量

变量名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
BIND|否|0.0.0.0|监听地址
PORT|否|8923|监听端口
QD_DEBUG|否|False|是否启用Debug模式
WORKER_METHOD|否|Queue|任务定时执行方式, <br>默认为 Queue, 可选 Queue 或 Batch, <br>Batch 模式为旧版定时任务执行方式, 性能较弱, <br>**建议仅当 Queue 定时执行模式失效时使用**
MULTI_PROCESS|否|False|(实验性)是否启用多进程模式, <br>Windows平台无效
AUTO_RELOAD|否|False|是否启用自动热加载, <br>MULTI_PROCESS=True时无效
STATIC_URL_PREFIX|否|`/static/`|静态文件URL前缀
DOMAIN|否|''|指定访问域名, <br>**(建议修改)**, 否则通过邮件重置密码及邮箱推送等功能无效
AES_KEY|否|binux|AES加密密钥, **(强烈建议修改)**
COOKIE_SECRET|否|binux|cookie加密密钥, **(强烈建议修改)**
COOKIE_DAY|否|5|Cookie在客户端中保留的天数
DB_TYPE|否|sqlite3|需要使用MySQL时设置为'mysql'
JAWSDB_MARIA_URL|否|''|需要使用MySQL时, <br>设置为 (mysql://用户名:密码@hostname:port/数据库名?auth_plugin=)
QD_SQL_ECHO|否|False|是否启用 SQLAlchmey 的日志输出, 默认为 False, <br>设置为 True 时, 会在控制台输出 SQL 语句, <br>允许设置为 debug 以启用 debug 模式
QD_SQL_LOGGING_NAME|否|QD.sql_engine|SQLAlchmey 日志名称, 默认为 'QD.sql_engine'
QD_SQL_LOGGING_LEVEL|否|Warning|SQLAlchmey 日志级别, 默认为 'Warning'
QD_SQL_ECHO_POOL|否|True|是否启用 SQLAlchmey 的连接池日志输出, 默认为 True, <br>允许设置为 debug 以启用 debug 模式
QD_SQL_LOGGING_POOL_NAME|否|QD.sql_pool|SQLAlchmey 连接池日志名称, 默认为 'QD.sql_pool'
QD_SQL_LOGGING_POOL_LEVEL|否|Warning|SQLAlchmey 连接池日志级别, 默认为 'Warning'
QD_SQL_POOL_SIZE|否|10|SQLAlchmey 连接池大小, 默认为 10
QD_SQL_MAX_OVERFLOW|否|50|SQLAlchmey 连接池最大溢出, 默认为 50
QD_SQL_POOL_PRE_PING|否|True|是否在连接池获取连接前, <br>先ping一下, 默认为 True
QD_SQL_POOL_RECYCLE|否|3600|SQLAlchmey 连接池回收时间, 默认为 3600
QD_SQL_POOL_TIMEOUT|否|60|SQLAlchmey 连接池超时时间, 默认为 60
QD_SQL_POOL_USE_LIFO|否|True|SQLAlchmey 是否使用 LIFO 算法, 默认为 True
REDISCLOUD_URL|否|''|需要使用Redis或RedisCloud时, <br>设置为 <http://rediscloud:密码@hostname:port>
REDIS_DB_INDEX|否|1|默认为1
QD_EVIL|否|500|(限Redis连接已开启)登录用户或IP在1小时内 <br>分数 = 操作失败(如登录, 验证, 测试等操作)次数 * 相应惩罚分值 <br>分数达到evil上限后自动封禁直至下一小时周期
EVIL_PASS_LAN_IP|否|True|是否关闭本机私有IP地址用户及Localhost_API请求的evil限制
TRACEBACK_PRINT|否|False|是否启用在控制台日志中打印Exception的TraceBack信息
PUSH_PIC_URL|否|[push_pic.png](https://fastly.jsdelivr.net/gh/qd-today/qd@master/web/static/img/push_pic.png)|默认为[push_pic.png](https://fastly.jsdelivr.net/gh/qd-today/qd@master/web/static/img/push_pic.png)
PUSH_BATCH_SW|否|True|是否允许开启定期推送 QD 任务日志, 默认为True
MAIL_SMTP|否|""|邮箱SMTP服务器
MAIL_PORT|否|465|邮箱SMTP服务器端口
MAIL_SSL|否|True|是否启用邮箱SSL, 默认为True
MAIL_STARTTLS|否|False|是否启用邮箱STARTTLS, 默认为False
MAIL_USER|否|""|邮箱用户名
MAIL_PASSWORD|否|""|邮箱密码
MAIL_FROM|否|MAIL_USER|发送时使用的邮箱，默认与MAIL_USER相同
MAIL_DOMAIN_HTTPS|否|False|发送的邮件链接启用HTTPS, <br>非框架前端使用HTTPS, <br>如果前端需要HTTPS, 请使用反向代理.
PROXIES|否|""|全局代理域名列表,用"|"分隔
PROXY_DIRECT_MODE|否|""|全局代理黑名单模式,默认不启用 <br>"url"为网址匹配模式;"regexp"为正则表达式匹配模式
PROXY_DIRECT|否|""|全局代理黑名单匹配规则
NEW_TASK_DELAY|否|1|新建任务后准备时间, 单位为秒, 默认为1秒
TASK_WHILE_LOOP_TIMEOUT|否|900|任务运行中单个 While 循环最大运行时间, <br>单位为秒, 默认为 15 分钟
TASK_REQUEST_LIMIT|否|1500|任务运行中单个任务最大请求次数, <br>默认为 1500 次
USE_PYCURL|否|True|是否启用Pycurl模组
ALLOW_RETRY|否|True|在Pycurl环境下部分请求可能导致Request错误时, <br>自动修改冲突设置并重发请求
DNS_SERVER|否|""|通过Curl使用指定DNS进行解析(仅支持Pycurl环境), <br>如 8.8.8.8
CURL_ENCODING|否|True|是否允许使用Curl进行Encoding操作
CURL_CONTENT_LENGTH|否|True|是否允许Curl使用Headers中自定义Content-Length请求
NOT_RETRY_CODE|否|[详见配置](https://github.com/qd-today/qd/blob/master/config.py)...|[详见配置](https://github.com/qd-today/qd/blob/master/config.py)...
EMPTY_RETRY|否|True|[详见配置](https://github.com/qd-today/qd/blob/master/config.py)...
USER0ISADMIN|否|True|第一个注册用户为管理员，False关闭
NOTEPAD_LIMIT|否|20|单个用户拥有记事本最大数量, 默认为 20
EXTRA_ONNX_NAME|否|""|config目录下自定义ONNX文件名<br>(不填 ".onnx" 后缀)<br>多个onnx文件名用"\|"分隔
EXTRA_CHARSETS_NAME|否|""|config目录下自定义ONNX对应自定义charsets.json文件名<br>(不填 ".json" 后缀)<br>多个json文件名用"\|"分隔
WS_PING_INTERVAL|No|5|WebSocket ping间隔, 单位为秒, 默认为 5s
WS_PING_TIMEOUT|No|30|WebSocket ping超时时间, 单位为秒, 默认为 30s
WS_MAX_MESSAGE_SIZE|No|10485760|WebSocket 单次接收最大消息大小, 默认为 10MB
WS_MAX_QUEUE_SIZE|No|100|WebSocket 最大消息队列大小, 默认为 100
WS_MAX_CONNECTIONS_SUBSCRIBE|No|30|WebSocket 公共模板更新页面最大连接数, 默认为 30
SUBSCRIBE_ACCELERATE_URL|No|jsdelivr_cdn|订阅加速方式或地址, 用于加速公共模板更新, 仅适用于 GitHub. <br>[详见配置](https://github.com/qd-today/qd/blob/master/config.py)...

> 详细信息请查阅[config.py](https://github.com/qd-today/qd/blob/master/config.py)
