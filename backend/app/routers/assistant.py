import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import BMIIn, BPIn, ChatIn, ReportIn
from app.services import activity, agent, health_tools

settings = get_settings()
router = APIRouter(tags=["Assistant & Tools"], dependencies=[Depends(get_current_user)])
_hits: dict[str, deque] = defaultdict(deque)


def _rate_limit(request: Request) -> None:
    """Protects the free LLM quota: N chat calls per IP per minute."""
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "x")).split(",")[0].strip()
    q, now = _hits[ip], time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= settings.CHAT_RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Too many messages - please wait a minute.")
    q.append(now)


@router.post("/assistant/chat")
def chat(body: ChatIn, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _rate_limit(request)
    loc = {"lat": body.lat, "lon": body.lon} if body.lat is not None and body.lon is not None else None
    return agent.respond(body.message, [m.model_dump() for m in body.history], db, loc)


@router.get("/assistant/status")
def status():
    return {"llm_enabled": settings.llm_enabled, "model": settings.LLM_MODEL if settings.llm_enabled else None}


@router.post("/tools/bmi")
def bmi(body: BMIIn):
    return health_tools.bmi(body.weight_kg, body.height_cm)


@router.post("/tools/blood-pressure")
def bp(body: BPIn):
    try:
        return health_tools.blood_pressure(body.systolic, body.diastolic)
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.post("/tools/report")
def report(body: ReportIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = health_tools.analyse_report(body.text, body.sex)
    activity.log(db, user, "report_analyzed",
                 f"Analysed a lab report ({len(result['results'])} tests, {result['abnormal_count']} outside range)")
    return result
