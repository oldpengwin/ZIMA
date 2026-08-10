"""
Database Models for ZIMA Platform

SQLAlchemy models for PostgreSQL database.
"""

from datetime import datetime
from typing import List, Optional
from enum import Enum
import uuid

from sqlalchemy import Column, String, Text, Boolean, DateTime, ARRAY, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Import pgvector for vector support
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None


# Base class for declarative models
Base = declarative_base()


class NeurotypeEnum(Enum):
    """Neurotype enumeration"""
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
    """Connection request status enumeration"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Profile(Base):
    """User profile model"""
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discord_id = Column(String(64), unique=True, nullable=False, index=True)
    discord_username = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=False)
    neurotype = Column(String(20), nullable=False, index=True)
    skills = Column(ARRAY(String), default=[])
    offering = Column(ARRAY(String), default=[])
    looking_for = Column(ARRAY(String), default=[])
    projects = Column(ARRAY(String), default=[])
    location = Column(String(100))
    bio = Column(Text)
    links = Column(ARRAY(String), default=[])
    is_open = Column(Boolean, default=True, index=True)
    tagline = Column(String(255))  # LLM-generated summary
    embedding = Column(Vector(384)) if Vector else Column(ARRAY(Float))  # For vector search
    vision_2036 = Column(Text)  # Long-term vision
    mission = Column(Text)  # Personal mission
    badges = Column(ARRAY(String), default=[])  # Achievements
    wall_posts = Column(ARRAY(String), default=[])  # Recent activity
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Profile {self.display_name} ({self.neurotype})>"

    def to_dict(self) -> dict:
        """Convert profile to dictionary"""
        return {
            "id": str(self.id),
            "discord_id": self.discord_id,
            "discord_username": self.discord_username,
            "display_name": self.display_name,
            "neurotype": self.neurotype,
            "skills": self.skills or [],
            "offering": self.offering or [],
            "looking_for": self.looking_for or [],
            "projects": self.projects or [],
            "location": self.location,
            "bio": self.bio,
            "links": self.links or [],
            "is_open": self.is_open,
            "tagline": self.tagline,
            "vision_2036": self.vision_2036,
            "mission": self.mission,
            "badges": self.badges or [],
            "wall_posts": self.wall_posts or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ConnectionRequest(Base):
    """Connection request model"""
    __tablename__ = "connection_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    to_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(20), default="pending", index=True)
    message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id", name="_from_to_uc"),
    )

    def __repr__(self):
        return f"<ConnectionRequest {self.id} {self.status}>"

    def to_dict(self) -> dict:
        """Convert connection request to dictionary"""
        return {
            "id": str(self.id),
            "from_user_id": str(self.from_user_id),
            "to_user_id": str(self.to_user_id),
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Project(Base):
    """Project model"""
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    neurotypes_needed = Column(ARRAY(String), default=[])
    skills_needed = Column(ARRAY(String), default=[])
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Project {self.title}>"

    def to_dict(self) -> dict:
        """Convert project to dictionary"""
        return {
            "id": str(self.id),
            "owner_id": str(self.owner_id),
            "title": self.title,
            "description": self.description,
            "neurotypes_needed": self.neurotypes_needed or [],
            "skills_needed": self.skills_needed or [],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ProjectParticipant(Base):
    """Project participant model"""
    __tablename__ = "project_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    profile_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String(100))
    joined_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("project_id", "profile_id", name="_project_profile_uc"),
    )

    def __repr__(self):
        return f"<ProjectParticipant {self.project_id} {self.profile_id}>"

    def to_dict(self) -> dict:
        """Convert project participant to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "profile_id": str(self.profile_id),
            "role": self.role,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None
        }


class Organization(Base):
    """Organization model"""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    mission = Column(Text)
    location = Column(String(100))
    roles_open = Column(ARRAY(String), default=[])
    project_links = Column(ARRAY(String), default=[])
    email = Column(String(255))
    beta_info = Column(Text)  # Information about beta programs
    resume_request = Column(Boolean, default=False)  # Whether accepting resumes
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Organization {self.name}>"

    def to_dict(self) -> dict:
        """Convert organization to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "mission": self.mission,
            "location": self.location,
            "roles_open": self.roles_open or [],
            "project_links": self.project_links or [],
            "email": self.email,
            "beta_info": self.beta_info,
            "resume_request": self.resume_request,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Resource(Base):
    """Resource model for directory"""
    __tablename__ = "resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    type = Column(String(50), index=True)  # learning, tool, builder, hackathon, event, dataset, pattern, lesson
    category = Column(String(100), index=True)
    subcategory = Column(String(100))
    url = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="pending", index=True)  # pending, verified
    votes = Column(Integer, default=0)
    cool = Column(Integer, default=0)  # Separate scoring system
    created_at = Column(DateTime, server_default=func.now())
    submitted_by = Column(UUID(as_uuid=True))

    def __repr__(self):
        return f"<Resource {self.title}>"

    def to_dict(self) -> dict:
        """Convert resource to dictionary"""
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
            "submitted_by": str(self.submitted_by) if self.submitted_by else None
        }


class Message(Base):
    """Message model for user conversations"""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    to_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    content = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Message {self.id}>"

    def to_dict(self) -> dict:
        """Convert message to dictionary"""
        return {
            "id": str(self.id),
            "from_user_id": str(self.from_user_id),
            "to_user_id": str(self.to_user_id),
            "content": self.content,
            "read": self.read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Event(Base):
    """Event model"""
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    location = Column(String(100))
    official = Column(Boolean, default=False, index=True)
    description = Column(Text)
    contact_email = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Event {self.title}>"

    def to_dict(self) -> dict:
        """Convert event to dictionary"""
        return {
            "id": str(self.id),
            "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "location": self.location,
            "official": self.official,
            "description": self.description,
            "contact_email": self.contact_email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class LanguageEntry(Base):
    """Language map entry - tracks word usage and drift"""
    __tablename__ = "language_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    word = Column(String(100), nullable=False, index=True)
    definitions = Column(JSON, default={})  # {group_name: definition_sample}
    drift_score = Column(Float, default=0.0)  # 0.0-1.0, high > 0.7
    frequency_by_neurotype = Column(JSON, default={})  # {neurotype: count}
    frequency_by_location = Column(JSON, default={})  # {location: count}
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<LanguageEntry {self.word}>"

    def to_dict(self) -> dict:
        """Convert language entry to dictionary"""
        return {
            "id": str(self.id),
            "word": self.word,
            "definitions": self.definitions or {},
            "drift_score": self.drift_score,
            "frequency_by_neurotype": self.frequency_by_neurotype or {},
            "frequency_by_location": self.frequency_by_location or {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# Import for unique constraint
from sqlalchemy import UniqueConstraint