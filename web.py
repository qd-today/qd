#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-07-30 12:38:34

import sys

from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer

import config
from web.app import Application
from libs.log import Log

if __name__ == "__main__":
    # init logging
    logger_Web = Log("qiandao.Web").getlogger()

    if not config.debug:
        import logging
        import tornado.log
        channel = logging.StreamHandler(sys.stderr)
        channel.setFormatter(tornado.log.LogFormatter())
        channel.setLevel(logging.WARNING)
        logger_Web.addHandler(channel)

    if len(sys.argv) > 2 and sys.argv[1] == '-p' and sys.argv[2].isdigit():
        port = int(sys.argv[2])
    else:
        port = config.port

    http_server = HTTPServer(Application(), xheaders=True)
    http_server.bind(port, config.bind)
    http_server.start()

    logger_Web.info("http server started on %s:%s", config.bind, port)
    IOLoop.instance().start()
