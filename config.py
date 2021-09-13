#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-07-30 12:21:48

import os
import hashlib
from urllib.parse import urlparse

debug = False                                               # 是否开启Debug
gzip = True                                                 # 是否启用gzip
bind = str(os.getenv('BIND', '0.0.0.0'))                    # 框架运行监听地址(0.0.0.0表示监听所有IP地址)、
port = int(os.getenv('PORT', 8923))                         # 监听端口Port
https = bool(os.getenv('ENABLE_HTTPS', False))              # 发送的邮件链接启用HTTPS，非程序使用HTTPS，需要HTTPS需要使用反向代理
cookie_days = 5                                             # Cookie在客户端保留时间
mysql_url = urlparse(os.getenv('JAWSDB_MARIA_URL', ''))     # 格式: mysql://用户名:密码@hostname:port/数据库名
redis_url = urlparse(os.getenv('REDISCLOUD_URL', ''))       # 格式: (redis/http)://rediscloud:密码@hostname:port

class mysql(object):
    host = mysql_url.hostname or 'localhost'                # 访问MySQL的Hostname
    port = mysql_url.port or '3306'                         # MySQL的端口Port
    database = mysql_url.path[1:] or 'qiandao'              # 签到框架的数据库名
    user = mysql_url.username or 'qiandao'                  # 拥有访问MySQL签到框架数据库权限的用户名
    passwd = mysql_url.password or None                     # 用户名对应的密码

class sqlite3(object):
    path = './config/database.db'                           # Sqlite3数据库文件地址

# 数据库类型，修改 sqlite3 为 mysql 使用 mysql
db_type = os.getenv('DB_TYPE', 'sqlite3')                   # 默认为Sqlite3,需要使用MySQL时设置为'mysql'

# redis 连接参数，可选
class redis(object):
    host = redis_url.hostname or 'localhost'                # 访问Redis的Hostname
    port = redis_url.port or 6379                           # Redis的端口Port
    passwd = redis_url.password or None                     # 访问Redis权限密码
    db = int(os.getenv('REDIS_DB_INDEX', 1))                # 索引
evil = 100                                                  # 1小时内登录用户或IP上限

pbkdf2_iterations = 400                                     # pbkdf2 迭代次数
aes_key = hashlib.sha256(os.getenv('AES_KEY', 'binux').encode('utf-8')).digest()                # AES加密密钥，强烈建议修改
cookie_secret = hashlib.sha256(os.getenv('COOKIE_SECRET', 'binux').encode('utf-8')).digest()    # Cookie加密密钥，强烈建议修改
check_task_loop = 500                                       # Worker检查任务工作循环时间，单位毫秒
# Tornado httpclient.HTTPRequest参数配置
download_size_limit = 5*1024*1024                           # 允许用户单次请求下载最大值
request_timeout = 30.0                                      # HTTPRequest 请求超时时间
connect_timeout = 30.0                                      # HTTPRequest 连接超时时间
delay_max_timeout = 29.9                                    # delay 延时API最大时间限制，请小于上述timeout配置，否则会报599错误

# 全局代理域名列表相关设置
proxies = []                                                # proxies为全局代理域名列表，若希望部分地址不走代理，请修改proxy_direct_mode及proxy_direct
proxy_direct_mode = os.getenv('PROXY_DIRECT_MODE', '')      # url为网址匹配模式;regexp为正则表达式匹配模式;空则进行全局代理
# url为网址完全匹配模式, 在proxy_direct名单的url均不通过代理请求，以'|'分隔url网址, url格式应为scheme://domain或scheme://domain:port, 例如:os.getenv('PROXY_DIRECT', 'http://127.0.0.1:80|https://localhost') 
# regexp为正则表达式匹配模式, 满足正则表达式的网址均不通过代理请求
proxy_direct = os.getenv('PROXY_DIRECT', r"""(?xi)\A
                ([a-z][a-z0-9+\-.]*://)?                                                        # Scheme
                (0(.0){3}|127(.0){2}.1|localhost|\[::([\d]+)?\])                                # Domain/Hostname/IPv4/IPv6
                (:[0-9]+)? """                                                                  # :Port
                ) 

new_task_delay = 1                                          # 新建任务后准备时间

# 发送邮件内链接域名，如果是通过IP+端口Port方式请正确输入`IP:Port`
domain = os.getenv('DOMAIN', 'qiandao.today')               # 指定域名，建议修改，不然邮件重置密码之类的功能无效

# 邮件发送相关配置
mail_smtp = os.getenv('MAIL_SMTP',"")                       # 邮箱SMTP服务器
mail_port = int(os.getenv('MAIL_PORT', 465))                # 邮箱SMTP服务器端口
mail_ssl = True                                             # 是否使用SSL加密方式收发邮件
mail_user = os.getenv('MAIL_USER', '')                      # 邮箱用户名
mail_password = os.getenv('MAIL_PASSWORD', '')              # 邮箱密码
mail_domain = os.getenv('MAIL_DOMAIN', "mail.qiandao.today")# 发送邮件内容显示邮箱域名
# Mailgun Api_Key
mailgun_key = ""                                            # 优先用`mailgun`方式发送邮件

# google analytics
ga_key = ""                                                 # google analytics密钥

try:
    from local_config import *                              # 修改local_config.py文件的内容不受通过git更新源码的影响
except ImportError:
    pass
