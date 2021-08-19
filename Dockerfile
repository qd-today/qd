# 基础镜像
FROM python:3.8-alpine

# 维护者信息
LABEL maintainer "a76yyyy <q981331502@163.com>"

# 签到版本 20190220
# 集成皮蛋0.1.1  https://github.com/cdpidan/qiandaor
# 加入蓝调主题 20190118 https://www.quchao.net/QianDao-Theme.html
# --------------
# 基于以上镜像修改了：1、时区设置为上海 2、修改了链接限制 3、加入了send2推送
# 20210112 添加git模块，实现重启后自动更新镜像
# 20210628 使用gitee作为代码源，添加密钥用于更新
# 20210728 更换python版本为python3.8,默认包含redis

ADD . /usr/src/app
WORKDIR /usr/src/app

# 换源
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.ustc.edu.cn/g' /etc/apk/repositories

# Install packages
RUN apk update \
    && apk add --no-cache openrc redis libcurl bash git autoconf g++ tzdata nano openssh-client

# Needed for pycurl
ENV PYCURL_SSL_LIBRARY=openssl

# Install packages only needed for building, install and clean on a single layer
RUN apk add --no-cache --virtual .build-dependencies build-base curl-dev 

# Setting openrc-redis
RUN rc-status -a \
    && echo -e '#!/bin/sh \nredis-server /etc/redis.conf' > /etc/local.d/redis.start \
    && chmod +x /etc/local.d/redis.start \
    && rc-update add local \
    && rc-status -a 

# Qiandao
RUN mkdir -p /root/.ssh \
    && cp -f ssh/qiandao_fetch /root/.ssh/id_rsa \
    && cp -f ssh/qiandao_fetch.pub /root/.ssh/id_rsa.pub \
    && chmod 600 /root/.ssh/id_rsa \
    && ssh-keyscan gitee.com > /root/.ssh/known_hosts \
    && git clone git@gitee.com:a76yyyy/qiandao.git /gitclone_tmp \
    && yes | cp -rf /gitclone_tmp/. /usr/src/app
    
# Pip install modules
RUN pip install --upgrade setuptools \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-dependencies \
    && rm -rf /var/cache/apk/* 
   
ENV PORT 80
EXPOSE $PORT/tcp

# timezone
ENV TZ=CST-8

# 添加挂载点
VOLUME ["/usr/src/app/","/data"]

CMD ["sh","-c","redis-server --daemonize yes && python /usr/src/app/run.py"]

