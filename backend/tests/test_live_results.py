"""Persistence checks use disposable SQLite, never the operator database."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from backend.app import live_results, midterm
from backend.app.models import LiveRaceSnapshot


@pytest.fixture
def store(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    LiveRaceSnapshot.__table__.create(engine)
    yield sessionmaker(engine)
    engine.dispose()


def snapshot():
    raw = json.loads((Path(__file__).parent / "midterm_search.json").read_text())
    return midterm.to_json(midterm.normalize(raw, datetime.now(timezone.utc).isoformat()))


def test_idempotent_restart_office_projection_and_no_upstream(store, monkeypatch):
    value = snapshot()
    live_results.publish(value, store)
    live_results.publish(value, store)
    with store() as session:
        assert session.scalar(select(func.count()).select_from(LiveRaceSnapshot)) == sum(map(len, value["offices"].values()))
    monkeypatch.setattr(midterm, "get", lambda *_a, **_k: pytest.fail("upstream on read"))
    restarted = sessionmaker(store.kw["bind"])
    governor = live_results.read(midterm.ELECTION_DATE, "governor", restarted)
    assert set(governor["offices"]) == {"governor"}
    assert governor["revision"] == live_results.revision(midterm.ELECTION_DATE, store)
    assert governor["stale"] is False
    assert governor["offices"]["governor"][0]["candidates"][0]["votes"] == 0


def test_empty_partial_missing_and_certified_cannot_erase_valid(store):
    value = snapshot()
    live_results.publish(value, store)
    before = live_results.read(midterm.ELECTION_DATE, "governor", store)
    broken = copy.deepcopy(value)
    broken["offices"]["governor"][0]["candidates"] = []
    live_results.publish(broken, store)
    retained = live_results.read(midterm.ELECTION_DATE, "governor", store)
    assert retained["offices"]["governor"][0]["candidates"] == before["offices"]["governor"][0]["candidates"]
    assert retained["stale"] is True
    broken["offices"]["governor"][0]["candidates"] = [{"name": "Unknown", "votes": None}]
    live_results.publish(broken, store)
    assert live_results.read(midterm.ELECTION_DATE, "governor", store)["offices"]["governor"][0]["candidates"] == before["offices"]["governor"][0]["candidates"]
    with store.begin() as session:
        row = session.scalar(select(LiveRaceSnapshot).where(LiveRaceSnapshot.office == "governor"))
        row.certified = True
    changed = copy.deepcopy(value)
    changed["offices"]["governor"][0]["candidates"][0]["votes"] = 999
    live_results.publish(changed, store)
    assert live_results.read(midterm.ELECTION_DATE, "governor", store)["offices"]["governor"][0]["candidates"][0]["votes"] == 0


def test_transaction_rolls_back_all_races_and_old_results_survive(store):
    value = snapshot()
    live_results.publish(value, store)
    before = live_results.read(midterm.ELECTION_DATE, None, store)
    broken = copy.deepcopy(value)
    broken["offices"]["governor"][0]["candidates"][0]["votes"] = 99
    broken["offices"]["state-house"][0].pop("source_url")
    with pytest.raises(KeyError):
        live_results.publish(broken, store)
    assert live_results.read(midterm.ELECTION_DATE, None, store) == before


def test_overdue_data_retained_and_missing_office_is_explicit(store):
    value = snapshot()
    value["retrieved_at"] = "2020-01-01T00:00:00+00:00"
    live_results.publish(value, store)
    assert live_results.read(midterm.ELECTION_DATE, "governor", store)["stale"] is True
    with pytest.raises(ValueError, match="No scheduled"):
        live_results.read("2020-11-03", session_factory=store)


def test_additive_migration_preserves_existing_history(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from backend.app import database
    from sqlalchemy import text, inspect
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    monkeypatch.setattr(database, "engine", engine)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "0002")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO offices(id,name) VALUES ('retained','Historical office')"))
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT name FROM offices WHERE id='retained'")) == "Historical office"
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
        assert {i["name"] for i in inspect(connection).get_indexes("live_race_snapshots")} == {
            "ix_live_race_snapshots_election_date", "ix_live_race_snapshots_office"}
    engine.dispose()


def test_api_reads_only_selected_office_and_never_fetches(store, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    live_results.publish(snapshot(), store)
    monkeypatch.setattr(live_results, "SessionLocal", store)
    monkeypatch.setattr(midterm, "fetch", lambda: pytest.fail("HTTP fetched civicAPI"))
    client = TestClient(app)
    response = client.get("/api/midterm-2026?office=governor")
    assert response.status_code == 200
    assert set(response.json()["offices"]) == {"governor"}
    assert response.json()["revision"] == live_results.revision(midterm.ELECTION_DATE, store)
    assert client.get("/api/midterm-2026?office=invalid").status_code == 404
    assert client.get("/api/midterm-2026?office=governor", headers={"if-none-match": response.headers["etag"]}).status_code == 304


def test_null_or_renamed_candidates_do_not_freeze_a_race(store):
    value = snapshot()
    race = value["offices"]["governor"][0]
    race["candidates"] = [dict(race["candidates"][0], name="A", votes=10), dict(race["candidates"][0], name="Write-in", votes=None)]
    live_results.publish(value, store)
    race["candidates"][0]["votes"] = 20  # the write-in stays null
    live_results.publish(value, store)
    assert live_results.read(midterm.ELECTION_DATE, "governor", store)["offices"]["governor"][0]["candidates"][0]["votes"] == 20
    race["candidates"] = [dict(race["candidates"][0], name="A", votes=30)]  # write-in dropped
    live_results.publish(value, store)
    assert live_results.read(midterm.ELECTION_DATE, "governor", store)["offices"]["governor"][0]["candidates"][0]["votes"] == 30
    race["candidates"][0]["votes"] = None  # a known count turning missing is still rejected
    live_results.publish(value, store)
    retained = live_results.read(midterm.ELECTION_DATE, "governor", store)["offices"]["governor"][0]
    assert retained["candidates"][0]["votes"] == 30 and "Incomplete" in retained["refresh_error"]


def test_revision_is_stable_across_identical_runs_and_changes_with_votes(store):
    value = snapshot()
    live_results.publish(value, store)
    first = live_results.revision(midterm.ELECTION_DATE, store)
    again = copy.deepcopy(value)
    again["retrieved_at"] = "2099-01-01T00:00:00+00:00"
    live_results.publish(again, store)
    assert live_results.revision(midterm.ELECTION_DATE, store) == first
    # A race rebuilt from read() output (as retained races are) carries per-run metadata too.
    read_back = live_results.read(midterm.ELECTION_DATE, None, store)
    live_results.publish({**again, "offices": read_back["offices"]}, store)
    assert live_results.revision(midterm.ELECTION_DATE, store) == first
    again["offices"]["governor"][0]["candidates"][0]["votes"] = 5
    live_results.publish(again, store)
    assert live_results.revision(midterm.ELECTION_DATE, store) != first


def test_county_failure_goes_through_publish_and_retains_prior_race(store, monkeypatch):
    import requests
    raw = json.loads((Path(__file__).parent / "midterm_search.json").read_text())

    class Response:
        content = b"{}"
        def json(self):
            return raw

    county = midterm.County(fips="04001", name="Apache", percent_reporting=0, total_votes=0, candidates=[])
    monkeypatch.setattr(midterm, "county_results", lambda race_id: [county])
    live_results.publish(midterm.to_json(midterm.fetch(Response())), store)
    prior = {r["id"]: r for races in live_results.read(midterm.ELECTION_DATE, None, store)["offices"].values() for r in races}

    def down(race_id):
        raise requests.Timeout("slow")

    monkeypatch.setattr(midterm, "county_results", down)
    live_results.publish(midterm.to_json(midterm.fetch(Response(), prior)), store)
    governor = live_results.read(midterm.ELECTION_DATE, "governor", store)["offices"]["governor"][0]
    assert [c["name"] for c in governor["counties"]] == ["Apache"] and "Timeout" in governor["refresh_error"]


def test_catalog_endpoint_lists_races_and_reports_missing_table(store, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from backend.app import database
    from backend.app.main import app
    live_results.publish(snapshot(), store)
    monkeypatch.setattr(database, "SessionLocal", store)
    client = TestClient(app, raise_server_exceptions=False)
    body = client.get("/api/midterm-2026/catalog").json()
    assert {o["office"] for o in body["offices"]} >= {"governor"}
    empty = sessionmaker(create_engine(f"sqlite:///{tmp_path / 'empty.db'}"))
    monkeypatch.setattr(database, "SessionLocal", empty)
    assert client.get("/api/midterm-2026/catalog").status_code == 503
