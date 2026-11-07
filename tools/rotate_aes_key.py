#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""离线轮换 AES_KEY（支持 sqlite 与 MySQL）。

AES_KEY 加密的是数据库里的 user.userkey，以及 userid 为空的公共模板数据；
直接改环境变量会让存量数据无法解密，因此必须先执行本脚本。

    # 使用当前配置（DB_TYPE / JAWSDB_MARIA_URL，或默认 sqlite 路径）
    python tools/rotate_aes_key.py --old binux --new <新密钥>            # 试运行
    python tools/rotate_aes_key.py --old binux --new <新密钥> --apply    # 落库
    AES_KEY=<新密钥> python run.py

    # 也可以显式指定目标
    python tools/rotate_aes_key.py --old binux --new <新密钥> --url mysql+aiomysql://user:pass@host:3306/db
    python tools/rotate_aes_key.py --old binux --new <新密钥> --db /usr/src/app/config/database.db

脚本先用旧密钥解密、再用新密钥加密并回读校验，任何一行失败都会中止且不提交。
"""

import argparse
import asyncio
import hashlib
import os
import shutil
import sys
import time

from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine

from libs import mcrypto

# userid 为空的公共模板数据直接用 AES_KEY 加密，其余数据用 user.userkey
PUBLIC_COLUMNS = {
    'tpl': ('har', 'tpl'),
    'task': ('init_env', 'env'),
}


def _key(raw):
    return hashlib.sha256(raw.encode('utf-8')).digest()


def _build_url(args):
    if args.url:
        return args.url
    if args.db:
        return f'sqlite+aiosqlite:///{args.db}'
    import config  # pylint: disable=import-outside-toplevel
    if config.db_type == 'mysql':
        mysql = config.mysql
        return URL.create(
            'mysql+aiomysql',
            username=mysql.user,
            password=mysql.passwd,
            host=mysql.host,
            port=int(mysql.port or 3306),
            database=mysql.database,
            query={'auth_plugin': mysql.auth_plugin},
        )
    return f'sqlite+aiosqlite:///{config.sqlite3.path}'


async def _columns(conn, table):
    if conn.dialect.name == 'mysql':
        result = await conn.execute(text(
            'SELECT COLUMN_NAME FROM information_schema.COLUMNS '
            'WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table'
        ), {'table': table})
        return [row[0] for row in result.fetchall()]
    result = await conn.execute(text(f'PRAGMA table_info({table})'))
    return [row[1] for row in result.fetchall()]


async def _rotate_user(conn, quote, old_key, new_key, apply, report):
    table = quote('user')
    rows = (await conn.execute(text(f'SELECT id, userkey FROM {table}'))).fetchall()
    for userid, blob in rows:
        if not blob:
            continue
        userkey = mcrypto.aes_decrypt(blob, old_key)
        rotated = mcrypto.aes_encrypt(userkey, new_key)
        if mcrypto.aes_decrypt(rotated, new_key) != userkey:
            raise RuntimeError(f'user.id={userid} 回读校验失败, 已中止')
        report.append(f'user.id={userid} userkey 重新加密')
        if apply:
            await conn.execute(
                text(f'UPDATE {table} SET userkey=:value WHERE id=:id'),
                {'value': rotated, 'id': userid},
            )
    return len(rows)


async def _rotate_public(conn, quote, table_name, old_key, new_key, apply, report):
    available = await _columns(conn, table_name)
    targets = [column for column in PUBLIC_COLUMNS.get(table_name, ()) if column in available]
    if not targets:
        return 0
    table = quote(table_name)
    select = ', '.join(quote(column) for column in targets)
    rows = (await conn.execute(
        text(f'SELECT id, {select} FROM {table} WHERE userid IS NULL')
    )).fetchall()
    for row in rows:
        rowid, values = row[0], row[1:]
        updates = {}
        for column, value in zip(targets, values):
            if value is None:
                continue
            if isinstance(value, str):
                value = value.encode('utf-8')
            try:
                plain = mcrypto.aes_decrypt(value, old_key)
            except Exception:
                continue  # 明文列或非本框架加密的数据, 跳过
            rotated = mcrypto.aes_encrypt(plain, new_key)
            if mcrypto.aes_decrypt(rotated, new_key) != plain:
                raise RuntimeError(f'{table_name}.id={rowid}.{column} 回读校验失败, 已中止')
            updates[column] = rotated
        if updates:
            report.append(f'{table_name}.id={rowid} 公共数据重新加密: {", ".join(updates)}')
            if apply:
                assignments = ', '.join(f'{quote(column)}=:{column}' for column in updates)
                await conn.execute(
                    text(f'UPDATE {table} SET {assignments} WHERE id=:id'),
                    {**updates, 'id': rowid},
                )
    return len(rows)


async def _run(args):
    url = _build_url(args)
    old_key, new_key = _key(args.old), _key(args.new)
    backup = None
    if args.apply and str(url).startswith('sqlite'):
        path = str(url).rsplit('///', 1)[-1]
        if os.path.exists(path):
            backup = f'{path}.aes-{time.strftime("%Y%m%d%H%M%S")}.bak'
            shutil.copy2(path, backup)

    engine = create_async_engine(url)
    report = []
    try:
        async with engine.connect() as conn:
            quote = conn.dialect.identifier_preparer.quote
            trans = await conn.begin()
            try:
                users = await _rotate_user(conn, quote, old_key, new_key, args.apply, report)
                publics = 0
                for table_name in PUBLIC_COLUMNS:
                    publics += await _rotate_public(
                        conn, quote, table_name, old_key, new_key, args.apply, report
                    )
                if args.apply:
                    await trans.commit()
                else:
                    await trans.rollback()
            except Exception:
                await trans.rollback()
                raise
    finally:
        await engine.dispose()

    if args.apply:
        print('已提交' + (f', 备份: {backup}' if backup else '（MySQL 请自行保留 mysqldump 备份）'))
    else:
        print('试运行完成 (未写入), 加 --apply 落库')
    for line in report:
        print('  ' + line)
    print(f'用户 {users} 条, 公共数据 {publics} 条')
    print('请将 AES_KEY 设置为新值后启动, 旧密钥仅需保留在备份中')


def main():
    parser = argparse.ArgumentParser(description='QD AES_KEY 离线轮换')
    parser.add_argument('--old', required=True, help='当前 AES_KEY 明文值')
    parser.add_argument('--new', required=True, help='目标 AES_KEY 明文值')
    parser.add_argument('--db', help='sqlite 数据库路径')
    parser.add_argument('--url', help='显式指定 SQLAlchemy 异步 URL')
    parser.add_argument('--apply', action='store_true', help='实际写入, 默认仅试运行')
    args = parser.parse_args()

    if args.old == args.new:
        sys.exit('新旧密钥相同, 无需轮换')
    asyncio.run(_run(args))


if __name__ == '__main__':
    main()
