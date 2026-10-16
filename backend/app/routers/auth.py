"""Register / login / profile / activity / account deletion."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import security
from app.db import get_db
from app.deps import get_current_user
from app.models import ActivityLog, Ambulance, AmbulanceRequest, Assessment, BloodRequest, Donor, User
from app.schemas import DeleteAccountIn, LoginIn, PasswordChangeIn, ProfileIn, RegisterIn
from app.services import activity

router = APIRouter(prefix="/auth", tags=["Auth"])


def _user(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "city": u.city,
            "blood_group": u.blood_group, "created_at": u.created_at.isoformat(),
            "last_login": u.last_login.isoformat() if u.last_login else None}


def _session(u: User) -> dict:
    return {"token": security.create_token(u.id), "user": _user(u)}


def _ip(request: Request) -> str:
    return (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "x")).split(",")[0].strip()


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    problem = security.password_problem(body.password)
    if problem:
        raise HTTPException(422, problem)
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(409, "An account with this email already exists. Try signing in.")
    u = User(name=body.name, email=body.email, phone=body.phone, password_hash=security.hash_password(body.password),
             last_login=datetime.now(timezone.utc))
    db.add(u)
    db.commit()
    db.refresh(u)
    activity.log(db, u, "account", "Created your VitalAI account")
    return _session(u)


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    key = f"{_ip(request)}|{body.email}"
    if security.login_blocked(key):
        raise HTTPException(429, "Too many failed attempts. Please wait 15 minutes and try again.")
    u = db.query(User).filter(User.email == body.email).first()
    if not u:
        security.burn_time()
    if not u or not security.verify_password(body.password, u.password_hash):
        security.login_failed(key)
        raise HTTPException(401, "Incorrect email or password.")
    security.login_ok(key)
    u.last_login = datetime.now(timezone.utc)
    db.commit()
    return _session(u)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user(user)


@router.patch("/me")
def update_me(body: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.name, user.phone, user.city, user.blood_group = body.name, body.phone, body.city, body.blood_group
    db.commit()
    activity.log(db, user, "account", "Updated your profile")
    return _user(user)


@router.post("/change-password")
def change_password(body: PasswordChangeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not security.verify_password(body.current_password, user.password_hash):
        raise HTTPException(403, "Current password is incorrect.")
    problem = security.password_problem(body.new_password)
    if problem:
        raise HTTPException(422, problem)
    user.password_hash = security.hash_password(body.new_password)
    db.commit()
    activity.log(db, user, "account", "Changed your password")
    return {"ok": True}


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    counts = dict(db.query(ActivityLog.type, func.count(ActivityLog.id)).filter(ActivityLog.user_id == user.id)
                  .group_by(ActivityLog.type).all())
    last = (db.query(Assessment).filter(Assessment.user_id == user.id).order_by(Assessment.created_at.desc()).first())
    return {
        "assessments": counts.get("diagnosis", 0),
        "blood_requests": counts.get("blood_request", 0),
        "donor_registered": counts.get("donor_registered", 0) > 0,
        "ambulance_requests": counts.get("ambulance_request", 0),
        "reports_analysed": counts.get("report_analyzed", 0),
        "last_assessment": {"disease": last.disease, "risk_level": last.risk_level,
                            "probability": last.probability, "created_at": last.created_at.isoformat()} if last else None,
    }


@router.get("/activity")
def activity_feed(limit: int = 50, type: str | None = None, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    q = db.query(ActivityLog).filter(ActivityLog.user_id == user.id)
    if type:
        q = q.filter(ActivityLog.type == type)
    rows = q.order_by(ActivityLog.created_at.desc()).limit(min(max(limit, 1), 200)).all()
    return [{"id": r.id, "type": r.type, "title": r.title, "ref_id": r.ref_id,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.delete("/me")
def delete_account(body: DeleteAccountIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Deletes the account and the personal data created through it."""
    if not security.verify_password(body.password, user.password_hash):
        raise HTTPException(403, "Password is incorrect.")
    logs = db.query(ActivityLog).filter(ActivityLog.user_id == user.id).all()

    def ids(t):
        return [l.ref_id for l in logs if l.type == t and l.ref_id]

    if ids("blood_request"):
        db.query(BloodRequest).filter(BloodRequest.id.in_(ids("blood_request"))).delete(synchronize_session=False)
    if ids("ambulance_request"):
        db.query(AmbulanceRequest).filter(AmbulanceRequest.id.in_(ids("ambulance_request"))).delete(synchronize_session=False)
    if ids("ambulance_registered"):
        db.query(Ambulance).filter(Ambulance.id.in_(ids("ambulance_registered"))).delete(synchronize_session=False)
    if ids("donor_registered"):
        db.query(Donor).filter(Donor.id.in_(ids("donor_registered"))).delete(synchronize_session=False)
    db.query(Assessment).filter(Assessment.user_id == user.id).delete(synchronize_session=False)
    db.query(ActivityLog).filter(ActivityLog.user_id == user.id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"deleted": True}
