"""
Read-side access to RoleGrant — the table the Node.js Discord bot writes to
directly (src/db/supabase.js's recordRoleGrant, called from
src/roles/roleManager.js) every time it grants a Discord role. Until this
existed, nothing on the Python/API side ever read this table at all: the
bot's role history was written to the shared database and then never
surfaced anywhere outside it. This is the other direction of the "hooking"
gap from core/discord_client.py (Python -> Discord) — here it's
Discord-bot-writes -> Python-API-reads, using the shared database as the
integration point rather than a live call, which is the right tool for
"what roles does this person currently have" (a read of settled state) as
opposed to "make something happen on Discord right now" (which needs the
live REST call in discord_client.py)."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from src.database.models import RoleGrant


def get_role_grants_for_discord_id(db: Session, discord_id: str) -> List[RoleGrant]:
    return (
        db.query(RoleGrant)
        .filter(RoleGrant.discord_id == discord_id)
        .order_by(RoleGrant.granted_at.desc())
        .all()
    )


def record_grant(
    db: Session,
    discord_id: str,
    role_key: str,
    source: str = "system",
    metadata: Optional[dict] = None,
) -> RoleGrant:
    """Upsert a role grant (unique on discord_id + role_key), mirroring what the
    Node bot used to write to Supabase directly. Going forward the bot POSTs to
    the API instead of holding a Supabase service key — the DB write happens
    here, in one place, under the same connection pool as everything else."""
    grant = (
        db.query(RoleGrant)
        .filter(RoleGrant.discord_id == discord_id, RoleGrant.role_key == role_key)
        .one_or_none()
    )
    if grant is None:
        grant = RoleGrant(id=uuid.uuid4(), discord_id=discord_id, role_key=role_key)
        db.add(grant)
    grant.source = source
    grant.role_metadata = metadata or {}
    grant.granted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(grant)
    return grant
