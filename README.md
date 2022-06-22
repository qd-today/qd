<p align="center">
   <a href="https://github.com/qiandao-today/qiandao">
   <img style="border-radius:50%" width="150" src="https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/web/static/img/icon.png">
   </a>
</p>

<h1 align="center">QianDao for Python3</h1>

<div align="center">
Qiandao —— 一个<b>HTTP请求定时任务自动执行框架</b> base on HAR Editor and Tornado Server

[![HomePage][HomePage-image]][HomePage-url]
[![Github][Github-image]][Github-url]
[![Gitee][Gitee-image]][Gitee-url]
[![license][github-license-image]][github-license-url]
[![Build Image][workflow-image]][workflow-url]
[![last commit][last-commit-image]][last-commit-url]
[![commit activity][commit-activity-image]][commit-activity-url]
[![docker version][docker-version-image]][docker-version-url]
[![docker pulls][docker-pulls-image]][docker-pulls-url]
[![docker stars][docker-stars-image]][docker-stars-url]
[![docker image size][docker-image-size-image]][docker-image-size-url]
![repo size][repo-size-image]
![python version][python-version-image]

[HomePage-image]: https://img.shields.io/badge/HomePage-qiandao--today-brightgreen
[HomePage-url]: https://qiandao.a76yyyy.cn
[Github-image]: https://img.shields.io/static/v1?label=Github&message=qiandao-today&color=brightgreen
[Github-url]: https://github.com/qiandao-today/qiandao/
[Gitee-image]: https://img.shields.io/static/v1?label=Gitee&message=a76yyyy&color=brightgreen
[Gitee-url]: https://gitee.com/a76yyyy/qiandao/
[github-license-image]: https://img.shields.io/github/license/qiandao-today/qiandao
[github-license-url]: https://github.com/qiandao-today/qiandao/blob/master/LICENSE
[last-commit-image]: https://img.shields.io/github/last-commit/qiandao-today/qiandao
[last-commit-url]: https://github.com/qiandao-today/qiandao/
[commit-activity-image]: https://img.shields.io/github/commit-activity/m/qiandao-today/qiandao
[commit-activity-url]: https://github.com/qiandao-today/qiandao/
[docker-version-image]: https://img.shields.io/docker/v/a76yyyy/qiandao?style=flat
[docker-version-url]: https://hub.docker.com/r/a76yyyy/qiandao/tags?page=1&ordering=last_updated
[docker-pulls-image]: https://img.shields.io/docker/pulls/a76yyyy/qiandao?style=flat
[docker-pulls-url]: https://hub.docker.com/r/a76yyyy/qiandao
[docker-stars-image]: https://img.shields.io/docker/stars/a76yyyy/qiandao?style=flat
[docker-stars-url]: https://hub.docker.com/r/a76yyyy/qiandao
[docker-image-size-image]: https://img.shields.io/docker/image-size/a76yyyy/qiandao?style=flat
[docker-image-size-url]: https://hub.docker.com/r/a76yyyy/qiandao
[repo-size-image]: https://img.shields.io/github/repo-size/qiandao-today/qiandao
[python-version-image]: https://img.shields.io/github/pipenv/locked/python-version/qiandao-today/qiandao
[workflow-image]: https://github.com/qiandao-today/qiandao/actions/workflows/Build%20Image.yml/badge.svg
[workflow-url]: https://github.com/qiandao-today/qiandao/actions/workflows/Build%20Image.yml

</div>

<p align="center">
   <img width="45%" style="border:solid 1px #DCEBFB" src="https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/web/static/img/login.png" >
   <img width="45%" style="border:solid 1px #DCEBFB" src="https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/web/static/img/index.png">
</p>

操作说明
==========

[HAR editor 使用指南](https://github.com/qiandao-today/qiandao/blob/master/docs/har-howto.md)

**操作前请一定要记得备份数据库**

**请勿同时运行新旧版 Qiandao 框架, 或将不同运行中容器的数据库映射为同一文件, 更新后请重启容器或清空浏览器缓存**

Docker容器部署方式
==========

1. **Docker地址** : [https://hub.docker.com/r/a76yyyy/qiandao](https://hub.docker.com/r/a76yyyy/qiandao)

2. **Docker Compose部署方式**

   ``` bash
   # 创建并切换至 qiandao 目录
   mkdir -p $(pwd)/qiandao/config && cd $(pwd)/qiandao
   # 下载 docker-compose.yml
   wget https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/docker-compose.yml
   # 根据需求和配置描述修改配置环境变量
   vi ./docker-compose.yml
   # 执行 Docker Compose 命令
   docker-compose up -d
   ```

   > 配置描述见下文[配置环境变量](#configpy-配置环境变量)
   > 
   > 如不需要`OCR功能`或者`硬盘空间不大于600M`, 请使用 **`a76yyyy/qiandao:lite-latest`** 镜像, **该镜像仅去除了OCR相关功能, 其他与主线版本保持一致**。

3. **Docker部署方式**

   ``` bash
   docker run -d --name qiandao -p 8923:80 -v $(pwd)/qiandao/config:/usr/src/app/config a76yyyy/qiandao
   ```

- 容器内部无法连通外网时尝试该命令:  

   ``` bash
   docker run -d --name qiandao --env PORT=8923 --net=host -v $(pwd)/qiandao/config:/usr/src/app/config a76yyyy/qiandao
   ```

   > 请注意使用该命令创建容器后, 请将模板里 `http://localhost/` 形式的api请求, 手动改成`api://` 或 `http://localhost:8923/` 后, 才能正常完成相关API请求。

4. **数据库备份指令** :

   ``` bash
   docker cp 容器名:/usr/src/app/config/database.db .
   ```

- **数据库恢复指令** :

  ``` bash
  docker cp database.db 容器名:/usr/src/app/config/
  ```

5. Docker 配置邮箱(强制使用SSL)

   ``` bash
   docker run -d --name qiandao -p 8923:80 -v $(pwd)/qiandao/config:/usr/src/app/config --env MAIL_SMTP=STMP服务器 --env MAIL_PORT=邮箱服务器端口 --env MAIL_USER=用户名 --env MAIL_PASSWORD=密码  --env DOMAIN=域名 a76yyyy/qiandao
   ```

6. Docker 使用MySQL

   ``` bash
   docker run -d --name qiandao -p 8923:80 -v $(pwd)/qiandao/config:/usr/src/app/config --ENV DB_TYPE=mysql --ENV JAWSDB_MARIA_URL=mysql://用户名:密码@hostname:port/数据库名 a76yyyy/qiandao
   ```

7. 其余可参考 Wiki : [Docker部署 Qiandao 站教程](https://github.com/qiandao-today/qiandao/blob/master/docs/Docker-howto.md)

8. DockerHub : [介绍](http://mirrors.ustc.edu.cn/help/dockerhub.html)

9. **Docker已预装Curl环境, 默认安装pycurl模组**

Web源码部署方式
===========

1. **Version : python3.8**

   ``` bash
   # 请先cd到框架源码根目录
   pip3 install -r requirements.txt
   ```

2. **可选 redis, Mysql**

   ``` bash
   mysql < qiandao.sql
   ```

3. **修改相关设置**

   ``` bash
   # 请先在框架根目录下新建local_config.py, 在linux环境下可执行以下命令
   cp config.py local_config.py
   # 修改local_config.py文件的内容不受通过git更新源码的影响
   ```

4. **启动**

   ``` bash
   python ./run.py
   ```

   > 数据不随项目分发, 去 [https://github.com/qiandao-today/templates](https://github.com/qiandao-today/templates) 查看你需要的模板, 点击下载。
   >
   > 在你自己的主页中 「我的模板 **+**」 点击 **+** 上传模板。
   >
   > 模板需要发布才会在「公开模板」中展示, 你需要管理员权限在「我的发布请求」中审批通过。

5. **设置管理员**

   ``` bash
   python ./chrole.py your@email.address admin
   ```

6. **qiandao.py-CMD操作**

   ``` bash
   python ./qiandao.py tpl.har [--key=value]* [env.json]
   ```

config.py-配置环境变量
===========

变量名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
BIND|否|0.0.0.0|监听地址
PORT|否|8923|监听端口
QIANDAO_DEBUG|否|False|是否启用Debug模式
MULTI_PROCESS|否|False|是否启用多进程模式, <br>Windows平台无效
AUTO_RELOAD|否|False|是否启用自动热加载, <br>MULTI_PROCESS=True时无效
ENABLE_HTTPS|否|False|发送的邮件链接启用HTTPS, <br>非程序使用HTTPS, 需要HTTPS需要使用反向代理
DOMAIN|否|qiandao.today|指定访问域名, <br>**<建议修改>**, 否则邮件重置密码等功能无效
AES_KEY|否|binux|AES加密密钥, **<强烈建议修改>**
COOKIE_SECRET|否|binux|cookie加密密钥, **<强烈建议修改>**
COOKIE_DAY|否|5|Cookie在客户端保留天数
DB_TYPE|否|sqlite3|需要使用MySQL时设置为'mysql'
JAWSDB_MARIA_URL|否|''|需要使用MySQL时, <br>设置为 <mysql://用户名:密码@hostname:port/数据库名?auth_plugin=>
REDISCLOUD_URL|否|''|需要使用Redis或RedisCloud时, <br>设置为 <http://rediscloud:密码@hostname:port>
REDIS_DB_INDEX|否|1|默认为1
QIANDAO_EVIL|否|500|(限Redis连接已开启)登录用户或IP在1小时内 <br>操作失败(如登录, 验证, 测试等操作)次数*相应惩罚分值 <br>达到evil上限后自动封禁直至下一小时周期
EVIL_PASS_LAN_IP|否|True|是否关闭本机私有IP地址用户及Localhost_API请求的evil限制
TRACEBACK_PRINT|否|False|是否启用在控制台日志中打印Exception的TraceBack信息
PUSH_PIC_URL|否|[push_pic.png](https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/web/static/img/push_pic.png)|默认为[push_pic.png](https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/web/static/img/push_pic.png)
PUSH_BATCH_SW|否|True|是否允许开启定期推送 Qiandao 任务日志, 默认为True
MAIL_SMTP|否|""|邮箱SMTP服务器
MAIL_PORT|否|""|邮箱SMTP服务器端口
MAIL_USER|否|""|邮箱用户名
MAIL_PASSWORD|否|""|邮箱密码
MAIL_FROM|否|MAIL_USER|发送时使用的邮箱，默认与MAIL_USER相同
MAIL_DOMAIN|否|mail.qiandao.today|邮箱域名,没啥用, 使用的DOMAIN
PROXIES|否|""|全局代理域名列表,用"|"分隔
PROXY_DIRECT_MODE|否|""|全局代理黑名单模式,默认不启用 <br>"url"为网址匹配模式;"regexp"为正则表达式匹配模式
PROXY_DIRECT|否|""|全局代理黑名单匹配规则
USE_PYCURL|否|True|是否启用Pycurl模组
ALLOW_RETRY|否|True|在Pycurl环境下部分请求可能导致Request错误时, <br>自动修改冲突设置并重发请求
DNS_SERVER|否|""|通过Curl使用指定DNS进行解析(仅支持Pycurl环境), <br>如 8.8.8.8
CURL_ENCODING|否|True|是否允许使用Curl进行Encoding操作
CURL_CONTENT_LENGTH|否|True|是否允许Curl使用Headers中自定义Content-Length请求
NOT_RETRY_CODE|否|[详见配置](https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/config.py)...|[详见配置](https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/config.py)...
EMPTY_RETRY|否|True|[详见配置](https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/config.py)...
USER0ISADMIN|否|True|第一个注册用户为管理员，False关闭
EXTRA_ONNX_NAME|否|""|config目录下自定义ONNX文件名<br>(不填 ".onnx" 后缀)<br>多个onnx文件名用"\|"分隔
EXTRA_CHARSETS_NAME|否|""|config目录下自定义ONNX对应自定义charsets.json文件名<br>(不填 ".json" 后缀)<br>多个json文件名用"\|"分隔
> 详细信息请查阅[config.py](https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/config.py)

## 旧版local_config.py迁移

|  Line  |  Delete  |  Modify  |
|  ----  | ----  | ----  |
|10|~~```import urlparse```~~|```from urllib.parse import urlparse```|
|18|~~```mysql_url = urlparse.urlparse(os.getenv('JAWSDB_MARIA_URL', ''))```~~|```mysql_url = urlparse(os.getenv('JAWSDB_MARIA_URL', ''))```|
|19|~~```redis_url = urlparse.urlparse(os.getenv('REDISCLOUD_URL', ''))```~~|```redis_url = urlparse(os.getenv('REDISCLOUD_URL', ''))```|
|43|~~```aes_key = hashlib.sha256(os.getenv('AES_KEY', 'binux').encode('utf-8')).digest()```~~|```aes_key = hashlib.sha256(os.getenv('AES_KEY', 'binux')).digest()```|
|44|~~```cookie_secret = hashlib.sha256(os.getenv('COOKIE_SECRET', 'binux').encode('utf-8')).digest()```~~|```cookie_secret = hashlib.sha256(os.getenv('COOKIE_SECRET', 'binux')).digest()```|

更新方法
===========

1. **源码部署更新**

   ``` bash
   # 先cd到源码所在目录, 执行命令后重启进程 
   wget https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/update.sh -O ./update.sh && \
   sh ./update.sh 
   ```

2. **Docker容器部署更新**

   ``` bash
   # 先进入容器后台, 执行命令后重启容器 
   wget https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/update.sh -O /usr/src/app/update.sh && \
   sh /usr/src/app/update.sh
   ```

3. **强制同步最新源码**

   ``` bash
   # 先cd到仓库代码根目录, 执行命令后重启进程 
   wget https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/update.sh -O ./update.sh && \
   sh ./update.sh -f
   ```

更新日志
===========

详见 **[CHANGELOG.md](./CHANGELOG.md)**

鸣谢
===========

[Binux](https://github.com/binux/qiandao)

[Mark](https://www.quchao.net/)

[PiDan](https://github.com/cdpidan)

[AragonSnow](https://hexo.aragon.wang/)

[AragonSnow/qiandao](https://github.com/aragonsnow/qiandao)

[戏如人生](https://49594425.xyz/)

[buzhibujuelb](https://github.com/buzhibujuelb)

[billypon](https://github.com/billypon)

[powersee](https://github.com/powersee)

[acooler15](https://github.com/acooler15)

[a76yyyy](https://github.com/a76yyyy/qiandao)

[……](https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/version.json)

个人项目精力有限, 仅保证对Chrome浏览器的支持。如果测试了其他浏览器可以pull request。

许可
===========

[MIT](https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/LICENSE) 许可协议
