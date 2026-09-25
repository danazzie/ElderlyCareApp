from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuditEvent, CareCircle, Membership, User, now
from ..security import current_user, require_membership

router = APIRouter(prefix="/circles", tags=["circles"])


class CircleIn(BaseModel):
    recipient_name: str
    recipient_dob: str = ""
    recipient_notes: str = ""
    consent: bool = False


class JoinIn(BaseModel):
    invite_code: str
    role: str = "member"  # member | caregiver


def _circle_out(c: CareCircle, db: Session) -> dict:
    members = (
        db.query(Membership, User).join(User, Membership.user_id == User.id)
        .filter(Membership.circle_id == c.id, Membership.status == "active").all()
    )
    return {
        "id": c.id, "recipient_name": c.recipient_name, "recipient_dob": c.recipient_dob,
        "recipient_notes": c.recipient_notes, "invite_code": c.invite_code,
        "consent_recorded_at": c.consent_recorded_at.isoformat() if c.consent_recorded_at else None,
        "members": [{"user_id": m.user_id, "name": u.name, "email": u.email, "role": m.role}
                    for m, u in members],
    }


@router.post("")
def create_circle(data: CircleIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    circle = CareCircle(recipient_name=data.recipient_name, recipient_dob=data.recipient_dob,
                        recipient_notes=data.recipient_notes, owner_user_id=user.id,
                        consent_recorded_at=now() if data.consent else None)
    db.add(circle)
    db.flush()
    db.add(Membership(user_id=user.id, circle_id=circle.id, role="owner"))
    db.add(AuditEvent(circle_id=circle.id, actor_user_id=user.id, action="circle_created",
                      entity=f"circle:{circle.id}", detail={"recipient": data.recipient_name}))
    db.commit()
    return _circle_out(circle, db)


@router.get("")
def my_circles(user: User = Depends(current_user), db: Session = Depends(get_db)):
    memberships = db.query(Membership).filter(Membership.user_id == user.id,
                                              Membership.status == "active").all()
    return [{**_circle_out(db.get(CareCircle, m.circle_id), db), "my_role": m.role} for m in memberships]


@router.post("/join")
def join_circle(data: JoinIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    circle = db.query(CareCircle).filter(CareCircle.invite_code == data.invite_code).first()
    if not circle:
        raise HTTPException(404, "Invalid invite code")
    if data.role not in ("member", "caregiver", "viewer"):
        raise HTTPException(400, "Role must be member, caregiver or viewer")
    existing = db.query(Membership).filter(Membership.circle_id == circle.id,
                                           Membership.user_id == user.id).first()
    if existing:
        return _circle_out(circle, db)
    db.add(Membership(user_id=user.id, circle_id=circle.id, role=data.role))
    db.add(AuditEvent(circle_id=circle.id, actor_user_id=user.id, action="member_joined",
                      entity=f"user:{user.id}", detail={"role": data.role}))
    db.commit()
    return _circle_out(circle, db)


@router.get("/{circle_id}")
def get_circle(circle_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = require_membership(db, user, circle_id)
    circle = db.get(CareCircle, circle_id)
    return {**_circle_out(circle, db), "my_role": m.role}


@router.get("/{circle_id}/audit")
def audit_log(circle_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)
    events = (db.query(AuditEvent, User).join(User, AuditEvent.actor_user_id == User.id)
              .filter(AuditEvent.circle_id == circle_id)
              .order_by(AuditEvent.at.desc()).limit(100).all())
    return [{"id": e.id, "action": e.action, "entity": e.entity, "detail": e.detail,
             "actor": u.name, "at": e.at.isoformat()} for e, u in events]
