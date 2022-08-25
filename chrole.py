# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Binux <roy@binux.me>
#
# Distributed under terms of the MIT license.

"""
change the role of user
"""

import asyncio
import sys
import db

def usage():
    print('Usage: python3 %s <email> [role]' % sys.argv[0])
    print('Example: python3 %s admin@qiandao.today admin' % sys.argv[0])
    sys.exit(1)

async def main():
    email = sys.argv[1]
    role = sys.argv[2] if len(sys.argv) == 3 else ''
    userdb = db.User()

    user = await userdb.get(email=email, fields=['id'])
    if not user:
        print("Cannot find user: ", email)
        sys.exit(1)
    rowcount = await userdb.mod(user['id'], role=role)
    if rowcount >= 1:
        print("role of {} changed to {}".format(email, role or '[empty]'))
    else:
        print("role of {} not changed".format(email))


if __name__ == '__main__':
    if not 2 <= len(sys.argv) <= 3:
        usage()
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        run = asyncio.ensure_future(main(), loop=loop)
        loop.run_until_complete(run)