"""Technical job/scheduler checks using retained data and mocked HTTP responses."""

import fcntl
import json
import plistlib
from datetime import datetime

import pytest
import requests
from sqlalchemy import delete, func, select

from test_2026_providers import client, retained
from backend.app.database import SessionLocal
from backend.app.lifecycle import activity
from backend.app.models import MetricObservation, PublicationSnapshot, RefreshAttempt
from backend.app.publication_input import SnapshotInput
from scripts import provider_2026, refresh_2026
from scripts.early_vote_runtime import run_refresh
from scripts.manage_early_vote_schedule import configuration, next_run


def fake_response(url, payload, status=200):
    response = requests.Response()
    response.status_code = status
    response.url = url
    response.headers["content-type"] = "application/json"
    response._content = json.dumps(payload).encode()
    return response


def mock_feeds(monkeypatch, tmp_path, *, broken=False):
    calls = []
    monkeypatch.setattr(provider_2026, "ROOT", tmp_path)
    monkeypatch.setattr(provider_2026, "RAW", tmp_path / "data/raw/2026")

    def get(url, **kwargs):
        calls.append((url, kwargs))
        category = url.rsplit("/", 1)[-1]
        if category == "inperson":
            return fake_response(url, {"error": "early-vote data not found"}, 404)
        if broken and category == "returned":
            raise requests.Timeout("Synthetic network timeout")
        if broken:
            return fake_response(url, {"state": "AZ", "category": category, "snapshot_date": "2026-10-27", "regions": {}, "statewide_total": {}})
        _, _, feed = retained(category)
        return fake_response(url, feed)

    monkeypatch.setattr(provider_2026.requests, "get", get)
    return calls


def test_fetch_is_civicapi_early_vote_only_with_timeouts(monkeypatch, tmp_path):
    calls = mock_feeds(monkeypatch, tmp_path)
    payloads, failures = provider_2026.fetch_provider_inputs()
    assert len(payloads) == 2 and not failures
    assert [url for url, _ in calls] == [f"https://civicapi.org/api/v2/early-vote/AZ/{category}" for category in ("requested", "returned", "inperson")]
    assert all(options == {"timeout": (5, 25), "allow_redirects": False} for _, options in calls)
    assert all(payload["kind"] == "participation" and not payload.get("votes") for payload in payloads)


def test_failed_or_empty_fetch_preserves_last_success_and_records_failure(client, monkeypatch, tmp_path):
    mock_feeds(monkeypatch, tmp_path, broken=True)
    with SessionLocal() as s:
        before = activity(s, "az-2026-governor")["statewide"]
        old_attempts = set(s.scalars(select(RefreshAttempt.id)))
    assert refresh_2026.refresh_early_voting() == 1
    with SessionLocal() as s:
        after = activity(s, "az-2026-governor")
        assert [(m["key"], m["value"]) for m in after["statewide"]["metrics"]] == [(m["key"], m["value"]) for m in before["metrics"]]
        assert after["failures"] and after["stale"]
        new_attempts = set(s.scalars(select(RefreshAttempt.id))) - old_attempts
        assert len(new_attempts) == 2
    with SessionLocal.begin() as s:
        s.execute(delete(RefreshAttempt).where(RefreshAttempt.id.in_(new_attempts)))


def test_successful_job_repeated_imports_reuse_existing_snapshots(client, monkeypatch):
    payloads = [retained(category)[1] for category in ("requested", "returned")]
    monkeypatch.setattr(provider_2026, "fetch_provider_inputs", lambda: (payloads, []))
    monkeypatch.setattr(refresh_2026, "save_manifest", SnapshotInput.model_validate)
    with SessionLocal() as s:
        before = [s.scalar(select(func.count()).select_from(model)) for model in (PublicationSnapshot, MetricObservation)]
    assert refresh_2026.refresh_early_voting() == 0
    assert refresh_2026.refresh_early_voting() == 0
    with SessionLocal() as s:
        assert [s.scalar(select(func.count()).select_from(model)) for model in (PublicationSnapshot, MetricObservation)] == before


def test_lock_and_job_audit_preserve_success_on_failure_and_skip_overlap(tmp_path):
    assert run_refresh(lambda: 0, local=tmp_path) == 0
    status_path = tmp_path / "early-voting-refresh-status.json"
    successful = json.loads(status_path.read_text())["last_success_at"]
    assert run_refresh(lambda: 1, local=tmp_path) == 1
    failed = json.loads(status_path.read_text())
    assert failed["status"] == "failed" and failed["last_success_at"] == successful
    with (tmp_path / "early-voting-refresh.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert run_refresh(lambda: pytest.fail("Overlapping callback ran"), local=tmp_path) == 0
        assert json.loads(status_path.read_text()) == failed
    log = (tmp_path / "logs/early-voting-refresh.log").read_text()
    assert "SUCCESS" in log and "FAILED" in log and "SKIPPED" in log


def test_launchd_configuration_uses_persistent_calendar_and_absolute_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///backend/local/custom.db")
    root = tmp_path / "Project With Spaces"
    config = configuration(root=root)
    assert config["StartCalendarInterval"] == [{"Hour": h, "Minute": 0} for h in (0, 6, 12, 18)]
    assert config["RunAtLoad"] is True
    assert config["ProgramArguments"] == [str(root / ".venv/bin/python"), str(root / "scripts/refresh_2026.py"), "--early-voting"]
    assert config["EnvironmentVariables"]["DATABASE_URL"] == f"sqlite:///{root / 'backend/local/custom.db'}"
    assert plistlib.loads(plistlib.dumps(config)) == config
    now = datetime(2026, 10, 28, 13, 0).astimezone()
    assert datetime.fromisoformat(next_run(config, now)).hour == 18
    with pytest.raises(ValueError):
        configuration(root=root, hours=5)
