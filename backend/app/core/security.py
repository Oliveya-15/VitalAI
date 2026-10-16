"""Password hashing (scrypt, standard library) and JWT access tokens."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

settings = get_settings()
ALGO = "HS256"

# ---------------------------------------------------------------- passwords
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return "scrypt${}${}${}${}${}".format(_N, _R, _P, base64.b64encode(salt).decode(), base64.b64encode(h).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        calc = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc, base64.b64decode(h))
    except Exception:
        return False


_DUMMY = None


def burn_time() -> None:
    """Spend the same time as a real check so unknown emails can't be detected by response time."""
    global _DUMMY
    if _DUMMY is None:
        _DUMMY = hash_password("dummy-password-1")
    verify_password("wrong-password-1", _DUMMY)


def password_problem(pw: str) -> str | None:
    if len(pw) < 8:
        return "Password must be at least 8 characters."
    if len(pw) > 128:
        return "Password is too long (max 128 characters)."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain at least one letter and one number."
    return None


# ---------------------------------------------------------------- tokens
def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=settings.JWT_EXPIRE_DAYS)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def decode_token(token: str) -> int | None:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
        return int(data["sub"])
    except Exception:
        return None


# ---------------------------------------------------------------- brute-force guard
_fails: dict[str, deque] = defaultdict(deque)


def login_blocked(key: str) -> bool:
    q, now = _fails[key], time.time()
    while q and now - q[0] > settings.LOGIN_WINDOW_SECONDS:
        q.popleft()
    return len(q) >= settings.LOGIN_MAX_FAILS


def login_failed(key: str) -> None:
    _fails[key].append(time.time())


def login_ok(key: str) -> None:
    _fails.pop(key, None)
