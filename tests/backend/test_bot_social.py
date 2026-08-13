"""Tests for the bot-facing social endpoints (/bot/matches, /bot/connect) and
the integrity fix that `neurotype` can't be self-assigned via a profile PUT.

Real app + real Postgres. User auth via the dev-token JWT path; bot endpoints
via the X-Bot-Key service key. Discord DM calls are monkeypatched (no live bot
token in the test env) — the behavior under test is the API's, not Discord's.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from src.db.session import engine
from src.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _require_schema():
    if "profiles" not in inspect(engine).get_table_names():
        pytest.skip("Schema not migrated — run `alembic upgrade head` before running backend tests.")


def _did() -> str:
    return str(uuid.uuid4().int)[:18]


def _auth_headers(discord_id: str, username: str = "testuser") -> dict:
    resp = client.post("/api/v1/auth/dev-token", params={"discord_id": discord_id, "username": username})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _bot_headers() -> dict:
    from src.core.config import get_settings
    get_settings().bot_api_key = "test-bot-key"
    return {"X-Bot-Key": "test-bot-key"}


def _onboard(discord_id: str, display_name: str = "Builder", neurotype: str | None = None) -> dict:
    headers = _bot_headers()
    r = client.post(
        "/api/v1/bot/profiles/upsert",
        headers=headers,
        json={"discord_id": discord_id, "discord_username": "u", "display_name": display_name,
              "onboarding_completed": True},
    )
    assert r.status_code == 200, r.text
    if neurotype:
        r2 = client.post(
            "/api/v1/bot/profiles/identified",
            headers=headers,
            json={"discord_id": discord_id, "neurotype": neurotype},
        )
        assert r2.status_code == 200, r2.text
    return r.json()


# ─────────── integrity: neurotype is not self-assignable ───────────
def test_neurotype_cannot_be_set_at_signup():
    did = _did()
    headers = _auth_headers(did)
    # Try to self-assign an archetype at profile creation — must be ignored.
    created = client.post(
        "/api/v1/profiles", headers=headers,
        json={"display_name": "NoCheat", "neurotype": "developer"},
    )
    assert created.status_code == 201, created.text
    assert created.json().get("neurotype") in (None, "")


def test_neurotype_cannot_be_set_via_profile_put():
    did = _did()
    headers = _auth_headers(did)
    created = client.post("/api/v1/profiles", headers=headers, json={"display_name": "NoCheat"})
    assert created.status_code == 201, created.text
    pid = created.json()["id"]
    # Try to self-assign a matching-relevant archetype without taking the quiz.
    upd = client.put(f"/api/v1/profiles/{pid}", headers=headers, json={"neurotype": "developer", "tagline": "hi"})
    assert upd.status_code == 200, upd.text
    assert upd.json()["tagline"] == "hi"          # legit field applied
    assert upd.json().get("neurotype") in (None, "")  # archetype ignored


# ─────────── /bot/matches ───────────
def test_bot_matches_requires_service_key():
    assert client.get(f"/api/v1/bot/matches/{_did()}").status_code == 401


def test_bot_matches_returns_enriched_public_matches():
    headers = _bot_headers()
    me, a, b = _did(), _did(), _did()
    _onboard(me, "Me", neurotype="developer")
    _onboard(a, "Ada", neurotype="fabricant")
    _onboard(b, "Bea", neurotype="mycelian")
    r = client.get(f"/api/v1/bot/matches/{me}", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "matches" in data
    for m in data["matches"]:
        assert "display_name" in m and "neurotype" in m and "score" in m
        assert "discord_id" not in m  # public-safe enrichment


def test_bot_matches_without_archetype_is_clear_error():
    headers = _bot_headers()
    did = _did()
    _onboard(did, "NoArchetype")  # no neurotype
    r = client.get(f"/api/v1/bot/matches/{did}", headers=headers)
    assert r.status_code == 400
    assert "quiz" in r.json()["detail"].lower()


# ─────────── /bot/connect ───────────
def test_bot_connect_requires_service_key():
    r = client.post("/api/v1/bot/connect", json={"from_discord_id": _did(), "to_discord_id": _did()})
    assert r.status_code == 401


def test_bot_connect_creates_request_and_notifies(monkeypatch):
    import src.api.routes as routes_module

    sent = []

    async def _fake_send_dm(discord_id, content):
        sent.append((discord_id, content))
        return True

    monkeypatch.setattr(routes_module.discord_client, "send_dm", _fake_send_dm)

    headers = _bot_headers()
    frm, to = _did(), _did()
    _onboard(frm, "From")
    _onboard(to, "To")

    r = client.post(
        "/api/v1/bot/connect",
        headers=headers,
        json={"from_discord_id": frm, "to_discord_id": to, "message": "let's build"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "sent"
    assert any(did == to for did, _ in sent)  # target DM'd

    dup = client.post(
        "/api/v1/bot/connect",
        headers=headers,
        json={"from_discord_id": frm, "to_discord_id": to},
    )
    assert dup.status_code == 409  # duplicate request rejected


def test_bot_connect_rejects_self_and_missing_profiles():
    headers = _bot_headers()
    same = _did()
    assert client.post(
        "/api/v1/bot/connect", headers=headers,
        json={"from_discord_id": same, "to_discord_id": same},
    ).status_code == 400
    assert client.post(
        "/api/v1/bot/connect", headers=headers,
        json={"from_discord_id": _did(), "to_discord_id": _did()},
    ).status_code == 404
