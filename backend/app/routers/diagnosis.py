from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Assessment, User
from app.schemas import PredictIn
from app.services import activity, ml_service

router = APIRouter(prefix="/diagnosis", tags=["Diagnosis"], dependencies=[Depends(get_current_user)])


@router.get("/models")
def models():
    return ml_service.list_models()


@router.get("/{disease}/schema")
def schema(disease: str):
    try:
        meta = ml_service.get_meta(disease)
    except KeyError:
        raise HTTPException(404, "Unknown disease module")
    return {k: meta[k] for k in ("key", "title", "features", "best_model", "metrics", "leaderboard", "n_samples")}


@router.post("/{disease}/predict")
def predict(disease: str, body: PredictIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        meta = ml_service.get_meta(disease)
    except KeyError:
        raise HTTPException(404, "Unknown disease module")
    # range sanity check (allow 3x the observed training span to catch typos, not real outliers)
    for f in meta["features"]:
        v = body.values.get(f["name"])
        if v is None:
            raise HTTPException(422, f"Missing field: {f['label']}")
        span = max(f["max"] - f["min"], 1e-9)
        if v < f["min"] - 3 * span or v > f["max"] + 3 * span:
            raise HTTPException(422, f"{f['label']} = {v} looks unrealistic. Please re-check the value.")
    try:
        result = ml_service.predict(disease, body.values)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    row = Assessment(user_id=user.id, client_id=f"user:{user.id}", disease=disease, inputs=body.values,
                     probability=result["probability"], risk_level=result["risk_level"], model_name=result["model"])
    db.add(row)
    db.commit()
    activity.log(db, user, "diagnosis",
                 f"{result['title']} screening: {result['risk_level']} risk ({round(result['probability'] * 100)}%)",
                 {"disease": disease, "risk_level": result["risk_level"]}, row.id)
    return result


@router.get("/history")
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(Assessment).filter(Assessment.user_id == user.id)
            .order_by(Assessment.created_at.desc()).limit(100).all())
    return [{"id": r.id, "disease": r.disease, "probability": r.probability, "risk_level": r.risk_level,
             "model": r.model_name, "created_at": r.created_at.isoformat()} for r in rows]


@router.delete("/history")
def clear_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Assessment).filter(Assessment.user_id == user.id).delete()
    db.commit()
    activity.log(db, user, "account", "Cleared your screening history")
    return {"ok": True}
