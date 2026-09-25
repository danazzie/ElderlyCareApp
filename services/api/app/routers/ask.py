"""Ask Ihtama — Q&A over the approved care record (Graph C)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ai.graphs.ask_graph import ask_graph
from ..db import get_db
from ..models import Message, User
from ..security import current_user, require_membership

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

    db.add(Message(circle_id=circle_id, user_id=user.id, role="user", content=question))
    result = ask_graph.invoke({"circle_id": circle_id, "question": question, "variant": data.variant})
    answer = result.get("answer", "")
    citations = result.get("citations", [])
    route = result.get("route", "record_fact")
    msg = Message(circle_id=circle_id, user_id=user.id, role="assistant",
                  content=answer, citations_json=citations, route=route)
    db.add(msg)
    db.commit()
    return {"id": msg.id, "answer": answer, "citations": citations, "route": route,
            "variant": data.variant}


@router.get("/circles/{circle_id}/messages")
def messages(circle_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)
    rows = (db.query(Message).filter(Message.circle_id == circle_id)
            .order_by(Message.created_at.asc()).limit(200).all())
    return [{"id": m.id, "role": m.role, "content": m.content, "citations": m.citations_json,
             "route": m.route, "created_at": m.created_at.isoformat()} for m in rows]
