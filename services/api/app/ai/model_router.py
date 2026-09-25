"""ModelRouter: one place that talks to model providers.

- Per-task model tiers (frontier vision model only for extraction; small model
  for everything else — see EVALS.md cost table).
- Fallback chain OpenAI -> Anthropic on 5xx/timeout (tagged in traces).
- Offline demo mode: with no OPENAI_API_KEY the router delegates to
  deterministic fixtures so the app, CI and smoke evals run without spend.
Switching providers is config, not code.
"""
import base64
import hashlib
import json
import logging
import math
import re
from pathlib import Path
from typing import Any

from ..config import DEMO_MODE, settings

log = logging.getLogger("ihtama.models")

_TIERS = {
    "extraction": lambda: settings.extraction_model,
    "fast": lambda: settings.fast_model,
    "answer": lambda: settings.answer_model,
}


class ModelRouter:
    def complete(
        self,
        task: str,
        system: str,
        user_content: str | list[dict],
        *,
        tier: str = "fast",
        json_mode: bool = False,
        temperature: float | None = None,
        context: dict | None = None,
    ) -> str:
        """context carries demo hints (e.g. filename) and trace metadata."""
        if DEMO_MODE:
            from . import demo_fixtures
            return demo_fixtures.complete(task, system, user_content, context or {})
        return self._complete_live(task, system, user_content, tier, json_mode, temperature)

    def _complete_live(self, task, system, user_content, tier, json_mode, temperature) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        model = _TIERS[tier]()
        temp = settings.temperature if temperature is None else temperature
        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temp,
            "max_tokens": settings.max_tokens,
            "api_key": settings.openai_api_key,
            "tags": [f"task:{task}", f"tier:{tier}"],
        }
        if json_mode:
            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
        messages = [SystemMessage(content=system), HumanMessage(content=user_content)]
        try:
            return ChatOpenAI(**kwargs).invoke(messages, config={"run_name": f"ihtama:{task}"}).content
        except Exception as exc:  # fallback chain
            log.warning("OpenAI failed for task=%s (%s); trying fallback", task, exc)
            if settings.anthropic_api_key:
                from langchain_anthropic import ChatAnthropic  # optional dependency

                llm = ChatAnthropic(
                    model="claude-3-5-sonnet-latest",
                    temperature=temp,
                    max_tokens=settings.max_tokens,
                    api_key=settings.anthropic_api_key,
                    tags=[f"task:{task}", "fallback:anthropic"],
                )
                return llm.invoke(messages, config={"run_name": f"ihtama:{task}:fallback"}).content
            raise

    # ---------------- speech to text ----------------
    def transcribe(self, audio_path: str) -> str:
        if DEMO_MODE:
            from . import demo_fixtures
            return demo_fixtures.transcript_for(Path(audio_path).name)
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        with open(audio_path, "rb") as f:
            return client.audio.transcriptions.create(model=settings.transcribe_model, file=f).text

    # ---------------- embeddings ----------------
    def embed(self, texts: list[str]) -> list[list[float]]:
        if DEMO_MODE:
            return [_hash_embed(t) for t in texts]
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.embeddings.create(model=settings.embedding_model, input=texts)
        return [d.embedding for d in resp.data]

    # ---------------- vision helper ----------------
    @staticmethod
    def image_content(text: str, image_paths: list[str]) -> list[dict]:
        parts: list[dict] = [{"type": "text", "text": text}]
        for p in image_paths:
            ext = Path(p).suffix.lstrip(".") or "png"
            b64 = base64.b64encode(Path(p).read_bytes()).decode()
            parts.append({"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}})
        return parts


def _hash_embed(text: str, dim: int = 384) -> list[float]:
    """Deterministic bag-of-words hashing embedding for offline mode.
    Retrieval quality offline comes mainly from the BM25 half of the hybrid."""
    vec = [0.0] * dim
    for token in re.findall(r"\w+", text.lower()):
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


router = ModelRouter()


def parse_json(text: str) -> dict:
    """Robust JSON parsing for model output (handles code fences)."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?|\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise
