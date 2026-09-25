from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import CareCircle, Membership, User
from ..security import create_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _user_out(user: User, db: Session) -> dict:
    memberships = db.query(Membership).filter(Membership.user_id == user.id).all()
    pending = []
    for m in memberships:
        if m.status != "pending":
            continue
        circle = db.get(CareCircle, m.circle_id)
        pending.append({
            "circle_id": m.circle_id, "role": m.role, "status": "pending",
            "recipient_name": circle.recipient_name if circle else "",
        })
    return {
        "id": user.id, "email": user.email, "name": user.name, "locale": user.locale,
        "memberships": [{"circle_id": m.circle_id, "role": m.role, "status": m.status}
                        for m in memberships if m.status == "active"],
        "pending_joins": pending,
    }


@router.post("/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(409, "Email already registered")
    user = User(email=data.email.lower(), name=data.name, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    return {"token": create_token(user.id), "user": _user_out(user, db)}


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"token": create_token(user.id), "user": _user_out(user, db)}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _user_out(user, db)
