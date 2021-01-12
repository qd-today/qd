# 基础镜像
FROM python:2.7-alpine

# 维护者信息
LABEL maintainer "asdaragon <aragonchen0@gmail.com>"

# 签到版本 20190220
# 集成皮蛋0.1.1  https://github.com/cdpidan/qiandaor
# 加入蓝调主题 20190118 https://www.quchao.net/QianDao-Theme.html
# --------------
# 基于以上镜像修改了：1、时区设置为上海 2、修改了链接限制 3、加入了send2推送
# 20210112 添加git模块，实现重启后自动更新镜像

ADD . /usr/src/app
WORKDIR /usr/src/app

# 基础镜像已经包含pip组件
RUN apk update \
    && apk add bash git autoconf g++ \
    && pip install --no-cache-dir -r requirements.txt
   
ENV PORT 80
EXPOSE $PORT/tcp

# timezone
ENV TZ=CST-8

# 添加挂载点
VOLUME ["/usr/src/app/"]

ENTRYPOINT  git config --global credential.helper store && \
            git fetch --all && \
            git reset --hard origin/master && \
            python  /usr/src/app/run.py

