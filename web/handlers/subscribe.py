#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-08-08 21:06:02

import json
import os
import traceback
import time
import requests
import base64

from base import *

class SubscribeHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self, userid):
        msg = ''
        user = self.current_user
        adminflg = False
        if (user['id'] == int(userid)) and (user['role'] == u'admin'):
            adminflg = True
        repos = json.loads(self.db.site.get(1, fields=('repos'))['repos'])
        try:
            now_ts = int(time.time())
            # 如果上次更新时间大于1天则更新模板仓库
            if (now_ts - int(repos['lastupdate']) > 24 * 3600):
                for repo in repos['repos']:
                    if repo['repoacc']:
                        url = '{0}@{1}'.format(repo['repourl'].replace('https://github.com/', 'https://cdn.jsdelivr.net/gh/'), repo['repobranch'])
                    else:
                        if (repo['repourl'].find('https://github.com/') > -1):
                            url = '{0}/{1}'.format(repo['repourl'].replace('https://github.com/', 'https://raw.githubusercontent.com/'), repo['repobranch'])
                        else:
                            url = repo['repourl']

                    hfile_link = url + '/tpls_history.json'
                    res = requests.get(hfile_link, verify=False)
                    if res.status_code == 200:
                        hfile = json.loads(res.content.decode(res.encoding, 'replace'))
                        for har in hfile['har'].values():
                            if (har['content'] == ''):
                                harfile_link = "{0}/{1}".format(url, har['filename'])
                                har_res = requests.get(harfile_link, verify=False)
                                if har_res.status_code == 200:
                                    har['content'] = base64.b64encode(har_res.content.decode(har_res.encoding or 'utf-8', 'replace'))
                                else:
                                    msg = '{pre}\r\n打开链接错误{link}'.format(pre=msg, link=harfile_link)

                            for k, v in repo.items():
                                har[k] = v
                            tpl = self.db.pubtpl.list(name = har['name'], 
                                                      reponame=har['reponame'],
                                                      repourl=har['repourl'], 
                                                      repobranch=har['repobranch'], 
                                                      fields=('id', 'name', 'version'))

                            if (len(tpl) > 0):
                                if (int(tpl[0]['version']) < int(har['version'])):
                                    har['update'] = True
                                    self.db.pubtpl.mod(tpl[0]['id'], **har)
                            else:
                                self.db.pubtpl.add(har)
                    else:
                        msg = '{pre}\r\n打开链接错误{link}'.format(pre=msg, link=hfile_link)
                if msg == '':
                    repos["lastupdate"] = now_ts
                    self.db.site.mod(1, repos=json.dumps(repos, ensure_ascii=False, indent=4))

            tpls = self.db.pubtpl.list()

            self.render('pubtpl_subscribe.html', tpls=tpls, user=user, userid=user['id'], adminflg=adminflg, repos=repos['repos'], msg=msg)

        except Exception:
            traceback.print_exc()
            user = self.current_user
            tpls = self.db.pubtpl.list()
            self.render('pubtpl_subscribe.html', tpls=tpls, user=user, userid=user['id'], adminflg=adminflg, repos=repos['repos'], msg=traceback.format_exc())
            return

class SubscribeRefreshHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, userid):
        try:
            user = self.current_user
            op = self.request.arguments.get('op', '')
            if (op == ''):
                raise Exception('op参数为空')

            if (user['id'] == int(userid)) and (user['role'] == u'admin'):
                repos = json.loads(self.db.site.get(1, fields=('repos'))['repos'])
                repos["lastupdate"] = 0
                self.db.site.mod(1, repos=json.dumps(repos, ensure_ascii=False, indent=4))
                if (op == 'clear'):
                    for pubtpl in self.db.pubtpl.list(fields=('id')):
                        self.db.pubtpl.delete(pubtpl['id'])
            else:
                raise Exception('没有权限操作')
        except Exception:
            traceback.print_exc()
            self.render('utils_run_result.html', log=traceback.format_exc(), title=u'设置失败', flg='danger')
            return

        self.redirect('/subscribe/{0}/'.format(userid) ) 
        return

class Subscrib_signup_repos_Handler(BaseHandler):
    @tornado.web.authenticated
    def get(self, userid):
        user = self.current_user
        if (user['id'] == int(userid)) and (user['role'] == u'admin'):
            self.render('pubtpl_register.html', userid=userid)
        else:
            self.render('utils_run_result.html', log='非管理员用户，不可设置', title=u'设置失败', flg='danger')
        return

    @tornado.web.authenticated
    def post(self, userid):
        try:
            user = self.current_user
            if (user['id'] == int(userid)) and (user['role'] == u'admin'):
                env = {}
                for k, v  in self.request.body_arguments.items():
                    if (v[0] == 'false') or (v[0] == 'true'):
                        env[k] = True if v == 'true' else False
                    else:
                        env[k] = v[0]

                if (env['reponame'] != '') and (env['repourl'] != '') and (env['repobranch'] != ''):
                    repos = json.loads(self.db.site.get(1, fields=('repos'))['repos'])
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
                        self.db.site.mod(1, repos=json.dumps(repos, ensure_ascii=False, indent=4))
                else:
                    raise Exception('仓库名/url/分支不能为空')
            else:
                raise Exception('非管理员用户，不可设置')

        except Exception:
            traceback.print_exc()
            self.render('utils_run_result.html', log=traceback.format_exc(), title=u'设置失败', flg='danger')
            return

        self.render('utils_run_result.html', log=u'设置成功，请手动刷新页面查看', title=u'设置成功', flg='success')
        return

class unsubscribe_repos_Handler(BaseHandler):
    @tornado.web.authenticated
    def post(self, userid):
        try:
            user = self.current_user
            if (user['id'] == int(userid)) and (user['role'] == u'admin'):
                env = {}
                for k, v  in self.request.body_arguments.items():
                    env[k] = v[0]

                if (env['reponame'] != ''):
                    repos = json.loads(self.db.site.get(1, fields=('repos'))['repos'])
                    tmp = repos['repos']
                    inflg = False
                    repoindex = 99
                    # 检查是否存在同名仓库
                    for i in range(0, len(tmp)):
                        if tmp[i]['reponame'] == env['reponame']:
                            repoindex = i
                            del tmp[repoindex]
                            repos['repos'] = tmp
                            pubtpls = self.db.pubtpl.list(reponame=env['reponame'], fields=('id'))
                            for pubtpl in pubtpls:
                                self.db.pubtpl.delete(pubtpl['id'])
                            self.db.site.mod(1, repos=json.dumps(repos, ensure_ascii=False, indent=4))
                            break
                    else:
                        raise Exception('不存在此仓库')

                else:
                    raise Exception('仓库名不能为空')
            else:
                raise Exception('非管理员用户，不可设置')

        except Exception:
            traceback.print_exc()
            self.render('utils_run_result.html', log=traceback.format_exc(), title=u'设置失败', flg='danger')
            return

        self.render('utils_run_result.html', log=u'设置成功，请手动刷新页面查看', title=u'设置成功', flg='success')
        return

handlers = [
        ('/subscribe/(\d+)/', SubscribeHandler),
        ('/subscribe/refresh/(\d+)/', SubscribeRefreshHandler),
        ('/subscribe/signup_repos/(\d+)/', Subscrib_signup_repos_Handler),
        ('/subscribe/unsubscribe_repos/(\d+)/', unsubscribe_repos_Handler),
        ]

