"""
Tests for src/core/discord_client.py — the Python-backend-to-Discord push
calls. Runs with no DISCORD_BOT_TOKEN configured (this repo's dev/test
.env doesn't set one), which exercises the actual, common "not configured"
path: every call must degrade to a logged warning and a clean `False`
return, never an exception that could take down whatever it's attached to.

HTTP behavior against a real Discord API is deliberately not covered here
(that would mean either hitting the live Discord API from CI or mocking
httpx deeply enough that the test proves nothing) — see
test_api_routes.py's deletion/connection tests for how the *call sites*
(privacy_service-adjacent routes) are verified via monkeypatching this
module's functions directly.
"""

import asyncio

from src.core import discord_client


def test_remove_guild_member_role_without_token_is_a_safe_noop():
    result = asyncio.run(discord_client.remove_guild_member_role("123456789", "987654321", reason="test"))
    assert result is False


def test_send_dm_without_token_is_a_safe_noop():
    result = asyncio.run(discord_client.send_dm("123456789", "hello"))
    assert result is False
