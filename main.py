#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QQ 机器人启动入口"""

import asyncio
from bot.core import BotCore


if __name__ == '__main__':
    bot = BotCore()
    asyncio.run(bot.run())
