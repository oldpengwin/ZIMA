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
    term = f"%{query}%"
    skill_match = text("EXISTS (SELECT 1 FROM unnest(profiles.skills) s WHERE s ILIKE :term)").bindparams(term=term)
    project_match = text("EXISTS (SELECT 1 FROM unnest(profiles.projects) p WHERE p ILIKE :term)").bindparams(term=term)
    return (
        db.query(Profile)
        .filter(
            or_(
                Profile.display_name.ilike(term),
                Profile.location.ilike(term),
                skill_match,
                project_match,
            )
        )
        .order_by(Profile.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
