#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 21:06:02

import base64
import json
import random
import time
import traceback
from urllib.parse import quote

import aiohttp

from config import proxies

from .base import *


class SubscribeHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    async def get(self, userid):
        msg = ''
        user = self.current_user
        adminflg = False
        if (user['id'] == int(userid)) and (user['role'] == u'admin'):
            adminflg = True
        repos = json.loads((await self.db.site.get(1, fields=('repos',)))['repos'])
        try:
            if proxies:
                proxy = random.choice(proxies)
            else:
                proxy = {}
            # 如果上次更新时间大于1天则更新模板仓库
            if (int(time.time()) - int(repos['lastupdate']) > 24 * 3600):
                tpls = await self.db.pubtpl.list()
                await self.render('pubtpl_wait.html', tpls=tpls, user=user, userid=user['id'], adminflg=adminflg, repos=repos['repos'], msg=msg)
                return

            tpls = await self.db.pubtpl.list()
            await self.render('pubtpl_subscribe.html', tpls=tpls, user=user, userid=user['id'], adminflg=adminflg, repos=repos['repos'], msg=msg)

        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            user = self.current_user
            tpls = await self.db.pubtpl.list()
            await self.render('pubtpl_subscribe.html', tpls=tpls, user=user, userid=user['id'], adminflg=adminflg, repos=repos['repos'], msg=str(e))
            logger_Web_Handler.error('UserID: %s browse Subscribe failed! Reason: %s', userid, str(e).replace('\\r\\n','\r\n'))
            return

class SubscribeUpdatingHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    async def post(self, userid):
        msg = ''
        user = self.current_user
        adminflg = False
        success = False
        if (user['id'] == int(userid)) and (user['role'] == u'admin'):
            adminflg = True
        try:
            async with self.db.transaction() as sql_session:
                repos = json.loads((await self.db.site.get(1, fields=('repos',), sql_session=sql_session))['repos'])
                if proxies:
                    proxy = random.choice(proxies)
                else:
                    proxy = {}
                # 如果上次更新时间大于1天则更新模板仓库
                if (int(time.time()) - int(repos['lastupdate']) > 24 * 3600):
                    for repo in repos['repos']:
                        if repo['repoacc']:
                            url = '{0}@{1}'.format(repo['repourl'].replace('https://github.com/', 'https://cdn.jsdelivr.net/gh/'), repo['repobranch'])
                        else:
                            if (repo['repourl'].find('https://github.com/') > -1):
                                url = '{0}/{1}'.format(repo['repourl'].replace('https://github.com/', 'https://raw.githubusercontent.com/'), repo['repobranch'])
                            else:
                                url = repo['repourl']

                        hfile_link = url + '/tpls_history.json'
                        async with aiohttp.ClientSession(conn_timeout=config.connect_timeout*5) as session:
                            async with session.get(hfile_link, verify_ssl=False, timeout=config.request_timeout) as res:
                                if res.status == 200:
                                    hfile = await res.json(content_type="")
                                    logger_Web_Handler.info('200 Get repo {repo} history file success!'.format(repo=repo['reponame']))
                                    for har in hfile['har'].values():
                                        for k, v in repo.items():
                                            har[k] = v
                                        tpl = await self.db.pubtpl.list(name = har['name'], 
                                                                reponame=har['reponame'],
                                                                repourl=har['repourl'], 
                                                                repobranch=har['repobranch'], 
                                                                fields=('id', 'name', 'version'),
                                                                sql_session=sql_session)

                                        if (len(tpl) > 0):
                                            if (int(tpl[0]['version']) < int(har['version'])):
                                                if (har['content'] == ''):
                                                    har_url = "{0}/{1}".format(url, quote(har['filename']))
                                                    async with session.get(har_url, verify_ssl=False, timeout=config.request_timeout) as har_res:
                                                        if har_res.status == 200:
                                                            har['content'] = base64.b64encode(await har_res.read()).decode()
                                                        else:
                                                            logger_Web_Handler.error('Update {repo} public template {name} failed! Reason: {link} open error!'.format(repo=repo['reponame'], name=har['name'], link=har_url))
                                                            msg += '打开链接错误{link}\r\n'.format(link=har_url)
                                                            continue
                                                har['update'] = True
                                                await self.db.pubtpl.mod(tpl[0]['id'], **har, sql_session=sql_session)
                                                logger_Web_Handler.info('Update {repo} public template {name} success!'.format(repo=repo['reponame'], name=har['name']))
                                        else:
                                            if (har['content'] == ''):
                                                har_url = "{0}/{1}".format(url, quote(har['filename']))
                                                async with session.get(har_url, verify_ssl=False, timeout=config.request_timeout) as har_res:
                                                    if har_res.status == 200:
                                                        har['content'] = base64.b64encode(await har_res.read()).decode()
                                                    else:
                                                        logger_Web_Handler.error('Add {repo} public template {name} failed! Reason: {link} open error!'.format(repo=repo['reponame'], name=har['name'], link=har_url))
                                                        msg += '打开链接错误{link}\r\n'.format(link=har_url)
                                                        continue
                                            await self.db.pubtpl.add(har, sql_session=sql_session)
                                            logger_Web_Handler.info('Add {repo} public template {name} success!'.format(repo=repo['reponame'], name=har['name']))
                                        
                                else:
                                    logger_Web_Handler.error('Get repo {repo} history file failed! Reason: {link} open error!'.format(repo=repo['reponame'], link=hfile_link))
                                    msg += '打开链接错误{link}\r\n'.format(link=hfile_link)
                
            if msg:
                raise Exception(msg)
            success = True
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
                
            msg = str(e).replace('\\r\\n','\r\n')
            if msg.endswith('\r\n'):
                msg = msg[:-2]
            logger_Web_Handler.error('UserID: %s update Subscribe failed! Reason: %s', userid, msg)

        try:
            async with self.db.transaction() as sql_session:
                repos = json.loads((await self.db.site.get(1, fields=('repos',), sql_session=sql_session))['repos'])
                repos["lastupdate"] = int(time.time())
                await self.db.site.mod(1, repos=json.dumps(repos, ensure_ascii=False, indent=4), sql_session=sql_session)
            
            if success:
                self.write(json.dumps({'code': 0, 'msg': '更新成功, 请刷新页面查看'}))
            else:
                self.write(json.dumps({'code': 1, 'msg': '失败原因: ' + msg.replace("\r\n", "<br>") + "<br>Note: 请刷新页面并修改配置后, 通过强制更新或重建缓存重试!" }))
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
        return

class SubscribeRefreshHandler(BaseHandler):
    @tornado.web.authenticated
    async def post(self, userid):
        try:
            user = self.current_user
            op = self.get_argument('op', '')
            if (op == ''):
                raise Exception('op参数为空')
            
            async with self.db.transaction() as sql_session:
                if (user['id'] == int(userid)) and (user['role'] == u'admin'):
                    repos = json.loads((await self.db.site.get(1, fields=('repos',), sql_session=sql_session))['repos'])
                    repos["lastupdate"] = 0
                    await self.db.site.mod(1, repos=json.dumps(repos, ensure_ascii=False, indent=4), sql_session=sql_session)
                    if (op == 'clear'):
                        for pubtpl in await self.db.pubtpl.list(fields=('id',), sql_session=sql_session):
                            await self.db.pubtpl.delete(pubtpl['id'], sql_session=sql_session)
                else:
                    raise Exception('没有权限操作')
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            await self.render('utils_run_result.html', log=str(e), title=u'设置失败', flg='danger')
            logger_Web_Handler.error('UserID: %s refresh Subscribe failed! Reason: %s', userid, str(e).replace('\\r\\n','\r\n'))
            return

        self.redirect('/subscribe/{0}/'.format(userid) ) 
        return

class Subscrib_signup_repos_Handler(BaseHandler):
    @tornado.web.authenticated
    async def get(self, userid):
        user = self.current_user
        if (user['id'] == int(userid)) and (user['role'] == u'admin'):
            await self.render('pubtpl_register.html', userid=userid)
        else:
            await self.render('utils_run_result.html', log='非管理员用户，不可设置', title=u'设置失败', flg='danger')
            logger_Web_Handler.error('UserID: %s browse Subscrib_signup_repos failed! Reason: 非管理员用户，不可设置', userid)
        return

    @tornado.web.authenticated
    async def post(self, userid):
        try:
            user = self.current_user
            if (user['id'] == int(userid)) and (user['role'] == u'admin'):
                envs = {}
                for key in self.request.body_arguments:
                    envs[key] = self.get_body_arguments(key)
                env = {}
                for k, v  in envs.items():
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
            if config.traceback_print:
                traceback.print_exc()
            await self.render('utils_run_result.html', log=str(e), title=u'设置失败', flg='danger')
            logger_Web_Handler.error('UserID: %s modify Subscribe_signup_repos failed! Reason: %s', userid, str(e).replace('\\r\\n','\r\n'))
            return

        await self.render('utils_run_result.html', log=u'设置成功，请关闭操作对话框或刷新页面查看', title=u'设置成功', flg='success')
        return

class GetReposInfoHandler(BaseHandler):
    @tornado.web.authenticated
    async def post(self, userid):
        try:
            user = self.current_user
            if (user['id'] == int(userid)) and (user['role'] == u'admin'):
                envs = {}
                for key in self.request.body_arguments:
                    envs[key] = self.get_body_arguments(key)
                tmp = json.loads((await self.db.site.get(1, fields=('repos',)))['repos'])['repos']
                repos = []
                for repoid, selected  in envs.items():
                    if isinstance(selected[0],bytes):
                        selected[0] = selected[0].decode()
                    if (selected[0] == 'true'):
                        repos.append(tmp[int(repoid)])
            else:
                raise Exception('非管理员用户，不可查看')
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            await self.render('utils_run_result.html', log=str(e), title=u'获取信息失败', flg='danger')
            logger_Web_Handler.error('UserID: %s get Subscribe_Repos_Info failed! Reason: %s', userid, str(e).replace('\\r\\n','\r\n'))
            return

        await self.render('pubtpl_reposinfo.html',  repos=repos)
        return

class unsubscribe_repos_Handler(BaseHandler):
    @tornado.web.authenticated
    async def get(self, userid):
        try:
            user = self.current_user
            if (user['id'] == int(userid)) and (user['role'] == u'admin'):
                await self.render('pubtpl_unsubscribe.html', user=user)
            else:
                raise Exception('非管理员用户，不可设置')
            return
        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            await self.render('utils_run_result.html', log=str(e), title=u'打开失败', flg='danger')
            logger_Web_Handler.error('UserID: %s browse UnSubscribe_Repos failed! Reason: %s', userid, str(e).replace('\\r\\n','\r\n'))
            return
    
    @tornado.web.authenticated
    async def post(self, userid):
        try:
            user = self.current_user
            if (user['id'] == int(userid)) and (user['role'] == u'admin'):
                envs = {}
                for key in self.request.body_arguments:
                    envs[key] = self.get_body_arguments(key)
                env = {}
                for k, v  in envs.items():
                    try:
                        env[k] = json.loads(v[0])
                    except:
                        env[k] = v[0]
                async with self.db.transaction() as sql_session:
                    repos = json.loads((await self.db.site.get(1, fields=('repos',),sql_session=sql_session))['repos'])
                    tmp = repos['repos']
                    result = []
                    for i, j  in enumerate(tmp):
                        # 检查是否存在同名仓库
                        if not env['selectedrepos'].get(str(i),False) :
                            result.append(j)
                        else:
                            pubtpls = await self.db.pubtpl.list(reponame=j['reponame'], fields=('id',),sql_session=sql_session)
                            for pubtpl in pubtpls:
                                await self.db.pubtpl.delete(pubtpl['id'],sql_session=sql_session)
                    repos['repos'] = result
                    await self.db.site.mod(1, repos=json.dumps(repos, ensure_ascii=False, indent=4), sql_session=sql_session)
            else:
                raise Exception('非管理员用户，不可设置')

        except Exception as e:
            if config.traceback_print:
                traceback.print_exc()
            await self.render('utils_run_result.html', log=str(e), title=u'设置失败', flg='danger')
            logger_Web_Handler.error('UserID: %s unsubscribe Subscribe_Repos failed! Reason: %s', userid, str(e).replace('\\r\\n','\r\n'))
            return

        await self.render('utils_run_result.html', log=u'设置成功，请关闭操作对话框或刷新页面查看', title=u'设置成功', flg='success')
        return

handlers = [
        ('/subscribe/(\d+)/', SubscribeHandler),
        ('/subscribe/(\d+)/updating/', SubscribeUpdatingHandler),
        ('/subscribe/refresh/(\d+)/', SubscribeRefreshHandler),
        ('/subscribe/signup_repos/(\d+)/', Subscrib_signup_repos_Handler),
        ('/subscribe/(\d+)/get_reposinfo', GetReposInfoHandler),
        ('/subscribe/unsubscribe_repos/(\d+)/', unsubscribe_repos_Handler),
        ]

