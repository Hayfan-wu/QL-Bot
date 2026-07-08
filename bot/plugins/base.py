# -*- coding: utf-8 -*-
"""插件基类"""

import re


class Plugin:
    """所有插件的基类

    子类需要设置：
    - name: 插件名称
    - commands: 支持触发该插件的命令前缀列表（正则或字符串）

    并实现：
    - match(text): 判断消息是否匹配
    - handle(text, sender_id, group_id): 处理消息，返回字符串回复
    """

    name = 'base'
    commands = []

    def match(self, text):
        """判断消息是否命中该插件"""
        if not self.commands:
            return False
        text = text.strip()
        for cmd in self.commands:
            if isinstance(cmd, str):
                if text.lower().startswith(cmd.lower()):
                    return True
            else:
                if cmd.search(text):
                    return True
        return False

    def handle(self, text, sender_id, group_id=None):
        """处理消息，返回回复内容（字符串）或 None"""
        raise NotImplementedError
