"""
Neurotype quiz service — orchestrates the pure engine with persistence.

Flow: score the (cleaned) answers against the profile's skills, store an
append-only QuizResponse for audit/re-scoring, and update the profile's two
neurotype badges. `neurotype` (the back-compat alias) is kept = identified,
falling back to assessed.

All scoring/cleaning lives in src.quiz.engine (deterministic, no LLM); this
layer only touches the DB and enforces the small set of service-level rules.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from src.core.neurotypes import is_valid_type
from src.database.models import Profile, QuizResponse
from src.quiz import engine
from src.services import network_service, profile_service

logger = logging.getLogger(__name__)

_VALID_SOURCES = {"web", "discord"}


class QuizServiceError(Exception):
    pass


def get_public_quiz(version: str = "v1") -> dict:
    """The weight-free question bank for a client to render."""
    try:
        return engine.public_bank(version)
    except engine.QuizError as e:
        raise QuizServiceError(str(e)) from e


def submit_quiz(
    db: Session,
    profile_id: str,
    answers: Any,
    identified: Optional[str] = None,
    skills_override: Optional[List[str]] = None,
    source: str = "web",
    version: str = "v1",
) -> dict:
    """Score, persist, and update the profile. Returns the ranked result plus
    the stored response. Raises QuizServiceError on bad input (profile missing,
    unknown identified type, bad source/version)."""
    if source not in _VALID_SOURCES:
        raise QuizServiceError(f"Invalid source {source!r}; expected one of {sorted(_VALID_SOURCES)}")
    if identified is not None and not is_valid_type(identified):
        raise QuizServiceError(f"Invalid identified neurotype: {identified!r}")

    profile = profile_service.get_profile_by_id(db, profile_id)
    if not profile:
        raise QuizServiceError(f"Profile {profile_id} not found")

    skills = skills_override if skills_override is not None else (profile.skills or [])

    try:
        # engine.score cleans the answers internally; we also keep the cleaned
        # map to store exactly what counted (never the raw wire payload).
        result = engine.score(answers, skills, version)
        cleaned = engine.clean_answers(answers, version)
    except engine.QuizError as e:
        raise QuizServiceError(str(e)) from e

    assessed = result["top"]
    scores = {row["id"]: row["score"] for row in result["ranked"]}

    response = QuizResponse(
        id=uuid.uuid4(),
        profile_id=profile.id,
        quiz_version=version,
        answers=cleaned,
        scores=scores,
        assessed_neurotype=assessed,
        identified_neurotype=identified,
        source=source,
    )
    db.add(response)

    profile.assessed_neurotype = assessed
    if identified is not None:
        profile.identified_neurotype = identified
    # Alias for existing readers/graph: prefer the person's chosen identity.
    profile.neurotype = profile.identified_neurotype or profile.assessed_neurotype

    db.commit()
    db.refresh(response)

    # The archetype network aggregate just changed — drop its cache so the next
    # read recomputes (rather than churning on every read).
    network_service.invalidate()

    logger.info(
        "Quiz submit: profile=%s assessed=%s identified=%s answered=%d source=%s",
        profile.id, assessed, identified, result["answered"], source,
    )
    return {"result": result, "quiz_response": response.to_dict(), "profile_id": str(profile.id)}


def set_identified_neurotype(db: Session, profile_id: str, identified: str) -> Profile:
    """Set only the self-identified badge (e.g. the user picks after seeing
    their assessed result). Does not re-run scoring."""
    if not is_valid_type(identified):
        raise QuizServiceError(f"Invalid identified neurotype: {identified!r}")
    profile = profile_service.get_profile_by_id(db, profile_id)
    if not profile:
        raise QuizServiceError(f"Profile {profile_id} not found")
    profile.identified_neurotype = identified
    profile.neurotype = identified
    db.commit()
    db.refresh(profile)
    network_service.invalidate()
    logger.info("Set identified neurotype for profile=%s -> %s", profile.id, identified)
    return profile
