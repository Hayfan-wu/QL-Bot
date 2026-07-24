# QL-Bot · QQ 机器人控制框架

基于 NapCatQQ 反向 WebSocket 的通用 QQ 机器人插件化框架。

本仓库只负责 QQ 群交互与控制调度，不管理任何业务脚本。业务项目把 QQ 控制插件放在自己的仓库中，QL-Bot 启动时自动扫描加载，**无需修改 QL-Bot 的 `.env` 即可新增业务项目**。

## 设计思路

```
QL-Bot/           <- 本仓库：QQ 机器人框架
├── main.py
├── bot/
│   ├── core.py
│   ├── project_loader.py   <- 自动扫描业务项目插件
│   ├── plugins/
│   │   └── example.py      <- 内置示例插件
│   └── ...
└── .env                     <- 只放机器人核心配置

/opt
├── QL-WPS/       <- 业务仓库：WPS 自动脚本
│   ├── wps_auto.py
│   ├── .env
│   └── bot_plugins/
│       └── wps.py          <- WPS 的 QQ 控制插件
│
├── QL-SF/        <- 业务仓库：顺丰脚本（示例）
│   ├── sfsy.py
│   ├── .env
│   └── bot_plugins/
│       └── sf.py
```

## 核心原则

- **QL-Bot `.env` 不存储任何业务项目配置**
- 业务项目的青龙地址、脚本路径、Token 等全部放在各自仓库的 `.env`
- 新增业务项目只需 `git clone` 到 `/opt` 下，重启 QL-Bot 即可自动加载

## 快速开始

### 1. 克隆仓库

```bash
cd /opt
git clone https://github.com/Hayfan-wu/QL-Bot.git
cd QL-Bot
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
nano .env
```

```bash
# 机器人核心配置（只填这些）
QQ_BOT_QQ=你的机器人QQ号
NAPCAT_API=http://127.0.0.1:3000
ADMIN_QQ=你的QQ号
WS_HOST=0.0.0.0
WS_PORT=8080
WS_PATH=/onebot/v11/ws/
PROJECT_SCAN_DIRS=/opt
```

### 3. 启动

```bash
python3 main.py
```

启动后会自动扫描 `/opt` 下所有项目的 `bot_plugins/` 目录并加载插件。


## 新增业务项目（无需改 QL-Bot）

假设要新增一个「京东」项目：

### 1. 创建业务仓库 `QL-JD`

```
QL-JD/
├── jd_auto.py
├── .env
└── bot_plugins/
    └── jd.py
```

### 2. `QL-JD/.env` 放项目自己的配置

```bash
QL_URL=http://127.0.0.1:5700
QL_CLIENT_ID=你的client_id
QL_CLIENT_SECRET=你的client_secret
```

### 3. `QL-JD/bot_plugins/jd.py` 写控制插件

```python
# -*- coding: utf-8 -*-
import re
from bot.plugins.base import Plugin
from bot.project_env import ProjectEnv

class JdPlugin(Plugin):
    name = 'jd'
    commands = [re.compile(r'^JD\s*登录', re.IGNORECASE)]

    def handle(self, text, sender_id, group_id=None):
        env = ProjectEnv(self.project_dir)
        return f'京东插件已加载，项目目录：{self.project_dir}'
```

### 4. 部署到服务器

```bash
cd /opt
git clone https://github.com/你的账号/QL-JD.git
```

### 5. 重启 QL-Bot

```bash
cd /opt/QL-Bot
git pull   # 框架本身无需改动
pkill -f "python3 main.py"
export $(cat .env | grep -v '^#' | xargs)
nohup python3 main.py > main.log 2>&1 &
```

无需修改 QL-Bot 的 `.env` 或任何代码。

## 业务项目插件开发规范

1. 插件文件必须放在业务项目根目录的 `bot_plugins/` 下
2. 插件类必须继承 `bot.plugins.base.Plugin`
3. 必须设置 `name` 和 `commands`
4. 必须实现 `handle(text, sender_id, group_id)` 方法
5. 需要读取项目 `.env` 时，使用 `bot.project_env.ProjectEnv`
6. 如果需要处理多步会话（如登录），提供 `register_session_handlers(handlers)` 函数

### 会话处理器示例

```python
def register_session_handlers(handlers):
    handlers['your_plugin_name'] = your_session_handler

def your_session_handler(text, sender_id, group_id, session_data):
    return '收到会话输入'
```

## 文件说明

```
QL-Bot/
├── main.py                 # 启动入口
├── bot/
│   ├── config.py           # 机器人核心配置
│   ├── core.py             # WS 服务、插件加载、消息分发
│   ├── project_loader.py   # 业务项目插件扫描加载器
│   ├── project_env.py      # 项目级 .env 读取工具
│   ├── utils.py            # 日志、消息发送
│   ├── ql_api.py           # 青龙 Open API 封装
│   ├── session.py          # 用户会话管理
│   └── plugins/
│       ├── base.py         # 插件基类
│       └── example.py      # 内置示例插件
├── .env.example            # 机器人核心配置模板
├── wps-bot.service         # systemd 服务模板
├── requirements.txt
└── README.md
```

## 重启命令

```bash
cd /opt/QL-Bot
git pull
pkill -f "python3 main.py"
export $(cat .env | grep -v '^#' | xargs)
nohup python3 main.py > main.log 2>&1 &
tail -f main.log
```
