# Pusher

## Push Registration

The QD framework provides various [push methods](#push methods), and you can register different push tools in `Toolbox`->`Push Registration` to push notifications to you when specific events occur (e.g. timed task execution failure).

::: tip

The parameters filled in when registering the push are separated and connected by `;`. If the parameter value is empty, please be sure to keep the `;` after the parameter position, otherwise it may cause parameter parsing error.

:::

### Push Registration Test

After registering the push method in `Toolbox`->`Push Registration`, you can click the `Test` button to test whether the push method is available.

If the push method is available, you will receive a push message, otherwise you will be prompted that the push failed.

::: tip

When testing the push registration, please make sure that the following conditions are met:

- The correct parameters are filled in;

- The `email` and `password` are filled in with the user's email and password of the QD framework.

:::

### Push Registration Former value

After registering the push method in `Toolbox`->`Push Registration`, you can click the `Former value` button to view the former value of the push registration.

::: tip

When viewing the former value of the push registration, please make sure that the `email` and `password` are filled in with the user's email and password of the QD framework.

:::

## Push Methods

The QD framework provides the following push methods:

### E-mail Push

E-mail push does not need to set parameters in `Toolbox`->`Push Registration`, you need to configure the following parameters in the environment variables:

Variable name|Required|Default|Description
:-: | :-: | :-: | :-:
MAIL_SMTP|True|""|Email SMTP server
MAIL_PORT|False|465|Email SMTP server port
MAIL_SSL|False|True|Whether to use SSL
MAIL_STARTTLS|False|False|Whether to use TLS
MAIL_USER|True|""|Email username
MAIL_PASSWORD|True|""|Email password
MAIL_FROM|False|MAIL_USER|The Email used when sending, the default is the same as MAIL_USER
MAIL_DOMAIN_HTTPS|False|False|Whether to use HTTPS for email domain name. <br>Not the framework itself HTTPS configuration. <br>If you need HTTPS, please use an external reverse proxy

If you are using the following email, refer to the SMTP enable method and configuration method below to get your SMTP server address and port.

Email|SMTP enable method|SMTP configuration method|Other instructions
:-: | :-: | :-: | :-:
Tencent Enterprise Mail|[How to enable Tencent Enterprise Mail POP/SMTP/IMAP service?](https://open.work.weixin.qq.com/help2/pc/19886)|[Common mail client software settings](https://open.work.weixin.qq.com/help2/pc/19885)|[How do members bind/associate WeChat and enable secure login to get client-specific passwords?](https://open.work.weixin.qq.com/help2/pc/19902)
QQ Mail|[How to enable QQ Mail POP3/SMTP/IMAP service?](https://service.mail.qq.com/detail/0/428)|[How to turn on POP3/SMTP/IMAP?](https://service.mail.qq.com/detail/0/310)|[Why do I need to set a separate password to enable POP3/SMTP/IMAP?](https://service.mail.qq.com/detail/0/86)
Netease Enterprise Mail|-|[Enterprise Mail POP, SMTP, IMAP server address settings.](https://qiye.163.com/help/client-profile.html)|[What is a client authorization code and how do I use it?](https://qiye.163.com/help/af988e.html)
Netease Mail|[What is POP3, SMTP and IMAP?](https://help.mail.163.com/faqDetail.do?code=d7a5dc8471cd0c0e8b4b8f4f8e49998b374173cfe9171305fa1ce630d7f67ac21b87735d7227c217)|[How to enable client protocol?](https://help.mail.163.com/faqDetail.do?code=d7a5dc8471cd0c0e8b4b8f4f8e49998b374173cfe9171305fa1ce630d7f67ac2a5feb28b66796d3b)|-
Gmail|-|[How to use POP3/SMTP/IMAP service?](https://support.google.com/mail/answer/7104828?hl=en)|[Sign in with app passwords](https://support.google.com/accounts/answer/185833?hl=en)
Outlook|-|[POP, IMAP and SMTP settings](https://support.microsoft.com/en-us/office/pop-imap-and-smtp-settings-8361e398-8af4-4e97-b147-6c6c4ac95353)|[Use app passwords with apps that don't support two-step verification](https://support.microsoft.com/en-us/account-billing/using-app-passwords-with-apps-that-don-t-support-two-step-verification-5896ed9b-4263-e681-128a-a6f2979a7944)

::: tip MailGun

If you have configured MailGun, please configure the following parameters in the environment variables:

Variable name|Required|Default|Description
:-: | :-: | :-: | :-:
MAILGUN_KEY|True|""|MailGun API Key
MAILGUN_DOMAIN|True|DOMAIN|MailGun Domain, <br>The default is the value of the DOMAIN in the environment variables, <br>Please configure the value of DOMAIN in the environment variables, <br>and set the corresponding Domain in the MailGun console, <br>otherwise MailGun cannot be used

:::

### Bark Push

Bark push needs to set parameters in `Toolbox`->`Push Registration`:

Parameter name|Required|Default|Description
:-: | :-: | :-: | :-:
BarkUrl|True|""|Bark push address, <br>The format is `https://api.day.app/push_key`, <br>The push_key can be obtained in the Bark client, <br>If you are using a self-built Bark service, <br>please replace `https://api.day.app/` with your Bark service address. <br>For example: `http://bark.example.com/push_key`

### Server Chan Push

Server Chan push needs to set parameters in `Toolbox`->`Push Registration`:

Parameter name|Required|Default|Description
:-: | :-: | :-: | :-:
skey|True|""|Server Chan push sendkey, <br>Can be obtained in [Server Chan](https://sct.ftqq.com/sendkey)

### Telegram Bot Push

Telegram Bot push needs to set parameters in `Toolbox`->`Push Registration`:

Parameter name|Required|Default|Description
:-: | :-: | :-: | :-:
TG_TOKEN|True|""|Telegram Bot Token, <br>Can be obtained in [BotFather](https://t.me/BotFather), <br>Should be a combination of Bot ID and corresponding Key, but not including `bot`, <br>That is, the token form: `1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`
TG_USERID|True|""|Telegram Chat ID, <br>Can be obtained in [Telegram API](https://api.telegram.org/bot1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/getUpdates), <br>The `chat_id` field in the Telegram API, such as `222222222`
TG_HOST|False|""|Telegram API Host, <br>Can be a domain name or IP address, <br>For example, `tg.mydomain.com`, <br>You can also add the `http://` or `https://` prefix, <br>If left blank, the default value `api.telegram.org` is used
PROXY_URL|False|""|Proxy address, <br>The format is `scheme://username:password@host:port`, <br>For example, `http://user:password@host:port`, <br>If left blank, the Proxy is not used
PUSH_PIC_URL|False|""|Custom push picture address, <br>If left blank, the environment variable `PUSH_PIC_URL` value is used

::: details Example

Assume that you have created a Telegram Bot API with a custom domain name:

```https://tg.mydomain.com/bot1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/sendMessage?chat_id=222222222&text=HelloWorld```

The above request will send a `HelloWorld` message to the chat `222222222`, then when registering the Telegram Bot as a push method:

- `TG_TOKEN` is `1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`
- `TG_USERID` is `222222222`
- `TG_HOST` is `tg.mydomain.com`

Therefore, the final form is as follows:

``` Text
1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA;222222222;tg.mydomain.com
```

:::

### DingTalk Push

DingTalk push needs to set parameters in `Toolbox`->`Push Registration`:

Parameter name|Required|Default|Description
:-: | :-: | :-: | :-:
DINGDING_TOKEN|True|""|DingTalk push Token, <br>Can be obtained in [Custom Robot Access](https://open.dingtalk.com/document/robots/custom-robot-access), <br>If you set the `IP address range` in `Security Settings`, <br>Please add the IP address of the QD server to `IP address range`, <br>Otherwise, you will not be able to receive push messages; <br>If you set the `Custom Keywords` in `Security Settings`, <br>Please add `QD`/`Push`/`Test` to `Custom Keywords`, <br>Otherwise, you will not be able to receive push messages; <br>Please do not enable `Signature` in `Security Settings`, QD framework does not support DingTalk Signature push for the time being.
PUSH_PIC_URL|False|""|Custom push picture address, <br>If left blank, the environment variable `PUSH_PIC_URL` value is used

### WXPusher Push

WXPusher push needs to set parameters in `Toolbox`->`Push Registration`:

Parameter name|Required|Default|Description
:-: | :-: | :-: | :-:
APPTOKEN|True|""|WXPusher push Token, <br>Can be obtained in [WXPusher](https://wxpusher.zjiecode.com/docs/#/?id=%e8%8e%b7%e5%8f%96apptoken)
WxPusher_UID|True|""|WXPusher push UID, <br>Can be obtained in [WXPusher](https://wxpusher.zjiecode.com/docs/#/?id=%e8%8e%b7%e5%8f%96uid)

### WeCom Application Push

WeCom application push needs to set parameters in `Toolbox`->`Push Registration`:

Parameter name|Required|Default|Description
:-: | :-: | :-: | :-:
CorpID|True|""|WeCom CorpID, <br>Can be obtained in [WeCom](https://developer.work.weixin.qq.com/document/path/98728)
AgentID|True|""|WeCom application AgentID, <br>Can be obtained in [WeCom](https://developer.work.weixin.qq.com/document/path/90665#agentid)
AgentSecret|True|""|WeCom application Secret, <br>Can be obtained in [WeCom](https://developer.work.weixin.qq.com/document/path/90665#secret)
PUSH_PIC_URL_or_Media_id|False|""|Custom push picture address or Media_id, <br>Media_id can be obtained through [WeCom](https://developer.work.weixin.qq.com/document/path/90253#10112) interface, <br>If left blank, the environment variable `PUSH_PIC_URL` value is used
QYWX_PROXY_HOST|False|""|WeCom Host, <br>Can be a domain name or IP address, <br>For example, `qywx.mydomain.com`, <br>You can also add the `http://` or `https://` prefix, <br>If left blank, the default value `https://qyapi.weixin.qq.com/` is used

::: tip QYWX_PROXY_HOST

If you use Nginx to proxy the WeCom application push, the following is an example of Nginx configuration:

``` Nginx
server {
    listen 443 ssl;
    server_name qywx.mydomain.com;
    ssl_certificate /etc/nginx/ssl/qywx.mydomain.com.crt;
    ssl_certificate_key /etc/nginx/ssl/qywx.mydomain.com.key;
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

### WeCom Webhook Push

WeCom Webhook push needs to set parameters in `Toolbox`->`Push Registration`:

Parameter name|Required|Default|Description
:-: | :-: | :-: | :-:
QYWX_WebHook_Key|True|""|WeCom Webhook Key, <br>Can be obtained in [WeCom](https://work.weixin.qq.com/api/doc/90000/90136/91770)

### Custom Push

Custom push supports `GET` and `POST` push methods, using `{log}` and `{t}` to represent the log and title to be replaced.

Custom push needs to set parameters in `Toolbox`->`Push Registration`:

#### Custom Get Push

Parameter name|Required|Default|Description
:-: | :-: | :-: | :-:
URL|True|""|Custom Get push address, <br>For example, `https://example.com/push?log={log}&t={t}`
GET_Header|False|""|Custom Get push Header, <br>Use json format (double quotes), the format is `{ "key1": "value1", "key2": "value2" }`, <br>If left blank, the Header is not set

#### Custom Post Push

Parameter name|Required|Default|Description
:-: | :-: | :-: | :-:
URL|True|""|Custom Post push address, <br>For example, `https://example.com/push`
POST_Header|False|""|Custom Post push Header, <br>Use json format (double quotes), the format is `{ "key1": "value1", "key2": "value2" }`, <br>For example, `{ "key1": "{log}", "key2": "{t}" }`, <br>If left blank, the Header is not set
POST_Data|False|""|Custom Post push Body, <br>Use json format (double quotes), <br>For example, `{ "key1": "{log}", "key2": "{t}" }`, <br>If left blank, the Body is not set

## Push Settings

After registering the push method in `Toolbox`->`Push Registration`, you can set the trigger conditions of the push method in `Toolbox`->`Push Settings`.

In `Push Settings`, you can set the push switch of each task, the task result push channel, the task result notification selection, and the task result batch push.

### Task Result Push Channel

The task result push channel is used to set the task result push channel. The task result push channel includes the following:

- [Bark Push](#bark-push)
- [Server Chan Push](#server-chan-push)
- [WXPusher Push](#wxpusher-push)
- [E-mail Push](#e-mail-push)
- [WeCom Application Push](#wecom-application-push)
- [Telegram Bot Push](#telegram-bot-push)
- [DingTalk Push](#dingtalk-push)
- [WeCom Webhook Push](#wecom-webhook-push)
- [Custom Push](#custom-push)

### Task Result Notification Selection

The task result notification selection is used to set when to push the task result. The task result notification selection includes the following:

- Manual execution success notification
- Manual execution failure notification
- Automatic execution success notification
- Automatic execution failure notification

`Notify after automatic error` can be set to push notifications after automatic execution fails several times. For example, if set to `3`, the notification will be pushed after automatic execution fails 3 times.

### Task Result Batch Push

The task result batch push is used to set the batch push of the task result. When `Enable batch push` is turned on, the task result within the specified time interval before the current push time will be batch pushed according to the `Batch push time setting` and `Batch push time interval` when the task result is pushed.

- `Batch push time setting`: The initial batch push time setting, for example, set to `12:00:00`, then a batch push will be made at `12:00:00` on the same day.

- `Batch push time interval`: Set how many seconds to push the task result once. The default is `86400` seconds, that is, the task result within 86400 seconds before the current push time will be batch pushed every day.
