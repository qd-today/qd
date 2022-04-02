#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-07-30 12:22:52

import os
import jinja2
import tornado.web

import config
import json
from libs import utils
from libs.fetcher import Fetcher
from web.handlers import handlers, ui_modules, ui_methods
from libs.log import Log

logger_Web = Log('qiandao.Web').getlogger()
class Application(tornado.web.Application):
    def __init__(self,db=None):
        settings = dict(
                template_path = os.path.join(os.path.dirname(__file__), "tpl"),
                static_path = os.path.join(os.path.dirname(__file__), "static"),
                debug = config.debug,
                gzip = config.gzip,
                autoreload = config.autoreload,

                cookie_secret = config.cookie_secret,
                login_url = '/login',
                )
        version_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "version.json")
        super(Application, self).__init__(handlers, **settings)

        self.jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(settings['template_path']),
                extensions=['jinja2.ext.loopcontrols', ],
                autoescape=True,
                auto_reload=config.autoreload)

        self.db = db

        self.fetcher = Fetcher()
        
        with open(version_path, "r", encoding='utf-8') as f:
            version_data = json.load(f)

        self.jinja_env.globals.update({
            'config': config,
            'format_date': utils.format_date,
            'varbinary2ip': utils.varbinary2ip,
            'version': version_data['version']
            })
        self.jinja_env.filters.update(ui_methods)
