#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 20:40:53

import config
import umsgpack
from libs.log import Log
from libs.utils import is_lan

logger_RedisDB = Log('qiandao.RedisDB').getlogger()
class RedisDB(object):
    def __init__(self, host=config.redis.host, port=config.redis.port, password=config.redis.passwd, db=config.redis.db, evil=config.evil):
        try:
            import redis
        except ImportError:
            self.client = None
            return

        self.evil_limit = evil
        try:
            self.client = redis.StrictRedis(host=host, port=port, password=password, db=db, socket_timeout=3, socket_connect_timeout=3)
            self.client.ping()
        except redis.exceptions.ConnectionError as e:
            logger_RedisDB.warning('Connect Redis falied: %s',e)
            self.client = None

    def evil(self, ip, userid, cnt=None):
        if not self.client:
            return
        if cnt == self.client.incrby('ip_%s' % ip, cnt):
            self.client.expire('ip_%s' % ip, 3600)
        if userid and cnt == self.client.incrby('user_%s' % userid, cnt):
            self.client.expire('user_%s' % userid, 3600)

    def is_evil(self, ip, userid=None):
        if not self.client:
            return False
        if config.evil_pass_lan_ip and is_lan(ip):
            return False
        if userid:
            if int(self.client.get('user_%s' % userid) or '0') > self.evil_limit:
                return True
            else:
                return False
        if int(self.client.get('ip_%s' % ip) or '0') > self.evil_limit:
            return True
        return False

    def cache(self, key, _lambda, timeout=60*60):
        if not self.client:
            return _lambda()
        ret = self.client.get('cache_%s' % key)
        if ret:
            return umsgpack.unpackb(ret)
        ret = _lambda()
        self.client.set('cache_%s', umsgpack.packb(ret))
        return ret

    def close(self):
        if self.client:
            self.client.close()
