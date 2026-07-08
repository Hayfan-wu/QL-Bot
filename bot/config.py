# -*- coding: utf-8 -*-
"""机器人配置管理"""

import os


class Config:
    """通过环境变量读取配置"""

    # 机器人自己的 QQ 号（用于识别群 @ 消息）
    QQ_BOT_QQ = os.getenv('QQ_BOT_QQ', '')

    # NapCat HTTP API（用于回复消息）
    NAPCAT_API = os.getenv('NAPCAT_API', 'http://127.0.0.1:3000')
    NAPCAT_TOKEN = os.getenv('NAPCAT_TOKEN', '')

    # 青龙面板 Open API
    QL_URL = os.getenv('QL_URL', 'http://127.0.0.1:5700')
    QL_CLIENT_ID = os.getenv('QL_CLIENT_ID', '')
    QL_CLIENT_SECRET = os.getenv('QL_CLIENT_SECRET', '')

    # 管理员 QQ，多个用逗号分隔，留空不限制
    ADMIN_QQ = os.getenv('ADMIN_QQ', '')

    # WebSocket 监听配置
    WS_HOST = os.getenv('WS_HOST', '0.0.0.0')
    WS_PORT = int(os.getenv('WS_PORT', '8080'))
    WS_PATH = os.getenv('WS_PATH', '/onebot/v11/ws/')
    WS_TOKEN = os.getenv('WS_TOKEN', '')

    # 插件目录
    PLUGIN_DIR = os.getenv('PLUGIN_DIR', 'bot/plugins')

    # 会话超时时间（秒）
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '300'))
