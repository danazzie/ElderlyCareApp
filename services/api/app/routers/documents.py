"""Document intake + human-in-the-loop review, backed by Graph A.

Upload starts the graph in the background (extraction can take ~30s live); the
frontend polls GET /documents/{id}. The graph pauses at the human_review
interrupt; POST /documents/{id}/review resumes the same checkpointed thread."""
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ai.graphs.document_graph import document_graph
from ..config import settings
from ..db import SessionLocal, get_db
from ..models import Document, ExtractedItem, User
from ..security import current_user, require_membership

log = logging.getLogger("ihtama.documents")
router = APIRouter(tags=["documents"])

ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def _thread_config(document_id: str) -> dict:
    return {"configurable": {"thread_id": f"doc:{document_id}"}}


def _run_graph(document_id: str, circle_id: str, user_id: str, filename: str, storage_path: str):
    try:
        document_graph.invoke(
            {"document_id": document_id, "circle_id": circle_id, "user_id": user_id,
             "filename": filename, "storage_path": storage_path, "revision": 0},
            config=_thread_config(document_id),
        )
    except Exception:
        log.exception("document graph failed for %s", document_id)
        db = SessionLocal()
        try:
            doc = db.get(Document, document_id)
            if doc and doc.status in ("pending", "processing"):
                doc.status = "rejected"
                doc.reject_reason = "Processing failed — please try again."
                db.commit()
        finally:
            db.close()


@router.post("/circles/{circle_id}/documents")
def upload_document(circle_id: str, background: BackgroundTasks,
                    file: UploadFile = File(...),
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)  # any active member may upload
    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, f"Unsupported file type {suffix}. Allowed: {', '.join(sorted(ALLOWED))}")

    doc = Document(circle_id=circle_id, filename=file.filename or "upload", uploaded_by=user.id,
                   storage_path="", status="processing")
    db.add(doc)
    db.flush()
    dest = settings.upload_dir / circle_id / f"{doc.id}{suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    doc.storage_path = str(dest)
    db.commit()

    background.add_task(_run_graph, doc.id, circle_id, user.id, doc.filename, str(dest))
    return {"id": doc.id, "status": "processing"}


@router.get("/circles/{circle_id}/documents")
def list_documents(circle_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_membership(db, user, circle_id)
    docs = db.query(Document).filter(Document.circle_id == circle_id).order_by(Document.created_at.desc()).all()
    return [{"id": d.id, "filename": d.filename, "doc_type": d.doc_type, "status": d.status,
             "summary": d.summary, "reject_reason": d.reject_reason,
             "created_at": d.created_at.isoformat()} for d in docs]


def _doc_detail(doc: Document, db: Session) -> dict:
    items = db.query(ExtractedItem).filter(ExtractedItem.document_id == doc.id).all()
    review_request = None
    if doc.status in ("needs_review", "needs_clarification"):
        state = document_graph.get_state(_thread_config(doc.id))
        for task in getattr(state, "tasks", []) or []:
            for intr in getattr(task, "interrupts", []) or []:
                review_request = intr.value
    return {
        "id": doc.id, "filename": doc.filename, "doc_type": doc.doc_type, "status": doc.status,
        "summary": doc.summary, "reject_reason": doc.reject_reason, "pages": doc.pages,
        "created_at": doc.created_at.isoformat(),
        "items": [{"id": i.id, "kind": i.kind, "payload": i.payload_json, "source_page": i.source_page,
                   "source_quote": i.source_quote, "confidence": i.confidence, "flags": i.flags,
                   "review_status": i.review_status} for i in items],
        "review_request": review_request,
    }


@router.get("/documents/{document_id}")
def get_document(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    require_membership(db, user, doc.circle_id)
    return _doc_detail(doc, db)


@router.get("/documents/{document_id}/file")
def get_document_file(document_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    require_membership(db, user, doc.circle_id)
    return FileResponse(doc.storage_path, filename=doc.filename)


class ReviewIn(BaseModel):
    action: str                      # approved | edited | rejected
    items: dict[str, str] = {}       # item_id -> approved | rejected
    edits: dict[str, dict] = {}      # item_id -> {"payload": {...}} for action=edited
    reason: str = ""


@router.post("/documents/{document_id}/review")
def review_document(document_id: str, data: ReviewIn,
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    # approval power: owner and members only (caregivers upload but don't approve)
    require_membership(db, user, doc.circle_id, roles=["owner", "member"])
    if doc.status not in ("needs_review", "needs_clarification"):
        raise HTTPException(409, f"Document is not awaiting review (status={doc.status})")
    if data.action not in ("approved", "edited", "rejected"):
        raise HTTPException(400, "action must be approved, edited or rejected")

    # Resume the interrupted LangGraph thread with the human decision
    document_graph.invoke(
        Command(resume={"action": data.action, "items": data.items,
                        "edits": data.edits, "reason": data.reason, "reviewer": user.id}),
        config=_thread_config(document_id),
    )
    db.expire_all()
    doc = db.get(Document, document_id)
    return _doc_detail(doc, db)
