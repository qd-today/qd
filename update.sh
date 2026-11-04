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

install_deps_uv() {
    # 四种形态，各自的依赖来源不同：
    #   新镜像（容器 + /opt/venv） -> 镜像自带，热更新只换代码
    #   旧镜像（容器，无 /opt/venv） -> 依赖装在系统 python，与新代码不兼容，只能换镜像
    #   Alpine 裸机（musl）        -> GitHub Release 的 musllinux 轮子
    #   Ubuntu / Debian 裸机（glibc）-> PyPI 的 manylinux 轮子
    if [ -f /.dockerenv ]; then
        if [ -x /opt/venv/bin/python ]; then
            echo "Info: 依赖由镜像提供（wheelhouse -> /opt/venv），热更新不重装依赖"
            echo "Info: 如需更新依赖版本，请拉取对应 tag 的新镜像"
            return 0
        fi
        echo "Error: 当前镜像没有 /opt/venv，与新代码不兼容。" >&2
        echo "       这是依赖形态变更的边界，热更新无法跨越，请拉取对应 tag 的新镜像。" >&2
        return 1
    fi

    if is_musl; then
        install_deps_from_release
    else
        install_deps_from_pypi
    fi
}

install_deps_from_pypi() {
    # glibc（Ubuntu / Debian 等）：PyPI 的 manylinux 轮子齐全，不需要用我们自编的
    # musllinux 轮子。注意 pycurl——PyPI 版没有 IMPERSONATE 补丁，这条路上 ja3 线
    # 装不出来，需要指纹伪装请用 Alpine 或容器部署。
    if ! command -v uv >/dev/null 2>&1; then
        echo "Error: 需要 uv，见 https://docs.astral.sh/uv/" >&2
        return 1
    fi
    echo "Info: 检测到 glibc，从 PyPI 安装依赖"
    _req=$(mktemp) || return 1
    if uv export --frozen --no-hashes --no-emit-project -o "$_req" >/dev/null 2>&1; then
        # shellcheck disable=SC2086
        uv pip install --system --break-system-packages --no-cache \
            --index-url https://pypi.org/simple -r "$_req"
        _rc=$?
    else
        # shellcheck disable=SC2086
        uv pip install --system --break-system-packages --no-cache \
            --index-url https://pypi.org/simple pycurl ddddocr onnxruntime
        _rc=$?
    fi
    rm -f "$_req"
    if [ "$_rc" -ne 0 ]; then
        echo "Error: 依赖安装失败" >&2
        return $_rc
    fi
    echo "Info: 提示——PyPI 的 pycurl 不含 IMPERSONATE 补丁，ja3 线在此形态下不可用"
    return 0
}

install_deps_from_release() {
    # 与 pyproject.toml / uv.lock 同批发布的三个仓库版本；升级依赖时改这里
    _onnx_release=1.24.4
    _ddddocr_release=1.6.1
    _pycurl_release=2.0.0

    _arch=$(uname -m)
    case "$_arch" in
        arm64) _arch=aarch64 ;;   # macOS 报 arm64，Alpine 报 aarch64
    esac
    case "$_arch" in
        x86_64|aarch64|riscv64|ppc64le|loongarch64|armv7l|armv6l|i686) ;;
        *) echo "Error: 不支持的架构 $_arch" >&2; return 1 ;;
    esac

    _tmp=$(mktemp -d) || return 1
    _fetch() {
        _url="https://github.com/qd-today/$1/releases/download/$2/$3-wheels-$_arch.tar.gz"
        echo "Info: 下载 $_url"
        wget -q "$_url" -O "$_tmp/$1.tar.gz" || return 1
        tar xzf "$_tmp/$1.tar.gz" -C "$_tmp" || return 1
    }

    echo "Info: 架构 $_arch，pycurl=$_pycurl_release ddddocr=$_ddddocr_release onnxruntime=$_onnx_release"
    _fetch pycurl-docker "$_pycurl_release" pycurl-docker || { rm -rf "$_tmp"; return 1; }

    _indexes="--extra-index-url file://$_tmp/wheels-$_arch/simple"
    if [ "${QD_NO_OCR:-0}" != "1" ]; then
        _fetch ddddocr-docker "$_ddddocr_release" ddddocr-docker || { rm -rf "$_tmp"; return 1; }
        _fetch onnxruntime-docker "$_onnx_release" onnxruntime-docker || { rm -rf "$_tmp"; return 1; }
        for _d in "$_tmp"/wheels-*/simple; do
            [ "$_d" = "$_tmp/wheels-$_arch/simple" ] && continue
            _indexes="$_indexes --extra-index-url file://$_d"
        done
    fi

    # wheelhouse 里的 wheel 自包含 C 依赖，但仍要这几个系统包（清单随 wheelhouse 发布）
    _pkgs=$(cat "$_tmp"/wheels-*/system-packages.txt 2>/dev/null | sort -u | tr '\n' ' ')
    if [ -n "$_pkgs" ]; then
        echo "Info: 安装系统包 $_pkgs"
        apk add --no-cache $_pkgs || { rm -rf "$_tmp"; return 1; }
    fi

    if ! command -v uv >/dev/null 2>&1; then
        echo "Error: 需要 uv，见 https://docs.astral.sh/uv/" >&2
        rm -rf "$_tmp"
        return 1
    fi

    _req="$_tmp/req.txt"
    if uv export --frozen --no-hashes --no-emit-project -o "$_req" >/dev/null 2>&1; then
        echo "Info: 按 uv.lock 安装依赖"
        # shellcheck disable=SC2086
        uv pip install --system --break-system-packages --no-cache \
            --index-url https://pypi.org/simple $_indexes -r "$_req"
    else
        echo "Info: 未在项目目录，按包名安装依赖"
        # shellcheck disable=SC2086
        uv pip install --system --break-system-packages --no-cache \
            --index-url https://pypi.org/simple $_indexes pycurl ddddocr onnxruntime
    fi
    _rc=$?
    rm -rf "$_tmp"
    return $_rc
}

update_in_alpine() {
    # 当前版本号低于 20211228 时, 使用国内源并提示 DDDDOCR API 不可用
    if [ "$(echo "${localversion}" | awk '$1>20211228 {print 0} $1<=20211228 {print 1}')" == 1 ];then
        echo "https://dl-cdn.alpinelinux.org/alpine/edge/main" > /etc/apk/repositories
        echo "https://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories
        set_alpine_mirrors "${alpine_mirrors}"
        apk del .python-rundeps
        echo "Info: 如需使用DDDDOCR API, 请重新拉取最新容器 (32位系统暂不支持此API). "
    fi

    set_alpine_mirrors "${alpine_mirrors}"

    # 编译工具用完即删：锁里 greenlet / pycryptodome 这类在没有 musllinux 轮子的架构上要现编
    apk add --no-cache --virtual .build_deps build-base python3-dev linux-headers libffi-dev

    if [ -x "/usr/bin/python3" ]; then
        ln -sf /usr/bin/python3 /usr/bin/python
        ln -sf /usr/bin/python3 /usr/local/bin/python
    fi

    install_deps_uv

    apk del .build_deps
    rm -rf /var/cache/apk/* /usr/share/man/* /tmp/qd-req.txt /tmp/qd-req.install.txt
}

echo_auto_reload() {
    if [ "$(printenv AUTO_RELOAD)" ] && [ "${AUTO_RELOAD}" == "False" ];then
        echo "Info: 请手动重启容器, 或设置环境变量AUTO_RELOAD以开启热更新功能"
    fi
}

update_version() {
    # pyproject.toml 与 uv.lock 随归档包一起下来，不再单独拉 requirements.txt
    if grep -q -E "Alpine|alpine" /etc/issue
    then
        update_in_alpine
    else
        update_out_alpine
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
    if ! have_git; then
        update_tarball
        return
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
            update_version && \
            update_git && \
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
                            update_version && \
                            update_git && \
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
                    update_version && \
                    update_git && \
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
            update_version "${remoteversion}" && \
            update_git && \
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
