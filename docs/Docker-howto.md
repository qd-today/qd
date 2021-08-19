# Docker部署签到站教程

> **注:**
> 如果你使用的系统已经预装Docker,或者你使用的是Docker容器平台,可以跳过安装Docker步骤  
> 本教程配置后的站点使用的数据库默认为sqlite3  
> 更新镜像时只需要备份容器中的 ./config/database.db 文件即可  
> 将容器中的数据库文件拷贝到当前目录  
> ```
> docker cp qiandao:/usr/src/app/config/database.db .
> ```
> 将备份的数据库拷贝到容器中(当前目录的database.db文件)
> ```
> docker cp database.db qiandao:/usr/src/app/config
> ```
> 建议恢复数据库后立即重启容器,重启方法请见下方 **其他命令**  

源项目地址 [点击访问][1]  

如何创建自己的Docker镜像,可参考本镜像的构建文件 [Dockerfile][3]  

***

### 一、Linux安装Docker  
1. 国内主机安装Docker  
    1. 使用国内镜像安装Docker  
        ```
        curl -sSL https://get.daocloud.io/docker | sh
        ```
    2. 启动Docker服务  
        ```
    	service docker start
        ```
2. 国外主机安装Docker  
	1. 使用官网地址安装Docker  
	    ```
		curl -sSL https://get.docker.com | sh
		```
	2. 启动Docker服务  
	    ```
		service docker start
        ```
3. Centos使用yum安装Docker  
	如果在国内使用该方式,推荐使用阿里云的yum源,配置方法请百度  
	1. 升级现有依赖（建议）  
	    ```
		yum update -y
		```
	2. 安装Docker  
		```
        yum install docker -y
        ```
    3. 启动Docker服务  
        ```
		service docker start
		```
4. **设置Docker服务项开机自启**( **重要** )  
    ```
    systemctl enable docker
    ```

### 二、下载/更新Docker镜像

1. 国内主机拉取/更新镜像  
    ```
	docker pull daocloud.io/a76yyyy/qiandao
	```
2. 国外主机拉取/更新镜像  
	```
    docker pull a76yyyy/qiandao
    ```
3. 更新镜像需要删除并重新创建容器（**需要手动备份数据库文件**）,不删除重新创建容器则依然使用创建时的版本,或手动更新代码!  

### 三、创建容器
1. 说明  
	Docker中容器的名称与ID是唯一的,如果需要重新创建容器,需要先删除之前的容器,见后面其他命令  
	如果在创建容器后,自动启动容器出现问题,可能是端口冲突,你可以选择关闭占用80端口的程序  
	或更改容器开放端口（容器内程序的监听端口制作时已更改为80）  
	```
	docker run -d -p 你指定的端口:80 --name qiandao daocloud.io/a76yyyy/qiandao
	```  
	注:如果你已经创建了容器,请删除后重新创建  
2. 国内主机  
	1. 什么是Volume  
		你可以把Volume理解为一个挂载点，意为将主机中的目录挂载到容器中，这样可以在容器中与主机挂载点的文件交互  
		添加Volume需要添加以下参数  
		-v 主机挂载点:容器挂载点  
		```
		-v /root(建议使用绝对路径):/usr/src/root(建议使用绝对路径)
		```  
		意为将主机中的/root目录 连接到容器中的 /usr/src/root 位置,在容器中复制文件到/usr/src/root中,其会出现在主机的/root目录中
		
	2. **设置容器重启动策略**  
	    重启动策略有以下三种：
        1. 始终重启(可用作开机自启,前提是Docker服务必须开机自启动)
            ```
            --restart=always
            ```
        2. 退出状态非0时重启
            ```
            --restart=on-failure
            ```
            该方式可以指定遇到错误时尝试重启的最大次数,例出错时最大重启5次
            ```
            --restart=on-failure:5
            ```
        3. 不重启(**默认**)
            ```
            --restart=no
            ```
		4. 样例(始终重启--开机时,如果Docker服务项已经启动则自动启动该容器)
		    ```
		    docker run -d -p 80:80 --name qiandao --restart=always daocloud.io/a76yyyy/qiandao
	        ```  
	3. 不需要挂载Volume  
	    ```
		docker run -d -p 80:80 --name qiandao daocloud.io/a76yyyy/qiandao
	    ```  
	4. 需要挂载Volume(在root目录下创建volume,并连接至容器中/usr/src/app/volume位置,也就是代码目录的volume文件夹)  
	    ```
		mkdir -p /root/volume
		docker run -d -p 80:80 --name qiandao -v /root/volume:/usr/src/app/volume daocloud.io/a76yyyy/qiandao
		```  
3. 国外主机  
	1. 不需要挂载Volume  
	    ```
		docker run -d -p 80:80 --name qiandao a76yyyy/qiandao
	    ```  
	2. 需要挂载Volume(在root目录下创建volume,并连接至容器中/usr/src/app/volume位置,也就是代码目录的volume文件夹)  
	    ```
		mkdir -p /root/volume
		docker run -d -p 80:80 --name qiandao -v /root/volume:/usr/src/app/volume a76yyyy/qiandao
		```

### 四、启动容器  
1. 说明  
	首次创建容器后，将自动启动容器
2. 手动启动容器  
	```
    docker start qiandao
    ```

### 五、配置站点管理员  
1. 进入容器管理  
    ```	
    docker exec -it qiandao /bin/bash
    ```
2. 设置站点管理员  
    ```
	python ./chrole.py 注册邮箱(该用户必须已经注册) admin
	```
	例：
	```
	python ./chrole.py 123456@qq.com admin
	```
3. 退出容器管理  
    ```
	exit
	```

### 六、其他命令  
1. 重启容器  
    ```
	docker restart qiandao
	```
2. 关闭容器  
    ```
	docker stop qiandao
	```
3. 删除容器  
    ```
	docker rm -v qiandao
	```
    使用参数 -v 的作用是为了确保删除容器自动创建的Volume
4. 启动docker时自动启动容器  
    ```
	docker update --restart=always qiandao
	```
### 七、站点其他配置  

其他站点配置请参考 [配置说明][2]

[1]:https://github.com/binux/qiandao
[2]:https://gitee.com/a76yyyy/qiandao/blob/master/README.md
[3]:https://gitee.com/a76yyyy/qiandao/blob/master/Dockerfile
