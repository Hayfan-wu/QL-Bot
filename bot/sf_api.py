# -*- coding: utf-8 -*-
"""顺丰微信扫码登录 API。

该模块只完成顺丰会员扫码登录态识别，不承诺生成积分任务 Cookie。
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import qrcode
import requests


class SFLoginStatus(enum.IntEnum):
    NOT_SCAN = 0
    HAS_SCAN = 1
    CANCEL_SCAN = 2
    LOGINED = 3
    EXPIRED = 123
    UNKNOWN = -999


@dataclass
class SFQRCodeSession:
    owf_session: str
    raw_qr_url: str
    oauth_url: str
    qr_png: bytes
    created_at: float


@dataclass
class SFWechatLoginResult:
    status: SFLoginStatus
    message: str
    owf_session: str = ""
    token: str = ""
    memid: str = ""
    mem_no: str = ""
    mobile: str = ""
    sign: str = ""
    sign_type: str = ""
    ts: Optional[int] = None
    raw: Optional[Dict[str, Any]] = None

    @property
    def masked_mobile(self) -> str:
        if len(self.mobile) >= 7:
            return f"{self.mobile[:3]}****{self.mobile[-4:]}"
        return self.mobile

    @classmethod
    def from_response(cls, payload: Dict[str, Any], cookies: Dict[str, str]) -> "SFWechatLoginResult":
        if payload.get("success") is False:
            code = payload.get("code")
            status = SFLoginStatus.EXPIRED if code == 123 else SFLoginStatus.UNKNOWN
            return cls(
                status=status,
                message=payload.get("message") or payload.get("detailMessage") or "扫码失败",
                raw=payload,
            )

        result = payload.get("result") or {}
        raw_status = result.get("status")
        try:
            status = SFLoginStatus(raw_status)
        except ValueError:
            status = SFLoginStatus.UNKNOWN

        return cls(
            status=status,
            message=payload.get("message") or "",
            owf_session=cookies.get("OWFSESSION", ""),
            token=result.get("token") or "",
            memid=result.get("memid") or "",
            mem_no=result.get("memNo") or "",
            mobile=result.get("mobile") or cookies.get("loginUser", ""),
            sign=result.get("sign") or "",
            sign_type=result.get("signType") or "",
            ts=result.get("ts"),
            raw=payload,
        )


class SFWechatLoginAPI:
    BASE_URL = "https://www.sf-express.com"
    APPID = "wx0d9aa0e894066e87"
    REDIRECT_URI = "https://ucmp.sf-express.com/wxaccess/weixin/callback"
    STATE_PREFIX = "gh_8a8cce549a85__login_by_scan__0__"

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/126 Safari/537.36"
            ),
            "Referer": f"{self.BASE_URL}/chn/sc/login",
        })

    def build_oauth_url(self, owf_session: str) -> str:
        state = self.STATE_PREFIX + owf_session.upper()
        return (
            "https://open.weixin.qq.com/connect/oauth2/authorize"
            + "?appid=" + self.APPID
            + "&redirect_uri=" + quote(self.REDIRECT_URI, safe="")
            + "&response_type=code"
            + "&scope=snsapi_base"
            + "&state=" + state
            + "&connect_redirect=1#wechat_redirect"
        )

    def create_qrcode_session(self) -> SFQRCodeSession:
        response = self.session.get(
            f"{self.BASE_URL}/sf-service-core-web/service/user/qrcode/getqrcode",
            params={
                "timestamp": str(int(time.time() * 1000)),
                "lang": "sc",
                "region": "cn",
                "translate": "",
            },
            timeout=20,
        )
        response.raise_for_status()
        owf_session = self.session.cookies.get("OWFSESSION")
        if not owf_session:
            raise RuntimeError("顺丰未返回 OWFSESSION，无法生成微信扫码登录二维码")

        oauth_url = self.build_oauth_url(owf_session)
        qr = qrcode.make(oauth_url)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        return SFQRCodeSession(
            owf_session=owf_session,
            raw_qr_url="",
            oauth_url=oauth_url,
            qr_png=buffer.getvalue(),
            created_at=time.time(),
        )

    def poll_login(self) -> SFWechatLoginResult:
        response = self.session.get(
            f"{self.BASE_URL}/sf-service-core-web/service/user/qrcode/loginCheck",
            params={"rememberMe": "true"},
            timeout=20,
        )
        payload = response.json()
        return SFWechatLoginResult.from_response(payload, self.session.cookies.get_dict())

    def exchange_to_sfsy_cookie(self, result: SFWechatLoginResult) -> Tuple[bool, str, str]:
        """尝试将顺丰会员态换成积分任务 Cookie。

        当前已验证 OWFSESSION、memid、memNo、mobile 不能直接访问
        mcs-mimp-web 积分任务接口，因此这里返回明确的未支持状态。
        """
        return False, "", "未找到可用的 mcs-mimp-web 换票接口，请手动提交 sfsyUrl。"
