#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 20:28:15

import os
import sys

from db.basedb import AlchemyMixin

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from .notepad import Notepad
from .pubtpl import Pubtpl
from .push_request import PushRequest
from .redisdb import RedisDB
from .site import Site
from .task import Task
from .tasklog import Tasklog
from .tpl import Tpl
from .user import User


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
        
