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
# 定位脚本自身路径：GNU readlink 支持 -f，macOS 自带的 BSD readlink 不支持
if readlink -f "$0" >/dev/null 2>&1; then
    _file=$(readlink -f "$0")
else
    _file="$(cd "$(dirname "$0")" && pwd -P)/$(basename "$0")"
fi

# 服务目录：脚本不一定就放在 QD 服务目录里（可能被拷到别处执行），
# 所以按下面顺序定位，定位不到才回退到脚本所在目录。
#   1. QD_HOME 环境变量（显式指定，优先级最高）
#   2. 脚本所在目录（其中含 version.json 时）
#   3. 当前工作目录（在其中含 version.json 时）
#   4. 脚本所在目录（兜底）
_script_dir=$(dirname "${_file}")
if [ -n "${QD_HOME:-}" ]; then
    if [ ! -d "${QD_HOME}" ]; then
        echo "Error: QD_HOME 指向的目录不存在: ${QD_HOME}" >&2
        exit 1
    fi
    _dir="${QD_HOME}"
elif [ -f "${_script_dir}/version.json" ]; then
    _dir="${_script_dir}"
elif [ -f "$(pwd)/version.json" ]; then
    _dir=$(pwd)
else
    _dir="${_script_dir}"
fi
cd "${_dir}" || exit
if [ ! -f "${_dir}/version.json" ]; then
    echo "Warn: ${_dir} 下没有 version.json，可能不是 QD 服务目录。" >&2
    echo "      若 update.sh 不在服务目录里，请用 QD_HOME=/path/to/qd 指定服务目录。" >&2
fi

# Treat unset variables as an error
set -o nounset

__ScriptVersion="2023.06.14"
__ScriptName="update.sh"
source_branch="master"

# 镜像源参数。默认全部指向官方，不设置时行为与之前完全一致。
#   PIP_INDEX              pip / uv 的包索引
#   GH_RELEASE_MIRROR      三仓 wheel 的前缀（如 https://ghproxy.example/），空 = 直连
#   UV_PYTHON_INSTALL_MIRROR  uv python install 的来源
#   UV_INSTALL_URL         官方 uv 安装脚本地址（仅 glibc 且本地无 uv 时用）
: "${PIP_INDEX:=https://pypi.org/simple}"
: "${GH_RELEASE_MIRROR:=}"
: "${UV_PYTHON_INSTALL_MIRROR:=}"
: "${UV_INSTALL_URL:=https://astral.sh/uv/install.sh}"

# uv 自己认这两个环境变量，命令里就不用重复传参
export UV_DEFAULT_INDEX="${PIP_INDEX}"
[ -n "${UV_PYTHON_INSTALL_MIRROR}" ] && export UV_PYTHON_INSTALL_MIRROR
alpine_mirrors="ustc"

# 虚拟环境：依赖统一装在 <服务目录>/.venv，与镜像构建时的路径一致
# （镜像里是 /usr/src/app/.venv，裸机部署时是 QD 服务目录）
VENV_DIR="${_dir}/.venv"
VENV_PYTHON="${VENV_DIR}/bin/python"

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

Environment:
  QD_HOME                 QD 服务目录。脚本不在服务目录里时用它指定。
  QD_VENV_PERSIST=1       让脚本把 PATH 提升写进 shell 启动文件（默认只临时提升，不改用户环境）。
  PIP_INDEX               pip / uv 的包索引，如 https://pypi.tuna.tsinghua.edu.cn/simple
  GH_RELEASE_MIRROR       三仓 wheel 的下载前缀，如 https://ghproxy.net/
  UV_PYTHON_INSTALL_MIRROR  uv python install 的来源
  UV_INSTALL_URL          官方 uv 安装脚本地址（仅 glibc 且本地无 uv 时用）

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
    # 解释器优先级：虚拟环境 > python3 > python
    # （Debian 默认只装 python3，没有 python 这个名字）
    _py=""
    if [ -x "${VENV_PYTHON}" ]; then
        _py="${VENV_PYTHON}"
    else
        for _c in python3 python; do
            if command -v "${_c}" >/dev/null 2>&1; then
                _py="${_c}"
                break
            fi
        done
    fi
    if [ -z "${_py}" ]; then
        echo "Error: 找不到 python 解释器" >&2
        return 1
    fi
    localversion=$("${_py}" -c 'import sys, json; print(json.load(open("version.json"))["version"])' 2>/dev/null)
    if [ -z "${localversion}" ]; then
        echo "Error: 读取 ${_dir}/version.json 失败，当前目录可能不是 QD 服务目录。" >&2
        echo "       若 update.sh 不在服务目录里，请用 QD_HOME=/path/to/qd 指定服务目录。" >&2
        return 1
    fi
}

update_out_alpine() {
    # 非 Alpine 环境（自带 python）：只用 uv 装依赖，不再维护 requirements.txt
    command -v uv >/dev/null 2>&1 || {
        echo "Error: 需要 uv 才能安装依赖，见 https://docs.astral.sh/uv/"; return 1; }
    install_deps_uv && \
    echo "Info: OCR 与 pycurl 已随镜像提供（latest / ja3 线自带，lite 线不带）"
}

set_alpine_mirrors() {
    echo -e "Info: 当前 Alpine 镜像源: \n$(grep -o 'https://[^ ]*/' /etc/apk/repositories | awk '!a[$0]++')"

    # 只在这里维护「源名 -> host + 中文名」，下面的替换逻辑是通用的一条正则，
    # 新增镜像源只改这张表，不用再复制四行 sed。
    case "$1" in
        default | =default     ) _host="dl-cdn.alpinelinux.org";     _label="默认官方源" ;;
        tsinghua | =tsinghua   ) _host="mirrors.tuna.tsinghua.edu.cn"; _label="清华大学源" ;;
        ustc | =ustc           ) _host="mirrors.ustc.edu.cn";         _label="中国科学技术大学源" ;;
        tencent | =tencent     ) _host="mirrors.cloud.tencent.com";   _label="腾讯云源" ;;
        aliyun | =aliyun       ) _host="mirrors.aliyun.com";          _label="阿里云源" ;;
        ""                     ) return 0 ;;
        * ) echo "Error: 未知的 Alpine 镜像源 '$1'。可选: default tsinghua ustc tencent aliyun" >&2
            return 1 ;;
    esac

    alpine_mirrors="$1"
    echo "Info: 正在设置 Alpine 镜像源为: ${_label}"
    # 把文件里任何已知源换成目标源，一条正则覆盖全部组合
    sed -i -E "s#https://(dl-cdn\.alpinelinux\.org|mirrors\.(tuna\.tsinghua\.edu\.cn|ustc\.edu\.cn|cloud\.tencent\.com|aliyun\.com))#https://${_host}#g" \
        /etc/apk/repositories
    echo -e "Info: 设置后的 Alpine 镜像源: \n$(grep -o 'https://[^ ]*/' /etc/apk/repositories | awk '!a[$0]++')"
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

#---------------------------------------------------------------------
# FUNCTION: sed_inplace
# DESCRIPTION: 跨平台的 sed 原地替换：BSD sed（macOS 自带）要求 -i 后跟一个
#              空后缀参数，GNU sed 与 busybox sed 则是 -i 无后缀。
#---------------------------------------------------------------------
sed_inplace() {
    if [ "$(uname -s)" = "Darwin" ]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

#---------------------------------------------------------------------
# FUNCTION: venv_path_prepend
# DESCRIPTION: 临时把虚拟环境的 bin 提到 PATH 最前。
#              只影响当前脚本及其子进程，退出后不保留。
#---------------------------------------------------------------------
venv_path_prepend() {
    case ":${PATH}:" in
        *":${VENV_DIR}/bin:"*) ;;
        *) PATH="${VENV_DIR}/bin:${PATH}"; export PATH ;;
    esac
}

#---------------------------------------------------------------------
# FUNCTION: venv_path_persist
# DESCRIPTION: 把 PATH 提升写进 shell 启动文件，让登录 / 交互 shell 自动生效。
#              属于对用户环境的改动，默认不调用，只在 QD_VENV_PERSIST=1 时由
#              declare_venv 触发。写的是可撤销的独立标记块，重复执行幂等。
#              Alpine 的 /etc/profile 会 source /etc/profile.d/*.sh（登录 shell）；
#              bash 交互 shell 读 ~/.bashrc；busybox ash 交互 shell 读 $ENV 指向的文件。
#---------------------------------------------------------------------
venv_path_persist() {
    _tmp=$(mktemp "${TMPDIR:-/tmp}/qd-venv.XXXXXX" 2>/dev/null || mktemp) \
        || { echo "Error: 无法创建临时文件" >&2; return 1; }
    # 先把配置块写进临时文件，再用 sed 替换占位符：
    # heredoc 直接重定向到文件，不嵌在命令替换里，兼容旧版 bash 的解析
    cat > "${_tmp}" << 'EOT'
# BEGIN qd virtualenv (auto-generated by update.sh)
if [ -x "__VENV_DIR__/bin/python" ]; then
    case ":${PATH}:" in
        *":__VENV_DIR__/bin:"*) ;;
        *) PATH="__VENV_DIR__/bin:${PATH}"; export PATH ;;
    esac
    export VIRTUAL_ENV="__VENV_DIR__"
    # busybox ash 的交互 shell 读 $ENV 指向的文件，不读 ~/.ashrc
    if [ -z "${ENV:-}" ] && [ -r "__HOME__/.ashrc" ]; then
        export ENV="__HOME__/.ashrc"
    fi
fi
# END qd virtualenv
EOT
    sed_inplace "s|__VENV_DIR__|${VENV_DIR}|g; s|__HOME__|${HOME:-/root}|g" "${_tmp}"
    _targets="/etc/profile.d/qd-venv.sh ${HOME:-/root}/.profile ${HOME:-/root}/.ashrc ${HOME:-/root}/.bashrc"
    for _t in ${_targets}; do
        _t_dir=$(dirname "${_t}")
        [ -d "${_t_dir}" ] || mkdir -p "${_t_dir}" 2>/dev/null || continue
        # 幂等：先删掉旧的同名块，再追加新块
        if [ -f "${_t}" ] && grep -q "^# BEGIN qd virtualenv" "${_t}" 2>/dev/null; then
            sed_inplace '/^# BEGIN qd virtualenv/,/^# END qd virtualenv/d' "${_t}" 2>/dev/null || true
        fi
        cat "${_tmp}" >> "${_t}" 2>/dev/null && echo "Info: PATH 优先级已写入 ${_t}"
    done
    rm -f "${_tmp}"
}

#---------------------------------------------------------------------
# FUNCTION: in_container
# DESCRIPTION: 判断当前是否在容器里，用于给出不同的 PATH 生效指引。
#---------------------------------------------------------------------
in_container() {
    [ -f /.dockerenv ] || [ -f /run/.containerenv ]
}

#---------------------------------------------------------------------
# FUNCTION: declare_venv
# DESCRIPTION: 声明当前 Python 运行在虚拟环境中，并提升 PATH 中该解释器的优先级。
#              永久生效属于改用户 shell 环境，默认不做，只在 QD_VENV_PERSIST=1
#              时由脚本代写；其余情况只给出指引，由用户自己决定。
#---------------------------------------------------------------------
declare_venv() {
    if [ ! -x "${VENV_PYTHON}" ]; then
        echo "Warn: 未找到虚拟环境解释器: ${VENV_PYTHON}"
        return 1
    fi
    # 声明 + 临时提升（只影响当前脚本及其子进程，脚本退出后不保留）
    export VIRTUAL_ENV="${VENV_DIR}"
    venv_path_prepend
    echo "Info: 当前 Python 运行于虚拟环境: ${VENV_DIR}"
    echo "Info:   解释器: ${VENV_PYTHON} ($("${VENV_PYTHON}" -V 2>&1))"
    echo "Info:   PATH 优先级: ${VENV_DIR}/bin 在本次执行的 PATH 中置顶（脚本退出后不保留）"
    # 永久生效默认不写：改用户的 shell 启动文件是侵入性操作，需显式要求
    if [ "${QD_VENV_PERSIST:-0}" = "1" ]; then
        venv_path_persist
    fi
    echo "Info: 提示: 在当前 shell 里使用该解释器，可执行:"
    echo "      export PATH=\"${VENV_DIR}/bin:\${PATH}\""
    echo "      export VIRTUAL_ENV=\"${VENV_DIR}\""
    echo "      # 或 source ${VENV_DIR}/bin/activate"
    if in_container; then
        echo "Info: 提示: 容器启动命令若是 sh -c \"python run.py\"（非登录 shell，不读启动文件），"
        echo "      请在 compose 里加 environment: PATH=${VENV_DIR}/bin:\$PATH，"
        echo "      或把启动命令改为 ${VENV_PYTHON} run.py"
    else
        echo "Info: 提示: 需要长期生效时，把上面的 export 写进 ~/.bashrc（或 ~/.profile）；"
        echo "      脚本默认不改你的 shell 启动文件，设 QD_VENV_PERSIST=1 可由脚本代写"
        echo "Info: 提示: 若服务由 systemd / supervisor 之类拉起，请在它的启动命令里用"
        echo "      ${VENV_PYTHON} run.py"
    fi
}

install_deps_uv() {
    # 容器与裸机动作一致：按 libc 选依赖来源，不看是否在容器里。
    #   musl（Alpine 容器 / Alpine 裸机 / 旧镜像）-> apk uv + 本地 wheelhouse
    #   glibc（Ubuntu / Debian 裸机）              -> 官方 uv + uv sync
    if is_musl; then
        install_deps_alpine
    else
        install_deps_glibc
    fi
}

# 读当前 Dockerfile 的三仓 ARG，拼成一个可比较的串。
# 依赖装不装由「更新前读一次、更新后再读一次」决定，不落任何状态文件。
deps_stamp() {
    _pycurl=$(sed -n 's/^ARG PYCURL_RELEASE=//p' Dockerfile 2>/dev/null | tail -1)
    _pycurl_prefix=$(sed -n 's/^ARG PYCURL_TAG_PREFIX=//p' Dockerfile 2>/dev/null | tail -1)
    _ddddocr=$(sed -n 's/^ARG DDDDOCR_RELEASE=//p' Dockerfile 2>/dev/null | tail -1)
    _onnx=$(sed -n 's/^ARG ONNXRUNTIME_RELEASE=//p' Dockerfile 2>/dev/null | tail -1)
    echo "${_pycurl_prefix}${_pycurl}|${_ddddocr}|${_onnx}"
}

# glibc 分支的依赖由 uv.lock 决定（不走 wheelhouse），用 lock 的校验和做同样的比对。
# cksum 是 POSIX 命令，Alpine / Debian / macOS 都有。
deps_stamp_lock() {
    if [ -f "${_dir}/uv.lock" ]; then
        cksum "${_dir}/uv.lock" 2>/dev/null | awk '{print $1"-"$2}'
    fi
}

install_deps_alpine() {
    echo "Info: 检测到 musl（Alpine），使用本地 wheelhouse 安装依赖"
    read_release_args || return 1

    # 依赖版本没变就不重装。判断依据是调用方传进来的「更新代码前读到的 ARG」，
    # 与当前 Dockerfile 比——不依赖任何落盘的状态文件。
    # 除了版本没变，还要确认依赖真的装过：空的 .venv（比如刚 python -m venv 建的）
    # 同样满足「版本没变」，跳过就会留下一个没装包的 venv。pycurl 是必装项，用它当标志。
    if [ -f "${VENV_DIR}/pyvenv.cfg" ] && [ -n "${_old_deps_stamp:-}" ] \
        && [ "${_old_deps_stamp}" = "$(deps_stamp)" ] \
        && ls "${VENV_DIR}"/lib/python*/site-packages/pycurl* >/dev/null 2>&1; then
        echo "Info: Dockerfile 的依赖版本未变，跳过下载与安装"
        declare_venv || true
        return 0
    fi

    set_alpine_mirrors "${alpine_mirrors}"

    # 少数纯 Python 包（greenlet / pycryptodome 这类）在部分架构上没有 musllinux
    # 轮子，要现编。编译工具只在裸机场景需要，装完即删。
    apk add --no-cache --virtual .build_deps build-base python3-dev linux-headers libffi-dev \
        || { echo "Error: 安装编译工具失败" >&2; return 1; }
    if [ -x "/usr/bin/python3" ]; then
        ln -sf /usr/bin/python3 /usr/bin/python
        ln -sf /usr/bin/python3 /usr/local/bin/python
    fi

    # uv 从 alpine 3.21 起才进 community 仓库。旧镜像（3.19 那批）走两段兜底：
    #   1. astral.sh 的官方脚本——旧镜像访问不到那个域名（wget exit 4），只能当备选
    #   2. apk add py3-pip + pip install uv——uv 在 PyPI 有 musllinux wheel，最稳
    if ! apk add --no-cache uv 2>/dev/null; then
        echo "Info: apk 没有 uv（老版本 alpine），尝试从 PyPI 安装"
        if ! python3 -m pip --version >/dev/null 2>&1; then
            apk add --no-cache py3-pip >/dev/null 2>&1 \
                || { echo "Error: 装不上 py3-pip" >&2; return 1; }
        fi
        # alpine 的 py3-pip 标了 externally-managed（PEP 668），不加这个参数会被拒
        python3 -m pip install --no-cache-dir --break-system-packages uv \
            --index-url "${PIP_INDEX}" \
            || { echo "Error: pip install uv 失败" >&2; return 1; }
        command -v uv >/dev/null 2>&1 || { echo "Error: uv 不在 PATH 里" >&2; return 1; }
        echo "Info: uv 已通过 pip 安装（$(uv --version 2>&1 | head -1)）"
    fi

    # 用 uv 的默认位置创建虚拟环境，与镜像里的路径一致（/usr/src/app/.venv）
    # 解释器版本由仓库根目录的 .python-version 决定（uv 的默认来源），
    # 版本范围由 pyproject 的 requires-python 约束，脚本不自己解析。
    # 系统解释器不满足时 uv 会按 .python-version 下载一个。
    uv python install || { echo "Error: 安装 Python 失败" >&2; return 1; }
    uv venv "${VENV_DIR}" --allow-existing \
        || { echo "Error: 创建或更新 .venv 失败" >&2; return 1; }

    # requirements.txt 由 lock 导出，不提交到仓库，避免「lock 改了文件没跟上」。
    # OCR 栈在 pyproject 的 optional-dependencies.ocr 里，不带 --extra 就导不出来。
    _req=/tmp/qd-requirements.txt
    _extra=""
    [ -n "$_ddddocr" ] && [ -n "$_onnx" ] && _extra="--extra ocr"
    # shellcheck disable=SC2086
    uv export --frozen --no-hashes --no-emit-project $_extra -o "$_req" \
        || { echo "Error: uv export 失败" >&2; return 1; }


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
        # 每个仓解压到自己的子目录：三个 tar 里的顶层目录都叫 wheels-<arch>，
        # 解压到同一处会互相覆盖，最后只剩一个仓的索引。
        _url="${GH_RELEASE_MIRROR}https://github.com/qd-today/$1/releases/download/$2/$3-wheels-$_arch.tar.gz"
        echo "Info: 下载 $_url"
        mkdir -p "$_tmp/$1"
        wget -q "$_url" -O "$_tmp/$1/pkg.tar.gz" || { echo "Error: 下载 $1 失败" >&2; return 1; }
        tar xzf "$_tmp/$1/pkg.tar.gz" -C "$_tmp/$1" || { echo "Error: 解压 $1 失败" >&2; return 1; }
    }

    # 这套 wheel 与镜像同批，全部自包含 C 依赖
    _fetch pycurl-docker "${_pycurl_prefix}${_pycurl}" pycurl-docker || { rm -rf "$_tmp"; return 1; }
    # 精简线（lite）的 Dockerfile 没有 OCR 版本参数，跳过
    if [ -n "$_ddddocr" ] && [ -n "$_onnx" ]; then
        _fetch ddddocr-docker "$_ddddocr" ddddocr-docker || { rm -rf "$_tmp"; return 1; }
        _fetch onnxruntime-docker "$_onnx" onnxruntime-docker || { rm -rf "$_tmp"; return 1; }
    fi

    # 先装系统包：清单随 wheelhouse 发布，上层照单安装
    _pkgs=$(cat "$_tmp"/*/wheels-*/system-packages.txt 2>/dev/null | sort -u | tr '\n' ' ')
    if [ -n "$_pkgs" ]; then
        echo "Info: 安装系统包 $_pkgs"
        apk add --no-cache $_pkgs || { echo "Error: 安装系统包失败" >&2; rm -rf "$_tmp"; return 1; }
    fi

    # 每个 wheelhouse 一个索引，按定义顺序查询；PyPI 只兜底纯 Python 包
    _indexes=""
    for _d in "$_tmp"/*/wheels-*/simple; do
        [ -d "$_d" ] && _indexes="$_indexes --extra-index-url file://$_d"
    done

    echo "Info: uv pip sync（按 requirements.txt 严格同步）"
    # shellcheck disable=SC2086
    uv pip sync --python "${VENV_PYTHON}" --no-cache \
        --default-index "${PIP_INDEX}" $_indexes "$_req"
    _rc=$?
    rm -rf "$_tmp" "$_req"
    apk del .build_deps >/dev/null 2>&1
    rm -rf /var/cache/apk/* /usr/share/man/*
    if [ "$_rc" -ne 0 ]; then
        echo "Error: 依赖安装失败" >&2
        return $_rc
    fi
    declare_venv || true
    return 0
}

install_deps_glibc() {
    echo "Info: 检测到 glibc（Ubuntu / Debian 等），使用官方 uv 与 uv sync"
    # 依赖由 uv.lock 决定：lock 没变且 venv 已就位就跳过，避免每次重复执行都重装一遍
    if [ -n "${_old_lock_stamp:-}" ] && [ "${_old_lock_stamp}" = "$(deps_stamp_lock)" ] \
        && [ -x "${VENV_PYTHON}" ]; then
        echo "Info: uv.lock 未变，跳过依赖同步"
        declare_venv || true
        return 0
    fi
    if ! command -v uv >/dev/null 2>&1; then
        echo "Info: 安装 uv"
        command -v curl >/dev/null 2>&1 && curl -LsSf "${UV_INSTALL_URL}" | sh \
            || wget -qO- "${UV_INSTALL_URL}" | sh
        # 官方安装脚本把 uv 放在 ~/.local/bin
        [ -x "$HOME/.local/bin/uv" ] && PATH="$HOME/.local/bin:$PATH" && export PATH
        # astral.sh 并不总是可达（实测有连不上的时候），和 musl 分支一样用 pip 兜底
        if ! command -v uv >/dev/null 2>&1; then
            echo "Info: 官方脚本没装上 uv，改用 pip"
            if ! python3 -m pip --version >/dev/null 2>&1; then
                apt-get install -y -qq python3-pip >/dev/null 2>&1 \
                    || { echo "Error: 装不上 python3-pip" >&2; return 1; }
            fi
            python3 -m pip install --no-cache-dir --break-system-packages uv \
                --index-url "${PIP_INDEX}" \
                || { echo "Error: pip install uv 失败" >&2; return 1; }
        fi
        command -v uv >/dev/null 2>&1 || { echo "Error: uv 安装失败" >&2; return 1; }
    fi
    # 与 Alpine 分支一致：解释器看 .python-version，范围看 requires-python，
    # 差别只在依赖来源（glibc 上 PyPI 的 manylinux 轮子齐全）。
    uv python install >/dev/null 2>&1 || true
    uv sync --frozen --extra ocr --default-index "${PIP_INDEX}" \
        || { echo "Error: uv sync 失败" >&2; return 1; }
    echo "Info: 提示——PyPI 的 pycurl 不含 IMPERSONATE 补丁，ja3 线在此形态下不可用"
    declare_venv || true
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
    tmp=$(mktemp -d)
    # gitee 会间歇限流（同一个 URL 刚才成功、这次 502），所以多源重试：
    # GitHub 的 tarball API 优先，回退 gitee；每个源试两次。
    _ok=0
    for _base in \
        "https://api.github.com/repos/qd-today/qd/tarball/${remoteversion}" \
        "https://gitee.com/qd-today/qd/repository/archive/${remoteversion}.tar.gz"; do
        for _try in 1 2; do
            echo "Info: 下载 ${_base}（第 ${_try} 次）"
            if wget -qO- --timeout=120 "${_base}" 2>/dev/null | tar xz -C "${tmp}" 2>/dev/null; then
                _ok=1
                break
            fi
            sleep 3
        done
        [ "$_ok" = "1" ] && break
    done
    if [ "$_ok" != "1" ]; then
        echo "Error: 下载或解压失败: ${remoteversion}" >&2
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
    # 用脚本所在目录而不是写死 /usr/src/app：裸机部署时目录不是这个
    cp -a "${src}/." "${_dir}/"
    chmod +x "${_dir}/update.sh" 2>/dev/null || true
    rm -rf "${tmp}"
}

# remoteversion 可以是分支名、tag 或 commit。commit 用「hex 且能解析成 commit」判定，
# 不能只看长度——tag 也可能长得像 hex。
is_commit() {
    case "$1" in
        *[!0-9a-f]*|"") return 1 ;;
    esac
    [ ${#1} -ge 7 ] && [ ${#1} -le 40 ] || return 1
    # qd 的 tag 是纯数字（如 20261108），也符合 hex 的形式。先排除已知 tag，
    # 否则指定 tag 会被当成 commit 处理，跳过版本比较与降级确认。
    # 不调 git cat-file——镜像里没有 .git，这里必须能离线判断。
    ! list_remote_tags 2>/dev/null | grep -qx "$1"
}

update_git() {
    # 没有 .git 时（镜像就是这种）走归档包：tarball 的 URL 接受任意 ref
    # （tag / commit / branch），与 git 的切换语义等价，只是没有本地历史。
    if ! have_git; then
        update_tarball
        return
    fi
    if [ "${remoteversion}" = ${source_branch} ];then
        git fetch --all && \
        git reset --hard origin/"${remoteversion}" && \
        git checkout -f "${remoteversion}" && \
        git pull
    elif is_commit "${remoteversion}"; then
        # 指定 commit：fetch 后 detached checkout（不建分支，避免和 tag 名冲突）
        git fetch --all && \
        git checkout -f "${remoteversion}"
    else
        git fetch origin "${remoteversion}" && \
        git reset --hard origin/"${source_branch}" && \
        git pull -t && \
        git checkout -f -b "${remoteversion}" "${remoteversion}"
    fi
}

update() {
    get_localversion || exit 1
    # 判断是否包含输入参数
    if [ "$#" != 0 ];then
        if [ "$1" = "force" ];then
            # 强制更新
            remoteversion=${source_branch}
            echo -e "Info: 正在强制更新中, 请稍候..."
            _old_deps_stamp=$(deps_stamp) && _old_lock_stamp=$(deps_stamp_lock) && \
            update_git && \
            cleanup_legacy_files && \
            install_deps_uv && \
            echo -e "Info: 更新完成! \nInfo: 当前版本: ${remoteversion}" && \
            echo_auto_reload
        else
            if list_remote_tags | grep -q -w "$1" || is_commit "$1"
            then
                remoteversion="$1"
                if list_remote_tags | grep -qx "$remoteversion"; then
                    : # tag 路径，走下面的版本比较
                elif is_commit "$remoteversion"; then
                    # 指定 commit：不参与版本比较。commit 没有版本号语义，可能比当前
                    # 新也可能旧，硬套 awk 的数字比较会把它误判成「降级」并要求交互确认。
                    echo -e "Info: 切换到 commit ${remoteversion}, 请稍候..."
                    _old_deps_stamp=$(deps_stamp) && _old_lock_stamp=$(deps_stamp_lock) && \
            update_git && \
                    cleanup_legacy_files && \
                    install_deps_uv && \
                    get_localversion && \
                    echo -e "Info: 更新完成! \nInfo: 当前 commit: ${remoteversion}" && \
                    echo_auto_reload
                elif [ "$(echo "$localversion" "$remoteversion" | awk '$1>$2 {print 0} $1=<$2 {print 1}')" == 0 ];then
                    # 要求用户手动确认更新至旧版本 (因为旧版本可能存在不兼容的情况)
                    echo -e "Warning: 当前版本: ${localversion} , 旧版本: ${remoteversion}"
                    echo -e "Warning: 旧版本可能导致容器崩溃, 建议直接拉取旧版本容器!"
                    read -r -p $"Warning: 如需继续更新至旧版本, 请确认已备份数据库! [Y/n] " input
                    case $input in
                        [yY][eE][sS]|[yY])
                            # 进入更新流程
                            echo -e "Info: 正在更新中, 请稍候..."
                            _old_deps_stamp=$(deps_stamp) && _old_lock_stamp=$(deps_stamp_lock) && \
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
                    _old_deps_stamp=$(deps_stamp) && _old_lock_stamp=$(deps_stamp_lock) && \
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
            _old_deps_stamp=$(deps_stamp) && _old_lock_stamp=$(deps_stamp_lock) && \
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


# 主流程收进函数里，末尾再调用。
# 原因：脚本执行过程中会用 git reset --hard 覆盖自身（代码更新到新版本），
# 而 bash 是逐行读取脚本文件的——文件被换掉后继续按原偏移量读，会执行到
# 错位的代码（实测会重复执行一段逻辑）。函数体在首次解析时就被完整读入
# 内存，之后文件怎么变都不影响本次执行。
main() {
if [ $# == 0 ]; then update || exit 1; exit 0; fi

# parse options:
# 长选项需要 GNU getopt：macOS 自带的是 BSD getopt，不认 --long。
# 装了 gnu-getopt（brew）时优先用 ggetopt；没有的话长选项明确提示，
# 短选项（-f / -l / -m / -v / -u）仍然可用。
# 约定：
#   -o 写成紧跟形式（-ohsm:uv:flr）：BSD getopt 只认这种，GNU / busybox 都认
#   --long 用等号形式（--long=a,b）：busybox getopt 只认这种，GNU 也认
# 选项串直接写死在这里，不用变量拼接：变量展开会让 ' * ' 之类被 glob 展开，
# 把当前目录的文件名当成参数传给 getopt。
_getopt_bin=getopt
command -v ggetopt >/dev/null 2>&1 && _getopt_bin=ggetopt
_getopt_bsd=""
if ! printf '%s\n' "--help" 2>/dev/null | "${_getopt_bin}" -oh --long=help -- >/dev/null 2>&1; then
    # BSD getopt（macOS 自带）：既不认 --long，也不认 -o，
    # optstring 必须直接作为第一个参数。
    _getopt_bsd="yes"
    for _arg in "$@"; do
        case "${_arg}" in
            --*)
                echo "Error: 长选项需要 GNU getopt（macOS 自带的 BSD getopt 不支持）。" >&2
                echo "       可执行 'brew install gnu-getopt' 让 ggetopt 优先于 getopt，" >&2
                echo "       或改用短选项：-f / -l / -m / -v / -u。" >&2
                exit 1
                ;;
        esac
    done
fi
if [ -n "${_getopt_bsd}" ]; then
    # BSD getopt 自己会输出结尾的 --，不能再把 -- 当输入传给它，
    # 否则它会把 -- 当成普通参数排在最前面，选项就匹配不上了。
    RET=$("${_getopt_bin}" hsm:uv:flr "$@")
else
    RET=$("${_getopt_bin}" -ohsm:uv:flr \
        --long=help,script-version,mirrors-alpine:,update,version:,force,local,remote \
        -- "$@")
fi

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

        -u | --update ) update || exit 1; exit 0 ;;

        -v | --version ) update "$2" || exit 1; exit 0 ;;

        -f | --force ) update "force" || exit 1; exit 0 ;;

        -l | --local ) get_localversion || exit 1; echo "当前版本: ${localversion}"; break ;;

        -r | --remote ) echo "远程版本: $(list_remote_tags | sort -r | head -n 1)"; break ;;

        -- ) shift; break ;;
        * ) echo "Error: internal error!" ; exit 1 ;;
     esac
done
}

main "$@"
