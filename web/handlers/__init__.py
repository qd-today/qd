#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<17175297.hk@gmail.com>
#         http://binux.me
# Created on 2012-12-15 16:15:50

import importlib
import os
import pkgutil

from . import base


def load_modules():
    handlers: list[tuple[str, base.BaseHandler]] = []
    ui_modules: dict[str, base.BaseUIModule] = {}
    ui_methods: dict[str, base.BaseWebSocket] = {}

    path = os.path.join(os.path.dirname(__file__), "")
    for finder, name, ispkg in pkgutil.iter_modules([path]):
        module = importlib.import_module("." + name, __name__)
        if hasattr(module, "handlers"):
            handlers.extend(module.handlers)
        if hasattr(module, "ui_modules"):
            ui_modules.update(module.ui_modules)
        if hasattr(module, "ui_methods"):
            ui_methods.update(module.ui_methods)

    return handlers, ui_modules, ui_methods


handlers: list[tuple[str, base.BaseHandler]]
ui_modules: dict[str, base.BaseUIModule]
ui_methods: dict[str, base.BaseWebSocket]

handlers, ui_modules, ui_methods = load_modules()
