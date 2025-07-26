# QD 项目指南

## 项目概述

QD 是一个基于 HAR Editor 和 Tornado Server 的 HTTP 请求定时任务自动执行框架，用于自动化 HTTP 请求任务。该项目使用 Python 构建，支持定时任务调度、请求模板管理和会话管理等功能。

## 架构

QD 项目的主要组件包括：

1. **Web 服务器**：基于 Tornado 的异步 web 服务器，提供 Web UI 和 API
2. **任务调度系统**：管理和执行定时任务，基于 APScheduler
3. **请求执行引擎**：Fetcher 负责执行 HTTP 请求，处理模板和环境变量
4. **数据存储**：支持多种数据库后端（如 SQLite、MySQL、PostgreSQL）
5. **Push 系统**：支持通过多种渠道（如 Telegram、钉钉等）推送通知

## 核心组件

- `qd.py`: 命令行入口，用于执行单个 HAR 模板
- `run.py`: 启动 Web 服务的入口点
- `libs/fetcher.py`: 核心请求执行引擎，处理 HTTP 请求执行和结果解析
- `libs/utils.py`: 通用工具函数
- `web/handlers/`: Web 请求处理程序，包含各种功能的路由处理
- `web/tpl/`: 前端模板文件
- `config.py`: 应用程序配置，定义系统全局设置和参数

## 工作流程

### 开发环境设置

1. 克隆仓库
2. 安装依赖 (推荐使用 pipenv)
   ```bash
   pipenv install
   ```
3. 配置 `config.py`
4. 运行 `run.py` 启动服务器
   ```bash
   python run.py
   ```

### 模板执行

模板执行可以通过命令行或 Web UI 完成：

```bash
python qd.py tpl.har [--key=value] [env.json]
```

其中：

- `tpl.har` 是 HAR 格式的请求模板
- `--key=value` 设置环境变量
- `env.json` 是包含环境变量的配置文件

### 代码约定

- **异步处理**：项目广泛使用 `asyncio` 进行异步操作，大部分 handler 和核心函数都是异步的
- **日志记录**：使用 `libs/log.py` 中的 Log 类进行日志记录，支持多种输出级别
- **错误处理**：根据 `config.traceback_print` 决定是否打印详细错误堆栈
- **环境变量**：模板中的变量使用 `{{ variable }}` 语法，在执行时会被替换

## 关键功能实现

### HAR 请求解析和执行

`libs/fetcher.py` 中的 Fetcher 类负责解析 HAR 文件并执行请求。它支持：

- 变量替换与渲染
- 会话管理与 Cookie 处理
- 结果提取与响应处理
- 错误重试机制

### 任务调度

任务调度使用 APScheduler 实现，在 `web/handlers/task.py` 中定义。定时任务支持：

- Cron 表达式定义执行时间
- 灵活的任务参数设置
- 任务日志记录与状态跟踪

### 消息推送

`libs/push.py` 实现了多种推送渠道，包括：

- Telegram
- 钉钉
- 企业微信
- Bark
- Serverchan 等

## 扩展和集成

- 可以通过 Docker 部署：项目提供了完整的 Docker 支持
  ```bash
  docker build -t qd .
  docker run -d -p 8923:8923 qd
  ```
- 支持自定义插件扩展功能（在 `libs/handler.py` 中扩展）
- 支持 WebUI 与 CLI 两种使用方式

## 调试技巧

- 启用调试日志：修改 config.py 中的 `debug` 为 `True`
- 单独测试请求：使用 `python qd.py` 命令行工具测试单个模板
- 查看任务日志：通过 Web UI 的任务页面访问详细执行记录

## 常见问题

- 端口冲突：`qd.py` 会检查端口是否被占用，如果被占用会自动启动服务
- 会话管理：请求之间的会话状态通过环境变量中的 `session` 字段维护
- 数据库连接问题：确保 `config.py` 中的数据库配置正确

## 参考文件

- `README.md`: 项目的主要文档
- `CHANGELOG.md`: 项目更新日志
- `/web/docs/`: 详细的用户指南
