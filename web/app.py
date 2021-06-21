#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-07-30 12:22:52

import os
import logging
import jinja2
import tornado.web

import config
from libs import utils
from libs.fetcher import Fetcher
from web.handlers import handlers, ui_modules, ui_methods

class Application(tornado.web.Application):
    def __init__(self):
        settings = dict(
                template_path = os.path.join(os.path.dirname(__file__), "tpl"),
                static_path = os.path.join(os.path.dirname(__file__), "static"),
                debug = config.debug,
                gzip = config.gzip,

                cookie_secret = config.cookie_secret,
                login_url = '/login',
                )
        super(Application, self).__init__(handlers, **settings)

        self.jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(settings['template_path']),
                extensions=['jinja2.ext.autoescape', 'jinja2.ext.loopcontrols', ],
                autoescape=True,
                auto_reload=config.debug)

        if config.db_type == 'sqlite3':
            import sqlite3_db as db
        else:
            import db

        class DB(object):
            user = db.UserDB()
            tpl = db.TPLDB()
            task = db.TaskDB()
            tasklog = db.TaskLogDB()
            push_request = db.PRDB()
            redis = db.RedisDB()
            site = db.SiteDB()
            pubtpl = db.PubTplDB()
        self.db = DB

        self.fetcher = Fetcher()

        self.jinja_env.globals.update({
            'config': config,
            'format_date': utils.format_date,
            })
        self.jinja_env.filters.update(ui_methods)
