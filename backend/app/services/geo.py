"""Distance maths + OpenStreetMap (Overpass) lookups for nearby hospitals / blood banks."""
from __future__ import annotations

import math
import random
import threading
import time
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# --- Overpass API Configuration ---
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
QUERY_TIMEOUT_S = 25.0
CONNECT_TIMEOUT_S = 10.0
ATTEMPTS_PER_MIRROR = 2
BACKOFF_BASE_S = 1.0
BACKOFF_MAX_S = 8.0
BACKOFF_JITTER = 0.5
RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}

CACHE_TTL = 600          # seconds
CACHE_MAX_ENTRIES = 512
RADIUS_M = 5000          # Default search radius
RESULT_LIMIT = 25

# --- OSM Tag Filters for Each Category ---
_KIND_FILTERS = {
    "hospital": [
        '["amenity"="hospital"]',
        '["healthcare"="hospital"]',
    ],
    "clinic": [
        '["amenity"="clinic"]',
        '["amenity"="doctors"]',
        '["healthcare"="clinic"]',
    ],
    "pharmacy": [
        '["amenity"="pharmacy"]',
        '["healthcare"="pharmacy"]',
    ],
    "blood_bank": [
        '["healthcare"="blood_donation"]',
        '["amenity"="blood_bank"]',
    ],
}

_DEFAULT_NAMES = {
    "hospital": "Hospital",
    "clinic": "Clinic / Doctor",
    "pharmacy": "Pharmacy",
    "blood_bank": "Blood Bank",
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------- #
# Thread-safe TTL cache
# --------------------------------------------------------------------------- #
class _TTLCache:
    def __init__(self, ttl: float, max_entries: int) -> None:
        self._ttl = ttl
        self._max = max_entries
        self._store: dict[Any, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < time.monotonic():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                now = time.monotonic()
                for k in [k for k, (exp, _) in self._store.items() if exp < now]:
                    self._store.pop(k, None)
                if len(self._store) >= self._max:
                    oldest = min(self._store, key=lambda k: self._store[k][0])
                    self._store.pop(oldest, None)
            self._store[key] = (time.monotonic() + self._ttl, value)

_cache = _TTLCache(CACHE_TTL, CACHE_MAX_ENTRIES)


# --------------------------------------------------------------------------- #
# HTTP Client
# --------------------------------------------------------------------------- #
_client_lock = threading.Lock()
_client_instance: httpx.Client | None = None

def _client() -> httpx.Client:
    global _client_instance
    if _client_instance is None:
        with _client_lock:
            if _client_instance is None:
                _client_instance = httpx.Client(
                    timeout=httpx.Timeout(QUERY_TIMEOUT_S, connect=CONNECT_TIMEOUT_S),
                    limits=httpx.Limits(max_connections=8, max_keepalive_connections=4),
                    headers={"User-Agent": "VitalAI/1.0 (health coordination project)"},
                    follow_redirects=True,
                )
    return _client_instance


# --------------------------------------------------------------------------- #
# Overpass API Transport
# --------------------------------------------------------------------------- #
def _backoff_delay(attempt: int) -> float:
    base = min(BACKOFF_MAX_S, BACKOFF_BASE_S * (2 ** (attempt - 1)))
    return base * (1.0 - BACKOFF_JITTER + random.random() * 2 * BACKOFF_JITTER)

def _post_to_overpass(query: str) -> dict[str, Any]:
    last_error: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(1, ATTEMPTS_PER_MIRROR + 1):
            try:
                resp = _client().post(endpoint, data={"data": query})
                if resp.status_code in RETRYABLE_STATUS:
                    raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
                if resp.status_code >= 400:
                    logger.error(f"Overpass rejected query on {endpoint}: {resp.text[:200]}")
                    raise RuntimeError(f"Map data service rejected the query ({resp.status_code}).")
                payload = resp.json()
                remark = str(payload.get("remark", ""))
                if "timed out" in remark.lower() or "runtime error" in remark.lower():
                    raise httpx.ReadTimeout(remark or "Overpass runtime error")
                return payload
            except RuntimeError:
                raise
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError, ValueError) as exc:
                last_error = exc
                if attempt < ATTEMPTS_PER_MIRROR:
                    time.sleep(_backoff_delay(attempt))
        logger.warning("Overpass mirror exhausted, failing over: %s", endpoint)
    raise RuntimeError("Map data service is busy right now. Please try again in a moment.") from last_error


# --------------------------------------------------------------------------- #
# Query Construction and Parsing
# --------------------------------------------------------------------------- #
def _build_query(kind: str, lat: float, lon: float) -> str:
    filters = _KIND_FILTERS.get(kind)
    if not filters:
        raise ValueError(f"Unsupported facility kind: {kind!r}")
    union = "\n".join(f"  nwr{f}(around:{RADIUS_M},{lat},{lon});" for f in filters)
    return f"[out:json][timeout:{int(QUERY_TIMEOUT_S)}];\n(\n{union}\n);\nout center;"

def _address_from_tags(tags: dict[str, str]) -> str | None:
    parts = [
        tags.get("addr:housenumber"), tags.get("addr:street"),
        tags.get("addr:suburb") or tags.get("addr:neighbourhood"),
        tags.get("addr:city"), tags.get("addr:postcode"),
    ]
    joined = ", ".join(p for p in parts if p)
    return joined or None

def _parse_element(el: dict[str, Any], kind: str) -> dict[str, Any] | None:
    tags: dict[str, str] = el.get("tags") or {}
    lat = el.get("lat")
    lon = el.get("lon")
    if lat is None or lon is None:
        center = el.get("center") or {}
        lat, lon = center.get("lat"), center.get("lon")
    if lat is None or lon is None:
        return None
    name = tags.get("name") or tags.get("name:en") or tags.get("operator") or _DEFAULT_NAMES.get(kind, "Medical facility")
    phone = tags.get("phone") or tags.get("contact:phone") or tags.get("emergency:phone")
    is_emergency = tags.get("emergency") == "yes" or tags.get("amenity") == "hospital" or tags.get("healthcare") == "hospital"
    return {
        "id": f"{el.get('type', 'node')}/{el.get('id')}",
        "name": name,
        "lat": lat,
        "lon": lon,
        "kind": kind,
        "phone": phone,
        "address": _address_from_tags(tags),
        "emergency": "yes" if is_emergency else "no",
    }


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def nearby(kind: str, lat: float, lon: float, radius_m: int | None = None, limit: int = RESULT_LIMIT) -> list[dict]:
    """Return places of `kind` near a point, sorted by distance, using OSM Overpass API."""
    if kind not in _KIND_FILTERS:
        raise ValueError(f"kind must be one of {list(_KIND_FILTERS)}")

    radius = radius_m or RADIUS_M
    key = (kind, round(lat, 2), round(lon, 2), radius)

    cached = _cache.get(key)
    if cached is not None:
        return cached[:limit]

    query = _build_query(kind, lat, lon)
    payload = _post_to_overpass(query)

    places = []
    for raw in payload.get("elements", []):
        parsed = _parse_element(raw, kind)
        if parsed:
            distance = haversine_km(lat, lon, parsed["lat"], parsed["lon"])
            if distance <= (radius / 1000):
                parsed["distance_km"] = round(distance, 2)
                places.append(parsed)

    places.sort(key=lambda p: p["distance_km"])
    _cache.set(key, places)
    return places[:limit]