"""
Precomputed per-profile aggregate stats (ProfileMatchStats) — the
AcousticBrainz "highlevel" (cheap, derived-classification) counterpart to
MatchScoreCache's "lowlevel" (raw computed feature) data. See the docstring
above ProfileMatchStats in src/database/models.py for the storage design.

This is the concrete answer to "what's visible vs what's needed, live vs
cached" for profile-page-style aggregate numbers (connection count, project
counts, average/top match): a profile page needs these numbers on every
view, but they don't need to be *correct as of this millisecond* — a
person's connection count being a few minutes stale is invisible to them,
whereas making every profile view run 4+ COUNT/AVG queries plus the full
match-scoring pass just to render a number nobody's actively watching in
real time is pure waste at scale. So: computed here, on demand or on a
schedule, read as a single indexed row everywhere else.

Deliberately NOT covered by this cache (kept live, computed inline where
they're used): profiles.updated_at-driven data (recency needs to be real),
connection request status (accept/reject must be immediately visible to
both parties, not eventually-consistent), and the match list itself (see
matching_service.py — that has its own finer-grained, per-pair cache with
correctness-by-fingerprint rather than a coarse aggregate)."""

import logging
import uuid
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.database.models import Connection, MatchScoreCache, Profile, ProfileMatchStats, Project, ProjectParticipant

logger = logging.getLogger(__name__)


def recompute_profile_stats(db: Session, profile_id: str) -> ProfileMatchStats:
    """Recomputes and upserts the stats row for one profile. Four cheap
    aggregate queries, run once, instead of on every read of this profile's
    stats. Call this after an action that changes one of the underlying
    counts (a connection accepted, a project joined) rather than never —
    the tradeoff this module makes is "recompute on write, read for free,"
    not "never recompute.\""""
    pid = uuid.UUID(str(profile_id))
    if not db.get(Profile, pid):
        raise ValueError(f"Profile {profile_id} not found")

    total_connections = (
        db.query(Connection)
        .filter(or_(Connection.from_user_id == pid, Connection.to_user_id == pid), Connection.status == "accepted")
        .count()
    )
    total_projects_owned = db.query(Project).filter(Project.owner_id == pid).count()
    total_projects_joined = db.query(ProjectParticipant).filter(ProjectParticipant.profile_id == pid).count()

    current_scores = (
        db.query(MatchScoreCache)
        .filter(
            MatchScoreCache.is_current.is_(True),
            or_(MatchScoreCache.profile_lo_id == pid, MatchScoreCache.profile_hi_id == pid),
        )
        .all()
    )
    cached_match_count = len(current_scores)
    avg_match_score: Optional[float] = None
    top_match_profile_id = None
    if current_scores:
        avg_match_score = sum(r.score for r in current_scores) / len(current_scores)
        best = max(current_scores, key=lambda r: r.score)
        top_match_profile_id = best.profile_hi_id if str(best.profile_lo_id) == str(pid) else best.profile_lo_id

    stats = db.get(ProfileMatchStats, pid)
    if stats is None:
        stats = ProfileMatchStats(profile_id=pid)
        db.add(stats)

    stats.total_connections = total_connections
    stats.total_projects_owned = total_projects_owned
    stats.total_projects_joined = total_projects_joined
    stats.cached_match_count = cached_match_count
    stats.avg_match_score = avg_match_score
    stats.top_match_profile_id = top_match_profile_id

    db.commit()
    db.refresh(stats)
    return stats


def get_or_compute_profile_stats(db: Session, profile_id: str) -> ProfileMatchStats:
    """Read path: return the precomputed row if one exists (the common
    case — O(1) primary-key read), only falling back to a live recompute
    the first time a profile is ever looked up (no row yet). This is the
    "cached read, lazy first-write" pattern — it never blocks a read on a
    background job existing, but it also never recomputes on a read once a
    row is there."""
    pid = uuid.UUID(str(profile_id))
    stats = db.get(ProfileMatchStats, pid)
    if stats is not None:
        return stats
    logger.info("No cached stats yet for profile %s — computing once and caching.", profile_id)
    return recompute_profile_stats(db, profile_id)
