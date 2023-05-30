#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<17175297.hk@gmail.com>
#         http://binux.me
# Created on 2012-12-15 16:16:38

from typing import Optional

import jinja2
import tornado.web
import tornado.websocket
import umsgpack
from tornado.web import HTTPError

import config
from db import DB
from libs import fetcher, utils
from libs.log import Log

logger_Web_Handler = Log('QD.Web.Handler').getlogger()

__ALL__ = ['HTTPError', 'BaseHandler', 'BaseWebSocket', 'BaseUIModule', 'logger_Web_Handler', ]

class _BaseHandler(tornado.web.RequestHandler):
    application_export: set[str] = set(('db', ))
    db:DB
    def __getattr__(self, key):
        if key in self.application_export:
            return getattr(self.application, key)
        raise AttributeError('no such attr: %s' % key)

    def render_string(self, template_name, **kwargs):
        try:
            template = self.application.jinja_env.get_template(template_name)
        except jinja2.TemplateNotFound as e:
            raise e

        namespace = dict(
                static_url=self.static_url,
                xsrf_token=self.xsrf_token,

                handler=self,
                request=self.request,
                current_user=self.current_user,
                locale=self.locale,
                xsrf_form_html=self.xsrf_form_html,
                reverse_url=self.reverse_url
            )
        namespace.update(kwargs)

        return template.render(namespace)

    def evil(self, incr=1):
        user = self.current_user
        userid = None
        if user:
            userid = user['id']
        self.db.redis.evil(self.ip, userid, incr)

    @property
    def ip(self):
        return self.request.remote_ip

    @property
    def ip2varbinary(self):
        return utils.ip2varbinary(self.request.remote_ip,utils.isIP(self.request.remote_ip))

    def get_current_user(self):
        ret = self.get_secure_cookie('user', max_age_days=config.cookie_days)
        if not ret:
            return ret
        user = umsgpack.unpackb(ret)
        try:
            user['isadmin'] = 'admin' in user['role'] if user['role'] else False
        except:
            return None
        return user

    def permission(self, obj, mode='r'):
        user = self.current_user
        if not obj:
            return False
        if 'userid' not in obj:
            return False
        if not obj['userid']:
            if mode == 'r':
                return True
            if user and user['isadmin']:
                return True
        if user and obj['userid'] == user['id']:
            return True
        return False

class BaseHandler(_BaseHandler):
    application_export = set(('db', 'fetcher'))
    fetcher: fetcher.Fetcher

    def prepare(self):
        if config.debug:
            return
        user = self.current_user
        userid = None
        if user:
            userid = user['id']
        if self.db.redis.is_evil(self.ip, userid):
            raise HTTPError(403)

    def check_permission(self, obj, mode='r'):
        if not obj:
            self.evil(+1)
            raise HTTPError(404)
        if not self.permission(obj, mode):
            self.evil(+5)
            raise HTTPError(401)
        return obj

class BaseWebSocketHandler(_BaseHandler,tornado.websocket.WebSocketHandler):
    def prepare(self):
        if config.debug:
            return
        user = self.current_user
        userid = None
        if user:
            userid = user['id']
        if self.db.redis.is_evil(self.ip, userid):
            self.set_status(403)
            self.finish('Forbidden: iP or userid arrived at the limit of evil')

    def check_permission(self, obj, mode='r'):
        if not obj:
            self.evil(+1)
            self.set_status(404)
            self.finish('Not Found')
            raise HTTPError(404)
        if not self.permission(obj, mode):
            self.evil(+5)
            self.set_status(401)
            self.finish('Unauthorized')
            raise HTTPError(401)
        return obj

    def get_compression_options(self):
        return {}

    @property
    def ping_interval(self) -> float | None:
        return config.websocket.ping_interval

    @property
    def ping_timeout(self) -> float | None:
        return config.websocket.ping_timeout

    @property
    def max_message_size(self) -> int | None:
        return config.websocket.max_message_size


class BaseUIModule(tornado.web.UIModule):
    pass
