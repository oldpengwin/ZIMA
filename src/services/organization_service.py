"""
Organization CRUD. The organizations table existed in the schema but had no
service or routes — this is the missing business logic. Organizations are
owner-scoped: create sets owner_id to the acting profile, and update/delete are
owner-only (enforced in the route layer). Deletion of the owner's account
nullifies owner_id (see privacy_service), so an org outlives its creator.
"""

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.database.models import Organization

_WRITABLE = {
    "name",
    "mission",
    "location",
    "org_type",
    "roles_open",
    "project_links",
    "email",
    "beta_info",
    "resume_request",
}


class OrganizationServiceError(Exception):
    pass


class OrganizationNotFoundError(OrganizationServiceError):
    pass


def create_organization(db: Session, owner_profile_id, data: Dict[str, Any]) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        owner_id=uuid.UUID(str(owner_profile_id)),
        **{k: v for k, v in data.items() if k in _WRITABLE},
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def get_organization(db: Session, org_id: str) -> Optional[Organization]:
    try:
        oid = uuid.UUID(str(org_id))
    except ValueError:
        return None
    return db.get(Organization, oid)


def list_organizations(db: Session, org_type: Optional[str] = None, limit: int = 24, offset: int = 0) -> List[Organization]:
    q = db.query(Organization).order_by(Organization.created_at.desc())
    if org_type:
        q = q.filter(Organization.org_type == org_type)
    return q.offset(offset).limit(limit).all()


def update_organization(db: Session, org_id: str, updates: Dict[str, Any]) -> Organization:
    org = get_organization(db, org_id)
    if not org:
        raise OrganizationNotFoundError(f"Organization {org_id} not found")
    for field, value in updates.items():
        if field in _WRITABLE and value is not None:
            setattr(org, field, value)
    db.commit()
    db.refresh(org)
    return org


def delete_organization(db: Session, org_id: str) -> None:
    org = get_organization(db, org_id)
    if not org:
        raise OrganizationNotFoundError(f"Organization {org_id} not found")
    db.delete(org)
    db.commit()
