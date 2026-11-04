# QD 运行环境。
#
# 基座是纯 alpine：Python 依赖全部来自三个 wheelhouse（onnxruntime / ddddocr / pycurl），
# 不再 FROM a76yyyy/pycurl 继承「已经装好的包」。
#
# 为什么不再继承基座：
#   - 依赖来源变成契约而不是启发式。旧版由 docker/install-deps.py 现场探测「基座提供了
#     什么」再跳过，那是猜测：曾经把打过 IMPERSONATE 补丁的 pycurl 覆盖成 PyPI 版，
#     ja3 线实际失效。
#   - venv 看不到基座里的包，继续 FROM 重基座会变成双份（venv 一份 + 基座一份）。
#   - 版本对齐由 uv.lock 与 wheelhouse tag 保证，不一致时解析直接失败。

ARG ALPINE_VERSION=3.24
# 官方 alpine 没有 loongarch64，CI 对 loong64 传 ghcr.io/loong64/alpine:3.24。
# 其余架构用默认值。
ARG BASE_IMAGE=alpine:${ALPINE_VERSION}
FROM ${BASE_IMAGE}

ARG ALPINE_VERSION
LABEL maintainer="a76yyyy <q981331502@163.com>"
LABEL org.opencontainers.image.source=https://github.com/qd-today/qd

# 本地构建加速（CI 在海外无需配置）
ARG APK_MIRROR=""
ARG PIP_MIRROR=""

# 依赖来源：三个组件仓库的发布版本。update.sh 从这里读，保证热更新装的是
# 与镜像构建同一批 wheel，不在脚本里维护第二份版本号。
ARG ONNXRUNTIME_RELEASE=1.24.4
ARG DDDDOCR_RELEASE=1.6.1
ARG PYCURL_RELEASE=2.0.0

WORKDIR /usr/src/app

# 依赖单一来源：pyproject.toml + uv.lock
COPY pyproject.toml uv.lock /usr/src/app/

# uv 默认把解压后的包缓存到 ~/.cache/uv；在容器里那是纯浪费（缓存体积约等于 venv）。
# 必须走环境变量而不是逐条 --no-cache：sync / pip / export 都要生效。
ENV UV_NO_CACHE=1
# 不去自动下载 Python：镜像里的 alpine python3 就是目标解释器
# uv 用 Alpine 仓库的包（apk add uv）：它是 native 到目标平台的二进制，
# 9 个架构都有。官方 ghcr 镜像只发主流平台，且用 --mount from= 挂进来时
# 拿到的是构建机架构的二进制，在 s390x / ppc64le 这类容器里跑不起来。
ENV UV_PYTHON_DOWNLOADS=never
# 为什么走 export + pip install 而不是 uv sync：
# uv.lock 里每个包都记了下载地址（source = { registry = "https://pypi.org/simple" }）
# 与具体的 sdist/wheel URL。`uv sync` 的语义是「从 lockfile 装」，它照着那些 URL 取，
# 不再解析索引——于是 pycurl 只会拿到 PyPI 的 sdist（PyPI 没有它的 musllinux 轮子），
# 当场因为缺 curl-config 编译失败，--extra-index-url 完全用不上。
# `uv export --no-hashes` 产出的只有 `pycurl==7.49.0` 这种版本约束、没有任何 URL，
# 于是安装时按下面的索引重新解析，命中 wheelhouse 里的 musllinux 轮子。
# 版本一致性仍由 lock 保证（export 的版本就是 lock 冻的版本）。
ENV UV_PYTHON=/usr/bin/python3

# 编译期工具：greenlet / markupsafe / tornado / pycryptodome 在部分架构没有 musllinux
# 轮子，必须现编；装完 apk del，不留在运行时镜像里。
#
# 三个 wheelhouse 用 bind mount 挂进来而不是 COPY：COPY 会把整份 wheel 写进镜像层，
# 而 RUN 结束后它们就用完了，镜像里不该有 /w1 /w2 /w3。
#
# 系统包取三个清单的并集（三个仓库各自只列自己需要的），再补上 ddddocr 那层的便利包
# （bash 给 update.sh 用、tzdata 给 zoneinfo、icu-data-en 给 onnxruntime 的 libicu）。
RUN \
    --mount=type=bind,from=a76yyyy/onnxruntime:${ONNXRUNTIME_RELEASE}-wheelhouse,source=/wheels,target=/w1 \
    --mount=type=bind,from=a76yyyy/ddddocr:${DDDDOCR_RELEASE}-wheelhouse,source=/wheels,target=/w2 \
    --mount=type=bind,from=a76yyyy/pycurl:${PYCURL_TAG_PREFIX}${PYCURL_RELEASE}-wheelhouse,source=/wheels,target=/w3 \
    set -eu && \
    { [ -z "$APK_MIRROR" ] || sed -i "s|https://dl-cdn.alpinelinux.org|$APK_MIRROR|g" /etc/apk/repositories; } && \
    apk add --update --no-cache \
        build-base python3-dev linux-headers libffi-dev \
        $(cat /w1/system-packages.txt /w2/system-packages.txt /w3/system-packages.txt | sort -u) \
        bash ca-certificates icu-data-en tzdata uv && \
    uv venv .venv --python /usr/bin/python3 && \
    uv export --frozen --no-hashes --no-emit-project --extra ocr -o /tmp/req.txt && \
    uv pip sync --python .venv/bin/python --no-cache \
        --index-url "${PIP_MIRROR:-https://pypi.org/simple}" \
        --extra-index-url file:///w1/simple \
        --extra-index-url file:///w2/simple \
        --extra-index-url file:///w3/simple \
        /tmp/req.txt && \
    .venv/bin/python -c "import pycurl; \
        assert pycurl.version.startswith('PycURL/7.49.0'), pycurl.version; \
        print('pycurl', pycurl.version)" && \
    apk del build-base python3-dev linux-headers libffi-dev uv && \
    rm -rf /var/cache/apk/*

# 代码直接用构建上下文（.dockerignore 已排除 .git / node_modules 等），
# 不再在构建时从 gitee clone——那会让镜像内容与仓库脱节，且需要把部署私钥打进镜像
COPY . /usr/src/app
RUN chmod +x /usr/src/app/update.sh && ln -sf /usr/src/app/update.sh /bin/update

# venv 里的可执行文件优先
ENV PATH=/usr/src/app/.venv/bin:$PATH

ENV PORT=80
EXPOSE 80/tcp

# timezone
ENV TZ=CST-8

# 添加挂载点
VOLUME ["/usr/src/app/config"]

CMD ["sh","-c","python /usr/src/app/run.py"]
