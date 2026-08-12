"""
Central configuration for the ZIMA Python backend.

Single source of truth for environment configuration. Every value that used
to be hardcoded in routes.py / profile_manager.py (SECRET_KEY, DB URL, mock
auth) is read from the environment here instead, and the app fails loudly at
import time if a required production value is missing rather than silently
falling back to an insecure default.
"""

import logging
import os
import secrets
from functools import lru_cache
from typing import List

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when required configuration is missing in a non-dev environment."""


class Settings:
    """
    Loads settings from environment variables (populated from .env via
    python-dotenv in the app entrypoint). No values are guessed silently:
    anything security-sensitive that's missing in production raises;
    anything missing in development gets a loudly-logged fallback.
    """

    def __init__(self) -> None:
        self.environment: str = os.getenv("ENVIRONMENT", os.getenv("NODE_ENV", "development")).lower()
        self.is_production: bool = self.environment == "production"

        self.database_url: str = self._require_or_dev_default(
            "DATABASE_URL",
            dev_default="postgresql://zima_user:zima_password@localhost:5432/zima",
        )

        self.secret_key: str = self._secret_key()
        self.algorithm: str = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

        self.discord_client_id: str = os.getenv("DISCORD_CLIENT_ID", "")
        self.discord_client_secret: str = os.getenv("DISCORD_CLIENT_SECRET", "")
        self.discord_redirect_uri: str = os.getenv(
            "DISCORD_REDIRECT_URI", "http://localhost:8000/api/v1/auth/discord/callback"
        )
        self.discord_oauth_configured: bool = bool(self.discord_client_id and self.discord_client_secret)
        if not self.discord_oauth_configured:
            logger.warning(
                "DISCORD_CLIENT_ID/DISCORD_CLIENT_SECRET not set — real Discord OAuth2 login is "
                "disabled. /api/v1/auth/discord/login will return 503 until these are configured."
            )

        # Server-to-Discord calls (role revocation on deletion, DM notifications) —
        # distinct from the OAuth2 client id/secret above, which is only for the
        # login flow. This must be the exact same bot token the Node bot uses
        # (DISCORD_TOKEN in its .env, required by src/config.js) — both processes
        # are the same Discord Application acting through the same bot user, just
        # from two different codebases. DISCORD_BOT_TOKEN is checked first since
        # that's the more self-descriptive name for a Python-only reader, but
        # DISCORD_TOKEN is accepted too so one .env value configures both
        # processes without the person having to duplicate it under two keys.
        # See core/discord_client.py.
        self.discord_bot_token: str = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN", "")
        self.discord_server_id: str = os.getenv("DISCORD_SERVER_ID", "")
        self.discord_vetted_role_id: str = os.getenv("VETTED_ROLE_ID", "")
        self.discord_bot_configured: bool = bool(self.discord_bot_token)
        if not self.discord_bot_configured:
            logger.warning(
                "DISCORD_BOT_TOKEN not set — the backend cannot push anything back to Discord "
                "(role revocation on account deletion, DM notifications). Those calls will be "
                "skipped with a logged warning, not silently no-op'd. Set DISCORD_BOT_TOKEN "
                "(same value as the bot's DISCORD_TOKEN) to enable them."
            )

        # Dev-only password login backdoor (see core/auth.py). Never available in production.
        self.dev_auth_enabled: bool = not self.is_production
        if self.dev_auth_enabled:
            logger.warning(
                "ENVIRONMENT != 'production' — the /api/v1/auth/dev-token endpoint is ENABLED. "
                "This issues a real session JWT for any discord_id with no password check. "
                "It exists for local/dev/test use only and must never be reachable in production."
            )

        allowed_origins_raw = os.getenv(
            "ALLOWED_ORIGINS", "http://localhost,http://localhost:3000,http://localhost:8000"
        )
        self.allowed_origins: List[str] = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

        self.frontend_url: str = os.getenv("FRONTEND_URL", "")

        # Service key for the Discord bot -> API path (e.g. submitting a quiz on
        # behalf of a Discord user). Compared in constant time; if unset, the
        # bot service endpoints reject every caller (fail-closed).
        self.bot_api_key: str = os.getenv("BOT_API_KEY", "")
        if not self.bot_api_key and self.is_production:
            logger.warning(
                "BOT_API_KEY is not set — the Discord bot service endpoints "
                "(/api/v1/bot/*) will reject all callers until it is configured."
            )

    def _require_or_dev_default(self, key: str, dev_default: str) -> str:
        value = os.getenv(key)
        if value:
            return value
        if self.is_production:
            raise ConfigError(f"{key} is required in production and was not set.")
        logger.warning("%s not set — using development default (%s).", key, dev_default)
        return dev_default

    def _secret_key(self) -> str:
        value = os.getenv("SECRET_KEY")
        if value and value != "change-this-to-a-strong-random-string-in-production":
            return value
        if self.is_production:
            raise ConfigError(
                "SECRET_KEY is required in production and must not be the placeholder default."
            )
        # Dev fallback: generate a random key for this process so JWTs are at least
        # internally consistent for the life of the process, and say so loudly.
        generated = secrets.token_urlsafe(32)
        logger.warning(
            "SECRET_KEY not set (or left as the placeholder) — generated a random development "
            "key for this process. Tokens will NOT survive a restart. Set SECRET_KEY in .env."
        )
        return generated


@lru_cache
def get_settings() -> Settings:
    """Settings are cached per-process; call get_settings() wherever config is needed."""
    return Settings()
