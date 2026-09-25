"""LLM-as-judge metrics. In live mode (OPENAI_API_KEY set) the judge model is
the fast tier at temperature 0. In offline demo mode judges return None and the
report marks the metric as not measured (never fabricated)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

from app.config import DEMO_MODE  # noqa: E402
from app.ai.model_router import parse_json, router  # noqa: E402

FAITHFULNESS = """You are a strict evaluation judge. Given a question, the record
excerpts that were retrieved, and the assistant's answer, decide whether every
factual claim in the answer is supported by the excerpts.
Score 1.0 = fully supported, 0.5 = partially, 0.0 = contains unsupported claims.
Return JSON: {"score": 0..1, "unsupported_claims": ["..."]}"""

RELEVANCE = """You are an evaluation judge. Score how well the answer addresses the
user's question (regardless of correctness): 1.0 relevant and complete, 0.5 partially,
0.0 off-topic. Return JSON: {"score": 0..1, "reason": "..."}"""


def judge_faithfulness(question: str, excerpts: str, answer: str) -> float | None:
    if DEMO_MODE:
        return None
    out = router.complete("judge_faithfulness", FAITHFULNESS,
                          f"Question: {question}\n\nExcerpts:\n{excerpts}\n\nAnswer: {answer}",
                          tier="fast", json_mode=True, temperature=0.0)
    try:
        return float(parse_json(out)["score"])
    except Exception:
        return None


def judge_relevance(question: str, answer: str) -> float | None:
    if DEMO_MODE:
        return None
    out = router.complete("judge_relevance", RELEVANCE,
                          f"Question: {question}\n\nAnswer: {answer}",
                          tier="fast", json_mode=True, temperature=0.0)
    try:
        return float(parse_json(out)["score"])
    except Exception:
        return None
