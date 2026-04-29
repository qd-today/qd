# HAR 抓包教程

> 本文档介绍如何在 **网页浏览器** 和 **桌面 / 移动客户端抓包工具** 中导出 HAR 文件，供 QD 框架直接导入或交给 [AI 自动识别签到接口](./ai-sign-template.md)。

## 一、什么是 HAR？

HAR（**H**TTP **A**rchive）是一种 JSON 格式的浏览器抓包记录，包含完整的请求 URL、方法、Headers、Cookies、Body 与响应内容。QD 框架的核心是「重放 HAR 中的请求」，因此抓出一份正确的 HAR 是创建签到任务的第一步。

> 在线分析工具：<https://toolbox.googleapps.com/apps/har_analyzer/?lang=zh_CN>

## 二、抓包前的通用准备

无论用哪款工具，都建议：

1. **登录目标网站**：先用浏览器手动登录到能看到「签到」按钮的页面。
2. **关闭所有无关标签页**：减少干扰请求。
3. **确认是否需要二步验证 / 验证码**：如果有，请在抓包前完成。
4. **新开一个隐身窗口** 或 **清空网络面板** 后再开始抓包，得到的 HAR 更干净。

> 隐私提醒：HAR 中可能包含 Cookie、Token、邮箱等敏感信息，**不要直接发到聊天群、论坛**。如果上传到 QD 的 AI 分析功能，请确认你的 `AI_BASE_URL` 是可信服务（OpenAI、自部署 Ollama 等）。

---

## 三、浏览器（推荐，最简单）

### 3.1 Chrome / Edge / 国产 Chromium 浏览器

1. 在已登录的目标网站页面按 `F12` 或 `Ctrl + Shift + I`（macOS：`⌥ + ⌘ + I`），打开开发者工具。
2. 切到顶部的 **Network（网络）** 选项卡。
3. 确认左上角 **录制按钮（红色圆点）** 处于亮起状态；如果是灰色的，点一下让它变红。
4. 勾选 **Preserve log（保留日志）**，避免页面跳转后日志被清空。
5. 点击 **🚫 Clear（清除）** 按钮清空已有日志。
6. **现在去网页上手动点一次「签到」按钮**，等待页面提示签到成功。
7. 在请求列表区域 **右键 → Save all as HAR with content（另存为带内容的 HAR）**。
8. 选择保存位置，得到一个 `.har` 文件。

> 小技巧：如果签到流程包含跳转或弹窗，建议保持「Preserve log」一直勾选。

### 3.2 Firefox

1. 按 `F12` 打开开发者工具，切到 **网络** 面板。
2. 在面板顶部勾选 **持续日志（Persist Logs）**。
3. 点击 **垃圾桶图标** 清空。
4. 在页面上完成一次签到操作。
5. 在请求列表 **右键 → 全部另存为 HAR**。

### 3.3 Safari（macOS）

1. 先在 **Safari → 设置 → 高级** 中勾选「在菜单栏中显示开发菜单」。
2. 顶部菜单 **开发 → 显示 Web 检查器**。
3. 切到 **网络** 面板，点击 **导出** 按钮即可下载 HAR。

---

## 四、桌面客户端抓包工具

### 4.1 Fiddler Classic（Windows）

适合需要抓 **桌面客户端 / 老版本 IE / 不暴露给浏览器调试** 的请求。

1. 安装并打开 [Fiddler Classic](https://www.telerik.com/fiddler/fiddler-classic)。
2. 顶部菜单 **Tools → Options**。
   - **HTTPS** 选项卡：勾选 `Capture HTTPS CONNECTs` 与 `Decrypt HTTPS traffic`。第一次会弹窗安装根证书，**必须点击「是」**，否则抓不到 HTTPS 内容。
   - **Connections** 选项卡：默认监听端口 8888，勾选 `Allow remote computers to connect`（如需手机抓包）。
3. 重启 Fiddler 后，在浏览器或客户端里完成签到操作。
4. 在左侧请求列表选中相关请求（按住 `Ctrl` 多选；或使用 `Ctrl+A` 全选）。
5. 顶部菜单 **File → Export Sessions → Selected Sessions...**，选择 **HTTPArchive v1.2** 格式，导出为 `.har`。

### 4.2 Charles（Windows / macOS）

1. 安装 [Charles Proxy](https://www.charlesproxy.com/)，**Help → SSL Proxying → Install Charles Root Certificate**，按提示信任证书。
2. **Proxy → SSL Proxying Settings**，勾选 `Enable SSL Proxying`，添加目标域名（例如 `*.example.com:443`）。
3. 让客户端走 Charles 代理（Charles 会自动配置系统代理；macOS 也可以走 Charles 自己的端口 8888）。
4. 在客户端里完成签到操作。
5. 顶部菜单 **File → Export Session...**，选择 **HTTP Archive (.har)**。

### 4.3 mitmproxy / mitmweb（跨平台命令行）

适合开发者，纯本地运行：

```bash
# 1. 安装
pip install mitmproxy

# 2. 启动 web 界面，监听 8080 端口
mitmweb --listen-port 8080

# 3. 浏览器访问 http://mitm.it 安装根证书（按提示选系统）
# 4. 让客户端走 127.0.0.1:8080 代理
# 5. 完成签到操作
# 6. 在 mitmweb 界面 File → Save，选 HAR
```

或者纯命令行抓出 HAR：

```bash
mitmdump -s "$(python -c 'import mitmproxy.addons.savehar; print(mitmproxy.addons.savehar.__file__)')" -w out.har
```

### 4.4 Wireshark（不推荐用于 QD）

Wireshark 抓的是裸 TCP 包而非 HAR，需要解 TLS 才能看到 HTTPS 明文，**不能直接导出 QD 可用的 HAR**，不建议用于本场景。

---

## 五、移动端抓包

### 5.1 Android

1. 在电脑上启动 Charles / Fiddler / mitmproxy。
2. 手机和电脑连同一个 Wi-Fi。
3. **设置 → 无线和网络 → Wi-Fi → 长按当前网络 → 修改网络 → 高级 → 代理 → 手动**，填写电脑 IP + 抓包工具端口。
4. 浏览器访问对应工具的证书页（Charles 是 `chls.pro/ssl`，mitm 是 `mitm.it`），下载并 **设为「VPN 与应用」证书**。
5. **Android 7+** 默认不再信任用户证书，需要：
   - 应用是 debug 版：在 `network_security_config.xml` 显式信任用户 CA；
   - 或使用 Magisk 模块 `MoveCertificates` 把用户 CA 提升为系统 CA（需要 Root）。
6. 在目标 App 中完成签到，在抓包工具中导出 HAR。

### 5.2 iOS

1. 同上让 iOS 走电脑代理。
2. Safari 访问 `chls.pro/ssl` 下载描述文件 → **设置 → 通用 → VPN与设备管理** 安装。
3. **设置 → 通用 → 关于本机 → 证书信任设置**，把 Charles 证书的开关 **手动打开**（这一步极易忘）。
4. 完成签到，导出 HAR。

### 5.3 Stream / HttpCanary / 小黄鸟（移动原生抓包）

- iOS 上的 **Stream** 或 **Thor** App、Android 上的 **HttpCanary（小黄鸟）**、**Reqable** 都可以原生抓包。
- 抓到目标请求后，可以用「导出 → HAR」或「分享为文件」得到 `.har`。

---

## 六、抓包效果验证

抓完后 **务必先自己检查一遍** 再交给 QD：

1. 用文本编辑器打开 `.har`，搜索关键字（如 `sign`、`check`、`daily`）确认有相关请求。
2. 在 Chrome DevTools 里把 HAR **拖回 Network 面板**重新查看，可以可视化检查每条请求。
3. 检查 Cookie、Token 是否完整。如果是 OAuth Bearer Token，注意 Token 有效期，过期后需要重抓。

---

## 七、常见问题

| 问题 | 处理 |
| --- | --- |
| HTTPS 请求看不到内容（显示 Tunnel） | 没装根证书，按对应工具说明重装 |
| 抓到的 HAR 没有响应体 | 导出时漏勾「with content」/「保留响应体」 |
| 部分请求被「证书绑定（Pinning）」拒绝 | 用 SSLUnpinning 模块、Frida 脚本，或换调试版 App |
| 文件超过 50 MB QD 不让上传 | 在 DevTools 里只勾选少数关键请求再导出，或精简 HAR 中无关 entries |
| App 走的是 WebSocket / gRPC | 当前 QD 仅支持 HTTP(S)，不能直接重放 |

---

## 八、下一步

抓到 `.har` 文件后，有两条路：

1. **手动整理**：进入 QD 的「HAR 编辑器」 → **追加 HAR** 上传，逐条剔除噪声请求，再保存为模板。
2. **AI 一键识别**（推荐）：直接上传后点击 **「AI 智能识别签到」** 按钮，让 AI 自动挑出签到接口。详见 [AI 转换签到模板教程](./ai-sign-template.md)。
