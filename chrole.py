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
import logging
import sys

import db

logger = logging.getLogger(__name__)


def usage():
    print(f'Usage: python3 {sys.argv[0]} <email> [role]')
    print(f'Example: python3 {sys.argv[0]} admin@qd.today admin')
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
        logger.info("role of %s changed to %s", email, role or '[empty]')
    else:
        logger.warning("role of %s not changed", email)


if __name__ == '__main__':
    if not 2 <= len(sys.argv) <= 3:
        usage()
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        run = asyncio.ensure_future(main(), loop=loop)
        loop.run_until_complete(run)
