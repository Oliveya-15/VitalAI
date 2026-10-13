"""Distance maths + Geoapify lookups for nearby hospitals / blood banks."""
from __future__ import annotations

import math
import threading
import time

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

CACHE_TTL = 600          # seconds
CACHE_MAX_ENTRIES = 512


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# Geoapify category mapping
_KINDS = {
    "hospital": "healthcare.hospital",
    "clinic": "healthcare.clinic_or_praxis",
    "pharmacy": "healthcare.pharmacy",
    "blood_bank": "healthcare.blood_donation",
}


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
                    timeout=httpx.Timeout(15.0, connect=5.0),
                    headers={"User-Agent": "VitalAI/1.0 (health coordination project)"},
                    follow_redirects=True,
                )
    return _client_instance


# --------------------------------------------------------------------------- #
# Geoapify transport
# --------------------------------------------------------------------------- #

def _query_geoapify(lat: float, lon: float, radius: int, kind: str) -> list:
    """Query Geoapify Places API."""
    api_key = getattr(settings, 'GEOAPIFY_API_KEY', '')
    if not api_key:
        logger.error("GEOAPIFY_API_KEY is missing from environment variables.")
        raise RuntimeError("Map data service is misconfigured. Please contact support.")

    category = _KINDS.get(kind, "healthcare")
    # Geoapify uses circle:lon,lat,radius
    filter_str = f"circle:{lon},{lat},{radius}"
    
    url = "https://api.geoapify.com/v2/places"
    params = {
        "categories": category,
        "filter": filter_str,
        "limit": 25,
        "apiKey": api_key,
    }

    try:
        r = _client().get(url, params=params)
        
        if r.status_code == 401:
            logger.error("Geoapify API key is invalid (401 Unauthorized).")
            raise RuntimeError("Map data service is busy right now. Please try again in a moment.")
            
        r.raise_for_status()
        return r.json().get("features", [])
        
    except httpx.TimeoutException:
        logger.error("Geoapify request timed out.")
        raise RuntimeError("Map data service is busy right now. Please try again in a moment.")
    except Exception as exc:
        logger.error("Geoapify query failed: %s", exc)
        raise RuntimeError("Map data service is busy right now. Please try again in a moment.") from exc


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def nearby(kind: str, lat: float, lon: float, radius_m: int | None = None, limit: int = 25) -> list[dict]:
    """Return places of `kind` near a point, nearest first. Uses Geoapify."""
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {list(_KINDS)}")
    
    radius = radius_m or getattr(settings, 'NEARBY_RADIUS_M', 3000)
    key = (kind, round(lat, 2), round(lon, 2), radius)

    cached = _cache.get(key)
    if cached is not None:
        return cached[:limit]

    features = _query_geoapify(lat, lon, radius, kind)

    places = []
    for f in features:
        props = f.get("properties", {})
        geom = f.get("geometry", {})
        coords = geom.get("coordinates")  # [lon, lat]
        
        if not coords or len(coords) < 2:
            continue
            
        p_lon, p_lat = coords[0], coords[1]
        
        # Extract phone from various possible fields
        phone = props.get("phone") or props.get("contact", {}).get("phone")
        
        # Build address
        address = props.get("address_line1") or props.get("address_line2") or props.get("formatted")
        
        places.append({
            "name": props.get("name") or f"Unnamed {kind.replace('_', ' ')}",
            "kind": kind,
            "lat": p_lat,
            "lon": p_lon,
            "distance_km": round(haversine_km(lat, lon, p_lat, p_lon), 2),
            "phone": phone,
            "emergency": "yes" if kind == "hospital" else "no",
            "address": address,
        })

    places.sort(key=lambda p: p["distance_km"])
    _cache.set(key, places)
    return places[:limit]