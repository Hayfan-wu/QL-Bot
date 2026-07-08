# -*- coding: utf-8 -*-
"""青龙面板 Open API 封装"""

import requests

from bot.config import Config
from bot.utils import Log


class QingLongAPI:
    """青龙环境变量管理"""

    def __init__(self):
        self.base_url = Config.QL_URL.rstrip('/')
        self.client_id = Config.QL_CLIENT_ID
        self.client_secret = Config.QL_CLIENT_SECRET
        self.token = None

    def _get_token(self):
        url = f'{self.base_url}/open/auth/token'
        params = {'client_id': self.client_id, 'client_secret': self.client_secret}
        try:
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            if data.get('code') == 200:
                self.token = data['data']['token']
                return self.token
            raise Exception(f'青龙登录失败: {data}')
        except Exception as e:
            Log.fail(f'青龙登录异常: {e}')
            raise

    def _headers(self):
        if not self.token:
            self._get_token()
        return {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}

    def list_envs(self, search_value=''):
        url = f'{self.base_url}/open/envs'
        params = {'searchValue': search_value} if search_value else {}
        r = requests.get(url, headers=self._headers(), params=params, timeout=10)
        data = r.json()
        if data.get('code') == 200:
            return data.get('data', [])
        raise Exception(f'获取环境变量失败: {data}')

    def create_env(self, name, value, remarks=''):
        url = f'{self.base_url}/open/envs'
        # 新版青龙（v2.15+）要求 body 为数组，旧版为对象，优先尝试数组
        payloads = [
            [{'name': name, 'value': value, 'remarks': remarks}],
            {'name': name, 'value': value, 'remarks': remarks},
        ]
        last_error = None
        for payload in payloads:
            r = requests.post(url, headers=self._headers(), json=payload, timeout=10)
            data = r.json()
            if data.get('code') == 200:
                return data.get('data')
            last_error = data
        raise Exception(f'创建环境变量失败: {last_error}')

    def update_env(self, env_id, name, value, remarks=''):
        url = f'{self.base_url}/open/envs'
        # 新版青龙（v2.15+）要求 body 为数组，旧版为对象，优先尝试数组
        payloads = [
            [{'id': env_id, 'name': name, 'value': value, 'remarks': remarks}],
            {'id': env_id, 'name': name, 'value': value, 'remarks': remarks},
        ]
        last_error = None
        for payload in payloads:
            r = requests.put(url, headers=self._headers(), json=payload, timeout=10)
            data = r.json()
            if data.get('code') == 200:
                return data.get('data')
            last_error = data
        raise Exception(f'更新环境变量失败: {last_error}')

    def delete_env(self, env_id):
        url = f'{self.base_url}/open/envs'
        r = requests.delete(url, headers=self._headers(), json=[env_id], timeout=10)
        data = r.json()
        if data.get('code') == 200:
            return True
        raise Exception(f'删除环境变量失败: {data}')


# 全局实例
ql = QingLongAPI()
