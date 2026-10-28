"""Read-only Cloudflare inspection and private token retention, without live access."""

import base64
import json
import stat

import pytest
from test_pipeline_api import ROOT  # noqa: F401 -- establishes module search path

from scripts import inspect_cloudflare as inspection


def configure(monkeypatch, tmp_path, *, wrong_tunnel=False):
    monkeypatch.setattr(inspection, "ROOT", tmp_path)
    monkeypatch.setattr(inspection, "API_TOKEN", tmp_path / "secrets/api-token")
    monkeypatch.setattr(
        inspection, "CONNECTOR_TOKEN", tmp_path / "secrets/tunnel-token"
    )
    inspection.private_write(inspection.API_TOKEN, "synthetic-api-secret")
    token = base64.b64encode(
        json.dumps(
            {
                "t": "wrong-id" if wrong_tunnel else inspection.TARGET["tunnel_id"],
                "s": "synthetic-connector-secret",
            }
        ).encode()
    ).decode()
    calls = []

    class Response:
        status_code = 200
        ok = True

        def __init__(self, value):
            self.value = value

        def json(self):
            return {"success": True, "result": self.value}

    class Session:
        def __init__(self):
            self.headers = {}

        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            path = url.removeprefix("https://api.cloudflare.com/client/v4/")
            if path == "zones":
                return Response(
                    [
                        {
                            "name": "azelections.app",
                            "id": "zone",
                            "status": "active",
                            "account": {"id": "account"},
                        }
                    ]
                )
            if path.endswith("/configurations"):
                return Response(
                    {
                        "config": {
                            "ingress": [
                                {
                                    "hostname": "other.example",
                                    "service": "http://username:private-password@other:8080/?token=secret-query",
                                },
                                {"service": "http_status:404"},
                            ]
                        }
                    }
                )
            if path.endswith("/token"):
                return Response(token)
            if path.endswith("/dns_records"):
                return Response(
                    [
                        {
                            "id": "mail",
                            "name": "azelections.app",
                            "type": "MX",
                            "content": "mail.example",
                        }
                    ]
                )
            if "/rulesets/" in path:
                return Response(
                    {"id": "existing-rule-set", "rules": [{"id": "existing-rule"}]}
                )
            assert path.endswith(inspection.TARGET["tunnel_id"])
            return Response({"name": inspection.TARGET["tunnel_name"]})

    monkeypatch.setattr(inspection.requests, "Session", Session)
    return token, calls


def test_inspection_retains_other_configuration_and_never_prints_secrets(
    monkeypatch, tmp_path, capsys
):
    token, calls = configure(monkeypatch, tmp_path)
    inspection.inspect()
    output = capsys.readouterr().out
    for secret in (token, "synthetic-api-secret", "private-password", "secret-query"):
        assert secret not in output
    assert not inspection.CONNECTOR_TOKEN.exists()
    snapshot = json.loads(
        (tmp_path / ".production/cloudflare-inventory.json").read_text()
    )
    assert snapshot["dns_records"][0]["id"] == "mail"
    assert (
        snapshot["configuration"]["config"]["ingress"][0]["hostname"] == "other.example"
    )
    assert json.loads(output)["changes_applied"] is False
    assert not any(url.endswith("/token") for url, _ in calls)
    assert all(
        options["allow_redirects"] is False and options["timeout"] == (5, 30)
        for _, options in calls
    )


def test_wrong_tunnel_token_is_not_saved(monkeypatch, tmp_path):
    token, _ = configure(monkeypatch, tmp_path, wrong_tunnel=True)
    monkeypatch.setattr("sys.argv", ["inspect_cloudflare.py", "save-connector-token"])
    monkeypatch.setattr(inspection, "getpass", lambda _: token)
    with pytest.raises(SystemExit, match="does not identify"):
        inspection.main()
    assert not inspection.CONNECTOR_TOKEN.exists()


def test_connector_only_setup_requires_no_account_api_call(
    monkeypatch, tmp_path, capsys
):
    token, calls = configure(monkeypatch, tmp_path)
    inspection.API_TOKEN.unlink()
    monkeypatch.setattr("sys.argv", ["inspect_cloudflare.py", "save-connector-token"])
    monkeypatch.setattr(inspection, "getpass", lambda _: token)
    inspection.main()
    assert not calls
    assert inspection.CONNECTOR_TOKEN.read_text().strip() == token
    assert stat.S_IMODE(inspection.CONNECTOR_TOKEN.stat().st_mode) == 0o600
    assert token not in capsys.readouterr().out
