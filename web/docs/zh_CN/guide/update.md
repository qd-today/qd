# 更新方法

> 操作前请一定要记得备份数据库!!!
>
> 更新后请重启容器或清空浏览器缓存。

## 源码部署更新

``` sh
# 先cd到源码所在目录, 执行命令后重启进程 
wget https://gitee.com/a76yyyy/qiandao/raw/master/update.sh -O ./update.sh && \
sh ./update.sh 
```

## Docker容器部署更新

``` sh
# 先进入容器后台, 执行命令后重启容器 
wget https://gitee.com/a76yyyy/qiandao/raw/master/update.sh -O /usr/src/app/update.sh && \
sh /usr/src/app/update.sh
```

## 强制同步最新源码

``` sh
# 先cd到仓库代码根目录, 执行命令后重启进程 
wget https://gitee.com/a76yyyy/qiandao/raw/master/update.sh -O ./update.sh && \
sh ./update.sh -f
```
