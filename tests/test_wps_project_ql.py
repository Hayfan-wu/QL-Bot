from bot.plugins import wps
from bot.ql_api import QingLongAPI


def test_qinglong_api_can_be_created_from_explicit_credentials():
    api = QingLongAPI(
        base_url="http://project-ql:5700/",
        client_id="project_client_id",
        client_secret="project_client_secret",
    )

    assert api.base_url == "http://project-ql:5700"
    assert api.client_id == "project_client_id"
    assert api.client_secret == "project_client_secret"


def test_wps_uses_qinglong_credentials_from_project_env(tmp_path, monkeypatch):
    project_dir = tmp_path / "QL-WPS"
    project_dir.mkdir()
    (project_dir / ".env").write_text(
        "\n".join(
            [
                "QL_URL=http://wps-ql:5700/",
                "QL_CLIENT_ID=wps_client_id",
                "QL_CLIENT_SECRET=wps_client_secret",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("WPS_PROJECT_DIR", str(project_dir))

    api = wps._get_wps_ql()

    assert api.base_url == "http://wps-ql:5700"
    assert api.client_id == "wps_client_id"
    assert api.client_secret == "wps_client_secret"


def test_wps_script_path_prefers_new_env_name(monkeypatch):
    monkeypatch.setenv("WPS_SCRIPT_PATH", "/opt/QL-WPS/wps_auto.py")
    monkeypatch.setenv("WPS_AUTO_PATH", "/old/path/wps_auto.py")

    assert wps._get_wps_script_path() == "/opt/QL-WPS/wps_auto.py"
