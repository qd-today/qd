# 基础镜像
FROM a76yyyy/pycurl:latest

# 维护者信息
LABEL maintainer "a76yyyy <q981331502@163.com>"
LABEL org.opencontainers.image.source=https://github.com/qd-today/qd

ADD ssh/qd_fetch /root/.ssh/id_rsa
ADD ssh/qd_fetch.pub /root/.ssh/id_rsa.pub
WORKDIR /usr/src/app

# QD && Pip install modules
RUN sed -i 's/mirrors.ustc.edu.cn/dl-cdn.alpinelinux.org/g' /etc/apk/repositories && \
    sed -i 's/edge/v3.19/g' /etc/apk/repositories && \
    sed -i '/testing/d' /etc/apk/repositories && \
    apk update && apk add --update --no-cache openssh-client && \
    chmod 600 /root/.ssh/id_rsa && \
    ssh-keyscan gitee.com > /root/.ssh/known_hosts && \
    let num=$RANDOM%100+10 && \
    sleep $num && \
    git clone --depth 1 git@gitee.com:qd-today/qd.git /gitclone_tmp && \
    yes | cp -rf /gitclone_tmp/. /usr/src/app && \
    rm -rf /gitclone_tmp && \
    chmod +x /usr/src/app/update.sh && \
    ln -s /usr/src/app/update.sh /bin/update && \
    apk add --update --no-cache openssh-client python3 py3-six \
    py3-markupsafe py3-pycryptodome py3-tornado py3-wrapt \
    py3-packaging py3-greenlet py3-urllib3 py3-cryptography \
    py3-aiosignal py3-async-timeout py3-attrs py3-frozenlist \
    py3-multidict py3-charset-normalizer py3-aiohttp \
    py3-typing-extensions py3-yarl py3-cffi && \
    [[ $(getconf LONG_BIT) = "32" ]] && \
    echo "Tips: 32-bit systems do not support ddddocr, so there is no need to install numpy and opencv-python" || \
    apk add --update --no-cache py3-numpy-dev py3-opencv py3-pillow && \
    apk add --no-cache --virtual .build_deps cmake make perl \
    autoconf g++ automake py3-pip py3-setuptools py3-wheel python3-dev \
        linux-headers libtool util-linux && \
    sed -i '/ddddocr/d' requirements.txt && \
    sed -i '/packaging/d' requirements.txt && \
    sed -i '/wrapt/d' requirements.txt && \
    sed -i '/pycryptodome/d' requirements.txt && \
    sed -i '/tornado/d' requirements.txt && \
    sed -i '/MarkupSafe/d' requirements.txt && \
    sed -i '/pillow/d' requirements.txt && \
    sed -i '/opencv/d' requirements.txt && \
    sed -i '/numpy/d' requirements.txt && \
    sed -i '/greenlet/d' requirements.txt && \
    sed -i '/urllib3/d' requirements.txt && \
    sed -i '/cryptography/d' requirements.txt && \
    sed -i '/aiosignal/d' requirements.txt && \
    sed -i '/async-timeout/d' requirements.txt && \
    sed -i '/attrs/d' requirements.txt && \
    sed -i '/frozenlist/d' requirements.txt && \
    sed -i '/multidict/d' requirements.txt && \
    sed -i '/charset-normalizer/d' requirements.txt && \
    sed -i '/aiohttp/d' requirements.txt && \
    sed -i '/typing-extensions/d' requirements.txt && \
    sed -i '/yarl/d' requirements.txt && \
    sed -i '/cffi/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt --break-system-packages && \
    apk del .build_deps && \
    sed -i 's/dl-cdn.alpinelinux.org/mirrors.ustc.edu.cn/g' /etc/apk/repositories && \
    rm -rf /var/cache/apk/* && \
    rm -rf /usr/share/man/*

ENV PORT 80
EXPOSE $PORT/tcp

# timezone
ENV TZ=CST-8

# 添加挂载点
VOLUME ["/usr/src/app/config"]

CMD ["sh","-c","python /usr/src/app/run.py"]
