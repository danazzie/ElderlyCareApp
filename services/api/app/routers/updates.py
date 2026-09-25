"""Voice care updates, backed by Graph B (transcribe -> structure -> red flags ->
caregiver confirm ? -> save)."""
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ai.graphs.voice_graph import voice_graph
from ..config import settings
from ..db import get_db
from ..models import CareUpdate, User
from ..security import current_user, require_membership

router = APIRouter(tags=["updates"])

AUDIO_ALLOWED = {".m4a", ".mp3", ".wav", ".webm", ".ogg", ".mp4"}


def _cfg(update_id: str) -> dict:
    return {"configurable": {"thread_id": f"update:{update_id}"}}


def _update_out(u: CareUpdate, db: Session, review: dict | None = None) -> dict:
    author = None
    if u.author_user_id:
        from ..models import User as U
        row = db.get(U, u.author_user_id)
        author = row.name if row else None
    return {"id": u.id, "author": author, "transcript": u.transcript, "structured": u.structured_json,
            "red_flags": u.red_flags, "status": u.status, "created_at": u.created_at.isoformat(),
            "confirm_request": review}


@router.post("/circles/{circle_id}/updates")
def create_update(circle_id: str,
                  audio: UploadFile | None = File(None),
                  text: str = Form(""),
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)
    if audio is None and not text.strip():
        raise HTTPException(400, "Provide an audio file or a text note")

    upd = CareUpdate(circle_id=circle_id, author_user_id=user.id, transcript=text.strip())
    db.add(upd)
    db.flush()
    audio_path, filename = "", ""
    if audio is not None:
        suffix = Path(audio.filename or "note.m4a").suffix.lower()
        if suffix not in AUDIO_ALLOWED:
            raise HTTPException(400, f"Unsupported audio type {suffix}")
        dest = settings.upload_dir / circle_id / "audio" / f"{upd.id}{suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as out:
            shutil.copyfileobj(audio.file, out)
        upd.audio_path = str(dest)
        audio_path, filename = str(dest), audio.filename or ""
    db.commit()

    # Runs to the caregiver_confirm interrupt and returns the draft for review
    result = voice_graph.invoke(
        {"update_id": upd.id, "circle_id": circle_id, "user_id": user.id,
         "audio_path": audio_path, "filename": filename, "transcript": text.strip()},
        config=_cfg(upd.id),
    )
    interrupts = result.get("__interrupt__", [])
    review = interrupts[0].value if interrupts else None
    db.expire_all()
    return _update_out(db.get(CareUpdate, upd.id), db, review)


class ConfirmIn(BaseModel):
    action: str                 # confirmed | discarded
    structured: dict | None = None  # optional caregiver corrections


@router.post("/updates/{update_id}/confirm")
def confirm_update(update_id: str, data: ConfirmIn,
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    upd = db.get(CareUpdate, update_id)
    if not upd:
        raise HTTPException(404, "Update not found")
    require_membership(db, user, upd.circle_id)
    if upd.author_user_id != user.id:
        raise HTTPException(403, "Only the author can confirm their update")
    if upd.status != "draft":
        raise HTTPException(409, f"Update already {upd.status}")
    if data.action not in ("confirmed", "discarded"):
        raise HTTPException(400, "action must be confirmed or discarded")

    voice_graph.invoke(Command(resume={"action": data.action, "structured": data.structured}),
                       config=_cfg(update_id))
    db.expire_all()
    return _update_out(db.get(CareUpdate, update_id), db)


@router.get("/circles/{circle_id}/updates")
def list_updates(circle_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)
    rows = (db.query(CareUpdate).filter(CareUpdate.circle_id == circle_id)
            .order_by(CareUpdate.created_at.desc()).limit(50).all())
    return [_update_out(u, db) for u in rows]
