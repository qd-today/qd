#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 21:06:02

import time
from .base import *

import requests
import re
import codecs
import os

class AboutHandler(BaseHandler):
    @tornado.web.addslash
    def get(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'tpl','about.html'), 'r',encoding='utf-8') as f:
            html_content = f.read()

        self.finish(html_content)

handlers = [
        ('/about/?', AboutHandler),
        ]
