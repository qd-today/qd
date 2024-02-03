#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-07-30 12:38:34

import logging
import sys

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.log import LogFormatter as TornadoLogFormatter

import config
from db import DB
from libs.log import Log
from web.app import Application

if __name__ == "__main__":
    # init logging
    logger_web = Log('QD.Web').getlogger()

    if not config.debug:
        channel = logging.StreamHandler(sys.stderr)
        channel.setFormatter(TornadoLogFormatter())
        channel.setLevel(logging.WARNING)
        logger_web.addHandler(channel)

    if len(sys.argv) > 2 and sys.argv[1] == '-p' and sys.argv[2].isdigit():
        port = int(sys.argv[2])
    else:
        port = config.port

    http_server = HTTPServer(Application(DB()), xheaders=True)
    http_server.bind(port, config.bind)
    http_server.start()

    logger_web.info("http server started on %s:%s", config.bind, port)
    IOLoop.instance().start()
