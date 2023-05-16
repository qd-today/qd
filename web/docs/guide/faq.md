# FAQ

## how to backup and restore the database?

QD uses **sqlite3** as the framework database by default, and the `database.db` file is saved in `config` directory. When deploying with a Docker container, you can use the `docker cp` command to back up the database file, and then use the `docker cp` command to restore the database file in the new container.

``` sh
# database backup
docker cp container_name:/usr/src/app/config/database.db .
# Database recovery
docker cp database.db container_name:/usr/src/app/config/
```

## how to configure the email server in Docker?

``` sh
docker run -d --name qd -p 8923:80 -v $(pwd)/qd/config:/usr/src/app/config --env MAIL_SMTP=$STMP_Server_ --env MAIL_PORT=$Mailbox_server_port --env MAIL_USER=$Username --env MAIL_PASSWORD=$Password --env DOMAIN=$Domain a76yyyy/qiandao
```

## how to use MySQL in Docker?

``` sh
docker run -d --name qd -p 8923:80 -v $(pwd)/qd/config:/usr/src/app/config --ENV DB_TYPE=mysql --ENV JAWSDB_MARIA_URL=mysql://$username:$password@$hostname:$port/$database_name?auth_plugin= a76yyyy/qiandao
```

## how to build a Docker image by myself?

Please refer to the build file [Dockerfile](https://github.com/qd-today/qd/blob/master/Dockerfile) of this image.

## How to view the API and Jinja2 template variables supported by the current framework?

Please access the home page of the framework, and then click the `Common API/Filter` button in the upper left corner to view the API and Jinja2 template variables supported by the current framework.

## how to submit a bug issue?

Please enable `Debug` mode after encountering a problem, and then submit detailed error information to [Issue](https://github.com/qd-today/qd/issues).

## Which requests are necessary for QD?

Empirically, the following requests are necessary:

- login page
- POST to login page
- Issue a request for username, password
- The page that caused the page to jump after sending
- The first page before and after page turning

## Will my username and password be revealed?

In order to help users initiate requests, user names and passwords still need to be recorded. This can only rely on the self-discipline of server maintainers to ensure the security of back-end data. But in the framework design, each user is encrypted with a secure key when storing. Encrypting user data with a key can ensure that user data cannot be decrypted only by obtaining the database. (Encrypted user data includes templates uploaded by users, variables set by users for tasks, etc.)

If you are still worried, you can build the QD framework by yourself, download the template and run it on your own server.

## Prompt warning message: `Connect Redis falied: Error 10061`

QD uses `redis` as a flow limiting tool. If the `redis` service is not installed, the framework will prompt the following warning message.

``` sh
[W xxxxxx xx:xx:xx QD.RedisDB redisdb:28] Connect Redis falied: Error 10061 connecting to localhost:6379. No connection could be made because the target machine actively refused it.
```

However, `redis` is not required in this framework, if you don't need to use the `flow-limiting` feature, you can ignore the warning message.

> It is recommended to use `Docker compose` to deploy the QD framework, and the Docker compose configuration already installs the redis container by default.

## Prompt warning message: `Import PyCurl module falied`

QD uses the `pycurl` module to send HTTP proxy requests. If the `pycurl` module is not installed, the framework will prompt the following warning message:

``` sh
[W xxxxxx xx:xx:xx QD.Http.Fetcher fetcher:34] Import PyCurl module falied: No module named 'pycurl'
```

However, `pycurl` is not required in this framework, if you don't need to use the `proxy` function, you can ignore the warning message.

> The `pycurl` module is cumbersome to install on the Windows system, and the `libcurl` library needs to be installed. For the specific installation method, please refer to [pycurl official documentation](http://pycurl.io/docs/latest/install.html).
>
> It is recommended to use a container or linux system to deploy the QD framework. The docker container has a pre-installed Curl environment, and the pycurl module is installed by default

## How to Register Notification Tools

You can register different notification tools to receive notifications when specific events (such as failed check-ins) occur.

### TgBot

Assuming you have created a Telegram bot API with a custom domain::

`https://tg.mydomain.com/bot1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/sendMessage?chat_id=222222222&text=HelloWorld`

The above request will send a `HelloWorld` message to the chat with ID `222222222`. When registering TgBot as a notification method:

- `TG_TOKEN` should be filled with the combination of the bot ID and corresponding key, but without `bot`. That is, the token provided by BotFather when applying for TgBot: `1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`
- `TG_USERID` should be filled with the `chat_id` field in the Telegram API, that is, `222222222`
- `TG_HOST` should be filled with `tg.mydomain.com`, and it can also include the `http://` or `https://` prefix

Therefore, the final result looks like:

`1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA;222222222;tg.mydomain.com`
