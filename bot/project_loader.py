# -*- coding: utf-8 -*-
"""业务项目插件加载器

实现零侵入：业务项目只需在仓库根目录下创建 `bot_plugins/` 目录，
在里面放插件 Python 文件，QL-Bot 启动时会自动扫描 /opt 下的业务项目并加载。

QL-Bot 的 .env 中不需要配置任何项目路径。
"""

import os
import sys
import importlib
import importlib.util
import inspect

from bot.plugins.base import Plugin
from bot.utils import Log


# 默认扫描目录，多个用逗号分隔，可从环境变量覆盖
PROJECT_SCAN_DIRS = [d.strip() for d in os.getenv('PROJECT_SCAN_DIRS', '/opt').split(',') if d.strip()]
# 业务项目内放置插件的子目录名
PROJECT_PLUGIN_DIR = 'bot_plugins'


def _find_project_plugins():
    """扫描项目目录，查找 bot_plugins/ 下的插件"""
    plugin_files = []  # (project_dir, filename, full_path)
    seen_paths = set()

    for scan_dir in PROJECT_SCAN_DIRS:
        if not os.path.isdir(scan_dir):
            continue
        try:
            entries = os.listdir(scan_dir)
        except Exception as e:
            Log.warn(f'无法读取目录 {scan_dir}: {e}')
            continue

        for entry in entries:
            project_dir = os.path.join(scan_dir, entry)
            plugin_dir = os.path.join(project_dir, PROJECT_PLUGIN_DIR)
            if not os.path.isdir(plugin_dir):
                continue

            for filename in sorted(os.listdir(plugin_dir)):
                if filename.startswith('_') or not filename.endswith('.py'):
                    continue
                full_path = os.path.join(plugin_dir, filename)
                if full_path in seen_paths:
                    continue
                seen_paths.add(full_path)
                plugin_files.append((project_dir, filename, full_path))

    return plugin_files


def load_project_plugins(plugins_list, session_handlers=None):
    """动态加载业务项目插件到 plugins_list，并注册会话处理器"""
    if session_handlers is None:
        session_handlers = {}

    plugin_files = _find_project_plugins()
    if not plugin_files:
        Log.info('未发现业务项目插件')
        return

    for project_dir, filename, full_path in plugin_files:
        # 把项目根目录加入 sys.path，方便插件 import 项目自身模块
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)

        plugin_dir_path = os.path.dirname(full_path)
        if plugin_dir_path not in sys.path:
            sys.path.insert(0, plugin_dir_path)

        module_name = f'project_plugin_{os.path.basename(project_dir)}_{filename[:-3]}'
        try:
            spec = importlib.util.spec_from_file_location(module_name, full_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Plugin) and obj is not Plugin:
                    if obj in [p.__class__ for p in plugins_list]:
                        continue
                    plugin = obj()
                    # 把项目目录注入插件实例
                    plugin.project_dir = project_dir
                    plugins_list.append(plugin)
                    Log.ok(f'已加载业务项目插件: {plugin.name} (来自 {project_dir})')

            # 如果模块提供了 register_session_handlers 函数，注册会话处理器
            if hasattr(module, 'register_session_handlers'):
                try:
                    module.register_session_handlers(session_handlers)
                except Exception as e:
                    Log.fail(f'注册会话处理器失败 {full_path}: {e}')

        except Exception as e:
            Log.fail(f'加载业务项目插件 {full_path} 失败: {e}')
