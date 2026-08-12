"""
Data export and account deletion.

This is the piece the client's transcripts specifically call for: "LinkedIn-
style" full data export, and immediate deletion on consent withdrawal with
no retention period. It is also the piece Frost specifically asked to be
able to test — that deleting one user's data never corrupts anyone else's.

Design (see the docstring at the top of database/models.py for the
per-table reasoning): deleting a profile is not one DELETE statement. It is
a deliberate, table-by-table policy:

  HARD DELETE (the row IS the deleted user's data, or IS the relationship
  and has no meaning once one side is gone):
    - profiles                 (the account itself)
    - connections               (a request only makes sense between two live users)
    - project_participants      (a roster entry for a person who's gone)
    - role_grants, quest_completions (Discord-specific, tied 1:1 to the person)
    - match_score_cache         (every cached/historical score computed FOR or
                                  AGAINST this profile — a compatibility score
                                  derived from a now-gone profile's data has no
                                  independent meaning and is itself profiling
                                  data about the deleted person; ALL rows for
                                  the pair are purged, current and history
                                  alike, not just the current one)

  NULL OUT THE FK, KEEP THE ROW (the row has independent value to other
  people or the community and must survive):
    - projects.owner_id         -> NULL, owner_deleted=True   (project keeps existing)
    - resources.submitted_by    -> NULL                        (resource keeps existing)
    - messages.from_user_id/to_user_id -> NULL, *_deleted=True (thread keeps existing for the other party)

  NEVER TOUCHED (the audit trail must outlive the event it records):
    - deletion_requests, deletion_audit_log
    - consent_records (kept, but subject_deleted=True and profile_id nulled)

Every step's row count is recorded in DeletionAuditLog so the operation is
independently verifiable after the fact — that's what
tests/backend/test_privacy_service.py checks against.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.orm import Session

from sqlalchemy import or_

from src.database.models import (
    Connection,
    ConsentRecord,
    DeletionAuditLog,
    DeletionRequest,
    MatchScoreCache,
    Message,
    Organization,
    Profile,
    ProfileMatchStats,
    Project,
    ProjectParticipant,
    QuestCompletion,
    QuizResponse,
    Resource,
    RoleGrant,
)

logger = logging.getLogger(__name__)


class PrivacyServiceError(Exception):
    pass


class ProfileNotFoundError(PrivacyServiceError):
    pass


def export_user_data(db: Session, profile_id: str) -> Dict[str, Any]:
    """LinkedIn-style full export: every row that references this user,
    gathered into one JSON-serializable bundle. Read-only — does not
    mutate anything."""
    profile = db.get(Profile, uuid.UUID(str(profile_id)))
    if not profile:
        raise ProfileNotFoundError(f"Profile {profile_id} not found")

    connections = (
        db.query(Connection)
        .filter((Connection.from_user_id == profile.id) | (Connection.to_user_id == profile.id))
        .all()
    )
    owned_projects = db.query(Project).filter(Project.owner_id == profile.id).all()
    participations = db.query(ProjectParticipant).filter(ProjectParticipant.profile_id == profile.id).all()
    messages_sent = db.query(Message).filter(Message.from_user_id == profile.id).all()
    messages_received = db.query(Message).filter(Message.to_user_id == profile.id).all()
    resources_submitted = db.query(Resource).filter(Resource.submitted_by == profile.id).all()
    role_grants = db.query(RoleGrant).filter(RoleGrant.discord_id == profile.discord_id).all()
    quest_completions = db.query(QuestCompletion).filter(QuestCompletion.discord_id == profile.discord_id).all()
    consent_records = db.query(ConsentRecord).filter(ConsentRecord.profile_id == profile.id).all()
    quiz_responses = db.query(QuizResponse).filter(QuizResponse.profile_id == profile.id).all()
    cached_match_scores = (
        db.query(MatchScoreCache)
        .filter(
            MatchScoreCache.is_current.is_(True),
            or_(MatchScoreCache.profile_lo_id == profile.id, MatchScoreCache.profile_hi_id == profile.id),
        )
        .all()
    )

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile.to_dict(),
        "connections": [c.to_dict() for c in connections],
        "owned_projects": [p.to_dict() for p in owned_projects],
        "project_participations": [p.to_dict() for p in participations],
        "messages_sent": [m.to_dict() for m in messages_sent],
        "messages_received": [m.to_dict() for m in messages_received],
        "resources_submitted": [r.to_dict() for r in resources_submitted],
        "role_grants": [r.to_dict() for r in role_grants],
        "quest_completions_count": len(quest_completions),
        "quiz_responses": [q.to_dict() for q in quiz_responses],
        "consent_records": [c.to_dict() for c in consent_records],
        # Derived/profiling data computed FROM this profile's own fields —
        # current cached compatibility scores only; superseded history rows
        # aren't part of what the person would recognize as "my data" in a
        # LinkedIn-style export, though they're still purged on deletion.
        "cached_match_scores": [c.to_dict() for c in cached_match_scores],
    }


def preview_deletion(db: Session, profile_id: str) -> Dict[str, int]:
    """Dry run: counts what WOULD be affected, without changing anything.
    Lets an admin (or a test) sanity-check the blast radius before
    committing to a real deletion."""
    profile = db.get(Profile, uuid.UUID(str(profile_id)))
    if not profile:
        raise ProfileNotFoundError(f"Profile {profile_id} not found")

    pid = profile.id
    return {
        "connections": db.query(Connection)
        .filter((Connection.from_user_id == pid) | (Connection.to_user_id == pid))
        .count(),
        "project_participations": db.query(ProjectParticipant).filter(ProjectParticipant.profile_id == pid).count(),
        "owned_projects_to_orphan": db.query(Project).filter(Project.owner_id == pid).count(),
        "owned_organizations_to_orphan": db.query(Organization).filter(Organization.owner_id == pid).count(),
        "messages_to_anonymize": db.query(Message)
        .filter((Message.from_user_id == pid) | (Message.to_user_id == pid))
        .count(),
        "resources_to_orphan": db.query(Resource).filter(Resource.submitted_by == pid).count(),
        "role_grants": db.query(RoleGrant).filter(RoleGrant.discord_id == profile.discord_id).count(),
        "quest_completions": db.query(QuestCompletion).filter(QuestCompletion.discord_id == profile.discord_id).count(),
        "quiz_responses": db.query(QuizResponse).filter(QuizResponse.profile_id == pid).count(),
        "consent_records_to_anonymize": db.query(ConsentRecord).filter(ConsentRecord.profile_id == pid).count(),
        "cached_match_scores_to_delete": db.query(MatchScoreCache)
        .filter(or_(MatchScoreCache.profile_lo_id == pid, MatchScoreCache.profile_hi_id == pid))
        .count(),
    }


def delete_user(db: Session, profile_id: str, requested_by: str = "self") -> Dict[str, Any]:
    """Executes the deletion policy documented at the top of this module in
    one transaction. Returns the completed DeletionRequest (with its audit
    log) as a dict. Raises and rolls back the whole transaction if any step
    fails — a half-completed deletion is worse than a failed one."""
    profile = db.get(Profile, uuid.UUID(str(profile_id)))
    if not profile:
        raise ProfileNotFoundError(f"Profile {profile_id} not found")

    pid = profile.id
    discord_id = profile.discord_id

    deletion_request = DeletionRequest(
        id=uuid.uuid4(),
        profile_id=pid,
        discord_id=discord_id,
        requested_by=requested_by,
        status="pending",
    )
    db.add(deletion_request)
    db.flush()  # get deletion_request.id without committing yet

    def _log(table_name: str, action: str, rows_affected: int) -> None:
        db.add(
            DeletionAuditLog(
                id=uuid.uuid4(),
                deletion_request_id=deletion_request.id,
                table_name=table_name,
                action=action,
                rows_affected=rows_affected,
            )
        )

    try:
        # 1. Hard-delete relationship rows that have no meaning once this user is gone.
        n = db.query(Connection).filter((Connection.from_user_id == pid) | (Connection.to_user_id == pid)).delete(synchronize_session=False)
        _log("connections", "hard_delete", n)

        n = db.query(ProjectParticipant).filter(ProjectParticipant.profile_id == pid).delete(synchronize_session=False)
        _log("project_participants", "hard_delete", n)

        n = db.query(RoleGrant).filter(RoleGrant.discord_id == discord_id).delete(synchronize_session=False)
        _log("role_grants", "hard_delete", n)

        n = db.query(QuizResponse).filter(QuizResponse.profile_id == pid).delete(synchronize_session=False)
        _log("quiz_responses", "hard_delete", n)

        n = db.query(QuestCompletion).filter(QuestCompletion.discord_id == discord_id).delete(synchronize_session=False)
        _log("quest_completions", "hard_delete", n)

        # Purge every cached/historical match score involving this profile, both
        # directions and both current and superseded rows — a compatibility score
        # computed from a now-deleted profile's skills/neurotype/etc. is itself
        # derived personal data and has no remaining purpose once that profile is
        # gone. (The FK's ondelete='CASCADE' would remove these automatically once
        # the profile row is deleted below, but that's the safety net, not the
        # mechanism — this explicit delete is what makes it auditable in the same
        # report as every other step, per this module's design.)
        n = (
            db.query(MatchScoreCache)
            .filter((MatchScoreCache.profile_lo_id == pid) | (MatchScoreCache.profile_hi_id == pid))
            .delete(synchronize_session=False)
        )
        _log("match_score_cache", "hard_delete", n)

        n = db.query(ProfileMatchStats).filter(ProfileMatchStats.profile_id == pid).delete(synchronize_session=False)
        _log("profile_match_stats", "hard_delete", n)

        # 2. Orphan (don't destroy) rows that other people/the community still need.
        n = (
            db.query(Project)
            .filter(Project.owner_id == pid)
            .update({"owner_id": None, "owner_deleted": True}, synchronize_session=False)
        )
        _log("projects", "nullified", n)

        n = (
            db.query(Organization)
            .filter(Organization.owner_id == pid)
            .update({"owner_id": None, "owner_deleted": True}, synchronize_session=False)
        )
        _log("organizations", "nullified", n)

        n = (
            db.query(Resource)
            .filter(Resource.submitted_by == pid)
            .update({"submitted_by": None}, synchronize_session=False)
        )
        _log("resources", "nullified", n)

        n = (
            db.query(Message)
            .filter(Message.from_user_id == pid)
            .update({"from_user_id": None, "from_user_deleted": True}, synchronize_session=False)
        )
        n += (
            db.query(Message)
            .filter(Message.to_user_id == pid)
            .update({"to_user_id": None, "to_user_deleted": True}, synchronize_session=False)
        )
        _log("messages", "nullified", n)

        # 3. Anonymize (never delete) the consent audit trail.
        n = (
            db.query(ConsentRecord)
            .filter(ConsentRecord.profile_id == pid)
            .update({"profile_id": None, "subject_deleted": True}, synchronize_session=False)
        )
        _log("consent_records", "anonymized", n)

        # 4. Finally, hard-delete the profile itself — the account's PII is gone.
        db.query(Profile).filter(Profile.id == pid).delete(synchronize_session=False)
        _log("profiles", "hard_delete", 1)

        deletion_request.status = "completed"
        deletion_request.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception:
        db.rollback()
        logger.exception("Deletion failed for profile %s — transaction rolled back, nothing was changed", profile_id)
        raise

    db.refresh(deletion_request)
    logger.info("Deleted profile %s (discord_id=%s), deletion_request=%s", profile_id, discord_id, deletion_request.id)
    return deletion_request.to_dict()
