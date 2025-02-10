#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 21:06:02
# pylint: disable=broad-exception-raised

import asyncio
import base64
import json
import random
import time
from typing import Dict
from urllib.parse import quote, urlparse

import aiohttp
from tornado.web import addslash, authenticated

import config
from config import domain, proxies
from web.handlers.base import (BaseHandler, BaseWebSocketHandler,
                               logger_web_handler)


class SubscribeHandler(BaseHandler):
    @addslash
    @authenticated
    async def get(self, userid):
        msg = ''
        user = self.current_user
        adminflg = False
        if (user['id'] == int(userid)) and (user['role'] == 'admin'):
            adminflg = True
        repos = json.loads((await self.db.site.get(1, fields=('repos',)))['repos'])
        try:
            # 如果上次更新时间大于1天则更新模板仓库
            if int(time.time()) - int(repos['lastupdate']) > 24 * 3600:
                tpls = await self.db.pubtpl.list()
                await self.render('pubtpl_wait.html', tpls=tpls, user=user, userid=user['id'], adminflg=adminflg, repos=repos['repos'], msg=msg)
                return

            tpls = await self.db.pubtpl.list()
            await self.render('pubtpl_subscribe.html', tpls=tpls, user=user, userid=user['id'], adminflg=adminflg, repos=repos['repos'], msg=msg)

        except Exception as e:
            user = self.current_user
            tpls = await self.db.pubtpl.list()
            await self.render('pubtpl_subscribe.html', tpls=tpls, user=user, userid=user['id'], adminflg=adminflg, repos=repos['repos'], msg=str(e))
            logger_web_handler.error('UserID: %s browse Subscribe failed! Reason: %s', userid, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
            return


class SubscribeUpdatingHandler(BaseWebSocketHandler):
    users: Dict[int, BaseWebSocketHandler] = {}
    updating = False
    updating_start_time = 0

    def check_origin(self, origin: str) -> bool:
        parsed_origin = urlparse(origin)
        origin = parsed_origin.netloc.lower()
        host: str = self.request.headers.get("Host", "")
        logger_web_handler.debug("check_origin: %s, host: %s", origin, host)

        return origin.endswith(domain) or host.lower() == origin

    async def update(self, userid):
        SubscribeUpdatingHandler.updating = True
        SubscribeUpdatingHandler.updating_start_time = int(time.time())
        success = False
        fail_count = 0
        try:
            async with self.db.transaction() as sql_session:
                repos = json.loads((await self.db.site.get(1, fields=('repos',), sql_session=sql_session))['repos'])
                if proxies:
                    proxy = random.choice(proxies)
                    if proxy and proxy.get("href"):
                        proxy = proxy["href"]
                    else:
                        proxy = None
                else:
                    proxy = None
                # 如果上次更新时间大于1天则更新模板仓库
                if int(time.time()) - int(repos['lastupdate']) > 24 * 3600:
                    for repo in repos['repos']:
                        await self.send_global_message({'code': 1000, 'message': f'-----开始更新 {repo["reponame"]} 模板仓库-----'})
                        if repo['repoacc']:
                            if config.subscribe_accelerate_url == 'jsdelivr_cdn':
                                url = f"{repo['repourl'].replace('https://github.com/', 'https://cdn.jsdelivr.net/gh/')}@{repo['repobranch']}"
                            elif config.subscribe_accelerate_url == 'jsdelivr_fastly':
                                url = f"{repo['repourl'].replace('https://github.com/', 'https://fastly.jsdelivr.net/gh/')}@{repo['repobranch']}"
                            elif config.subscribe_accelerate_url == 'ghproxy':
                                url = f"{repo['repourl'].replace('https://github.com/', 'https://ghfast.top/https://raw.githubusercontent.com/')}/{repo['repobranch']}"
                            elif config.subscribe_accelerate_url == 'qd-ph':
                                url = f"{repo['repourl'].replace('https://github.com/', 'https://qd-gh.crossg.us.kg/https://raw.githubusercontent.com/')}/{repo['repobranch']}"
                            else:
                                if config.subscribe_accelerate_url.endswith('/'):
                                    url = f"{repo['repourl'].replace('https://github.com/', config.subscribe_accelerate_url)}/{repo['repobranch']}"
                                else:
                                    url = f"{repo['repourl'].replace('https://github.com', config.subscribe_accelerate_url)}/{repo['repobranch']}"
                        else:
                            if repo['repourl'].find('https://github.com/') > -1:
                                url = f'{repo["repourl"].replace("https://github.com/", "https://raw.githubusercontent.com/")}/{repo["repobranch"]}'
                            else:
                                url = repo['repourl']
                        await self.send_global_message({'code': 1000, 'message': f'仓库地址: {url}'})

                        hfile_link = url + '/tpls_history.json'
                        hfile = {'har': {}}
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.connect_timeout * 10, connect=config.connect_timeout * 5)) as session:
                            await asyncio.sleep(0.001)
                            async with session.get(hfile_link, verify_ssl=False, timeout=config.request_timeout, proxy=proxy) as res:
                                if res.status == 200:
                                    hfile = await res.json(content_type="")
                                    logger_web_handler.info('200 Get repo %s history file success!', repo["reponame"])
                                    await self.send_global_message({'code': 1000, 'message': 'tpls_history.json 文件获取成功'})

                                else:
                                    logger_web_handler.error('Get repo %s history file failed! Reason: %s open error!', repo["reponame"], hfile_link)
                                    await self.send_global_message({'code': 0, 'message': f'tpls_history.json 文件获取失败, 原因: 打开链接 {hfile_link} 出错!'})
                                    await self.send_global_message({'code': 0, 'message': f'HTTP 代码: {res.status}, 错误信息: {res.reason if res.reason else "Unknown"}'})
                                    fail_count += 1
                                    continue
                            for har in hfile['har'].values():
                                for k, v in repo.items():
                                    har[k] = v
                                tpl = await self.db.pubtpl.list(name=har['name'],
                                                                reponame=har['reponame'],
                                                                repourl=har['repourl'],
                                                                repobranch=har['repobranch'],
                                                                fields=('id', 'name', 'version'),
                                                                sql_session=sql_session)

                                if len(tpl) > 0:
                                    if int(tpl[0]['version']) < int(har['version']):
                                        if har['content'] == '':
                                            har_url = f"{url}/{quote(har['filename'])}"
                                            await asyncio.sleep(0.001)
                                            async with session.get(har_url, verify_ssl=False, timeout=config.request_timeout, proxy=proxy) as har_res:
                                                if har_res.status == 200:
                                                    har['content'] = base64.b64encode(await har_res.read()).decode()
                                                else:
                                                    logger_web_handler.error('Update %s public template %s failed! Reason: %s open error!', repo['reponame'], har['name'], har_url)
                                                    await self.send_global_message({'code': 0, 'message': f'模板: {har["name"]} 更新失败, 原因: 打开链接 {har_url} 出错!'})
                                                    await self.send_global_message({'code': 0, 'message': f'HTTP 代码: {har_res.status}, 错误信息: {har_res.reason if har_res.reason else "Unknown"}'})
                                                    fail_count += 1
                                                    continue
                                        har['update'] = True
                                        await self.db.pubtpl.mod(tpl[0]['id'], **har, sql_session=sql_session)
                                        logger_web_handler.info('Update %s public template %s success!', repo['reponame'], har['name'])
                                        await self.send_global_message({'code': 1000, 'message': f'模板: {har["name"]} 更新成功'})
                                else:
                                    if har['content'] == '':
                                        har_url = f"{url}/{quote(har['filename'])}"
                                        await asyncio.sleep(0.001)
                                        async with session.get(har_url, verify_ssl=False, timeout=config.request_timeout, proxy=proxy) as har_res:
                                            if har_res.status == 200:
                                                har['content'] = base64.b64encode(await har_res.read()).decode()
                                            else:
                                                logger_web_handler.error('Add %s public template %s failed! Reason: %s open error!', repo['reponame'], har['name'], har_url)
                                                await self.send_global_message({'code': 0, 'message': f'模板: {har["name"]} 添加失败, 原因: 打开链接 {har_url} 出错!'})
                                                await self.send_global_message({'code': 0, 'message': f'HTTP 代码: {har_res.status}, 错误信息: {har_res.reason if har_res.reason else "Unknown"}'})
                                                fail_count += 1
                                                continue
                                    await self.db.pubtpl.add(har, sql_session=sql_session)
                                    logger_web_handler.info('Add %s public template %s success!', repo['reponame'], har['name'])
                                    await self.send_global_message({'code': 1000, 'message': f'模板: {har["name"]} 添加成功'})
                        await self.send_global_message({'code': 1000, 'message': f'-----更新 {repo["reponame"]} 模板仓库结束-----'})
            success = True
        except Exception as e:
            msg = str(e).replace('\\r\\n', '\r\n')
            if msg == "":
                msg = e.__class__.__name__
            if msg.endswith('\r\n'):
                msg = msg[:-2]
            logger_web_handler.error('UserID: %s update Subscribe failed! Reason: %s', userid, msg, exc_info=config.traceback_print)
            await self.send_global_message({'code': 0, 'message': f'更新失败, 原因: {msg}'})

        try:
            async with self.db.transaction() as sql_session:
                repos = json.loads((await self.db.site.get(1, fields=('repos',), sql_session=sql_session))['repos'])
                repos["lastupdate"] = int(time.time())
                await self.db.site.mod(1, repos=json.dumps(repos, ensure_ascii=False, indent=4), sql_session=sql_session)

            if success:
                if fail_count == 0:
                    await self.close_all(1000, 'Update success, please refresh your browser.')
                else:
                    await self.close_all(4001, f'Update success, but {fail_count} templates update failed.')
            else:
                await self.close_all(4006, 'Update failed, please check failure reason.')
        except Exception as e:
            logger_web_handler.error('UserID: %s update Subscribe or close connection failed! Reason: %s', userid, e, exc_info=config.traceback_print)

        SubscribeUpdatingHandler.updating = False
        SubscribeUpdatingHandler.updating_start_time = 0
        SubscribeUpdatingHandler.users = {}

    def on_message(self, message):
        return

    def on_close(self):
        for userid, ws in list(SubscribeUpdatingHandler.users.items()):
            if ws == self:
                SubscribeUpdatingHandler.users[userid].close(1000, 'client close connection')
                SubscribeUpdatingHandler.users.pop(userid)
                break

    async def send_global_message(self, message):
        task = []
        for userid, ws in list(SubscribeUpdatingHandler.users.items()):
            if ws and ws.ws_connection and not ws.ws_connection.is_closing():
                task.append(ws.write_message(message))
            else:
                SubscribeUpdatingHandler.users.pop(userid)
        await asyncio.gather(*task)

    @addslash
    @authenticated
    async def open(self, userid):  # pylint: disable=arguments-differ,invalid-overridden-method
        user = self.current_user
        # 判断用户是否已经登录
        if not user:
            self.close(4403, 'Forbidden: user not login or cookie expired')
            return

        # 判断是否为当前用户
        if user['id'] != int(userid):
            self.close(4403, 'Forbidden: userid not match with cookie, please check your cookie or login again')
            return

        # 判断用户是否为管理员
        adminflg = False
        if (user['id'] == int(userid)) and (user['role'] == 'admin'):
            adminflg = True

        if not adminflg and len(SubscribeUpdatingHandler.users) >= config.websocket.max_connections_subscribe:
            self.close(4429, 'Too many connections, please wait for a moment')
            return

        # 判断用户是否已经在列表中
        if len(SubscribeUpdatingHandler.users) == 0:
            if SubscribeUpdatingHandler.updating and (int(time.time()) - SubscribeUpdatingHandler.updating_start_time > 60):
                SubscribeUpdatingHandler.updating = False
        elif userid in SubscribeUpdatingHandler.users:
            SubscribeUpdatingHandler.users[userid].close(1001, 'Another client login, close this connection')
            SubscribeUpdatingHandler.users.pop(userid)
        SubscribeUpdatingHandler.users[userid] = self

        # 判断是否已经在更新中
        if SubscribeUpdatingHandler.updating:
            self.write_message({'code': 1000, 'message': '正在更新中...'})
            return
        else:
            self.write_message({'code': 1000, 'message': '开始更新...'})
            try:
                await self.update(userid)
            except Exception as e:
                SubscribeUpdatingHandler.updating = False
                raise e

    async def close_all(self, code, reason):
        for userid, ws in list(SubscribeUpdatingHandler.users.items()):
            if ws and ws.ws_connection and not ws.ws_connection.is_closing():
                ws.close(code, reason)
                SubscribeUpdatingHandler.users.pop(userid)
        SubscribeUpdatingHandler.users = {}


class SubscribeRefreshHandler(BaseHandler):
    @authenticated
    async def get(self, userid):
        await self.post(userid)

    @authenticated
    async def post(self, userid):
        try:
            user = self.current_user
            op = self.get_argument('op', '')
            if op == '':
                raise Exception('op参数为空')

            async with self.db.transaction() as sql_session:
                if (user['id'] == int(userid)) and (user['role'] == 'admin'):
                    repos = json.loads((await self.db.site.get(1, fields=('repos',), sql_session=sql_session))['repos'])
                    repos["lastupdate"] = 0
                    await self.db.site.mod(1, repos=json.dumps(repos, ensure_ascii=False, indent=4), sql_session=sql_session)
                    if op == 'clear':
                        for pubtpl in await self.db.pubtpl.list(fields=('id',), sql_session=sql_session):
                            await self.db.pubtpl.delete(pubtpl['id'], sql_session=sql_session)
                else:
                    raise Exception('没有权限操作')
        except Exception as e:
            logger_web_handler.error('UserID: %s refresh Subscribe failed! Reason: %s', userid, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
            await self.render('utils_run_result.html', log=str(e), title='设置失败', flg='danger')
            return

        self.redirect(f'/subscribe/{int(userid)}/')
        return


class SubscribSignupReposHandler(BaseHandler):
    @authenticated
    async def get(self, userid):
        user = self.current_user
        if (user['id'] == int(userid)) and (user['role'] == 'admin'):
            await self.render('pubtpl_register.html', userid=userid)
        else:
            await self.render('utils_run_result.html', log='非管理员用户，不可设置', title='设置失败', flg='danger')
            logger_web_handler.error('UserID: %s browse Subscrib_signup_repos failed! Reason: 非管理员用户，不可设置', userid)
        return

    @authenticated
    async def post(self, userid):
        try:
            user = self.current_user
            if (user['id'] == int(userid)) and (user['role'] == 'admin'):
                envs = {}
                for key in self.request.body_arguments:
                    envs[key] = self.get_body_arguments(key)
                env = {}
                for k, v in envs.items():
                    if (v[0] == 'false') or (v[0] == 'true'):
                        env[k] = True if v[0] == 'true' else False
                    else:
                        env[k] = v[0]

                if (env['reponame'] != '') and (env['repourl'] != '') and (env['repobranch'] != ''):
                    repos = json.loads((await self.db.site.get(1, fields=('repos',)))['repos'])
                    tmp = repos['repos']
                    inflg = False

                    # 检查是否存在同名仓库
                    for repo in repos['repos']:
                        if repo['reponame'] == env['reponame']:
                            inflg = True
                            break

                    if inflg:
                        raise Exception('已存在同名仓库')
                    else:
                        tmp.append(env)
                        repos['repos'] = tmp
                        repos["lastupdate"] = 0
                        await self.db.site.mod(1, repos=json.dumps(repos, ensure_ascii=False, indent=4))
                else:
                    raise Exception('仓库名/url/分支不能为空')
            else:
                raise Exception('非管理员用户，不可设置')

        except Exception as e:
            logger_web_handler.error('UserID: %s modify Subscribe_signup_repos failed! Reason: %s', userid, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
            await self.render('utils_run_result.html', log=str(e), title='设置失败', flg='danger')
            return

        await self.render('utils_run_result.html', log='设置成功，请关闭操作对话框或刷新页面查看', title='设置成功', flg='success')
        return


class GetReposInfoHandler(BaseHandler):
    @authenticated
    async def post(self, userid):
        try:
            user = self.current_user
            if (user['id'] == int(userid)) and (user['role'] == 'admin'):
                envs = {}
                for key in self.request.body_arguments:
                    envs[key] = self.get_body_arguments(key)
                tmp = json.loads((await self.db.site.get(1, fields=('repos',)))['repos'])['repos']
                repos = []
                for repoid, selected in envs.items():
                    if isinstance(selected[0], bytes):
                        selected[0] = selected[0].decode()
                    if selected[0] == 'true':
                        repos.append(tmp[int(repoid)])
            else:
                raise Exception('非管理员用户，不可查看')
        except Exception as e:
            logger_web_handler.error('UserID: %s get Subscribe_Repos_Info failed! Reason: %s', userid, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
            await self.render('utils_run_result.html', log=str(e), title='获取信息失败', flg='danger')
            return

        await self.render('pubtpl_reposinfo.html', repos=repos)
        return


class UnsubscribeReposHandler(BaseHandler):
    @authenticated
    async def get(self, userid):
        try:
            user = self.current_user
            if (user['id'] == int(userid)) and (user['role'] == 'admin'):
                await self.render('pubtpl_unsubscribe.html', user=user)
            else:
                raise Exception('非管理员用户，不可设置')
            return
        except Exception as e:
            logger_web_handler.error('UserID: %s browse UnSubscribe_Repos failed! Reason: %s', userid, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
            await self.render('utils_run_result.html', log=str(e), title='打开失败', flg='danger')
            return

    @authenticated
    async def post(self, userid):
        try:
            user = self.current_user
            if (user['id'] == int(userid)) and (user['role'] == 'admin'):
                envs = {}
                for key in self.request.body_arguments:
                    envs[key] = self.get_body_arguments(key)
                env = {}
                for k, v in envs.items():
                    try:
                        env[k] = json.loads(v[0])
                    except Exception as e:
                        logger_web_handler.debug('Deserialize failed! Reason: %s', str(e).replace('\\r\\n', '\r\n'))
                        env[k] = v[0]
                async with self.db.transaction() as sql_session:
                    repos = json.loads((await self.db.site.get(1, fields=('repos',), sql_session=sql_session))['repos'])
                    tmp = repos['repos']
                    result = []
                    for i, j in enumerate(tmp):
                        # 检查是否存在同名仓库
                        if not env['selectedrepos'].get(str(i), False) :
                            result.append(j)
                        else:
                            pubtpls = await self.db.pubtpl.list(reponame=j['reponame'], fields=('id',), sql_session=sql_session)
                            for pubtpl in pubtpls:
                                await self.db.pubtpl.delete(pubtpl['id'], sql_session=sql_session)
                    repos['repos'] = result
                    await self.db.site.mod(1, repos=json.dumps(repos, ensure_ascii=False, indent=4), sql_session=sql_session)
            else:
                raise Exception('非管理员用户，不可设置')

        except Exception as e:
            logger_web_handler.error('UserID: %s unsubscribe Subscribe_Repos failed! Reason: %s', userid, str(e).replace('\\r\\n', '\r\n'), exc_info=config.traceback_print)
            await self.render('utils_run_result.html', log=str(e), title='设置失败', flg='danger')
            return

        await self.render('utils_run_result.html', log='设置成功，请关闭操作对话框或刷新页面查看', title='设置成功', flg='success')
        return


handlers = [
    (r'/subscribe/(\d+)/', SubscribeHandler),
    (r'/subscribe/(\d+)/updating/', SubscribeUpdatingHandler),
    (r'/subscribe/refresh/(\d+)/', SubscribeRefreshHandler),
    (r'/subscribe/signup_repos/(\d+)/', SubscribSignupReposHandler),
    (r'/subscribe/(\d+)/get_reposinfo', GetReposInfoHandler),
    (r'/subscribe/unsubscribe_repos/(\d+)/', UnsubscribeReposHandler),
]
