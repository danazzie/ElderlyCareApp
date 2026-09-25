"""Shared care plan (approved items only) + the Today home-screen aggregate."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (Appointment, AuditEvent, CareCircle, CareUpdate, Document,
                      Medication, Task, User)
from ..security import current_user, require_membership

router = APIRouter(tags=["plan"])


@router.get("/circles/{circle_id}/plan")
def get_plan(circle_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)
    meds = db.query(Medication).filter(Medication.circle_id == circle_id,
                                       Medication.active.is_(True)).order_by(Medication.name).all()
    appts = db.query(Appointment).filter(Appointment.circle_id == circle_id) \
        .order_by(Appointment.when_text).all()
    tasks = db.query(Task).filter(Task.circle_id == circle_id).order_by(Task.created_at.desc()).all()
    return {
        "medications": [{"id": m.id, "name": m.name, "dose": m.dose_text, "schedule": m.schedule_text,
                         "source_item_id": m.source_item_id} for m in meds],
        "appointments": [{"id": a.id, "when": a.when_text, "where": a.where_text, "what": a.what,
                          "with_whom": a.with_whom, "status": a.status} for a in appts],
        "tasks": [{"id": t.id, "title": t.title, "due": t.due_text, "status": t.status,
                   "assignee": t.assignee_user_id, "source": t.source} for t in tasks],
    }


class TaskIn(BaseModel):
    title: str
    due: str = ""
    assignee_user_id: str | None = None


@router.post("/circles/{circle_id}/tasks")
def create_task(circle_id: str, data: TaskIn, user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)
    task = Task(circle_id=circle_id, title=data.title, due_text=data.due,
                assignee_user_id=data.assignee_user_id, source="manual")
    db.add(task)
    db.commit()
    return {"id": task.id, "title": task.title, "due": task.due_text, "status": task.status}


@router.post("/tasks/{task_id}/toggle")
def toggle_task(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    require_membership(db, user, task.circle_id)
    task.status = "done" if task.status == "open" else "open"
    db.add(AuditEvent(circle_id=task.circle_id, actor_user_id=user.id,
                      action=f"task_{task.status}", entity=f"task:{task.id}",
                      detail={"title": task.title}))
    db.commit()
    return {"id": task.id, "status": task.status}


@router.get("/circles/{circle_id}/today")
def today(circle_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)
    circle = db.get(CareCircle, circle_id)
    approvals = db.query(Document).filter(Document.circle_id == circle_id,
                                          Document.status.in_(["needs_review", "needs_clarification"])).all()
    latest_update = (db.query(CareUpdate).filter(CareUpdate.circle_id == circle_id,
                                                 CareUpdate.status == "confirmed")
                     .order_by(CareUpdate.created_at.desc()).first())
    next_appt = (db.query(Appointment).filter(Appointment.circle_id == circle_id,
                                              Appointment.status != "done")
                 .order_by(Appointment.when_text).first())
    open_tasks = db.query(Task).filter(Task.circle_id == circle_id, Task.status == "open").count()
    meds = db.query(Medication).filter(Medication.circle_id == circle_id,
                                       Medication.active.is_(True)).all()
    red_flag_updates = (db.query(CareUpdate).filter(CareUpdate.circle_id == circle_id,
                                                    CareUpdate.status == "confirmed")
                        .order_by(CareUpdate.created_at.desc()).limit(10).all())
    alerts = [f for u in red_flag_updates for f in (u.red_flags or [])][:3]
    return {
        "recipient_name": circle.recipient_name,
        "approvals_waiting": [{"id": d.id, "filename": d.filename, "doc_type": d.doc_type,
                               "status": d.status, "summary": d.summary} for d in approvals],
        "latest_update": ({"id": latest_update.id, "structured": latest_update.structured_json,
                           "at": latest_update.created_at.isoformat()} if latest_update else None),
        "next_appointment": ({"when": next_appt.when_text, "what": next_appt.what,
                              "where": next_appt.where_text} if next_appt else None),
        "open_tasks": open_tasks,
        "medications_count": len(meds),
        "medications": [{"name": m.name, "dose": m.dose_text, "schedule": m.schedule_text} for m in meds],
        "alerts": alerts,
    }
