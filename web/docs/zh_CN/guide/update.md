# 更新方法

> 操作前请一定要记得备份数据库!!!
>
> 更新后请重启容器或清空浏览器缓存。

## 源码部署更新

``` sh
# 先 cd 到源码所在目录, 执行命令后重启进程
wget https://gitee.com/qd-today/qd/raw/master/update.sh -O ./update.sh && \
sh ./update.sh
```

## Docker Compose 部署更新

``` sh
# 先 cd 到 docker-compose.yml 所在目录, 执行命令后重启容器
docker compose pull && \
docker compose up -d
```

## Docker 容器部署更新

``` sh
# 先进入容器后台, 执行命令后重启容器
# docker exec -it 容器名 /bin/sh
wget https://gitee.com/qd-today/qd/raw/master/update.sh -O /usr/src/app/update.sh && \
sh /usr/src/app/update.sh
```

## 强制同步最新源码

``` sh
# 先 cd 到仓库代码根目录, 执行命令后重启进程
wget https://gitee.com/qd-today/qd/raw/master/update.sh -O ./update.sh && \
sh ./update.sh -f
```
