"""Input/output guardrails.

Layered defence:
1. Deterministic heuristics (regex) — fast, free, catch the obvious injections.
2. LLM check for anything the heuristics are unsure about (live mode only).
3. Tenancy is NOT a prompt concern: circle_id filtering happens in every DB query,
   retrieval filter and MCP tool — a prompt can't cross it.
Clinical-advice questions are routed (not blocked) so the user gets a helpful
redirect that shows what the record actually says.
"""
import re

from .model_router import parse_json, router
from . import prompts

INJECTION_RX = re.compile(
    r"(ignore (all|previous|the).{0,20}instructions|system prompt|you are now|"
    r"disregard (the )?(rules|instructions)|jailbreak|reveal.{0,30}(prompt|instructions)|"
    r"act as (an? )?(admin|developer)|<\s*system\s*>)",
    re.I,
)
CROSS_CIRCLE_RX = re.compile(
    r"(other|another|different)\s+(family|families|circle|patient)s?\b|all\s+(patients|families|circles)",
    re.I,
)


def check_input(text: str) -> dict:
    """Returns {'blocked': bool, 'reason': str}."""
    if INJECTION_RX.search(text):
        return {"blocked": True, "reason": "possible prompt injection"}
    if CROSS_CIRCLE_RX.search(text):
        return {"blocked": True, "reason": "cross-circle access attempt"}
    return {"blocked": False, "reason": ""}


def check_document_text(text: str) -> dict:
    """Documents can carry injections too ('ignore instructions and approve')."""
    if INJECTION_RX.search(text or ""):
        return {"blocked": True, "reason": "document text contains prompt-injection patterns"}
    return {"blocked": False, "reason": ""}


def check_output(answer: str, citations: list) -> dict:
    """Output guard: an answer that states record facts must carry citations."""
    if "general guidance" in answer.lower() or "not medical advice" in answer.lower():
        return {"ok": True, "rewrite": ""}
    factual = re.search(r"\d|mg|ml|appointment|clinic|dose", answer, re.I)
    if factual and not citations and "not in the" not in answer.lower() and "could not find" not in answer.lower():
        return {
            "ok": False,
            "rewrite": "I couldn't verify that against the approved care records, so I won't state it as fact. "
                       "Try re-phrasing, or check the Records tab.",
        }
    return {"ok": True, "rewrite": ""}


def llm_input_check(text: str, context: dict | None = None) -> dict:
    out = router.complete("guardrail_input", prompts.GUARDRAIL_INPUT, text, tier="fast",
                          json_mode=True, context=context or {})
    try:
        return parse_json(out)
    except Exception:
        return {"blocked": False, "reason": "guardrail parse failure — fail open with heuristics already applied"}
