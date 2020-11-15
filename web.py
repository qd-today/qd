#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-07-30 12:38:34

import sys
import os.path
import logging
import tornado.log
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer

import config
from web.app import Application

if __name__ == "__main__":
    # init logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
    channel = logging.StreamHandler(sys.stdout)
    channel.setFormatter(tornado.log.LogFormatter())
    logger.addHandler(channel)

    if not config.debug:
        channel = logging.StreamHandler(sys.stderr)
        channel.setFormatter(tornado.log.LogFormatter())
        channel.setLevel(logging.WARNING)
        logger.addHandler(channel)

    if len(sys.argv) > 2 and sys.argv[1] == '-p' and sys.argv[2].isdigit():
        port = int(sys.argv[2])
    else:
        port = config.port

    http_server = HTTPServer(Application(), xheaders=True)
    http_server.bind(port, config.bind)
    http_server.start()

    https_enable = False
    if os.path.exists(config.certfile) & os.path.exists(config.keyfile):
        https_enable = True
        https_server = HTTPServer(Application(), ssl_options={
            "certfile": os.path.abspath(config.certfile),
            "keyfile": os.path.abspath(config.keyfile),
        }, xheaders=True)
        https_server.bind(config.https_port, config.bind)
        https_server.start()

    logging.info("http server started on %s:%s", config.bind, port)
    if https_enable:
        logging.info("https server started on %s:%s", config.bind, config.https_port)

    IOLoop.instance().start()
