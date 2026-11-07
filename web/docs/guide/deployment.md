# Deployment

## Docker Container Deployment

Docker Container Deployment is the easiest way to deploy QD.

> Please always remember to back up your database before updating or redeploying.

### Container

**DockerHub URL** : [https://hub.docker.com/r/qdtoday/qd](https://hub.docker.com/r/qdtoday/qd)

> Tag meaning:
>
> - `latest`: Latest Release version, with OCR (captcha recognition) included
> - `lite-latest`: Latest Release version without OCR related functions, smallest image
> - `ja3-latest`: Same as `latest`, but with curl-impersonate integrated to solve the problem that ja3 fingerprint is identified as curl, does not support http3 and Quic connection
> - `ja3-lite-latest`: Same as `lite-latest`, but with curl-impersonate integrated, smallest image that still passes ja3 fingerprint checks
> - `20xxxxxx`: Specify Release version, version number is represented by Release release date. The same four flavours exist with a prefix: `ja3-20xxxxxx`, `lite-20xxxxxx`, `ja3-lite-20xxxxxx`
> - `dev`: Latest development version, synchronized with the latest source code, no stability guarantee. The same four flavours exist with a prefix: `lite-dev`, `ja3-dev`, `ja3-lite-dev`
>
> Architecture note: the OCR dependencies have no musllinux wheels for `386`, `arm/v6` and `s390x`. On those three architectures `latest` is still pullable, but the platform entry is the `lite` flavour (no captcha recognition); `ja3-latest` is the `ja3-lite` flavour on `386` and `arm/v6`, and is not published for `s390x`. Use `amd64`, `arm64`, `arm/v7`, `ppc64le`, `riscv64` or `loong64` if you need captcha recognition.

### Deploy Method

#### 1. Docker Compose (Recommend)

``` sh
# Create and switch to the QD directory.
mkdir -p $(pwd)/qd/config && cd $(pwd)/qd
# Download docker-compose.yml
wget https://fastly.jsdelivr.net/gh/qd-today/qd@master/docker-compose.yml
# Modify the configuration environment variables according to the requirements and configuration description
vi ./docker-compose.yml
# Execute Docker Compose command
docker-compose up -d
```

> See [Configuration](#configuration-environment-variables) below for configuration description
>
> If you don't need `OCR` or `hard disk space is not larger than 600M`, please use **`qdtoday/qd:lite-latest`** image, **this image only removes OCR related functions and keeps the same behaviour as the mainline version**.
>
> **Please don't use AliCloud image source to pull Docker container, it will not pull the latest image.**

#### 2. 1Panel Deployment

2.1. Create a new application in 1Panel

   ![Click to install](../public/panel1.png)

   > The QD framework name may be different in different 1Panel versions, but they are all `QD` icons.

2.2. Configure related settings

   ![Installation configuration](../public/panel2.png)

   > If you need to set environment variables, please click `Edit Compose file`
   >
   > See [Configuration](#configuration-environment-variables) below for configuration description
   >
   > If you don't need `OCR` or `hard disk space is not larger than 600M`, please use **`qdtoday/qd:lite-latest`** image, **this image only removes OCR related functions and keeps the same behaviour as the mainline version**.

2.3. Click `Confirm` to install QD via 1Panel

#### 3. Docker Run

``` sh
docker run -d --name qd -p 8923:80 -v $(pwd)/qd/config:/usr/src/app/config qdtoday/qd
```

Try this command if you cannot connect to the external network inside the container:

``` sh
# Create container using Host network mode, port: 8923
docker run -d --name qd --env PORT=8923 --net=host -v $(pwd)/qd/config:/usr/src/app/config qdtoday/qd
```

> Please note that after creating a container with this command, please change the api request of `http://localhost/` form in the template to `api://` or `http://localhost:8923/` manually in order to complete the related API request properly.
>
> **Do not run both old and new versions of QD framework, or map different running QD container databases to the same file.**

## Source Code Deployment

1. **Version >= python3.9**

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

## Session secret

Session cookies are signed with `COOKIE_SIGN_SECRET`. When it is not set, a random secret is generated on every start and kept in memory only, so **all sessions are invalidated after a service/container restart** and users have to log in again; the secret is never written to disk.

For multi-instance / multi-container deployments sharing one database, every instance must use the same secret, otherwise sessions randomly break depending on which instance serves the request:

``` sh
# generate once and keep it safe
openssl rand -hex 32
```

``` yaml
environment:
  - COOKIE_SIGN_SECRET=<the value generated above>
```

> Changing this secret (or removing it so a new random one is generated) **invalidates all sessions immediately**; tasks, templates, variables and credentials in the database are not affected.
>
> `COOKIE_SECRET` is deprecated and ignored by default.

## Rotate AES_KEY

`AES_KEY` is the database data encryption key. It encrypts `user.userkey` (the stored user credentials) and the public template data whose `userid` is empty (`tpl.har` / `tpl.tpl` / `task.init_env` / `task.env`).

The default value `binux` is public, so it is only acceptable for a fully isolated internal deployment; once the database or a backup leaks, the stored credentials can be decrypted offline.

> **Changing the `AES_KEY` environment variable directly makes the existing data undecryptable**: logging in then fails with a 500 (`decrypt error`), and the saved tasks and public templates can no longer be read.
> Existing data must be migrated to the new key with `tools/rotate_aes_key.py` before the environment variable is changed.

The migration script decrypts with the old key, encrypts with the new one and verifies every row by reading it back; a single failure aborts the whole run and nothing is written. It only prints a dry run by default — add `--apply` to actually write.

The summary prints "re-encrypted N columns, skipped M columns". **Do not treat the run as successful when M is non-zero** — confirm why those columns were skipped before starting the service.

### Source code deployment

Dependencies are managed by uv (the virtual environment lives in `.venv`), and the script has to be run from the repository root:

``` sh
cd /path/to/qd

# 1. generate a new secret (once, keep it safe)
openssl rand -hex 32

# 2. stop the service and back up the database, then do a dry run
.venv/bin/python -m tools.rotate_aes_key --old binux --new <new secret>

# 3. apply it once the dry run output looks right
.venv/bin/python -m tools.rotate_aes_key --old binux --new <new secret> --apply

# 4. set AES_KEY=<new secret> and start the service again
```

For sqlite a `<database>.aes-<timestamp>.bak` copy is left next to the database before it is written; MySQL is not backed up, keep your own `mysqldump`.

### Docker deployment

Inside the image the code lives in `/usr/src/app`, the interpreter is `/usr/src/app/.venv/bin/python` and the database is in the mounted `config` directory (`/usr/src/app/config`). Run the migration in a throwaway container that mounts the same data directory as the running container:

``` sh
# 1. stop the running container (so no task or login writes while the migration runs)
docker stop <container>

# 2. back up the database, then run the migration in a throwaway container
docker run --rm -it \
  -v /host/path/config:/usr/src/app/config \
  --entrypoint sh \
  <image> -c "cd /usr/src/app && python -m tools.rotate_aes_key --old binux --new <new secret> --apply"

# 3. start the container with the new secret
docker run -d --name qd -p 8923:80 \
  -v /host/path/config:/usr/src/app/config \
  -e AES_KEY=<new secret> \
  <image>
```

MySQL deployments have to pass the same database environment variables as the running container so that the script connects to the same database:

``` sh
docker run --rm -it \
  -e DB_TYPE=mysql \
  -e JAWSDB_MARIA_URL='mysql://username:password@hostname:3306/database_name?auth_sqombs=' \
  --entrypoint sh \
  <image> -c "cd /usr/src/app && python -m tools.rotate_aes_key --old binux --new <new secret> --apply"
```

> `--old` takes the plaintext value of the **currently effective** AES_KEY; if one has been set before, do not pass the default `binux`.
>
> The migration has to run with the service stopped, otherwise running tasks and login requests read and write the database concurrently.
>
> Once the migration is done and verified, set `AES_KEY_STRICT=True` to make the framework refuse to start while `AES_KEY` is still the default value.

## Configuration Environment Variables

|variable name|required|default value|description|
|:-: | :-: | :-: | :-:|
|BIND|No|0.0.0.0|Listening address|
|PORT|No|8923|Listening port|
|QD_DEBUG|No|False|Whether to enable Debug mode|
|WORKER_METHOD|No|Queue|Task timing execution method, <br>The default is Queue, optional Queue or Batch, <br>Batch mode is the old version of timing task execution method, the performance is weak, <br>**Recommended only when Queue timed execution mode fails**|
|MULTI_PROCESS|No|False|(Experimental) Whether to enable multi-process mode, <br>invalid on Windows platform|
|AUTO_RELOAD|No|False|Whether to enable automatic hot reload, <br>invalid when MULTI_PROCESS=True|
|STATIC_URL_PREFIX|No|`/static/`|Static file URL prefix|
|DOMAIN|No|''|Specify the access domain name, <br>**(recommended modification)**, otherwise the function of resetting password by email is not valid|
|AES_KEY|No|binux|Database encryption key for stored credentials, **(set it on first deploy; migrate data before changing, or credentials become undecryptable)**, see [Rotate AES_KEY](#rotate-aes_key)|
|AES_KEY_STRICT|No|False|When True, refuse to start while AES_KEY is still the default value, **(migrate data first)**|
|COOKIE_SIGN_SECRET|No|random per start|Session cookie signing key, never stored; generated on every start when unset (**all sessions drop after restart**), set it explicitly for multi-instance/multi-container deployments; can be overridden by defining `cookie_secret` in local_config.py, **(COOKIE_SECRET is deprecated and ignored)**|
|COOKIE_DAY|No|5|The number of days the cookie is kept in the client|
|DB_TYPE|No|sqlite3|Set to 'mysql' when MySQL is required|
|JAWSDB_MARIA_URL|No|''|When you need to use MySQL, <br> set to `mysql://username:password@hostname:port/database_name?auth_plugin=`|
|QD_SQL_ECHO|No|False|Whether to enable the log output of SQLAlchmey, the default is False, <br>When set to True, the SQL statement will be output on the console, <br>allow to set to debug to enable debug mode|
|QD_SQL_LOGGING_NAME|No|QD.sql_engine|SQLAlchmey log name, default is 'QD.sql_engine'|
|QD_SQL_LOGGING_LEVEL|No|Warning|SQLAlchmey log level, default is 'Warning'|
|QD_SQL_ECHO_POOL|No|True|Whether to enable SQLAlchmey's connection pool log output, the default is True, <br>allow setting to debug to enable debug mode|
|QD_SQL_LOGGING_POOL_NAME|No|QD.sql_pool|SQLAlchmey connection pool log name, the default is 'QD.sql_pool'|
|QD_SQL_LOGGING_POOL_LEVEL|No|Warning|SQLAlchmey connection pool log level, default is 'Warning'|
|QD_SQL_POOL_SIZE|No|10|SQLAlchmey connection pool size, default is 10|
|QD_SQL_MAX_OVERFLOW|No|50|SQLAlchmey connection pool maximum overflow, the default is 50|
|QD_SQL_POOL_PRE_PING|No|True|Whether to ping before the connection pool gets a connection, the default is True|
|QD_SQL_POOL_RECYCLE|No|3600|SQLAlchmey connection pool recovery time, the default is 3600|
|QD_SQL_POOL_TIMEOUT|No|60|SQLAlchmey connection pool timeout, the default is 60|
|QD_SQL_POOL_USE_LIFO|No|True|SQLAlchmey whether to use LIFO algorithm, the default is True|
|REDISCLOUD_URL|No|''|When you need to use Redis or RedisCloud, <br> set to <http://rediscloud:password@hostname:port>|
|REDIS_DB_INDEX|No|1|The default is 1|
|QD_EVIL|No|500|(Only when the Redis connection is enabled)<br>Score = number of operation failures (such as login, verification, test, etc.) * corresponding penalty points<br>When the score reaches the upper limit of evil, it will be automatically banned until the next hour cycle|
|EVIL_PASS_LAN_IP|No|True|Whether to turn off the evil restriction of local private IP address users and Localhost_API requests|
|TRACEBACK_PRINT|No|False|Whether to enable to print Exception's TraceBack information in the console log|
|PUSH_PIC_URL|No|[push_pic.png](https://fastly.jsdelivr.net/gh/qd-today/qd@master/web/static/img/push_pic.png)|The default is [push_pic.png](https ://fastly.jsdelivr.net/gh/qd-today/qd@master/web/static/img/push_pic.png)|
|PUSH_BATCH_SW|No|True|Whether to allow periodic push of QD task logs, the default is True|
|MAIL_SMTP|No|""|Email SMTP server|
|MAIL_PORT|No|465|Email SMTP server port|
|MAIL_SSL|No|True|Whether to use SSL when connecting to the email server, the default is True|
|MAIL_STARTTLS|No|False|Whether to use TLS when connecting to the email server, the default is False|
|MAIL_USER|No|""|Email username|
|MAIL_PASSWORD|No|""|Email password|
|MAIL_FROM|No|MAIL_USER|The Email used when sending, the default is the same as MAIL_USER|
|MAIL_DOMAIN_HTTPS|No|False|Whether to use HTTPS for email domain name. <br>Not the framework itself HTTPS configuration. <br>If you need HTTPS, please use an external reverse proxy|
|PROXIES|No|""|Global proxy domain name list, separated by "\|"|
|PROXY_DIRECT_MODE|No|""|Global proxy blacklist mode, not enabled by default <br>"url" is URL matching mode; "regexp" is regular expression matching mode|
|PROXY_DIRECT|No|""|Global proxy blacklist matching rules|
|NEW_TASK_DELAY|No|1|Preparation time after new task, default is 1 second|
|TASK_WHILE_LOOP_TIMEOUT|No|900|Maximum runtime of a single While loop during a task run, <br>the default is 15 minutes|
|TASK_REQUEST_LIMIT|No|1500|Maximum number of requests per task run, <br>the default is 1500|
|USE_PYCURL|No|True|Whether to enable Pycurl module|
|ALLOW_RETRY|No|True|When some requests in the Pycurl environment may cause Request errors, <br>automatically modify the conflict settings and resend the request|
|DNS_SERVER|No|""|Use specified DNS for resolution via Curl (only supports Pycurl environment), <br>such as 8.8.8.8|
|CURL_ENCODING|No|True|Whether to allow to use Curl for Encoding operation|
|CURL_CONTENT_LENGTH|No|True|Whether to allow Curl to use custom Content-Length request in Headers|
|NOT_RETRY_CODE|No|[See configuration for details](https://github.com/qd-today/qd/blob/master/config.py)...|[See configuration for details](https://github.com/qd-today/qd/blob/master/config.py)...|
|EMPTY_RETRY|No|True|[See configuration for details](https://github.com/qd-today/qd/blob/master/config.py)...|
|USER0ISADMIN|No|True|The first registered user is an administrator, False to close|
|NOTEPAD_LIMIT|No|20|The maximum number of notepads within the same user, the default is 20|
|EXTRA_ONNX_NAME|No|""|Customize the ONNX file name in the config directory<br>(do not fill in the ".onnx" suffix)<br>Separate multiple onnx file names with "\|"|
|EXTRA_CHARSETS_NAME|No|""|Custom ONNX in the config directory corresponds to the custom charsets.json file name<br>(do not fill in the ".json" suffix)<br>Multiple json file names are separated by "\|"|
|WS_PING_INTERVAL|No|5|WebSocket ping interval, the default is 5 seconds|
|WS_PING_TIMEOUT|No|30|WebSocket ping timeout, the default is 30 seconds|
|WS_MAX_MESSAGE_SIZE|No|10485760|WebSocket maximum message size, the default is 10485760 bytes|
|WS_MAX_QUEUE_SIZE|No|100|WebSocket maximum queue size, the default is 100|
|WS_MAX_CONNECTIONS_SUBSCRIBE|No|30|WebSocket subscribe page maximum number of connections, the default is 30|
|SUBSCRIBE_ACCELERATE_URL|No|qd-ph|Subscribe page acceleration URL, the default is qd-ph, <br>[See configuration for details](https://github.com/qd-today/qd/blob/master/config.py)...|

> For details, please refer to [config.py](https://github.com/qd-today/qd/blob/master/config.py)

#### 4. Bare Alpine (source deployment)

Container images ship their Python dependencies, so this step is only needed when you
run the source directly on Alpine.

``` sh
sh update.sh
```

Outside a container it also installs the Python dependencies: it downloads prebuilt
musllinux wheels from the three component repositories' GitHub Releases and installs
them with uv. PyPI is not enough here — onnxruntime and OpenCV have no musllinux
wheels, and pycurl is source-only. Use `QD_NO_OCR=1 sh update.sh` to skip the two OCR
wheelhouses.
