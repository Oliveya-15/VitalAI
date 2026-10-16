from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import ActivityLog, BloodRequest, Donor, User
from app.schemas import BloodRequestIn, DonorIn, OptOutIn, StatusIn
from app.services import activity
from app.services import blood_service as bs

router = APIRouter(prefix="/blood", tags=["Blood Network"], dependencies=[Depends(get_current_user)])


def _owns_donor(db: Session, user: User, donor: Donor) -> bool:
    """A donor record belongs to the user who registered it, or to the user whose profile phone matches."""
    if user.phone and user.phone == donor.phone:
        return True
    return db.query(ActivityLog).filter(ActivityLog.user_id == user.id, ActivityLog.type == "donor_registered",
                                        ActivityLog.ref_id == donor.id).first() is not None


@router.get("/compatibility")
def compatibility():
    return {"groups": bs.GROUPS, "can_receive_from": bs.RBC_COMPATIBLE_DONORS}


@router.post("/donors", status_code=201)
def register_donor(body: DonorIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    existing = db.query(Donor).filter(Donor.phone == body.phone).first()
    data = body.model_dump()
    if existing:
        if not _owns_donor(db, user, existing):
            raise HTTPException(409, "This phone number is already registered as a donor by another account.")
        for k, v in data.items():
            setattr(existing, k, v)
        existing.available = True
        db.commit()
        activity.log(db, user, "donor_registered", f"Updated your donor profile ({existing.blood_group})", None, existing.id)
        return {"id": existing.id, "updated": True}
    d = Donor(**data)
    db.add(d)
    db.commit()
    activity.log(db, user, "donor_registered", f"Registered as a blood donor ({d.blood_group}, {d.city})", None, d.id)
    return {"id": d.id, "updated": False}


@router.post("/donors/opt-out")
def opt_out(body: OptOutIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Removes a donor record - only if it is yours (registered by you or matching your profile phone)."""
    d = db.query(Donor).filter(Donor.phone == body.phone).first()
    if not d:
        return {"removed": 0}
    if not _owns_donor(db, user, d):
        raise HTTPException(403, "You can only remove a donor profile that you registered.")
    db.delete(d)
    db.commit()
    activity.log(db, user, "donor_removed", "Removed your donor profile")
    return {"removed": 1}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    donors = dict(db.query(Donor.blood_group, func.count(Donor.id)).group_by(Donor.blood_group).all())
    open_req = dict(db.query(BloodRequest.blood_group, func.count(BloodRequest.id))
                    .filter(BloodRequest.status == "open").group_by(BloodRequest.blood_group).all())
    return {
        "total_donors": sum(donors.values()),
        "open_requests": sum(open_req.values()),
        "by_group": [{"group": g, "donors": donors.get(g, 0), "open_requests": open_req.get(g, 0)} for g in bs.GROUPS],
    }


def _public(r: BloodRequest) -> dict:
    return {"id": r.id, "patient_name": r.patient_name, "blood_group": r.blood_group, "units": r.units,
            "hospital": r.hospital, "city": r.city, "urgency": r.urgency, "status": r.status, "note": r.note,
            "contact_phone": r.contact_phone, "lat": r.lat, "lon": r.lon, "created_at": r.created_at.isoformat()}


@router.post("/requests", status_code=201)
def create_request(body: BloodRequestIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = BloodRequest(**body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    activity.log(db, user, "blood_request",
                 f"Requested {r.units} unit(s) of {r.blood_group} blood at {r.hospital} ({r.urgency})", None, r.id)
    return {"request": _public(r), "matches": bs.match_donors(db, r)}


@router.get("/requests")
def list_requests(city: str | None = None, blood_group: str | None = None, db: Session = Depends(get_db)):
    q = db.query(BloodRequest).filter(BloodRequest.status == "open")
    if city:
        q = q.filter(func.lower(BloodRequest.city) == city.strip().lower())
    if blood_group:
        q = q.filter(BloodRequest.blood_group == blood_group)
    order = {"critical": 0, "urgent": 1, "normal": 2}
    rows = q.order_by(BloodRequest.created_at.desc()).limit(100).all()
    rows.sort(key=lambda r: order.get(r.urgency, 3))
    return [_public(r) for r in rows]


@router.get("/requests/{rid}/matches")
def matches(rid: int, db: Session = Depends(get_db)):
    r = db.get(BloodRequest, rid)
    if not r:
        raise HTTPException(404, "Request not found")
    return bs.match_donors(db, r)


@router.patch("/requests/{rid}/status")
def set_status(rid: int, body: StatusIn, contact_phone: str, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    """Only the person who created the request (same phone number) may close it."""
    r = db.get(BloodRequest, rid)
    if not r:
        raise HTTPException(404, "Request not found")
    if contact_phone.replace(" ", "") != r.contact_phone:
        raise HTTPException(403, "Phone number does not match the request creator.")
    r.status = body.status
    db.commit()
    activity.log(db, user, "blood_request_closed", f"Marked blood request #{r.id} as {body.status}", None, r.id)
    return _public(r)


@router.post("/donors/{donor_id}/mark-donated")
def mark_donated(donor_id: int, db: Session = Depends(get_db)):
    d = db.get(Donor, donor_id)
    if not d:
        raise HTTPException(404, "Donor not found")
    d.last_donated = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}
