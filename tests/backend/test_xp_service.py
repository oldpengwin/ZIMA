"""Tests for src/services/xp_service.py — the deterministic, server-side XP /
gamification system. Covers the pure level math in isolation and the DB-backed
award path: fixed points, idempotency (a second identical award is a no-op),
per-entity awards for repeatable events, and the level-threshold role-tier
unlock recording a RoleGrant. No Discord network is touched — award() returns
the role_keys to apply and the route layer does the (best-effort) Discord call,
so this stays a pure DB/logic test."""

import uuid

import pytest
from sqlalchemy import inspect

from src.database.models import RoleGrant, XpEvent
from src.db.session import engine, session_scope
from src.services import xp_service


@pytest.fixture(autouse=True)
def _require_schema():
    if "xp_events" not in inspect(engine).get_table_names():
        pytest.skip("Schema not migrated — run `alembic upgrade head` before running backend tests.")


def _discord_id() -> str:
    return str(uuid.uuid4().int)[:18]


# ───────────────────────────── pure level math ─────────────────────────────
class TestLevelMath:
    def test_level_for_xp_boundaries(self):
        assert xp_service.level_for_xp(0) == 1
        assert xp_service.level_for_xp(49) == 1
        assert xp_service.level_for_xp(50) == 2
        assert xp_service.level_for_xp(119) == 2
        assert xp_service.level_for_xp(120) == 3
        assert xp_service.level_for_xp(10_000) == len(xp_service.LEVEL_THRESHOLDS)

    def test_next_level_threshold(self):
        assert xp_service.next_level_threshold(0) == 50
        assert xp_service.next_level_threshold(50) == 120
        # Past the top defined threshold there is no next level.
        assert xp_service.next_level_threshold(10_000) is None

    def test_role_keys_are_cumulative(self):
        assert xp_service.role_keys_for_level(1) == []
        assert xp_service.role_keys_for_level(3) == ["tier-contributor"]
        assert xp_service.role_keys_for_level(5) == ["tier-contributor", "tier-builder"]


# ───────────────────────────── DB-backed awards ─────────────────────────────
class TestAward:
    def test_award_adds_points_and_summary(self):
        did = _discord_id()
        with session_scope() as db:
            result = xp_service.award(db, did, "onboarding_completed")
            assert result["awarded"] is True
            assert result["xp"] == 50
            assert result["level"] == 2
            assert result["next_level_at"] == 120
            assert result["xp_to_next_level"] == 70

    def test_once_per_user_event_is_idempotent(self):
        did = _discord_id()
        with session_scope() as db:
            xp_service.award(db, did, "onboarding_completed")
            again = xp_service.award(db, did, "onboarding_completed")
            assert again["awarded"] is False
            assert again["xp"] == 50  # not doubled
        with session_scope() as db:
            rows = db.query(XpEvent).filter(XpEvent.discord_id == did).all()
            assert len(rows) == 1

    def test_repeatable_event_awards_once_per_ref(self):
        did = _discord_id()
        with session_scope() as db:
            xp_service.award(db, did, "project_created", ref_id="proj-A")
            xp_service.award(db, did, "project_created", ref_id="proj-B")
            dup = xp_service.award(db, did, "project_created", ref_id="proj-A")  # same entity again
            assert dup["awarded"] is False
            assert dup["xp"] == 50  # two distinct projects * 25, third was a no-op

    def test_unknown_event_type_raises(self):
        did = _discord_id()
        with session_scope() as db:
            with pytest.raises(xp_service.XpServiceError):
                xp_service.award(db, did, "not_a_real_event")

    def test_crossing_threshold_unlocks_tier_and_records_grant(self):
        did = _discord_id()
        with session_scope() as db:
            xp_service.award(db, did, "onboarding_completed")   # 50  -> level 2
            xp_service.award(db, did, "quiz_completed")         # 80  -> level 2
            result = xp_service.award(db, did, "first_project_join")  # 120 -> level 3
            assert result["level"] == 3
            assert "tier-contributor" in result["newly_unlocked"]
        with session_scope() as db:
            grants = db.query(RoleGrant).filter(
                RoleGrant.discord_id == did, RoleGrant.role_key == "tier-contributor"
            ).all()
            assert len(grants) == 1
            assert grants[0].source == "xp"

    def test_tier_not_re_granted_on_later_awards(self):
        did = _discord_id()
        with session_scope() as db:
            xp_service.award(db, did, "onboarding_completed")
            xp_service.award(db, did, "quiz_completed")
            xp_service.award(db, did, "first_project_join")     # unlock tier-contributor
            later = xp_service.award(db, did, "project_created", ref_id="proj-1")
            assert later["newly_unlocked"] == []  # already granted, not re-emitted
        with session_scope() as db:
            grants = db.query(RoleGrant).filter(
                RoleGrant.discord_id == did, RoleGrant.role_key == "tier-contributor"
            ).all()
            assert len(grants) == 1
