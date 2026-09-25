"""Ask Ihtama — Q&A over the approved care record (Graph C)."""
from pathlib import Path
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ai.graphs.ask_graph import ask_graph
from ..ai.model_router import router as model_router
from ..config import settings
from ..db import get_db
from ..models import Message, User, uid
from ..security import current_user, require_membership

AUDIO_ALLOWED = {".m4a", ".mp3", ".wav", ".webm", ".ogg", ".mp4"}

router = APIRouter(tags=["ask"])


class AskIn(BaseModel):
    question: str
    variant: str = "A"  # RAG A/B variant, exposed for the experiment


@router.post("/circles/{circle_id}/ask")
def ask(circle_id: str, data: AskIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)
    question = data.question.strip()
    if not question:
        raise HTTPException(400, "Empty question")
    if data.variant not in ("A", "B"):
        raise HTTPException(400, "variant must be A or B")

    prior = (db.query(Message).filter(Message.circle_id == circle_id)
             .order_by(Message.created_at.desc()).limit(8).all())
    history = [{"role": m.role, "content": m.content} for m in reversed(prior)]

    db.add(Message(circle_id=circle_id, user_id=user.id, role="user", content=question))
    result = ask_graph.invoke({
        "circle_id": circle_id, "question": question, "variant": data.variant, "history": history,
    })
    answer = result.get("answer", "")
    citations = result.get("citations", [])
    route = result.get("route", "record_fact")
    msg = Message(circle_id=circle_id, user_id=user.id, role="assistant",
                  content=answer, citations_json=citations, route=route)
    db.add(msg)
    db.commit()
    return {"id": msg.id, "answer": answer, "citations": citations, "route": route,
            "variant": data.variant}


@router.post("/circles/{circle_id}/ask/transcribe")
def transcribe_ask(circle_id: str, audio: UploadFile = File(...),
                   user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Speech-to-text for Ask only — does not create a care-plan voice update."""
    require_membership(db, user, circle_id)
    suffix = Path(audio.filename or "ask.webm").suffix.lower()
    if suffix not in AUDIO_ALLOWED:
        raise HTTPException(400, f"Unsupported audio type {suffix}")
    original = Path(audio.filename or "ask.webm").name
    dest = settings.upload_dir / circle_id / "ask" / f"{uid()}_{original}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as out:
        shutil.copyfileobj(audio.file, out)
    try:
        text = (model_router.transcribe(str(dest)) or "").strip()
    finally:
        dest.unlink(missing_ok=True)
    if not text:
        raise HTTPException(400, "Could not transcribe that audio")
    return {"transcript": text}


@router.get("/circles/{circle_id}/messages")
def messages(circle_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)
    rows = (db.query(Message).filter(Message.circle_id == circle_id)
            .order_by(Message.created_at.asc()).limit(200).all())
    return [{"id": m.id, "role": m.role, "content": m.content, "citations": m.citations_json,
             "route": m.route, "created_at": m.created_at.isoformat()} for m in rows]


@router.delete("/circles/{circle_id}/messages")
def clear_messages(circle_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)
    deleted = db.query(Message).filter(Message.circle_id == circle_id).delete()
    db.commit()
    return {"deleted": deleted}
