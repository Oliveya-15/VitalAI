from sqlalchemy.orm import Session

from app.models import ActivityLog, User


def log(db: Session, user: User, type_: str, title: str, detail: dict | None = None, ref_id: int | None = None) -> None:
    db.add(ActivityLog(user_id=user.id, type=type_, title=title[:160], detail=detail, ref_id=ref_id))
    db.commit()
