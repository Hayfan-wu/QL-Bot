# -*- coding: utf-8 -*-
"""工具函数"""

import re
import requests
from datetime import datetime

from bot.config import Config


class Log:
    """简单的日志工具"""

    @staticmethod
    def _ts():
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def info(msg):
        print(f'[{Log._ts()}] [INFO] {msg}', flush=True)

    @staticmethod
    def ok(msg):
        print(f'[{Log._ts()}] [OK] {msg}', flush=True)

    @staticmethod
    def warn(msg):
        print(f'[{Log._ts()}] [WARN] {msg}', flush=True)

    @staticmethod
    def fail(msg):
        print(f'[{Log._ts()}] [FAIL] {msg}', flush=True)


def normalize_text(text, bot_qq=''):
    """清理消息文本：移除 @机器人 和 CQ 码"""
    if not text:
        return ''
    # 移除 CQ:at 码
    text = re.sub(r'\[CQ:at,qq=\d+\]', ' ', text)
    # 移除 @机器人QQ
    if bot_qq:
        text = re.sub(rf'@{bot_qq}\s*', ' ', text)
        text = re.sub(rf'@{bot_qq}', ' ', text)
    # 替换全角空格、换行等统一为空格
    text = text.replace('\u3000', ' ').replace('\n', ' ').replace('\r', ' ')
    # 合并多个空格
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def send_qq_message(message, user_id=None, group_id=None):
    """通过 NapCat HTTP API 发送 QQ 消息"""
    if not Config.NAPCAT_API:
        Log.fail('未配置 NAPCAT_API，无法回复消息')
        return False

    headers = {'Content-Type': 'application/json'}
    if Config.NAPCAT_TOKEN:
        headers['Authorization'] = f'Bearer {Config.NAPCAT_TOKEN}'

    if group_id:
        url = f'{Config.NAPCAT_API}/send_group_msg'
        payload = {'group_id': int(group_id), 'message': message}
    elif user_id:
        url = f'{Config.NAPCAT_API}/send_private_msg'
        payload = {'user_id': int(user_id), 'message': message}
    else:
        Log.fail('未指定 user_id 或 group_id')
        return False

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        result = r.json()
        Log.info(f'发送消息结果: {result}')
        return True
    except Exception as e:
        Log.fail(f'发送消息失败: {e}')
        return False
