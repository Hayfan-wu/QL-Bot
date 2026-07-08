# -*- coding: utf-8 -*-
"""示例插件

新增项目时，参考本文件：
1. 在 bot/plugins/ 下新建 py 文件
2. 继承 Plugin 基类
3. 设置 name 和 commands
4. 实现 handle 方法
"""

import re
from bot.plugins.base import Plugin


class ExamplePlugin(Plugin):
    name = 'example'
    commands = [
        '示例',
        re.compile(r'^hello$', re.IGNORECASE),
    ]

    def handle(self, text, sender_id, group_id=None):
        if text.lower() == 'hello':
            return 'Hello! 欢迎使用 QQ 机器人框架。'
        if text.startswith('示例'):
            return (
                '这是一个示例插件。\n'
                '新增项目只需在 bot/plugins/ 目录下新建一个 Python 文件，\n'
                '继承 Plugin 基类并注册命令即可。'
            )
        return None
