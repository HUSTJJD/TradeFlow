# 港股通量化交易监控系统

这是一个基于 LongPort SDK 的量化交易监控程序，针对港股通标的进行实时监控，基于 MACD 策略生成买卖信号，并通过邮件推送通知。

## 功能特点

- **实时监控**：轮询监控指定标的（默认为热门港股）。
- **量化策略**：内置 MACD 波段策略，自动识别金叉/死叉。
- **邮件通知**：集成 SMTP 邮件服务，信号触发直达邮箱。
- **仓位建议**：提供基础的资金管理和仓位建议。

## 环境要求

- Python 3.8+
- LongPort 账户及 Open API 权限

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

1. 复制示例配置文件：
   ```bash
   cp config/config.yaml.example config/config.yaml
   ```
2. 编辑 `config/config.yaml` 文件：
   - 填写你的 LongPort App Key, App Secret 和 Access Token。
   - 填写邮件服务器配置（SMTP Server, Port, Sender, Receiver）以启用邮件通知。
   - 根据需要调整策略参数和监控标的列表。

或者设置环境变量（优先级高于配置文件）：

- `LONGPORT_APP_KEY`
- `LONGPORT_APP_SECRET`
- `LONGPORT_ACCESS_TOKEN`
- `SMTP_SERVER`
- `SMTP_PORT`
- `SENDER_EMAIL`
- `SENDER_PASSWORD`
- `RECEIVER_EMAIL`

## 运行

```bash
python run.py
```

## 自定义

- **标的池**：在 `config/config.yaml` 的 `monitor.symbols` 中添加或删除股票代码。
- **策略参数**：在 `config/config.yaml` 的 `strategy` 部分调整 MACD 参数或时间周期。
- **交易设置**：在 `config/config.yaml` 的 `trading` 部分调整资金和仓位比例。

## 开发指南

### 配置同步

为了保护敏感信息，项目包含 `config/config.yaml` (实际配置，被 git 忽略) 和 `config/config.yaml.example` (配置模板，提交到 git)。

当你修改了 `config/config.yaml` 的结构（如添加新参数）时，请运行以下命令将结构同步到模板，同时自动屏蔽敏感信息：

```bash
python scripts/sync_config.py
```

### 自动同步 (Git Hook)

你可以安装 git pre-commit hook，在每次提交前自动同步配置：

```bash
python scripts/sync_config.py --install
```

## 注意事项

- 本程序仅供学习和参考，不构成投资建议。
- 实盘交易请务必充分测试。
