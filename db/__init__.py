#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 20:28:15


from db.basedb import AlchemyMixin
from db.notepad import Notepad
from db.pubtpl import Pubtpl
from db.push_request import PushRequest
from db.redisdb import RedisDB
from db.site import Site
from db.task import Task
from db.tasklog import Tasklog
from db.tpl import Tpl
from db.user import User


class DB(AlchemyMixin):
    def __init__(self) -> None:
        self.user = User()
        self.tpl = Tpl()
        self.task = Task()
        self.tasklog = Tasklog()
        self.push_request = PushRequest()
        self.redis = RedisDB()
        self.site = Site()
        self.pubtpl = Pubtpl()
        self.notepad = Notepad()
