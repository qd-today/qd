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
# 20210728 更换python版本为python3.8

ADD . /usr/src/app
WORKDIR /usr/src/app

# 安装curl
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.ustc.edu.cn/g' /etc/apk/repositories
RUN apk add --update curl && rm -rf /var/cache/apk/*

# 基础镜像已经包含pip组件
RUN apk update \
    && apk add bash git autoconf g++ tzdata nano openssh-client \
    && mkdir -p /root/.ssh \
    && cp -f ssh/qiandao_fetch /root/.ssh/id_rsa \
    && cp -f ssh/qiandao_fetch.pub /root/.ssh/id_rsa.pub \
    && chmod 600 /root/.ssh/id_rsa \
    && ssh-keyscan gitee.com > /root/.ssh/known_hosts \
    && git clone git@gitee.com:a76yyyy/qiandao.git /gitclone_tmp \
    && yes | cp -rf /gitclone_tmp/. /usr/src/app \
    && pip install --upgrade setuptools \
    && pip install --no-cache-dir -r requirements.txt
   
ENV PORT 80
EXPOSE $PORT/tcp

# timezone
ENV TZ=CST-8

# 添加挂载点
VOLUME ["/usr/src/app/"]

CMD ["python","/usr/src/app/run.py"]

