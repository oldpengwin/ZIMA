"""
Tests for src/services/matching_service.py's caching layer (MatchScoreCache).

Covers exactly what the caching pass was for: identical results whether a
score comes from cache or is computed fresh, reuse across the two people in
a pair (the algorithm is symmetric), and correct invalidation the instant
either profile's matching-relevant fields change — a stale cache silently
returned would be worse than no cache at all.

Runs against the same real, shared, non-empty Postgres database as the rest
of tests/backend/ (seed_data.py may have already populated hundreds of
other profiles) — per the "test behavior, not syntax" doctrine, these tests
don't assume isolation. Assertions look up specific profiles/pairs by id
rather than assuming a fixed match-list length or the fixture profiles
ranking within any particular top-N; `_LARGE_LIMIT` is large enough that
the fixture's own profiles are always included in the scored set regardless
of how many other seeded profiles outscore them.
"""

import uuid

import pytest
from sqlalchemy import inspect

from src.database.models import MatchScoreCache, Profile
from src.db.session import engine, session_scope
from src.services import matching_service


@pytest.fixture(autouse=True)
def _require_schema():
    if "match_score_cache" not in inspect(engine).get_table_names():
        pytest.skip("Schema not migrated — run `alembic upgrade head` before running backend tests.")


_LARGE_LIMIT = 100_000  # large enough to include every seeded profile, not just the top-N by score


def _discord_id() -> str:
    return str(uuid.uuid4().int)[:18]


def _make_profile(db, **overrides) -> Profile:
    defaults = dict(
        id=uuid.uuid4(),
        discord_id=_discord_id(),
        discord_username="test_user",
        display_name="Test User",
        neurotype="developer",
        skills=["python"],
        offering=["backend development"],
        looking_for=["frontend developers"],
        projects=[],
        location=None,
        is_open=True,
    )
    defaults.update(overrides)
    profile = Profile(**defaults)
    db.add(profile)
    db.flush()
    return profile


class TestMatchScoreCaching:
    def test_second_call_hits_cache_and_returns_identical_scores(self):
        with session_scope() as db:
            a = _make_profile(db, display_name="Alice", neurotype="developer", offering=["python"], looking_for=["design"])
            b = _make_profile(db, display_name="Bob", neurotype="fabricant", offering=["design"], looking_for=["python"])
            a_id, b_id = a.id, b.id

        with session_scope() as db:
            first = matching_service.find_matches(db, str(a_id), limit=_LARGE_LIMIT)
        with session_scope() as db:
            second = matching_service.find_matches(db, str(a_id), limit=_LARGE_LIMIT)

        assert first == second
        first_b = next(m for m in first["matches"] if m["profile_id"] == str(b_id))
        second_b = next(m for m in second["matches"] if m["profile_id"] == str(b_id))
        assert first_b == second_b

        with session_scope() as db:
            lo, hi = sorted([str(a_id), str(b_id)])
            current_rows = (
                db.query(MatchScoreCache)
                .filter(
                    MatchScoreCache.is_current.is_(True),
                    MatchScoreCache.profile_lo_id == lo,
                    MatchScoreCache.profile_hi_id == hi,
                )
                .count()
            )
            # Exactly one row for the A<->B pair — the second call must not have
            # inserted a duplicate; it should have read the existing row.
            assert current_rows == 1

    def test_score_reused_symmetrically_for_the_other_participant(self):
        """A cache row computed while A looks at their matches must be
        readable when B looks at theirs — same pair, same score, no
        recomputation, regardless of which side queries first."""
        with session_scope() as db:
            a = _make_profile(db, display_name="Cleo", neurotype="mycelian")
            b = _make_profile(db, display_name="Dev", neurotype="cultivar")
            a_id, b_id = a.id, b.id

        with session_scope() as db:
            a_view = matching_service.find_matches(db, str(a_id), limit=_LARGE_LIMIT)
        a_score = next(m["score"]["total"] for m in a_view["matches"] if m["profile_id"] == str(b_id))

        with session_scope() as db:
            lo, hi = sorted([str(a_id), str(b_id)])
            rows_before = (
                db.query(MatchScoreCache)
                .filter(MatchScoreCache.profile_lo_id == lo, MatchScoreCache.profile_hi_id == hi)
                .count()
            )
            b_view = matching_service.find_matches(db, str(b_id), limit=_LARGE_LIMIT)
            rows_after = (
                db.query(MatchScoreCache)
                .filter(MatchScoreCache.profile_lo_id == lo, MatchScoreCache.profile_hi_id == hi)
                .count()
            )

        b_score = next(m["score"]["total"] for m in b_view["matches"] if m["profile_id"] == str(a_id))
        assert a_score == b_score
        # B's call must not have inserted a new row for the A<->B pair — it was
        # already cached from A's call and is symmetric, so it's a pure read.
        assert rows_after == rows_before == 1

    def test_editing_a_matching_relevant_field_invalidates_the_cache(self):
        with session_scope() as db:
            a = _make_profile(db, display_name="Elle", neurotype="artisan", skills=["illustration"])
            b = _make_profile(db, display_name="Finn", neurotype="chronicler", skills=["writing"])
            a_id, b_id = a.id, b.id

        with session_scope() as db:
            before = matching_service.find_matches(db, str(a_id), limit=_LARGE_LIMIT)
        before_score = next(m["score"]["total"] for m in before["matches"] if m["profile_id"] == str(b_id))

        with session_scope() as db:
            profile_b = db.get(Profile, b_id)
            profile_b.offering = ["a brand new offering that changes the skill overlap"]
            profile_a = db.get(Profile, a_id)
            profile_a.looking_for = ["a brand new offering that changes the skill overlap"]

        with session_scope() as db:
            after = matching_service.find_matches(db, str(a_id), limit=_LARGE_LIMIT)
        after_score = next(m["score"]["total"] for m in after["matches"] if m["profile_id"] == str(b_id))

        assert after_score != before_score

        with session_scope() as db:
            lo, hi = sorted([str(a_id), str(b_id)])
            # History is retained (is_current=False), not deleted, for audit/trend purposes.
            history_rows = (
                db.query(MatchScoreCache)
                .filter(
                    MatchScoreCache.is_current.is_(False),
                    MatchScoreCache.profile_lo_id == lo,
                    MatchScoreCache.profile_hi_id == hi,
                )
                .count()
            )
            current_rows = (
                db.query(MatchScoreCache)
                .filter(
                    MatchScoreCache.is_current.is_(True),
                    MatchScoreCache.profile_lo_id == lo,
                    MatchScoreCache.profile_hi_id == hi,
                )
                .count()
            )
            assert history_rows >= 1
            assert current_rows == 1  # still exactly one live row for the pair, not two

    def test_algorithm_version_bump_invalidates_even_with_unchanged_profiles(self, monkeypatch):
        with session_scope() as db:
            a = _make_profile(db, display_name="Gale", neurotype="loomkeeper")
            b = _make_profile(db, display_name="Hart", neurotype="verdant")
            a_id, b_id = a.id, b.id
        lo, hi = sorted([str(a_id), str(b_id)])

        def _current_row(db):
            return (
                db.query(MatchScoreCache)
                .filter(
                    MatchScoreCache.is_current.is_(True),
                    MatchScoreCache.profile_lo_id == lo,
                    MatchScoreCache.profile_hi_id == hi,
                )
                .one()
            )

        with session_scope() as db:
            matching_service.find_matches(db, str(a_id), limit=_LARGE_LIMIT)
            assert _current_row(db).algorithm_version == matching_service.ALGORITHM_VERSION

        monkeypatch.setattr(matching_service, "ALGORITHM_VERSION", "999-test-bump")
        with session_scope() as db:
            matching_service.find_matches(db, str(a_id), limit=_LARGE_LIMIT)
            assert _current_row(db).algorithm_version == "999-test-bump"

    def test_raises_for_user_without_neurotype(self):
        with session_scope() as db:
            a = _make_profile(db, display_name="NoQuiz", neurotype=None)
            a_id = a.id
        with session_scope() as db:
            with pytest.raises(matching_service.MatchingError):
                matching_service.find_matches(db, str(a_id))

    def test_closed_profiles_excluded_as_candidates(self):
        with session_scope() as db:
            a = _make_profile(db, display_name="Open", neurotype="seedcaster")
            closed = _make_profile(db, display_name="Closed", neurotype="fabricant", is_open=False)
            a_id, closed_id = a.id, closed.id
        with session_scope() as db:
            result = matching_service.find_matches(db, str(a_id), limit=_LARGE_LIMIT)
        assert all(m["profile_id"] != str(a_id) for m in result["matches"])
        # The closed profile must never appear as a candidate, however many
        # other (open) seeded profiles do.
        assert all(m["profile_id"] != str(closed_id) for m in result["matches"])
