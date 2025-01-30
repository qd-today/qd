# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

Nothing right now.

## [20250129] - 2025.01.29 更新

### Fixed

1. Bugfix(web): 🐛修复变量包装器以防止HTML注入

### Changed

1. chore(ci): 🛠️ 更新CodeQL分析配置
2. style(qd): ✨ 优化端口检查超时设置
3. refactor(web): 🔧 优化数据处理逻辑, 使用forEach替代map并添加parseInt以确保类型安全

## [20250128] - 2025.01.28 更新

### Fixed

1. Bugfix(worker): 🐛 模板成功失败数的修改独立至任务执行之外 fixed qd-today/qd#511
2. Bugfix(task_multi): 🐛 修复多任务定时随机值错误 fixed qd-today/qd#515
3. Bugfix(cookies): 🐛 增加框架中与getcookies扩展的通信数据标记 fixed qd-today/qd#571 by @ckx000 qd-today/qd#572

### Changed

1. Chore: 更新加速镜像 qd-today/qd#557
2. chore(depends): 🐳更新依赖项

## [20240210] - 2024.02.10 更新

### Fixed

1. Bugfix(web): 🐛 修复无法修改任务 fixed qd-today/qd#500
2. Bugfix(libs.utils): 🐛 587 端口使用 starttls 方法 fixed qd-today/qd#424
3. Bugfix(web): 🐛 管理员未验证邮箱开启强制验证失败

### Changed

1. Build(package): 🏗️ 更新包依赖

## [20240208] - 2024.02.08 更新

### Fixed

1. Fix 访客执行任务后端报错
2. Fix websockets 禁止跨域问题 (qd-today/qd#463)
3. Fix `cffi` Docker 构建
4. Fix telegram 消息格式，避免过多的无效信息干扰 (qd-today/qd#488)
5. Fix qd-today/qd#493: recovery permission (qd-today/qd#494)
6. Fix qd-today/qd#477: `api://` error when Server not bind `0.0.0.0` (qd-today/qd#495)
7. Fix 部分日志不显示错误详情（需打开 `config.traceback_print` 开关） qd-today/qd#491
8. Fix 无法跳转发布项详情
9. Fix 任务定时开关设置
10. Fix `incr_success` 应发生在事务即将结束前

### Changed

1. Update `entry_editor.html` (qd-today/qd#465)
2. Update 包依赖和前端依赖
3. Refactor 优化代码和 logger 格式和静态类型 by `pylint`/`flake8`/`mypy` (qd-today/qd#496)
4. Merge logger 和错误栈打印
5. Change 解析 Url 方式
6. Optimize `for` 循环调试显示
7. Change 删除公开模板时自动取消发布请求
8. Change 支持自定义单用户拥有记事本最大数量配置
9. Change 更改节日祝福判断

### Docs

1. Docs(contrib): 📚 修改贡献者展示

## [20230821] - 2023.08.21 更新

### Fixed

1. Fix 修复鼠标移动请求位置关系错乱的问题 (qd-today/qd#447)
2. Fix 修复删除模板导致无限推送问题 (qd-today/qd#462)

### Changed

1. Update web and backend packages
2. 优化企业微信推送错误提示

## [20230718] - 2023.07.18 更新

### Features

1. 添加 `bianscii` 模块中的方法至 jinja_global 域
2. `urlencode` 和 `urldecode` 支持指定编码 Feat qd-today/qd#437

### Changed

1. Add `html_unescape` option for unicode
2. 在 about.html 中添加 `_proxy` 和 `__log__` 说明 About qd-today/qd#427
3. 优化并完善 about.html 常用参数及过滤器信息显示
4. 企业微信代理支持 https 和 http 前缀
5. 优化注册推送 placeholder

### Fixed

1. Fix 后端与前端提取 header 正则不一致, 修改为以前端为准

## [20230618] - 2023.06.18 更新

### Features

1. 为 for 循环段 添加 `loop` 信息, 支持基于 `range` 和 `list` 的 for 循环
2. 测试中支持 if 控制语句, 优化测试中 if 控制语句的信息格式及错误信息显示
3. 添加 while 循环 Feat qd-today/qd#371

   > - 添加 `TASK_WHILE_LOOP_TIMEOUT` 环境变量, 单个 while 循环超时限制为 15 分钟;
   > - 添加 `TASK_REQUEST_LIMIT` 环境变量, 单个任务中请求数限制为 1500;
   > - 测试中支持 while 控制语句查看信息
   > - while 循环中支持 `loop_index` 和 `loop_index0`
   > - 具体可以查看前端 `关于` 页面信息

4. 时间戳 API 加入更多转换功能 Feat qd-today/qd#388

   > - 支持 `ts` 输入小数以输出毫秒及微秒级时间
   > - 支持使用 `%f` 作为毫微秒时间的格式化字符串

5. Telegram 消息标题增加 `hashtag` 以便于搜索 Feat qd-today/qd#401
6. 添加 `COOKIE_SECURE_MODE` 环境变量配置, 用于 HTTPS 下的 Cookie 安全设置开关
7. 添加 `STATIC_URL_PREFIX` 环境变量配置 Feat qd-today/qd#359
8. 添加 `display_import_warning` 配置
9. 允许使用 `update.sh` 修改 Alpine apk 镜像源

### Changed

1. 添加前端请求超时提示
2. 订阅公共模板以文件名作为默认模板名
3. 优化 `config.py` 文件配置内容顺序和注释
4. 优化邮箱设置

   > - 未配置 `DOMAIN` 环境变量或参数时, 禁止修改强制验证邮箱功能
   > - 未配置 `DOMAIN` 时, 邮箱推送自动失效并在后端日志提示
   > - 未配置 `DOMAIN` 时, 用户注册或修改密码时在前端提示
   > - 邮箱域名 `MAIL_DOMAIN` 合并入 `DOMAIN` 变量
   > - MailGun API 优化

5. 优化网站管理页面错误显示效果
6. 当设置重试间隔后允许重试间隔超过12小时
7. Update deployment, update, faq in docs
8. Clean and optimize code
9. Add description for left button
10. Update google analysis method
11. Update requirements.txt, replace `pytz` with built-in `zoneinfo`

### Fixed

1. Fix server disconnected for subscribe
2. Fix not display err msg for subscribe
3. Fix `qd.py` failure
4. Fix "Stream abnormally closed" which causes task not recorded in SQL db.
5. Fix set empty `retry_interval` not work
6. Fix typo

## [20230601] - 2023.06.01 更新

### Features

1. 添加 WebSocket 支持
2. 公共模板更新前端使用 WebSocket 推送更新进度

> **Tips: 反代用户需要进行 WebSocket 相关反代配置的设置或修改**

### Changed

1. 允许用户设置公共模板加速方式
2. update requirements packages
3. 前端 Query String Parameters 为空时自动修正 Request Url
4. 优化 Code quality

### Fixed

1. Fix 前端 RequestURL 自动将变量进行编码
2. Fix RequestUrl 丢失 QueryString 的 bug
3. Fix Request Payload 内容丢失的bug
4. Fix typo

## [20230518] - 2023.05.18 更新

### Features

1. 框架更名为 QD

### Changed

1. Update frontend js components
2. 节假日信息更改为前端脚本判断(Add lunar.js)
3. Replace querystring[deprecated] with qs
4. Update Dockerfile

### Fixed

1. Fix running multi DB instances
2. Fix password_md5 convert error
3. Fix encodeURIComponent error
4. Fix 更新公共模板时 Proxies 配置无效 Fix qd-today/qd#412

## [20230430] - 2023.04.30 更新

### Features

1. 我的模板中增加类似公共模板的备注说明 Feat qd-today/qd#366
2. 添加滑块识别验证码支持 Feat qd-today/qd#397
3. 支持网页恢复Sqlite数据库
4. 添加节假日庆祝信息

### Changed

1. 优化工具箱-记事本前端逻辑 Feat a76yyyy/qd#30
2. 修改网页端框架标题

### Fixed

1. 修复报错日志顺序异常 Fix qd-today/qd#391
2. Mandatory smtp authentication. Fix qd-today/qd#394
3. 修复网页显示时区与系统时区不一致 Fix qd-today/qd#396

## [20230228] - 2023.02.28 更新

### Features

1. 添加企业微信Webhook支持 feat qd-today/qd#361
2. 添加 [QD 文档站](https://qd-today.github.io/qd/)
3. 新建任务时自动提取模板变量 default 值 feat a76yyyy/qd#29

### Changed

1. 支持在API请求中使用 int(variable) 和 float(variable) 语法 fix qd-today/qd#374
2. 优化公共模板更新页面前端显示逻辑

### Fixed

1. 修复 config 文件夹不存在导致报错的bug Fix qd-today/qd#363

## [20230111] - 2023.01.11 更新

### Features

1. 支持6位cron定时 feat qd-today/qd#347
2. 成功失败条件支持jinja2格式变量 Support variables for success or fail asserts
3. Add keep-alive for updating subscribe
4. Add config "unsafe_eval_timeout"
5. Add config "task_max_retry_count"

### Changed

1. Use aiohttp to initiate requests
2. 更新 前端组件 & Use pnpm

### Fixed

1. 修复 if 判断表达式报错 Fix qd-today/qd#350 from odoo/odoo#101136
2. 修复 Typo
3. 其他优化和修复

## [20221218] - 2022.12.18 更新

1. 支持退订默认公共模板分支
2. 添加企业微信代理URL设置支持
3. 优化公开模板发布逻辑 fix qd-today/qd#321
4. 更新 openssl 和 ddddocr
5. 更新 前端组件
6. 修复 企业微信应用提示 mediaid 失败 fix qd-today/qd#316
7. 修复 Typo
8. 其他优化和修复

## [20220911] - 2022.09.11 更新

1. 允许用户选择定时任务执行方式
2. 修复 DIYPusher 的 bug
3. 其他优化和修复

## [20220901] - 2022.09.01 更新

1. 修复多个数据库转换问题
2. 修复前端 header 无法勾选的问题
3. 其他优化和修复

## [20220828] - 2022.08.28 更新

1. 添加多种 jinja2 过滤器并更新关于页面
2. 添加 Ja3 Dockerfile
3. 添加 curlToHAR feature close a76yyyy/qd#7
4. 添加 单账号多记事本 feature close qd-today/qd#154
5. 添加 SQLAlchemy ORM feature for qd-today/qd#253
6. Debug 日志模式记录 Tornado Client 请求
7. 优化公共模板更新性能, 仅 har version 更新时增量更新 content
8. 优化定时任务执行性能, 实现生产者-消费者异步队列模型
9. 其他优化和修复

## [20220728] - 2022.07.28 更新

1. 增加 if, else endif 关键字支持 (by [aa889788](https://github.com/qd-today/qd/commits?author=aa889788))
2. 不允许在单条请求中测试循环或条件控制语句
3. 添加控制语句API请求并修改插入API样式
4. 修复因空格导致的任务分组选择出错 Fix qd-today/qd#275
5. 其他优化和修复

## [20220525] - 2022.05.25 更新

1. 修复获取Cookie的Bug
2. 更新getcookie按钮机制
3. 修复保存har时Jinja Filter报错 Fix qd-today/qd#256
4. 更新 jsdelivr CDN
5. 修复分组名称以数字开头导致500报错 Fix qd-today/qd#261
6. 支持单独删除失败日志 Fix a76yyyy/qd#14
7. 定时页面显示单个任务是否已经定时
8. 当config.debug为True时, traceback_print默认为True
9. 手动执行任务失败后失败计次+1
10. 工具箱添加总日志显示 feat qd-today/qd#161

## [20220410] - 2022.04.10 更新

1. 关闭私有IP用户及API请求的evil限制
2. 优化网页端备份恢复数据库
3. 优化前端js占用容器空间
4. 添加源码方式更新容器重启提示
5. 支持自定义onnx导入及ocr调用

## [20220315] - 2022.03.15 更新

1. 更新求模板链接
2. 允许更多环境变量配置
3. 修复记事本为空时追加报错的bug
4. 控制access log的输出 (by [hiCasper](https://github.com/qd-today/qd/commits?author=hiCasper))
5. 未验证的管理员开启验证邮箱时尝试发送验证邮件
6. 优化Dockerfile,分离Redis
7. 添加qiandao-lite相关说明和配置
8. 统一DB连接操作,Cursor操作结束后自动关闭
9. 优化日志输出, 避免重复日志

> 源码部署更新方式如下, 如**更新后发生错误请重新拉取容器!**

 ``` bash
   # 先cd到源码所在目录, 执行命令后重启进程
   wget https://fastly.jsdelivr.net/gh/qd-today/qd@master/update.sh -O ./update.sh && \
   sh ./update.sh
   ```

## [20220208] - 2022.02.08 更新

1. 63c0074: 修复contenteditable=plaintext-only导致Firefox无法编辑的bug …
2. mysql可设置auth_plugin fix qd-today/qd #173
3. 采用本地方式调用部分js脚本
4. 使用grunt管理前端脚本和bower
5. 更新python版本及模块包版本
6. 为Github Packages建立基于源码更新的Latest Package
7. 添加OCR识别和目标检测API
8. 容器更新至Python 3.10
9. 添加自定义dns解析配置

> 请勿使用update.sh更新至此版本, 如**更新后发生错误请重新拉取容器!**

## [20211228] - 2021.12.28 更新

1. 修复jinja2模板变量导致推送日志失败的bug
2. 修复非管理员用户公共模板页面无法使用searchbar的bug
3. 添加Faker API函数用于创建伪数据
4. jinja过滤器优先使用内置random
5. 兼容 [Python 3.10](https://stackoverflow.com/questions/69381312/in-vs-code-importerror-cannot-import-name-mapping-from-collections/69727802#69727802)
6. 使用后端判断api接口地址(by [acooler15](https://github.com/qd-today/qd/pull/168))
7. 优化并统一网页渲染(by [acooler15](https://github.com/qd-today/qd/pull/169))
8. 支持管理员手动验证用户邮箱
9. 修复删除模板后无法点击相应任务的删除按钮的bug
10. 更新源码时自动更新Python模组包

## [20211217] - 2021.12.17 更新

1. 定期日志推送按模板分组 fix #153
2. 自定义全局Jinja2函数支持管道符模式
3. 支持dict和lispsum jinja2函数
4. contenteditable只允许纯文本编辑
5. 支持移动端下载模板
6. Jinja2模板引擎渲染出错时在前端显示500错误信息
7. 数据库password_md5字段加密，增加数据库安全性
8. 工具箱及站点设置均使用MD5密码传输
9. 修复使用jinja全局函数时前端变量显示undefined的bug
10. 修复$scope.preview_match前端报错的bug
11. 修复按钮空白区域无响应bug
12. 移除无用包

## [20211204] - 2021.12.04 更新

1. 修复前端全局匹配结果被toString()的bug
2. 公共模板、首页及用户管理页面添加排序及搜索功能
3. 修复自定义推送bug
4. 支持采用GB2312对字符串进行urlencode编码
5. 优化模板编辑界面插入请求按钮显示
6. 插入API支持插入时间戳,GB2312编码,RSA解码
7. 添加每日批量推送签到日志功能
8. 支持设置是否允许开启定期推送功能
9. 微信推送改为mpnews模板
10. 修复管理员改密后未同时修改password_md5的bug
11. 优化异步性能，避免网页加载导致阻塞
12. 更新软件包

## [20211115] - 2021.11.15 更新

1. 编辑任务时变量默认值为前值(by billypon)
2. 修复编辑任务时无法识别模板的新变量(by billypon)
3. 编辑任务逻辑优化(by billypon)
4. 修改备注长度
5. 修复更新错误后无法停止的bug

## [20211102] - 2021.11.02 更新

1. 修复前端无正则匹配显示结果
2. 修复工具箱-记事本
3. 更新update.sh以允许自定义更新方式
4. 加减乘除实现多组数据计算 fix qd-today/qd#136
5. 第一个用户默认为管理员，在config.py中设置或修改环境变量USER0ISADMIN (by [AragonSnow](https://github.com/qd-today/qd/commits?author=AragonSnow))

## [20211023] - 2021.10.23 更新

1. CRON添加随机延时 (by [acooler15](https://github.com/qd-today/qd/commits?author=acooler15))
2. 优化签到日志显示信息
3. 统一日志格式
4. API请求允许POST
5. 缩短手动执行任务前端响应时间
6. 修复无法将签到任务的重试次数设为0
7. 修复UnboundLocalError

## [20211017] - 2021.10.17 更新

1. 修复请求测试按钮绑定事件失效的bug
2. 多任务操作时显示优化
3. 公共模板允许同时退订多个仓库

## [20211016] - 2021.10.16 更新

1. 添加Tg Bot 和 DingDing Bot推送
2. 修复并优化日志推送功能
3. 日志推送允许'\r\n'换行
4. 修复验证邮箱bug
5. 允许开启热加载功能
6. 允许开启多进程功能(性能及存在问题未知)
7. 优化前端文件结构
8. 修复更新公共模板导致订阅空白的bug
9. 点击关于页面不再301重定向
10. 修复编辑模板页面显示序号问题

## [20211010] - 2021.10.10 更新

1. 修复数据库aip字段类型
2. 修复并优化公共模板添加、更新的性能
3. 关于页面优化并添加RSA加解密介绍
4. 修复不满足成功条件断言时显示OK的bug
5. 允许设置任务重试次数及重试间隔时间
6. Select控件支持搜索
7. 基于CoffeeScript重新编译js脚本
8. 优化框架文件结构

## [20210928] - 2021.09.28 更新

1. 更新并优化fetcher脚本
2. 更新输入提示(by [cxk000](https://github.com/qd-today/qd/commits?author=ckx000))
3. 修复{{unicode(arg)}}不能正常转换unicode的bug
4. 修复重复添加'|urlencode'的bug
5. 优化fetcher重试逻辑

## [20210917] - 2021.09.17 更新

1. 修复变量名冲突时自动添加'_'失效的bug
2. 支持socks5h代理
3. 添加har时可见postdata的text控件
4. 修复Proxies的bug

> **Tips: Socks5说明**
>
> Socks5h代理: socks5代理通过服务端进行域名解析.
>
> 如通过代理请求返回500或599错误时, 可尝试将 `socks5://host:port` 改为 `socks5h://host:port`, 以使用Socks5h方式请求

## [20210916] - 2021.09.16 更新

1. 代理允许添加账户密码
2. 修复unicode转换时不间断空格输出乱码的bug
3. 修复修改任务分组时分组名为中文导致的乱码bug
4. 支持socks5代理
5. 分别构建 Pycurl 与 QD 容器
6. 优化登录页面,"我的"首页和"多任务操作"页面(by [acooler15](https://github.com/acooler15/qiandao))

## [20210910] - 2021.09.10 更新

1. 添加全局代理黑名单机制
2. 完善时间戳API
3. 修复重置密码功能
4. 修复前端正则表达式全局匹配和匹配为空时的bug
5. 允许正则表达式匹配修饰符'/s'和'/u'
6. 添加参数时在末尾添加(by [billypon](https://github.com/billypon/qiandao/commit/243220407809863ddf7805be193954021eea65ce))
7. 修复header['name']为空时报错的bug(20210912)

> **Tips: 全局代理黑名单机制说明**

   ```python
   # 以下为全局代理域名列表相关设置
   # proxies为全局代理域名列表, 默认为空[], 表示不启用全局代理;
   # 代理格式应为'scheme://username:password@host:port',例如:proxies = ['http://admin:admin@127.0.0.1:8923','https://proxy.com:8888'];
   # 任务级代理请在新建或修改任务时添加,任务级代理优先级大于全局代理;
   proxies = os.getenv('PROXIES', '').split('|')               # 若希望部分地址不走代理, 请修改proxy_direct_mode及proxy_direct
   proxy_direct_mode = os.getenv('PROXY_DIRECT_MODE', '')      # 默认为空, 可选输入:'url'为网址匹配模式;'regexp'为正则表达式匹配模式;''空则不启用全局代理黑名单
   # proxy_direct_mode = os.getenv('PROXY_DIRECT_MODE', 'url')进入网址完全匹配模式, 在proxy_direct名单的url均不通过代理请求, 以'|'分隔url网址, url格式应为scheme://domain或scheme://domain:port
   # 例如: proxy_direct = os.getenv('PROXY_DIRECT', 'http://127.0.0.1:80|https://localhost');
   # proxy_direct_mode= os.getenv('PROXY_DIRECT_MODE', 'regexp')进入正则表达式匹配模式, 满足正则表达式的网址均不通过代理请求;
   # 启用regexp模式后自动采用以下默认匹配正则表达式, 如无特别需求请勿修改
   proxy_direct = os.getenv('PROXY_DIRECT', r"""(?xi)\A
                  ([a-z][a-z0-9+\-.]*://)?                                                        # Scheme
                  (0(.0){3}|127(.0){2}.1|localhost|\[::([\d]+)?\])                                # Domain/Hostname/IPv4/IPv6
                  (:[0-9]+)? """                                                                  # :Port
                  )
   ```

## [20210908] - 2021.09.08 更新

1. 修复提取变量处输入正则表达式频繁卡顿的bug
2. 修复提取变量处正则表达式错误导致500的bug
3. 输入变量名与API变量冲突时自动添加 '_'
4. 修复导入har自动提取API函数名作为变量导致500报错的bug
5. 前端更新

> **Tips: 20210906 -> 20210908版本更新了Python相关特性和前端脚本, 不再与旧版python兼容, 请升级至Python 3.6及以上**

## [20210907] - 2021.09.07 更新

1. 修复单独调用worker脚本时的异常bug
2. 允许设置新建任务后准备延时时间
3. 更新代码以适配python3的async/await特性
4. 更新API和关于页面

## [20210906] - 2021.09.06 更新

1. 签到日志支持使用 '\r\n' 进行换行
2. 面板备份还原数据失败添加提示
3. 修复我的模板分组按钮不显示已有分组的bug
4. 修复新建任务时分组名为中文导致的乱码bug

## [20210905] - 2021.09.05 更新

1. 优化任务前值显示方案
2. 修复IPv6访问时的bug
3. 管理用户界面添加用户最后登录IP显示
4. 我的页面添加分组任务“全选/反选”复选框

## [20210903] - 2021.09.03 更新

1. 修复更新新版框架后因旧版框架cookie缓存导致的500错误
2. 修复util编解码问题
3. 添加368和armv6架构容器构建
4. 优化插入请求功能
5. 修复pycurl导致若干500和599错误
6. 更新需求模块

## [20210902] - 2021.09.02 更新

1. 修复Image解码失败的bug
2. 添加请求时限设置
3. 修复延时API超过请求时限导致的bug
4. 查看任务的模板数据时自动导入任务变量(by [billypon](https://github.com/billypon/qiandao))
5. 默认去除pycurl模组, 解决部分500和599错误

   ```bash
   # 如需使用Proxy功能请安装PyCurl
   # Windows源码运行, 请执行 pip install pycurl==7.43.0.5
   pip install pycurl # pip3 install pycurl
   # 如因curl导致500或599错误, 请卸载PyCurl或修改环境变量USE_PYCURL为False
   # pip uninstall pycurl
   ```

## [20210807] - 2021.08.07 更新

1. 更新Wiki
2. 修复网页编码导致的Body解析bug

## [20210731] - 2021.07.31 更新

1. 修复旧版数据库导致的编码bug
2. 添加部分说明
3. 优化docker配置
4. 允许headers中文编码
5. 修复不间断空格导致的编解码bug
6. 修复delay延时功能
7. 增加log的详细错误显示

## [20210729] - 2021.07.29 更新

1. 修复异常抛出时泄露源码路径的bug
2. 修复原sql的groups字段bug
3. 优化DockerFile及配置文件

## [20210728] - 2021.07.28 更新

1. 适配python版本至python3.8

## [20210628] - 2021.06.28 更新

1. 修改Dockfile,采用密钥更新

## [20210626] - 2021.06.26 更新

1. 公共仓库添加评论功能, 跳转到github, 国内打不开的问题自行解决
2. 公共仓库添加强制更新按钮
3. 修复mysql创建数据库错误
4. 修复about页面打开500错误

## [20210621] - 2021.06.21 更新

1. 重写公共模板仓库的订阅方法, 允许添加第三方库(具体规范参考)
2. 模板使用缓存的方式, 默认是每隔一天重新读取, 可以手动刷新缓存
3. 新增多任务禁用/启用/删除/定时/分组
4. 任务和模板分组栏修改颜色
5. 修复注册用户时没有创建md5密码的bug

## [20210413] - 2021.04.13 更新

1. 添加proxy功能, 目前暂时不可用(By billypon)

## [20210220] - 2021.02.20 更新

1. 完善MD5
2. 修复部分站点500的问题
3. 公共模板添加清缓存功能
4. 修复容忍错误推送的失效的BUG
5. 主循环修改为0.5s, 使定时运行更准确
6. 修复/register没有注册按钮的BUG
7. 密码验证修改为md5
8. 更换默认微信推送图片

## [20210122] - 2021.01.22 更新

1. 整合推送模块
2. 添加定时cron支持
3. ENABLE_HTTPS 使能时邮件链接为https

## [20210117] - 2021.01.17 更新

1. 添加企业微信支持
2. 支持在用户管理里修改密码

## [20210116] - 2021.01.16 更新

1. 修复点击登陆失败后注册按钮消失的问题

## [20210113] - 2021.01.13 更新

1. 启用邮箱验证前必须验证管理员邮箱

## [20210108] - 2021.01.08 更新

1. 修复20210122注册按钮丢失的BUG
2. 添加记事本访问接口
3. 添加自定义推送示例
4. sqlite3_db_task_converter放在web启动之前

## [20210107] - 2021.01.07 更新

1. 底部添加本项目链接
2. 禁止注册时隐藏注册按钮
3. 显示注册推送的前值
4. 添加记事本功能, 用户可以将数据保存在本地
5. 推送注册和推送设置按钮移动到工具箱
6. 定时时间以任务起始时间为依据
7. 新增自定义推送功能
8. bark推送改为POST, 可以推送日志

## [20201224] - 2020.12.24 更新

1. 修复模板编辑中'{{变量}}'自动urlencode的问题

## [20201223] - 2020.12.23 更新

1. 添加EMAIL发送开关

## [20201222] - 2020.12.22 更新

1. 修复任务运行结束后'logDay'报错
2. 邮箱变量设置为环境变量获取

## [20201204] - 2020.12.04 更新

1. 修复任务运行结束后'logDay'报错

## [20201120] - 2020.11.20 更新

1. 修复模板订阅时url太长报错的问题, 模板按照修改时间来排序
2. 支持网站设置仅保留一定天数的日志, 日志清理时间在任务成功完成之后,默认365天
3. 手动清除一定天数的日志
4. 分组折叠/展开 支持记忆
5. 修复模板编辑页面反选错误的bug

## [20201105] - 2020.11.05 更新

1. 用户管理, 备份, 网站管理, 密码不显示明文, 不输入账号密码返回页面显示中文

## [20201031] - 2020.10.31 更新

1. 允许普通用户备份/恢复
2. 模板编辑页显示请求排序
3. 模板编辑页可以同时删除多个请求
4. 主页允许多项操作删除/分组, 取消分组的勾选框, 改为点击即可显示隐藏
5. 公共仓库打开失败时使用本地仓库

## [20200918] - 2020.09.18 更新

1. 允许备份/恢复 用户的所有任务和模板
2. 修复模板编辑时, 变量作为url会自动url转码的bug
3. 模板编辑时允许拖拽请求
4. 模板订阅添加错误显示, 避免500

## [20200914] - 2020.09.14 更新(By liubei121212)

1. 添加 unicode 函数
2. 优化 api 页样式
3. 在模板编辑页中测试时也可以复制错误信息了
4. 优化日志页复制错误信息的实现方式
5. 添加常用 api/过滤器
6. 修复主页和推送设置中长用户名的显示
7. 前值、edit 页面的错误信息增加复制按钮

## [20200910] - 2020.09.10 更新

1. 鉴于github 污染严重, 使用gitee代替作为订阅源
2. 首页的检查模板更新取消, 打开公共模板仓库会自动检查更新
3. 修复邮箱验证, 注册后未验证可以再次点击注册验证
4. 修改任务时显示前值

> **Tips:** 本次更新有js脚本更新, 请开启chrome 的 “disable cache”功能更新js脚本

## [20200907] - 2020.09.07 更新

1. 在数据库管理中增加一键备份/恢复所有模板的功能

## [20200901] - 2020.09.01 更新

1. 正则提取支持post方式
2. 取消getcookie插件提示(By powersee)
3. 管理员可以查看用户是否验证邮箱, 可以设置不验证邮箱无法登陆
4. 支持任务分组
5. 推送带上任务备注

## [20200719] - 2020.07.19更新

1. 修改按钮“推送通知开关”为“推送设置”
2. 添加错误提醒容忍。在自动签到到一定次数错误后, 才推送提醒。

## [20200717] - 2020.07.17更新

1. 使报错显示中文, 添加点击复制错误日志按钮(by [liubei121212](https://github.com/liubei121212/qiandao))
2. 主页版本从alpha修改为20200717

## [20200709] - 2020.07.09更新

1. 添加 管理员 备份数据库功能
2. 添加任务日志清空功能
3. 修复定时的随机延时取消失败的BUG
4. 添加任务禁用功能
5. 为了提高兼容性, 请求不验证SSL

## [20200622] - 2020.6.22 更新

1. 修复检查公共模板更新功能；
2. 美化左侧三按钮(By 十六君)
3. 修复插入RSA加密实际是字符串替换的BUG
4. 修改请求为不验证SSL, 提升兼容性

## [20200614] - 2020.6.14 更新

1. 添加RSA加密/解密
2. 用户管理页面添加用户最后登陆时间
3. 字符串替换功能可以返回纯文本, 避免有转义'\\'的出现,需要替换参数r=text

## [20200612] - 2020.6.12 更新

1. 定时日志BUG太多, 修不过来, 取消此功能
2. 修复用户不存在时登录500错误

## [20200611] - 2020.6.11 更新

1. 修复MySQL的支持, 不需要手动更新Mysql数据库

## [20200610] - 2020.6.10 更新

1. 添加管理员管理用户功能, 可以将用户禁用/启用/删除
2. 添加关闭/开启注册功能
3. 修改主页的'检查更新'为'检查模板更新'

> **Tips:** 使用前需要进入容器, 将对应已注册邮箱设置为管理员 :
>
>   ``` bash
>   docker exec -it 容器名 /bin/bash
>   python ./chrole.py 邮箱 admin
>   ```
>
> 被禁用的账户将不能登录网站,所有任务将被禁用。
> 被删除的账户, 会删除该用户的所有任务, 模板和日志
>
> 如果使用mysql 在 20200604 请使用以下命令 :
>
> ``` sql
> ALTER TABLE `user` ADD `status`  VARBINARY(1024) NOT NULL DEFAULT 'Enable';
> CREATE TABLE IF NOT EXISTS `site` (
>          `id` INTEGER NOT NULL PRIMARY KEY,
>          `regEn` INT UNSIGNED NOT NULL DEFAULT 1
>       );
> INSERT INTO `site` VALUES(1,1);
> ```

## [20200606] - 2020.6.6 更新

1. 修复用户不存在依然能登陆的BUG(具体表现为 : 新用户新建模板保存时500错误, 注册推送时提示NoneType)
2. 完善注册推送的注册消息
3. 修复自动完成不推送的bug
4. 添加定时 “今日已签过” 选项, 可以直接定时第二天
5. 修复公共模板的HAR订阅功能

## [20200605] - 2020.6.5 更新

1. 修复 sqlite3 数据库初始值错误的问题, 仅影响新建数据库的用户

## [20200604] - 2020.6.4 更新

1. 根据反馈, HAR编辑里插入链接修改默认地址为localhost
2. 修复2020601版, 插入请求后修改为localhost地址, 点击测试的500错误的问题
3. 支持定时后 随机延时

> **Tips:** 本次更新会把之前的定时设置全部取消, 介意请勿更新
>
> 如果使用 mysql 在 20200601 请使用以下命令:
>
> ``` sql
> ALTER TABLE  `task` ADD `newontime`  VARBINARY(256) NOT NULL DEFAULT '{\"sw\":false
> \"time\":\"00:10:10\",\"randsw\":false,\"tz1\":0,\"tz2\":0 }'
> ```
>
> 延时的另一种用法, 间隔定时运行 : 如果要实现每1周定时运行一次, 设置最大最小值都是604800, 即可

## [20200601] - 2020.6.1 更新

1. 时间显示修改为具体时间, 取消之前的 "1小时后"等模糊显示(By 戏如人生)
2. 新建任务时可以选择分组
3. Bark推送支持保存历史信息, 需要升级APP。
4. HAR编辑里添加添加插入unicode解码, url解码, 正则表达式, 字符串替换的功能

## [20200531] - 2020.5.31 更新

1. 修复定时 ‘day out of month’ 的BUG
2. 取消定时界面的今日运行选项, 自动判断当前时间是今天还是第二天
3. 集成了时间戳获取、unicode转换、url转换功能(By [gxitm](https://github.com/gxitm))
4. 集成了正则表达式、字符串替换功能。

## [20200530] - 2020.5.30 更新

1. 修改 任务失败时 推送的消息内容为 任务日志；
2. 因浏览器支持不好, 取消 2020.5.18更新的 ‘模板上传指定格式为.har’；
3. 新增模板编辑 追加HAR 的功能；
4. 新增模板请求删除功能。

## [20200526] - 2020.5.26 更新

1. 修复定时日志发送的最后一条日志的bug
2. 修复定时日志出错影响程序运行的bug

## [20200525] - 2020.5.25 更新

1. Bark, S酱, WXPusher 注册合并为一个按钮
2. 任务推送支持注册后也能关闭
3. 支持分任务开/关推送
4. 新增每日日志功能, 可以将每日定时前的最后一个日志推送到S酱和WXPusher
5. 修复“↓”按钮定位不准的bug

> **Tips:** 如果使用mysql 在 5.22 请使用以下命令 :
>
> ``` sql
> ALTER TABLE `task` ADD `pushsw` VARBINARY(128) NOT NULL DEFAULT '{\"logen\":false,\"pushen\":true}';
> ALTER TABLE `user` ADD `logtime` VARBINARY(128) NOT NULL DEFAULT '{\"en\":false,\"time\":\"20:00:00\"\"ts\":0,\"schanEn\":false,\"WXPEn\":false}';
> ```

## [20200522] - 2020.5.22 更新

1. 分组增加折叠/展开功能
2. 左侧增加新建模板按钮, “↑”回到顶部,  “↓”表示跳转到模板页面
3. 修复删除任务时日志不删除bug

## [20200519] - 2020.5.19 更新

1. 添加手动检查模板更新的按钮。

   > **Tips:** 如果使用mysql 在 5.18 请使用以下命令 :
   >
   > ``` sql
   > ALTER TABLE `tpl` ADD `tplurl` VARCHAR(1024) NULL DEFAULT '' ;
   > ALTER TABLE `tpl` ADD `updateable` INT UNSIGNED NOT NULL DEFAULT 0;
   > ```

## [20200518] - 2020.5.18 更新

1. 定时的 "今日是否运行" 修改 为 "今日运行"
2. 添加模板订阅功能, 仓库地址在[https://github.com/qd-today/templates](https://github.com/qd-today/templates)

   > **Tips:** 主页打开公共模板按钮, 点击订阅后自动导入模板, 需要自己确认保存

3. 模板上传指定格式为.har

## [20200516] - 2020.5.16 更新

1. 添加任务分类功能

   > **Tips:** 如果使用mysql 请使用以下命令 :
   >
   > ``` sql
   > ALTER TABLE `task` ADD `_groups` VARBINARY(128) NOT NULL DEFAULT 'None' ;
   > ```

2. 定时功能显示之前的定时值

## [20200512] - 初始版本

1. 签到框架基于quchaonet的蓝调主题

2. 设置任务最低间隔时间及任务request最高100限制 (by 戏如人生)

   <http://cordimax.f3322.net:5558/381.html>

3. 增加了server酱、bark推送, WXPusher推送, 并可以设置推送开关（by AragonSnow）
   需要推送的 : 登录账号以后点击注册bark/s酱/WXPusher, 测试推送没有问题以后,再点击提交

4. 增加定时功能, 在新建任务以后会出现定时按钮, 设置每天的定时时间。

> **Tips: 不兼容旧版的数据库,  旧版数据库导入会自动转换, 旧版将无法使用**
>
> **使用SQLite3的, 默认路径改为config文件夹里面, 方便挂载后备份**
>
> **使用Mysq的,请使用一下命令更新数据库:**
>
> ``` sql
> ALTER TABLE `task` ADD `ontimeflg` INT UNSIGNED NOT NULL DEFAULT 0;
> ALTER TABLE `task` ADD `ontime` VARCHAR(256) NOT NULL DEFAULT '00:10:00';
> ALTER TABLE `user` ADD `skey` VARBINARY(128) NOT NULL DEFAULT '' ;
> ALTER TABLE `user` ADD `barkurl` VARBINARY(128) NOT NULL DEFAULT '' ;
> ALTER TABLE `user` ADD `wxpusher` VARBINARY(128) NOT NULL DEFAULT '' ;
> ALTER TABLE `user` ADD `noticeflg` INT UNSIGNED NOT NULL DEFAULT 1;
> ```
