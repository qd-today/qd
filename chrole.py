#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Binux <roy@binux.me>
#
# Distributed under terms of the MIT license.

"""
change the role of user
"""

import sys
import config
if config.db_type == 'sqlite3':
    import sqlite3_db as db
else:
    import db
userdb = db.UserDB()

if not 2 <= len(sys.argv) <= 3:
    print("Usage: {} email [role]".format(sys.argv[0]))
    sys.exit(1)
else:
    email = sys.argv[1]
    role = sys.argv[2] if len(sys.argv) == 3 else ''

    user = userdb.get(email=email, fields=['id'])
    if not user:
        print("Cannot find user: ", email)
        sys.exit(1)
    userdb.mod(user['id'], role=role)
    print("role of {} changed to {}".format(email, role or '[empty]'))
