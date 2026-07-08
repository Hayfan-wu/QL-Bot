# QL-Bot · QQ 机器人控制框架

基于 NapCatQQ 反向 WebSocket 的通用 QQ 机器人插件化框架。

本仓库只负责 QQ 群交互与控制调度，具体的业务脚本（如 WPS 自动签到）放在各自的业务仓库中。新增业务只需写一个控制插件放到 `bot/plugins/`，再配置对应的脚本路径即可。

## 设计思路

```
QL-Bot/           <- 本仓库：QQ 机器人框架 + 控制插件
├── main.py
├── bot/
│   ├── core.py
│   ├── plugins/
│   │   ├── wps.py      <- WPS 控制插件
│   │   └── example.py  <- 新插件模板
│   └── ...
└── .env          <- 只放机器人配置、业务项目路径

QL-WPS/           <- 业务仓库：具体自动化脚本
├── .env          <- WPS 自己的青龙配置
└── wps_auto.py

QL-SF/            <- 业务仓库：顺丰脚本
├── .env          <- 顺丰自己的青龙配置
└── sfsy.py

QL-JD/            <- 未来新业务仓库（示例）
└── jd_auto.py
```

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

关键配置：

```bash
# QQ 机器人
QQ_BOT_QQ=你的机器人QQ号
NAPCAT_API=http://127.0.0.1:3000
ADMIN_QQ=你的QQ号

# WPS 项目路径（指向 QL-WPS 仓库）
WPS_PROJECT_DIR=/opt/QL-WPS
WPS_SCRIPT_PATH=/opt/QL-WPS/wps_auto.py

```

WPS 使用的青龙面板配置请放到 `/opt/QL-WPS/.env`：

```bash
QL_URL=http://127.0.0.1:5700
QL_CLIENT_ID=你的WPS项目青龙ClientID
QL_CLIENT_SECRET=你的WPS项目青龙ClientSecret
```

`WPS_COOKIE` 不需要手动写入 `.env`。发送 `@机器人 WPS登录` 后粘贴 Cookie，机器人会自动把 `WPS_COOKIE` 写入 `QL-WPS/.env` 指定的青龙面板。

顺丰配置请放到 `/opt/QL-SF/.env`：

```bash
QL_URL=http://127.0.0.1:5700
QL_CLIENT_ID=你的顺丰项目青龙ClientID
QL_CLIENT_SECRET=你的顺丰项目青龙ClientSecret
SFSY_SCRIPT_PATH=/opt/QL-SF/sfsy.py
SF_QR_OUTPUT_DIR=/opt/QL-Bot
```

`sfsyUrl` 不需要手动写入 `.env`。发送 `@机器人 顺丰Cookie sessionId=...;_login_user_id_=...;_login_mobile_=...` 后，机器人会自动把 `sfsyUrl` 写入 `QL-SF/.env` 指定的青龙面板；发送 `@机器人 顺丰执行` 时，会从青龙读取 `sfsyUrl` 并注入到 `/opt/QL-SF/sfsy.py` 的执行环境。

### 3. 启动

```bash
python3 main.py
```

## WPS 控制插件命令

| 命令 | 说明 |
| --- | --- |
| `@机器人 WPS登录` | 45 秒内粘贴 Cookie，自动验证并写入青龙 `WPS_COOKIE` |
| `@机器人 WPS登录 <cookie>` | 一键登录 |
| `@机器人 WPS查询` | 查询 WPS 账号状态、签到、任务、抽奖 |
| `@机器人 WPS执行` | 立即执行 `WPS_SCRIPT_PATH` 指向的脚本 |
| `@机器人 WPS管理` | 查看当前 `WPS_COOKIE` |
| `@机器人 WPS管理 登出` | 删除 `WPS_COOKIE` |
| `@机器人 帮助` | 显示命令列表 |

## 顺丰扫码登录

顺丰插件支持微信扫码识别顺丰会员态，但当前不会自动生成积分任务 Cookie。

### 顺丰命令

| 命令 | 说明 |
| --- | --- |
| `@机器人 顺丰登录` | 生成微信 OAuth 二维码，扫码后发送 `顺丰状态` 查询结果 |
| `@机器人 顺丰状态` | 轮询扫码状态，状态包括未扫码、已扫码、取消、已登录 |
| `@机器人 顺丰Cookie <sfsyUrl>` | 手动保存积分任务 Cookie |
| `@机器人 顺丰查询` | 查看 `sfsyUrl` 和 `SF_WECHAT_LOGIN` 保存状态 |
| `@机器人 顺丰执行` | 立即执行 `SFSY_SCRIPT_PATH` 指向的脚本 |
| `@机器人 顺丰管理 登出` | 删除顺丰相关青龙变量 |

### 顺丰环境变量

| 变量 | 说明 |
| --- | --- |
| `SF_WECHAT_LOGIN` | 微信扫码后保存的顺丰会员态，包含 `OWFSESSION`、`memid`、`memNo`、`mobile` |
| `sfsyUrl` | 顺丰积分任务 Cookie，格式为 `sessionId=xxx;_login_user_id_=xxx;_login_mobile_=xxx` |
| `SFSY_SCRIPT_PATH` | 顺丰业务脚本路径，配置在 `/opt/QL-SF/.env` |
| `SF_QR_OUTPUT_DIR` | 顺丰二维码图片输出目录，配置在 `/opt/QL-SF/.env` |

### 当前限制

微信扫码登录已验证可以拿到顺丰会员态，但该会员态不能直接换成 `mcs-mimp-web` 积分任务 Cookie。若后续找到无短信换票接口，可在 `bot/sf_api.py` 中新增换票方法，再由插件自动写入 `sfsyUrl`。

## 新增控制插件（适配新业务脚本）

参考 `bot/plugins/example.py`，只需三步：

1. 在 `bot/plugins/` 下新建 `xxx.py`
2. 继承 `Plugin` 基类，实现 `name` 和 `commands`
3. 在 `.env` 中新增该业务脚本路径（可选）

```python
# bot/plugins/jd.py
from bot.plugins.base import Plugin
import re

class JdPlugin(Plugin):
    name = 'jd'
    commands = [re.compile(r'^JD\s*登录', re.IGNORECASE)]

    def handle(self, text, sender_id, group_id=None):
        return '京东插件示例'
```

## 文件说明

```
QL-Bot/
├── main.py                 # 启动入口
├── bot/
│   ├── config.py           # 配置管理
│   ├── core.py             # WS 服务、插件加载、消息分发
│   ├── utils.py            # 日志、消息发送
│   ├── ql_api.py           # 青龙 Open API 封装
│   ├── wps_api.py          # WPS 信息查询/验证
│   ├── session.py          # 用户会话管理
│   └── plugins/
│       ├── base.py         # 插件基类
│       ├── wps.py          # WPS 控制插件
│       └── example.py      # 新插件模板
├── .env.example            # 环境变量模板
├── wps-bot.service         # systemd 服务模板
├── requirements.txt
└── README.md
```

## 与业务仓库配合

以 QL-WPS 为例：

```bash
cd /opt
git clone https://github.com/Hayfan-wu/QL-WPS.git
git clone https://github.com/Hayfan-wu/QL-SF.git
git clone https://github.com/Hayfan-wu/QL-Bot.git

# QL-Bot 的 .env 中配置
WPS_PROJECT_DIR=/opt/QL-WPS
WPS_SCRIPT_PATH=/opt/QL-WPS/wps_auto.py

# QL-WPS 的 .env 中配置
QL_URL=http://127.0.0.1:5700
QL_CLIENT_ID=你的WPS项目青龙ClientID
QL_CLIENT_SECRET=你的WPS项目青龙ClientSecret

# QL-SF 的 .env 中配置
QL_URL=http://127.0.0.1:5700
QL_CLIENT_ID=你的顺丰项目青龙ClientID
QL_CLIENT_SECRET=你的顺丰项目青龙ClientSecret
SFSY_SCRIPT_PATH=/opt/QL-SF/sfsy.py
SF_QR_OUTPUT_DIR=/opt/QL-Bot

# 启动 QQ 机器人
cd /opt/QL-Bot
python3 main.py
```

以后更新业务脚本只需在对应仓库执行 `git pull`，控制框架无需改动。

## 重启命令

```bash
cd /opt/QL-Bot
git pull
pkill -f "python3 main.py"
export $(cat .env | grep -v '^#' | xargs)
nohup python3 main.py > main.log 2>&1 &
tail -f main.log
```
