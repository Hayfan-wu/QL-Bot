from bot.plugins import sf
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


def test_sf_uses_qinglong_credentials_from_project_env(tmp_path, monkeypatch):
    project_dir = tmp_path / "QL-SF"
    project_dir.mkdir()
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "QL_URL=http://sf-ql:5700/",
                "QL_CLIENT_ID=sf_client_id",
                "QL_CLIENT_SECRET=sf_client_secret",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("SF_PROJECT_DIR", str(project_dir))

    api = sf._get_sf_ql()

    assert api.base_url == "http://sf-ql:5700"
    assert api.client_id == "sf_client_id"
    assert api.client_secret == "sf_client_secret"


def test_sf_uses_default_project_env_without_bot_env(tmp_path, monkeypatch):
    project_dir = tmp_path / "QL-SF"
    project_dir.mkdir()
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "QL_URL=http://sf-default-ql:5700/",
                "QL_CLIENT_ID=default_sf_client_id",
                "QL_CLIENT_SECRET=default_sf_client_secret",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("SF_PROJECT_DIR", raising=False)
    monkeypatch.delenv("SFSY_SCRIPT_PATH", raising=False)
    monkeypatch.setattr(sf, "DEFAULT_SF_PROJECT_DIR", str(project_dir), raising=False)

    api = sf._get_sf_ql()

    assert api.base_url == "http://sf-default-ql:5700"
    assert api.client_id == "default_sf_client_id"
    assert api.client_secret == "default_sf_client_secret"


def test_sf_script_path_reads_project_env(tmp_path, monkeypatch):
    project_dir = tmp_path / "QL-SF"
    project_dir.mkdir()
    (project_dir / ".env").write_text(
        "SFSY_SCRIPT_PATH=/custom/sfsy.py\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("SFSY_SCRIPT_PATH", raising=False)
    monkeypatch.setattr(sf, "DEFAULT_SF_PROJECT_DIR", str(project_dir), raising=False)

    assert sf._get_sf_script_path() == "/custom/sfsy.py"


def test_sf_qr_output_dir_reads_project_env(tmp_path, monkeypatch):
    project_dir = tmp_path / "QL-SF"
    project_dir.mkdir()
    (project_dir / ".env").write_text(
        "SF_QR_OUTPUT_DIR=/custom/qr\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("SF_QR_OUTPUT_DIR", raising=False)
    monkeypatch.setattr(sf, "DEFAULT_SF_PROJECT_DIR", str(project_dir), raising=False)

    assert sf._get_sf_qr_output_dir() == "/custom/qr"


def test_build_sfsy_env_injects_cookie_from_qinglong(monkeypatch):
    monkeypatch.setattr(
        "bot.plugins.sf._get_env",
        lambda name: {"name": name, "value": "sessionId=s1;_login_user_id_=u1;_login_mobile_=13856914746"},
    )

    env = sf._build_sfsy_env()

    assert env[SF_COOKIE_ENV] == "sessionId=s1;_login_user_id_=u1;_login_mobile_=13856914746"
