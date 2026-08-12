"""
Wraps core.neurotype_matcher.NeurotypeMatcher (unchanged — it's the one
pre-existing module that was already correct and well-tested) around real
ORM Profile rows. No LLM involved: this is deterministic, pure-code scoring,
matching the product's stated "retrieval, not generation" philosophy.

Caching layer (added alongside MatchScoreCache in src/database/models.py):
--------------------------------------------------------------------------
Scoring a pair of profiles is pure CPU (four cheap comparisons, no I/O), so
the expensive part was never any single computation — it was doing it on
every request, for every candidate, even when neither profile involved had
changed since the last time. `find_matches` used to fetch every profile row
and recompute all N pairwise scores on every call, for every caller.

The fix is a content-addressed cache (MatchScoreCache): each pair's score
is computed once, stored under a fingerprint of the matching-relevant
fields of both profiles plus the algorithm's own version, and reused for
free until either profile edits one of those fields or the algorithm
changes — at which point the fingerprint no longer matches and it's treated
as a cache miss, not silently served stale. Because the algorithm is
symmetric (verified below), a score computed when A looks at their matches
is immediately valid when B looks at theirs, too — one cache population
serves both directions.

What's still computed live, deliberately: which candidates are matchable at
all (a cheap SQL filter, not worth caching — it changes constantly as
profiles are created/edited) and which of those the caller actually asked
to see (top-`limit`, not top-everyone). Only the expensive part — the
per-pair score itself — is cached.
"""

import hashlib
import json
import logging
import uuid
from typing import Dict, List, Optional

from sqlalchemy import or_, tuple_
from sqlalchemy.orm import Session

from src.core.neurotype_matcher import Neurotype, NeurotypeMatcher
from src.core.neurotype_matcher import Profile as MatchProfile
from src.database.models import MatchScoreCache, Profile

logger = logging.getLogger(__name__)

# Bump this whenever calculate_match_score's weights or sub-score logic
# change in core/neurotype_matcher.py. Every cached row is stamped with the
# version that produced it; a version mismatch invalidates the row exactly
# like a fingerprint mismatch does, so a scoring-logic change can't ever
# silently serve pre-change scores.
ALGORITHM_VERSION = "1"


class MatchingError(Exception):
    pass


def _to_match_profile(profile: Profile) -> Optional[MatchProfile]:
    """Converts an ORM Profile to the matcher's dataclass. Returns None for
    profiles that haven't taken the archetype quiz yet — they're real
    accounts but aren't matchable on neurotype until they have one."""
    if not profile.neurotype:
        return None
    try:
        neurotype = Neurotype(profile.neurotype)
    except ValueError:
        logger.warning("Profile %s has unrecognized neurotype %r — excluded from matching", profile.id, profile.neurotype)
        return None
    return MatchProfile(
        id=str(profile.id),
        discord_id=profile.discord_id,
        display_name=profile.display_name,
        neurotype=neurotype,
        skills=profile.skills or [],
        offering=profile.offering or [],
        looking_for=profile.looking_for or [],
        projects=profile.projects or [],
        location=profile.location,
        is_open=profile.is_open,
    )


def _fingerprint_fields(profile: Profile) -> dict:
    """Every field calculate_match_score actually reads. Anything not in
    this dict (bio, tagline, badges, ...) can change without invalidating
    a cached score — deliberately, since those fields don't affect it."""
    return {
        "neurotype": profile.neurotype,
        "skills": sorted(profile.skills or []),
        "offering": sorted(profile.offering or []),
        "looking_for": sorted(profile.looking_for or []),
        "projects": sorted(profile.projects or []),
        "location": (profile.location or "").strip().lower(),
        "is_open": bool(profile.is_open),
    }


def _pair_fingerprint(a: Profile, b: Profile) -> str:
    """Must be canonicalized by profile id, not by call order: find_matches
    is called with one profile as "target" and the other as "candidate",
    and which one is which flips depending on who's asking (A looking at
    their matches vs B looking at theirs, for the exact same pair). If the
    fingerprint were keyed by target/candidate role instead of by id order,
    the identical unchanged pair would hash differently depending on who
    called, so B's read of A's already-cached, still-valid row would look
    like a mismatch and force a spurious recompute+rewrite on every single
    lookup from the "other side" of a pair — silently defeating the
    cross-user cache reuse this module exists to provide."""
    fields_a, fields_b = _fingerprint_fields(a), _fingerprint_fields(b)
    lo, hi = (fields_a, fields_b) if str(a.id) < str(b.id) else (fields_b, fields_a)
    payload = json.dumps({"lo": lo, "hi": hi}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_pair(id_a: str, id_b: str) -> tuple:
    """The scoring algorithm is symmetric — every sub-score in
    core/neurotype_matcher.py.calculate_match_score is built from set
    intersection/union or a symmetric compatibility-matrix lookup, with no
    directional term — so (A, B) and (B, A) are the same computation. This
    orders any pair the same way regardless of call direction, so it's
    stored (and found) as one row, not two."""
    a, b = str(id_a), str(id_b)
    return (a, b) if a < b else (b, a)


def _load_current_cache(db: Session, user_id: str, candidate_ids: List[str]) -> Dict[str, MatchScoreCache]:
    """One query for every candidate's current cache row (if any), keyed by
    candidate id. Avoids N+1 lookups — this is the batch equivalent of the
    per-pair query the naive version would need."""
    if not candidate_ids:
        return {}
    rows = (
        db.query(MatchScoreCache)
        .filter(
            MatchScoreCache.is_current.is_(True),
            or_(
                (MatchScoreCache.profile_lo_id == user_id) & (MatchScoreCache.profile_hi_id.in_(candidate_ids)),
                (MatchScoreCache.profile_hi_id == user_id) & (MatchScoreCache.profile_lo_id.in_(candidate_ids)),
            ),
        )
        .all()
    )
    result = {}
    for row in rows:
        other_id = str(row.profile_hi_id) if str(row.profile_lo_id) == str(user_id) else str(row.profile_lo_id)
        result[other_id] = row
    return result


def find_matches(db: Session, user_id: str, limit: int = 5) -> Dict:
    """Find top matches for a user. Raises MatchingError with a clear reason
    if the user themself hasn't completed the archetype quiz (can't score
    neurotype compatibility for someone with no neurotype) or if there are
    no other matchable profiles yet.

    Pushes the "matchable at all" filter (neurotype IS NOT NULL) down to
    SQL instead of fetching every profile row and filtering in Python —
    profiles that can never be matched (no archetype yet) were previously
    fetched, deserialized, and iterated over on every single call for
    nothing."""
    target_row = db.get(Profile, uuid.UUID(str(user_id)))
    if target_row is None or not target_row.neurotype:
        raise MatchingError(
            "This user hasn't completed the archetype quiz yet, so no neurotype-based matches "
            "can be calculated. Complete onboarding first."
        )

    # Push BOTH "matchable" filters down to SQL: has an archetype, and is open
    # to matching. Previously is_open was filtered in Python after loading every
    # candidate row — O(N) memory on large userbases for rows we then discard.
    candidate_rows = (
        db.query(Profile)
        .filter(
            Profile.neurotype.isnot(None),
            Profile.is_open.is_(True),
            Profile.id != target_row.id,
        )
        .all()
    )
    if not candidate_rows:
        return {"user_id": str(user_id), "matches": [], "reason": "Not enough matchable profiles yet."}

    match_profiles: List[MatchProfile] = [p for p in (_to_match_profile(pr) for pr in [target_row] + candidate_rows) if p]
    matcher = NeurotypeMatcher(match_profiles)

    candidates_by_id = {str(p.id): p for p in candidate_rows}
    cache_by_candidate = _load_current_cache(db, str(target_row.id), list(candidates_by_id.keys()))

    scored: List[Dict] = []
    to_write: List[MatchScoreCache] = []
    stale_pair_keys: List[tuple] = []
    hits = 0

    for candidate_id, candidate_row in candidates_by_id.items():
        # is_open is already enforced in the SQL query above.
        candidate_mp = matcher._profile_by_id.get(candidate_id)
        if candidate_mp is None:
            continue  # no/unrecognized neurotype — not matchable, see _to_match_profile

        fingerprint = _pair_fingerprint(target_row, candidate_row)
        cached = cache_by_candidate.get(candidate_id)

        if cached is not None and cached.input_fingerprint == fingerprint and cached.algorithm_version == ALGORITHM_VERSION:
            hits += 1
            scored.append({"profile": candidate_mp, "score": {"total": cached.score, "breakdown": cached.breakdown or {}}})
            continue

        # Cache miss (never computed, or either profile / the algorithm changed since).
        user_mp = matcher._profile_by_id[str(target_row.id)]
        result = matcher.calculate_match_score(user_mp, candidate_mp)
        scored.append({"profile": candidate_mp, "score": result})

        lo, hi = _canonical_pair(target_row.id, candidate_row.id)
        if cached is not None:
            stale_pair_keys.append((lo, hi))
        to_write.append(
            MatchScoreCache(
                id=uuid.uuid4(),
                profile_lo_id=lo,
                profile_hi_id=hi,
                score=result["total"],
                algorithm_version=ALGORITHM_VERSION,
                input_fingerprint=fingerprint,
                breakdown=result["breakdown"],
                is_current=True,
            )
        )

    if stale_pair_keys:
        # One bulk UPDATE for every stale pair, not one round trip per pair — this loop used
        # to issue an individual UPDATE per candidate, which meant "a profile edits one field"
        # was O(candidates) DB round trips just to invalidate, on top of the recompute cost.
        db.query(MatchScoreCache).filter(
            MatchScoreCache.is_current.is_(True),
            tuple_(MatchScoreCache.profile_lo_id, MatchScoreCache.profile_hi_id).in_(stale_pair_keys),
        ).update({"is_current": False}, synchronize_session=False)
    if to_write:
        db.add_all(to_write)
    if stale_pair_keys or to_write:
        db.commit()

    logger.debug(
        "find_matches user=%s: %d cache hits, %d computed live (of %d candidates)",
        user_id, hits, len(to_write), len(scored),
    )

    scored.sort(key=lambda x: x["score"]["total"], reverse=True)
    top = scored[:limit]

    return {
        "user_id": str(user_id),
        "matches": [{"profile_id": m["profile"].id, "score": m["score"]} for m in top],
    }
