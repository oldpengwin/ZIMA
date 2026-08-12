"""
Canonical Database Models for the ZIMA Platform.

This is the single source of truth for the ZIMA schema, reconciling the three
schemas that previously disagreed with each other:
  - supabase/schema.sql (what the Discord bot actually wrote)
  - the old src/core/profile_manager.py raw-SQL field set
  - this file's own previous, broken version (missing imports, unresolved names)

Design notes:
  - `profiles` is a superset of the Discord bot's simple onboarding fields
    (discord_id, discord_username, display_name, location, skills, bio,
    links, onboarding_completed_at) PLUS the richer matching/product fields
    (neurotype, offering, looking_for, projects, tagline, embedding, etc).
    The bot only ever writes the first set; it's safe for it to keep doing
    that because every added column here is nullable/defaulted. See
    supabase/schema.sql, which has been updated to match this file.
  - `neurotype` is nullable: a profile exists (and the bot can onboard
    someone) before the archetype quiz has been taken.
  - Privacy/deletion is a first-class concern, not bolted on: ConsentRecord,
    DeletionRequest and DeletionAuditLog exist so that the "delete a user
    without corrupting anyone else's data" requirement is auditable and
    testable (see src/services/privacy_service.py and
    tests/backend/test_privacy_service.py).
  - Foreign keys that point at a profile use ondelete='SET NULL' where the
    referencing row has independent value once the profile is gone (a
    project other people still work on, a resource the community still
    uses, a message the other party still holds), and ondelete='CASCADE'
    where the row IS the relationship and has no independent value once one
    side is gone (a connection, a project roster entry, a role grant).
    These DB-level constraints are a safety net; the actual deletion flow in
    privacy_service.py performs them explicitly so it can produce an audit
    report of what happened.
"""

from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func, text as sql_text

Base = declarative_base()


def _uuid_pk():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class NeurotypeEnum(Enum):
    """The 10 canonical archetypes (Archetypes.md). Any other archetype set
    found elsewhere in the project (the 7-type Figma file, the 6-type regex
    set in demo/zima-globe.html) is stale/deprecated — this is the one the
    product and backend use."""

    SEEDCASTER = "seedcaster"
    FABRICANT = "fabricant"
    MYCELIAN = "mycelian"
    TERRAFORMER = "terraformer"
    DEVELOPER = "developer"
    ARTISAN = "artisan"
    CHRONICLER = "chronicler"
    CULTIVAR = "cultivar"
    LOOMKEEPER = "loomkeeper"
    VERDANT = "verdant"


class ConnectionStatusEnum(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Profile(Base):
    """A builder's profile. Also the platform's identity record — there is
    no separate `users` table; `profiles.id` IS the user id everywhere."""

    __tablename__ = "profiles"

    id = _uuid_pk()

    # Discord identity + the fields the bot's onboarding modal writes today.
    discord_id = Column(String(64), unique=True, nullable=False, index=True)
    discord_username = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=False)
    location = Column(String(100))
    skills = Column(ARRAY(String), default=list, server_default="{}")
    bio = Column(Text)
    links = Column(ARRAY(String), default=list, server_default="{}")
    onboarding_completed_at = Column(DateTime(timezone=True))

    # Richer product/matching fields, filled in later via the web app.
    # Two neurotypes by design: `assessed_neurotype` is what the typology quiz
    # + skills compute (the system's judgement), `identified_neurotype` is what
    # the person self-selects at the end (their chosen identity). Both surface
    # as separate badges. `neurotype` is kept as a back-compat alias = the
    # identified one (falling back to assessed), so existing readers/graph code
    # that reads `neurotype` keep working.
    neurotype = Column(String(20), index=True)  # nullable until quiz is taken; = identified or assessed
    assessed_neurotype = Column(String(20), index=True)   # computed by the quiz engine
    identified_neurotype = Column(String(20), index=True)  # self-selected
    offering = Column(ARRAY(String), default=list, server_default="{}")
    looking_for = Column(ARRAY(String), default=list, server_default="{}")
    projects = Column(ARRAY(String), default=list, server_default="{}")
    is_open = Column(Boolean, default=True, server_default="true", index=True)
    tagline = Column(String(255))
    vision_2036 = Column(Text)
    mission = Column(Text)
    badges = Column(ARRAY(String), default=list, server_default="{}")
    wall_posts = Column(ARRAY(String), default=list, server_default="{}")

    # Privacy
    consented_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # set briefly during deletion txn; row is then hard-deleted

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Profile {self.display_name} ({self.neurotype})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "discord_id": self.discord_id,
            "discord_username": self.discord_username,
            "display_name": self.display_name,
            "location": self.location,
            "skills": self.skills or [],
            "bio": self.bio,
            "links": self.links or [],
            "onboarding_completed_at": self.onboarding_completed_at.isoformat() if self.onboarding_completed_at else None,
            "neurotype": self.neurotype,
            "assessed_neurotype": self.assessed_neurotype,
            "identified_neurotype": self.identified_neurotype,
            "offering": self.offering or [],
            "looking_for": self.looking_for or [],
            "projects": self.projects or [],
            "is_open": self.is_open,
            "tagline": self.tagline,
            "vision_2036": self.vision_2036,
            "mission": self.mission,
            "badges": self.badges or [],
            "wall_posts": self.wall_posts or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Connection(Base):
    """A connection request between two profiles (renamed from
    `connection_requests` conceptually — same table shape, clearer name)."""

    __tablename__ = "connections"

    id = _uuid_pk()
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    to_user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default=ConnectionStatusEnum.PENDING.value, server_default="pending", index=True)
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("from_user_id", "to_user_id", name="_from_to_uc"),)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "from_user_id": str(self.from_user_id),
            "to_user_id": str(self.to_user_id),
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Project(Base):
    __tablename__ = "projects"

    id = _uuid_pk()
    # SET NULL, not CASCADE: a project other people are working on must survive its
    # owner's account deletion. owner_deleted is set so the UI can render "[deleted user]".
    owner_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    owner_deleted = Column(Boolean, default=False, server_default="false")
    title = Column(String(200), nullable=False)
    description = Column(Text)
    neurotypes_needed = Column(ARRAY(String), default=list, server_default="{}")
    skills_needed = Column(ARRAY(String), default=list, server_default="{}")
    status = Column(String(20), default="active", server_default="active", index=True)  # idea | building | launched
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "owner_deleted": self.owner_deleted,
            "title": self.title,
            "description": self.description,
            "neurotypes_needed": self.neurotypes_needed or [],
            "skills_needed": self.skills_needed or [],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProjectParticipant(Base):
    __tablename__ = "project_participants"

    id = _uuid_pk()
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(100))
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("project_id", "profile_id", name="_project_profile_uc"),)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "profile_id": str(self.profile_id),
            "role": self.role,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }


class Organization(Base):
    __tablename__ = "organizations"

    id = _uuid_pk()
    # SET NULL like projects: an org survives its creator's account deletion.
    owner_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    owner_deleted = Column(Boolean, default=False, server_default="false")
    name = Column(String(200), nullable=False, index=True)
    mission = Column(Text)
    location = Column(String(100))
    org_type = Column(String(50))  # hardware | advocacy | employment | finance | infrastructure | research | education
    roles_open = Column(ARRAY(String), default=list, server_default="{}")
    project_links = Column(ARRAY(String), default=list, server_default="{}")
    email = Column(String(255))
    beta_info = Column(Text)
    resume_request = Column(Boolean, default=False, server_default="false")
    trust_score = Column(Float, default=0.5, server_default="0.5")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "owner_deleted": self.owner_deleted,
            "name": self.name,
            "mission": self.mission,
            "location": self.location,
            "org_type": self.org_type,
            "roles_open": self.roles_open or [],
            "project_links": self.project_links or [],
            "email": self.email,
            "beta_info": self.beta_info,
            "resume_request": self.resume_request,
            "trust_score": self.trust_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Resource(Base):
    __tablename__ = "resources"

    id = _uuid_pk()
    title = Column(String(200), nullable=False)
    type = Column(String(50), index=True)  # learning | tool | builder | hackathon | event | dataset | pattern | lesson
    category = Column(String(100), index=True)
    subcategory = Column(String(100))
    url = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="pending", server_default="pending", index=True)
    votes = Column(Integer, default=0, server_default="0")
    cool = Column(Integer, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # SET NULL: the resource is a community asset and outlives its submitter's account.
    submitted_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "title": self.title,
            "type": self.type,
            "category": self.category,
            "subcategory": self.subcategory,
            "url": self.url,
            "description": self.description,
            "status": self.status,
            "votes": self.votes,
            "cool": self.cool,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_by": str(self.submitted_by) if self.submitted_by else None,
        }


class Message(Base):
    __tablename__ = "messages"

    id = _uuid_pk()
    # SET NULL, not CASCADE: the recipient keeps their side of the thread after the
    # sender deletes their account (content is preserved; identity is not).
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    to_user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    from_user_deleted = Column(Boolean, default=False, server_default="false")
    to_user_deleted = Column(Boolean, default=False, server_default="false")
    content = Column(Text, nullable=False)
    read = Column(Boolean, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "from_user_id": str(self.from_user_id) if self.from_user_id else None,
            "to_user_id": str(self.to_user_id) if self.to_user_id else None,
            "from_user_deleted": self.from_user_deleted,
            "to_user_deleted": self.to_user_deleted,
            "content": self.content,
            "read": self.read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Event(Base):
    __tablename__ = "events"

    id = _uuid_pk()
    title = Column(String(200), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    location = Column(String(100))
    official = Column(Boolean, default=False, server_default="false", index=True)
    description = Column(Text)
    contact_email = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "location": self.location,
            "official": self.official,
            "description": self.description,
            "contact_email": self.contact_email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class LanguageEntry(Base):
    """Shared Language Map — tracks word usage/drift across archetypes."""

    __tablename__ = "language_entries"

    id = _uuid_pk()
    word = Column(String(100), nullable=False, index=True)
    definitions = Column(JSON, default=dict, server_default="{}")
    drift_score = Column(Float, default=0.0, server_default="0.0")
    frequency_by_neurotype = Column(JSON, default=dict, server_default="{}")
    frequency_by_location = Column(JSON, default=dict, server_default="{}")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "word": self.word,
            "definitions": self.definitions or {},
            "drift_score": self.drift_score,
            "frequency_by_neurotype": self.frequency_by_neurotype or {},
            "frequency_by_location": self.frequency_by_location or {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RoleGrant(Base):
    """Mirrors supabase's role_grants — now also readable from the canonical
    Postgres DB so the Python side can see Discord role history."""

    __tablename__ = "role_grants"

    id = _uuid_pk()
    discord_id = Column(String(64), nullable=False, index=True)
    role_key = Column(String(100), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String(50), default="onboarding", server_default="onboarding")
    role_metadata = Column(JSON, default=dict, server_default="{}")

    __table_args__ = (UniqueConstraint("discord_id", "role_key", name="_discord_role_uc"),)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "discord_id": self.discord_id,
            "role_key": self.role_key,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "source": self.source,
            "metadata": self.role_metadata or {},
        }


class QuestCompletion(Base):
    __tablename__ = "quest_completions"

    id = _uuid_pk()
    discord_id = Column(String(64), nullable=False, index=True)
    quest_key = Column(String(100), nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    quest_metadata = Column(JSON, default=dict, server_default="{}")

    __table_args__ = (UniqueConstraint("discord_id", "quest_key", name="_discord_quest_uc"),)


# ─────────────────────────── Derived/cached data (AcousticBrainz-style) ───────────────────────────
#
# `profiles` above stays a tightly-typed, hot-path relational table — the
# equivalent of what AcousticBrainz calls its core entity (an MBID-keyed
# recording). The two tables below are that platform's other half of the
# pattern: expensive-to-compute or read-heavy *derived* data, stored
# separately so it can be cached, versioned, and evolved independently of
# the identity table it's derived from, without ever touching that table's
# schema. Specifically, borrowed directly from how AcousticBrainz stores
# lowlevel/highlevel audio-feature submissions:
#
#   1. Every computation is INSERTED as a new row, never UPDATEd in place.
#      A `submission history` (here, old match scores) is kept for
#      audit/trend purposes instead of being silently overwritten — the
#      same "append, don't mutate" principle the rest of this schema
#      already applies to deletion_audit_log.
#   2. One narrow, indexed "current" pointer (`is_current`) makes the
#      common read ("give me the match score right now") an O(1) indexed
#      lookup instead of a `MAX(computed_at)` scan.
#   3. The full computed payload lives in a JSONB column (`breakdown`) so
#      the algorithm can grow new dimensions later without a migration —
#      but any field that's actually filtered or sorted on in a hot query
#      (`score`) is promoted to a real indexed column instead of staying
#      buried in JSON. AcousticBrainz does the same thing with e.g.
#      `lossless` on its lowlevel table.
#   4. Cache validity is a content hash (`input_fingerprint`), not a TTL —
#      a row is correct for as long as neither profile's matching-relevant
#      fields nor the algorithm itself have changed, however long that is,
#      and is known-stale the instant either one does.


class MatchScoreCache(Base):
    """Cached pairwise neurotype-match computation. See services/
    matching_service.py — this is what turns "recompute every candidate on
    every /match/{user_id} call" into "compute once, reuse until either
    profile or the algorithm changes." The scoring algorithm in
    core/neurotype_matcher.py is symmetric (score(A, B) == score(B, A) —
    every sub-score is computed from the union/intersection of both
    profiles' fields with no directional term), so each unordered pair is
    stored exactly once under a canonical ordering (`profile_lo_id` is
    always the lexicographically smaller of the two profile ids), not once
    per direction — a match score computed for A is immediately reusable
    when B looks at their own matches, cutting the effective cache
    population in half versus storing it per-direction."""

    __tablename__ = "match_score_cache"

    id = _uuid_pk()
    profile_lo_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_hi_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    score = Column(Float, nullable=False, index=True)  # promoted hot-path column — mirrors AB's `lossless`
    algorithm_version = Column(String(20), nullable=False)
    input_fingerprint = Column(String(64), nullable=False)  # sha256 of both profiles' matching-relevant fields
    breakdown = Column(JSON, nullable=False, default=dict, server_default="{}")  # skill/neurotype/project/location sub-scores

    is_current = Column(Boolean, nullable=False, default=True, server_default="true")
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        # Partial unique index: exactly one is_current=true row per pair, unlimited
        # is_current=false history rows. A plain UniqueConstraint here would also
        # forbid multiple history rows, defeating the point of keeping history.
        Index(
            "ix_match_score_cache_current_pair",
            "profile_lo_id",
            "profile_hi_id",
            unique=True,
            postgresql_where=sql_text("is_current"),
        ),
        Index("ix_match_score_cache_lo_current", "profile_lo_id", "is_current"),
        Index("ix_match_score_cache_hi_current", "profile_hi_id", "is_current"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "profile_lo_id": str(self.profile_lo_id),
            "profile_hi_id": str(self.profile_hi_id),
            "score": self.score,
            "algorithm_version": self.algorithm_version,
            "breakdown": self.breakdown or {},
            "is_current": self.is_current,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
        }


class ProfileMatchStats(Base):
    """Cheap-to-read aggregate summary per profile — AcousticBrainz's
    "highlevel" (derived classification) equivalent of MatchScoreCache's
    "lowlevel" (raw computed feature) data. Recomputed on-demand/on a
    schedule by services/stats_service.py, never inline on a page request,
    so rendering a profile's stats is always a single-row primary-key read
    regardless of how many connections/projects/cached matches exist behind
    it. One row per profile, overwritten in place (unlike MatchScoreCache):
    this is a rollup, not an auditable event, so there's nothing worth
    keeping history of."""

    __tablename__ = "profile_match_stats"

    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    total_connections = Column(Integer, nullable=False, default=0, server_default="0")
    total_projects_owned = Column(Integer, nullable=False, default=0, server_default="0")
    total_projects_joined = Column(Integer, nullable=False, default=0, server_default="0")
    cached_match_count = Column(Integer, nullable=False, default=0, server_default="0")
    avg_match_score = Column(Float, nullable=True)
    top_match_profile_id = Column(UUID(as_uuid=True), nullable=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "profile_id": str(self.profile_id),
            "total_connections": self.total_connections,
            "total_projects_owned": self.total_projects_owned,
            "total_projects_joined": self.total_projects_joined,
            "cached_match_count": self.cached_match_count,
            "avg_match_score": self.avg_match_score,
            "top_match_profile_id": str(self.top_match_profile_id) if self.top_match_profile_id else None,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
        }


class QuizResponse(Base):
    """One neurotype-typology submission. Append-only — a new row per
    submission, never updated in place — so that when the question bank is
    swapped/retuned you can re-score old answers and check whether people's
    self-identified type still aligns with the assessed one over time (the
    "keep changing them and testing if things align" requirement). Stores the
    CLEANED answers and the full per-type score breakdown, keyed to the
    profile; CASCADE so it's purged with the account."""

    __tablename__ = "quiz_responses"

    id = _uuid_pk()
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_version = Column(String(20), nullable=False)
    answers = Column(JSON, nullable=False, default=dict, server_default="{}")   # cleaned {question_id: option_id}
    scores = Column(JSON, nullable=False, default=dict, server_default="{}")     # combined per-type scores
    assessed_neurotype = Column(String(20), nullable=True)    # top type computed from this submission
    identified_neurotype = Column(String(20), nullable=True)  # self-selected (nullable until they pick)
    source = Column(String(20), default="web", server_default="web")  # web | discord
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "profile_id": str(self.profile_id),
            "quiz_version": self.quiz_version,
            "assessed_neurotype": self.assessed_neurotype,
            "identified_neurotype": self.identified_neurotype,
            "scores": self.scores or {},
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────── Privacy / consent / deletion ───────────────────────────


class ConsentRecord(Base):
    """Explicit consent tracking. Kept after a profile is deleted (with the
    subject anonymized) as the compliance record that consent was granted
    and later withdrawn — this table is never touched by the deletion flow
    itself, only appended to."""

    __tablename__ = "consent_records"

    id = _uuid_pk()
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    subject_deleted = Column(Boolean, default=False, server_default="false")
    consent_type = Column(String(50), nullable=False)  # e.g. "data_processing", "discord_scrape"
    granted_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    source = Column(String(50))  # e.g. "discord_onboarding", "web_signup"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "profile_id": str(self.profile_id) if self.profile_id else None,
            "subject_deleted": self.subject_deleted,
            "consent_type": self.consent_type,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "source": self.source,
        }


class DeletionRequest(Base):
    """One row per account-deletion event. Never modified by the deletion it
    records — this and DeletionAuditLog are the audit trail that proves a
    deletion happened and exactly what it touched."""

    __tablename__ = "deletion_requests"

    id = _uuid_pk()
    profile_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # not an FK: profile row is gone after completion
    discord_id = Column(String(64), nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    requested_by = Column(String(50), default="self", server_default="self")  # self | admin
    status = Column(String(20), default="pending", server_default="pending", index=True)  # pending | completed | failed

    audit_entries = relationship("DeletionAuditLog", back_populates="deletion_request", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "profile_id": str(self.profile_id),
            "discord_id": self.discord_id,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "requested_by": self.requested_by,
            "status": self.status,
            "audit": [a.to_dict() for a in self.audit_entries],
        }


class DeletionAuditLog(Base):
    __tablename__ = "deletion_audit_log"

    id = _uuid_pk()
    deletion_request_id = Column(UUID(as_uuid=True), ForeignKey("deletion_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    table_name = Column(String(100), nullable=False)
    action = Column(String(20), nullable=False)  # hard_delete | anonymized | nullified
    rows_affected = Column(Integer, nullable=False, default=0)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

    deletion_request = relationship("DeletionRequest", back_populates="audit_entries")

    def to_dict(self) -> dict:
        return {
            "table_name": self.table_name,
            "action": self.action,
            "rows_affected": self.rows_affected,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }
