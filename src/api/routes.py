"""
FastAPI routes for the ZIMA Platform.

Rewritten on top of the SQLAlchemy services layer (src/services/*) instead
of the old raw-psycopg2 ProfileManager. Fixes applied vs. the previous
version:
  - `uuid.uuid4()` used without importing `uuid` (crashed POST /match/request)
  - `TokenData` instantiated with kwargs but had no `__init__` (crashed every
    real authenticated call) — see core/auth.py
  - Auth was fully mocked (any password matched "mock_password"'s hash) —
    replaced with real Discord OAuth2, see /auth/discord/*
  - DB connection string and JWT secret were hardcoded — now read from
    core/config.py, which fails loudly in production if unset
  - Connection requests were faked in-memory ("in a real implementation this
    would create a database record") — now real, via services/connection_service.py
"""

import logging
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy.orm import Session

from src.core.auth import (
    TokenData,
    create_access_token,
    discord_authorize_url,
    exchange_discord_code,
    get_current_user,
    require_bot_service,
)
from src.core import discord_client
from src.core import neurotypes as neurotype_registry
from src.core.config import get_settings
from src.db.session import get_db
from src.api.schemas import OrganizationCreate, OrganizationUpdate, ProjectUpdate
from src.services import (
    connection_service,
    matching_service,
    network_service,
    organization_service,
    privacy_service,
    profile_service,
    project_service,
    quiz_service,
    role_service,
    stats_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


def _recompute_stats_best_effort(db: Session, *profile_ids: Optional[str]) -> None:
    """Refreshes ProfileMatchStats for whichever profiles an action just
    affected — e.g. both sides of a newly-accepted connection, or a
    project's owner plus whoever just joined it. Best-effort and never
    raises: a stats-cache refresh failing must not fail the write it's
    attached to (the write already committed), but it's logged loudly, not
    swallowed — see the module docstring in services/stats_service.py for
    why this is triggered here rather than recomputed on every read."""
    for profile_id in profile_ids:
        if not profile_id:
            continue
        try:
            stats_service.recompute_profile_stats(db, str(profile_id))
        except Exception:
            logger.exception("Best-effort stats recompute failed for profile_id=%s — stats may be briefly stale.", profile_id)


async def _notify_discord_best_effort(discord_id: Optional[str], content: str) -> None:
    """See core/discord_client.py — this is the Python-backend-pushes-to-Discord
    half of the "hooking" the bot and API previously lacked. Wrapped again here
    (discord_client's own functions already catch httpx errors) so a genuinely
    unexpected exception in this layer still can't take down the response it's
    attached to; it's logged either way, never silent."""
    if not discord_id:
        return
    try:
        await discord_client.send_dm(discord_id, content)
    except Exception:
        logger.exception("Unexpected error sending Discord DM to discord_id=%s", discord_id)


async def _revoke_discord_access_best_effort(discord_id: Optional[str]) -> None:
    """Called after a real account deletion — the Discord side of "get rid of
    their information without ruining everything else." A deleted account's
    Vetted role granted during onboarding must not silently outlive the
    account it was granted for."""
    if not discord_id:
        return
    settings = get_settings()
    try:
        if settings.discord_vetted_role_id:
            await discord_client.remove_guild_member_role(
                discord_id, settings.discord_vetted_role_id, reason="ZIMA account deletion"
            )
        await discord_client.send_dm(
            discord_id,
            "Your ZIMA account and all associated data have been deleted, per your request. "
            "If you didn't request this, contact a moderator immediately.",
        )
    except Exception:
        logger.exception("Unexpected error revoking Discord access for discord_id=%s", discord_id)


# ─────────────────────────────────── Auth ───────────────────────────────────

_OAUTH_STATE_COOKIE = "zima_oauth_state"
_OAUTH_STATE_PATH = "/api/v1/auth/discord"


@router.get("/auth/discord/login")
async def discord_login() -> RedirectResponse:
    """Starts the real Discord OAuth2 flow. Returns 503 (not a fake success)
    if DISCORD_CLIENT_ID/SECRET aren't configured — see core/config.py.

    The `state` is bound to THIS browser: a random nonce is signed into the
    state JWT and also set in an httpOnly cookie. The callback requires the two
    to match, so a state minted for one visitor can't be replayed to complete a
    login in another session (login-CSRF / auth-code fixation)."""
    settings = get_settings()
    nonce = secrets.token_urlsafe(24)
    state = jwt.encode(
        {"nonce": nonce, "exp": time.time() + 600}, settings.secret_key, algorithm=settings.algorithm
    )
    response = RedirectResponse(discord_authorize_url(state))
    response.set_cookie(
        _OAUTH_STATE_COOKIE,
        nonce,
        max_age=600,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",  # sent on the top-level redirect back from Discord
        path=_OAUTH_STATE_PATH,
    )
    return response


@router.get("/auth/discord/callback")
async def discord_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    settings = get_settings()
    # Consume the state cookie regardless of outcome (single use).
    cookie_nonce = request.cookies.get(_OAUTH_STATE_COOKIE)
    response.delete_cookie(_OAUTH_STATE_COOKIE, path=_OAUTH_STATE_PATH)
    try:
        payload = jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state") from e
    if not cookie_nonce or payload.get("nonce") != cookie_nonce:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth state does not match this session")

    discord_user = await exchange_discord_code(code)
    discord_id = discord_user["id"]
    username = discord_user.get("username", discord_id)

    profile = profile_service.get_profile_by_discord_id(db, discord_id)
    if not profile:
        profile = profile_service.create_profile(
            db,
            {
                "discord_id": discord_id,
                "discord_username": username,
                "display_name": discord_user.get("global_name") or username,
                "consented": True,
                "consent_source": "discord_oauth_login",
            },
        )

    access_token = create_access_token(discord_id=discord_id, username=username)
    # If a frontend is configured, redirect back to it with the token in the URL
    # FRAGMENT (after '#'), so the SPA reads it and the token never reaches a
    # server log or referrer. Otherwise return JSON (API-only / local testing).
    if settings.frontend_url:
        from urllib.parse import urlencode

        frag = urlencode({"access_token": access_token, "profile_id": str(profile.id)})
        redirect = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/#/auth/callback?{frag}")
        redirect.delete_cookie(_OAUTH_STATE_COOKIE, path=_OAUTH_STATE_PATH)
        return redirect
    return {"access_token": access_token, "token_type": "bearer", "profile_id": str(profile.id)}


@router.post("/auth/dev-token")
async def dev_token(discord_id: str, username: str = "dev-user") -> Dict[str, str]:
    """Local/test-only: issues a real JWT for any discord_id, no password.
    Hard-disabled outside development — see core/config.Settings.dev_auth_enabled."""
    settings = get_settings()
    if not settings.dev_auth_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    access_token = create_access_token(discord_id=discord_id, username=username)
    return {"access_token": access_token, "token_type": "bearer"}


# ─────────────────────────────────── Profiles ───────────────────────────────────


@router.post("/profiles", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: Dict[str, Any],
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if profile_service.get_profile_by_discord_id(db, current_user.discord_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists for this account")
    profile_data["discord_id"] = current_user.discord_id
    profile_data.setdefault("discord_username", current_user.username)
    try:
        profile = profile_service.create_profile(db, profile_data)
    except profile_service.InvalidProfileDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except profile_service.DuplicateProfileError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return profile.to_dict()


@router.get("/profiles/me", response_model=Dict[str, Any])
async def get_my_profile(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    profile = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile.to_dict()


@router.get("/profiles/{profile_id}", response_model=Dict[str, Any])
async def get_profile(profile_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    profile = profile_service.get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile.to_dict()


@router.get("/profiles/{profile_id}/stats", response_model=Dict[str, Any])
async def get_profile_stats(profile_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Precomputed aggregate numbers (connections/projects/match summary) —
    see services/stats_service.py. A single indexed read; the first-ever
    call for a profile computes and caches it, every call after is free
    until the next write-triggered recompute."""
    if not profile_service.get_profile_by_id(db, profile_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    try:
        stats = stats_service.get_or_compute_profile_stats(db, profile_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return stats.to_dict()


@router.put("/profiles/{profile_id}", response_model=Dict[str, Any])
async def update_profile(
    profile_id: str,
    updates: Dict[str, Any],
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    profile = profile_service.get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    if profile.discord_id != current_user.discord_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only update your own profile")
    try:
        updated = profile_service.update_profile(db, profile_id, updates)
    except profile_service.InvalidProfileDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return updated.to_dict()


@router.get("/profiles/{profile_id}/roles", response_model=List[Dict[str, Any]])
async def get_profile_roles(profile_id: str, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Discord role grant history for a profile — written by the Node bot
    (src/roles/roleManager.js) directly to the shared database, read here
    for the first time. See services/role_service.py."""
    profile = profile_service.get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return [r.to_dict() for r in role_service.get_role_grants_for_discord_id(db, profile.discord_id)]


@router.get("/profiles", response_model=List[Dict[str, Any]])
async def search_profiles(
    q: Optional[str] = Query(None, min_length=2, max_length=200),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    if q:
        profiles = profile_service.search_profiles(db, q, limit, offset)
    else:
        profiles = profile_service.get_all_profiles(db, limit, offset)
    return [p.to_dict() for p in profiles]


# ─────────────────────────────────── Matching ───────────────────────────────────


@router.get("/match/{user_id}", response_model=Dict[str, Any])
async def find_matches(
    user_id: str,
    limit: int = Query(5, ge=1, le=20),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    user_profile = profile_service.get_profile_by_id(db, user_id)
    if not user_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user_profile.discord_id != current_user.discord_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only find matches for yourself")

    try:
        result = matching_service.find_matches(db, user_id, limit)
    except matching_service.MatchingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return result


@router.post("/match/request", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def request_connection(
    request_data: Dict[str, Any],
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    to_user_id = request_data.get("to_user_id")
    if not to_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="to_user_id is required")

    from_profile = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not from_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Your profile was not found")

    try:
        conn = connection_service.create_connection(
            db, str(from_profile.id), to_user_id, request_data.get("message", "")
        )
    except connection_service.DuplicateConnectionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except connection_service.ConnectionServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    to_profile = profile_service.get_profile_by_id(db, to_user_id)
    await _notify_discord_best_effort(
        to_profile.discord_id if to_profile else None,
        f"**{from_profile.display_name}** wants to connect on ZIMA: \"{conn.message or 'Let’s build something.'}\"\n"
        f"Reply on the platform to accept or decline.",
    )
    return conn.to_dict()


@router.get("/match/{user_id}/requests", response_model=Dict[str, Any])
async def get_connection_requests(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    user_profile = profile_service.get_profile_by_id(db, user_id)
    if not user_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user_profile.discord_id != current_user.discord_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only get your own connection requests")

    connections = connection_service.get_connections_for_user(db, user_id)
    return {
        "user_id": user_id,
        "requests": [c.to_dict() for c in connections],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.put("/match/requests/{connection_id}", response_model=Dict[str, Any])
async def respond_to_connection(
    connection_id: str,
    body: Dict[str, str],
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    status_value = body.get("status")
    if status_value not in {"accepted", "rejected", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status must be accepted/rejected/cancelled")
    try:
        conn = connection_service.update_connection_status(db, connection_id, status_value)
    except connection_service.ConnectionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    if status_value == "accepted":
        # Both sides' connection counts just changed — refresh both, not on next read.
        _recompute_stats_best_effort(db, conn.from_user_id, conn.to_user_id)
        requester = profile_service.get_profile_by_id(db, str(conn.from_user_id))
        accepter = profile_service.get_profile_by_id(db, str(conn.to_user_id))
        if requester and accepter:
            await _notify_discord_best_effort(
                requester.discord_id,
                f"**{accepter.display_name}** accepted your connection request on ZIMA. Say hi!",
            )
    return conn.to_dict()


# ─────────────────────────────────── Projects ───────────────────────────────────


@router.post("/projects", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_project(
    data: Dict[str, Any],
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    owner = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Your profile was not found")
    try:
        project = project_service.create_project(db, str(owner.id), data)
    except project_service.ProjectServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    _recompute_stats_best_effort(db, owner.id)
    return project.to_dict()


@router.get("/projects", response_model=List[Dict[str, Any]])
async def list_projects(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    return [p.to_dict() for p in project_service.list_projects(db, status_filter, limit, offset)]


@router.get("/projects/{project_id}", response_model=Dict[str, Any])
async def get_project(project_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project.to_dict()


@router.post("/projects/{project_id}/join", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def join_project(
    project_id: str,
    body: Dict[str, str] = {},
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    profile = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Your profile was not found")
    try:
        participant = project_service.join_project(db, project_id, str(profile.id), body.get("role", "contributor"))
    except project_service.ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except project_service.ProjectServiceError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    _recompute_stats_best_effort(db, profile.id)
    return participant.to_dict()


@router.put("/projects/{project_id}", response_model=Dict[str, Any])
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    owner = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not owner or project.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only edit your own project")
    try:
        updated = project_service.update_project(db, project_id, body.model_dump(exclude_unset=True))
    except project_service.ProjectServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return updated.to_dict()


@router.delete("/projects/{project_id}", response_model=Dict[str, Any])
async def delete_project(
    project_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    owner = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not owner or project.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only delete your own project")
    project_service.delete_project(db, project_id)
    return {"deleted": True, "id": project_id}


# ─────────────────────────────────── Organizations ───────────────────────────────────


@router.post("/organizations", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrganizationCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    owner = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Your profile was not found")
    org = organization_service.create_organization(db, owner.id, body.model_dump())
    return org.to_dict()


@router.get("/organizations", response_model=List[Dict[str, Any]])
async def list_organizations(
    org_type: Optional[str] = Query(None, max_length=50),
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    return [o.to_dict() for o in organization_service.list_organizations(db, org_type, limit, offset)]


@router.get("/organizations/{org_id}", response_model=Dict[str, Any])
async def get_organization(org_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    org = organization_service.get_organization(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org.to_dict()


@router.put("/organizations/{org_id}", response_model=Dict[str, Any])
async def update_organization(
    org_id: str,
    body: OrganizationUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    org = organization_service.get_organization(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    owner = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not owner or org.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only edit your own organization")
    updated = organization_service.update_organization(db, org_id, body.model_dump(exclude_unset=True))
    return updated.to_dict()


@router.delete("/organizations/{org_id}", response_model=Dict[str, Any])
async def delete_organization(
    org_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    org = organization_service.get_organization(db, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    owner = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not owner or org.owner_id != owner.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only delete your own organization")
    organization_service.delete_organization(db, org_id)
    return {"deleted": True, "id": org_id}


# ─────────────────────────────────── Privacy: export & deletion ───────────────────────────────────


@router.get("/users/me/export", response_model=Dict[str, Any])
async def export_my_data(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """LinkedIn-style full data export for the authenticated user."""
    profile = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return privacy_service.export_user_data(db, str(profile.id))


@router.get("/users/me/deletion-preview", response_model=Dict[str, int])
async def preview_my_deletion(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, int]:
    """Shows what deleting your account would affect, before you commit to it."""
    profile = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return privacy_service.preview_deletion(db, str(profile.id))


@router.delete("/users/me", response_model=Dict[str, Any])
async def delete_my_account(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Immediate deletion, no retention period, per the product's stated
    consent-withdrawal policy. Returns the audit report of exactly what was
    hard-deleted / nullified / anonymized so the caller can verify it."""
    profile = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    discord_id = profile.discord_id  # captured before the row is hard-deleted below
    report = privacy_service.delete_user(db, str(profile.id), requested_by="self")
    await _revoke_discord_access_best_effort(discord_id)
    return report


@router.delete("/admin/users/{profile_id}", response_model=Dict[str, Any])
async def admin_delete_user(
    profile_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Admin-triggered deletion (e.g. for testing, or acting on a support
    request). TODO(next pass): real role-based authorization — today any
    authenticated user can call this, which is only acceptable because it's
    not exposed publicly yet. Flagged here rather than silently shipped."""
    logger.warning(
        "admin_delete_user called by discord_id=%s for profile_id=%s — "
        "role-based authorization is NOT YET implemented for this endpoint.",
        current_user.discord_id,
        profile_id,
    )
    target = profile_service.get_profile_by_id(db, profile_id)
    discord_id = target.discord_id if target else None
    try:
        report = privacy_service.delete_user(db, profile_id, requested_by="admin")
    except privacy_service.ProfileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    await _revoke_discord_access_best_effort(discord_id)
    return report


# ─────────────────────────────────── Neurotypes & network ───────────────────────────────────


@router.get("/neurotypes", response_model=Dict[str, Any])
async def get_neurotypes() -> Dict[str, Any]:
    """Canonical archetype registry — presentation + graph metadata (emoji,
    colours, tagline, connections). The backend is the single source of truth
    so the globe, cards, Discord and web all render the same definitions.
    Static + cheap; safe for clients to cache hard."""
    return {
        "neurotypes": {n["id"]: n for n in neurotype_registry.all_neurotypes()},
        "order": list(neurotype_registry.NEUROTYPE_IDS),
        "edges": [{"source": a, "target": b} for a, b in neurotype_registry.edges()],
    }


@router.get("/network", response_model=Dict[str, Any])
async def get_network(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Cached, public-safe archetype-network aggregate for the globe: per-type
    counts, graph edges, and location points (display_name + neurotype + city
    only — never discord_id). Recomputed at most once per TTL / on write, so
    polling it never churns the DB."""
    return network_service.get_network(db)


# ─────────────────────────────────── Neurotype quiz ───────────────────────────────────


@router.get("/quiz", response_model=Dict[str, Any])
async def get_quiz(version: str = Query("v1", pattern=r"^v[0-9]{1,4}$")) -> Dict[str, Any]:
    """The weight-free question bank to render (Discord or web). Scoring weights
    are never exposed, so the archetype mapping isn't guessable from the payload."""
    try:
        return quiz_service.get_public_quiz(version)
    except quiz_service.QuizServiceError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


def _run_quiz_submit(db: Session, profile_id: str, body: Dict[str, Any], source: str) -> Dict[str, Any]:
    identified = body.get("identified") or body.get("identified_neurotype")
    try:
        return quiz_service.submit_quiz(
            db,
            profile_id,
            body.get("answers"),
            identified=identified,
            source=source,
            version=str(body.get("version", "v1")),
        )
    except quiz_service.QuizServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/quiz/submit", response_model=Dict[str, Any])
async def submit_quiz(
    body: Dict[str, Any],
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Submit the authenticated user's own quiz (web path). Answers are cleaned
    by the engine — unknown question/option ids are dropped, never stored."""
    profile = profile_service.get_profile_by_discord_id(db, current_user.discord_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Your profile was not found")
    return _run_quiz_submit(db, str(profile.id), body, source="web")


@router.post("/bot/quiz/submit", response_model=Dict[str, Any])
async def bot_submit_quiz(
    body: Dict[str, Any],
    _bot: None = Depends(require_bot_service),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Discord bot service path: submit a quiz for a given discord_id. Guarded
    by the X-Bot-Key service key (see core/auth.require_bot_service)."""
    discord_id = body.get("discord_id")
    if not discord_id or not isinstance(discord_id, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="discord_id is required")
    profile = profile_service.get_profile_by_discord_id(db, discord_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No profile for that discord_id (onboard first)")
    return _run_quiz_submit(db, str(profile.id), body, source="discord")


@router.post("/bot/profiles/identified", response_model=Dict[str, Any])
async def bot_set_identified(
    body: Dict[str, Any],
    _bot: None = Depends(require_bot_service),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Discord bot service path: set a builder's self-identified badge after
    they pick it at the end of the quiz. Guarded by the X-Bot-Key service key."""
    discord_id = body.get("discord_id")
    identified = body.get("neurotype") or body.get("identified")
    if not discord_id or not isinstance(discord_id, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="discord_id is required")
    if not identified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="neurotype is required")
    profile = profile_service.get_profile_by_discord_id(db, discord_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No profile for that discord_id")
    try:
        updated = quiz_service.set_identified_neurotype(db, str(profile.id), identified)
    except quiz_service.QuizServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return updated.to_dict()


# ─────────────────────────────────── Bot service: profiles & roles ───────────────────────────────────


@router.post("/bot/profiles/upsert", response_model=Dict[str, Any])
async def bot_upsert_profile(
    body: Dict[str, Any],
    _bot: None = Depends(require_bot_service),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Discord bot service path: create-or-update a profile from onboarding.
    Replaces the bot's former direct Supabase service-key write, so the bot no
    longer needs admin DB access. Guarded by X-Bot-Key."""
    if not body.get("discord_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="discord_id is required")
    try:
        profile, created = profile_service.upsert_by_discord_id(
            db, body, mark_onboarded=bool(body.get("onboarding_completed"))
        )
    except profile_service.InvalidProfileDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except profile_service.DuplicateProfileError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    result = profile.to_dict()
    result["created"] = created
    return result


@router.get("/bot/profiles/by-discord/{discord_id}", response_model=Dict[str, Any])
async def bot_get_profile(
    discord_id: str,
    _bot: None = Depends(require_bot_service),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Discord bot service path: fetch a profile by discord_id (used to check
    whether someone has already onboarded). Guarded by X-Bot-Key."""
    profile = profile_service.get_profile_by_discord_id(db, discord_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No profile for that discord_id")
    return profile.to_dict()


@router.post("/bot/role-grants", response_model=Dict[str, Any])
async def bot_record_role_grant(
    body: Dict[str, Any],
    _bot: None = Depends(require_bot_service),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Discord bot service path: record a role grant after the bot assigns a
    Discord role. The Discord-side role add still happens in the bot; only the
    DB record moves here. Guarded by X-Bot-Key."""
    discord_id = body.get("discord_id")
    role_key = body.get("role_key")
    if not discord_id or not role_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="discord_id and role_key are required")
    metadata = body.get("metadata")
    grant = role_service.record_grant(
        db,
        str(discord_id),
        str(role_key),
        source=str(body.get("source", "system")),
        metadata=metadata if isinstance(metadata, dict) else {},
    )
    return grant.to_dict()


@router.put("/profiles/{profile_id}/identified-neurotype", response_model=Dict[str, Any])
async def set_identified_neurotype(
    profile_id: str,
    body: Dict[str, str],
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Owner sets their self-identified badge (e.g. after seeing the assessed
    result). Owner-only."""
    profile = profile_service.get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    if profile.discord_id != current_user.discord_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only set your own neurotype")
    identified = body.get("neurotype") or body.get("identified")
    if not identified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="neurotype is required")
    try:
        updated = quiz_service.set_identified_neurotype(db, profile_id, identified)
    except quiz_service.QuizServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return updated.to_dict()
