#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""离线轮换 AES_KEY（支持 sqlite 与 MySQL）。

AES_KEY 直接加密 user.userkey，以及所有经 db.user.encrypt/decrypt 传入假值 id
（0 / NULL）的数据，后者落在 tpl.har / tpl.tpl / task.init_env / task.env /
task.session。其余数据用 user.userkey 加密，userkey 的明文在轮换前后不变，
因此不需要重新加密。直接改环境变量会让存量数据无法解密，必须先执行本脚本。

必须从仓库根目录执行：脚本要 import libs / config，而它们只在仓库根目录下可导入。
用 `python -m tools.rotate_aes_key` 而不是 `python tools/rotate_aes_key.py`：
后者会把 sys.path[0] 设成 tools/，import libs 直接失败。

    # 使用当前配置（DB_TYPE / JAWSDB_MARIA_URL，或默认 sqlite 路径）
    python -m tools.rotate_aes_key --old binux --new <新密钥>            # 试运行
    python -m tools.rotate_aes_key --old binux --new <新密钥> --apply    # 落库
    AES_KEY=<新密钥> python run.py

    # 也可以显式指定目标
    python -m tools.rotate_aes_key --old binux --new <新密钥> --url mysql+aiomysql://user:pass@host:3306/db
    python -m tools.rotate_aes_key --old binux --new <新密钥> --db /usr/src/app/config/database.db

脚本先用旧密钥解密、再用新密钥加密并回读校验，任何一行失败都会中止且不提交。
sqlite 落库前会在同目录留一份 <库名>.aes-<时间戳>.bak；MySQL 不做备份，请自行 mysqldump。
"""

import argparse
import asyncio
import hashlib
import os
import shutil
import sys
import time

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from libs import mcrypto

# db.user.encrypt/decrypt 里是 `if id:`，0 / NULL 都算假值并改用 config.aes_key。
# 因此公共数据的判定必须与之一致：NULL 和 0 都要覆盖。只用 IS NULL 会漏掉
# userid=0 的行，而 task.userid 是 NOT NULL，只用 IS NULL 会让整张 task 表都匹配不到。
PUBLIC_COLUMNS = {
    'tpl': ('har', 'tpl'),
    'task': ('init_env', 'env', 'session'),
}
PUBLIC_WHERE = 'userid IS NULL OR userid = 0'


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
        try:
            userkey = mcrypto.aes_decrypt(blob, old_key)
        except Exception as exc:
            raise RuntimeError(
                f'user.id={userid} userkey 无法用 --old 解密, '
                '--old 可能不是当前生效的 AES_KEY 明文值, 已中止'
            ) from exc
        # userkey 是 PBKDF2 的 32 字节摘要。解密结果不是它，说明 --old 不对；
        # 乱码恰好能被 umsgpack 解成一个合法值时若不拦住，会把垃圾重新加密写回。
        if not isinstance(userkey, bytes) or len(userkey) != 32:
            raise RuntimeError(
                f'user.id={userid} userkey 解密结果不是 32 字节, '
                '--old 可能不是当前生效的 AES_KEY 明文值, 已中止'
            )
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


async def _rotate_public(conn, quote, table_name, old_key, new_key, apply, report, stats):
    available = await _columns(conn, table_name)
    targets = [column for column in PUBLIC_COLUMNS.get(table_name, ()) if column in available]
    if not targets:
        return 0
    table = quote(table_name)
    select = ', '.join(quote(column) for column in targets)
    rows = (await conn.execute(
        text(f'SELECT id, {select} FROM {table} WHERE {PUBLIC_WHERE}')
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
                # 明文列或非本框架加密的数据可以跳过，但必须计入报告；
                # 若 --old 填错导致整批都解不开，事务里会据此中止。
                stats['skipped'] += 1
                report.append(f'  ! {table_name}.id={rowid}.{column} 旧密钥无法解密, 跳过')
                continue
            # 乱码偶尔能被 umsgpack 解成一个标量；这些列存的是 HAR / 模板文本 /
            # 变量字典 / cookie 列表，业务数据只会是 dict / list / str。
            # 标量一律按解密失败处理，避免把垃圾重新加密写回。
            if plain is None or isinstance(plain, (bool, int, float)):
                stats['skipped'] += 1
                report.append(f'  ! {table_name}.id={rowid}.{column} 解密结果异常, 跳过')
                continue
            rotated = mcrypto.aes_encrypt(plain, new_key)
            if mcrypto.aes_decrypt(rotated, new_key) != plain:
                raise RuntimeError(f'{table_name}.id={rowid}.{column} 回读校验失败, 已中止')
            updates[column] = rotated
            stats['rotated'] += 1
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
    if args.apply:
        # 库路径要从 URL 里解出来，不能用字符串 rsplit：sqlite+aiosqlite:////abs/path
        # 这种绝对路径形式下 rsplit('///') 会把开头的 '/' 切掉，解出来的是相对路径，
        # os.path.exists 判否 → 备份被静默跳过。make_url 解析出的 database 保留原样。
        parsed = make_url(str(url))
        if parsed.get_backend_name() == 'sqlite':
            path = parsed.database
            if path and os.path.exists(path):
                backup = f'{path}.aes-{time.strftime("%Y%m%d%H%M%S")}.bak'
                shutil.copy2(path, backup)

    engine = create_async_engine(url)
    report = []
    stats = {'rotated': 0, 'skipped': 0}
    try:
        async with engine.connect() as conn:
            quote = conn.dialect.identifier_preparer.quote
            trans = await conn.begin()
            try:
                users = await _rotate_user(conn, quote, old_key, new_key, args.apply, report)
                publics = 0
                for table_name in PUBLIC_COLUMNS:
                    publics += await _rotate_public(
                        conn, quote, table_name, old_key, new_key, args.apply, report, stats
                    )
                if stats['skipped'] and not stats['rotated']:
                    raise RuntimeError(
                        '所有候选公共列都无法用 --old 解密, '
                        '--old 可能不是当前生效的 AES_KEY 明文值, 已中止'
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
    print(f'用户 {users} 条, 公共数据 {publics} 条, '
          f'重新加密 {stats["rotated"]} 列, 跳过 {stats["skipped"]} 列')
    if stats['skipped']:
        print('警告: 有列未能用旧密钥解密且被跳过, 请确认 --old 与这些数据的来源')
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
