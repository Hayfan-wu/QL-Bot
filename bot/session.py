# -*- coding: utf-8 -*-
"""用户会话状态管理"""

from datetime import datetime
from bot.config import Config


class SessionManager:
    """管理用户多轮交互会话"""

    def __init__(self, timeout=None):
        self.timeout = timeout or Config.SESSION_TIMEOUT
        self._sessions = {}

    def _key(self, sender_id, group_id=None):
        return f'{sender_id}_{group_id or "private"}'

    def set(self, sender_id, group_id, plugin, data=None):
        """设置会话状态

        Args:
            sender_id: 发送者 QQ
            group_id: 群号（私聊为 None）
            plugin: 插件名称
            data: 自定义数据字典
        """
        key = self._key(sender_id, group_id)
        self._sessions[key] = {
            'plugin': plugin,
            'data': data or {},
            'time': datetime.now().timestamp()
        }

    def get(self, sender_id, group_id=None):
        """获取会话状态，超时自动清理"""
        key = self._key(sender_id, group_id)
        session = self._sessions.get(key)
        if not session:
            return None
        if datetime.now().timestamp() - session.get('time', 0) > self.timeout:
            del self._sessions[key]
            return None
        return session

    def clear(self, sender_id, group_id=None):
        """清除会话状态"""
        key = self._key(sender_id, group_id)
        if key in self._sessions:
            del self._sessions[key]


# 全局会话管理器
sessions = SessionManager()
