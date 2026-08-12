"""
Tiny in-process TTL cache. Deliberately dependency-free (no Redis) so the app
stays lean and portable: read-heavy aggregates like the archetype network are
computed at most once per TTL per worker, which is exactly what "cache it so
our servers don't churn" asks for without adding infrastructure.

If you later run many API replicas and want a shared cache, swap this module's
internals for Redis behind the same get_or_compute/invalidate interface — call
sites won't change.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple


class TTLCache:
    def __init__(self, ttl_seconds: float) -> None:
        self.ttl = float(ttl_seconds)
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get_or_compute(self, key: str, compute: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            hit = self._store.get(key)
            if hit is not None and (now - hit[0]) < self.ttl:
                return hit[1]
        # Compute outside the lock so a slow computation doesn't block readers.
        value = compute()
        with self._lock:
            self._store[key] = (time.monotonic(), value)
        return value

    def invalidate(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key is None:
                self._store.clear()
            else:
                self._store.pop(key, None)
