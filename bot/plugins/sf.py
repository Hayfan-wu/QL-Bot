# -*- coding: utf-8 -*-
"""顺丰账号插件。

扫码登录只保存顺丰会员态；积分任务 Cookie 仍使用 sfsyUrl 手动提交。
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from bot.plugins.base import Plugin
from bot.ql_api import QingLongAPI, ql
from bot.session import sessions
from bot.sf_api import SFLoginStatus, SFWechatLoginAPI


SF_COOKIE_ENV = "sfsyUrl"
SF_WECHAT_ENV = "SF_WECHAT_LOGIN"
SF_LOGIN_TIMEOUT = 180
SF_SCRIPT_ENV_NAMES = [
    SF_COOKIE_ENV,
    "SFBF",
    "SF_PROXY_API_URL",
    "SF_KEEPALIVE",
    "WXPUSHER_APP_TOKEN",
    "WXPUSHER_UIDS",
    "WXPUSHER_TOPIC_IDS",
    "WXPUSHER_ONLY_EXPIRED",
]


def _now_ts():
    return datetime.now().timestamp()


def _parse_env_file(env_path):
    """读取简单 KEY=VALUE 格式的 .env 文件"""
    values = {}
    if not env_path or not os.path.exists(env_path):
        return values

    with open(env_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get_sf_script_path():
    """获取顺丰脚本路径"""
    project_dir = os.getenv("SF_PROJECT_DIR", "").strip()
    if os.getenv("SFSY_SCRIPT_PATH"):
        return os.getenv("SFSY_SCRIPT_PATH")
    if project_dir:
        return os.path.join(project_dir, "sfsy.py")
    return "sfsy.py"


def _get_sf_project_dir():
    """获取 QL-SF 项目目录"""
    project_dir = os.getenv("SF_PROJECT_DIR", "").strip()
    if project_dir:
        return project_dir

    script_path = _get_sf_script_path()
    script_dir = os.path.dirname(os.path.expanduser(script_path))
    return script_dir or ""


def _get_sf_ql():
    """从 QL-SF 项目 .env 创建青龙客户端；缺省时兼容旧全局配置"""
    project_dir = _get_sf_project_dir()
    env_path = os.path.join(project_dir, ".env") if project_dir else ""
    env_values = _parse_env_file(env_path)

    ql_url = env_values.get("QL_URL")
    client_id = env_values.get("QL_CLIENT_ID")
    client_secret = env_values.get("QL_CLIENT_SECRET")

    if ql_url and client_id and client_secret:
        return QingLongAPI(
            base_url=ql_url,
            client_id=client_id,
            client_secret=client_secret,
        )

    return ql


def _get_env(name):
    sf_ql = _get_sf_ql()
    envs = sf_ql.list_envs(name)
    for env in envs:
        if env.get("name") == name:
            return env
    return None


def _env_id(env):
    return env.get("id") or env.get("_id")


def _save_env(name, value, remarks=""):
    existing = _get_env(name)
    sf_ql = _get_sf_ql()
    if existing:
        return sf_ql.update_env(_env_id(existing), name, value, remarks=remarks)
    return sf_ql.create_env(name, value, remarks=remarks)


def _delete_env(name):
    existing = _get_env(name)
    if existing:
        _get_sf_ql().delete_env(_env_id(existing))
        return True
    return False


def _format_wechat_value(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _parse_sfsy_cookie(cookie):
    parsed = {}
    for part in cookie.split(";"):
        if "=" not in part:
            continue
        key, value = part.strip().split("=", 1)
        parsed[key] = value
    required = {"sessionId", "_login_user_id_", "_login_mobile_"}
    if not required.issubset(parsed):
        return {}
    return parsed


def _mask_cookie(cookie):
    masked_parts = []
    for part in cookie.split(";"):
        if "=" not in part:
            masked_parts.append(part)
            continue
        key, value = part.strip().split("=", 1)
        masked_parts.append(f"{key}={value[:4]}..." if value else f"{key}=")
    return ";".join(masked_parts)


def _mask_mobile(mobile):
    if len(mobile) >= 7:
        return f"{mobile[:3]}****{mobile[-4:]}"
    return mobile


def _format_image_cq(path):
    uri = Path(path).resolve().as_uri()
    return f"[CQ:image,file={uri}]"


def _build_sfsy_env():
    """构造顺丰脚本执行环境，把青龙变量注入本地进程"""
    env = os.environ.copy()

    for name in SF_SCRIPT_ENV_NAMES:
        item = _get_env(name)
        if item and item.get("value"):
            env[name] = item.get("value")

    return env


def _run_sfsy():
    script_path = _get_sf_script_path()
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
            env=_build_sfsy_env(),
        )
        output = result.stdout + result.stderr
        if len(output) > 1500:
            output = output[:1500] + "\n... 输出过长，已截断"
        return f"[返回码 {result.returncode}]\n{output}"
    except subprocess.TimeoutExpired:
        return "⏰ 执行超时（超过 5 分钟）"
    except Exception as exc:
        return f"❌ 执行失败：{exc}"


class SfPlugin(Plugin):
    name = "sf"
    commands = [
        re.compile(r"^顺丰\s*登录", re.IGNORECASE),
        re.compile(r"^顺丰\s*状态", re.IGNORECASE),
        re.compile(r"^顺丰\s*Cookie", re.IGNORECASE),
        re.compile(r"^顺丰\s*查询", re.IGNORECASE),
        re.compile(r"^顺丰\s*执行", re.IGNORECASE),
        re.compile(r"^顺丰\s*管理", re.IGNORECASE),
    ]

    def __init__(self):
        self.api_by_key = {}

    def handle(self, text, sender_id, group_id=None):
        text = text.strip()
        if re.match(r"^顺丰\s*登录", text, re.IGNORECASE):
            return self._handle_login(sender_id, group_id)
        if re.match(r"^顺丰\s*状态", text, re.IGNORECASE):
            return self._handle_status(sender_id, group_id)
        if re.match(r"^顺丰\s*Cookie", text, re.IGNORECASE):
            cookie = re.sub(r"^顺丰\s*Cookie\s*", "", text, flags=re.IGNORECASE).strip()
            return self._handle_cookie(cookie)
        if re.match(r"^顺丰\s*查询", text, re.IGNORECASE):
            return self._handle_query()
        if re.match(r"^顺丰\s*执行", text, re.IGNORECASE):
            return _run_sfsy()
        if re.match(r"^顺丰\s*管理", text, re.IGNORECASE):
            return self._handle_manage(text)
        return "未知命令，发送「顺丰登录」开始扫码。"

    def _session_key(self, sender_id, group_id):
        return f"{group_id or 'private'}:{sender_id}"

    def _handle_login(self, sender_id, group_id):
        api = SFWechatLoginAPI()
        qr_session = api.create_qrcode_session()
        key = self._session_key(sender_id, group_id)
        self.api_by_key[key] = api

        output_dir = Path(os.getenv("SF_QR_OUTPUT_DIR", ".")).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        qr_path = output_dir / f"sf_login_{sender_id}.png"
        qr_path.write_bytes(qr_session.qr_png)

        sessions.set(sender_id, group_id, "sf", {
            "step": "waiting_scan",
            "qr_path": str(qr_path),
            "owf_session": qr_session.owf_session,
        })
        return (
            "📷 顺丰微信扫码二维码已生成。\n"
            f"{_format_image_cq(qr_path)}\n"
            f"二维码文件：{qr_path}\n"
            "请用微信扫一扫完成授权，然后发送「顺丰状态」。\n"
            "说明：扫码成功后只保存顺丰会员态，不会自动生成积分任务 Cookie。"
        )

    def _handle_status(self, sender_id, group_id):
        session = sessions.get(sender_id, group_id)
        if not session or session.get("plugin") != "sf":
            return "⚠️ 当前没有顺丰扫码会话，请先发送「顺丰登录」。"
        if _now_ts() - session.get("time", 0) > SF_LOGIN_TIMEOUT:
            sessions.clear(sender_id, group_id)
            return "⏰ 顺丰扫码会话已超时，请重新发送「顺丰登录」。"

        key = self._session_key(sender_id, group_id)
        api = self.api_by_key.get(key)
        if not api:
            sessions.clear(sender_id, group_id)
            return "⚠️ 扫码会话已丢失，请重新发送「顺丰登录」。"

        result = api.poll_login()
        if result.status == SFLoginStatus.NOT_SCAN:
            return "⌛ 等待扫码中。请用微信扫一扫二维码。"
        if result.status == SFLoginStatus.HAS_SCAN:
            return "📱 已扫码，等待微信内确认。"
        if result.status == SFLoginStatus.CANCEL_SCAN:
            sessions.clear(sender_id, group_id)
            return "❌ 已取消扫码登录。"
        if result.status == SFLoginStatus.LOGINED:
            value = _format_wechat_value({
                "owf_session": result.owf_session,
                "token": result.token,
                "memid": result.memid,
                "mem_no": result.mem_no,
                "mobile": result.mobile,
                "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            _save_env(SF_WECHAT_ENV, value, remarks=f"顺丰会员扫码 {result.masked_mobile}")
            sessions.clear(sender_id, group_id)
            return (
                "✅ 顺丰会员扫码完成。\n"
                f"账号：{result.masked_mobile}\n"
                f"已保存到青龙变量：{SF_WECHAT_ENV}\n"
                "注意：已完成顺丰会员扫码，但未获取积分任务 Cookie。\n"
                "如需签到，请继续发送「顺丰Cookie sessionId=...;_login_user_id_=...;_login_mobile_=...」。"
            )
        sessions.clear(sender_id, group_id)
        return f"❌ 扫码失败：{result.message or '未知状态'}"

    def _handle_cookie(self, cookie):
        parsed = _parse_sfsy_cookie(cookie)
        if not parsed:
            return (
                "⚠️ sfsyUrl 格式不完整。\n"
                "正确格式：sessionId=xxx;_login_user_id_=xxx;_login_mobile_=xxx"
            )
        remark = f"顺丰积分 Cookie {_mask_mobile(parsed['_login_mobile_'])}"
        _save_env(SF_COOKIE_ENV, cookie, remarks=remark)
        return f"✅ 已保存积分任务 Cookie 到青龙变量：{SF_COOKIE_ENV}\n预览：{_mask_cookie(cookie)}"

    def _handle_query(self):
        cookie_env = _get_env(SF_COOKIE_ENV)
        wechat_env = _get_env(SF_WECHAT_ENV)
        lines = ["📦 顺丰账号状态"]
        lines.append(f"积分 Cookie：{'已保存' if cookie_env else '未保存'}")
        lines.append(f"微信会员态：{'已保存' if wechat_env else '未保存'}")
        if cookie_env:
            lines.append(f"Cookie 预览：{_mask_cookie(cookie_env.get('value', ''))}")
        return "\n".join(lines)

    def _handle_manage(self, text):
        if "登出" not in text:
            return "可用命令：顺丰管理 登出"
        deleted_cookie = _delete_env(SF_COOKIE_ENV)
        deleted_wechat = _delete_env(SF_WECHAT_ENV)
        if deleted_cookie or deleted_wechat:
            return "✅ 已删除顺丰相关青龙变量。"
        return "ℹ️ 没有找到顺丰相关青龙变量。"
