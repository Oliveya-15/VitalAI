"""Blood-group compatibility and donor ranking."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import BloodRequest, Donor
from app.services.geo import haversine_km

settings = get_settings()
GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]

# recipient -> donor groups whose RED CELLS they can safely receive
RBC_COMPATIBLE_DONORS = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": GROUPS[:],
}


def is_eligible(d: Donor, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if not d.available or not d.consent:
        return False
    if d.last_donated is None:
        return True
    last = d.last_donated if d.last_donated.tzinfo else d.last_donated.replace(tzinfo=timezone.utc)
    return now - last >= timedelta(days=settings.DONOR_REST_DAYS)


def mask_phone(p: str) -> str:
    return p[:2] + "*" * max(len(p) - 5, 2) + p[-3:] if len(p) > 5 else "***"


def match_donors(db: Session, req: BloodRequest, limit: int = 20) -> list[dict]:
    allowed = RBC_COMPATIBLE_DONORS.get(req.blood_group, [req.blood_group])
    donors = db.query(Donor).filter(Donor.blood_group.in_(allowed), Donor.available.is_(True)).all()
    out = []
    for d in donors:
        if not is_eligible(d):
            continue
        dist = None
        if None not in (req.lat, req.lon, d.lat, d.lon):
            dist = haversine_km(req.lat, req.lon, d.lat, d.lon)
        same_city = d.city.strip().lower() == req.city.strip().lower()
        if dist is None and not same_city:
            continue
        # lower score = better. Exact group match and closeness win.
        score = (0 if d.blood_group == req.blood_group else 5) + (dist if dist is not None else 15)
        out.append(
            {
                "donor_id": d.id,
                "name": d.name,
                "blood_group": d.blood_group,
                "exact_match": d.blood_group == req.blood_group,
                "city": d.city,
                "distance_km": round(dist, 1) if dist is not None else None,
                "phone": d.phone,
                "_score": score,
            }
        )
    out.sort(key=lambda x: x["_score"])
    for o in out:
        o.pop("_score")
    return out[:limit]
