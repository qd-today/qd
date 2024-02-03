# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-07 17:36:17

# import os
# import sys
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time

import umsgpack
from Crypto.Hash import MD5
from sqlalchemy import (VARBINARY, Column, Integer, String, delete, select,
                        text, update)
from sqlalchemy.dialects.mysql import INTEGER, TINYINT

from db.basedb import AlchemyMixin, BaseDB, config
from libs import mcrypto as crypto
from libs import utils


class User(BaseDB, AlchemyMixin):
    '''
    User DB

    id, email, email_verified, password, userkey, nickname, role, ctime, mtime, atime, cip, mip, aip
    '''
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String(256), nullable=False, unique=True, index=True)
    email_verified = Column(TINYINT(1), nullable=False, server_default=text("'0'"))
    password = Column(VARBINARY(128), nullable=False)
    password_md5 = Column(VARBINARY(128), nullable=False, server_default=text("''"))
    userkey = Column(VARBINARY(128), nullable=False)
    ctime = Column(INTEGER, nullable=False)
    mtime = Column(INTEGER, nullable=False)
    atime = Column(INTEGER, nullable=False)
    cip = Column(VARBINARY(16), nullable=False)
    mip = Column(VARBINARY(16), nullable=False)
    aip = Column(VARBINARY(16), nullable=False)
    skey = Column(String(128), nullable=False, server_default=text("''"))
    barkurl = Column(String(128), nullable=False, server_default=text("''"))
    wxpusher = Column(String(128), nullable=False, server_default=text("''"))
    noticeflg = Column(INTEGER, nullable=False, server_default=text("'1'"))
    logtime = Column(String(1024), nullable=False, server_default=text('\'{"en":false,"time":"20:00:00","ts":0,"schanEn":false,"WXPEn":false}\''))
    status = Column(String(1024), nullable=False, server_default=text("'Enable'"))
    diypusher = Column(String(1024), nullable=False, server_default=text("''"))
    qywx_token = Column(String(1024), nullable=False, server_default=text("''"))
    tg_token = Column(String(1024), nullable=False, server_default=text("''"))
    dingding_token = Column(String(1024), nullable=False, server_default=text("''"))
    qywx_webhook = Column(String(1024), nullable=False, server_default=text("''"))
    push_batch = Column(String(1024), nullable=False, server_default=text('\'{"sw":false,"time":0,"delta":86400}\''))
    nickname = Column(String(64), unique=True, index=True)
    role = Column(String(128))

    class UserDBException(Exception):
        pass

    class NoUserException(UserDBException):
        pass

    class DeplicateUser(UserDBException):
        pass

    class UserNameError(UserDBException):
        pass

    @staticmethod
    def check_nickname(nickname):
        if isinstance(nickname, str):
            nickname = nickname.encode('utf8')
        return len(nickname) < 64

    async def add(self, email, password, ip, sql_session=None):
        user = await self.get(email=email, fields=('id',), sql_session=sql_session)
        if user is not None:
            raise self.DeplicateUser('duplicate username')

        now = time.time()
        if isinstance(ip, str):
            ip_version = utils.is_ip(ip)
            ip = utils.ip2varbinary(ip, ip_version)
        userkey = umsgpack.unpackb(crypto.password_hash(password))[0]

        hash = MD5.new()
        hash.update(password.encode('utf-8'))
        password_hash = crypto.password_hash(password)
        password_md5_hash = crypto.password_hash(hash.hexdigest(), password_hash)

        insert = dict(
            email=email,
            email_verified=0,
            password=crypto.aes_encrypt(password_hash, userkey),
            userkey=crypto.aes_encrypt(userkey),
            nickname=None,
            role=None,
            ctime=now,
            mtime=now,
            atime=now,
            cip=ip,
            mip=ip,
            aip=ip,
            password_md5=password_md5_hash,
        )
        await self._insert(User(**insert), sql_session=sql_session)
        return

    async def challenge(self, email, password, sql_session=None):
        user = await self.get(email=email, fields=('id', 'password'), sql_session=sql_session)
        if user is None:
            return False
        password_hash = await self.decrypt(user['id'], user['password'], sql_session=sql_session)
        if password_hash == crypto.password_hash(password, password_hash):
            return True

        return False

    async def challenge_md5(self, email, password_md5, sql_session=None):
        user = await self.get(email=email, fields=('id', 'password', 'password_md5'), sql_session=sql_session)
        if user is None:
            return False
        else:
            if user['password_md5'] == '':
                pass
            else:
                password_hash = await self.decrypt(user['id'], user['password'], sql_session=sql_session)
                if crypto.password_hash(password_md5, password_hash) == user['password_md5']:
                    return True
        return False

    async def mod(self, id, sql_session=None, **kwargs):
        assert 'id' not in kwargs, 'id not modifiable'
        assert 'email' not in kwargs, 'email not modifiable'
        assert 'userkey' not in kwargs, 'userkey not modifiable'

        if 'password' in kwargs:
            kwargs['password'] = await self.encrypt(id, crypto.password_hash(kwargs['password']), sql_session=sql_session)

        if 'token' in kwargs:
            kwargs['token'] = await self.encrypt(id, crypto.password_hash(kwargs['token']), sql_session=sql_session)

        result = await self._update(update(User).where(User.id == id).values(**kwargs), sql_session=sql_session)
        return result

    # @utils.method_cache
    async def __getuserkey(self, id, sql_session=None):
        row = await self.get(id=id, fields=('userkey',), sql_session=sql_session)
        return crypto.aes_decrypt(row['userkey'])

    async def encrypt(self, id, data, sql_session=None):
        if id:
            userkey = await self.__getuserkey(id, sql_session=sql_session)
        else:
            userkey = config.aes_key

        try:
            return crypto.aes_encrypt(data, userkey)
        except Exception as exc:
            raise self.UserDBException('encrypt error') from exc

    async def decrypt(self, id, data, sql_session=None):
        if id:
            userkey = await self.__getuserkey(id, sql_session=sql_session)
        else:
            userkey = config.aes_key
        try:
            old = tmp = crypto.aes_decrypt(data, userkey)
            if isinstance(tmp, dict):
                old = {}
                for key, value in tmp.items():
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    old[key] = value
            return old
        except Exception as exc:
            raise self.UserDBException('decrypt error') from exc

    async def get(self, id=None, email=None, fields=None, one_or_none=False, first=True, to_dict=True, sql_session=None):
        if fields is None:
            _fields = User
        else:
            _fields = (getattr(User, field) for field in fields)

        if id:
            smtm = select(_fields).where(User.id == id)
        elif email:
            smtm = select(_fields).where(User.email == email)
        else:
            raise self.UserDBException('get user need id or email')

        result = await self._get(smtm, one_or_none=one_or_none, first=first, sql_session=sql_session)
        if to_dict and result is not None:
            return self.to_dict(result, fields)
        return result

    async def list(self, fields=None, limit=None, to_dict=True, sql_session=None, **kwargs):
        if fields is None:
            _fields = User
        else:
            _fields = (getattr(User, field) for field in fields)

        smtm = select(_fields)

        for key, value in kwargs.items():
            smtm = smtm.where(getattr(User, key) == value)

        if limit:
            smtm = smtm.limit(limit)

        result = await self._get(smtm, sql_session=sql_session)
        if to_dict and result is not None:
            return [self.to_dict(row, fields) for row in result]
        return result

    def delete(self, id, sql_session=None):
        return self._delete(delete(User).where(User.id == id), sql_session=sql_session)


if __name__ == '__main__':
    import asyncio

    async def test():
        user = User()
        try:
            async with user.session as sql_session:
                async with sql_session.begin():
                    await user.add('admin1@localhost', 'admin', '127.0.0.1', sql_session=sql_session)
            await user.add('admin2@localhost', 'admin', '127.0.0.1')
        except User.DeplicateUser as e:
            print(e)
        await user.get(email='admin1@localhost')
        user1 = await user.get(email='admin1@localhost')
        user2 = await user.get(email='admin2@localhost', fields=('id',))
        print('user1: ', user1)
        print('user2: ', user2)

        user1_list = await user.list(email='admin1@localhost')
        user2_list = await user.list(email='admin2@localhost', fields=('id', 'email', 'password'))
        print('user1_list: ', user1_list)
        print('user2_list: ', user2_list)

        await user.mod(user1['id'], password='admin1')
        user1 = await user.get(email='admin1@localhost')
        print('user1 after mod : ', user1)

        await user.delete(user1['id'])
        await user.delete(user2['id'])
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = asyncio.ensure_future(test(), loop=loop)
    loop.run_until_complete(task)
