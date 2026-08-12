"""
Tests for src/services/profile_service.py against a real Postgres test DB.

Replaces the old tests/backend/test_profile_manager.py, which mocked
psycopg2 entirely and therefore never exercised real SQL — the module it
tested (core/profile_manager.py) is now deprecated in favor of this
SQLAlchemy-based service layer (see the deprecation note at the top of
profile_manager.py).
"""

import uuid

import pytest
from sqlalchemy import inspect

from src.db.session import engine, session_scope
from src.services import profile_service


@pytest.fixture(autouse=True)
def _require_schema():
    if "profiles" not in inspect(engine).get_table_names():
        pytest.skip("Schema not migrated — run `alembic upgrade head` before running backend tests.")


def _discord_id() -> str:
    return str(uuid.uuid4().int)[:18]


def test_create_profile_requires_discord_id_and_display_name():
    with session_scope() as db:
        with pytest.raises(profile_service.InvalidProfileDataError):
            profile_service.create_profile(db, {"display_name": "No Discord Id"})
        with pytest.raises(profile_service.InvalidProfileDataError):
            profile_service.create_profile(db, {"discord_id": _discord_id()})


def test_create_profile_rejects_invalid_neurotype():
    with session_scope() as db:
        with pytest.raises(profile_service.InvalidProfileDataError):
            profile_service.create_profile(
                db, {"discord_id": _discord_id(), "display_name": "Bad Archetype", "neurotype": "wizard"}
            )


def test_create_profile_allows_null_neurotype_before_quiz():
    with session_scope() as db:
        profile = profile_service.create_profile(db, {"discord_id": _discord_id(), "display_name": "Pre-Quiz User"})
        assert profile.neurotype is None


def test_duplicate_discord_id_rejected():
    discord_id = _discord_id()
    with session_scope() as db:
        profile_service.create_profile(db, {"discord_id": discord_id, "display_name": "First"})
    with session_scope() as db:
        with pytest.raises(profile_service.DuplicateProfileError):
            profile_service.create_profile(db, {"discord_id": discord_id, "display_name": "Second"})


def test_get_profile_by_id_and_discord_id():
    discord_id = _discord_id()
    with session_scope() as db:
        created = profile_service.create_profile(db, {"discord_id": discord_id, "display_name": "Findable"})
        pid = created.id

    with session_scope() as db:
        by_id = profile_service.get_profile_by_id(db, str(pid))
        by_discord = profile_service.get_profile_by_discord_id(db, discord_id)
        assert by_id is not None and by_discord is not None
        assert by_id.id == by_discord.id


def test_get_profile_by_id_returns_none_for_garbage_input():
    with session_scope() as db:
        assert profile_service.get_profile_by_id(db, "not-a-uuid") is None
        assert profile_service.get_profile_by_id(db, str(uuid.uuid4())) is None


def test_update_profile_only_touches_allowed_fields():
    with session_scope() as db:
        created = profile_service.create_profile(db, {"discord_id": _discord_id(), "display_name": "Updatable"})
        pid = str(created.id)

    with session_scope() as db:
        updated = profile_service.update_profile(
            db, pid, {"bio": "new bio", "discord_id": "should-be-ignored", "id": "should-be-ignored"}
        )
        assert updated.bio == "new bio"
        assert updated.discord_id != "should-be-ignored"


def test_update_profile_not_found_raises():
    with session_scope() as db:
        with pytest.raises(profile_service.ProfileNotFoundError):
            profile_service.update_profile(db, str(uuid.uuid4()), {"bio": "x"})


def test_search_profiles_matches_skills_case_insensitively():
    marker = uuid.uuid4().hex[:8]
    with session_scope() as db:
        profile_service.create_profile(
            db,
            {
                "discord_id": _discord_id(),
                "display_name": f"Searchable {marker}",
                "skills": [f"very-unique-skill-{marker}"],
            },
        )

    with session_scope() as db:
        results = profile_service.search_profiles(db, f"VERY-UNIQUE-SKILL-{marker}".upper())
        assert any(marker in p.display_name for p in results)
