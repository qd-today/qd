# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: a76yyyy<q981331502@163.com>
# Created on 2022-08-12 18:41:09

# import os
# import sys
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import Column, Integer, Text, delete, select, update

from db.basedb import AlchemyMixin, BaseDB


class Notepad(BaseDB, AlchemyMixin):
    '''
    Site db

    regEn
    '''
    __tablename__ = 'notepad'
    id = Column(Integer, primary_key=True)
    userid = Column(Integer, nullable=False)
    notepadid = Column(Integer, nullable=False)
    content = Column(Text)

    def add(self, insert, sql_session=None):
        return self._insert(Notepad(**insert), sql_session=sql_session)

    def mod(self, userid, notepadid, sql_session=None, **kwargs):
        assert userid, 'need userid'
        assert notepadid, 'need notepadid'

        return self._update(update(Notepad).where(Notepad.userid == userid).where(Notepad.notepadid == notepadid).values(**kwargs), sql_session=sql_session)

    async def get(self, userid, notepadid, fields=None, one_or_none=False, first=True, to_dict=True, sql_session=None):
        assert userid, 'need userid'
        assert notepadid, 'need notepadid'

        if fields is None:
            _fields = Notepad
        else:
            _fields = (getattr(Notepad, field) for field in fields)

        smtm = select(_fields).where(Notepad.userid == userid).where(Notepad.notepadid == notepadid)

        result = await self._get(smtm, one_or_none=one_or_none, first=first, sql_session=sql_session)
        if to_dict and result is not None:
            return self.to_dict(result, fields)
        return result

    async def list(self, fields=None, limit=1000, to_dict=True, sql_session=None, **kwargs):
        if fields is None:
            _fields = Notepad
        else:
            _fields = (getattr(Notepad, field) for field in fields)

        smtm = select(_fields)

        for key, value in kwargs.items():
            smtm = smtm.where(getattr(Notepad, key) == value)

        if limit:
            smtm = smtm.limit(limit)

        result = await self._get(smtm, sql_session=sql_session)
        if to_dict and result is not None:
            return [self.to_dict(row, fields) for row in result]
        return result

    def delete(self, userid, notepadid, sql_session=None):
        return self._delete(delete(Notepad).where(Notepad.userid == userid).where(Notepad.notepadid == notepadid), sql_session=sql_session)


if __name__ == '__main__':
    import asyncio

    async def test():
        notepad = Notepad()
        try:
            async with notepad.transaction() as sql_session:
                await notepad.add({'userid': 1, 'notepadid': 1, 'content': 'test'}, sql_session=sql_session)
            await notepad.add({'userid': 1, 'notepadid': 2})
            await notepad.add({'userid': 2, 'notepadid': 1})
            await notepad.add({'userid': 2, 'notepadid': 2})
        except Exception as e:
            print(e)
        notepad1 = await notepad.get(1, 1)
        notepad1_content = await notepad.get(1, 1, fields=('content',))
        notepad_list = await notepad.list(userid=1)
        notepad_list_content = await notepad.list(userid=1, fields=('content',))
        print('notepad1: ', notepad1)
        print('notepad1_content: ', notepad1_content)
        print('notepad_list: ', notepad_list)
        print('notepad_list_content: ', notepad_list_content)

        await notepad.mod(1, 1, content='test1')
        notepad1 = await notepad.get(1, 1)
        print('notepad1 after mod : ', notepad1)

        await notepad.delete(1, 1)
        await notepad.delete(1, 2)
        await notepad.delete(2, 1)
        await notepad.delete(2, 2)
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = asyncio.ensure_future(test(), loop=loop)
    loop.run_until_complete(task)
