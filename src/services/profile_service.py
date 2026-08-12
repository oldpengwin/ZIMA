"""
Profile CRUD service (SQLAlchemy-backed).

Replaces the old core/profile_manager.py raw-psycopg2 implementation.
Session-scoped, ORM-based, and shares one connection pool (src/db/session.py)
with every other service instead of opening its own pool per manager
instance.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import ConsentRecord, NeurotypeEnum, Profile

logger = logging.getLogger(__name__)

UPDATABLE_FIELDS = {
    "display_name",
    "location",
    "skills",
    "bio",
    "links",
    "neurotype",
    "offering",
    "looking_for",
    "projects",
    "is_open",
    "tagline",
    "vision_2036",
    "mission",
}


# Input-size limits — cheap, deterministic caps so free-text/array fields can't
# be used to bloat the DB or push unbounded payloads through the API.
MAX_ARRAY_ITEMS = 50
MAX_ARRAY_ITEM_LEN = 200
MAX_TEXT_LEN = 5000
MAX_SEARCH_LEN = 200

_ARRAY_FIELDS = {"skills", "links", "projects", "offering", "looking_for", "badges", "wall_posts"}
_TEXT_FIELDS = {"bio", "vision_2036", "mission"}


def _escape_like(value: str) -> str:
    """Escape LIKE/ILIKE wildcards so user-supplied `%`/`_` are matched
    literally (prevents wildcard abuse / needlessly expensive scans)."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _sanitize_array(value) -> list:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        s = str(item).strip()[:MAX_ARRAY_ITEM_LEN]
        if s:
            out.append(s)
        if len(out) >= MAX_ARRAY_ITEMS:
            break
    return out


def _sanitize_field(field: str, value):
    """Cap/normalize a single field value by name. Arrays are trimmed and
    length-capped; long free-text is truncated. Other fields pass through."""
    if field in _ARRAY_FIELDS:
        return _sanitize_array(value)
    if field in _TEXT_FIELDS and isinstance(value, str):
        return value[:MAX_TEXT_LEN]
    return value


class ProfileServiceError(Exception):
    pass


class ProfileNotFoundError(ProfileServiceError):
    pass


class DuplicateProfileError(ProfileServiceError):
    pass


class InvalidProfileDataError(ProfileServiceError):
    pass


def _validate_neurotype(value: Optional[str]) -> None:
    if value is None:
        return
    try:
        NeurotypeEnum(value)
    except ValueError:
        valid = ", ".join(n.value for n in NeurotypeEnum)
        raise InvalidProfileDataError(f"Invalid neurotype '{value}'. Must be one of: {valid}")


def create_profile(db: Session, data: Dict[str, Any]) -> Profile:
    """Create a profile. Used by both the Discord bot's onboarding upsert
    (via the API, going forward — see AGENT note in routes.py) and by
    direct signup. `discord_id` and `display_name` are required; everything
    else is optional so a bare onboarding record can be created before the
    archetype quiz or full profile fill-out happens."""

    for field in ("discord_id", "display_name"):
        if not data.get(field):
            raise InvalidProfileDataError(f"Missing required field: {field}")

    _validate_neurotype(data.get("neurotype"))

    # Cap/normalize arrays and long text before they hit the DB.
    for _field in _ARRAY_FIELDS | _TEXT_FIELDS:
        if _field in data:
            data[_field] = _sanitize_field(_field, data[_field])

    profile = Profile(
        id=uuid.uuid4(),
        discord_id=data["discord_id"],
        discord_username=data.get("discord_username", data["discord_id"]),
        display_name=data["display_name"],
        location=data.get("location"),
        skills=data.get("skills", []),
        bio=data.get("bio"),
        links=data.get("links", []),
        neurotype=data.get("neurotype"),
        offering=data.get("offering", []),
        looking_for=data.get("looking_for", []),
        projects=data.get("projects", []),
        is_open=data.get("is_open", True),
        tagline=data.get("tagline"),
        vision_2036=data.get("vision_2036"),
        mission=data.get("mission"),
    )
    db.add(profile)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateProfileError(f"A profile for discord_id={data['discord_id']} already exists") from e

    # Record consent at creation time — every profile must have a consent trail.
    if data.get("consented", True):
        db.add(
            ConsentRecord(
                id=uuid.uuid4(),
                profile_id=profile.id,
                consent_type="data_processing",
                granted_at=datetime.now(timezone.utc),
                source=data.get("consent_source", "api"),
            )
        )
        profile.consented_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(profile)
    logger.info("Created profile %s for discord_id=%s", profile.id, profile.discord_id)
    return profile


_ONBOARDING_UPDATE_FIELDS = {"display_name", "location", "skills", "bio", "links", "discord_username"}


def upsert_by_discord_id(db: Session, data: Dict[str, Any], mark_onboarded: bool = False):
    """Create-or-update a profile keyed by discord_id — the Discord bot's
    onboarding path, now going through the API instead of a direct Supabase
    service-key write. Returns (profile, created). Reuses create_profile (so
    validation, sanitization and the consent record all still happen) and, on
    an existing profile, applies only the onboarding-writable fields."""
    discord_id = data.get("discord_id")
    if not discord_id:
        raise InvalidProfileDataError("Missing required field: discord_id")

    profile = get_profile_by_discord_id(db, discord_id)
    if profile is None:
        profile = create_profile(db, data)
        created = True
    else:
        for field, value in data.items():
            if field in _ONBOARDING_UPDATE_FIELDS and value is not None:
                setattr(profile, field, _sanitize_field(field, value))
        created = False

    if mark_onboarded:
        profile.onboarding_completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(profile)
    logger.info("Upsert profile for discord_id=%s (created=%s)", discord_id, created)
    return profile, created


def get_profile_by_id(db: Session, profile_id: str) -> Optional[Profile]:
    try:
        pid = uuid.UUID(str(profile_id))
    except ValueError:
        return None
    return db.get(Profile, pid)


def get_profile_by_discord_id(db: Session, discord_id: str) -> Optional[Profile]:
    return db.query(Profile).filter(Profile.discord_id == discord_id).one_or_none()


def update_profile(db: Session, profile_id: str, updates: Dict[str, Any]) -> Profile:
    profile = get_profile_by_id(db, profile_id)
    if not profile:
        raise ProfileNotFoundError(f"Profile {profile_id} not found")

    if "neurotype" in updates:
        _validate_neurotype(updates["neurotype"])

    applied = {}
    for field, value in updates.items():
        if field not in UPDATABLE_FIELDS:
            continue
        value = _sanitize_field(field, value)
        setattr(profile, field, value)
        applied[field] = value

    if not applied:
        return profile

    db.commit()
    db.refresh(profile)
    logger.info("Updated profile %s: fields=%s", profile_id, list(applied.keys()))
    return profile


def get_all_profiles(db: Session, limit: int = 20, offset: int = 0, only_open: bool = False) -> List[Profile]:
    q = db.query(Profile).order_by(Profile.created_at.desc())
    if only_open:
        q = q.filter(Profile.is_open.is_(True))
    return q.offset(offset).limit(limit).all()


def search_profiles(db: Session, query: str, limit: int = 20, offset: int = 0) -> List[Profile]:
    """Deterministic ILIKE search across name/location/skills/projects — no
    LLM involved, matching the product's "pure code" search philosophy.
    Vector/semantic search is a documented next step once pgvector
    embeddings are populated (see IMPLEMENTATION_PLAN.md phase 3)."""
    q = (query or "").strip()[:MAX_SEARCH_LEN]
    if not q:
        return []
    # Escape LIKE wildcards so a literal `%`/`_` in the query stays literal.
    term = f"%{_escape_like(q)}%"
    skill_match = text(
        "EXISTS (SELECT 1 FROM unnest(profiles.skills) s WHERE s ILIKE :term ESCAPE '\\')"
    ).bindparams(term=term)
    project_match = text(
        "EXISTS (SELECT 1 FROM unnest(profiles.projects) p WHERE p ILIKE :term ESCAPE '\\')"
    ).bindparams(term=term)
    return (
        db.query(Profile)
        .filter(
            or_(
                Profile.display_name.ilike(term, escape="\\"),
                Profile.location.ilike(term, escape="\\"),
                skill_match,
                project_match,
            )
        )
        .order_by(Profile.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
