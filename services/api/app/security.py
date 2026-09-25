"""JWT auth + role checks. Every circle-scoped endpoint resolves Membership
first — this is the per-tenant isolation boundary (also enforced in MCP tools)."""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Membership, User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = "ahtama-static-salt"  # per-user salt in production; kept simple for the course demo
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")
    try:
        payload = jwt.decode(creds.credentials, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user


def require_membership(db: Session, user: User, circle_id: str, roles: list[str] | None = None) -> Membership:
    m = (
        db.query(Membership)
        .filter(Membership.circle_id == circle_id, Membership.user_id == user.id, Membership.status == "active")
        .first()
    )
    if m is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this care circle")
    if roles and m.role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {', '.join(roles)}")
    return m
