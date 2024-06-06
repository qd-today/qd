#!/usr/bin/env python
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-18 12:17:21

import asyncio
import json
import sys

from qd_core.client.fetcher import Fetcher
from qd_core.config import get_settings
from qd_core.plugins.manager import QDPluginManager
from qd_core.utils.log import Log

logger_qd = Log("QD").getlogger()


def usage():
    print(f"{sys.argv[0]} tpl.har [--key=value] [env.json]")
    sys.exit(1)


async def main(env):
    _ = QDPluginManager("qd.plugins")
    fetcher = Fetcher()
    env, _ = await fetcher.do_fetch(tpl, env)
    return env


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()

    # load tpl
    tpl_file = sys.argv[1]
    env = {}
    try:
        # deepcode ignore PT: tpl_file is a file
        tpl = json.load(open(tpl_file, encoding="utf-8"))

        # load env
        variables = {}

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
                logger_qd.error(e, exc_info=get_settings().log.traceback_print)
                usage()
        if "variables" not in env or not isinstance(env["variables"], dict) or "session" not in env:
            env = {
                "variables": env,
                "session": [],
            }
        env["variables"].update(variables)

        logger_qd.info("QD start to do fetch: %s", tpl_file)
        env = asyncio.run(main(env))

    except Exception as e:
        logger_qd.error("QD failed: %s", str(e).replace("\\r\\n", "\r\n"), exc_info=get_settings().log.traceback_print)
    else:
        logger_qd.info(
            "QD success! Results:\n %s", env.get("variables", {}).get("__log__", "").replace("\\r\\n", "\r\n")
        )
