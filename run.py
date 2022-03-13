#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>

import sys
import platform
import logging
import tornado.log
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.httpserver import HTTPServer

import config
from web.app import Application
from worker import MainWorker

from db import sqlite3_db_task_converter
import requests

requests.packages.urllib3.disable_warnings()

if __name__ == "__main__":
    if sys.getdefaultencoding() != 'utf-8':
        import importlib
        importlib.reload(sys)
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

    if not config.accesslog:
        logging.getLogger('tornado.access').disabled = True

    if len(sys.argv) > 2 and sys.argv[1] == '-p' and sys.argv[2].isdigit():
        port = int(sys.argv[2])
    else:
        port = config.port

    if platform.system() == 'Windows':
        config.multiprocess = False
    if config.multiprocess and config.autoreload:
        config.autoreload = False

    if config.db_type == 'sqlite3':
        import sqlite3_db as db
    else:
        import db

    class DB(object):
        def __init__(self) -> None:
            self.user = db.UserDB()
            self.tpl = db.TPLDB()
            self.task = db.TaskDB()
            self.tasklog = db.TaskLogDB()
            self.push_request = db.PRDB()
            self.redis = db.RedisDB()
            self.site = db.SiteDB()
            self.pubtpl = db.PubTplDB()
        def close(self):
            self.user.close()
            self.tpl.close()
            self.task.close()
            self.tasklog.close()
            self.push_request.close()
            self.redis.close()
            self.site.close()
            self.pubtpl.close()
        
    database = DB()

    try:
        converter = sqlite3_db_task_converter.DBconverter()
        converter.ConvertNewType(database) 

        http_server = HTTPServer(Application(database), xheaders=True)
        http_server.bind(port, config.bind)
        if config.multiprocess:
            http_server.start(num_processes=0)
        else:
            http_server.start()

        worker = MainWorker(database)
        PeriodicCallback(worker, config.check_task_loop).start()
        worker()

        logging.info("Http Server started on %s:%s", config.bind, port)
        IOLoop.instance().start()
    except KeyboardInterrupt :
        logging.info("Http Server is being manually interrupted... ")
        database.close()
        logging.info("Http Server is ended. ")

