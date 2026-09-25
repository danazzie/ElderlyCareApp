"""Graph A — Document -> approved care plan (the mandatory multi-step workflow).

ingest -> guard_document -> classify ??(non-care)??? reject -> END
                               ?
                          extract_items  (vision model + care-document-review Skill)
                               ?
                          validate_items (deterministic checks)
                               ?
                    draft_plan_diff (vs current plan)
                               ?
                        human_review ? (LangGraph interrupt)
                    ???????????????????????????
                approved      edited        rejected
                    ?       (revalidate,      ?
                    ?        loop ?3)         ?
              commit_to_plan ??? write_audit ???? END

Branching: non-care rejection, unreadable -> review in manual mode.
Loop: edited items go back through validation (bounded).
HITL: interrupt() before any write to the shared plan — nothing reaches the
care plan without a family approval. State is checkpointed in SQLite.
"""
import re
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from ...db import SessionLocal
from ...models import AuditEvent, Appointment, Document, ExtractedItem, Medication, Task
from .. import guardrails, prompts, rag
from ..model_router import parse_json, router
from .common import checkpointer


class DocState(TypedDict, total=False):
    document_id: str
    circle_id: str
    user_id: str
    filename: str
    storage_path: str
    pages_text: list[str]          # extracted text per page ([] for photos)
    is_image: bool
    doc_type: str
    is_care_document: bool
    reject_reason: str
    extraction: dict               # raw model output
    validation_issues: list[str]
    plan_diff: dict                # {new: [], changed: [], duplicates: []}
    review: dict                   # resume payload from the human
    revision: int
    status: str


# ---------------------------------------------------------------- nodes
def ingest(state: DocState) -> DocState:
    path = state["storage_path"]
    is_image = bool(re.search(r"\.(jpe?g|png|webp)$", path, re.I))
    pages: list[str] = []
    if not is_image and path.lower().endswith(".pdf"):
        from pypdf import PdfReader

        try:
            reader = PdfReader(path)
            pages = [(p.extract_text() or "") for p in reader.pages]
        except Exception:
            pages = []
    return {"pages_text": pages, "is_image": is_image}


def guard_document(state: DocState) -> DocState:
    """Documents can carry prompt injections; scan the raw text before it ever
    reaches a model prompt."""
    verdict = guardrails.check_document_text("\n".join(state.get("pages_text", [])))
    if verdict["blocked"]:
        return {"is_care_document": False, "reject_reason": f"Blocked by input guardrail: {verdict['reason']}",
                "status": "rejected"}
    return {}


def classify(state: DocState) -> DocState:
    if state.get("status") == "rejected":
        return {}
    text_sample = "\n".join(state.get("pages_text", []))[:4000]
    if state["is_image"] and not text_sample:
        user_content: Any = router.image_content("Classify this document image.", [state["storage_path"]])
    else:
        user_content = f"Document text:\n{text_sample}"
    out = router.complete("classify_document", prompts.CLASSIFY_DOCUMENT, user_content,
                          tier="fast", json_mode=True, context={"filename": state["filename"]})
    result = parse_json(out)
    return {"doc_type": result.get("doc_type", "unknown"),
            "is_care_document": bool(result.get("is_care_document")),
            "reject_reason": "" if result.get("is_care_document") else
            "This doesn't look like a care document (e.g. a bill or receipt), so nothing was added to the care plan."}


def route_after_classify(state: DocState) -> str:
    return "extract_items" if state.get("is_care_document") else "reject"


def reject(state: DocState) -> DocState:
    db = SessionLocal()
    try:
        doc = db.get(Document, state["document_id"])
        doc.status = "rejected"
        doc.doc_type = state.get("doc_type", "non_medical")
        doc.reject_reason = state.get("reject_reason", "Not a care document")
        db.add(AuditEvent(circle_id=state["circle_id"], actor_user_id=state["user_id"],
                          action="document_rejected", entity=f"document:{state['document_id']}",
                          detail={"reason": doc.reject_reason, "doc_type": doc.doc_type}))
        db.commit()
    finally:
        db.close()
    return {"status": "rejected"}


def extract_items(state: DocState) -> DocState:
    db = SessionLocal()
    try:
        meds = db.query(Medication).filter(Medication.circle_id == state["circle_id"],
                                           Medication.active.is_(True)).all()
        current = "; ".join(f"{m.name} {m.dose_text} {m.schedule_text}" for m in meds) or "none recorded yet"
    finally:
        db.close()

    system = prompts.EXTRACTION_V2.format(skill=prompts.load_skill(), current_medications=current)
    text_sample = "\n\n".join(f"[page {i+1}]\n{t}" for i, t in enumerate(state.get("pages_text", [])))[:12000]
    if state["is_image"]:
        user_content: Any = router.image_content("Extract care facts from this document image.", [state["storage_path"]])
    else:
        user_content = f"Document ({state['filename']}):\n{text_sample}"
    out = router.complete("extract_items", system, user_content, tier="extraction",
                          json_mode=True, context={"filename": state["filename"]})
    return {"extraction": parse_json(out)}


def validate_items(state: DocState) -> DocState:
    """Deterministic validation on top of the model output — trust but verify."""
    ex = state.get("extraction", {})
    issues: list[str] = list(ex.get("needs_clarification", []))
    db = SessionLocal()
    try:
        current = {m.name.strip().lower(): m for m in
                   db.query(Medication).filter(Medication.circle_id == state["circle_id"],
                                               Medication.active.is_(True)).all()}
    finally:
        db.close()

    for item in ex.get("items", []):
        payload, flags = item.get("payload", {}), item.get("flags", [])
        if item.get("kind") == "medication":
            dose = str(payload.get("dose", ""))
            if not dose or dose.upper() == "MISSING":
                if "missing_field" not in flags:
                    flags.append("missing_field")
            if dose.upper().startswith("CONFLICT") and "conflict" not in flags:
                flags.append("conflict")
            name = str(payload.get("name", "")).strip().lower()
            existing = current.get(name)
            if existing and existing.dose_text and payload.get("dose") and \
                    existing.dose_text.lower() != str(payload["dose"]).lower() and "conflict" not in flags:
                if "dose_changed" not in flags:
                    flags.append("dose_changed")
        if item.get("kind") == "appointment" and not str(payload.get("when", "")).strip():
            flags.append("missing_field")
        if not item.get("source_quote"):
            flags.append("no_source")
        item["flags"] = flags
    return {"validation_issues": issues, "extraction": ex}


def draft_plan_diff(state: DocState) -> DocState:
    """Persist draft ExtractedItems and compute the plan diff shown at review."""
    ex = state.get("extraction", {})
    db = SessionLocal()
    try:
        # replace prior drafts on re-validation loops
        db.query(ExtractedItem).filter(ExtractedItem.document_id == state["document_id"],
                                       ExtractedItem.review_status == "pending").delete()
        diff = {"new": [], "changed": [], "flagged": []}
        for item in ex.get("items", []):
            row = ExtractedItem(
                document_id=state["document_id"], circle_id=state["circle_id"],
                kind=item.get("kind", "instruction"), payload_json=item.get("payload", {}),
                source_page=int(item.get("source_page", 1) or 1),
                source_quote=item.get("source_quote", ""),
                confidence=float(item.get("confidence", 1.0) or 1.0),
                flags=item.get("flags", []),
            )
            db.add(row)
            db.flush()
            entry = {"item_id": row.id, "kind": row.kind, "payload": row.payload_json, "flags": row.flags}
            if row.flags:
                diff["flagged"].append(entry)
            elif "change" in row.payload_json or row.payload_json.get("status", "").startswith("MOVED"):
                diff["changed"].append(entry)
            else:
                diff["new"].append(entry)

        doc = db.get(Document, state["document_id"])
        has_open_questions = (not ex.get("readable", True)) or bool(state.get("validation_issues"))
        doc.status = "needs_clarification" if has_open_questions else "needs_review"
        doc.doc_type = ex.get("doc_type", doc.doc_type)
        doc.summary = ex.get("summary", "")
        db.commit()
        return {"plan_diff": diff, "status": doc.status}
    finally:
        db.close()


def human_review(state: DocState) -> DocState:
    """LangGraph interrupt: execution pauses here until a family member responds
    via POST /documents/{id}/review, which resumes the thread with the decision."""
    decision = interrupt({
        "document_id": state["document_id"],
        "summary": state.get("extraction", {}).get("summary", ""),
        "plan_diff": state.get("plan_diff", {}),
        "validation_issues": state.get("validation_issues", []),
        "readable": state.get("extraction", {}).get("readable", True),
    })
    return {"review": decision, "revision": state.get("revision", 0) + 1}


def route_after_review(state: DocState) -> str:
    action = state.get("review", {}).get("action", "rejected")
    if action == "approved":
        return "commit_to_plan"
    if action == "edited" and state.get("revision", 0) <= 3:
        return "apply_edits"
    return "reject_by_reviewer"


def apply_edits(state: DocState) -> DocState:
    """Reviewer edited items -> merge edits into extraction, then loop to validation."""
    edits: dict = state.get("review", {}).get("edits", {})
    ex = state.get("extraction", {})
    db = SessionLocal()
    try:
        rows = db.query(ExtractedItem).filter(ExtractedItem.document_id == state["document_id"],
                                              ExtractedItem.review_status == "pending").all()
        by_id = {r.id: r for r in rows}
        items = []
        for r in rows:
            payload = edits.get(r.id, {}).get("payload", r.payload_json)
            flags = [f for f in r.flags if f not in ("conflict", "missing_field")] if r.id in edits else r.flags
            items.append({"kind": r.kind, "payload": payload, "source_page": r.source_page,
                          "source_quote": r.source_quote, "confidence": r.confidence, "flags": flags})
        ex["items"] = items
        ex["needs_clarification"] = []
        db.commit()
    finally:
        db.close()
    return {"extraction": ex}


BLOCKING_FLAGS = {"conflict", "missing_field"}


def commit_to_plan(state: DocState) -> DocState:
    """Only runs after explicit human approval. Items with blocking flags stay
    pending (doc-09/doc-10 behaviour: a conflicted dose can never be approved)."""
    review = state.get("review", {})
    item_decisions: dict = review.get("items", {})  # item_id -> approved|rejected
    db = SessionLocal()
    committed, blocked = 0, 0
    try:
        rows = db.query(ExtractedItem).filter(ExtractedItem.document_id == state["document_id"],
                                              ExtractedItem.review_status == "pending").all()
        doc = db.get(Document, state["document_id"])
        for r in rows:
            decision = item_decisions.get(r.id, "approved")
            if decision == "rejected":
                r.review_status = "rejected"
                r.reviewed_by = state["user_id"]
                continue
            if BLOCKING_FLAGS & set(r.flags or []):
                blocked += 1  # stays pending until edited/clarified
                continue
            r.review_status = "approved"
            r.reviewed_by = state["user_id"]
            committed += 1
            if r.kind == "medication":
                p = r.payload_json
                name = str(p.get("name", "")).strip()
                if str(p.get("change", "")).upper() == "STOPPED":
                    for m in db.query(Medication).filter(Medication.circle_id == state["circle_id"],
                                                         Medication.active.is_(True)).all():
                        if m.name.lower() == name.lower():
                            m.active = False
                    continue
                existing = next((m for m in db.query(Medication).filter(
                    Medication.circle_id == state["circle_id"], Medication.active.is_(True)).all()
                    if m.name.lower() == name.lower()), None)
                if existing:
                    existing.dose_text = str(p.get("dose", existing.dose_text))
                    existing.schedule_text = str(p.get("frequency", existing.schedule_text))
                    existing.source_item_id = r.id
                else:
                    db.add(Medication(circle_id=state["circle_id"], name=name,
                                      dose_text=str(p.get("dose", "")),
                                      schedule_text=str(p.get("frequency", "")), source_item_id=r.id))
            elif r.kind == "appointment":
                p = r.payload_json
                when = str(p.get("when", ""))
                if p.get("amends_existing") or str(p.get("status", "")).upper().startswith("MOVED"):
                    moved_from = str(p.get("status", "")).replace("MOVED from ", "")
                    target = next((a for a in db.query(Appointment).filter(
                        Appointment.circle_id == state["circle_id"]).all()
                        if moved_from and moved_from in a.when_text), None)
                    if target:
                        target.when_text = when
                        target.status = "rescheduled"
                        target.source_item_id = r.id
                        continue
                exists = any(a.when_text == when and a.what == str(p.get("what", ""))
                             for a in db.query(Appointment).filter(Appointment.circle_id == state["circle_id"]).all())
                if not exists:
                    db.add(Appointment(circle_id=state["circle_id"], when_text=when,
                                       where_text=str(p.get("where", "")), what=str(p.get("what", "")),
                                       with_whom=str(p.get("with_whom", "")), source_item_id=r.id))
            elif r.kind == "instruction":
                db.add(Task(circle_id=state["circle_id"], title=str(r.payload_json.get("text", ""))[:200],
                            source=f"document:{state['document_id']}"))
            # observations stay as approved extracted items (queryable via RAG)

        doc.status = "approved" if blocked == 0 else "needs_clarification"
        db.commit()

        # Approved content enters the RAG corpus (only approved data is retrievable)
        pages = state.get("pages_text") or []
        if not any(p.strip() for p in pages):
            quotes = [f"{r.source_quote}\n{r.payload_json}" for r in rows if r.review_status == "approved"]
            pages = [doc.summary + "\n\n" + "\n".join(quotes)]
        rag.index_document(state["circle_id"], state["document_id"], doc.filename, pages,
                           source_type=doc.doc_type)
        return {"status": doc.status, "plan_diff": {**state.get("plan_diff", {}),
                                                    "committed": committed, "blocked": blocked}}
    finally:
        db.close()


def reject_by_reviewer(state: DocState) -> DocState:
    db = SessionLocal()
    try:
        doc = db.get(Document, state["document_id"])
        doc.status = "rejected"
        doc.reject_reason = state.get("review", {}).get("reason", "Rejected at review")
        db.query(ExtractedItem).filter(ExtractedItem.document_id == state["document_id"],
                                       ExtractedItem.review_status == "pending") \
            .update({"review_status": "rejected", "reviewed_by": state["user_id"]})
        db.commit()
    finally:
        db.close()
    return {"status": "rejected"}


def write_audit(state: DocState) -> DocState:
    db = SessionLocal()
    try:
        db.add(AuditEvent(circle_id=state["circle_id"], actor_user_id=state["user_id"],
                          action=f"document_{state.get('status', 'processed')}",
                          entity=f"document:{state['document_id']}",
                          detail={"doc_type": state.get("doc_type", ""),
                                  "committed": state.get("plan_diff", {}).get("committed"),
                                  "blocked": state.get("plan_diff", {}).get("blocked")}))
        db.commit()
    finally:
        db.close()
    return {}


def build_document_graph():
    g = StateGraph(DocState)
    g.add_node("ingest", ingest)
    g.add_node("guard_document", guard_document)
    g.add_node("classify", classify)
    g.add_node("reject", reject)
    g.add_node("extract_items", extract_items)
    g.add_node("validate_items", validate_items)
    g.add_node("draft_plan_diff", draft_plan_diff)
    g.add_node("human_review", human_review)
    g.add_node("apply_edits", apply_edits)
    g.add_node("commit_to_plan", commit_to_plan)
    g.add_node("reject_by_reviewer", reject_by_reviewer)
    g.add_node("write_audit", write_audit)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "guard_document")
    g.add_edge("guard_document", "classify")
    g.add_conditional_edges("classify", route_after_classify,
                            {"extract_items": "extract_items", "reject": "reject"})
    g.add_edge("reject", END)
    g.add_edge("extract_items", "validate_items")
    g.add_edge("validate_items", "draft_plan_diff")
    g.add_edge("draft_plan_diff", "human_review")
    g.add_conditional_edges("human_review", route_after_review,
                            {"commit_to_plan": "commit_to_plan", "apply_edits": "apply_edits",
                             "reject_by_reviewer": "reject_by_reviewer"})
    g.add_edge("apply_edits", "validate_items")  # the bounded edit loop
    g.add_edge("commit_to_plan", "write_audit")
    g.add_edge("reject_by_reviewer", "write_audit")
    g.add_edge("write_audit", END)
    return g.compile(checkpointer=checkpointer())


document_graph = build_document_graph()
