# 推送工具

## 推送注册

QD 框架提供多种[推送方式](#推送方式)，你可以在 `工具箱`->`推送注册` 中注册不同的推送工具，以便在发生特定事件（例如定时任务执行失败）时向你推送通知。

::: tip 提醒

推送注册时填写的参数以 `;` 分隔并连接, 如果参数值为空, 请务必保留该参数位置后的 `;` , 否则可能导致参数解析错误.

:::

### 推送注册测试

在 `工具箱`->`推送注册` 中注册推送方式后, 可以点击 `测试` 按钮来测试推送方式是否可用.

如果推送方式可用, 则会收到一条推送消息, 否则会提示推送失败.

::: tip 提醒

进行推送注册测试时, 请确保以下条件已满足:

- 填写了正确的参数;

- `邮箱` 和 `密码` 中填写了 QD 框架的用户邮箱和密码.

:::

### 推送注册前值

在 `工具箱`->`推送注册` 中注册推送方式后, 可以点击 `前值` 按钮来查看推送注册的前值.

::: tip 提醒

查看推送注册前值时, 请确保 `邮箱` 和 `密码` 中填写了 QD 框架的用户邮箱和密码.

:::

## 推送方式

QD 框架提供以下推送方式：

### 邮件推送

邮件推送无需在 `工具箱`->`推送注册` 中设置参数, 需要在环境变量中配置以下参数：

变量名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
MAIL_SMTP|是|""|邮箱SMTP服务器
MAIL_PORT|否|465|邮箱SMTP服务器端口
MAIL_SSL|否|True|是否使用SSL
MAIL_STARTTLS|否|False|是否使用STARTTLS
MAIL_USER|是|""|邮箱用户名
MAIL_PASSWORD|是|""|邮箱密码
MAIL_FROM|否|MAIL_USER|发送时使用的邮箱，默认与MAIL_USER相同
MAIL_DOMAIN_HTTPS|否|False|发送的邮件链接启用HTTPS, <br>非框架前端使用HTTPS, <br>如果前端需要HTTPS, 请使用反向代理.

如果你使用的是以下邮箱, 参考下方的SMTP开启方式和配置方法来获取你的SMTP服务器地址和端口。

邮箱|SMTP开启方式|SMTP配置方法|其他说明
:-: | :-: | :-: | :-:
腾讯企业邮箱|[如何开启腾讯企业邮箱的POP/SMTP/IMAP服务？](https://open.work.weixin.qq.com/help2/pc/19886)|[常用邮件客户端软件设置](https://open.work.weixin.qq.com/help2/pc/19885)|[成员如何绑定/关联微信以及开启安全登录获取客户端专用密码？](https://open.work.weixin.qq.com/help2/pc/19902)
QQ邮箱|[如何开启QQ邮箱的POP3/SMTP/IMAP服务？](https://service.mail.qq.com/detail/0/428)|[如何打开POP3/SMTP/IMAP功能？](https://service.mail.qq.com/detail/0/310)|[开启POP3/SMTP/IMAP功能为什么需要先设置独立密码？](https://service.mail.qq.com/detail/0/86)
网易企业邮箱|-|[企业邮箱的POP、SMTP、IMAP服务器地址设置。](https://qiye.163.com/help/client-profile.html)|[什么是客户端授权码，如何使用？](https://qiye.163.com/help/af988e.html)
网易邮箱|[什么是POP3、SMTP及IMAP？](https://help.mail.163.com/faqDetail.do?code=d7a5dc8471cd0c0e8b4b8f4f8e49998b374173cfe9171305fa1ce630d7f67ac21b87735d7227c217)|[如何开启客户端协议？](https://help.mail.163.com/faqDetail.do?code=d7a5dc8471cd0c0e8b4b8f4f8e49998b374173cfe9171305fa1ce630d7f67ac2a5feb28b66796d3b)|-
Gmail|-|[如何使用POP3/SMTP/IMAP服务？](https://support.google.com/mail/answer/7104828?hl=zh-Hans)|[如何使用客户端授权密码？](https://support.google.com/accounts/answer/185833?hl=zh-Hans)
Outlook|-|[POP、IMAP 和 SMTP 设置](https://support.microsoft.com/zh-cn/office/pop-imap-%E5%92%8C-smtp-%E8%AE%BE%E7%BD%AE-8361e398-8af4-4e97-b147-6c6c4ac95353)|[对不支持双重验证的应用使用应用密码](https://support.microsoft.com/zh-cn/account-billing/%E5%AF%B9%E4%B8%8D%E6%94%AF%E6%8C%81%E5%8F%8C%E9%87%8D%E9%AA%8C%E8%AF%81%E7%9A%84%E5%BA%94%E7%94%A8%E4%BD%BF%E7%94%A8%E5%BA%94%E7%94%A8%E5%AF%86%E7%A0%81-5896ed9b-4263-e681-128a-a6f2979a7944)

::: tip MailGun

如果您配置了 MailGun, 请在环境变量中配置以下参数：

变量名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
MAILGUN_KEY|是|""|MailGun API Key
MAILGUN_DOMAIN|是|DOMAIN|MailGun Domain, <br>默认为环境变量中的 DOMAIN 值, <br>请在环境变量中配置 DOMAIN 值, <br>并在 MailGun 控制台中设置对应的 Domain, <br>否则无法使用 MailGun

:::

### Bark 推送

Bark 推送需要在 `工具箱`->`推送注册` 中设置参数：

参数名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
BarkUrl|是|""|Bark 推送地址, <br>格式为 `https://api.day.app/推送码`, <br>推送码可在 Bark 客户端中获取, <br>如果你使用的是自建 Bark 服务, <br>请将 `https://api.day.app/` 替换为你的 Bark 服务地址 .<br>例如: `http://bark.example.com/推送码`

### Server 酱推送

Server 酱推送需要在 `工具箱`->`推送注册` 中设置参数：

参数名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
skey|是|""|Server 酱推送 SCKEY, <br>可在 [Server 酱](https://sct.ftqq.com/sendkey) 中获取对应的 SendKey

### Telegram Bot 推送

Telegram Bot 推送需要在 `工具箱`->`推送注册` 中设置参数：

参数名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
TG_TOKEN|是|""|Telegram Bot Token, <br>可在 [BotFather](https://t.me/BotFather) 中获取, <br>应当为 Bot 的 ID 以及对应的 Key 的组合，但是不包括 `bot`, <br>即 token 形式：`1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`
TG_USERID|是|""|Telegram Chat ID, <br>可在 [Telegram API](https://api.telegram.org/bot1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/getUpdates) 中获取, <br>Telegram API中的 `chat_id` 字段，如 `222222222`
TG_HOST|否|""|Telegram API Host, <br>可为域名或IP地址, <br>例如 `tg.mydomain.com`, <br>也可以带上 `http://` 或者 `https://` 前缀, <br>如果留空, 则使用默认值 `api.telegram.org`
PROXY_URL|否|""|Proxy 代理地址, <br>格式为 `scheme://username:password@host:port`, <br>例如 `http://user:password@host:port`, <br>如果留空, 则不使用 Proxy 代理
PUSH_PIC_URL|否|""|自定义推送图片地址, <br>如果留空, 则使用环境变量 `PUSH_PIC_URL` 值

::: details 示例

假设你已经创建了一个具有自定义域名的 Telegram Bot API:

```https://tg.mydomain.com/bot1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/sendMessage?chat_id=222222222&text=HelloWorld```

上面这个请求将会向`222222222`这个聊天发送一条`HelloWorld`消息, 那么在注册 Telegram Bot 作为推送方式时：

- `TG_TOKEN` 为`1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`
- `TG_USERID` 为 `222222222`
- `TG_HOST` 为 `tg.mydomain.com`

因此最终填写形式形如：

``` Text
1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA;222222222;tg.mydomain.com
```

:::

### 钉钉推送

钉钉推送需要在 `工具箱`->`推送注册` 中设置参数：

参数名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
DINGDING_TOKEN|是|""|钉钉推送 Token, <br>可在 [自定义机器人接入](https://open.dingtalk.com/document/robots/custom-robot-access) 中获取, <br>如果你在 `安全设置` 中设置了 `IP地址段` , <br>请将 QD 服务器的 IP 地址添加到 `IP地址段` 中, <br>否则无法接收到推送消息; <br>如果你在 `安全设置` 中设置了 `自定义关键词` , <br>请将 `QD`/`推送`/`测试` 添加到 `自定义关键词` 中, <br>否则无法接收到推送消息; <br>请勿在 `安全设置` 中开启 `加签`, QD 框架暂不支持钉钉加签推送.
PUSH_PIC_URL|否|""|自定义推送图片地址, <br>如果留空, 则使用环境变量 `PUSH_PIC_URL` 值

### WXPusher 推送

WXPusher 推送需要在 `工具箱`->`推送注册` 中设置参数：

参数名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
APPTOKEN|是|""|WXPusher 推送 Token, <br>可在 [WXPusher](https://wxpusher.zjiecode.com/docs/#/?id=%e8%8e%b7%e5%8f%96apptoken) 中获取
WxPusher_UID|是|""|WXPusher 推送 UID, <br>可在 [WXPusher](https://wxpusher.zjiecode.com/docs/#/?id=%e8%8e%b7%e5%8f%96uid) 中获取

### 企业微信应用推送

企业微信应用推送需要在 `工具箱`->`推送注册` 中设置参数：

参数名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
CorpID|是|""|企业微信 CorpID, <br>可在 [企业微信](https://developer.work.weixin.qq.com/document/path/98728) 中获取
AgentID|是|""|企业微信应用 AgentID, <br>可在 [企业微信](https://developer.work.weixin.qq.com/document/path/90665#agentid) 中获取
AgentSecret|是|""|企业微信应用 Secret, <br>可在 [企业微信](https://developer.work.weixin.qq.com/document/path/90665#secret) 中获取
PUSH_PIC_URL_or_Media_id|否|""|自定义推送图片地址或 Media_id, <br>Media_id 可以通过 [企业微信](https://developer.work.weixin.qq.com/document/path/90253#10112) 接口获取, <br>如果留空, 则使用环境变量 `PUSH_PIC_URL` 值
QYWX_PROXY_HOST|否|""|企业微信 Host, <br>可为域名或IP地址, <br>例如 `qywx.mydomain.com`, <br>也可以带上 `http://` 或者 `https://` 前缀, <br>如果留空, 则使用默认值 `https://qyapi.weixin.qq.com/`

::: tip QYWX_PROXY_HOST

如果你使用 Nginx 代理企业微信应用推送, 以下为 Nginx 配置示例:

``` Nginx
server {
    listen 443 ssl;
    server_name qywx.mydomain.com;
    ssl_certificate /etc/nginx/ssl/qywx.mydomain.com/fullchain.cer;
    ssl_certificate_key /etc/nginx/ssl/qywx.mydomain.com/private.key;
    ssl_session_timeout 5m;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:HIGH:!aNULL:!MD5:!RC4:!DHE;
    ssl_prefer_server_ciphers on;
    location / {
        proxy_pass https://qyapi.weixin.qq.com/;
    }
}
```

:::

### 企业微信 Webhook 推送

企业微信 Webhook 推送需要在 `工具箱`->`推送注册` 中设置参数：

参数名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
QYWX_WebHook_Key|是|""|企业微信 Webhook Key, <br>可在 [企业微信](https://work.weixin.qq.com/api/doc/90000/90136/91770) 中获取

### 自定义推送

自定义推送支持 `GET` 和 `POST` 推送方式, 使用 `{log}` 和 `{t}` 表示要替换的日志和标题.

自定义推送需要在 `工具箱`->`推送注册` 中设置参数：

#### 自定义 Get 推送

参数名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
URL|是|""|自定义 Get 推送地址, <br>例如 `https://example.com/push?log={log}&t={t}`
GET_Header|否|""|自定义 Get 推送 Header, <br>使用 json 格式(半角双引号), 格式为 `{ "key1": "value1", "key2": "value2" }`, <br>如果留空, 则不设置 Header

#### 自定义 Post 推送

参数名|是否必须|默认值|说明
:-: | :-: | :-: | :-:
URL|是|""|自定义 Post 推送地址, <br>例如 `https://example.com/push`
POST_Header|否|""|自定义 Post 推送 Header, <br>使用 json 格式(半角双引号), 格式为 `{ "key1": "value1", "key2": "value2" }`, <br>如果留空, 则不设置 Header
POST_Data|否|""|自定义 Post 推送 Body, <br>使用 json 格式(半角双引号), <br>例如 `{ "key1": "{log}", "key2": "{t}" }`, <br>如果留空, 则不设置 Body

## 推送设置

在 `工具箱`->`推送注册` 中注册推送方式后, 可以在 `工具箱`->`推送设置` 中设置推送方式的触发条件.

在 `推送设置` 中, 可以设置每个任务的推送开关, 任务结果推送渠道, 任务结果通知选择, 任务结果批量推送等.

### 任务结果推送渠道

用于设置任务结果推送渠道, 任务结果推送渠道包括以下几种:

- [Bark 推送](#bark-推送)
- [Server 酱推送](#server-酱推送)
- [WXPusher 推送](#wxpusher-推送)
- [邮件推送](#邮件推送)
- [企业微信应用推送](#企业微信应用推送)
- [Telegram Bot 推送](#telegram-bot-推送)
- [钉钉推送](#钉钉推送)
- [企业微信 Webhook 推送](#企业微信-webhook-推送)
- [自定义推送](#自定义推送)

### 任务结果通知选择

用于设置在何时推送任务结果, 任务结果通知选择包括以下几种:

- 手动执行成功通知
- 手动执行失败通知
- 自动执行成功通知
- 自动执行失败通知

`自动错误几次后提醒` 可以设置在自动执行失败几次后推送通知, 例如设置为 `3` , 则当自动执行失败 3 次后, 会推送通知.

### 任务结果批量推送

当 `开启定期批量推送` 时, 会根据 `批量推送时间设置` 和 `批量推送时间间隔` 来批量推送距离本次推送时间前指定时间间隔内的任务结果.

- `批量推送时间设置`: 初次批量推送时间设置, 例如设置为 `12:00:00` , 则会在当天的 `12:00:00` 进行一次批量推送.

- `批量推送时间间隔`: 设置每隔多少秒推送一次任务结果, 默认为 `86400` 秒, 即每隔一天批量推送本次推送时间前86400秒内的任务结果.
