# -*- coding: utf-8 -*-
"""机器人核心：插件加载、消息接收、指令分发"""

import os
import sys
import json
import asyncio
import importlib
import inspect
import websockets

from bot.plugins.base import Plugin
from bot.config import Config
from bot.session import sessions
from bot.utils import Log, normalize_text, send_qq_message
from bot.project_loader import load_project_plugins


class BotCore:
    def __init__(self):
        self.plugins = []
        self.session_handlers = {}

    def load_plugins(self):
        """自动加载 bot/plugins/ 目录下所有插件"""
        plugin_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), Config.PLUGIN_DIR)
        if not os.path.isdir(plugin_dir):
            Log.warn(f'插件目录不存在: {plugin_dir}')
            return

        Log.info(f'正在加载框架插件，目录: {plugin_dir}')
        sys.path.insert(0, os.path.dirname(plugin_dir))

        for filename in sorted(os.listdir(plugin_dir)):
            if filename.startswith('_') or not filename.endswith('.py'):
                continue
            module_name = f'bot.plugins.{filename[:-3]}'
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, Plugin) and obj is not Plugin and obj not in [p.__class__ for p in self.plugins]:
                        plugin = obj()
                        self.plugins.append(plugin)
                        Log.ok(f'已加载框架插件: {plugin.name}')
            except Exception as e:
                Log.fail(f'加载框架插件 {filename} 失败: {e}')

        # 加载业务项目插件（/opt 下各项目 bot_plugins/ 目录）
        load_project_plugins(self.plugins, self.session_handlers)

        Log.info(f'共加载 {len(self.plugins)} 个插件')

    def dispatch(self, text, sender_id, group_id=None):
        """分发消息到匹配的插件"""
        # 检查是否有等待中的会话
        session = sessions.get(sender_id, group_id)
        if session:
            plugin_name = session.get('plugin')

            # 优先调用插件注册的会话处理器
            handler = self.session_handlers.get(plugin_name)
            if handler:
                try:
                    reply = handler(text, sender_id, group_id, session)
                    if reply:
                        send_qq_message(reply, user_id=sender_id, group_id=group_id)
                    return
                except Exception as e:
                    Log.fail(f'会话处理失败: {e}')
                    send_qq_message(f'处理失败: {str(e)}', user_id=sender_id, group_id=group_id)
                    return

            for plugin in self.plugins:
                if plugin.name == plugin_name:
                    try:
                        reply = plugin.handle(text, sender_id, group_id)
                        if reply:
                            send_qq_message(reply, user_id=sender_id, group_id=group_id)
                    except Exception as e:
                        Log.fail(f'插件 {plugin.name} 处理失败: {e}')
                        send_qq_message(f'处理失败: {str(e)}', user_id=sender_id, group_id=group_id)
                    return

        # 没有会话时，按命令匹配插件
        for plugin in self.plugins:
            try:
                if plugin.match(text):
                    reply = plugin.handle(text, sender_id, group_id)
                    if reply:
                        send_qq_message(reply, user_id=sender_id, group_id=group_id)
                    return
            except Exception as e:
                Log.fail(f'插件 {plugin.name} 匹配失败: {e}')

        # 没有任何插件命中
        Log.info('没有插件命中该消息')

    def _check_permission(self, sender_id):
        if not Config.ADMIN_QQ:
            return True
        return str(sender_id) in Config.ADMIN_QQ.split(',')

    async def handle_ws(self, websocket):
        # websockets 14+ 不再传入 path 参数，通过 request.path 获取
        try:
            req_path = websocket.request.path
        except Exception:
            req_path = '/'
        if Config.WS_PATH and req_path != Config.WS_PATH:
            Log.warn(f'NapCat 连接路径不匹配: {req_path}，期望: {Config.WS_PATH}')
            return
        Log.ok(f'NapCat 已连接: {websocket.remote_address}, path={req_path}')
        try:
            async for message in websocket:
                Log.info(f'收到原始消息: {message}')
                try:
                    data = json.loads(message)
                    post_type = data.get('post_type')
                    if post_type != 'message':
                        continue

                    raw_msg = data.get('raw_message', '')
                    sender = data.get('sender', {})
                    sender_id = sender.get('user_id')
                    group_id = data.get('group_id')
                    message_type = data.get('message_type', '')

                    # 权限检查
                    if not self._check_permission(sender_id):
                        send_qq_message('你没有权限使用此机器人', user_id=sender_id, group_id=group_id)
                        continue

                    # 群消息必须 @ 机器人才响应
                    if message_type == 'group':
                        if not Config.QQ_BOT_QQ:
                            Log.warn('未配置 QQ_BOT_QQ，无法识别群 @ 消息')
                            continue
                        bot_qq_str = str(Config.QQ_BOT_QQ)
                        if bot_qq_str not in raw_msg and f'[CQ:at,qq={bot_qq_str}]' not in raw_msg:
                            Log.info('群消息未 @ 机器人，忽略')
                            continue

                    # 清理消息文本
                    text = normalize_text(raw_msg, bot_qq_str if message_type == 'group' else '')
                    Log.info(f'处理命令: sender={sender_id}, group={group_id}, text={text}')

                    if not text:
                        continue

                    self.dispatch(text, sender_id, group_id)

                except Exception as e:
                    Log.fail(f'处理消息异常: {e}')
        except websockets.exceptions.ConnectionClosed as e:
            Log.info(f'NapCat 断开连接: {e}')

    async def run(self):
        self.load_plugins()
        Log.ok(f'启动 QQ 机器人，监听 ws://{Config.WS_HOST}:{Config.WS_PORT}{Config.WS_PATH}')
        async with websockets.serve(self.handle_ws, Config.WS_HOST, Config.WS_PORT):
            await asyncio.Future()
