"""Project + project-roster CRUD."""

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import Project, ProjectParticipant

logger = logging.getLogger(__name__)


class ProjectServiceError(Exception):
    pass


class ProjectNotFoundError(ProjectServiceError):
    pass


VALID_STATUSES = {"idea", "building", "launched"}


def create_project(db: Session, owner_id: str, data: Dict[str, Any]) -> Project:
    if not data.get("title"):
        raise ProjectServiceError("title is required")
    status = data.get("status", "idea")
    if status not in VALID_STATUSES:
        raise ProjectServiceError(f"status must be one of {sorted(VALID_STATUSES)}")

    project = Project(
        id=uuid.uuid4(),
        owner_id=owner_id,
        title=data["title"],
        description=data.get("description"),
        neurotypes_needed=data.get("neurotypes_needed", []),
        skills_needed=data.get("skills_needed", []),
        status=status,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Owner is automatically a participant.
    db.add(ProjectParticipant(id=uuid.uuid4(), project_id=project.id, profile_id=owner_id, role="owner"))
    db.commit()
    return project


def get_project(db: Session, project_id: str) -> Optional[Project]:
    return db.get(Project, uuid.UUID(str(project_id)))


def list_projects(db: Session, status: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Project]:
    q = db.query(Project)
    if status:
        q = q.filter(Project.status == status)
    return q.order_by(Project.created_at.desc()).offset(offset).limit(limit).all()


_UPDATABLE = {"title", "description", "neurotypes_needed", "skills_needed", "status"}


def update_project(db: Session, project_id: str, updates: Dict[str, Any]) -> Project:
    project = get_project(db, project_id)
    if not project:
        raise ProjectNotFoundError(f"Project {project_id} not found")
    if updates.get("status") is not None and updates["status"] not in VALID_STATUSES:
        raise ProjectServiceError(f"status must be one of {sorted(VALID_STATUSES)}")
    for field, value in updates.items():
        if field in _UPDATABLE and value is not None:
            setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: str) -> None:
    project = get_project(db, project_id)
    if not project:
        raise ProjectNotFoundError(f"Project {project_id} not found")
    db.delete(project)  # project_participants cascade via FK
    db.commit()


def join_project(db: Session, project_id: str, profile_id: str, role: str = "contributor") -> ProjectParticipant:
    if not db.get(Project, uuid.UUID(str(project_id))):
        raise ProjectNotFoundError(f"Project {project_id} not found")
    participant = ProjectParticipant(id=uuid.uuid4(), project_id=project_id, profile_id=profile_id, role=role)
    db.add(participant)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ProjectServiceError("Already a participant on this project") from e
    db.refresh(participant)
    return participant


def list_participants(db: Session, project_id: str) -> List[ProjectParticipant]:
    return db.query(ProjectParticipant).filter(ProjectParticipant.project_id == project_id).all()
