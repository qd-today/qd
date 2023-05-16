# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>
import asyncio
import json
import os
import platform
import sys

import tornado.log

import config
from db import db_converter
from libs.log import Log

if __name__ == "__main__":
    if sys.getdefaultencoding() != 'utf-8':
        import importlib
        importlib.reload(sys)
    # init logging
    logger = Log().getlogger()
    logger_QD = Log('QD.Run').getlogger()

    if config.debug:
        import logging
        channel = logging.StreamHandler(sys.stderr)
        channel.setFormatter(tornado.log.LogFormatter())
        channel.setLevel(logging.WARNING)
        logger_QD.addHandler(channel)

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

    try:
        from db import DB
        from db.basedb import engine
        database = DB()
        converter = db_converter.DBconverter()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        run = asyncio.ensure_future(converter.ConvertNewType(database) , loop=loop)
        loop.run_until_complete(run)

        from tornado.httpserver import HTTPServer

        from web.app import Application
        default_version = json.load(open(os.path.join(os.path.dirname(__file__), 'version.json'),'r', encoding='utf-8'))['version']
        App= Application(database, default_version)
        http_server = HTTPServer(App, xheaders=True)
        http_server.bind(port, config.bind)
        if config.multiprocess:
            http_server.start(num_processes=0)
        else:
            http_server.start()

        from tornado.ioloop import IOLoop, PeriodicCallback

        from worker import BatchWorker, QueueWorker
        io_loop = IOLoop.instance()
        try:
            if config.worker_method.upper() == 'QUEUE':
                worker = QueueWorker(database)
                io_loop.add_callback(worker)
            elif config.worker_method.upper() == 'BATCH':
                worker = BatchWorker(database)
                PeriodicCallback(worker, config.check_task_loop).start()
            else:
                raise Exception('worker_method must be Queue or Batch, please check config!')
        except Exception as e:
            logger.exception('worker start error!')
            raise KeyboardInterrupt()

        logger_QD.info("Http Server started on %s:%s", config.bind, port)
        io_loop.start()
    except KeyboardInterrupt :
        logger_QD.info("Http Server is being manually interrupted... ")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        run = asyncio.ensure_future(engine.dispose() , loop=loop)
        loop.run_until_complete(run)
        logger_QD.info("Http Server is ended. ")

