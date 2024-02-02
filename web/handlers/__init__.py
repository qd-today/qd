#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<17175297.hk@gmail.com>
#         http://binux.me
# Created on 2012-12-15 16:15:50

import os

handlers = []
ui_modules = {}
ui_methods = {}
modules = []
for file in os.listdir(os.path.dirname(__file__)):
    if not file.endswith(".py"):
        continue
    if file == "__init__.py":
        continue
    modules.append(file[:-3])

for module in modules:
    module_object = __import__(f'{__package__}.{module}', fromlist=["handlers"])
    if hasattr(module_object, "handlers"):
        handlers.extend(module_object.handlers)
    if hasattr(module_object, "ui_modules"):
        ui_modules.update(module_object.ui_modules)
    if hasattr(module_object, "ui_methods"):
        ui_methods.update(module_object.ui_methods)
