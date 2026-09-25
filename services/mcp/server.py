"""Ahtama MCP server (`ahtama-mcp`).

Why MCP and not a plain API: these three tools are the single, authorised
capability layer shared by (1) the LangGraph agent nodes, (2) Claude Desktop /
any MCP client used by a family member, and (3) the eval runner. One
authorisation path (user token -> Membership check), one behaviour everywhere.

Tools
- get_care_record            read approved data only (profile/medications/appointments/updates)
- search_care_documents      the circle-scoped RAG index as a reusable capability
- propose_care_plan_change   encodes "no write without human approval" at the boundary:
                             it can only create a *pending* item that a family member
                             must approve in the app.

Run (stdio, e.g. for Claude Desktop):
    python services/mcp/server.py
Auth: set AHTAMA_TOKEN (JWT from /api/auth/login). Every call is checked against
Membership — tenancy is enforced server-side, not by prompt.
"""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

import jwt as pyjwt
from mcp.server.mcpserver import MCPServer  # MCP SDK v2 (was FastMCP in v1)

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import (Appointment, AuditEvent, CareCircle, CareUpdate,
                        ExtractedItem, Medication, Membership, Task)

Base.metadata.create_all(engine)

mcp = MCPServer("ahtama-mcp")


def _auth(circle_id: str, roles: list[str] | None = None) -> str:
    """Resolve the calling user from AHTAMA_TOKEN and verify circle membership."""
    token = os.environ.get("AHTAMA_TOKEN", "")
    if not token:
        raise PermissionError("AHTAMA_TOKEN is not set (login via /api/auth/login)")
    try:
        user_id = pyjwt.decode(token, settings.secret_key, algorithms=["HS256"])["sub"]
    except pyjwt.PyJWTError as e:
        raise PermissionError(f"Invalid token: {e}")
    db = SessionLocal()
    try:
        m = db.query(Membership).filter(Membership.circle_id == circle_id,
                                        Membership.user_id == user_id,
                                        Membership.status == "active").first()
        if m is None:
            raise PermissionError("Not a member of this care circle")
        if roles and m.role not in roles:
            raise PermissionError(f"Requires role: {roles}")
        return user_id
    finally:
        db.close()


@mcp.tool()
def get_care_record(circle_id: str, section: str = "medications", since: str = "") -> dict:
    """Read APPROVED care data for a circle. section: profile | medications |
    appointments | updates | tasks. Only data a family member has approved is
    returned — drafts and rejected items are never exposed."""
    _auth(circle_id)
    db = SessionLocal()
    try:
        if section == "profile":
            c = db.get(CareCircle, circle_id)
            return {"recipient_name": c.recipient_name, "dob": c.recipient_dob,
                    "notes": c.recipient_notes,
                    "consent_recorded_at": str(c.consent_recorded_at)}
        if section == "medications":
            meds = db.query(Medication).filter(Medication.circle_id == circle_id,
                                               Medication.active.is_(True)).all()
            return {"medications": [{"name": m.name, "dose_as_written": m.dose_text,
                                     "schedule_as_written": m.schedule_text} for m in meds]}
        if section == "appointments":
            appts = db.query(Appointment).filter(Appointment.circle_id == circle_id).all()
            return {"appointments": [{"when": a.when_text, "what": a.what, "where": a.where_text,
                                      "status": a.status} for a in appts]}
        if section == "updates":
            q = db.query(CareUpdate).filter(CareUpdate.circle_id == circle_id,
                                            CareUpdate.status == "confirmed")
            if since:
                from datetime import datetime
                q = q.filter(CareUpdate.created_at >= datetime.fromisoformat(since))
            return {"updates": [{"at": u.created_at.isoformat(), "structured": u.structured_json,
                                 "red_flags": u.red_flags} for u in q.limit(30).all()]}
        if section == "tasks":
            tasks = db.query(Task).filter(Task.circle_id == circle_id).all()
            return {"tasks": [{"title": t.title, "due": t.due_text, "status": t.status} for t in tasks]}
        return {"error": f"unknown section '{section}'"}
    finally:
        db.close()


@mcp.tool()
def search_care_documents(circle_id: str, query: str, k: int = 6, source_types: str = "") -> dict:
    """Semantic + keyword search over this circle's approved documents and
    confirmed care updates. Returns chunks with document name, page and text so
    every answer can cite its source. source_types: optional comma-separated
    filter (e.g. 'discharge_letter,care_update')."""
    _auth(circle_id)
    from app.ai import rag
    chunks = rag.retrieve(circle_id, query, k=k)
    wanted = {s.strip() for s in source_types.split(",") if s.strip()}
    if wanted:
        chunks = [c for c in chunks if c.get("source_type") in wanted]
    return {"chunks": [{"doc_name": c["doc_name"], "page": c["page"],
                        "source_type": c.get("source_type", ""), "score": c.get("score"),
                        "text": c["text"]} for c in chunks]}


@mcp.tool()
def propose_care_plan_change(circle_id: str, kind: str, payload: dict,
                             rationale: str, source_ref: str = "") -> dict:
    """Propose a change to the care plan (kind: medication | appointment | task).
    The proposal is created as a PENDING item that a family owner/member must
    approve in the Ahtama app — this tool can never write to the plan directly.
    That rule lives here, at the boundary, on purpose."""
    user_id = _auth(circle_id)
    if kind not in ("medication", "appointment", "task"):
        return {"error": "kind must be medication, appointment or task"}
    db = SessionLocal()
    try:
        item = ExtractedItem(document_id="mcp-proposal", circle_id=circle_id, kind=kind,
                             payload_json=payload, source_quote=f"MCP proposal: {rationale}"[:400],
                             source_page=0, confidence=1.0,
                             flags=["mcp_proposal"], review_status="pending")
        db.add(item)
        db.add(AuditEvent(circle_id=circle_id, actor_user_id=user_id,
                          action="plan_change_proposed", entity=f"item:{item.id}",
                          detail={"kind": kind, "rationale": rationale, "source_ref": source_ref}))
        db.commit()
        return {"pending_change_id": item.id, "status": "pending_family_approval",
                "note": "A family owner/member must approve this in the Ahtama app before it enters the plan."}
    finally:
        db.close()


@mcp.tool()
def create_task(circle_id: str, title: str, due: str = "", assignee_email: str = "") -> dict:
    """Create a household/care task in the circle (tasks are non-clinical and
    low-risk, so they do not require the approval flow)."""
    user_id = _auth(circle_id)
    db = SessionLocal()
    try:
        assignee_id = None
        if assignee_email:
            from app.models import User
            u = db.query(User).filter(User.email == assignee_email.lower()).first()
            assignee_id = u.id if u else None
        t = Task(circle_id=circle_id, title=title[:200], due_text=due,
                 assignee_user_id=assignee_id, source="mcp")
        db.add(t)
        db.add(AuditEvent(circle_id=circle_id, actor_user_id=user_id, action="task_created",
                          entity=f"task:{t.id}", detail={"title": title, "via": "mcp"}))
        db.commit()
        return {"task_id": t.id, "title": t.title, "due": t.due_text}
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()  # stdio transport (Claude Desktop); use `mcp.run(transport="streamable-http")` for HTTP
