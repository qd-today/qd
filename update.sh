#!/bin/bash
#
# FILE: update.sh
#
# DESCRIPTION: Update QD for Python3
#
# NOTES: This requires GNU getopt.
#        I do not issue any guarantee that this will work for you!
#
# COPYRIGHT: (c) 2021-2023 by a76yyyy
#
# LICENSE: MIT
#
# ORGANIZATION: qd-today (https://github.com/qd-today)
#
# CREATED: 2021-10-28 20:00:00
#
#=======================================================================
_file=$(readlink -f "$0")
_dir=$(dirname "${_file}")
cd "${_dir}" || exit

# Treat unset variables as an error
set -o nounset

__ScriptVersion="2023.06.14"
__ScriptName="update.sh"
source_branch="master"
alpine_mirrors="ustc"

#-----------------------------------------------------------------------
# FUNCTION: usage
# DESCRIPTION:  Display usage information.
#-----------------------------------------------------------------------
usage() {
    cat << EOT

Usage :  ${__ScriptName} [OPTION] ...
  Update QD for Python3 from given options.

Options:
  -h, --help                    Display help message
  -s, --script-version          Display script version
  -m, --mirrors-alpine=ustc        Set Alpine mirrors (default|tsinghua|ustc|tencent|aliyun)
  -u, --update                  Default update method
  -v, --version=TAG_VERSION     Forced Update to the specified tag version
  -f, --force                   Forced version update
  -l, --local                   Display Local version
  -r, --remote                  Display Remote version

Exit status:
  0   if OK,
  !=0 if serious problems.

Example:
  1) Use short options:
    $ sh ${__ScriptName} -v=$(python -c 'import sys, json; print(json.load(open("version.json"))["version"])')

  2) Use long options:
    $ sh ${__ScriptName} --update

Report issues to https://github.com/qd-today/qd

EOT
}   # ----------  end of function usage  ----------

get_localversion() {
    localversion=$(python -c 'import sys, json; print(json.load(open("version.json"))["version"])')
}

update_out_alpine() {
    # 非 Alpine 环境（自带 python）：只用 uv 装依赖，不再维护 requirements.txt
    command -v uv >/dev/null 2>&1 || {
        echo "Error: 需要 uv 才能安装依赖，见 https://docs.astral.sh/uv/"; return 1; }
    install_deps_uv && \
    echo "Info: OCR 与 pycurl 已随镜像提供（latest / ja3 线自带，lite 线不带）"
}

set_alpine_mirrors() {
    echo -e "Info: 当前 Alpine 镜像源: \n$(grep -o 'https://[^ ]*/' /etc/apk/repositories |  awk '!a[$0]++')"
    case "$1" in
        default | =default )
            alpine_mirrors="default"
            echo "Info: 正在设置 Alpine 镜像源为: 默认官方源"
            sed -i 's/mirrors.tuna.tsinghua.edu.cn/dl-cdn.alpinelinux.org/g' /etc/apk/repositories
            sed -i 's/mirrors.ustc.edu.cn/dl-cdn.alpinelinux.org/g' /etc/apk/repositories
            sed -i 's/mirrors.cloud.tencent.com/dl-cdn.alpinelinux.org/g' /etc/apk/repositories
            sed -i 's/mirrors.aliyun.com/dl-cdn.alpinelinux.org/g' /etc/apk/repositories
            echo -e "Info: 设置后的 Alpine 镜像源: \n$(grep -o 'https://[^ ]*/' /etc/apk/repositories |  awk '!a[$0]++')"
            ;;
        tsinghua | =tsinghua )
            alpine_mirrors="tsinghua"
            echo "Info: 正在设置 Alpine 镜像源为: 清华大学源"
            sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories
            sed -i 's/mirrors.ustc.edu.cn/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories
            sed -i 's/mirrors.cloud.tencent.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories
            sed -i 's/mirrors.aliyun.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories
            echo -e "Info: 设置后的 Alpine 镜像源: \n$(grep -o 'https://[^ ]*/' /etc/apk/repositories |  awk '!a[$0]++')"
            ;;
        ustc | =ustc )
            alpine_mirrors="ustc"
            echo "Info: 正在设置 Alpine 镜像源为: 中国科学技术大学源"
            sed -i 's/dl-cdn.alpinelinux.org/mirrors.ustc.edu.cn/g' /etc/apk/repositories
            sed -i 's/mirrors.tuna.tsinghua.edu.cn/mirrors.ustc.edu.cn/g' /etc/apk/repositories
            sed -i 's/mirrors.cloud.tencent.com/mirrors.ustc.edu.cn/g' /etc/apk/repositories
            sed -i 's/mirrors.aliyun.com/mirrors.ustc.edu.cn/g' /etc/apk/repositories
            echo -e "Info: 设置后的 Alpine 镜像源: \n$(grep -o 'https://[^ ]*/' /etc/apk/repositories |  awk '!a[$0]++')"
            ;;
        tencent | =tencent )
            alpine_mirrors="tencent"
            echo "Info: 正在设置 Alpine 镜像源为: 腾讯云源"
            sed -i 's/dl-cdn.alpinelinux.org/mirrors.cloud.tencent.com/g' /etc/apk/repositories
            sed -i 's/mirrors.tuna.tsinghua.edu.cn/mirrors.cloud.tencent.com/g' /etc/apk/repositories
            sed -i 's/mirrors.ustc.edu.cn/mirrors.cloud.tencent.com/g' /etc/apk/repositories
            sed -i 's/mirrors.aliyun.com/mirrors.cloud.tencent.com/g' /etc/apk/repositories
            echo -e "Info: 设置后的 Alpine 镜像源: \n$(grep -o 'https://[^ ]*/' /etc/apk/repositories |  awk '!a[$0]++')"
            ;;
        aliyun | =aliyun )
            alpine_mirrors="aliyun"
            echo "Info: 正在设置 Alpine 镜像源为: 阿里云源"
            sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories
            sed -i 's/mirrors.tuna.tsinghua.edu.cn/mirrors.aliyun.com/g' /etc/apk/repositories
            sed -i 's/mirrors.ustc.edu.cn/mirrors.aliyun.com/g' /etc/apk/repositories
            sed -i 's/mirrors.cloud.tencent.com/mirrors.aliyun.com/g' /etc/apk/repositories
            echo -e "Info: 设置后的 Alpine 镜像源: \n$(grep -o 'https://[^ ]*/' /etc/apk/repositories |  awk '!a[$0]++')"
            ;;
        * )
            echo "Error: 未知的 Alpine 镜像源: $1"
            echo "支持的 Alpine 镜像源: default, tsinghua, ustc, tencent, aliyun"
            exit 1
            ;;
    esac
}

is_musl() {
    # Alpine 是 musl，Debian / Ubuntu 系是 glibc。两者能装的轮子完全不同。
    [ -e /lib/ld-musl-*.so.1 ] 2>/dev/null && return 0
    ldd --version 2>&1 | grep -qi musl
}

# 三仓的发布版本只写在 Dockerfile 的 ARG 里，这里读同一份，
# 让热更新装的 wheel 与镜像构建用的完全一致，不在脚本里维护第二份版本号。
read_release_args() {
    if [ ! -f Dockerfile ]; then
        echo "Error: 找不到 Dockerfile，无法确定依赖版本" >&2
        return 1
    fi
    _pycurl=$(sed -n 's/^ARG PYCURL_RELEASE=//p' Dockerfile | tail -1)
    _pycurl_prefix=$(sed -n 's/^ARG PYCURL_TAG_PREFIX=//p' Dockerfile | tail -1)
    _ddddocr=$(sed -n 's/^ARG DDDDOCR_RELEASE=//p' Dockerfile | tail -1)
    _onnx=$(sed -n 's/^ARG ONNXRUNTIME_RELEASE=//p' Dockerfile | tail -1)
    if [ -z "$_pycurl" ]; then
        echo "Error: Dockerfile 里没有 ARG PYCURL_RELEASE" >&2
        return 1
    fi
    echo "Info: 依赖版本取自 Dockerfile —— pycurl=${_pycurl_prefix}${_pycurl} ddddocr=${_ddddocr:-无} onnxruntime=${_onnx:-无}"
}

install_deps_uv() {
    # 四种形态：
    #   新镜像（容器 + .venv）  -> 镜像自带，热更新只换代码
    #   旧镜像（容器，无 .venv）-> 依赖在系统 python，与新代码不兼容，只能换镜像
    #   Alpine 裸机（musl）     -> apk uv + 本地 wheelhouse（musllinux）
    #   glibc 裸机（Ubuntu 等） -> 官方 uv + uv sync（许多 manylinux 轮子）
    if [ -f /.dockerenv ]; then
        if [ -x .venv/bin/python ]; then
            echo "Info: 依赖由镜像提供（/usr/src/app/.venv），热更新不重装依赖"
            echo "Info: 如需更新依赖版本，请拉取对应 tag 的新镜像"
            return 0
        fi
        echo "Error: 当前镜像没有 .venv，与新代码不兼容。" >&2
        echo "       这是依赖形态变更的边界，热更新无法跨越，请拉取对应 tag 的新镜像。" >&2
        return 1
    fi

    if is_musl; then
        install_deps_alpine
    else
        install_deps_glibc
    fi
}

install_deps_alpine() {
    echo "Info: 检测到 musl（Alpine），使用本地 wheelhouse 安装依赖"
    set_alpine_mirrors "${alpine_mirrors}"

    # 少数纯 Python 包（greenlet / pycryptodome 这类）在部分架构上没有 musllinux
    # 轮子，要现编。编译工具只在裸机场景需要，装完即删。
    apk add --no-cache --virtual .build_deps build-base python3-dev linux-headers libffi-dev \
        || { echo "Error: 安装编译工具失败" >&2; return 1; }
    if [ -x "/usr/bin/python3" ]; then
        ln -sf /usr/bin/python3 /usr/bin/python
        ln -sf /usr/bin/python3 /usr/local/bin/python
    fi

    apk add --no-cache uv || { echo "Error: 安装 uv 失败" >&2; return 1; }

    # 用 uv 的默认位置创建虚拟环境，与镜像里的路径一致（/usr/src/app/.venv）
    uv venv .venv --python python3 || { echo "Error: 创建 .venv 失败" >&2; return 1; }

    # requirements.txt 由 lock 导出，不提交到仓库，避免「lock 改了文件没跟上」
    _req=/tmp/qd-requirements.txt
    uv export --frozen --no-hashes --no-emit-project -o "$_req" \
        || { echo "Error: uv export 失败" >&2; return 1; }

    read_release_args || return 1

    _arch=$(uname -m)
    case "$_arch" in
        arm64) _arch=aarch64 ;;
    esac
    case "$_arch" in
        x86_64|aarch64|riscv64|ppc64le|loongarch64|armv7l|armv6l|i686) ;;
        *) echo "Error: 不支持的架构 $_arch" >&2; return 1 ;;
    esac

    _tmp=$(mktemp -d) || return 1
    _fetch() {
        _url="https://github.com/qd-today/$1/releases/download/$2/$3-wheels-$_arch.tar.gz"
        echo "Info: 下载 $_url"
        wget -q "$_url" -O "$_tmp/$1.tar.gz" || { echo "Error: 下载 $1 失败" >&2; return 1; }
        tar xzf "$_tmp/$1.tar.gz" -C "$_tmp" || { echo "Error: 解压 $1 失败" >&2; return 1; }
    }

    # 这套 wheel 与镜像同批，全部自包含 C 依赖
    _fetch pycurl-docker "${_pycurl_prefix}${_pycurl}" pycurl-docker || { rm -rf "$_tmp"; return 1; }
    # 精简线（lite）的 Dockerfile 没有 OCR 版本参数，跳过
    if [ -n "$_ddddocr" ] && [ -n "$_onnx" ]; then
        _fetch ddddocr-docker "$_ddddocr" ddddocr-docker || { rm -rf "$_tmp"; return 1; }
        _fetch onnxruntime-docker "$_onnx" onnxruntime-docker || { rm -rf "$_tmp"; return 1; }
    fi

    # 先装系统包：清单随 wheelhouse 发布，上层照单安装
    _pkgs=$(cat "$_tmp"/wheels-*/system-packages.txt 2>/dev/null | sort -u | tr '\n' ' ')
    if [ -n "$_pkgs" ]; then
        echo "Info: 安装系统包 $_pkgs"
        apk add --no-cache $_pkgs || { echo "Error: 安装系统包失败" >&2; rm -rf "$_tmp"; return 1; }
    fi

    # 每个 wheelhouse 一个索引，按定义顺序查询；PyPI 只兜底纯 Python 包
    _indexes=""
    for _d in "$_tmp"/wheels-*/simple; do
        [ -d "$_d" ] && _indexes="$_indexes --extra-index-url file://$_d"
    done

    echo "Info: uv pip sync（按 requirements.txt 严格同步）"
    # shellcheck disable=SC2086
    uv pip sync --python .venv/bin/python --no-cache \
        --index-url https://pypi.org/simple $_indexes "$_req"
    _rc=$?
    rm -rf "$_tmp" "$_req"
    apk del .build_deps >/dev/null 2>&1
    rm -rf /var/cache/apk/* /usr/share/man/*
    if [ "$_rc" -ne 0 ]; then
        echo "Error: 依赖安装失败" >&2
        return $_rc
    fi
    return 0
}

install_deps_glibc() {
    echo "Info: 检测到 glibc（Ubuntu / Debian 等），使用官方 uv 与 uv sync"
    if ! command -v uv >/dev/null 2>&1; then
        echo "Info: 安装 uv"
        command -v curl >/dev/null 2>&1 && curl -LsSf https://astral.sh/uv/install.sh | sh \
            || wget -qO- https://astral.sh/uv/install.sh | sh
        # 官方安装脚本把 uv 放在 ~/.local/bin
        [ -x "$HOME/.local/bin/uv" ] && PATH="$HOME/.local/bin:$PATH" && export PATH
        command -v uv >/dev/null 2>&1 || { echo "Error: uv 安装失败" >&2; return 1; }
    fi
    # glibc 上 PyPI 的 manylinux 轮子齐全，不需要我们的 musllinux 那份
    uv sync --frozen || { echo "Error: uv sync 失败" >&2; return 1; }
    echo "Info: 提示——PyPI 的 pycurl 不含 IMPERSONATE 补丁，ja3 线在此形态下不可用"
    return 0
}

# 兼容旧版本：requirements.txt 现在由 uv export 生成，仓库里不再存它。
# 老版本留下的那份会误导 uv sync（它读 lock，不读 requirements.txt），删掉。
cleanup_legacy_files() {
    if [ -f requirements.txt ]; then
        echo "Info: 移除旧版遗留的 requirements.txt（依赖现在由 uv.lock 管理）"
        rm -f requirements.txt
    fi
    if [ -f Pipfile ] || [ -f Pipfile.lock ]; then
        echo "Info: 移除旧版遗留的 Pipfile / Pipfile.lock"
        rm -f Pipfile Pipfile.lock
    fi
}


echo_auto_reload() {
    if [ "$(printenv AUTO_RELOAD)" ] && [ "${AUTO_RELOAD}" == "False" ];then
        echo "Info: 请手动重启容器, 或设置环境变量AUTO_RELOAD以开启热更新功能"
    fi
}


# 镜像用 COPY 构建（不带 .git），此时走 tarball 更新；带 .git 时保持原逻辑
have_git() {
    git rev-parse --is-inside-work-tree >/dev/null 2>&1
}

# 列出远端版本 tag：有 .git 用 git，否则查 gitee API（公共仓库，无需 token）
list_remote_tags() {
    if have_git; then
        git ls-remote --tags origin | grep -o 'refs/tags/[0-9]*' | grep -o '[^\/]*$'
    else
        wget -qO- "https://gitee.com/api/v5/repos/qd-today/qd/tags?per_page=100" \
            | grep -o '"name": *"[0-9][0-9.]*"' | grep -o '[0-9][0-9.]*'
    fi
}

# 无 .git 时的代码更新：下载归档包覆盖代码，config/ 是挂载点不能动
update_tarball() {
    uri="https://gitee.com/qd-today/qd/repository/archive/${remoteversion}.tar.gz"
    tmp=$(mktemp -d)
    echo "Info: 下载 ${uri}"
    if ! wget -qO- "${uri}" | tar xz -C "${tmp}" 2>/dev/null; then
        echo "Error: 下载或解压失败: ${uri}"
        rm -rf "${tmp}"
        return 1
    fi
    src=$(find "${tmp}" -maxdepth 1 -mindepth 1 -type d | head -n 1)
    if [ -z "${src}" ]; then
        echo "Error: 归档内容为空"
        rm -rf "${tmp}"
        return 1
    fi
    # config/ 是 VOLUME 挂载点：既不能删（Resource busy）也不该被归档覆盖，
    # 归档里的 config 只有 .gitkeep，直接丢弃，用户的配置原样保留
    rm -rf "${src}/config"
    cp -a "${src}/." /usr/src/app/
    chmod +x /usr/src/app/update.sh 2>/dev/null || true
    rm -rf "${tmp}"
}

update_git() {
    # 没有 .git 就无法确定版本、无法和 Dockerfile 的 ARG 对齐，
    # 依赖会装成另一套。这种情况直接报错，让用户克隆仓库或换镜像。
    if ! have_git; then
        echo "Error: 当前目录没有 git 仓库，无法更新代码。" >&2
        echo "       请用 git clone 获取源码后再执行本脚本，或直接拉取新镜像。" >&2
        return 1
    fi
    if [ "${remoteversion}" = ${source_branch} ];then
        git fetch --all && \
        git reset --hard origin/"${remoteversion}" && \
        git checkout -f "${remoteversion}" && \
        git pull
    else
        git fetch origin "${remoteversion}" && \
        git reset --hard origin/"${source_branch}" && \
        git pull -t && \
        git checkout -f -b "${remoteversion}" "${remoteversion}"
    fi
}

update() {
    get_localversion
    # 判断是否包含输入参数
    if [ "$#" != 0 ];then
        if [ "$1" = "force" ];then
            # 强制更新
            remoteversion=${source_branch}
            echo -e "Info: 正在强制更新中, 请稍候..."
            update_git && \
            cleanup_legacy_files && \
            install_deps_uv && \
            echo -e "Info: 更新完成! \nInfo: 当前版本: ${remoteversion}" && \
            echo_auto_reload
        else
            if list_remote_tags | grep -q -w "$1"
            then
                remoteversion="$1"
                if [ "$(echo "$localversion" "$remoteversion" | awk '$1>$2 {print 0} $1=<$2 {print 1}')" == 0 ];then
                    # 要求用户手动确认更新至旧版本 (因为旧版本可能存在不兼容的情况)
                    echo -e "Warning: 当前版本: ${localversion} , 旧版本: ${remoteversion}"
                    echo -e "Warning: 旧版本可能导致容器崩溃, 建议直接拉取旧版本容器!"
                    read -r -p $"Warning: 如需继续更新至旧版本, 请确认已备份数据库! [Y/n] " input
                    case $input in
                        [yY][eE][sS]|[yY])
                            # 进入更新流程
                            echo -e "Info: 正在更新中, 请稍候..."
                            update_git && \
                            cleanup_legacy_files && \
                            install_deps_uv && \
                            get_localversion && \
                            echo -e "Info: 更新完成! \nInfo: 当前版本: $localversion" && \
                            echo_auto_reload
                            ;;
                        [nN][oO]|[nN])
                            echo "Info: 已取消更新!"
                            exit 0
                            ;;
                        *)
                            echo "Invalid input..."
                            exit 1
                            ;;
                    esac
                else
                    echo -e "Info: 正在强制切换至指定Tag版本: $1, 请稍候..."
                    update_git && \
                    cleanup_legacy_files && \
                    install_deps_uv && \
                    get_localversion && \
                    echo -e "Info: 更新完成! \nInfo: 当前版本: $localversion" && \
                    echo_auto_reload
                fi
            else
                echo "'$1' is not correct type of tag"
                echo "For available version tags, see 'https://gitee.com/qd-today/qd/tags'"
            fi
        fi
    else
        # 默认更新至最新Tag版本
        remoteversion=$(list_remote_tags | sort -r | head -n 1)
        if [ "$(echo "$localversion" "$remoteversion" | awk '$1>=$2 {print 0} $1<$2 {print 1}')" == 1 ];then
            echo -e "Info: 当前版本: $localversion \nInfo: 新版本: $remoteversion \nInfo: 正在更新中, 请稍候..."
            update_git && \
            cleanup_legacy_files && \
            install_deps_uv && \
            get_localversion && \
            echo -e "Info: 更新完成! \nInfo: 当前版本: $localversion" && \
            echo_auto_reload
        else
            echo "Info: 当前版本: $localversion , 无需更新!"
        fi
    fi
}


if [ $# == 0 ]; then update; exit 0; fi

# parse options:
RET=$(getopt -o hsm:uv:flr \
    --long help,script-version,mirrors-alpine:,update,version:,force,local,remote \
    -n ' * ERROR' -- "$@")

exitcode=$?
if [ ${exitcode} != 0 ] ; then echo "Error: $__ScriptName exited with doing nothing." >&2 ; usage; exit 1 ; fi

# Note the quotes around $RET: they are essential!
eval set -- "$RET"

# set option values
while true; do
    case "$1" in
        -h | --help ) usage; exit 1 ;;

        -s | --script-version ) echo "$(basename "$0") -- version $__ScriptVersion"; exit 1 ;;

        -m | --mirrors-alpine ) set_alpine_mirrors "$2"; shift 2;;

        -u | --update ) update; exit 0 ;;

        -v | --version ) update "$2"; exit 0 ;;

        -f | --force ) update "force"; exit 0 ;;

        -l | --local ) get_localversion; echo "当前版本: ${localversion}"; shift ;;

        -r | --remote ) echo "远程版本: $(git ls-remote --tags origin | grep -o 'refs/tags/[0-9]*' | sort -r | head -n 1 | grep -o '[^\/]*$')"; shift ;;

        -- ) shift; break ;;
        * ) echo "Error: internal error!" ; exit 1 ;;
     esac
done
