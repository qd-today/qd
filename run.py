#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>
from libs.log import Log
import tornado.log

import sys
import platform
import config

from db import sqlite3_db_task_converter
import requests

requests.packages.urllib3.disable_warnings()

if __name__ == "__main__":
    if sys.getdefaultencoding() != 'utf-8':
        import importlib
        importlib.reload(sys)
    # init logging
    logger = Log().getlogger()
    logger_Qiandao = Log('qiandao.run').getlogger()

    if config.debug:
        import logging
        channel = logging.StreamHandler(sys.stderr)
        channel.setFormatter(tornado.log.LogFormatter())
        channel.setLevel(logging.WARNING)
        logger_Qiandao.addHandler(channel)

    if not config.accesslog:
        tornado.log.access_log.disabled = True
    else:
        tornado.log.access_log = Log('tornado.access').getlogger()
        # tornado.log.app_log = Log('tornado.application').getlogger()

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
        from web.app import Application
        converter = sqlite3_db_task_converter.DBconverter()
        converter.ConvertNewType(DB()) 
        converter.db.close()

        from tornado.httpserver import HTTPServer
        http_server = HTTPServer(Application(database), xheaders=True)
        http_server.bind(port, config.bind)
        if config.multiprocess:
            http_server.start(num_processes=0)
        else:
            http_server.start()

        from worker import MainWorker
        from tornado.ioloop import IOLoop, PeriodicCallback
        worker = MainWorker(database)
        PeriodicCallback(worker, config.check_task_loop).start()
        worker()

        logger_Qiandao.info("Http Server started on %s:%s", config.bind, port)
        IOLoop.instance().start()
    except KeyboardInterrupt :
        logger_Qiandao.info("Http Server is being manually interrupted... ")
        database.close()
        logger_Qiandao.info("Http Server is ended. ")

