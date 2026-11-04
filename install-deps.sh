#!/bin/sh
# 在裸 Alpine 上为 QD 安装 Python 依赖。
#
# 容器部署不需要跑这个——镜像里已经装好了。这个脚本只服务「源码部署在 Alpine 上」
# 的场景：那里拿不到 wheelhouse 镜像（没有 docker），只能从三个仓库的 GitHub Release
# 取预编译的 musllinux 轮子。
#
#   sh install-deps.sh              # 完整版（含验证码识别）
#   QD_NO_OCR=1 sh install-deps.sh  # 精简版，少装两个 wheelhouse
set -eu

# 与 pyproject.toml / uv.lock 同批发布的三个仓库版本。
# 升级依赖时改这里，并确认 uv.lock 里的包版本与这三个 Release 里的 wheel 一致。
ONNX_RELEASE=1.24.4
DDDDOCR_RELEASE=1.6.1
PYCURL_RELEASE=2.0.0

arch=$(uname -m)
# macOS 报 arm64，Alpine 报 aarch64；Release 资产用的是后者
[ "$arch" = "arm64" ] && arch=aarch64
case "$arch" in
    x86_64|aarch64|arm64|riscv64|ppc64le|loongarch64|armv7l|armv6l|i686) ;;
    *) echo "Error: 不支持的架构 $arch" >&2; exit 1 ;;
esac

echo "Info: 架构 $arch，依赖版本 pycurl=$PYCURL_RELEASE ddddocr=$DDDDOCR_RELEASE onnxruntime=$ONNX_RELEASE"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

fetch() {
    repo=$1; tag=$2; name=$3
    url="https://github.com/qd-today/$repo/releases/download/$tag/$name-wheels-$arch.tar.gz"
    echo "Info: 下载 $url"
    wget -q "$url" -O "$tmp/$repo.tar.gz"
    tar xzf "$tmp/$repo.tar.gz" -C "$tmp"
}

# pycurl 是一定要的；OCR 两个按需
fetch pycurl-docker "$PYCURL_RELEASE" pycurl-docker
indexes="--extra-index-url file://$tmp/wheels-$arch/simple"

if [ "${QD_NO_OCR:-0}" != "1" ]; then
    fetch ddddocr-docker "$DDDDOCR_RELEASE" ddddocr-docker
    fetch onnxruntime-docker "$ONNX_RELEASE" onnxruntime-docker
    # 三个 wheelhouse 各挂一个索引，顺序即优先级
    indexes="--extra-index-url file://$tmp/wheels-$arch/simple"
    for d in "$tmp"/wheels-*/simple; do
        [ "$d" = "$tmp/wheels-$arch/simple" ] && continue
        indexes="$indexes --extra-index-url file://$d"
    done
fi

# wheelhouse 里的 wheel 自包含 C 依赖，但仍需要这几个系统包（清单随 wheelhouse 发布）
pkgs=$(cat "$tmp"/wheels-*/system-packages.txt 2>/dev/null | sort -u | tr '\n' ' ')
if [ -n "$pkgs" ]; then
    echo "Info: 安装系统包 $pkgs"
    apk add --no-cache $pkgs
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: 需要 uv，见 https://docs.astral.sh/uv/" >&2
    exit 1
fi

echo "Info: 用 uv 安装依赖"
# 优先用 uv.lock 的精确版本；不在项目目录时退回按包名装（PyPI 兜底纯 Python 依赖）
req="$tmp/req.txt"
if uv export --frozen --no-hashes --no-emit-project -o "$req" >/dev/null 2>&1; then
    echo "Info: 按 uv.lock 安装"
    # shellcheck disable=SC2086
    uv pip install --system --break-system-packages --no-cache \
        --index-url https://pypi.org/simple \
        $indexes -r "$req"
else
    echo "Info: 未在项目目录，按包名安装"
    # shellcheck disable=SC2086
    uv pip install --system --break-system-packages --no-cache \
        --index-url https://pypi.org/simple \
        $indexes pycurl ddddocr onnxruntime
fi

echo "Info: 完成"
