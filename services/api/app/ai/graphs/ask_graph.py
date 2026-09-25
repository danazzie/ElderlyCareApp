"""Graph C — Ask Ihtama (Q&A over approved records with citations).

input_guardrail ??(blocked)??? refuse -> END
       ?
   classify ??? clinical ??? safe_redirect (show recorded instruction) -> END
       ?        out_of_scope ??? polite_decline -> END
       ?        record_fact | general_care
       ?
   retrieve (circle-scoped, variant A/B) -> answer_with_citations
       ?
   faithfulness_check ??(unsupported, 1 retry)??? answer_with_citations  [loop]
       ?
   output_guardrail -> END
"""
from typing import TypedDict

from langgraph.graph import END, StateGraph

from .. import guardrails, prompts, rag
from ..model_router import parse_json, router


class AskState(TypedDict, total=False):
    circle_id: str
    question: str
    variant: str            # RAG A/B variant
    route: str
    blocked_reason: str
    chunks: list[dict]
    answer: str
    citations: list[dict]
    faithful: bool
    retries: int


def input_guardrail(state: AskState) -> AskState:
    verdict = guardrails.check_input(state["question"])
    if verdict["blocked"]:
        return {"route": "blocked", "blocked_reason": verdict["reason"]}
    return {}


def route_after_guard(state: AskState) -> str:
    return "refuse" if state.get("route") == "blocked" else "classify"


def refuse(state: AskState) -> AskState:
    return {"answer": "I can't help with that request. I only answer questions about this "
                      "family's approved care record.",
            "citations": [], "route": "blocked"}


def classify(state: AskState) -> AskState:
    out = router.complete("classify_question", prompts.CLASSIFY_QUESTION, state["question"],
                          tier="fast", json_mode=True)
    return {"route": parse_json(out).get("route", "record_fact")}


def route_by_class(state: AskState) -> str:
    return {"clinical": "safe_redirect", "out_of_scope": "polite_decline"}.get(state["route"], "retrieve")


def safe_redirect(state: AskState) -> AskState:
    """Never advise; show what the record says and point to the doctor."""
    chunks = rag.retrieve(state["circle_id"], state["question"], k=2,
                          variant=state.get("variant", "A"))
    recorded = "; ".join(f"\u201c{c['text'][:160].strip()}\u201d [{c['doc_name']}, p.{c['page']}]"
                         for c in chunks) or "no related instruction found in the approved records"
    citations = [{"doc_id": c["doc_id"], "doc_name": c["doc_name"], "page": c["page"],
                  "quote": c["text"][:120]} for c in chunks]
    return {"answer": prompts.CLINICAL_REDIRECT.format(topic="medication or treatment changes",
                                                       recorded=recorded),
            "citations": citations}


def polite_decline(state: AskState) -> AskState:
    return {"answer": "I'm Ihtama, the family care assistant — I can answer questions about the care "
                      "record, plan, documents and updates. That one is outside what I do.",
            "citations": []}


def retrieve(state: AskState) -> AskState:
    chunks = rag.retrieve(state["circle_id"], state["question"], variant=state.get("variant", "A"))
    return {"chunks": chunks}


def answer_with_citations(state: AskState) -> AskState:
    chunks = state.get("chunks", [])
    excerpts = "\n\n".join(f"[{c['doc_name']}, p.{c['page']}]\n{c['text']}" for c in chunks)
    out = router.complete("answer", prompts.ANSWER_WITH_CITATIONS,
                          f"Question: {state['question']}\n\nRecord excerpts:\n{excerpts or '(none found)'}",
                          tier="answer", json_mode=True,
                          temperature=0.2, context={"chunks": chunks})
    result = parse_json(out)
    return {"answer": result.get("answer", ""), "citations": result.get("citations", [])}


def faithfulness_check(state: AskState) -> AskState:
    if not state.get("chunks"):
        return {"faithful": True}  # "not in the records" answers have nothing to verify
    excerpts = "\n\n".join(c["text"] for c in state["chunks"])
    out = router.complete("faithfulness", prompts.FAITHFULNESS_JUDGE,
                          f"Question: {state['question']}\nExcerpts:\n{excerpts}\nAnswer: {state.get('answer','')}",
                          tier="fast", json_mode=True, context={"chunks": state.get("chunks", [])})
    verdict = parse_json(out)
    return {"faithful": bool(verdict.get("faithful", True)), "retries": state.get("retries", 0)}


def route_after_check(state: AskState) -> str:
    if not state.get("faithful") and state.get("retries", 0) < 1:
        return "regenerate"
    return "output_guardrail"


def regenerate(state: AskState) -> AskState:
    return {"retries": state.get("retries", 0) + 1}


def output_guardrail(state: AskState) -> AskState:
    verdict = guardrails.check_output(state.get("answer", ""), state.get("citations", []))
    if not verdict["ok"]:
        return {"answer": verdict["rewrite"], "citations": []}
    return {}


def build_ask_graph():
    g = StateGraph(AskState)
    for name, fn in [("input_guardrail", input_guardrail), ("refuse", refuse), ("classify", classify),
                     ("safe_redirect", safe_redirect), ("polite_decline", polite_decline),
                     ("retrieve", retrieve), ("answer_with_citations", answer_with_citations),
                     ("faithfulness_check", faithfulness_check), ("regenerate", regenerate),
                     ("output_guardrail", output_guardrail)]:
        g.add_node(name, fn)
    g.set_entry_point("input_guardrail")
    g.add_conditional_edges("input_guardrail", route_after_guard, {"refuse": "refuse", "classify": "classify"})
    g.add_edge("refuse", END)
    g.add_conditional_edges("classify", route_by_class,
                            {"safe_redirect": "safe_redirect", "polite_decline": "polite_decline",
                             "retrieve": "retrieve"})
    g.add_edge("safe_redirect", END)
    g.add_edge("polite_decline", END)
    g.add_edge("retrieve", "answer_with_citations")
    g.add_edge("answer_with_citations", "faithfulness_check")
    g.add_conditional_edges("faithfulness_check", route_after_check,
                            {"regenerate": "regenerate", "output_guardrail": "output_guardrail"})
    g.add_edge("regenerate", "answer_with_citations")
    g.add_edge("output_guardrail", END)
    return g.compile()  # no checkpointer: Ask is stateless request/response


ask_graph = build_ask_graph()
