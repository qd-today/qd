#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-07 17:36:17

import time
import logging
import umsgpack

from Crypto.Hash import MD5

import config
from libs import mcrypto as crypto, utils
from basedb import BaseDB

logger = logging.getLogger('qiandao.userdb')
class UserDB(BaseDB):
    '''
    User DB

    id, email, email_verified, password, userkey, nickname, role, ctime, mtime, atime, cip, mip, aip
    '''
    __tablename__ = 'user'

    class UserDBException(Exception): pass
    class NoUserException(UserDBException): pass
    class DeplicateUser(UserDBException): pass
    class UserNameError(UserDBException): pass

    def __init__(self, host=config.mysql.host, port=config.mysql.port,
            database=config.mysql.database, user=config.mysql.user, passwd=config.mysql.passwd):
        import mysql.connector
        self.conn = mysql.connector.connect(user=user, password=passwd, host=host, port=port,
                database=database, autocommit=True)

    @staticmethod
    def check_nickname(nickname):
        if isinstance(nickname, unicode):
            nickname = nickname.encode('utf8')
        return len(nickname) < 64

    def add(self, email, password, ip):
        if self.get(email=email, fields='1') is not None:
            raise self.DeplicateUser('duplicate username')

        now = time.time()
        if isinstance(ip, basestring):
            ip = utils.ip2int(ip)
        userkey = umsgpack.unpackb(crypto.password_hash(password))[0]

        hash = MD5.new()
        hash.update(password.encode('utf-8'))
        password_md5 = hash.hexdigest()

        insert = dict(
                email = email,
                email_verified = 0,
                password = crypto.aes_encrypt(
                    crypto.password_hash(password), userkey),
                userkey = crypto.aes_encrypt(userkey),
                nickname = None,
                role = None,
                ctime = now,
                mtime = now,
                atime = now,
                cip = ip,
                mip = ip,
                aip = ip,
                password_md5 = password_md5,
                )
        return self._insert(**insert)

    def challenge(self, email, password):
        user = self.get(email=email, fields=('id', 'password'))
        if not user:
            return False
        password_hash = self.decrypt(user['id'], user['password'])
        if password_hash == crypto.password_hash(password, password_hash):
            return True

        return False

    def challenge_MD5(self, email, password):
        user = self.get(email=email, fields=('id', 'password_md5'))
        if not user:
            return False
        else:
            if (user['password_md5'] == ''):
                pass
            else:
                if password == user['password_md5']:
                    return True
        return False

    def mod(self, id, **kwargs):
        assert 'id' not in kwargs, 'id not modifiable'
        assert 'email' not in kwargs, 'email not modifiable'
        assert 'userkey' not in kwargs, 'userkey not modifiable'

        if 'password' in kwargs:
            kwargs['password'] = self.encrypt(id, crypto.password_hash(kwargs['password']))
            
        if 'token' in kwargs:
            kwargs['token'] = self.encrypt(id, crypto.password_hash(kwargs['token']))

        return self._update(where="id=%s" % self.placeholder, where_values=(id, ), **kwargs)

    @utils.method_cache
    def __getuserkey(self, id):
        for (userkey, ) in self._select(what='userkey',
                where='id=%s' % self.placeholder, where_values=(id, )):
            return crypto.aes_decrypt(userkey)

    def encrypt(self, id, data):
        if id:
            userkey = self.__getuserkey(id)
        else:
            userkey = config.aes_key

        try:
            return crypto.aes_encrypt(data, userkey)
        except Exception as e:
            raise self.UserDBException('encrypt error')

    def decrypt(self, id, data):
        if id:
            userkey = self.__getuserkey(id)
        else:
            userkey = config.aes_key
        try:
            return crypto.aes_decrypt(data, userkey)
        except Exception as e:
            raise self.UserDBException('decrypt error')

    def get(self, id=None, email=None, fields=None):
        assert 'userkey' not in fields, 'userkey not allow to get'

        if id:
            where = 'id = %s' % self.placeholder
            value = (id, )
        elif email:
            where = 'email = %s' % self.placeholder
            value = (email, )
        else:
            raise self.UserDBException('get user need id or email')

        for user in self._select2dic(what=fields, where=where, where_values=value):
            return user
    
    def list(self, fields=None, limit=None, **kwargs):
        where = '1=1'
        where_values = []
        for key, value in kwargs.iteritems():
            if value is None:
                where += ' and %s is %s' % (self.escape(key), self.placeholder)
            else:
                where += ' and %s = %s' % (self.escape(key), self.placeholder)
            where_values.append(value)
        for tpl in self._select2dic(what=fields, where=where, where_values=where_values, limit=limit):
            yield tpl

    def delete(self, id):
        self._delete(where="id=%s" % self.placeholder, where_values=(id, ))
