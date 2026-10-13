"""Distance maths + free OpenStreetMap (Overpass) lookups for nearby hospitals / blood banks."""
from __future__ import annotations

import math
import random
import threading
import time

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

CACHE_TTL = 600          # seconds
CACHE_MAX_ENTRIES = 512

# Per-mirror retry policy
ATTEMPTS_PER_MIRROR = 3  # 1 initial attempt + 2 retries
BACKOFF_BASE_S = 1.0     # 1s, 2s, 4s ...
BACKOFF_MAX_S = 8.0
BACKOFF_JITTER = 0.5     # ±50%

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# kind -> Overpass selectors
_KINDS = {
    "hospital": ['nwr["amenity"="hospital"]'],
    "clinic": ['nwr["amenity"~"clinic|doctors"]'],
    "pharmacy": ['nwr["amenity"="pharmacy"]'],
    "blood_bank": ['nwr["healthcare"="blood_donation"]', 'nwr["amenity"="blood_bank"]'],
}


MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


# --------------------------------------------------------------------------- #
# Thread-safe TTL cache with a hard size cap
# --------------------------------------------------------------------------- #

class _TTLCache:
    """Small in-memory TTL cache: bounded, thread-safe, no external deps."""

    def __init__(self, ttl: float, max_entries: int) -> None:
        self._ttl = ttl
        self._max = max_entries
        self._store: dict[tuple, tuple[float, list]] = {}
        self._lock = threading.Lock()

    def get(self, key: tuple) -> list | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < time.monotonic():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: tuple, value: list) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                now = time.monotonic()
                for k in [k for k, (exp, _) in self._store.items() if exp < now]:
                    self._store.pop(k, None)
                if len(self._store) >= self._max:
                    oldest = min(self._store, key=lambda k: self._store[k][0])
                    self._store.pop(oldest, None)
            self._store[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


_cache = _TTLCache(CACHE_TTL, CACHE_MAX_ENTRIES)


# --------------------------------------------------------------------------- #
# Shared HTTP client (connection pooling)
# --------------------------------------------------------------------------- #

_client_lock = threading.Lock()
_client_instance: httpx.Client | None = None


def _client() -> httpx.Client:
    global _client_instance
    if _client_instance is None:
        with _client_lock:
            if _client_instance is None:
                _client_instance = httpx.Client(
                    timeout=httpx.Timeout(12.0, connect=5.0),
                    limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
                    headers={"User-Agent": "VitalAI/1.0 (health coordination project)"},
                    follow_redirects=True,
                )
    return _client_instance


# --------------------------------------------------------------------------- #
# Overpass transport: mirror failover + exponential backoff
# --------------------------------------------------------------------------- #

def _backoff_delay(attempt: int) -> float:
    base = min(BACKOFF_MAX_S, BACKOFF_BASE_S * (2 ** (attempt - 1)))
    return base * (1.0 - BACKOFF_JITTER + random.random() * 2 * BACKOFF_JITTER)


def _query_overpass(query: str) -> list:
    """
    Try each public Overpass server in turn.

    For every mirror we retry up to ATTEMPTS_PER_MIRROR times on transient
    failures (timeouts, 429/5xx, Overpass `remark` timeouts) using exponential
    backoff with jitter. If a mirror is exhausted we fail over to the next one.
    """
    last: object = None

    for url in MIRRORS:
        for attempt in range(1, ATTEMPTS_PER_MIRROR + 1):
            try:
                r = _client().post(url, data={"data": query})

                if r.status_code in RETRYABLE_STATUS:
                    last = f"{url} -> {r.status_code}"
                    logger.warning(
                        "Overpass busy on %s (attempt %d/%d): HTTP %s",
                        url, attempt, ATTEMPTS_PER_MIRROR, r.status_code,
                    )
                    raise httpx.HTTPStatusError(
                        f"HTTP {r.status_code}", request=r.request, response=r
                    )

                if r.status_code >= 400:
                    # Non-transient (bad query, blocked). Retrying won't help.
                    logger.error("Overpass rejected query on %s: HTTP %s", url, r.status_code)
                    raise RuntimeError(
                        f"Map data service rejected the query ({r.status_code})."
                    )

                payload = r.json()

                # Overpass answers 200 with a `remark` when it times out.
                remark = str(payload.get("remark", ""))
                if "timed out" in remark.lower() or "runtime error" in remark.lower():
                    last = f"{url} -> remark: {remark}"
                    logger.warning("Overpass remark on %s: %s", url, remark)
                    raise httpx.ReadTimeout(remark or "Overpass runtime error")

                return payload.get("elements", [])

            except RuntimeError:
                raise
            except (httpx.TimeoutException, httpx.TransportError,
                    httpx.HTTPStatusError, ValueError) as exc:
                last = exc
                if attempt < ATTEMPTS_PER_MIRROR:
                    delay = _backoff_delay(attempt)
                    logger.warning(
                        "Overpass attempt %d/%d on %s failed (%s); sleeping %.2fs",
                        attempt, ATTEMPTS_PER_MIRROR, url, exc, delay,
                    )
                    time.sleep(delay)
                else:
                    logger.warning(
                        "Overpass mirror exhausted, failing over: %s", url,
                    )

    raise RuntimeError(
        "Map data service is busy right now. Please try again in a moment."
    ) from last


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def nearby(kind: str, lat: float, lon: float, radius_m: int | None = None, limit: int = 25) -> list[dict]:
    """Return places of `kind` near a point, nearest first. Uses OSM data (free, no key)."""
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {list(_KINDS)}")
    radius = radius_m or settings.NEARBY_RADIUS_M
    # Snap to ~1.1 km grid so GPS jitter / map panning reuses cached results.
    key = (kind, round(lat, 2), round(lon, 2), radius)

    cached = _cache.get(key)
    if cached is not None:
        return cached[:limit]

    parts = "".join(f"{sel}(around:{radius},{lat},{lon});" for sel in _KINDS[kind])
    query = f"[out:json][timeout:10];({parts});out center tags 40;"

    elements = _query_overpass(query)

    places = []
    for el in elements:
        c = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
        if c.get("lat") is None:
            continue
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en") or f"Unnamed {kind.replace('_', ' ')}"
        places.append(
            {
                "name": name,
                "kind": kind,
                "lat": c["lat"],
                "lon": c["lon"],
                "distance_km": round(haversine_km(lat, lon, c["lat"], c["lon"]), 2),
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "emergency": tags.get("emergency"),
                "address": ", ".join(
                    x for x in [tags.get("addr:street"), tags.get("addr:city")] if x
                ) or None,
            }
        )
    places.sort(key=lambda p: p["distance_km"])
    _cache.set(key, places)
    return places[:limit]