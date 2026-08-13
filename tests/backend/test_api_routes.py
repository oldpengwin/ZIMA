"""
API route tests, rewritten against the real FastAPI app + real Postgres
test DB instead of mocking ProfileManager (which no longer exists — see
src/services/*). This exercises the actual dependency chain: real JWT
issuance/verification, real SQLAlchemy queries, real HTTP status codes —
which is what caught the original TokenData/uuid-import bugs being invisible
to the old, fully-mocked test suite.

Auth in these tests goes through the real /auth/dev-token endpoint (issues
a real, valid JWT for a given discord_id, no password) rather than mocking
get_current_user — see core/auth.py and core/config.py for why this
endpoint only exists outside production.
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


def _auth_headers(discord_id: str, username: str = "testuser") -> dict:
    resp = client.post("/api/v1/auth/dev-token", params={"discord_id": discord_id, "username": username})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "zima-api"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data and "docs" in data and "health" in data


def test_dev_token_issues_a_real_working_jwt():
    headers = _auth_headers(discord_id=str(uuid.uuid4().int)[:18])
    # A garbage/missing token must be rejected...
    assert client.get("/api/v1/profiles/me").status_code == 401
    # ...but a real one, even against a fresh account with no profile yet, must
    # decode successfully and reach the 404-not-found branch, not a 401.
    resp = client.get("/api/v1/profiles/me", headers=headers)
    assert resp.status_code == 404


def test_create_and_fetch_profile_end_to_end():
    discord_id = str(uuid.uuid4().int)[:18]
    headers = _auth_headers(discord_id)

    create_resp = client.post(
        "/api/v1/profiles",
        headers=headers,
        json={
            "display_name": "Test User",
            "neurotype": "developer",
            "skills": ["Python", "JavaScript"],
            "offering": ["Backend development"],
            "looking_for": ["Frontend developers"],
            "location": "Test City",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["display_name"] == "Test User"
    assert created["neurotype"] == "developer"
    assert created["discord_id"] == discord_id  # server-set from the token, not client input

    # Duplicate creation for the same account is rejected, not silently overwritten.
    dup_resp = client.post("/api/v1/profiles", headers=headers, json={"display_name": "Second Attempt"})
    assert dup_resp.status_code == 409

    get_resp = client.get(f"/api/v1/profiles/{created['id']}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["display_name"] == "Test User"

    me_resp = client.get("/api/v1/profiles/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["id"] == created["id"]


def test_update_profile_requires_ownership():
    owner_discord_id = str(uuid.uuid4().int)[:18]
    owner_headers = _auth_headers(owner_discord_id)
    create_resp = client.post("/api/v1/profiles", headers=owner_headers, json={"display_name": "Owner"})
    profile_id = create_resp.json()["id"]

    # A different authenticated user cannot update someone else's profile.
    other_headers = _auth_headers(str(uuid.uuid4().int)[:18])
    forbidden = client.put(f"/api/v1/profiles/{profile_id}", headers=other_headers, json={"bio": "hacked"})
    assert forbidden.status_code == 403

    # The owner can.
    ok = client.put(f"/api/v1/profiles/{profile_id}", headers=owner_headers, json={"bio": "real bio"})
    assert ok.status_code == 200
    assert ok.json()["bio"] == "real bio"

    # An invalid neurotype is rejected with a 400, not a silent write or a 500.
    bad = client.put(f"/api/v1/profiles/{profile_id}", headers=owner_headers, json={"neurotype": "not-a-real-archetype"})
    assert bad.status_code == 400


def test_connection_request_end_to_end():
    """Regression test for the specific bug found in the audit: POST
    /match/request used uuid.uuid4() without importing uuid, so this endpoint
    crashed on every real call. It's now backed by a real connection_service
    call and a real DB row."""
    a_headers = _auth_headers(str(uuid.uuid4().int)[:18])
    a_profile = client.post("/api/v1/profiles", headers=a_headers, json={"display_name": "Requester"}).json()

    b_headers = _auth_headers(str(uuid.uuid4().int)[:18])
    b_profile = client.post("/api/v1/profiles", headers=b_headers, json={"display_name": "Recipient"}).json()

    resp = client.post(
        "/api/v1/match/request",
        headers=a_headers,
        json={"to_user_id": b_profile["id"], "message": "let's collaborate"},
    )
    assert resp.status_code == 201, resp.text
    connection = resp.json()
    assert connection["status"] == "pending"
    assert connection["message"] == "let's collaborate"

    # A duplicate request between the same pair is rejected, not duplicated.
    dup = client.post("/api/v1/match/request", headers=a_headers, json={"to_user_id": b_profile["id"]})
    assert dup.status_code == 409

    # The recipient can see and accept it.
    inbox = client.get(f"/api/v1/match/{b_profile['id']}/requests", headers=b_headers)
    assert inbox.status_code == 200
    assert len(inbox.json()["requests"]) == 1

    accept = client.put(
        f"/api/v1/match/requests/{connection['id']}", headers=b_headers, json={"status": "accepted"}
    )
    assert accept.status_code == 200
    assert accept.json()["status"] == "accepted"

    # Accepting triggers a best-effort ProfileMatchStats recompute for both
    # sides (routes.py) — the count should already reflect it, not require a
    # second unrelated write to become correct.
    a_stats = client.get(f"/api/v1/profiles/{a_profile['id']}/stats", headers=a_headers)
    b_stats = client.get(f"/api/v1/profiles/{b_profile['id']}/stats", headers=b_headers)
    assert a_stats.status_code == 200 and b_stats.status_code == 200
    assert a_stats.json()["total_connections"] == 1
    assert b_stats.json()["total_connections"] == 1


def test_neurotypes_endpoint_lists_all_ten_canonical_archetypes():
    resp = client.get("/api/v1/neurotypes")
    assert resp.status_code == 200
    neurotypes = resp.json()["neurotypes"]
    assert len(neurotypes) == 10
    assert set(neurotypes.keys()) == {
        "seedcaster", "fabricant", "mycelian", "terraformer", "developer",
        "artisan", "chronicler", "cultivar", "loomkeeper", "verdant",
    }


def test_privacy_export_and_delete_reachable_end_to_end():
    """Smoke test that the privacy endpoints are wired correctly through the
    real HTTP layer — the deep behavioral guarantees live in
    test_privacy_service.py."""
    headers = _auth_headers(str(uuid.uuid4().int)[:18])
    client.post("/api/v1/profiles", headers=headers, json={"display_name": "Deletable"})

    export = client.get("/api/v1/users/me/export", headers=headers)
    assert export.status_code == 200
    assert export.json()["profile"]["display_name"] == "Deletable"

    preview = client.get("/api/v1/users/me/deletion-preview", headers=headers)
    assert preview.status_code == 200

    delete = client.delete("/api/v1/users/me", headers=headers)
    assert delete.status_code == 200
    assert delete.json()["status"] == "completed"

    # Profile is really gone now.
    gone = client.get("/api/v1/profiles/me", headers=headers)
    assert gone.status_code == 404


def test_account_deletion_triggers_discord_access_revocation():
    """See src/api/routes.py's _revoke_discord_access_best_effort and
    src/core/discord_client.py — deleting an account must also try to pull
    the Discord-side access that account was ever granted, not just erase
    the database rows. discord_client's real HTTP calls are monkeypatched
    here since there's no live Discord bot token in this environment; the
    behavior under test is "the deletion endpoint calls out with the right
    discord_id," not Discord's own API behavior."""
    import src.api.routes as routes_module

    calls = []

    async def _fake_remove_role(discord_id, role_id, *, reason):
        calls.append(("remove_role", discord_id, role_id))
        return True

    async def _fake_send_dm(discord_id, content):
        calls.append(("send_dm", discord_id, content))
        return True

    original_remove = routes_module.discord_client.remove_guild_member_role
    original_dm = routes_module.discord_client.send_dm
    routes_module.discord_client.remove_guild_member_role = _fake_remove_role
    routes_module.discord_client.send_dm = _fake_send_dm
    try:
        discord_id = str(uuid.uuid4().int)[:18]
        headers = _auth_headers(discord_id)
        client.post("/api/v1/profiles", headers=headers, json={"display_name": "ToRevoke"})

        resp = client.delete("/api/v1/users/me", headers=headers)
        assert resp.status_code == 200
    finally:
        routes_module.discord_client.remove_guild_member_role = original_remove
        routes_module.discord_client.send_dm = original_dm

    # A DM was attempted for the right discord_id, confirming deletion.
    dm_calls = [c for c in calls if c[0] == "send_dm" and c[1] == discord_id]
    assert len(dm_calls) == 1
    assert "deleted" in dm_calls[0][2].lower()


def test_connection_events_trigger_discord_dm_notifications():
    """A connection request and its acceptance must each attempt a DM to
    the relevant party — the two concrete gaps described in
    core/discord_client.py's module docstring (things that happen on the
    web side that were previously invisible on Discord)."""
    import src.api.routes as routes_module

    calls = []

    async def _fake_send_dm(discord_id, content):
        calls.append((discord_id, content))
        return True

    original_dm = routes_module.discord_client.send_dm
    routes_module.discord_client.send_dm = _fake_send_dm
    try:
        a_discord_id = str(uuid.uuid4().int)[:18]
        b_discord_id = str(uuid.uuid4().int)[:18]
        a_headers = _auth_headers(a_discord_id)
        a_profile = client.post("/api/v1/profiles", headers=a_headers, json={"display_name": "Notifier A"}).json()
        b_headers = _auth_headers(b_discord_id)
        b_profile = client.post("/api/v1/profiles", headers=b_headers, json={"display_name": "Notifier B"}).json()

        conn = client.post(
            "/api/v1/match/request", headers=a_headers, json={"to_user_id": b_profile["id"]}
        ).json()
        # B (the recipient) should have been notified.
        assert any(discord_id == b_discord_id for discord_id, _ in calls)

        client.put(f"/api/v1/match/requests/{conn['id']}", headers=b_headers, json={"status": "accepted"})
        # A (the original requester) should have been notified of the acceptance.
        assert any(discord_id == a_discord_id for discord_id, _ in calls)
    finally:
        routes_module.discord_client.send_dm = original_dm


def test_profile_roles_endpoint_reflects_role_grants_table():
    """See src/services/role_service.py — the Node bot writes role_grants
    directly to the shared DB; this is the first thing on the Python side
    that reads it back out."""
    from src.database.models import RoleGrant
    from src.db.session import session_scope

    discord_id = str(uuid.uuid4().int)[:18]
    headers = _auth_headers(discord_id)
    profile = client.post("/api/v1/profiles", headers=headers, json={"display_name": "Vetted Person"}).json()

    with session_scope() as db:
        db.add(RoleGrant(discord_id=discord_id, role_key="vetted", source="onboarding"))

    resp = client.get(f"/api/v1/profiles/{profile['id']}/roles", headers=headers)
    assert resp.status_code == 200
    roles = resp.json()
    assert len(roles) == 1
    assert roles[0]["role_key"] == "vetted"
    assert roles[0]["discord_id"] == discord_id


# ─────────────────── neurotype quiz + network (feature: neurotype-quiz) ───────────────────


def test_quiz_bank_is_weight_free():
    resp = client.get("/api/v1/quiz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "v1"
    assert len(data["questions"]) == 20
    for q in data["questions"]:
        for o in q["options"]:
            assert "weights" not in o  # scoring weights must never leave the server


def test_neurotypes_enriched_with_graph_metadata():
    resp = client.get("/api/v1/neurotypes")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["neurotypes"]) == 10
    dev = data["neurotypes"]["developer"]
    assert dev["emoji"] and dev["color"]["base"] and dev["tagline"]
    assert data["edges"]  # graph edges present


def test_quiz_submit_sets_assessed_then_self_select_identified():
    discord_id = str(uuid.uuid4().int)[:18]
    headers = _auth_headers(discord_id)
    client.post("/api/v1/profiles", headers=headers, json={"display_name": "Quizzer", "skills": ["python", "devops"]})

    resp = client.post(
        "/api/v1/quiz/submit",
        headers=headers,
        json={"answers": {"q01": "c", "q02": "a", "q13": "a"}},  # fabricant-leaning + dev skills
    )
    assert resp.status_code == 200, resp.text
    top = resp.json()["result"]["top"]
    assert top is not None

    me = client.get("/api/v1/profiles/me", headers=headers).json()
    assert me["assessed_neurotype"] == top

    pid = me["id"]
    sel = client.put(
        f"/api/v1/profiles/{pid}/identified-neurotype", headers=headers, json={"neurotype": "mycelian"}
    )
    assert sel.status_code == 200
    assert sel.json()["identified_neurotype"] == "mycelian"
    assert sel.json()["neurotype"] == "mycelian"  # alias follows the chosen identity


def test_quiz_submit_requires_auth():
    assert client.post("/api/v1/quiz/submit", json={"answers": {}}).status_code == 401


def test_set_identified_rejects_unknown_type():
    discord_id = str(uuid.uuid4().int)[:18]
    headers = _auth_headers(discord_id)
    pid = client.post("/api/v1/profiles", headers=headers, json={"display_name": "Picky"}).json()["id"]
    bad = client.put(f"/api/v1/profiles/{pid}/identified-neurotype", headers=headers, json={"neurotype": "wizard"})
    assert bad.status_code == 400


def test_network_aggregate_is_public_safe():
    resp = client.get("/api/v1/network")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) == 10
    assert "edges" in data and "total_builders" in data
    for point in data["location_points"]:
        assert "discord_id" not in point  # globe must never carry identity


def test_bot_quiz_submit_requires_service_key():
    r = client.post("/api/v1/bot/quiz/submit", json={"discord_id": "123", "answers": {}})
    assert r.status_code == 401


# ─────────────────── bot->API migration (feature: security-quickwins) ───────────────────


def _bot_headers():
    from src.core.config import get_settings
    get_settings().bot_api_key = "test-bot-key"  # ensure the service key is set for the test
    return {"X-Bot-Key": "test-bot-key"}


def test_bot_profile_upsert_is_create_then_update():
    headers = _bot_headers()
    did = str(uuid.uuid4().int)[:18]
    created = client.post(
        "/api/v1/bot/profiles/upsert",
        headers=headers,
        json={"discord_id": did, "discord_username": "botuser", "display_name": "Bot Onboard",
              "skills": ["python"], "onboarding_completed": True},
    )
    assert created.status_code == 200, created.text
    assert created.json()["created"] is True
    assert created.json()["onboarding_completed_at"] is not None

    updated = client.post(
        "/api/v1/bot/profiles/upsert",
        headers=headers,
        json={"discord_id": did, "display_name": "Renamed"},
    )
    assert updated.status_code == 200
    assert updated.json()["created"] is False
    assert updated.json()["display_name"] == "Renamed"

    got = client.get(f"/api/v1/bot/profiles/by-discord/{did}", headers=headers)
    assert got.status_code == 200 and got.json()["discord_id"] == did


def test_bot_role_grant_is_idempotent():
    headers = _bot_headers()
    did = str(uuid.uuid4().int)[:18]
    client.post("/api/v1/bot/profiles/upsert", headers=headers, json={"discord_id": did, "display_name": "Roled"})
    r = client.post("/api/v1/bot/role-grants", headers=headers,
                    json={"discord_id": did, "role_key": "vetted", "source": "onboarding"})
    assert r.status_code == 200, r.text
    assert r.json()["role_key"] == "vetted"
    r2 = client.post("/api/v1/bot/role-grants", headers=headers, json={"discord_id": did, "role_key": "vetted"})
    assert r2.status_code == 200  # upsert, no duplicate error


def test_bot_endpoints_require_service_key():
    assert client.post("/api/v1/bot/profiles/upsert", json={"discord_id": "x", "display_name": "y"}).status_code == 401
    assert client.get("/api/v1/bot/profiles/by-discord/x").status_code == 401
    assert client.post("/api/v1/bot/role-grants", json={"discord_id": "x", "role_key": "vetted"}).status_code == 401


def test_search_query_length_capped():
    # max_length=200 on the q param -> 422 for oversized input. /profiles search
    # requires auth (security-fixes: prevents anonymous scraping of the
    # userbase), so authenticate first — an unauthenticated call now correctly
    # 401s before query validation ever runs, which is exercised separately by
    # test_profile_reads_require_authentication below.
    headers = _auth_headers(str(uuid.uuid4().int)[:18])
    resp = client.get("/api/v1/profiles", params={"q": "a" * 500}, headers=headers)
    assert resp.status_code == 422
# ─────────────────── security fixes: authz + PII on profile reads ───────────────────


def test_profile_reads_require_authentication():
    """GET on other-user profile data must not be reachable anonymously —
    previously these leaked every user's discord_id to unauthenticated callers."""
    headers = _auth_headers(str(uuid.uuid4().int)[:18])
    pid = client.post("/api/v1/profiles", headers=headers, json={"display_name": "Private"}).json()["id"]
    for path in (
        f"/api/v1/profiles/{pid}",
        f"/api/v1/profiles/{pid}/stats",
        f"/api/v1/profiles/{pid}/roles",
        "/api/v1/profiles",
    ):
        assert client.get(path).status_code == 401, path


def test_other_users_profile_omits_discord_id():
    """A user viewing someone else's profile (or the search list) gets the
    public view with no discord_id; viewing your OWN profile still returns it."""
    a_id = str(uuid.uuid4().int)[:18]
    a_headers = _auth_headers(a_id)
    a = client.post("/api/v1/profiles", headers=a_headers, json={"display_name": "Alpha"}).json()
    b_headers = _auth_headers(str(uuid.uuid4().int)[:18])

    other_view = client.get(f"/api/v1/profiles/{a['id']}", headers=b_headers)
    assert other_view.status_code == 200
    assert "discord_id" not in other_view.json()
    assert other_view.json()["display_name"] == "Alpha"

    own_view = client.get(f"/api/v1/profiles/{a['id']}", headers=a_headers)
    assert own_view.json().get("discord_id") == a_id

    listing = client.get("/api/v1/profiles", headers=b_headers)
    assert listing.status_code == 200
    assert all("discord_id" not in p for p in listing.json())


def test_profile_roles_restricted_to_self_or_admin():
    a_headers = _auth_headers(str(uuid.uuid4().int)[:18])
    a = client.post("/api/v1/profiles", headers=a_headers, json={"display_name": "RoleOwner"}).json()
    b_headers = _auth_headers(str(uuid.uuid4().int)[:18])
    assert client.get(f"/api/v1/profiles/{a['id']}/roles", headers=b_headers).status_code == 403


def test_admin_delete_requires_admin_privilege():
    """DELETE /admin/users/{id} must reject non-admins (403) and only work for
    a caller whose discord_id is in ADMIN_DISCORD_IDS."""
    from src.core.config import get_settings

    victim_headers = _auth_headers(str(uuid.uuid4().int)[:18])
    victim = client.post("/api/v1/profiles", headers=victim_headers, json={"display_name": "Victim"}).json()

    # An ordinary authenticated user is not an admin.
    normal_headers = _auth_headers(str(uuid.uuid4().int)[:18])
    assert client.delete(f"/api/v1/admin/users/{victim['id']}", headers=normal_headers).status_code == 403

    # Grant admin to a caller (mutate the cached settings list) and it succeeds.
    admin_id = str(uuid.uuid4().int)[:18]
    admin_headers = _auth_headers(admin_id)
    settings = get_settings()
    settings.admin_discord_ids.append(admin_id)
    try:
        ok = client.delete(f"/api/v1/admin/users/{victim['id']}", headers=admin_headers)
        assert ok.status_code == 200, ok.text
        assert ok.json()["status"] == "completed"
    finally:
        settings.admin_discord_ids.remove(admin_id)
