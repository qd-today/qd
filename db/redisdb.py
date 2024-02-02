#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 20:40:53

from typing import Any, Optional

import umsgpack

import config
from libs.log import Log
from libs.utils import is_lan

try:
    import redis
    REDIS: Optional[Any] = redis
except ImportError:
    REDIS = None

logger_redis_db = Log('QD.RedisDB').getlogger()


class RedisDB(object):
    def __init__(self, host=config.redis.host, port=config.redis.port, password=config.redis.passwd, db=config.redis.db, evil=config.evil):
        if REDIS is None:
            self.client = None
            return

        self.evil_limit = evil
        try:
            self.client = redis.StrictRedis(host=host, port=port, password=password, db=db, socket_timeout=3, socket_connect_timeout=3)
            self.client.ping()
        except redis.ConnectionError as e:
            if config.display_import_warning:
                logger_redis_db.warning('Connect Redis falied: \"%s\". \nTips: This warning message is only for prompting, it will not affect running of QD framework. ', e)
            self.client = None

    def evil(self, ip, userid, cnt=None):
        if not self.client:
            return
        if cnt == self.client.incrby(f'ip_{ip}', cnt):
            self.client.expire(f'ip_{ip}', 3600)
        if userid and cnt == self.client.incrby(f'user_{userid}', cnt):
            self.client.expire(f'user_{userid}', 3600)

    def is_evil(self, ip, userid=None):
        if not self.client:
            return False
        if config.evil_pass_lan_ip and is_lan(ip):
            return False
        if userid:
            if int(self.client.get(f'user_{userid}') or '0') > self.evil_limit:
                return True
            return False
        if int(self.client.get(f'ip_{ip}') or '0') > self.evil_limit:
            return True
        return False

    def cache(self, key, _lambda, timeout=60 * 60):
        if not self.client:
            return _lambda()
        ret = self.client.get(f'cache_{key}')
        if ret:
            return umsgpack.unpackb(ret)
        ret = _lambda()
        packed_ret = umsgpack.packb(ret)
        self.client.set(f'cache_{key}', packed_ret)
        if timeout:
            self.client.expire(f'cache_{key}', timeout)
        return ret

    def close(self):
        if self.client:
            self.client.close()
