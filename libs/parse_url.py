#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: A76yyyy<q981331502@163.com>
#         http://www.a76yyyy.cn
# Created on 2022-03-14 12:00:00

import re
def parse_url(url):
    if not url:
        return None
    result = re.match('((?P<scheme>(https?|socks5h?)+)://)?((?P<username>[^:@/]+)(:(?P<password>[^@/]+))?@)?(?P<host>[^:@/]+):(?P<port>\d+)', url)
    return None if not result else {
        'scheme': result.group('scheme'),
        'host': result.group('host'),
        'port': int(result.group('port')),
        'username': result.group('username'),
        'password': result.group('password'),
    }