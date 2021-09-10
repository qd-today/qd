#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-07-30 12:21:48

import os
import hashlib
from urllib.parse import urlparse

debug = False
gzip = True
bind = str(os.getenv('BIND', '0.0.0.0'))
port = int(os.getenv('PORT', 8923))
https = bool(os.getenv('ENABLE_HTTPS', False))
cookie_days = 5
mysql_url = urlparse(os.getenv('JAWSDB_MARIA_URL', ''))
redis_url = urlparse(os.getenv('REDISCLOUD_URL', ''))

class mysql(object):
    host = mysql_url.hostname or 'localhost'
    port = mysql_url.port or '3306'
    database = mysql_url.path[1:] or 'qiandao'
    user = mysql_url.username or 'qiandao'
    passwd = mysql_url.password or None

class sqlite3(object):
    path = './config/database.db'

# 数据库类型，修改 sqlite3 为 mysql 使用 mysql
db_type = os.getenv('DB_TYPE', 'sqlite3')

# redis 连接参数，可选
class redis(object):
    host = redis_url.hostname or 'localhost'
    port = redis_url.port or 6379
    passwd = redis_url.password or None
    db = int(os.getenv('REDIS_DB_INDEX', 1))
evil = 100

pbkdf2_iterations = 400
aes_key = hashlib.sha256(os.getenv('AES_KEY', 'binux').encode('utf-8')).digest()
cookie_secret = hashlib.sha256(os.getenv('COOKIE_SECRET', 'binux').encode('utf-8')).digest()
check_task_loop = 500
# Tornado httpclient.HTTPRequest参数配置
download_size_limit = 5*1024*1024
request_timeout = 30.0
connect_timeout = 30.0
# delay 延时API最大时间限制，请小于上述timeout配置，否则会报599错误
delay_max_timeout = 29.9
# proxies为全局代理域名列表，若希望部分地址不走代理，请修改proxy_direct_mode及proxy_direct
proxies = []
proxy_direct_mode = os.getenv('PROXY_DIRECT_MODE', '') # url为网址匹配模式;regexp为正则表达式匹配模式;空则进行全局代理
# url为网址完全匹配模式, 在proxy_direct名单的url均不通过代理请求，以'|'分隔url网址, url格式应为scheme://domain或scheme://domain:port, 例如:os.getenv('PROXY_DIRECT', 'http://127.0.0.1:80|https://localhost') 
# regexp为正则表达式匹配模式, 满足正则表达式的网址均不通过代理请求
proxy_direct = os.getenv('PROXY_DIRECT', r"""(?xi)\A
                ([a-z][a-z0-9+\-.]*://)?                            # scheme
                (0(.0){3}|127(.0){2}.1|localhost|\[::([\d]+)?\])    # domain
                (:[0-9]+)? """                                      # :port
                ) 
# 新建任务后准备时间
new_task_delay = 1

# 域名
domain = os.getenv('DOMAIN', 'qiandao.today')

# mailgun 邮件发送, 域名和 apikey
mail_smtp = os.getenv('MAIL_SMTP',"")
mail_port = int(os.getenv('MAIL_PORT', 465))
mail_ssl = True
mail_user = os.getenv('MAIL_USER', '')
mail_password = os.getenv('MAIL_PASSWORD', '')
mail_domain = os.getenv('MAIL_DOMAIN', "mail.qiandao.today")
mailgun_key = ""

# google analytics
ga_key = ""

try:
    from local_config import *
except ImportError:
    pass
