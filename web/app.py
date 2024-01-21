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
from db import DB
from libs import utils
from libs.fetcher import Fetcher
from libs.log import Log
from web.handlers import handlers, ui_methods, ui_modules

logger_web = Log('QD.Web').getlogger()


class Application(tornado.web.Application):
    def __init__(self, db: DB, default_version=None):
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "tpl"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            static_url_prefix=config.static_url_prefix,
            debug=config.debug,
            gzip=config.gzip,
            autoreload=config.autoreload,

            cookie_secret=config.cookie_secret,
            login_url='/login',
            websocket_ping_interval=config.websocket.ping_interval,
            websocket_ping_timeout=config.websocket.ping_timeout,
            websocket_max_message_size=config.websocket.max_message_size,
        )

        super(Application, self).__init__(handlers, **settings)

        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(settings['template_path']),
            extensions=['jinja2.ext.loopcontrols', ],
            autoescape=True,
            auto_reload=config.autoreload)

        self.db = db
        self.version = default_version or 'Debug'

        self.fetcher = Fetcher()

        self.jinja_env.globals.update({
            'config': config,
            'format_date': utils.format_date,
            'varbinary2ip': utils.varbinary2ip,
            'version': self.version,
        })
        self.jinja_env.filters.update(ui_methods)
