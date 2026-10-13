"""Distance maths + free OpenStreetMap (Overpass) lookups for nearby hospitals / blood banks."""
from __future__ import annotations

import math
import time

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()
_cache: dict[tuple, tuple[float, list]] = {}
CACHE_TTL = 600  # seconds


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
]


def _query_overpass(query: str) -> list:
    """Try each public Overpass server in turn; skip ones that are overloaded."""
    last = None
    for url in MIRRORS:
        try:
            r = httpx.post(url, data={"data": query}, timeout=12,
                           headers={"User-Agent": "VitalAI/1.0 (health coordination project)"})
            if r.status_code in (429, 502, 503, 504):
                last = f"{url} -> {r.status_code}"
                logger.warning("Overpass busy: %s", last)
                continue
            r.raise_for_status()
            return r.json().get("elements", [])
        except Exception as exc:
            last = exc
            logger.warning("Overpass failed on %s: %s", url, exc)
    raise RuntimeError("Map data service is busy right now. Please try again in a moment.") from None


def nearby(kind: str, lat: float, lon: float, radius_m: int | None = None, limit: int = 25) -> list[dict]:
    """Return places of `kind` near a point, nearest first. Uses OSM data (free, no key)."""
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {list(_KINDS)}")
    radius = radius_m or settings.NEARBY_RADIUS_M
    key = (kind, round(lat, 2), round(lon, 2), radius)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1][:limit]

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
    _cache[key] = (time.time(), places)
    return places[:limit]