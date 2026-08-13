"""
Server-to-Discord push calls from the Python backend.

Until this module existed, the Node.js bot and the Python backend only
agreed on a database schema — neither could ever cause an effect in the
other's world. The bot writes profiles/role_grants directly to Postgres
(src/db/supabase.js) and the Python API reads/writes the same tables, so
DB-level state was always in sync, but nothing the *web app* did (accept a
connection, delete an account) could ever reach Discord itself, because the
FastAPI process isn't a Discord gateway client — it has no open socket to
push through. The bot's gateway connection is the only thing with a socket;
the Python backend has to reach Discord the same way any third-party
integration would: authenticated REST calls with the bot token.

This is deliberately narrow and one-directional (Python -> Discord REST),
not an attempt to reimplement the bot's gateway responsibilities:
  - Role grants during onboarding stay exactly as they are — the Node bot
    keeps doing that over the gateway, because it's already there when the
    modal is submitted.
  - What's new here is the reverse case the bot categorically cannot do:
    react to something that happened over on the web/API side. The Node bot
    is a Discord gateway client with no HTTP listener of its own — the only
    way it currently learns about API-side changes is by polling the shared
    DB. Two examples wired via this module (see services/privacy_service.py
    and api/routes.py): a Discord role granted during onboarding must be
    revoked when the account behind it is deleted (nothing currently did
    this — a deleted user could keep the "Vetted" role forever), and a
    connection request/acceptance that happens on the web app is invisible
    to the recipient until they think to check it, unless something DMs
    them.

Every call here is best-effort by design: a role-revoke or DM failing must
never block or roll back the database operation it's attached to (a failed
Discord call is not a reason to fail an account deletion the person is
legally entitled to). Failures are logged loudly (never silently swallowed)
so they're visible in ops, not treated as success.
"""

import logging
from typing import Optional

import httpx

from src.core.config import get_settings

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"


def _headers() -> Optional[dict]:
    settings = get_settings()
    if not settings.discord_bot_configured:
        logger.warning("Discord push call skipped — DISCORD_BOT_TOKEN not configured.")
        return None
    return {"Authorization": f"Bot {settings.discord_bot_token}"}


async def remove_guild_member_role(discord_user_id: str, role_id: str, *, reason: str) -> bool:
    """Best-effort. Returns False (and logs) on any failure — including the
    common, expected case of the user having already left the server, which
    is a 404 from Discord, not a bug here."""
    settings = get_settings()
    headers = _headers()
    if headers is None or not settings.discord_server_id or not role_id:
        if headers is not None:
            logger.warning(
                "remove_guild_member_role skipped for user=%s role=%s — DISCORD_SERVER_ID or the "
                "role id is not configured.", discord_user_id, role_id,
            )
        return False

    url = f"{DISCORD_API_BASE}/guilds/{settings.discord_server_id}/members/{discord_user_id}/roles/{role_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, headers={**headers, "X-Audit-Log-Reason": reason})
        if resp.status_code in (204, 404):
            # 404 covers both "member already left the server" and "role already
            # off them" — either way there's nothing left to revoke, not a failure.
            return True
        logger.warning(
            "Discord role revoke failed for user=%s role=%s: HTTP %s %s",
            discord_user_id, role_id, resp.status_code, resp.text[:300],
        )
        return False
    except httpx.HTTPError as e:
        logger.warning("Discord role revoke request failed for user=%s role=%s: %s", discord_user_id, role_id, e)
        return False


async def add_guild_member_role(discord_user_id: str, role_id: str, *, reason: str) -> bool:
    """Best-effort role GRANT — the symmetric partner of remove_guild_member_role,
    used to apply an XP tier role the moment a builder crosses a level threshold
    (see services/xp_service.py) instead of waiting for the bot to notice. Returns
    False (and logs) on any failure; a 204 (applied) or 404 (member not in the
    guild yet) is treated as done, not an error, exactly like the revoke path."""
    settings = get_settings()
    headers = _headers()
    if headers is None or not settings.discord_server_id or not role_id:
        if headers is not None:
            logger.warning(
                "add_guild_member_role skipped for user=%s role=%s — DISCORD_SERVER_ID or the "
                "role id is not configured.", discord_user_id, role_id,
            )
        return False

    url = f"{DISCORD_API_BASE}/guilds/{settings.discord_server_id}/members/{discord_user_id}/roles/{role_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(url, headers={**headers, "X-Audit-Log-Reason": reason})
        if resp.status_code in (204, 404):
            return True
        logger.warning(
            "Discord role grant failed for user=%s role=%s: HTTP %s %s",
            discord_user_id, role_id, resp.status_code, resp.text[:300],
        )
        return False
    except httpx.HTTPError as e:
        logger.warning("Discord role grant request failed for user=%s role=%s: %s", discord_user_id, role_id, e)
        return False


async def send_dm(discord_user_id: str, content: str) -> bool:
    """Best-effort DM. Discord requires opening/reusing a DM channel first,
    then posting to it — two calls, both logged (not raised) on failure,
    since the common failure mode (the user has DMs from server members
    disabled) is expected and not actionable."""
    headers = _headers()
    if headers is None:
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            channel_resp = await client.post(
                f"{DISCORD_API_BASE}/users/@me/channels", headers=headers, json={"recipient_id": discord_user_id}
            )
            if channel_resp.status_code >= 400:
                logger.warning(
                    "Could not open DM channel with user=%s: HTTP %s %s",
                    discord_user_id, channel_resp.status_code, channel_resp.text[:300],
                )
                return False
            channel_id = channel_resp.json()["id"]

            msg_resp = await client.post(
                f"{DISCORD_API_BASE}/channels/{channel_id}/messages", headers=headers, json={"content": content}
            )
            if msg_resp.status_code >= 400:
                logger.warning(
                    "Could not send DM to user=%s: HTTP %s %s",
                    discord_user_id, msg_resp.status_code, msg_resp.text[:300],
                )
                return False
            return True
    except httpx.HTTPError as e:
        logger.warning("Discord DM request failed for user=%s: %s", discord_user_id, e)
        return False
