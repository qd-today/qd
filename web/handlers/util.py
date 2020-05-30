#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base import *
from tornado import gen

import json
import re

class UtilDelayHandler(BaseHandler):
    @gen.coroutine
    def get(self, seconds):
        seconds = float(seconds)
        if seconds < 0:
            seconds = 0
        elif seconds > 30:
            seconds = 30
        yield gen.sleep(seconds)
        self.write(u'delay %s second.' % seconds)

handlers = [
    ('/util/delay/(\d+)', UtilDelayHandler),
]
