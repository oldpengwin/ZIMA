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
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy.orm import Session

from src.core.auth import (
    TokenData,
    create_access_token,
    discord_authorize_url,
    exchange_discord_code,
    get_current_user,
)
from src.core import discord_client
from src.core.config import get_settings
from src.core.neurotype_matcher import Neurotype
from src.db.session import get_db
from src.services import (
    connection_service,
    matching_service,
    privacy_service,
    profile_service,
    project_service,
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


@router.get("/auth/discord/login")
async def discord_login() -> RedirectResponse:
    """Starts the real Discord OAuth2 flow. Returns 503 (not a fake success)
    if DISCORD_CLIENT_ID/SECRET aren't configured — see core/config.py."""
    settings = get_settings()
    state = jwt.encode({"exp": time.time() + 600}, settings.secret_key, algorithm=settings.algorithm)
    return RedirectResponse(discord_authorize_url(state))


@router.get("/auth/discord/callback")
async def discord_callback(code: str, state: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    settings = get_settings()
    try:
        jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state") from e

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
    q: Optional[str] = Query(None, min_length=2),
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


# ─────────────────────────────────── Neurotypes ───────────────────────────────────


@router.get("/neurotypes", response_model=Dict[str, Any])
async def get_neurotypes() -> Dict[str, Any]:
    neurotypes = {}
    for neurotype in Neurotype:
        neurotypes[neurotype.value] = {
            "id": neurotype.value,
            "name": neurotype.name,
            "description": _neurotype_description(neurotype),
        }
    return {"neurotypes": neurotypes}


def _neurotype_description(neurotype: Neurotype) -> str:
    descriptions = {
        Neurotype.SEEDCASTER: "They plant what others haven't imagined yet.",
        Neurotype.FABRICANT: "If it doesn't exist, they build it.",
        Neurotype.MYCELIAN: "They think in networks and grow in the dark.",
        Neurotype.TERRAFORMER: "They redesign the spaces we inhabit.",
        Neurotype.DEVELOPER: "They write the tools of sovereignty.",
        Neurotype.ARTISAN: "They make the future beautiful enough to want.",
        Neurotype.CHRONICLER: "They make sure the work gets seen.",
        Neurotype.CULTIVAR: "They bridge the lab and the land.",
        Neurotype.LOOMKEEPER: "They hold the network together.",
        Neurotype.VERDANT: "They change the rules of the game.",
    }
    return descriptions.get(neurotype, "Unknown neurotype")
