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
    pip install -r requirements.txt && \
    echo "如需使用 DdddOCR API, 请确认安装 ddddocr Python模组 (如未安装, 请成功执行以下命令后重启 QD); " && \
    echo "pip3 install ddddocr" && \
    echo "如需使用 PyCurl 功能, 请确认安装 pycurl Python模组 (如未安装, 请成功执行以下命令后重启 QD); " && \
    echo "pip3 install pycurl"
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

update_in_alpine() {
    # 当前版本号低于 20211228 时, 使用国内源并提示 DDDDOCR API 不可用
    if [ "$(echo "${localversion}" | awk '$1>20211228 {print 0} $1<=20211228 {print 1}')" == 1 ];then
        echo "https://dl-cdn.alpinelinux.org/alpine/edge/main" > /etc/apk/repositories
        echo "https://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories
        set_alpine_mirrors "${alpine_mirrors}"
        apk del .python-rundeps
        echo "Info: 如需使用DDDDOCR API, 请重新拉取最新容器 (32位系统暂不支持此API). "
    fi
    # 安装Python3及框架依赖
    echo "https://dl-cdn.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories && \
    set_alpine_mirrors "${alpine_mirrors}" && \
    apk add --update --no-cache openssh-client python3 py3-six py3-markupsafe py3-pycryptodome py3-tornado py3-wrapt \
    py3-packaging py3-greenlet py3-urllib3 py3-cryptography py3-aiosignal py3-async-timeout py3-attrs py3-frozenlist \
    py3-multidict py3-charset-normalizer py3-aiohttp py3-typing-extensions py3-yarl && \
    if [ "$(printenv QIANDAO_LITE)" ] && [ "${QIANDAO_LITE}" = "True" ];then
        echo "Info: QD-Lite will not install ddddocr related components. "
    else
        if [ "$(getconf LONG_BIT)" = "32" ];then
            echo "Info: 32-bit systems do not support ddddocr, so there is no need to install numpy and opencv-python. "
        else
            apk add --no-cache py3-opencv py3-pillow
        fi
    fi && \
    # 安装编译依赖
    apk add --no-cache --virtual .build_deps cmake make perl autoconf g++ automake \
        linux-headers libtool util-linux py3-pip py3-setuptools py3-wheel python3-dev py3-numpy-dev && \
    # 判断是否存在python3
    if [ -x "/usr/bin/python3" ];then
        # 创建软链接
        ln -sf /usr/bin/python3 /usr/bin/python
        ln -sf /usr/bin/python3 /usr/local/bin/python
        # pypi 换源
        sed -i 's/pypi.tuna.tsinghua.edu.cn/mirrors.cloud.tencent.com\/pypi/g' requirements.txt
        # 删除Alpine已有的依赖包
        sed -i '/ddddocr/d' requirements.txt
        sed -i '/packaging/d' requirements.txt
        sed -i '/wrapt/d' requirements.txt
        sed -i '/pycryptodome/d' requirements.txt
        sed -i '/tornado/d' requirements.txt
        sed -i '/MarkupSafe/d' requirements.txt
        sed -i '/pillow/d' requirements.txt
        sed -i '/opencv/d' requirements.txt
        sed -i '/numpy/d' requirements.txt
        sed -i '/greenlet/d' requirements.txt
        sed -i '/urllib3/d' requirements.txt
        sed -i '/cryptography/d' requirements.txt
        sed -i '/aiosignal/d' requirements.txt
        sed -i '/async-timeout/d' requirements.txt
        sed -i '/attrs/d' requirements.txt
        sed -i '/frozenlist/d' requirements.txt
        sed -i '/multidict/d' requirements.txt
        sed -i '/charset-normalizer/d' requirements.txt
        sed -i '/aiohttp/d' requirements.txt
        sed -i '/typing-extensions/d' requirements.txt
        sed -i '/yarl/d' requirements.txt
    fi && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --compile --upgrade pycurl && \
    apk del .build_deps
    rm -rf /var/cache/apk/*
    rm -rf /usr/share/man/*
}

echo_auto_reload() {
    if [ "$(printenv AUTO_RELOAD)" ] && [ "${AUTO_RELOAD}" == "False" ];then
        echo "Info: 请手动重启容器, 或设置环境变量AUTO_RELOAD以开启热更新功能"
    fi
}

update_version() {
    wget https://gitee.com/qd-today/qd/raw/"${remoteversion}"/requirements.txt -O /usr/src/app/requirements.txt && \
    if grep -q -E "Alpine|alpine" /etc/issue
    then
        update_in_alpine
    else
        update_out_alpine
    fi
}

update_git() {
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
            if git ls-remote --tags origin | grep -o 'refs/tags/[0-9]*' | grep -o '[^\/]*$' | grep -q -w "$1"
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
        remoteversion=$(git ls-remote --tags origin | grep -o 'refs/tags/[0-9]*' | sort -r | head -n 1 | grep -o '[^\/]*$')
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
