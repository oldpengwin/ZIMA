"""
Authentication: real Discord OAuth2 (authorization-code flow) + JWT session
tokens.

Fixes from the old src/api/routes.py:
  - TokenData was a bare class with only class-level type annotations and no
    __init__, but every call site instantiated it with kwargs
    (TokenData(discord_id=..., username=...)) — that raised TypeError on
    every real (non-mocked) authenticated request. It's a dataclass now.
  - Login was entirely mocked (always checked the password against a hash
    of the literal string "mock_password"). Real login is now Discord
    OAuth2: /api/v1/auth/discord/login redirects to Discord,
    /api/v1/auth/discord/callback exchanges the code, fetches the Discord
    user, upserts a profile, and issues our own JWT.
  - SECRET_KEY is no longer hardcoded in this file — see core/config.py.

A `dev-token` backdoor endpoint still exists for local development and
tests (issuing a real JWT for any discord_id, no password), but it is
hard-disabled whenever ENVIRONMENT=production (see config.Settings) so it
can never ship live.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from src.core.config import get_settings

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/dev-token", auto_error=False)

DISCORD_API_BASE = "https://discord.com/api/v10"


@dataclass
class TokenData:
    discord_id: str
    username: str


def create_access_token(discord_id: str, username: str, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": discord_id, "username": username, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> TokenData:
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as e:
        raise credentials_exception from e

    discord_id = payload.get("sub")
    username = payload.get("username")
    if discord_id is None or username is None:
        raise credentials_exception
    return TokenData(discord_id=discord_id, username=username)


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> TokenData:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(token)


def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Authorization gate for admin-only endpoints. A caller is an admin iff
    their Discord id is listed in ADMIN_DISCORD_IDS (see core/config.py). An
    empty list means nobody is an admin — fail-closed — so a missing config
    denies everyone rather than leaving admin actions open to any logged-in user."""
    settings = get_settings()
    if current_user.discord_id not in settings.admin_discord_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def discord_authorize_url(state: str) -> str:
    settings = get_settings()
    if not settings.discord_oauth_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discord OAuth2 is not configured (DISCORD_CLIENT_ID/DISCORD_CLIENT_SECRET missing).",
        )
    params = {
        "client_id": settings.discord_client_id,
        "redirect_uri": settings.discord_redirect_uri,
        "response_type": "code",
        "scope": "identify",
        "state": state,
    }
    return f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"


async def exchange_discord_code(code: str) -> dict:
    """Exchanges an OAuth2 authorization code for a Discord user identity.
    Raises HTTPException on any failure — never returns a fabricated user."""
    settings = get_settings()
    if not settings.discord_oauth_configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Discord OAuth2 is not configured.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            f"{DISCORD_API_BASE}/oauth2/token",
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.discord_redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            logger.warning("Discord token exchange failed: %s %s", token_resp.status_code, token_resp.text)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Discord authorization failed")

        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Discord did not return an access token")

        user_resp = await client.get(
            f"{DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_resp.status_code != 200:
            logger.warning("Discord user fetch failed: %s %s", user_resp.status_code, user_resp.text)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to fetch Discord identity")

        return user_resp.json()
