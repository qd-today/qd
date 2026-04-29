# 使用 AI 自动生成签到模板

> QD 框架在 HAR 编辑器中内置了 **AI 智能识别签到** 功能：上传抓包后一键调用大模型，自动从几十上百条请求中挑出真正的签到接口，跳过手动剔除噪声请求的繁琐过程。

> 本教程基于 PR：`feat: AI 智能签到识别 + worker N+1 优化与安全告警`。

## 一、功能概述

- **输入**：浏览器或客户端导出的 HAR 文件（参见 [HAR 抓包教程](./har-capture.md)）。
- **输出**：一份只包含 1-3 条关键签到请求的最小化 HAR，可直接保存为 QD 模板执行。
- **底层协议**：兼容 OpenAI Chat Completions（`/v1/chat/completions`）。
  - 可对接 **OpenAI**、**DeepSeek**、**通义千问**、**Moonshot**、**OpenRouter** 等云服务；
  - 也可对接 **本地 Ollama / LM Studio / vLLM**（开启 OpenAI 兼容模式即可）。

---

## 二、启用 AI 功能

### 2.1 准备 API Key

挑一家提供 OpenAI 兼容协议的服务商，注册后拿到 API Key。下表是常见可选项（任选其一）：

| 服务 | Base URL | 推荐模型 |
| --- | --- | --- |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` / `gpt-4o` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 通义千问（阿里云 DashScope） | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` / `qwen2.5-72b-instruct` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| OpenRouter | `https://openrouter.ai/api/v1` | 任意模型 ID |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5:14b` 等 |

### 2.2 配置环境变量

在 `docker-compose.yml` 中找到 QD 服务的 `environment` 段，加入：

```yaml
services:
  qd:
    environment:
      - AI_API_KEY=sk-xxxxxxxxxxxxxxxx       # 必填，留空即关闭功能
      - AI_BASE_URL=https://api.deepseek.com/v1   # 可选，默认 https://api.openai.com/v1
      - AI_MODEL=deepseek-chat                # 可选，默认 gpt-4o-mini
      - AI_TIMEOUT=60                         # 可选，单次请求超时秒数
      - AI_MAX_HAR_ENTRIES=60                 # 可选，单 HAR 最多保留多少条请求送给 AI
```

非 Docker 部署可直接 `export AI_API_KEY=sk-xxx` 后再启动 `python run.py`，或写到 `local_config.py`。

### 2.3 重启生效

```bash
docker compose up -d --force-recreate qd
```

启动日志若不再出现 `[安全] COOKIE_SECRET 未设置...` 等告警即代表 QD 已成功读取你的环境变量。

### 2.4 验证

打开任意一个 HAR 编辑器页面（侧栏「HAR 模板」 → 新建 / 编辑任一模板），看右上角的按钮区域：

- 出现 **「AI 智能识别签到」** 按钮 → 启用成功。
- 仍未出现，或弹窗提示 `AI 功能未启用` → 检查环境变量是否生效（容器内执行 `env | grep AI_`）。

也可以直接请求接口：

```bash
curl http://your-qd-host:8923/har/ai_status
# {"enabled": true, "model": "deepseek-chat"}
```

---

## 三、操作步骤

### 第 1 步：准备 HAR

按 [HAR 抓包教程](./har-capture.md) 抓出一份 `.har` 文件，**确保里面包含一次完整的签到操作**。

### 第 2 步：进入 HAR 编辑器并导入

1. 在 QD 顶部菜单进入 **HAR 模板**，点 **新建**（或编辑任意已有模板）。
2. 点击 **追加 HAR** → 选择 `.har` 文件 → **上传**。
3. 此时左侧会出现几十甚至上百条请求。

### 第 3 步：AI 智能识别

1. 点右上角 **「AI 智能识别签到」** 按钮。
2. 弹窗中：
   - **提示词（可选）**：留空也能跑。如果你知道签到的中文叫法，可以填「每日签到」「积分领取」「打卡」等关键词，识别准确率更高。
   - 当 AI 配置正确时会显示当前模型名（如 `deepseek-chat`）。
3. 点 **开始分析**，等待 5-30 秒（取决于模型与网络）。
4. 分析完成后弹窗下方会显示 AI 给出的 JSON 结果，包括：
   - `sitename` / `siteurl` / `note` —— 站点信息建议
   - `entries[]` —— 识别出的关键请求（含原始 URL、Method、Body、识别理由）
   - `variables[]` —— 提示你需要补哪些变量（通常是 cookie / token）
   - `success_keyword` —— 签到成功响应中的关键字
5. 检查无误后点 **应用为当前模板**：编辑器中所有原始请求会被替换为 AI 给出的最小集合。

### 第 4 步：补充变量并测试

1. 编辑器右侧是变量面板，AI 一般会建议 `cookie` 等变量。点 **测试**。
2. 在测试弹窗里填入 `cookie`（可点 `点击获取` 借助 Get-Cookies 浏览器插件），其他变量按需填写。
3. 点击 **测试**，看响应是否包含「签到成功」「已签到」等关键字。
4. 测试通过后，回到编辑器点 **保存**。

### 第 5 步：创建任务

回到「HAR 模板」列表 → 选中刚保存的模板 → **新建任务**，填写定时表达式（如 `0 8 * * *` 每天早 8 点），保存即可。

---

## 四、提示词使用建议

提示词不是必填，但能显著提高识别精度。以下是典型场景：

- **签到名称不是「签到」**：填「积分」「打卡」「补卡」「采集」「领取」等真实按钮文案。
- **HAR 中混入了多个站点**：填站点名 + 操作，例如 `bilibili 视频心跳` 或 `nas-tools 每日刷流`。
- **明确排除某类请求**：填「忽略登录请求，只要签到接口」。
- **多步签到**：填「签到接口可能需要先获取 token 再 POST，请按顺序返回」。

---

## 五、AI 工作原理（FAQ）

**Q: AI 会泄漏我的 Cookie / Token 吗？**
- 后端在送给 AI 之前会做预处理：仅保留 `Content-Type` / `Referer` / `Origin` / `Authorization` / `X-CSRF-Token` 等少量必要 header；Cookie 只送 **名称**（不送值）；请求体超过 500 字符会截断。
- 你的 API Key 调用的是你自己选定的 `AI_BASE_URL`，请确认那是可信服务。如果非常敏感，建议用本地 Ollama。

**Q: AI 给出的结果不对怎么办？**
- 重新点 **开始分析** 重试一次（AI 输出有随机性）。
- 在「提示词」里写得更具体。
- 改用更强的模型（如 `gpt-4o`、`deepseek-chat`、`qwen2.5-72b-instruct`）。
- 若仍不行，AI 给出的 JSON 可作为参考，手动在编辑器里调整请求列表。

**Q: 一次请求消耗多少 Token？**
- HAR 经预处理后每条 entry 大概 0.2-0.5 KB，默认上限 60 条 = ~30 KB ≈ 8K-12K input tokens。
- 输出极短（一般 < 1K tokens）。
- 用 `gpt-4o-mini` 单次费用约 0.001 美元；DeepSeek、通义更便宜。

**Q: 返回 502 / 超时？**
- 模型服务挂了或被墙，换 `AI_BASE_URL`。
- 调高 `AI_TIMEOUT`（最大可设到 300 秒）。
- HAR 太大，调小 `AI_MAX_HAR_ENTRIES`（如 30）。

**Q: 我能否在没有图形界面的情况下调用？**
- 可以。后端暴露了 REST 接口：

  ```bash
  curl -X POST http://your-qd-host:8923/har/ai_analyze \
       -H 'Content-Type: application/json' \
       -H "Cookie: $(your-login-cookie)" \
       --data-binary @payload.json
  # payload.json: {"har": <HAR JSON>, "hint": "每日签到"}
  ```
  返回 `{ok: true, har: ..., result: ...}`。

---

## 六、安全与合规

1. **不要把生产 API Key 写进公共仓库**。Docker 部署用 `.env` 文件；裸机部署用 `local_config.py` 并加入 `.gitignore`。
2. **抓包前阅读目标站点的服务条款**：自动化签到在某些站点上是被允许的（积分、签到送奖励），在某些 SaaS 上明确禁止 —— 自己评估风险。
3. **不要替朋友 / 网友抓 HAR**：HAR 内含完整身份凭据，本质上等同于「把账号给别人」。
4. **建议使用本地模型**：长期高频使用建议 Ollama + Qwen2.5 14B / 32B，零外发数据，离线可用。

---

## 七、相关链接

- [QD 官方文档](https://qd-today.github.io/qd/zh_CN/)
- [HAR 抓包教程](./har-capture.md)
- [使用指南：如何使用](./how-to-use.md)
- [常见问题](./faq.md)
