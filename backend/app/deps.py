from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db import get_db
from app.models import User


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Please sign in to continue.", headers={"WWW-Authenticate": "Bearer"})
    uid = decode_token(authorization.split(" ", 1)[1].strip())
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(401, "Your session has expired. Please sign in again.", headers={"WWW-Authenticate": "Bearer"})
    return user
