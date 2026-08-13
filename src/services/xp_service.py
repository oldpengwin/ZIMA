"""
Deterministic, server-side XP / gamification for the ZIMA Discord community.

Design (follows the platform's "pure code, no AI; server-side truth only"
rule — the same one quiz_service.py's scoring follows):
  - XP is awarded for a small, fixed set of real actions, each worth a fixed
    number of points. No dynamic/AI scoring and no client-submitted totals: the
    client can never tell the server how much XP it has.
  - `xp_events` is an append-only ledger; total XP and level are DERIVED by
    summing it, never stored mutably on the profile. That makes awards
    idempotent and the whole history auditable.
  - Crossing a level threshold unlocks a Discord role tier. The unlock is
    recorded as a RoleGrant (source="xp") via role_service — the exact table
    the bot already uses — and the actual Discord role is applied by the caller
    (routes) via core/discord_client, best-effort and logged. No silent
    failure: an unlock with no configured role id is logged, not swallowed.

Idempotency: once-per-user events use ref_id="" so the unique
(discord_id, event_type, ref_id) constraint makes a second award a no-op;
repeatable events pass the triggering entity id as ref_id.
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from src.database.models import RoleGrant, XpEvent
from src.services import role_service

logger = logging.getLogger(__name__)


class XpServiceError(Exception):
    """Raised on an invalid award request (unknown event type, missing id)."""


# Fixed point values. Kept small and boring on purpose — this is a real reward
# loop for onboarding/first-contribution, not an economy (see module docstring).
AWARD_POINTS: Dict[str, int] = {
    "onboarding_completed": 50,
    "quiz_completed": 30,
    "first_project_join": 40,
    "project_created": 25,
}

# Events that can legitimately happen more than once per user. They MUST pass a
# ref_id (the triggering entity's id) so each distinct entity awards exactly
# once. Everything else is once-per-user (ref_id forced to "").
REPEATABLE_EVENTS = {"project_created"}

# Cumulative XP required to REACH each level. Index i => level (i + 1).
LEVEL_THRESHOLDS: List[int] = [0, 50, 120, 250, 450, 700]

# Level -> role_key granted the first time the user reaches that level. The
# role_key maps to a Discord role id in core/config.py (xp_tier_role_ids).
TIER_ROLES: Dict[int, str] = {
    3: "tier-contributor",
    5: "tier-builder",
}


# ───────────────────── Pure helpers (no DB — unit-testable) ─────────────────────
def level_for_xp(xp: int) -> int:
    """Highest level whose cumulative threshold has been reached. Level 1 at 0 xp."""
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            level = i + 1
        else:
            break
    return level


def next_level_threshold(xp: int) -> Optional[int]:
    """Cumulative XP needed for the next level, or None if already at the top."""
    for threshold in LEVEL_THRESHOLDS:
        if xp < threshold:
            return threshold
    return None


def role_keys_for_level(level: int) -> List[str]:
    """Every tier role_key a user at `level` is entitled to (cumulative)."""
    return [role_key for req, role_key in sorted(TIER_ROLES.items()) if level >= req]


def _normalize_ref(event_type: str, ref_id: str) -> str:
    return ref_id if event_type in REPEATABLE_EVENTS else ""


# ───────────────────────────── DB operations ─────────────────────────────
def _total_xp(db: Session, discord_id: str) -> int:
    total = (
        db.query(sa_func.coalesce(sa_func.sum(XpEvent.points), 0))
        .filter(XpEvent.discord_id == discord_id)
        .scalar()
    )
    return int(total or 0)


def get_summary(db: Session, discord_id: str) -> Dict:
    """Current XP standing for a Discord user: total, level, progress to next
    level, unlocked tiers, and the event history (newest first)."""
    total = _total_xp(db, discord_id)
    level = level_for_xp(total)
    nxt = next_level_threshold(total)
    events = (
        db.query(XpEvent)
        .filter(XpEvent.discord_id == discord_id)
        .order_by(XpEvent.created_at.desc())
        .all()
    )
    return {
        "discord_id": discord_id,
        "xp": total,
        "level": level,
        "next_level_at": nxt,
        "xp_to_next_level": (nxt - total) if nxt is not None else 0,
        "unlocked_tiers": role_keys_for_level(level),
        "events": [e.to_dict() for e in events],
    }


def award(db: Session, discord_id: str, event_type: str, ref_id: str = "") -> Dict:
    """Idempotently award XP for an event.

    Records the XpEvent and any newly-unlocked tier RoleGrant, then returns a
    summary dict with two extra keys the caller acts on:
      - `awarded`        : False if this event was already on the ledger (no-op)
      - `newly_unlocked` : role_keys the caller should apply on Discord now

    This function never touches Discord itself — applying the role is the
    caller's async best-effort job (routes._award_xp_best_effort), so the
    service stays pure DB logic and unit-testable without a network.
    """
    if not discord_id:
        raise XpServiceError("discord_id is required to award XP")
    if event_type not in AWARD_POINTS:
        raise XpServiceError(f"Unknown XP event type: {event_type!r}")
    ref = _normalize_ref(event_type, ref_id)

    existing = (
        db.query(XpEvent)
        .filter(
            XpEvent.discord_id == discord_id,
            XpEvent.event_type == event_type,
            XpEvent.ref_id == ref,
        )
        .one_or_none()
    )
    if existing is not None:
        summary = get_summary(db, discord_id)
        summary["awarded"] = False
        summary["newly_unlocked"] = []
        return summary

    points = AWARD_POINTS[event_type]
    db.add(XpEvent(discord_id=discord_id, event_type=event_type, ref_id=ref, points=points))
    db.flush()

    total = _total_xp(db, discord_id)
    level = level_for_xp(total)

    already_granted = {
        g.role_key for g in db.query(RoleGrant).filter(RoleGrant.discord_id == discord_id).all()
    }
    newly_unlocked: List[str] = []
    for role_key in role_keys_for_level(level):
        if role_key not in already_granted:
            role_service.record_grant(
                db, discord_id, role_key, source="xp",
                metadata={"unlocked_at_xp": total, "level": level},
            )
            newly_unlocked.append(role_key)

    db.commit()

    if newly_unlocked:
        logger.info(
            "XP: %s reached level %s (%s xp) via %s; unlocked tiers %s",
            discord_id, level, total, event_type, newly_unlocked,
        )

    summary = get_summary(db, discord_id)
    summary["awarded"] = True
    summary["awarded_event"] = {"event_type": event_type, "ref_id": ref, "points": points}
    summary["newly_unlocked"] = newly_unlocked
    return summary
