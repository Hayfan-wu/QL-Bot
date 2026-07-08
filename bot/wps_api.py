# -*- coding: utf-8 -*-
"""WPS 账号信息查询与验证工具（供 QQ Bot 插件使用）

只读查询，不执行签到/任务/抽奖等写操作。
"""

import re
import json
import requests
from datetime import datetime


# 与 wps_auto.py 保持一致
ACTIVITY_NUMBER = "HD2025031821201822"
PAGE_NUMBER = "YM2025040908558269"
FILTER_PARAMS = {"position": "ad_rwzx_invite_test", "token": "61b3f3ab86984a191927bfe7748b85a5"}


class WpsAPI:
    """WPS 账号信息查询"""

    SIGN_BASE = "https://personal-bus.wps.cn/sign_in/v1"
    ACT_BASE = "https://personal-act.wps.cn/activity-rubik"

    def __init__(self, cookie):
        self.cookie = cookie
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
            "Referer": f"https://personal-act.wps.cn/rubik2/portal/{ACTIVITY_NUMBER}/{PAGE_NUMBER}",
            "Origin": "https://personal-act.wps.cn",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        })
        for item in cookie.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                self.s.cookies.set(k, v, domain=".wps.cn")
        self.user_id = self._extract_uid(cookie)
        self.csrf = self.s.cookies.get("csrf", "")
        self.nickname = ""

    @staticmethod
    def _extract_uid(cookie):
        m = re.search(r'uid=(\d+)', cookie)
        return int(m.group(1)) if m else 0

    def check_login(self):
        """校验登录并返回 (ok, nickname, uid)"""
        try:
            r = self.s.post("https://account.wps.cn/p/auth/check",
                            headers={"X-CSRFToken": self.csrf}, json={}, timeout=15)
            d = r.json()
            if d.get("result") == "ok":
                self.nickname = d.get("nickname", "") or "未设置"
                return True, self.nickname, d.get("userid", self.user_id)
            return False, d.get("msg", "登录失效"), 0
        except Exception as e:
            return False, f"请求异常：{e}", 0

    def get_sign_stat(self):
        try:
            r = self.s.get(f"{self.SIGN_BASE}/user_stat", params={"channel": ""}, timeout=20)
            d = r.json().get("data", {}) or {}
            return {
                "has_signed": d.get("has_signed", False),
                "month_continuous_days": d.get("month_continuous_days", 0),
                "total_cumulative_days": d.get("total_cumulative_days", 0),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_page_info(self):
        try:
            r = self.s.get(f"{self.ACT_BASE}/activity/page_info",
                           params={"activity_number": ACTIVITY_NUMBER, "page_number": PAGE_NUMBER,
                                   "filter_params": json.dumps(FILTER_PARAMS)}, timeout=20)
            return r.json().get("data", []) or []
        except Exception:
            return []

    def get_tasks(self):
        data = self.get_page_info()
        for c in data:
            tc = c.get("task_center") or {}
            if tc.get("task_list"):
                return tc["task_list"]
        return []

    def get_lottery_info(self):
        data = self.get_page_info()
        for c in data:
            lv2 = c.get("lottery_v2")
            if lv2:
                return lv2
        return None

    def query_all(self):
        ok, nick, uid = self.check_login()
        if not ok:
            return {"ok": False, "error": nick}

        result = {
            "ok": True,
            "nickname": nick,
            "uid": uid,
            "sign": self.get_sign_stat(),
            "tasks": [],
            "lottery": None,
        }

        tasks = self.get_tasks()
        status_map = {0: "未完成", 1: "待领奖", 2: "已完成", 7: "未完成"}
        result["tasks"] = [
            {
                "id": t["task_id"],
                "status": status_map.get(t.get("task_status"), str(t.get("task_status"))),
                "status_code": t.get("task_status", 0),
                "event": t.get("task_event", ""),
                "title": t.get("title", ""),
            }
            for t in tasks
        ]

        lottery = self.get_lottery_info()
        if lottery:
            sessions = []
            for s in lottery.get("lottery_list", []):
                sessions.append({
                    "session_id": s.get("session_id"),
                    "status": s.get("session_status"),
                    "times": s.get("times", 0),
                    "cost_point": s.get("cost_point", 0),
                    "lottery_type": "次数" if s.get("lottery_type") == 0 else "积分",
                })
            result["lottery"] = {
                "integral": lottery.get("integral", 0),
                "sessions": sessions,
            }

        return result

    def format_report(self):
        data = self.query_all()
        if not data.get("ok"):
            return f"❌ 查询失败：{data.get('error')}"

        lines = [f"👤 用户：{data['nickname']}（uid={data['uid']}）"]

        sign = data["sign"]
        if "error" in sign:
            lines.append(f"\n📅 签到：获取失败 {sign['error']}")
        else:
            status = "已签到" if sign.get("has_signed") else "未签到"
            lines.append(f"\n📅 签到：{status}  连续{sign.get('month_continuous_days', 0)}天  累计{sign.get('total_cumulative_days', 0)}天")

        tasks = data["tasks"]
        undone = [t for t in tasks if t["status_code"] in (0, 1)]
        lines.append(f"\n📝 任务：共 {len(tasks)} 个，待处理 {len(undone)} 个")
        for t in tasks[:15]:
            lines.append(f"  [{t['status']}] {t['title']} ({t['event']})")
        if len(tasks) > 15:
            lines.append(f"  ... 还有 {len(tasks) - 15} 个任务")

        lottery = data["lottery"]
        if lottery:
            lines.append(f"\n🎁 抽奖：当前积分 {lottery['integral']}")
            for s in lottery["sessions"]:
                lines.append(f"  场次{s['session_id']}：{s['lottery_type']}抽奖，剩余 {s['times']} 次")
        else:
            lines.append("\n🎁 抽奖：未获取到抽奖信息")

        lines.append(f"\n⏰ 查询时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return "\n".join(lines)
