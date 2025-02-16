#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux <i@binux.me>
#         http://binux.me
# Created on 2014-07-30 12:21:48
# Modified on 2023-06-13 18:12:35
# pylint: disable=invalid-name, wildcard-import
# flake8: noqa: F401,F403

import hashlib
import os
from urllib.parse import parse_qs, urlparse

from libs.config_utils import strtobool

# QD 框架常用设置
debug = bool(strtobool(os.getenv('QD_DEBUG', 'False')))                      # 是否启用 QD 框架 Debug
bind = str(os.getenv('BIND', '0.0.0.0'))                                    # 框架运行监听地址 ('0.0.0.0' 表示监听所有 IP 地址)
port = int(os.getenv('PORT', '8923'))                                         # 监听端口 Port
multiprocess = bool(strtobool(os.getenv('MULTI_PROCESS', 'False')))          # 是否启用多进程模式, Windows 平台无效, 请谨慎使用
autoreload = bool(strtobool(os.getenv('AUTO_RELOAD', 'False')))              # 是否启用自动热加载, `multiprocess=True` 时无效
gzip = bool(strtobool(os.getenv('GZIP', 'True')))                            # 是否启用 gzip
accesslog = bool(strtobool(os.getenv('ACCESS_LOG', 'True')))                # 是否输出 Tornado access Log
display_import_warning = bool(strtobool(os.getenv('DISPLAY_IMPORT_WARNING', 'True')))           # 是否显示导入模组失败或 Redis 连接失败的警告
user0isadmin = bool(strtobool(os.getenv('USER0ISADMIN', 'True')))            # 是否将第一个注册用户设置为管理员
static_url_prefix = os.getenv('STATIC_URL_PREFIX', '/static/')              # 静态文件访问路径前缀, 默认为 '/static/'

# 指定域名, 用于发送邮件及微信推送内链接域名显示,
# 如果是 *域名* 方式请正确输入 `domain.com`, 请勿包含协议头 `http://` 或 `https://`
# 如果是通过 *IP+端口Port* 方式请正确输入 `IP:Port`
domain = os.getenv('DOMAIN', '')                                            # 建议修改, 不然邮件重置密码之类的功能无效

# Cookie 及加密设置
cookie_days = int(os.getenv('COOKIE_DAY', '5'))                               # Cookie 在客户端保留时间
cookie_secure_mode = bool(strtobool(os.getenv('COOKIE_SECURE_MODE', 'False')))                  # Cookie 是否启用安全模式, 默认为 False,
# 启用后仅支持通过 HTTPS 访问 QD 框架, 请确保已正确配置 HTTPS 及证书
# HTTP 访问将导致 Cookie 无法正常设置, 无法登录和使用框架功能

cookie_secret = hashlib.sha256(os.getenv('COOKIE_SECRET', 'binux').encode('utf-8')).digest()    # Cookie 加密密钥, 强烈建议修改
pbkdf2_iterations = int(os.getenv('PBKDF2_ITERATIONS', '400'))                                    # pbkdf2 迭代次数
aes_key = hashlib.sha256(os.getenv('AES_KEY', 'binux').encode('utf-8')).digest()                # AES 加密密钥, 强烈建议修改

# 数据库设置
## 数据库类型, 修改 sqlite3 为 mysql 使用 mysql
db_type = os.getenv('DB_TYPE', 'sqlite3')                                   # 默认为Sqlite3, 需要使用MySQL时设置为'mysql'

## MySQL URL设置
mysql_url = urlparse(os.getenv('JAWSDB_MARIA_URL', ''))                     # 格式: mysql://用户名:密码@hostname:port/数据库名?auth_plugin=


class mysql:
    ## 数据库连接参数, 建议基于 MySQL URL 自动设置, 可选
    host = mysql_url.hostname or 'localhost'                                # 访问 MySQL 的 Hostname
    port = mysql_url.port or '3306'                                         # MySQL 的 端口Port
    database = mysql_url.path[1:] or 'qd'                                   # QD 框架的数据库名
    user = mysql_url.username or 'qd'                                       # 拥有访问 MySQL 内 QD 框架数据库权限的用户名
    passwd = mysql_url.password or None                                     # 用户名对应的密码
    auth_plugin = parse_qs(mysql_url.query).get('auth_plugin', [''])[0]      # auth_plugin, 默认为空, 可修改为'mysql_native_password','caching_sha2_password'

## Sqlite3 设置


class sqlite3:
    path = os.path.join(os.path.dirname(__file__), 'config', 'database.db')   # Sqlite3数据库文件地址


class sqlalchemy:
    ## SQLAlchmey配置
    logging_name = os.getenv('QD_SQL_LOGGING_NAME', 'QD.sql')               # SQLAlchmey 日志名称
    logging_level = os.getenv('QD_SQL_LOGGING_LEVEL', 'WARNING')            # SQLAlchmey 日志级别
    pool_logging_name = os.getenv('QD_SQL_POOL_LOGGING_NAME', 'QD.sql.pool')  # 连接池日志名称
    pool_logging_level = os.getenv('QD_SQL_POOL_LOGGING_LEVEL', 'WARNING')  # 连接池日志级别
    pool_size = int(os.getenv('QD_SQL_POOL_SIZE', '10'))                    # 连接池大小
    max_overflow = int(os.getenv('QD_SQL_MAX_OVERFLOW', '50'))              # 连接池连接数量超过 pool_size 时, 最大连接数
    pool_pre_ping = bool(strtobool(os.getenv('QD_SQL_POOL_PRE_PING', 'True')))                  # 是否在获取连接前进行 ping 操作, 默认为 True
    pool_recycle = int(os.getenv('QD_SQL_POOL_RECYCLE', '3600'))            # 连接池中连接复用时间, 默认为 3600 秒
    pool_timeout = int(os.getenv('QD_SQL_POOL_TIMEOUT', '60'))              # 连接池获取连接超时时间, 默认为 60 秒
    pool_use_lifo = bool(strtobool(os.getenv('QD_SQL_POOL_USE_LIFO', 'True')))                  # 连接池是否使用 LIFO, 默认为 True


# Redis 设置
## Redis URL设置
redis_url = urlparse(os.getenv('REDISCLOUD_URL', ''))                       # 格式: (redis/http)://rediscloud:密码@hostname:port


class redis:
    ## redis 连接参数, 建议基于 Redis URL 自动设置, 可选
    host = redis_url.hostname or 'localhost'                                # 访问 Redis 的 Hostname
    port = redis_url.port or 6379                                           # Redis 的 端口Port
    passwd = redis_url.password or None                                     # 访问 Redis 权限密码
    db = int(os.getenv('REDIS_DB_INDEX', '1'))                                # 索引


evil = int(os.getenv('QD_EVIL', '500'))                                       # Redis连接成功后生效, 用于登录用户或IP在1小时内 操作失败(如登录, 验证, 测试等操作)次数*相应惩罚分值 达到evil值上限后自动封禁直至下一小时周期
evil_pass_lan_ip = bool(strtobool(os.getenv('EVIL_PASS_LAN_IP', 'True')))    # 是否针对本机私有IP地址用户及 Localhost_API 请求关闭 evil 限制

# 任务运行相关设置
worker_method = str(os.getenv('WORKER_METHOD', 'Queue')).upper()             # 任务定时执行方式, 默认为 Queue, 可选 Queue 或 Batch, Batch 模式为旧版定时任务执行方式, 性能较弱, 建议仅当定时执行失效时使用
queue_num = int(os.getenv('QUEUE_NUM', '50'))                                 # 定时执行任务队列最大数量, 仅在 Queue 模式下生效
check_task_loop = int(os.getenv('CHECK_TASK_LOOP', '500'))                    # Worker 检查任务工作循环时间, 单位毫秒
task_max_retry_count = int(os.getenv('TASK_MAX_RETRY_COUNT', '8'))            # 任务失败默认最大重试次数, 默认为8次
new_task_delay = int(os.getenv('NEW_TASK_DELAY', '1'))                        # 新建任务后准备时间, 单位为秒, 默认为1秒
task_while_loop_timeout = int(os.getenv('TASK_WHILE_LOOP_TIMEOUT', '900'))  # 任务运行中单个 While 循环最大运行时间, 单位为秒, 默认为15分钟
task_request_limit = int(os.getenv('TASK_REQUEST_LIMIT', '1500'))             # 任务运行中单个任务最大请求次数, 默认为 1500 次

# Tornado httpclient.HTTPRequest参数配置
download_size_limit = int(os.getenv('DOWNLOAD_SIZE_LIMIT', '5242880'))    # 允许用户单次请求下载最大值
request_timeout = float(os.getenv('REQUEST_TIMEOUT', '30.0'))                 # HTTP Request 请求超时时间
connect_timeout = float(os.getenv('CONNECT_TIMEOUT', '30.0'))                 # HTTP Request 连接超时时间
delay_max_timeout = float(os.getenv('DELAY_MAX_TIMEOUT', '29.9'))             # 延时API 最大时间限制, 请小于上述 timeout 配置, 否则会报 599 错误
unsafe_eval_timeout = float(os.getenv('UNSAFE_EVAL_TIMEOUT', '3.0'))          # unsafe_eval 最大时间限制

# PyCurl 相关设置
use_pycurl = bool(strtobool(os.getenv('USE_PYCURL', 'True')))                # 是否启用 Pycurl 模组, 当环境无 PyCurl 模组时无效
allow_retry = bool(strtobool(os.getenv('ALLOW_RETRY', 'True')))             # 在 Pycurl 环境下部分请求可能导致 Request 错误时, 自动修改冲突设置并重发请求
dns_server = str(os.getenv('DNS_SERVER', ''))                               # 通过 Curl 使用指定 DNS 进行解析(仅支持 Pycurl 环境)
curl_encoding = bool(strtobool(os.getenv('CURL_ENCODING', 'True')))         # 是否允许使用 Curl 进行 Encoding 操作,
# 当 PyCurl 返回 "Error 61 Unrecognized transfer encoding." 错误,
# 且 `ALLOW_RETRY=True` 时, 本次请求禁用 Headers 中的 Content-Encoding 并重试
curl_length = bool(strtobool(os.getenv('CURL_CONTENT_LENGTH', 'True')))     # 是否允许 Curl 使用 Headers 中自定义 Content-Length 请求,
# 当PyCurl返回 "HTTP 400 Bad Request" 错误, 且 `ALLOW_RETRY=True` 时,
# 本次请求禁用 Headers 中的 Content-Length 并重试
not_retry_code = list(map(int, os.getenv('NOT_RETRY_CODE', '301|302|303|304|305|307|400|401|403|404|405|407|408|409|410|412|415|413|414|500|501|502|503|504|599').split('|')))
# 启用后, 当满足 PyCurl 启用, HTTPError code 不在该列表中, 任务代理为空,
# 且 `ALLOW_RETRY=True` 时, 本次请求禁用 Pycurl 并重试
empty_retry = bool(strtobool(os.getenv('EMPTY_RETRY', 'True')))             # 启用后, 当满足 PyCurl 启用, 返回 Response 为空, 任务代理为空,
# 且 `ALLOW_RETRY=True` 时, 本次请求禁用 Pycurl 并重试

# 日志及推送设置
traceback_print = bool(strtobool(os.getenv('TRACEBACK_PRINT', 'True' if debug else 'False')))   # 是否启用在控制台日志中打印 Exception 的 TraceBack 信息
push_pic = os.getenv('PUSH_PIC_URL', 'https://gitee.com/qd-today/qd/raw/master/web/static/img/push_pic.png')    # 日志推送默认图片地址
push_batch_sw = bool(strtobool(os.getenv('PUSH_BATCH_SW', 'True')))         # 是否允许开启定期推送任务日志, 默认为 True
push_batch_delta = int(os.getenv('PUSH_BATCH_DELTA', '60'))                   # 执行 PUSH_BATCH 的时间间隔, 单位为秒, 默认为 60s, 非全局推动 QD 任务日志间隔


class websocket:
    # WebSocket 设置
    ping_interval = int(os.getenv('WS_PING_INTERVAL', '5'))                   # WebSocket ping 间隔, 单位为秒, 默认为 5s
    ping_timeout = int(os.getenv('WS_PING_TIMEOUT', '30'))                    # WebSocket ping超时时间, 单位为秒, 默认为 30s
    max_message_size = int(os.getenv('WS_MAX_MESSAGE_SIZE', '10485760'))  # WebSocket 单次接收最大消息大小, 默认为 10MB
    max_queue_size = int(os.getenv('WS_MAX_QUEUE_SIZE', '100'))               # WebSocket 最大消息队列大小, 默认为 100
    max_connections_subscribe = int(os.getenv('WS_MAX_CONNECTIONS_SUBSCRIBE', '30'))              # WebSocket 公共模板更新页面最大连接数, 默认为 30


# 订阅加速方式或地址, 用于加速公共模板更新, 仅适用于 GitHub.
# 可选 jsdelivr_cdn/jsdelivr_fastly/ghproxy/qd-ph/自定义地址, 默认为: qd-ph
# 自定义地址示例为: https://qd-gh.crossg.us.kg/https://raw.githubusercontent.com/
# 以直接替换 https://raw.githubusercontent.com/ 源文件地址.
subscribe_accelerate_url = os.getenv('SUBSCRIBE_ACCELERATE_URL', 'qd-ph')

# 全局代理域名列表相关设置
## proxies为全局代理域名列表, 默认为空[], 表示不启用全局代理;
## 代理格式应为'scheme://username:password@host:port',
## 例如: proxies = ['http://admin:admin@127.0.0.1:8923','https://proxy.com:8888'];
## 任务级代理请在新建或修改任务时添加,任务级代理优先级大于全局代理;
proxies = os.getenv('PROXIES', '').split('|')                               # 若希望部分地址不走代理, 请修改 `proxy_direct_mode` 及 `proxy_direct`
proxy_direct_mode = os.getenv('PROXY_DIRECT_MODE', 'regexp')                # 直连地址的匹配模式, 默认为 'regexp' 以过滤本地请求, 可选输入:
# 'regexp' 为正则表达式匹配模式;
# 'url' 为网址匹配模式;
# '' 空则不启用全局代理黑名单
## 不同 `proxy_direct_mode` 模式下的直连地址匹配规则:
## `proxy_direct_mode = os.getenv('PROXY_DIRECT_MODE', 'url')` 进入网址完全匹配模式,
## 在 `proxy_direct` 名单的 url 均不通过代理请求, 以 '|' 分隔url网址,
## url 格式应为 scheme://domain或scheme://domain:port
## 例如: proxy_direct = os.getenv('PROXY_DIRECT', 'http://127.0.0.1:80|https://localhost');
##
## `proxy_direct_mode= os.getenv('PROXY_DIRECT_MODE', 'regexp')` 进入正则表达式匹配模式,
## 满足正则表达式的网址均不通过代理请求;
## 启用 regexp 模式后自动采用以下默认匹配正则表达式, 如无特别需求请勿修改
proxy_direct = os.getenv('PROXY_DIRECT', r"""(?xi)\A
                ([a-z][a-z0-9+\-.]*://)?                                    # Scheme
                (0(.0){3}|127(.0){2}.1|localhost|\[::([\d]+)?\])            # Domain/Hostname/IPv4/IPv6
                (:[0-9]+)? """                                              # :Port
                         )

# 记事本设置
notepad_limit = int(os.getenv('NOTEPAD_LIMIT', '20'))                       # 单个用户拥有记事本最大数量, 默认为 20

# DdddOCR 设置
extra_onnx_name = os.getenv('EXTRA_ONNX_NAME', '').split('|')               # config 目录下自定义 ONNX 文件名(不含 ".onnx" 后缀), 多个onnx文件名用"|"分隔
extra_charsets_name = os.getenv('EXTRA_CHARSETS_NAME', '').split('|')       # config 目录下自定义 ONNX 对应自定义 `charsets.json` 文件名(不含 ".json" 后缀), 多个 json 文件名用"|"分隔

# 邮件发送相关配置
mail_smtp = os.getenv('MAIL_SMTP', "")                                      # 邮箱 SMTP 服务器
mail_port = int(os.getenv('MAIL_PORT', '465'))                              # 邮箱 SMTP 服务器端口
mail_ssl = bool(strtobool(os.getenv('MAIL_SSL', 'True')))                   # 是否使用 SSL 加密方式收发邮件
mail_starttls = bool(strtobool(os.getenv('MAIL_STARTTLS', 'False')))        # 是否使用 STARTTLS 加密方式收发邮件, 默认不启用
mail_user = os.getenv('MAIL_USER', '')                                      # 邮箱用户名
mail_password = os.getenv('MAIL_PASSWORD', '')                              # 邮箱密码
mail_from = os.getenv('MAIL_FROM', mail_user)                               # 发送时使用的邮箱，默认与 MAIL_USER 相同
mail_domain_https = bool(strtobool(os.getenv('ENABLE_HTTPS', 'False'))) or \
    bool(strtobool(os.getenv('MAIL_DOMAIN_HTTPS', 'False')))                # ))# 发送的邮件链接启用 HTTPS, 非框架自身 HTTPS 开关, 需要 HTTPS 请使用外部反向代理
## Mailgun 邮件发送方式配置
## Mailgun 中 Domain 为 QD 框架域名 `domain` 的值
mailgun_key = os.getenv('MAILGUN_KEY', "")                                  # Mailgun Api_Key, 若不为空则优先用 Mailgun 方式发送邮件
mailgun_domain = os.getenv('MAILGUN_DOMAIN', domain)                        # Mailgun Domain

# Google Analytics 设置
ga_key = os.getenv('GA_KEY', '')                                            # Google Analytics (GA) 密钥, 为空则不启用,
# GA 密钥格式为 G-XXXXXXXXXX,
# 如果为 UA-XXXXXXXXX-X, 请前往GA后台获取新版密钥

try:
    from local_config import *  # 修改 `local_config.py` 文件的内容不受通过 Git 更新源码的影响
    if not hasattr(mysql, 'auth_plugin'):
        setattr(mysql, 'auth_plugin', parse_qs(mysql_url.query).get('auth_plugin', [''])[0])
except ImportError:
    pass

try:
    from libs.parse_url import parse_url  # pylint: disable=ungrouped-imports
    for index, proxy in enumerate(proxies):
        if isinstance(proxy, str):
            proxies[index] = parse_url(proxy)
except Exception as e:
    raise e
