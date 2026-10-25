# QD 运行环境。
# 基座 a76yyyy/pycurl 已提供 pycurl（含 ja3 补丁）、ddddocr、OpenCV、onnxruntime，
# 本文件只安装 QD 自身的依赖并放入代码。
ARG BASE_IMAGE=a76yyyy/pycurl:1.5.0
FROM ${BASE_IMAGE}

# FROM 之前的 ARG 在 FROM 之后即失效，这里重新声明以供 LABEL 使用
ARG BASE_IMAGE
LABEL maintainer="a76yyyy <q981331502@163.com>"
LABEL org.opencontainers.image.source=https://github.com/qd-today/qd
LABEL org.opencontainers.image.base.name="${BASE_IMAGE}"

# 本地构建加速（CI 在海外无需配置）：APK_MIRROR 例 https://mirrors.tuna.tsinghua.edu.cn
ARG APK_MIRROR=""
ARG PIP_MIRROR=""

WORKDIR /usr/src/app

# 依赖分两类：
#   1) Alpine 原生 py3-* 包——与 musl 配套，无需源码编译
#   2) 其余纯 Python 包——从 requirements.txt 安装
# 关键：基座已提供的（pycurl）和第 1 类已装的，必须从 pip 清单里剔除。
# 否则 pip 会把基座里编译好的 pycurl 覆盖成 PyPI 上的 vanilla 版本，
# ja3 变体的 IMPERSONATE 补丁会随之失效（历史事故，见 commit 说明）。
COPY requirements.txt /tmp/requirements.txt
RUN set -eu && \
    { [ -z "$APK_MIRROR" ] || sed -i "s|https://dl-cdn.alpinelinux.org|$APK_MIRROR|g" /etc/apk/repositories; } && \
    apk update && \
    # py3-pip 保留在运行时：pip 只装 Alpine 源里没有的纯 Python 包，
    # 留着也方便使用者在容器内补装（基座本身不带 pip）
    apk add --update --no-cache \
        openssh-client python3 py3-pip py3-six py3-markupsafe py3-pycryptodome py3-tornado \
        py3-wrapt py3-packaging py3-greenlet py3-urllib3 py3-cryptography \
        py3-aiosignal py3-async-timeout py3-attrs py3-frozenlist \
        py3-multidict py3-charset-normalizer py3-aiohttp \
        py3-typing-extensions py3-yarl py3-cffi && \
    # 与上面的 apk 清单、基座提供的包保持一致；改依赖时同步这两处
    grep -vE '^(pycurl|aiohttp|aiosignal|async-timeout|attrs|charset-normalizer|cffi|cryptography|ddddocr|frozenlist|greenlet|markupsafe|multidict|numpy|opencv-python|packaging|pillow|pycryptodome|six|tornado|typing-extensions|urllib3|wrapt|yarl)[=<>~]' \
        /tmp/requirements.txt > /tmp/req.docker.txt && \
    { [ -z "$PIP_MIRROR" ] || export PIP_INDEX_URL="$PIP_MIRROR"; } && \
    pip install --no-cache-dir --break-system-packages -r /tmp/req.docker.txt && \
    rm -f /tmp/requirements.txt /tmp/req.docker.txt && \
    rm -rf /var/cache/apk/* /usr/share/man/* /root/.cache/pip

# 代码直接用构建上下文（.dockerignore 已排除 .git / node_modules 等），
# 不再在构建时从 gitee clone——那会让镜像内容与仓库脱节，且需要把部署私钥打进镜像
COPY . /usr/src/app
RUN chmod +x /usr/src/app/update.sh && ln -sf /usr/src/app/update.sh /bin/update

ENV PORT=80
EXPOSE 80/tcp

# timezone
ENV TZ=CST-8

# 添加挂载点
VOLUME ["/usr/src/app/config"]

CMD ["sh","-c","python /usr/src/app/run.py"]
