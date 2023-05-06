#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<17175297.hk@gmail.com>
#         http://binux.me
# Created on 2012-12-15 16:16:38

import json
import traceback
import typing

import jinja2
import tornado.web
import tornado.websocket
import umsgpack
from tornado.web import HTTPError

import config
from db import DB
from libs import utils
from libs.log import Log

logger_Web_Handler = Log('qiandao.Web.Handler').getlogger()

__ALL__ = ['HTTPError', 'BaseHandler', 'BaseWebSocket', 'BaseUIModule', 'logger_Web_Handler', ]

class BaseHandler(tornado.web.RequestHandler):
    application_export = set(('db', 'fetcher'))
    db:DB
    # db = DB()
    def __getattr__(self, key):
        if key in self.application_export:
            return getattr(self.application, key)
        raise AttributeError('no such attr: %s' % key)

    def render_string(self, template_name, **kwargs):
        try:
            template = self.application.jinja_env.get_template(template_name)
        except jinja2.TemplateNotFound:
            raise

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

    def prepare(self):
        if config.debug:
            return
        user = self.current_user
        userid = None
        if user:
            userid = user['id']
        if self.db.redis.is_evil(self.ip, userid):
            raise HTTPError(403)

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

    def check_permission(self, obj, mode='r'):
        if not obj:
            self.evil(+1)
            raise HTTPError(404)
        if not self.permission(obj, mode):
            self.evil(+5)
            raise HTTPError(401)
        return obj
    
    def write_error(self, status_code: int, **kwargs: typing.Any) -> None:
        """Override to implement custom error pages.

        ``write_error`` may call `write`, `render`, `set_header`, etc
        to produce output as usual.

        If this error was caused by an uncaught exception (including
        HTTPError), an ``exc_info`` triple will be available as
        ``kwargs["exc_info"]``.  Note that this exception may not be
        the "current" exception for purposes of methods like
        ``sys.exc_info()`` or ``traceback.format_exc``.
        """
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        trace = traceback.format_exception(*kwargs["exc_info"])
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            # self.set_header("Content-Type", "text/plain; charset=UTF-8")
            # for line in traceback.format_exception(*kwargs["exc_info"]):
            #     self.write(line)
            
            data = json.dumps({"code": status_code, "message": self._reason, "data": trace}, ensure_ascii=False, indent=4)
        else:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            data = json.dumps({"code": status_code, "message": self._reason, "data": ""}, ensure_ascii=False, indent=4)
        if config.traceback_print:
            traceback.print_exception(*kwargs["exc_info"])
        if len(kwargs["exc_info"]) > 1:
            logger_Web_Handler.debug(str(kwargs["exc_info"][1]))
        self.write(data)
        self.finish()

class BaseWebSocket(tornado.websocket.WebSocketHandler):
    pass

class BaseUIModule(tornado.web.UIModule):
    pass
