#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-07-30 12:21:48

import os
import hashlib
from urllib.parse import urlparse,parse_qs
from distutils.util import strtobool

debug = bool(strtobool(os.getenv('QIANDAO_DEBUG','False')))                 # 是否启用Debug
multiprocess = bool(strtobool(os.getenv('MULTI_PROCESS','False')))          # 是否启用多进程模式, Windows平台无效, 请谨慎使用
autoreload = bool(strtobool(os.getenv('AUTO_RELOAD','False')))              # 是否启用自动热加载, multiprocess=True时无效
gzip = bool(strtobool(os.getenv('GZIP','True')))                            # 是否启用gzip
bind = str(os.getenv('BIND', '0.0.0.0'))                                    # 框架运行监听地址(0.0.0.0表示监听所有IP地址)
port = int(os.getenv('PORT', 8923))                                         # 监听端口Port
queue_num = int(os.getenv('QUEUE_NUM', 50))                                 # 定时执行任务队列最大数量
https = bool(strtobool(os.getenv('ENABLE_HTTPS', 'False')))                 # 发送的邮件链接启用HTTPS, 非框架自身HTTPS开关, 需要HTTPS请使用外部反向代理
accesslog = bool(strtobool(os.getenv('ACCESS_LOG', 'True')))                # 是否输出Access Log

# 发送邮件及微信推送内链接域名, 如果是通过IP+端口Port方式请正确输入`IP:Port`
domain = os.getenv('DOMAIN', 'qiandao.today')                               # 指定域名, 建议修改, 不然邮件重置密码之类的功能无效

# PyCurl 相关设置
use_pycurl = bool(strtobool(os.getenv('USE_PYCURL','True')))                # 是否启用Pycurl模组, 当环境无PyCurl模组时无效
allow_retry = bool(strtobool(os.getenv('ALLOW_RETRY', 'True')))             # 在Pycurl环境下部分请求可能导致Request错误时, 自动修改冲突设置并重发请求
dns_server = str(os.getenv('DNS_SERVER', ''))                               # 通过Curl使用指定DNS进行解析(仅支持Pycurl环境)
curl_encoding = bool(strtobool(os.getenv('CURL_ENCODING', 'True')))         # 是否允许使用Curl进行Encoding操作, 当PyCurl返回"Error 61 Unrecognized transfer encoding."错误且'ALLOW_RETRY=True'时, 本次请求禁用Headers中的Content-Encoding并重试
curl_length = bool(strtobool(os.getenv('CURL_CONTENT_LENGTH', 'True')))     # 是否允许Curl使用Headers中自定义Content-Length请求, 当PyCurl返回"HTTP 400 Bad Request"错误且'ALLOW_RETRY=True'时, 本次请求禁用Headers中的Content-Length并重试
not_retry_code = list(map(int,os.getenv('NOT_RETRY_CODE', '301|302|303|304|305|307|400|401|403|404|405|407|408|409|410|412|415|413|414|500|501|502|503|504|599').split('|')))
                                                                            # 启用后, 当满足PyCurl启用, HTTPError code不在该列表中, 任务代理为空, 且'ALLOW_RETRY=True'时, 本次请求禁用Pycurl并重试
empty_retry = bool(strtobool(os.getenv('EMPTY_RETRY', 'True')))             # 启用后, 当满足PyCurl启用, 返回Response为空, 任务代理为空, 且'ALLOW_RETRY=True'时, 本次请求禁用Pycurl并重试

cookie_days = int(os.getenv('COOKIE_DAY', 5))                               # Cookie在客户端保留时间
mysql_url = urlparse(os.getenv('JAWSDB_MARIA_URL', ''))                     # 格式: mysql://用户名:密码@hostname:port/数据库名?auth_plugin=
redis_url = urlparse(os.getenv('REDISCLOUD_URL', ''))                       # 格式: (redis/http)://rediscloud:密码@hostname:port

# 日志及推送设置
traceback_print = bool(strtobool(os.getenv('TRACEBACK_PRINT', 'True' if debug else 'False')))    # 是否启用在控制台日志中打印Exception的TraceBack信息
push_pic = os.getenv('PUSH_PIC_URL', 'https://gitee.com/a76yyyy/qiandao/raw/master/web/static/img/push_pic.png')      # 日志推送默认图片地址
push_batch_sw = bool(strtobool(os.getenv('PUSH_BATCH_SW', 'True')))         # 是否允许开启定期推送签到任务日志, 默认为 True
push_batch_delta = int(os.getenv('PUSH_BATCH_DELTA', 60))                   # 执行 PUSH_BATCH 的时间间隔, 单位为秒, 默认为 60s, 非全局推动签到任务日志间隔

class mysql(object):
    host = mysql_url.hostname or 'localhost'                                # 访问MySQL的Hostname
    port = mysql_url.port or '3306'                                         # MySQL的端口Port
    database = mysql_url.path[1:] or 'qiandao'                              # 签到框架的数据库名
    user = mysql_url.username or 'qiandao'                                  # 拥有访问MySQL签到框架数据库权限的用户名
    passwd = mysql_url.password or None                                     # 用户名对应的密码
    auth_plugin = parse_qs(mysql_url.query).get('auth_plugin',[''])[0]      # auth_plugin, 默认为空, 可修改为'mysql_native_password','caching_sha2_password'

class sqlite3(object):
    path = os.path.join(os.path.dirname(__file__),'config','database.db')   # Sqlite3数据库文件地址

# 数据库类型, 修改 sqlite3 为 mysql 使用 mysql
db_type = os.getenv('DB_TYPE', 'sqlite3')                                   # 默认为Sqlite3, 需要使用MySQL时设置为'mysql'

# SQLAlchmey配置
class sqlalchemy(object):
    logging_name = os.getenv('QIANDAO_SQL_LOGGING_NAME', 'qiandao.sql')     # SQLAlchmey日志名称
    logging_level = os.getenv('QIANDAO_SQL_LOGGING_LEVEL', 'WARNING')             # SQLAlchmey日志级别
    pool_logging_name = os.getenv('QIANDAO_SQL_POOL_LOGGING_NAME', 'qiandao.sql.pool')                  # 连接池日志名称
    pool_logging_level = os.getenv('QIANDAO_SQL_POOL_LOGGING_LEVEL', 'WARNING')   # 连接池日志级别
    pool_size = int(os.getenv('QIANDAO_SQL_POOL_SIZE', '5'))                # 连接池大小
    max_overflow = int(os.getenv('QIANDAO_SQL_MAX_OVERFLOW', '10'))         # 连接池连接数量超过 pool_size 时, 最大连接数
    pool_pre_ping = bool(strtobool(os.getenv('QIANDAO_SQL_POOL_PRE_PING', 'True')))     # 是否在获取连接前进行 ping 操作, 默认为 True
    pool_recycle = int(os.getenv('QIANDAO_SQL_POOL_RECYCLE', '3600'))     # 连接池中连接复用时间, 默认为 3600 秒
    pool_timeout = int(os.getenv('QIANDAO_SQL_POOL_TIMEOUT', '30'))         # 连接池获取连接超时时间, 默认为 30 秒
    pool_use_lifo = bool(strtobool(os.getenv('QIANDAO_SQL_POOL_USE_LIFO', 'True')))     # 连接池是否使用 LIFO, 默认为 True

# redis 连接参数, 可选
class redis(object):
    host = redis_url.hostname or 'localhost'                                # 访问Redis的Hostname
    port = redis_url.port or 6379                                           # Redis的端口Port
    passwd = redis_url.password or None                                     # 访问Redis权限密码
    db = int(os.getenv('REDIS_DB_INDEX', 1))                                # 索引
evil = int(os.getenv('QIANDAO_EVIL', 500))                                  # Redis连接成功后生效, 用于登录用户或IP在1小时内 操作失败(如登录, 验证, 测试等操作)次数*相应惩罚分值 达到evil值上限后自动封禁直至下一小时周期
evil_pass_lan_ip = bool(strtobool(os.getenv('EVIL_PASS_LAN_IP','True')))    # 是否针对本机私有IP地址用户及Localhost_API请求关闭evil限制

pbkdf2_iterations = int(os.getenv('PBKDF2_ITERATIONS', 400))                # pbkdf2 迭代次数
aes_key = hashlib.sha256(os.getenv('AES_KEY', 'binux').encode('utf-8')).digest()                # AES加密密钥, 强烈建议修改
cookie_secret = hashlib.sha256(os.getenv('COOKIE_SECRET', 'binux').encode('utf-8')).digest()    # Cookie加密密钥, 强烈建议修改
check_task_loop = int(os.getenv('CHECK_TASK_LOOP', 500))                    # Worker检查任务工作循环时间, 单位毫秒
# Tornado httpclient.HTTPRequest参数配置
download_size_limit = int(os.getenv('DOWNLOAD_SIZE_LIMIT', 5*1024*1024))    # 允许用户单次请求下载最大值
request_timeout = float(os.getenv('REQUEST_TIMEOUT', 30.0))                 # HTTPRequest 请求超时时间
connect_timeout = float(os.getenv('CONNECT_TIMEOUT', 30.0))                 # HTTPRequest 连接超时时间
delay_max_timeout = float(os.getenv('DELAY_MAX_TIMEOUT', 29.9))             # delay 延时API最大时间限制, 请小于上述timeout配置, 否则会报599错误

# 以下为全局代理域名列表相关设置
# proxies为全局代理域名列表, 默认为空[], 表示不启用全局代理; 
# 代理格式应为'scheme://username:password@host:port',例如:proxies = ['http://admin:admin@127.0.0.1:8923','https://proxy.com:8888']; 
# 任务级代理请在新建或修改任务时添加,任务级代理优先级大于全局代理; 
proxies = os.getenv('PROXIES', '').split('|')                               # 若希望部分地址不走代理, 请修改proxy_direct_mode及proxy_direct 
proxy_direct_mode = os.getenv('PROXY_DIRECT_MODE', 'regexp')                # 默认为'regexp'以过滤本地请求, 可选输入:'regexp'为正则表达式匹配模式;'url'为网址匹配模式;''空则不启用全局代理黑名单 
# proxy_direct_mode = os.getenv('PROXY_DIRECT_MODE', 'url')进入网址完全匹配模式, 在proxy_direct名单的url均不通过代理请求, 以'|'分隔url网址, url格式应为scheme://domain或scheme://domain:port 
# 例如: proxy_direct = os.getenv('PROXY_DIRECT', 'http://127.0.0.1:80|https://localhost'); 
# proxy_direct_mode= os.getenv('PROXY_DIRECT_MODE', 'regexp')进入正则表达式匹配模式, 满足正则表达式的网址均不通过代理请求; 
# 启用regexp模式后自动采用以下默认匹配正则表达式, 如无特别需求请勿修改
proxy_direct = os.getenv('PROXY_DIRECT', r"""(?xi)\A
                ([a-z][a-z0-9+\-.]*://)?                                    # Scheme
                (0(.0){3}|127(.0){2}.1|localhost|\[::([\d]+)?\])            # Domain/Hostname/IPv4/IPv6
                (:[0-9]+)? """                                              # :Port
                ) 

new_task_delay = int(os.getenv('NEW_TASK_DELAY', 1))                        # 新建任务后准备时间

# ddddocr设置
extra_onnx_name = os.getenv('EXTRA_ONNX_NAME', '').split('|')               # config目录下自定义ONNX文件名(不含 ".onnx" 后缀), 多个onnx文件名用"|"分隔
extra_charsets_name = os.getenv('EXTRA_CHARSETS_NAME', '').split('|')       # config目录下自定义ONNX对应自定义charsets.json文件名(不含 ".json" 后缀), 多个json文件名用"|"分隔

# 邮件发送相关配置
mail_smtp = os.getenv('MAIL_SMTP',"")                                       # 邮箱SMTP服务器
mail_port = int(os.getenv('MAIL_PORT', 465))                                # 邮箱SMTP服务器端口
mail_ssl = bool(strtobool(os.getenv('MAIL_SSL','True')))                    # 是否使用SSL加密方式收发邮件
mail_user = os.getenv('MAIL_USER', '')                                      # 邮箱用户名
mail_password = os.getenv('MAIL_PASSWORD', '')                              # 邮箱密码
mail_from = os.getenv('MAIL_FROM', mail_user)                               # 发送时使用的邮箱，默认与MAIL_USER相同
mail_domain = os.getenv('MAIL_DOMAIN', "mail.qiandao.today")                # 发送邮件内容显示邮箱域名
# Mailgun Api_Key
mailgun_key = os.getenv('MAILGUN_KEY',"")                                   # 优先用`mailgun`方式发送邮件

# google analytics
ga_key = ""                                                                 # google analytics密钥
user0isadmin = bool(strtobool(os.getenv('USER0ISADMIN','True'))) 

try:
    from local_config import *                                              # 修改local_config.py文件的内容不受通过git更新源码的影响
    if not hasattr(mysql, 'auth_plugin'):
        setattr(mysql, 'auth_plugin', parse_qs(mysql_url.query).get('auth_plugin',[''])[0])
except ImportError:
    pass

try:
    from libs.parse_url import parse_url
    for index,proxy in enumerate(proxies):
        if isinstance(proxy,str):
            proxies[index] = parse_url(proxy)
except Exception as e:
    raise e
