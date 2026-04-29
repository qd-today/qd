# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Binux <roy@binux.me>

import asyncio
import json
import logging
import os
import platform
import sys

import tornado.log
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop, PeriodicCallback

import config
from db import DB, db_converter
from db.basedb import engine
from libs.log import Log
from web.app import Application
from worker import BatchWorker, QueueWorker

if sys.getdefaultencoding() != 'utf-8':
    import importlib
    importlib.reload(sys)


def _check_default_secrets(logger):
    """启动时检查关键密钥是否仍为默认值，是则醒目告警。

    生产部署（特别是 Docker 镜像）极易忘记覆盖默认 Cookie/AES 密钥，
    本检查不会阻止启动，但会输出 WARNING 提示用户。
    """
    import hashlib
    default_secret = hashlib.sha256(b'binux').digest()
    if config.cookie_secret == default_secret:
        logger.warning(
            "[安全] COOKIE_SECRET 未设置, 当前为默认值 'binux'。"
            "强烈建议通过环境变量覆盖, 例如: -e COOKIE_SECRET=$(openssl rand -hex 32)"
        )
    if config.aes_key == default_secret:
        logger.warning(
            "[安全] AES_KEY 未设置, 当前为默认值 'binux'。"
            "已存储的加密数据可被任何人解密, 建议生产环境覆盖该变量。"
        )
    if not config.domain:
        logger.warning(
            "[配置] DOMAIN 未设置, 邮件链接、推送链接将无法生成正确域名。"
        )


def start_server():
    # init logging
    logger = Log().getlogger()
    logger_qd = Log('QD.Run').getlogger()

    if config.debug:
        channel = logging.StreamHandler(sys.stderr)
        channel.setFormatter(tornado.log.LogFormatter())
        channel.setLevel(logging.WARNING)
        logger_qd.addHandler(channel)

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

    _check_default_secrets(logger_qd)

    try:
        database = DB()
        converter = db_converter.DBconverter(database)
        asyncio.run(converter.convert_new_type(database))

        with open(os.path.join(os.path.dirname(__file__), 'version.json'), 'r', encoding='utf-8') as _f:
            default_version = json.load(_f)['version']
        app = Application(database, default_version)
        http_server = HTTPServer(app, xheaders=True)
        http_server.bind(port, config.bind)
        if config.multiprocess:
            http_server.start(num_processes=0)
        else:
            http_server.start()

        io_loop = IOLoop.instance()
        try:
            if config.worker_method.upper() == 'QUEUE':
                worker = QueueWorker(database)
                io_loop.add_callback(worker)
            elif config.worker_method.upper() == 'BATCH':
                worker = BatchWorker(database)
                PeriodicCallback(worker, config.check_task_loop).start()
            else:
                raise RuntimeError('worker_method must be Queue or Batch, please check config!')
        except Exception as e:
            logger.exception('worker start error: %s', e)
            raise KeyboardInterrupt() from e

        logger_qd.info("Http Server started on %s:%s", config.bind, port)
        io_loop.start()
    except KeyboardInterrupt :
        logger_qd.info("Http Server is being manually interrupted... ")
        asyncio.run(engine.dispose())
        logger_qd.info("Http Server is ended. ")


if __name__ == "__main__":
    start_server()
