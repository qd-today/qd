# Deployment

## Docker Container Deployment

Docker Container Deployment is the easiest way to deploy QD.

> Please always remember to back up your database before updating or redeploying.

### Container

**DockerHub URL** : [https://hub.docker.com/r/a76yyyy/qiandao](https://hub.docker.com/r/a76yyyy/qiandao)

### Deploy Method

#### 1. Docker Compose (Recommend)

``` sh
# Create and switch to the QD directory.
mkdir -p $(pwd)/qiandao/config && cd $(pwd)/qiandao
# Download docker-compose.yml
wget https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/docker-compose.yml
# Modify the configuration environment variables according to the requirements and configuration description
vi ./docker-compose.yml
# Execute Docker Compose command
docker-compose up -d
```

> See [Configuration](#configuration-environment-variables) below for configuration description  
>
> If you don't need `OCR` or `hard disk space is not larger than 600M`, please use **`a76yyyy/qiandao:lite-latest`** image, **this image only removes OCR related functions, other than the mainline version to keep consistent**.
>
> **Please don't use AliCloud image source to pull Docker container, it will not pull the latest image.**

#### 2. Docker Run

``` sh
docker run -d --name qiandao -p 8923:80 -v $(pwd)/qiandao/config:/usr/src/app/config a76yyyy/qiandao
```

Try this command if you cannot connect to the external network inside the container:

``` sh
# Create container using Host network mode, port: 8923
docker run -d --name qiandao --env PORT=8923 --net=host -v $(pwd)/qiandao/config:/usr/src/app/config a76yyyy/qiandao
```

> Please note that after creating a container with this command, please change the api request of `http://localhost/` form in the template to `api://` or `http://localhost:8923/` manually in order to complete the related API request properly.
>
> **Do not run both old and new versions of QD framework, or map different running QD container databases to the same file.**

## Source Code Deployment

1. **Version >= python3.8**

   ``` sh
   # Please cd to the root of the framework source code first
   pip3 install -r requirements.txt
   ```

2. **Modify the configuration**

   ``` sh
   # Execute the following command to copy the configuration file
   # Modifying the content of the local_config.py file is not affected by updating the source code through git
   cp config.py local_config.py
   # Modify the configuration environment variables according to the requirements and configuration description
   vi local_config.py
   ```

3. **Run**

   ``` sh
   python ./run.py
   ```

4. **Access**

   ``` sh
   # Access the web page
   http://localhost:8923/
   ```

   > If you are using the source code deployment method, please change the api request of `http://localhost/` form in the template to `api://` or `http://localhost:8923/` manually in order to complete the related API request properly.
   >
   > Templates need to be published to be displayed in "Public Templates", and you need admin rights to approve them in "My Publish Requests".

## Configure administrators

``` sh
python ./chrole.py your@email.address admin
```

> The first registered user is the administrator by default, you need to log out and then login to get full administrator rights

## Configuration Environment Variables

|variable name|required|default value|description|
|:-: | :-: | :-: | :-:|
|BIND|No|0.0.0.0|Listening address|
|PORT|No|8923|Listening port|
|QIANDAO_DEBUG|No|False|Whether to enable Debug mode|
|WORKER_METHOD|No|Queue|Task timing execution method, <br>The default is Queue, optional Queue or Batch, <br>Batch mode is the old version of timing task execution method, the performance is weak, <br>**Recommended only when Queue timed execution mode fails**|
|MULTI_PROCESS|No|False|(Experimental) Whether to enable multi-process mode, <br>invalid on Windows platform|
|AUTO_RELOAD|No|False|Whether to enable automatic hot reload, <br>invalid when MULTI_PROCESS=True|
|ENABLE_HTTPS|No|False|Enable HTTPS for email sent, <br>Non-framework front-end using HTTPS, if the front-end needs HTTPS, please use a reverse proxy.|
|DOMAIN|No|qiandao.today|Specify the access domain name, <br>**(recommended modification)**, otherwise the function of resetting password by email is not valid|
|AES_KEY|No|binux|AES encryption key, **(Modification strongly recommended)**|
|COOKIE_SECRET|No|binux|cookie encryption key, **(Modification strongly recommended)**|
|COOKIE_DAY|No|5|The number of days the cookie is kept in the client|
|DB_TYPE|No|sqlite3|Set to 'mysql' when MySQL is required|
|JAWSDB_MARIA_URL|No|''|When you need to use MySQL, <br> set to `mysql://username:password@hostname:port/database_name?auth_plugin=`|
|QIANDAO_SQL_ECHO|No|False|Whether to enable the log output of SQLAlchmey, the default is False, <br>When set to True, the SQL statement will be output on the console, <br>allow to set to debug to enable debug mode|
|QIANDAO_SQL_LOGGING_NAME|No|qiandao.sql_engine|SQLAlchmey log name, default is 'qiandao.sql_engine'|
|QIANDAO_SQL_LOGGING_LEVEL|No|Warning|SQLAlchmey log level, default is 'Warning'|
|QIANDAO_SQL_ECHO_POOL|No|True|Whether to enable SQLAlchmey's connection pool log output, the default is True, <br>allow setting to debug to enable debug mode|
|QIANDAO_SQL_LOGGING_POOL_NAME|No|qiandao.sql_pool|SQLAlchmey connection pool log name, the default is 'qiandao.sql_pool'|
|QIANDAO_SQL_LOGGING_POOL_LEVEL|No|Warning|SQLAlchmey connection pool log level, default is 'Warning'|
|QIANDAO_SQL_POOL_SIZE|No|10|SQLAlchmey connection pool size, default is 10|
|QIANDAO_SQL_MAX_OVERFLOW|No|50|SQLAlchmey connection pool maximum overflow, the default is 50|
|QIANDAO_SQL_POOL_PRE_PING|No|True|Whether to ping before the connection pool gets a connection, the default is True|
|QIANDAO_SQL_POOL_RECYCLE|No|3600|SQLAlchmey connection pool recovery time, the default is 3600|
|QIANDAO_SQL_POOL_TIMEOUT|No|60|SQLAlchmey connection pool timeout, the default is 60|
|QIANDAO_SQL_POOL_USE_LIFO|No|True|SQLAlchmey whether to use LIFO algorithm, the default is True|
|REDISCLOUD_URL|No|''|When you need to use Redis or RedisCloud, <br> set to <http://rediscloud:password@hostname:port>|
|REDIS_DB_INDEX|No|1|The default is 1|
|QIANDAO_EVIL|No|500|(Only when the Redis connection is enabled)<br>Score = number of operation failures (such as login, verification, test, etc.) * corresponding penalty points<br>When the score reaches the upper limit of evil, it will be automatically banned until the next hour cycle|
|EVIL_PASS_LAN_IP|No|True|Whether to turn off the evil restriction of local private IP address users and Localhost_API requests|
|TRACEBACK_PRINT|No|False|Whether to enable to print Exception's TraceBack information in the console log|
|PUSH_PIC_URL|No|[push_pic.png](https://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/web/static/img/push_pic.png)|The default is [push_pic.png](https ://fastly.jsdelivr.net/gh/qiandao-today/qiandao@master/web/static/img/push_pic.png)|
|PUSH_BATCH_SW|No|True|Whether to allow periodic push of Qiandao task logs, the default is True|
|MAIL_SMTP|No|""|Email SMTP server|
|MAIL_PORT|No|""|Email SMTP server port|
|MAIL_USER|No|""|Email username|
|MAIL_PASSWORD|No|""|Email password|
|MAIL_FROM|No|MAIL_USER|The Email used when sending, the default is the same as MAIL_USER|
|MAIL_DOMAIN|No|mail.qiandao.today|Email domain name, useless, use DOMAIN|
|PROXIES|No|""|Global proxy domain name list, separated by "\|"|
|PROXY_DIRECT_MODE|No|""|Global proxy blacklist mode, not enabled by default <br>"url" is URL matching mode; "regexp" is regular expression matching mode|
|PROXY_DIRECT|No|""|Global proxy blacklist matching rules|
|USE_PYCURL|No|True|Whether to enable Pycurl module|
|ALLOW_RETRY|No|True|When some requests in the Pycurl environment may cause Request errors, <br>automatically modify the conflict settings and resend the request|
|DNS_SERVER|No|""|Use specified DNS for resolution via Curl (only supports Pycurl environment), <br>such as 8.8.8.8|
|CURL_ENCODING|No|True|Whether to allow to use Curl for Encoding operation|
|CURL_CONTENT_LENGTH|No|True|Whether to allow Curl to use custom Content-Length request in Headers|
|NOT_RETRY_CODE|No|[See configuration for details](https://github.com/qiandao-today/qiandao/blob/master/config.py)...|[See configuration for details](https://github.com/qiandao-today/qiandao/blob/master/config.py)...|
|EMPTY_RETRY|No|True|[See configuration for details](https://github.com/qiandao-today/qiandao/blob/master/config.py)...|
|USER0ISADMIN|No|True|The first registered user is an administrator, False to close|
|EXTRA_ONNX_NAME|No|""|Customize the ONNX file name in the config directory<br>(do not fill in the ".onnx" suffix)<br>Separate multiple onnx file names with "\|"|
|EXTRA_CHARSETS_NAME|No|""|Custom ONNX in the config directory corresponds to the custom charsets.json file name<br>(do not fill in the ".json" suffix)<br>Multiple json file names are separated by "\|"|

> For details, please refer to [config.py](https://github.com/qiandao-today/qiandao/blob/master/config.py)
