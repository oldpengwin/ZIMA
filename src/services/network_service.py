"""
Archetype-network aggregate for the globe / network view.

This is a read-heavy, expensive-ish aggregate (group-by over profiles) that the
public globe polls. It is cached in-process with a TTL and invalidated when a
neurotype changes (see quiz_service), so the DB isn't hit on every poll — the
"don't make the servers churn" requirement.

Output is PUBLIC-SAFE by construction: only display_name, neurotype and the
location city ever leave here — never discord_id, bio, skills, or links. The
globe can't be turned into a scraper for identity.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.core import neurotypes as nt
from src.core.cache import TTLCache
from src.database.models import Profile

# Aggregate recomputed at most once per this window per worker (or sooner if a
# write invalidates it).
NETWORK_TTL_SECONDS = 300
# Cap on the location-point list so a large userbase can't produce an unbounded
# public payload.
MAX_LOCATION_POINTS = 1000

_cache = TTLCache(NETWORK_TTL_SECONDS)
_CACHE_KEY = "network"


def invalidate() -> None:
    _cache.invalidate(_CACHE_KEY)


def get_network(db: Session) -> dict:
    return _cache.get_or_compute(_CACHE_KEY, lambda: _compute_network(db))


def _compute_network(db: Session) -> dict:
    counts = {nid: 0 for nid in nt.NEUROTYPE_IDS}
    for neurotype, count in db.query(Profile.neurotype, func.count(Profile.id)).group_by(Profile.neurotype).all():
        if neurotype in counts:
            counts[neurotype] = int(count)

    nodes = []
    for meta in nt.all_neurotypes():
        nodes.append(
            {
                "id": meta["id"],
                "label": meta["label"],
                "emoji": meta["emoji"],
                "tagline": meta["tagline"],
                "color": meta["color"],
                "count": counts[meta["id"]],
            }
        )

    edges = [{"source": a, "target": b} for a, b in nt.edges()]

    # Public-safe location points only. Ordered newest-first, capped.
    point_rows = (
        db.query(Profile.display_name, Profile.neurotype, Profile.location)
        .filter(Profile.neurotype.isnot(None), Profile.location.isnot(None))
        .order_by(Profile.created_at.desc())
        .limit(MAX_LOCATION_POINTS)
        .all()
    )
    location_points = [
        {"display_name": display_name, "neurotype": neurotype, "location": location}
        for display_name, neurotype, location in point_rows
    ]

    return {
        "total_builders": sum(counts.values()),
        "nodes": nodes,
        "edges": edges,
        "location_points": location_points,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cache_ttl_seconds": NETWORK_TTL_SECONDS,
    }
