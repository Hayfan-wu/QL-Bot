# -*- coding: utf-8 -*-
"""WPS 账号管理插件（按流程图交互优化）

交互命令：
  @机器人 WPS登录              -> 粘贴 Cookie -> 自动验证 -> 写入青龙 WPS_COOKIE
  @机器人 WPS查询              -> 查询 WPS 账号状态、签到、任务、抽奖
  @机器人 WPS执行              -> 立即执行一次 wps_auto.py
  @机器人 WPS管理 登出         -> 删除青龙 WPS_COOKIE
  @机器人 WPS列表              -> 查看当前保存的账号信息
  @机器人 帮助 / 菜单           -> 显示命令列表

会话规则：
  - 登录流程 45 秒无响应自动取消
  - 账号名自动从 WPS 账户获取
  - Cookie 保存到单一环境变量 WPS_COOKIE（多账号用 & 分隔）
"""

import os
import re
import subprocess
import sys
from datetime import datetime

from bot.plugins.base import Plugin
from bot.ql_api import ql
from bot.session import sessions
from bot.utils import Log
from bot.wps_api import WpsAPI


WPS_COOKIE_NAME = 'WPS_COOKIE'
# 登录会话超时 45 秒
LOGIN_TIMEOUT = 45


def _now_ts():
    return datetime.now().timestamp()


def _get_wps_cookie():
    """从青龙获取 WPS_COOKIE"""
    envs = ql.list_envs(WPS_COOKIE_NAME)
    for env in envs:
        if env.get('name') == WPS_COOKIE_NAME:
            return env
    return None


def _save_wps_cookie(cookie, nickname='', uid=0):
    """保存或更新 WPS_COOKIE"""
    remark = f'{nickname}({uid})' if nickname and uid else 'WPS Cookie'
    existing = _get_wps_cookie()
    if existing:
        return ql.update_env(existing['id'], WPS_COOKIE_NAME, cookie, remarks=remark)
    return ql.create_env(WPS_COOKIE_NAME, cookie, remarks=remark)


def _delete_wps_cookie():
    """删除 WPS_COOKIE"""
    existing = _get_wps_cookie()
    if existing:
        ql.delete_env(existing['id'])
        return True
    return False


def _run_wps_auto():
    """执行 wps_auto.py，返回输出"""
    script_path = os.getenv('WPS_AUTO_PATH', 'wps_auto.py')
    script_path = os.path.expanduser(script_path)
    base_dir = os.path.dirname(script_path) if os.path.dirname(script_path) else os.getcwd()
    script_name = os.path.basename(script_path)
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=base_dir,
        )
        output = result.stdout + result.stderr
        if len(output) > 1500:
            output = output[:1500] + '\n... 输出过长，已截断'
        return f'[返回码 {result.returncode}]\n{output}'
    except subprocess.TimeoutExpired:
        return '⏰ 执行超时（超过 5 分钟）'
    except Exception as e:
        return f'❌ 执行失败：{e}'


def _format_env_preview():
    """格式化当前 WPS_COOKIE 环境变量信息"""
    env = _get_wps_cookie()
    if not env:
        return '暂无 WPS_COOKIE 环境变量'
    value = env.get('value', '')
    remark = env.get('remarks', '')
    preview = value[:40] + '...' if len(value) > 40 else value
    return f'变量：{env.get("name")}\n备注：{remark}\n预览：{preview}'


class WpsPlugin(Plugin):
    name = 'wps'
    commands = [
        re.compile(r'^WPS\s*登录', re.IGNORECASE),
        re.compile(r'^账号[:：]?\s*WPS\s*登录', re.IGNORECASE),
        re.compile(r'^WPS\s*查询', re.IGNORECASE),
        re.compile(r'^账号[:：]?\s*WPS\s*查询', re.IGNORECASE),
        re.compile(r'^WPS\s*执行', re.IGNORECASE),
        re.compile(r'^账号[:：]?\s*WPS\s*执行', re.IGNORECASE),
        re.compile(r'^WPS\s*管理', re.IGNORECASE),
        re.compile(r'^账号[:：]?\s*WPS\s*管理', re.IGNORECASE),
        re.compile(r'^WPS\s*列表', re.IGNORECASE),
        re.compile(r'^账号[:：]?\s*WPS\s*列表', re.IGNORECASE),
        re.compile(r'^帮助$|^菜单$|^help$', re.IGNORECASE),
    ]

    def handle(self, text, sender_id, group_id=None):
        text = text.strip()

        # 帮助
        if re.match(r'^帮助$|^菜单$|^help$', text, re.IGNORECASE):
            return self.help_text()

        # 查询
        if self._is_query(text):
            return self._handle_query()

        # 执行
        if self._is_exec(text):
            return self._handle_exec()

        # 管理
        if self._is_manage(text):
            return self._handle_manage(text)

        # 列表
        if self._is_list(text):
            return self._format_list()

        # 登录
        if self._is_login(text):
            return self._handle_login(text, sender_id, group_id)

        return '未知命令，发送「帮助」查看命令列表'

    # ---------- 命令判断 ----------

    def _is_login(self, text):
        return bool(re.search(r'^WPS\s*登录', text, re.IGNORECASE))

    def _is_query(self, text):
        return bool(re.search(r'^WPS\s*查询', text, re.IGNORECASE))

    def _is_exec(self, text):
        return bool(re.search(r'^WPS\s*执行', text, re.IGNORECASE))

    def _is_manage(self, text):
        return bool(re.search(r'^WPS\s*管理', text, re.IGNORECASE))

    def _is_list(self, text):
        return bool(re.search(r'^WPS\s*列表', text, re.IGNORECASE))

    # ---------- 登录流程 ----------

    def _handle_login(self, text, sender_id, group_id):
        # 去掉命令前缀
        cookie = re.sub(r'^WPS\s*登录\s*', '', text, flags=re.IGNORECASE).strip()

        # 一键登录：命令后 directly 跟了 cookie
        if cookie:
            return self._process_cookie(cookie, sender_id, group_id)

        # 进入交互式登录，等待用户输入 Cookie
        sessions.set(sender_id, group_id, 'wps', {'step': 'waiting_cookie', 'time': _now_ts()})
        return (
            '🍪 请输入你的 WPS Cookie（支持多账号，多个 Cookie 用 & 分隔）：\n'
            '提示：45 秒内未输入将自动取消。'
        )

    def _process_cookie(self, cookie, sender_id, group_id):
        """验证并保存 Cookie"""
        if not cookie or cookie.startswith('WPS'):
            return '⚠️ 请输入有效的 Cookie'

        # 验证 WPS 登录
        ok, nickname, uid = WpsAPI(cookie).check_login()
        if not ok:
            sessions.clear(sender_id, group_id)
            return f'❌ WPS 登录验证失败：{nickname}\n请检查 Cookie 是否完整。'

        # 提交到青龙
        try:
            _save_wps_cookie(cookie, nickname, uid)
            sessions.clear(sender_id, group_id)
            return (
                f'🎉 登录成功！\n'
                f'👤 账号：{nickname}\n'
                f'🆔 uid：{uid}\n'
                f'📦 已保存到青龙环境变量：{WPS_COOKIE_NAME}\n'
                f'⏰ 时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n'
                f'可发送「WPS查询」查看状态，「WPS执行」立即签到。'
            )
        except Exception as e:
            sessions.clear(sender_id, group_id)
            return f'❌ 提交到青龙失败：{e}'

    # ---------- 查询 ----------

    def _handle_query(self):
        env = _get_wps_cookie()
        if not env:
            return '⚠️ 未找到 WPS_COOKIE，请先发送「WPS登录」提交 Cookie。'
        cookie = env.get('value', '')
        if not cookie:
            return '⚠️ WPS_COOKIE 为空，请重新登录。'
        return WpsAPI(cookie).format_report()

    # ---------- 执行 ----------

    def _handle_exec(self):
        env = _get_wps_cookie()
        if not env:
            return '⚠️ 未找到 WPS_COOKIE，请先发送「WPS登录」提交 Cookie。'
        return '🚀 正在执行 WPS 签到任务...\n' + _run_wps_auto()

    # ---------- 管理 ----------

    def _handle_manage(self, text):
        args = re.sub(r'^WPS\s*管理\s*', '', text, flags=re.IGNORECASE).strip()
        if not args:
            return '📦 当前 WPS_COOKIE 信息：\n' + _format_env_preview()

        if args.startswith('登出') or args.startswith('删除'):
            if _delete_wps_cookie():
                return '✅ 已删除 WPS_COOKIE 环境变量。'
            return '⚠️ 未找到 WPS_COOKIE，无需删除。'

        return '格式错误，正确格式：\nWPS管理 登出\nWPS管理 删除'

    # ---------- 列表 ----------

    def _format_list(self):
        return '📦 当前 WPS_COOKIE 信息：\n' + _format_env_preview()

    # ---------- 帮助 ----------

    def help_text(self):
        return (
            '📋 WPS 机器人命令列表\n'
            '─────────────────\n'
            '1️⃣ 登录账号：\n'
            '   @机器人 WPS登录\n'
            '   然后粘贴 Cookie（多账号用 & 分隔）\n\n'
            '2️⃣ 查询状态：\n'
            '   @机器人 WPS查询\n\n'
            '3️⃣ 立即执行签到：\n'
            '   @机器人 WPS执行\n\n'
            '4️⃣ 查看/删除 Cookie：\n'
            '   @机器人 WPS管理\n'
            '   @机器人 WPS管理 登出\n\n'
            '5️⃣ 显示本菜单：\n'
            '   @机器人 帮助'
        )


# 为 bot/core.py 的会话分发提供处理入口
# 当用户处于 waiting_cookie 状态时，bot/core.py 会把消息交给本插件处理，
# 但 handle 方法默认会按命令匹配。下面这个函数用于直接处理会话中的 Cookie 输入。

def handle_session(text, sender_id, group_id, session_data):
    """处理登录会话中的用户输入"""
    step = session_data.get('data', {}).get('step')
    start_time = session_data.get('data', {}).get('time', 0)

    if step != 'waiting_cookie':
        return None

    # 45 秒超时检查
    if _now_ts() - start_time > LOGIN_TIMEOUT:
        sessions.clear(sender_id, group_id)
        return '⏰ 登录会话已超时（45 秒无响应），请重新发送「WPS登录」。'

    plugin = WpsPlugin()
    return plugin._process_cookie(text.strip(), sender_id, group_id)
