"""Tests for src/services/stats_service.py — the precomputed-read half of
the caching pass (see its module docstring). Verifies the numbers are
actually correct (not just "a number came back") and that a second read
doesn't recompute (same row, not silently regenerated on every call)."""

import uuid

import pytest
from sqlalchemy import inspect

from src.database.models import Connection, Profile, Project, ProjectParticipant, ProfileMatchStats
from src.db.session import engine, session_scope
from src.services import stats_service


@pytest.fixture(autouse=True)
def _require_schema():
    if "profile_match_stats" not in inspect(engine).get_table_names():
        pytest.skip("Schema not migrated — run `alembic upgrade head` before running backend tests.")


def _discord_id() -> str:
    return str(uuid.uuid4().int)[:18]


def _make_profile(db, **overrides) -> Profile:
    defaults = dict(
        id=uuid.uuid4(), discord_id=_discord_id(), discord_username="x", display_name="Stats Test",
        skills=[], offering=[], looking_for=[], projects=[], is_open=True,
    )
    defaults.update(overrides)
    p = Profile(**defaults)
    db.add(p)
    db.flush()
    return p


class TestProfileStats:
    def test_computes_accurate_connection_and_project_counts(self):
        with session_scope() as db:
            a = _make_profile(db, display_name="Kai")
            b = _make_profile(db, display_name="Lena")
            c = _make_profile(db, display_name="Milo")
            db.add(Connection(id=uuid.uuid4(), from_user_id=a.id, to_user_id=b.id, status="accepted"))
            db.add(Connection(id=uuid.uuid4(), from_user_id=a.id, to_user_id=c.id, status="pending"))  # not accepted — excluded
            project = Project(id=uuid.uuid4(), owner_id=a.id, title="Kai's Build", status="idea")
            db.add(project)
            db.flush()
            db.add(ProjectParticipant(id=uuid.uuid4(), project_id=project.id, profile_id=a.id, role="owner"))
            db.add(ProjectParticipant(id=uuid.uuid4(), project_id=project.id, profile_id=b.id, role="contributor"))
            a_id = a.id

        with session_scope() as db:
            stats = stats_service.recompute_profile_stats(db, str(a_id))
            total_connections = stats.total_connections
            total_projects_owned = stats.total_projects_owned
            total_projects_joined = stats.total_projects_joined

        assert total_connections == 1  # only the accepted one counts
        assert total_projects_owned == 1
        assert total_projects_joined == 1  # a is also a participant on their own project

    def test_get_or_compute_caches_first_read_and_reuses_it(self):
        with session_scope() as db:
            a = _make_profile(db, display_name="Nia")
            a_id = a.id

        with session_scope() as db:
            assert db.get(ProfileMatchStats, a_id) is None  # nothing cached yet

        with session_scope() as db:
            first = stats_service.get_or_compute_profile_stats(db, str(a_id))
            first_computed_at = first.computed_at

        with session_scope() as db:
            row = db.get(ProfileMatchStats, a_id)
            assert row is not None  # the first read persisted a row

        with session_scope() as db:
            second = stats_service.get_or_compute_profile_stats(db, str(a_id))
            # Reading again must not silently recompute — same timestamp, same row.
            assert second.computed_at == first_computed_at

    def test_recompute_raises_for_missing_profile(self):
        with session_scope() as db:
            with pytest.raises(ValueError):
                stats_service.recompute_profile_stats(db, str(uuid.uuid4()))
