#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-18 12:17:21

import asyncio
import json
import socket
import sys

import config
from libs.fetcher import Fetcher
from libs.log import Log
from run import start_server

config.display_import_warning = False

logger_qd = Log("QD").getlogger()

# 判断 端口 是否被占用


def check_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect(("127.0.0.1", port))
        s.shutdown(2)
        logger_qd.debug("Port %s is used", port)
        return False
    except Exception:
        logger_qd.debug("Port %s is available", port)
        return True


def usage():
    print(f"{sys.argv[0]} tpl.har [--key=value] [env.json]")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage()

    # load tpl
    tpl_file = sys.argv[1]
    try:
        # deepcode ignore PT: tpl_file is a file
        tpl = json.load(open(tpl_file, encoding="utf-8"))
    except Exception as e:
        logger_qd.error(e, exc_info=config.traceback_print)
        usage()

    # load env
    variables = {}
    env = {}
    ENV_FILE = None
    for each in sys.argv[2:]:
        if each.startswith("--"):
            key, value = each.split("=", 1)
            key = key.lstrip("--")
            variables[key] = value
        else:
            ENV_FILE = each
    if ENV_FILE:
        try:
            # deepcode ignore PT: env_file is a file
            env = json.load(open(ENV_FILE, encoding="utf-8"))
        except Exception as e:
            logger_qd.error(e, exc_info=config.traceback_print)
            usage()
    if (
        "variables" not in env
        or not isinstance(env["variables"], dict)
        or "session" not in env
    ):
        env = {
            "variables": env,
            "session": [],
        }
    env["variables"].update(variables)

    MANUAL_START = check_port(config.port)
    if MANUAL_START:
        logger_qd.info("QD service is not running on port %s", config.port)
        logger_qd.info("QD service will be started on port %s", config.port)
        # 创建新进程, 以执行 run 中的 main 异步函数
        import multiprocessing

        p = multiprocessing.Process(target=start_server)
        p.start()
        # 循环检测端口是否被占用, 如果被占用, 则继续下一步
        while True:
            if not check_port(config.port):
                break
            else:
                import time

                time.sleep(1)
    else:
        logger_qd.info("QD service is running on port %s", config.port)

    # do fetch
    ioloop = asyncio.new_event_loop()
    asyncio.set_event_loop(ioloop)
    result: asyncio.Task = asyncio.ensure_future(
        Fetcher().do_fetch(tpl, env), loop=ioloop
    )
    logger_qd.info("QD start to do fetch: %s", tpl_file)
    ioloop.run_until_complete(result)
    ioloop.stop()

    try:
        env, _ = result.result()
    except Exception as e:
        logger_qd.error("QD failed: %s", e, exc_info=config.traceback_print)
    else:
        logger_qd.info(
            "QD success! Results:\n %s",
            env.get("variables", {}).get("__log__", "").replace("\\r\\n", "\r\n"),
        )

    if MANUAL_START:
        p.terminate()
        p.join()
        logger_qd.info("QD service is ended. ")
