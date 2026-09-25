"""Graph B — Voice care update.

transcribe -> structure -> detect_red_flags ??(urgent)??? notify_owner ??
                                    ? (normal)                          ?
                                    ?????????????????????????????????????
                                          caregiver_confirm ? (interrupt)
                                   confirmed ??? save (+RAG index) -> END
                                   discarded ??? END
Red flags (fall, chest pain, missed critical medication, wrong patient) notify
the owner immediately — before the caregiver even confirms.
"""
from typing import TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from ...db import SessionLocal
from ...models import AuditEvent, CareCircle, CareUpdate, User, now
from .. import prompts, rag
from ..model_router import parse_json, router
from .common import checkpointer


class VoiceState(TypedDict, total=False):
    update_id: str
    circle_id: str
    user_id: str
    audio_path: str
    filename: str
    transcript: str
    structured: dict
    red_flags: list[str]
    urgent: bool
    confirm: dict
    status: str


def transcribe(state: VoiceState) -> VoiceState:
    transcript = router.transcribe(state["audio_path"]) if state.get("audio_path") else state.get("transcript", "")
    db = SessionLocal()
    try:
        upd = db.get(CareUpdate, state["update_id"])
        upd.transcript = transcript
        db.commit()
    finally:
        db.close()
    return {"transcript": transcript}


def structure(state: VoiceState) -> VoiceState:
    db = SessionLocal()
    try:
        circle = db.get(CareCircle, state["circle_id"])
        recipient = circle.recipient_name if circle else "the care recipient"
    finally:
        db.close()
    system = prompts.STRUCTURE_UPDATE.format(recipient_name=recipient)
    out = router.complete("structure_update", system, state.get("transcript", ""),
                          tier="fast", json_mode=True,
                          context={"filename": state.get("filename", ""), "transcript": state.get("transcript", "")})
    structured = parse_json(out)
    db = SessionLocal()
    try:  # persist the draft so it is visible in the app before confirmation
        upd = db.get(CareUpdate, state["update_id"])
        upd.structured_json = structured
        db.commit()
    finally:
        db.close()
    return {"structured": structured}


def detect_red_flags(state: VoiceState) -> VoiceState:
    flags = list(state.get("structured", {}).get("red_flags", []))
    db = SessionLocal()
    try:
        upd = db.get(CareUpdate, state["update_id"])
        upd.red_flags = flags
        db.commit()
    finally:
        db.close()
    return {"red_flags": flags, "urgent": bool(flags)}


def route_urgency(state: VoiceState) -> str:
    return "notify_owner" if state.get("urgent") else "caregiver_confirm"


def notify_owner(state: VoiceState) -> VoiceState:
    """Immediate notification path (audit event now; push notification in prod)."""
    db = SessionLocal()
    try:
        db.add(AuditEvent(circle_id=state["circle_id"], actor_user_id=state["user_id"],
                          action="red_flag_alert", entity=f"care_update:{state['update_id']}",
                          detail={"red_flags": state.get("red_flags", [])}))
        db.commit()
    finally:
        db.close()
    return {}


def caregiver_confirm(state: VoiceState) -> VoiceState:
    decision = interrupt({
        "update_id": state["update_id"],
        "transcript": state.get("transcript", ""),
        "structured": state.get("structured", {}),
        "red_flags": state.get("red_flags", []),
    })
    return {"confirm": decision}


def route_confirm(state: VoiceState) -> str:
    if state.get("confirm", {}).get("action") == "confirmed":
        # wrong-patient notes can never be saved into this circle
        if any(str(f).startswith("wrong_patient") for f in state.get("red_flags", [])):
            return "discard"
        return "save"
    return "discard"


def save(state: VoiceState) -> VoiceState:
    structured = state.get("confirm", {}).get("structured") or state.get("structured", {})
    db = SessionLocal()
    try:
        upd = db.get(CareUpdate, state["update_id"])
        upd.structured_json = structured
        upd.red_flags = state.get("red_flags", [])
        upd.status = "confirmed"
        upd.confirmed_at = now()
        author = db.get(User, state["user_id"])
        db.add(AuditEvent(circle_id=state["circle_id"], actor_user_id=state["user_id"],
                          action="care_update_confirmed", entity=f"care_update:{state['update_id']}",
                          detail={"red_flags": state.get("red_flags", [])}))
        db.commit()
        text = f"Care update by {author.name if author else 'caregiver'}:\n{upd.transcript}\nStructured: {structured}"
        rag.index_update(state["circle_id"], state["update_id"], text, author.name if author else "")
    finally:
        db.close()
    return {"status": "confirmed"}


def discard(state: VoiceState) -> VoiceState:
    db = SessionLocal()
    try:
        upd = db.get(CareUpdate, state["update_id"])
        upd.status = "discarded"
        upd.structured_json = state.get("structured", {})
        upd.red_flags = state.get("red_flags", [])
        db.commit()
    finally:
        db.close()
    return {"status": "discarded"}


def build_voice_graph():
    g = StateGraph(VoiceState)
    g.add_node("transcribe", transcribe)
    g.add_node("structure", structure)
    g.add_node("detect_red_flags", detect_red_flags)
    g.add_node("notify_owner", notify_owner)
    g.add_node("caregiver_confirm", caregiver_confirm)
    g.add_node("save", save)
    g.add_node("discard", discard)

    g.set_entry_point("transcribe")
    g.add_edge("transcribe", "structure")
    g.add_edge("structure", "detect_red_flags")
    g.add_conditional_edges("detect_red_flags", route_urgency,
                            {"notify_owner": "notify_owner", "caregiver_confirm": "caregiver_confirm"})
    g.add_edge("notify_owner", "caregiver_confirm")
    g.add_conditional_edges("caregiver_confirm", route_confirm, {"save": "save", "discard": "discard"})
    g.add_edge("save", END)
    g.add_edge("discard", END)
    return g.compile(checkpointer=checkpointer())


voice_graph = build_voice_graph()
