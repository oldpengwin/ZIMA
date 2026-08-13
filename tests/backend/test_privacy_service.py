"""
Tests for src/services/privacy_service.py — the piece Frost specifically
asked to be able to validate: deleting one user's account must remove their
personal data without corrupting anyone else's.

Run against a REAL Postgres database (not mocks) per the doctrine's "test
behavior, not syntax" rule — a mocked-out deletion test proves nothing about
whether the cascade rules actually hold. Requires DATABASE_URL to point at a
disposable Postgres (see README for local setup); these tests create and
delete real rows.
"""

import uuid

import pytest
from sqlalchemy import inspect

from src.database.models import (
    Base,
    Connection,
    ConsentRecord,
    MatchScoreCache,
    Message,
    Profile,
    Project,
    ProjectParticipant,
    Resource,
)
from src.db.session import engine, session_scope
from src.services import privacy_service


@pytest.fixture(autouse=True)
def _require_schema():
    if "profiles" not in inspect(engine).get_table_names():
        pytest.skip("Schema not migrated — run `alembic upgrade head` before running backend tests.")


def _discord_id() -> str:
    return str(uuid.uuid4().int)[:18]


def _make_profile(db, **overrides) -> Profile:
    defaults = dict(
        id=uuid.uuid4(),
        discord_id=str(uuid.uuid4().int)[:18],
        discord_username="test_user",
        display_name="Test User",
        neurotype="developer",
        skills=["python"],
        offering=["backend development"],
        looking_for=["frontend developers"],
        is_open=True,
    )
    defaults.update(overrides)
    profile = Profile(**defaults)
    db.add(profile)
    db.flush()
    return profile


class TestDeletionDoesNotCorruptOtherUsers:
    """The core scenario: A, B, and C are seeded with realistic relationships.
    A is deleted. B and C's own data must be fully intact afterward."""

    def test_deleting_a_user_preserves_unrelated_users_data(self):
        with session_scope() as db:
            user_a = _make_profile(db, display_name="Alice", discord_id=_discord_id())
            user_b = _make_profile(db, display_name="Bob", discord_id=_discord_id())
            user_c = _make_profile(db, display_name="Carol", discord_id=_discord_id())

            # A <-> B connection; B <-> C connection (unrelated to A).
            conn_ab = Connection(id=uuid.uuid4(), from_user_id=user_a.id, to_user_id=user_b.id, status="accepted")
            conn_bc = Connection(id=uuid.uuid4(), from_user_id=user_b.id, to_user_id=user_c.id, status="accepted")
            db.add_all([conn_ab, conn_bc])

            # Project owned by A, with B and C as participants.
            project = Project(id=uuid.uuid4(), owner_id=user_a.id, title="Shared Build", status="building")
            db.add(project)
            db.flush()
            db.add_all(
                [
                    ProjectParticipant(id=uuid.uuid4(), project_id=project.id, profile_id=user_a.id, role="owner"),
                    ProjectParticipant(id=uuid.uuid4(), project_id=project.id, profile_id=user_b.id, role="contributor"),
                    ProjectParticipant(id=uuid.uuid4(), project_id=project.id, profile_id=user_c.id, role="contributor"),
                ]
            )

            # Messages A->B and B->A; a separate, unrelated B->C message. Content
            # embeds the run's own discord_id fragment so it's unique even across
            # repeated, non-transactional test runs against the same database.
            marker = user_a.discord_id[-6:]
            msg_a_to_b = Message(id=uuid.uuid4(), from_user_id=user_a.id, to_user_id=user_b.id, content=f"hey want to collab? [{marker}]")
            msg_b_to_a = Message(id=uuid.uuid4(), from_user_id=user_b.id, to_user_id=user_a.id, content=f"sure, let's do it [{marker}]")
            msg_b_to_c = Message(id=uuid.uuid4(), from_user_id=user_b.id, to_user_id=user_c.id, content=f"unrelated thread [{marker}]")
            db.add_all([msg_a_to_b, msg_b_to_a, msg_b_to_c])

            # A resource submitted by A.
            resource = Resource(id=uuid.uuid4(), title=f"A's tool [{marker}]", url="https://example.com/tool", submitted_by=user_a.id)
            db.add(resource)

            db.add(
                ConsentRecord(id=uuid.uuid4(), profile_id=user_a.id, consent_type="data_processing", granted_at=None)
            )
            db.flush()

            a_id, b_id, c_id, project_id, resource_id = user_a.id, user_b.id, user_c.id, project.id, resource.id
            conn_ab_id, conn_bc_id = conn_ab.id, conn_bc.id
            msg_a_to_b_id, msg_b_to_a_id, msg_b_to_c_id = msg_a_to_b.id, msg_b_to_a.id, msg_b_to_c.id

        # ── Act: delete A ──
        with session_scope() as db:
            report = privacy_service.delete_user(db, str(a_id), requested_by="self")

        assert report["status"] == "completed"

        with session_scope() as db:
            # A is fully gone.
            assert db.get(Profile, a_id) is None

            # B and C's own profile rows are completely untouched.
            b = db.get(Profile, b_id)
            c = db.get(Profile, c_id)
            assert b is not None and b.display_name == "Bob"
            assert c is not None and c.display_name == "Carol"

            # A<->B connection is gone (correct: meaningless with A gone).
            assert db.get(Connection, conn_ab_id) is None
            # B<->C connection is completely untouched.
            still_bc = db.get(Connection, conn_bc_id)
            assert still_bc is not None
            assert still_bc.status == "accepted"

            # The shared project survives, orphaned rather than destroyed.
            surviving_project = db.get(Project, project_id)
            assert surviving_project is not None
            assert surviving_project.owner_id is None
            assert surviving_project.owner_deleted is True
            assert surviving_project.title == "Shared Build"

            # B and C are still on the project roster; A's roster row is gone.
            remaining_participants = {
                p.profile_id for p in db.query(ProjectParticipant).filter(ProjectParticipant.project_id == project_id).all()
            }
            assert remaining_participants == {b_id, c_id}

            # Messages: A's identity is stripped but content (both directions) survives for B.
            a_to_b = db.get(Message, msg_a_to_b_id)
            b_to_a = db.get(Message, msg_b_to_a_id)
            assert a_to_b.from_user_id is None and a_to_b.from_user_deleted is True
            assert a_to_b.to_user_id == b_id and a_to_b.to_user_deleted is False
            assert b_to_a.to_user_id is None and b_to_a.to_user_deleted is True
            assert b_to_a.from_user_id == b_id

            # The unrelated B->C message is completely untouched.
            bc_msg = db.get(Message, msg_b_to_c_id)
            assert bc_msg.from_user_id == b_id and bc_msg.to_user_id == c_id
            assert bc_msg.from_user_deleted is False and bc_msg.to_user_deleted is False

            # The resource survives, orphaned.
            surviving_resource = db.get(Resource, resource_id)
            assert surviving_resource is not None
            assert surviving_resource.submitted_by is None
            assert surviving_resource.title.startswith("A's tool")

            # Consent record is retained (compliance trail) but anonymized.
            consent = db.query(ConsentRecord).filter(ConsentRecord.subject_deleted.is_(True)).order_by(
                ConsentRecord.id.desc()
            ).first()
            assert consent is not None
            assert consent.profile_id is None

    def test_audit_log_records_every_table_touched(self):
        with session_scope() as db:
            user = _make_profile(db, display_name="Solo", discord_id=_discord_id())
            user_id = user.id

        with session_scope() as db:
            report = privacy_service.delete_user(db, str(user_id), requested_by="self")

        table_names = {entry["table_name"] for entry in report["audit"]}
        # Even with zero rows in most related tables, every table in the
        # policy must appear in the audit log — an empty result is a real,
        # logged zero, not a silently skipped step.
        # quiz_responses (neurotype-quiz) and organizations (org-ownership) were
        # added to the deletion policy after this test was first written — the
        # service already handles both correctly (verified in
        # src/services/privacy_service.py); this expected set was just stale.
        assert table_names == {
            "connections",
            "project_participants",
            "role_grants",
            "quest_completions",
            "match_score_cache",
            "profile_match_stats",
            "projects",
            "organizations",
            "resources",
            "messages",
            "consent_records",
            "quiz_responses",
            "profiles",
        }

    def test_deleting_nonexistent_profile_raises(self):
        with session_scope() as db:
            with pytest.raises(privacy_service.ProfileNotFoundError):
                privacy_service.delete_user(db, str(uuid.uuid4()))

    def test_export_includes_all_related_data_and_does_not_mutate(self):
        with session_scope() as db:
            user_a = _make_profile(db, display_name="Dana", discord_id=_discord_id())
            user_b = _make_profile(db, display_name="Eli", discord_id=_discord_id())
            db.add(Connection(id=uuid.uuid4(), from_user_id=user_a.id, to_user_id=user_b.id, status="pending"))
            db.add(Message(id=uuid.uuid4(), from_user_id=user_a.id, to_user_id=user_b.id, content="hi"))
            a_id = user_a.id

        with session_scope() as db:
            export = privacy_service.export_user_data(db, str(a_id))

        assert export["profile"]["display_name"] == "Dana"
        assert len(export["connections"]) == 1
        assert len(export["messages_sent"]) == 1

        # Export must be read-only: the profile still exists afterward.
        with session_scope() as db:
            assert db.get(Profile, a_id) is not None

    def test_deletion_purges_cached_match_scores_both_directions_and_history(self):
        """A cached match score is derived from the deleted profile's own
        data (skills/neurotype/etc) — it must not survive the profile it
        was computed from, in either storage direction (profile_lo_id vs
        profile_hi_id) or generation (current vs superseded history)."""
        with session_scope() as db:
            user_a = _make_profile(db, display_name="Hana", discord_id=_discord_id())
            user_b = _make_profile(db, display_name="Ivan", discord_id=_discord_id())
            user_c = _make_profile(db, display_name="Jill", discord_id=_discord_id())
            lo, hi = sorted([str(user_a.id), str(user_b.id)])
            # A superseded (history) row for the same pair, plus the current one —
            # both must be purged, not just the live one.
            db.add(
                MatchScoreCache(
                    id=uuid.uuid4(), profile_lo_id=lo, profile_hi_id=hi, score=0.5,
                    algorithm_version="0", input_fingerprint="stale", breakdown={}, is_current=False,
                )
            )
            db.add(
                MatchScoreCache(
                    id=uuid.uuid4(), profile_lo_id=lo, profile_hi_id=hi, score=0.7,
                    algorithm_version="1", input_fingerprint="current", breakdown={}, is_current=True,
                )
            )
            # An unrelated B<->C cache row that must survive A's deletion untouched.
            lo_bc, hi_bc = sorted([str(user_b.id), str(user_c.id)])
            db.add(
                MatchScoreCache(
                    id=uuid.uuid4(), profile_lo_id=lo_bc, profile_hi_id=hi_bc, score=0.6,
                    algorithm_version="1", input_fingerprint="bc", breakdown={}, is_current=True,
                )
            )
            a_id, b_id, c_id = user_a.id, user_b.id, user_c.id

        with session_scope() as db:
            report = privacy_service.delete_user(db, str(a_id), requested_by="self")

        cache_entry = next(e for e in report["audit"] if e["table_name"] == "match_score_cache")
        assert cache_entry["rows_affected"] == 2  # both the current and the history row for A<->B

        with session_scope() as db:
            remaining = db.query(MatchScoreCache).all()
            pairs = {(str(r.profile_lo_id), str(r.profile_hi_id)) for r in remaining}
            assert (lo, hi) not in pairs
            assert (lo_bc, hi_bc) in pairs  # B<->C untouched

    def test_preview_matches_actual_deletion_counts(self):
        with session_scope() as db:
            user_a = _make_profile(db, display_name="Fay", discord_id=_discord_id())
            user_b = _make_profile(db, display_name="Gus", discord_id=_discord_id())
            db.add(Connection(id=uuid.uuid4(), from_user_id=user_a.id, to_user_id=user_b.id, status="pending"))
            a_id = user_a.id

        with session_scope() as db:
            preview = privacy_service.preview_deletion(db, str(a_id))
        assert preview["connections"] == 1

        with session_scope() as db:
            report = privacy_service.delete_user(db, str(a_id))
        connections_entry = next(e for e in report["audit"] if e["table_name"] == "connections")
        assert connections_entry["rows_affected"] == preview["connections"]
