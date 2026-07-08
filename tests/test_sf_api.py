from bot.sf_api import SFLoginStatus, SFWechatLoginAPI, SFWechatLoginResult


def test_build_oauth_url_uses_owf_session_token():
    api = SFWechatLoginAPI()
    url = api.build_oauth_url("310ac078ad53441d8aa89dc72b197ee3")

    assert url.startswith("https://open.weixin.qq.com/connect/oauth2/authorize?")
    assert "appid=wx0d9aa0e894066e87" in url
    assert "redirect_uri=https%3A%2F%2Fucmp.sf-express.com%2Fwxaccess%2Fweixin%2Fcallback" in url
    assert "scope=snsapi_base" in url
    assert "state=gh_8a8cce549a85__login_by_scan__0__310AC078AD53441D8AA89DC72B197EE3" in url


def test_parse_login_status_logined():
    payload = {
        "success": True,
        "code": 0,
        "result": {
            "status": 3,
            "token": "abc",
            "memid": "MEMID",
            "memNo": "MEMNO",
            "mobile": "13856914746",
        },
    }

    result = SFWechatLoginResult.from_response(payload, {"OWFSESSION": "abc", "loginUser": "13856914746"})

    assert result.status == SFLoginStatus.LOGINED
    assert result.memid == "MEMID"
    assert result.mem_no == "MEMNO"
    assert result.mobile == "13856914746"
    assert result.masked_mobile == "138****4746"


def test_parse_login_status_expired_error():
    payload = {
        "success": False,
        "code": 123,
        "message": "登录过期",
        "detailMessage": "Not found login info",
        "result": None,
    }

    result = SFWechatLoginResult.from_response(payload, {})

    assert result.status == SFLoginStatus.EXPIRED
    assert result.message == "登录过期"


def test_exchange_to_sfsy_cookie_is_explicitly_unsupported():
    api = SFWechatLoginAPI()
    result = SFWechatLoginResult(
        status=SFLoginStatus.LOGINED,
        message="请求成功",
        owf_session="owf",
        memid="memid",
        mem_no="memno",
        mobile="13856914746",
    )

    ok, cookie, message = api.exchange_to_sfsy_cookie(result)

    assert ok is False
    assert cookie == ""
    assert "未找到可用的 mcs-mimp-web 换票接口" in message
