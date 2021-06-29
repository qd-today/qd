#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-18 12:17:21

import sys
import json
import logging
import functools
from tornado.ioloop import IOLoop
from libs.fetcher import Fetcher

def usage():
    print("{} tpl.har [--key=value] [env.json]".format(sys.argv[0]))
    sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        usage()

    # load tpl
    tpl_file = sys.argv[1]
    try:
        tpl = json.load(open(tpl_file,encoding='utf-8'))
    except Exception as e:
        logging.error(e)
        usage()

    # load env
    variables = {}
    env = {}
    env_file = None
    for each in sys.argv[2:]:
        if each.startswith('--'):
            key, value = each.split('=', 1)
            key = key.lstrip('--')
            variables[key] = value
        else:
            env_file = each
    if env_file:
        try:
            env = json.load(open(env_file,encoding='utf-8'))
        except Exception as e:
            logging.error(e)
            usage()
    if 'variables' not in env or not isinstance(env['variables'], dict)\
            or 'session' not in env:
        env = {
                'variables': env,
                'session': [],
                }
    env['variables'].update(variables)

    # do fetch
    ioloop = IOLoop.instance()
    def ioloop_stop(x):
        ioloop.stop()

    fetcher = Fetcher()
    result = fetcher.do_fetch(tpl, env)
    ioloop.add_future(result, ioloop_stop)
    ioloop.start()

    try:
        result = result.result()
    except Exception as e:
        print('qiandao failed!', e)
    else:
        print('qiandao success!', result.get('variables', {}).get('__log__', ''))
