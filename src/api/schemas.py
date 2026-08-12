"""
Pydantic request models. Introduced for the endpoints built/hardened in this
pass (organizations, project edits) so their bodies are strictly validated
rather than raw Dict[str, Any]. Extend this file as the other write endpoints
are migrated off dicts.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mission: Optional[str] = Field(default=None, max_length=5000)
    location: Optional[str] = Field(default=None, max_length=100)
    org_type: Optional[str] = Field(default=None, max_length=50)
    roles_open: List[str] = Field(default_factory=list, max_length=50)
    project_links: List[str] = Field(default_factory=list, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    beta_info: Optional[str] = Field(default=None, max_length=5000)
    resume_request: bool = False


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    mission: Optional[str] = Field(default=None, max_length=5000)
    location: Optional[str] = Field(default=None, max_length=100)
    org_type: Optional[str] = Field(default=None, max_length=50)
    roles_open: Optional[List[str]] = Field(default=None, max_length=50)
    project_links: Optional[List[str]] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    beta_info: Optional[str] = Field(default=None, max_length=5000)
    resume_request: Optional[bool] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    neurotypes_needed: Optional[List[str]] = Field(default=None, max_length=50)
    skills_needed: Optional[List[str]] = Field(default=None, max_length=50)
    status: Optional[str] = Field(default=None, max_length=20)
