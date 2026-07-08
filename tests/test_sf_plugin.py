from bot.plugins.sf import (
    SF_COOKIE_ENV,
    SF_WECHAT_ENV,
    _format_image_cq,
    _format_wechat_value,
    _mask_cookie,
    _parse_sfsy_cookie,
)


def test_format_wechat_value_contains_member_fields():
    value = _format_wechat_value({
        "owf_session": "abc",
        "memid": "MEMID",
        "mem_no": "MEMNO",
        "mobile": "13856914746",
    })

    assert '"owf_session": "abc"' in value
    assert '"memid": "MEMID"' in value
    assert '"mem_no": "MEMNO"' in value
    assert '"mobile": "13856914746"' in value


def test_parse_sfsy_cookie_accepts_required_fields():
    cookie = "sessionId=s1;_login_user_id_=u1;_login_mobile_=13856914746"
    parsed = _parse_sfsy_cookie(cookie)

    assert parsed["sessionId"] == "s1"
    assert parsed["_login_user_id_"] == "u1"
    assert parsed["_login_mobile_"] == "13856914746"


def test_parse_sfsy_cookie_rejects_missing_mobile():
    cookie = "sessionId=s1;_login_user_id_=u1"
    parsed = _parse_sfsy_cookie(cookie)

    assert parsed == {}


def test_mask_cookie_hides_sensitive_values():
    masked = _mask_cookie("sessionId=abcdef123456;_login_mobile_=13856914746")

    assert "abcdef123456" not in masked
    assert "13856914746" not in masked
    assert "sessionId=abcd..." in masked
    assert "_login_mobile_=1385..." in masked


def test_env_names_are_stable():
    assert SF_COOKIE_ENV == "sfsyUrl"
    assert SF_WECHAT_ENV == "SF_WECHAT_LOGIN"


def test_format_image_cq_uses_file_uri_for_local_path():
    cq = _format_image_cq(r"C:\tmp\sf_login_10001.png")

    assert cq.startswith("[CQ:image,file=file:///")
    assert "sf_login_10001.png" in cq
