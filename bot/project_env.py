# -*- coding: utf-8 -*-
"""业务项目级环境变量读取工具

QQ 机器人框架本身零侵入业务项目配置。业务项目把专属配置放在自己仓库的 .env 中，
插件通过本项目目录读取即可。
"""

import os


class ProjectEnv:
    """读取某个业务项目目录下的 .env 文件"""

    def __init__(self, project_dir):
        self.project_dir = project_dir and project_dir.strip()
        self._values = {}
        if self.project_dir:
            self._load()

    def _load(self):
        env_path = os.path.join(self.project_dir, '.env')
        if not os.path.exists(env_path):
            return
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                self._values[key] = value

    def get(self, key, default=''):
        """项目 .env 优先，其次系统环境变量"""
        if key in self._values:
            return self._values[key]
        return os.getenv(key, default)

    def get_required(self, key):
        value = self.get(key)
        if not value:
            raise ValueError(f'项目 {self.project_dir} 的 .env 缺少配置项：{key}')
        return value
