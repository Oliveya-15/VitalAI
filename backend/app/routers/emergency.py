import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import Ambulance, AmbulanceRequest, User
from app.schemas import AmbulanceIn, AmbulanceRequestIn, AmbulanceStatusIn, TriageIn
from app.services import activity, geo, triage

settings = get_settings()
router = APIRouter(prefix="/emergency", tags=["Emergency"])
# NOTE: /numbers and /triage stay PUBLIC on purpose - nobody should need to log in to find the
# ambulance number or check for red-flag symptoms. Everything else here requires a signed-in user.
auth = [Depends(get_current_user)]


def _admin(x_admin_key: str | None):
    if not settings.ADMIN_KEY or not x_admin_key or not secrets.compare_digest(x_admin_key, settings.ADMIN_KEY):
        raise HTTPException(403, "Admin key required")


@router.get("/numbers")
def numbers():
    return settings.EMERGENCY_NUMBERS


@router.post("/triage")
def run_triage(body: TriageIn):
    return triage.triage(body.text)


@router.get("/nearby", dependencies=auth)
def nearby(kind: str, lat: float, lon: float, radius_m: int = 5000):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(422, "Invalid coordinates")
    try:
        return geo.nearby(kind, lat, lon, min(max(radius_m, 500), 15000))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))


def _amb(a: Ambulance, lat=None, lon=None) -> dict:
    out = {"id": a.id, "operator": a.operator, "phone": a.phone, "vehicle_type": a.vehicle_type,
           "city": a.city, "lat": a.lat, "lon": a.lon, "available": a.available, "verified": a.verified}
    if lat is not None:
        out["distance_km"] = round(geo.haversine_km(lat, lon, a.lat, a.lon), 1)
    return out


@router.post("/ambulances", status_code=201)
def register_ambulance(body: AmbulanceIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Providers self-register; they only appear to the public after an admin verifies them."""
    a = Ambulance(**body.model_dump())
    db.add(a)
    db.commit()
    activity.log(db, user, "ambulance_registered", f"Registered ambulance '{a.operator}' for verification", None, a.id)
    return {"id": a.id, "verified": False, "message": "Submitted. It will be listed after verification."}


@router.get("/ambulances", dependencies=auth)
def list_ambulances(lat: float | None = None, lon: float | None = None, db: Session = Depends(get_db)):
    rows = db.query(Ambulance).filter(Ambulance.verified.is_(True), Ambulance.available.is_(True)).all()
    out = [_amb(a, lat, lon) for a in rows]
    if lat is not None:
        out.sort(key=lambda x: x["distance_km"])
    return out[:30]


@router.post("/admin/ambulances/{aid}/verify")
def verify(aid: int, db: Session = Depends(get_db), x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    a = db.get(Ambulance, aid)
    if not a:
        raise HTTPException(404, "Not found")
    a.verified = True
    db.commit()
    return _amb(a)


@router.get("/admin/ambulances/pending")
def pending(db: Session = Depends(get_db), x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    return [_amb(a) for a in db.query(Ambulance).filter(Ambulance.verified.is_(False)).all()]


@router.post("/ambulance-requests", status_code=201)
def request_ambulance(body: AmbulanceRequestIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = AmbulanceRequest(**body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    activity.log(db, user, "ambulance_request", f"Requested an ambulance: {r.emergency_type} ({r.severity})", None, r.id)
    nearest = db.query(Ambulance).filter(Ambulance.verified.is_(True), Ambulance.available.is_(True)).all()
    suggestions = sorted((_amb(a, r.lat, r.lon) for a in nearest), key=lambda x: x["distance_km"])[:3]
    return {
        "id": r.id, "status": r.status, "suggested_ambulances": suggestions,
        "warning": (f"This platform coordinates help but cannot guarantee a response. "
                    f"For a life-threatening emergency call {settings.EMERGENCY_NUMBERS['ambulance']} now."),
    }


@router.get("/ambulance-requests/{rid}", dependencies=auth)
def get_request(rid: int, phone: str, db: Session = Depends(get_db)):
    r = db.get(AmbulanceRequest, rid)
    if not r or r.phone != phone.replace(" ", ""):
        raise HTTPException(404, "Request not found")
    amb = db.get(Ambulance, r.ambulance_id) if r.ambulance_id else None
    return {"id": r.id, "status": r.status, "emergency_type": r.emergency_type, "severity": r.severity,
            "ambulance": _amb(amb) if amb else None, "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat()}


@router.patch("/ambulance-requests/{rid}/status")
def update_request(rid: int, body: AmbulanceStatusIn, db: Session = Depends(get_db),
                   x_admin_key: str | None = Header(default=None)):
    _admin(x_admin_key)
    r = db.get(AmbulanceRequest, rid)
    if not r:
        raise HTTPException(404, "Not found")
    r.status = body.status
    if body.ambulance_id is not None:
        r.ambulance_id = body.ambulance_id
    db.commit()
    return {"id": r.id, "status": r.status, "ambulance_id": r.ambulance_id}
