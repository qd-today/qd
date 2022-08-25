#!/bin/bash
#
# FILE: update.sh
#
# DESCRIPTION: Update QianDao for Python3 
#
# NOTES: This requires GNU getopt.
#        I do not issue any guarantee that this will work for you!
#
# COPYRIGHT: (c) 2021-2022 by a76yyyy
#
# LICENSE: MIT
#
# ORGANIZATION: qiandao-today (https://github.com/qiandao-today)
#
# CREATED: 2021-10-28 20:00:00
#
#=======================================================================
_file=$(readlink -f $0)
_dir=$(dirname $_file)
cd $_dir
AUTO_RELOAD=$AUTO_RELOAD

# Treat unset variables as an error
set -o nounset

__ScriptVersion="2022.08.24"
__ScriptName="update.sh"


#-----------------------------------------------------------------------
# FUNCTION: usage
# DESCRIPTION:  Display usage information.
#-----------------------------------------------------------------------
usage() {
    cat << EOT

Usage :  ${__ScriptName} [OPTION] ...
  Update QianDao for Python3 from given options.

Options:
  -h, --help                    Display help message
  -s, --script-version          Display script version
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
    $ sh $__ScriptName -v=$(python -c 'import sys, json; print(json.load(open("version.json"))["version"])')

  2) Use long options:
    $ sh $__ScriptName --update

Report issues to https://github.com/qiandao-today/qiandao

EOT
}   # ----------  end of function usage  ----------

update() {
    localversion=$(python -c 'import sys, json; print(json.load(open("version.json"))["version"])')
    remoteversion=$(git ls-remote --tags origin | grep -o 'refs/tags/[0-9]*' | sort -r | head -n 1 | grep -o '[^\/]*$')
    if [ $(echo $localversion $remoteversion | awk '$1>=$2 {print 0} $1<$2 {print 1}') == 1 ];then
        echo -e "Info: 当前版本: $localversion \nInfo: 新版本: $remoteversion \nInfo: 正在更新中, 请稍候..."
        wget https://gitee.com/a76yyyy/qiandao/raw/$remoteversion/requirements.txt -O /usr/src/app/requirements.txt && \
        [[ -z $(file /bin/busybox | grep -i "musl") ]] && {\
            pip install -r requirements.txt && \
            echo "如需使用DdddOCR API, 请确认安装 ddddocr Python模组 (如未安装, 请成功执行以下命令后重启qiandao); " && \
            echo "pip3 install ddddocr" && \
            echo "如需使用PyCurl 功能, 请确认安装 pycurl Python模组 (如未安装, 请成功执行以下命令后重启qiandao); " && \
            echo "pip3 install pycurl" ;\
        } || { \
            if [ $(echo $localversion | awk '$1>20211228 {print 0} $1<=20211228 {print 1}') == 1 ];then
                echo "https://mirrors.ustc.edu.cn/alpine/edge/main" > /etc/apk/repositories 
                echo "https://mirrors.ustc.edu.cn/alpine/edge/community" >> /etc/apk/repositories 
                apk del .python-rundeps  
                echo "Info: 如需使用DDDDOCR API, 请重新拉取最新容器 (32位系统暂不支持此API). "
            fi
            apk add --update --no-cache python3 py3-pip py3-setuptools py3-wheel python3-dev py3-markupsafe py3-pycryptodome py3-tornado py3-wrapt py3-packaging py3-greenlet && \
            if [ $(printenv QIANDAO_LITE) ] && [ "$QIANDAO_LITE" = "True" ];then
                echo "Info: Qiandao-Lite will not install ddddocr related components. "
            else
                [[ $(getconf LONG_BIT) = "32" ]] && \
                    echo "Info: 32-bit systems do not support ddddocr, so there is no need to install numpy and opencv-python. " || \
                    apk add --update --no-cache py3-numpy-dev py3-opencv py3-pillow 
            fi && \
            apk add --no-cache --virtual .build_deps cmake make perl autoconf g++ automake \
                linux-headers libtool util-linux 
            if [ -n $(ls /usr/bin | grep -w "python3$") ];then
                ls /usr/bin | grep -w "python3$"
                ln -sf /usr/bin/python3 /usr/bin/python 
                ln -sf /usr/bin/python3 /usr/local/bin/python
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
            fi
            pip install --no-cache-dir -r requirements.txt 
            pip install --no-cache-dir --compile --upgrade pycurl 
            apk del .build_deps 
            rm -rf /var/cache/apk/* 
            rm -rf /usr/share/man/*
        } && \
        git fetch --all && \
        git reset --hard origin/master && \
        git checkout master && \
        git pull
    else
        echo "Info: 当前版本: $localversion , 无需更新!"
    fi
    if [ $(printenv AUTO_RELOAD) ] && [ "$AUTO_RELOAD" == "False" ];then
        echo "Info: 请手动重启容器, 或设置环境变量AUTO_RELOAD以开启热更新功能"
    fi
}

force_update() {
    localversion=$(python -c 'import sys, json; print(json.load(open("version.json"))["version"])')
    remoteversion=$(git ls-remote --tags origin | grep -o 'refs/tags/[0-9]*' | sort -r | head -n 1 | grep -o '[^\/]*$')
    echo -e "Info: 正在强制更新中, 请稍候..."
    wget https://gitee.com/a76yyyy/qiandao/raw/master/requirements.txt -O /usr/src/app/requirements.txt && \
    [[ -z $(file /bin/busybox | grep -i "musl") ]] && {\
        pip install -r requirements.txt && \
        echo "如需使用DdddOCR API, 请确认安装 ddddocr Python模组 (如未安装, 请成功执行以下命令后重启qiandao); " && \
        echo "pip3 install ddddocr" && \
        echo "如需使用PyCurl 功能, 请确认安装 pycurl Python模组 (如未安装, 请成功执行以下命令后重启qiandao); " && \
        echo "pip3 install pycurl" ;\
    } || { \
        if [ $(echo $localversion | awk '$1>20211228 {print 0} $1<=20211228 {print 1}') == 1 ];then
            echo "https://mirrors.ustc.edu.cn/alpine/edge/main" > /etc/apk/repositories 
            echo "https://mirrors.ustc.edu.cn/alpine/edge/community" >> /etc/apk/repositories 
            apk del .python-rundeps  
            echo "Info: 如需使用DDDDOCR API, 请重新拉取最新容器 (32位系统暂不支持此API). "
        fi
        apk add --update --no-cache python3 py3-pip py3-setuptools py3-wheel python3-dev py3-markupsafe py3-pycryptodome py3-tornado py3-wrapt py3-packaging py3-greenlet && \
        if [ $(printenv QIANDAO_LITE) ] && [ "$QIANDAO_LITE" = "True" ];then
            echo "Info: Qiandao-Lite will not install ddddocr related components. "
        else
            [[ $(getconf LONG_BIT) = "32" ]] && \
                echo "Info: 32-bit systems do not support ddddocr, so there is no need to install numpy and opencv-python. " || \
                apk add --update --no-cache py3-numpy-dev py3-opencv py3-pillow 
        fi && \
        apk add --no-cache --virtual .build_deps cmake make perl autoconf g++ automake \
            linux-headers libtool util-linux 
        if [ -n $(ls /usr/bin | grep -w "python3$") ];then
            ls /usr/bin | grep -w "python3$"
            ln -sf /usr/bin/python3 /usr/bin/python 
            ln -sf /usr/bin/python3 /usr/local/bin/python
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
        fi
        pip install --no-cache-dir -r requirements.txt 
        pip install --no-cache-dir --compile --upgrade pycurl 
        apk del .build_deps 
        rm -rf /var/cache/apk/* 
        rm -rf /usr/share/man/*
    } && \
    git fetch --all && \
    git reset --hard origin/master && \
    git checkout master && \
    git pull
    if [ $(printenv AUTO_RELOAD) ] && [ "$AUTO_RELOAD" == "False" ];then
        echo "Info: 请手动重启容器, 或设置环境变量AUTO_RELOAD以开启热更新功能"
    fi
}

update_version() {
    echo -e "Info: 正在强制切换至指定Tag版本: $1, 请稍候..."
    wget https://gitee.com/a76yyyy/qiandao/raw/$1/requirements.txt -O /usr/src/app/requirements.txt && \
    [[ -z $(file /bin/busybox | grep -i "musl") ]] && {\
        pip install -r requirements.txt && \
        echo "如需使用DdddOCR API, 请确认安装 ddddocr Python模组 (如未安装, 请成功执行以下命令后重启qiandao); " && \
        echo "pip3 install ddddocr" && \
        echo "如需使用PyCurl 功能, 请确认安装 pycurl Python模组 (如未安装, 请成功执行以下命令后重启qiandao); " && \
        echo "pip3 install pycurl" ;\
    } || { \
        if [ $(echo $localversion | awk '$1>20211228 {print 0} $1<=20211228 {print 1}') == 1 ];then
            echo "https://mirrors.ustc.edu.cn/alpine/edge/main" > /etc/apk/repositories 
            echo "https://mirrors.ustc.edu.cn/alpine/edge/community" >> /etc/apk/repositories 
            apk del .python-rundeps  
            echo "Info: 如需使用DDDDOCR API, 请重新拉取最新容器 (32位系统暂不支持此API). "
        fi
        apk add --update --no-cache python3 py3-pip py3-setuptools py3-wheel python3-dev py3-markupsafe py3-pycryptodome py3-tornado py3-wrapt py3-packaging py3-greenlet && \
        if [ $(printenv QIANDAO_LITE) ] && [ "$QIANDAO_LITE" = "True" ];then
            echo "Info: Qiandao-Lite will not install ddddocr related components. "
        else
            [[ $(getconf LONG_BIT) = "32" ]] && \
                echo "Info: 32-bit systems do not support ddddocr, so there is no need to install numpy and opencv-python. " || \
                apk add --update --no-cache py3-numpy-dev py3-opencv py3-pillow 
        fi && \
        apk add --no-cache --virtual .build_deps cmake make perl autoconf g++ automake \
            linux-headers libtool util-linux 
        if [ -n $(ls /usr/bin | grep -w "python3$") ];then
            ls /usr/bin | grep -w "python3$"
            ln -sf /usr/bin/python3 /usr/bin/python 
            ln -sf /usr/bin/python3 /usr/local/bin/python
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
        fi
        pip install --no-cache-dir -r requirements.txt 
        pip install --no-cache-dir --compile --upgrade pycurl 
        apk del .build_deps 
        rm -rf /var/cache/apk/* 
        rm -rf /usr/share/man/*
    } && \
    git fetch --all && \
    git checkout -f $1
    if [ $(printenv AUTO_RELOAD) ] && [ "$AUTO_RELOAD" == "False" ];then
        echo "Info: 请手动重启容器, 或设置环境变量AUTO_RELOAD以开启热更新功能"
    fi
}


if [ $# == 0 ]; then update; exit 0; fi

# parse options:
RET=`getopt -o hsuv:flr \
    --long help,script-version,update,version:,force,local,remote \
    -n ' * ERROR' -- "$@"`

if [ $? != 0 ] ; then echo "Error: $__ScriptName exited with doing nothing." >&2 ; exit 1 ; fi

# Note the quotes around $RET: they are essential!
eval set -- "$RET"

# set option values
while true; do
    case "$1" in
        -h | --help ) usage; exit 1 ;;
        -s | --script-version ) echo "$(basename $0) -- version $__ScriptVersion"; exit 1 ;;

        -u | --update ) update; exit 0 ;;

        -v | --version ) echo "$2" | grep [^0-9] >/dev/null && echo "'$2' is not correct type of tag" || update_version $2; exit 0 ;;

        -f | --force ) force_update; exit 0 ;;

        -l | --local ) echo "当前版本: $(python -c 'import sys, json; print(json.load(open("version.json"))["version"])')"; shift ;;

        -r | --remote ) echo "远程版本: $(git ls-remote --tags origin | grep -o 'refs/tags/[0-9]*' | sort -r | head -n 1 | grep -o '[^\/]*$')"; shift ;;

        -- ) shift; break ;;
        * ) echo "Error: internal error!" ; exit 1 ;;
     esac
done

# # remaining argument
# for arg do
#     # method
# done
