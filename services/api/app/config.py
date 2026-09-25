"""Application settings. Every value can be overridden with environment variables."""
from pathlib import Path

from pydantic_settings import BaseSettings

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    app_name: str = "Ihtama API"
    secret_key: str = "dev-only-secret-key-change-in-production-0123456789"
    access_token_expire_minutes: int = 60 * 24 * 7

    database_url: str = f"sqlite:///{DATA_DIR / 'ihtama.db'}"
    upload_dir: Path = DATA_DIR / "uploads"
    chroma_dir: Path = DATA_DIR / "chroma"
    checkpoint_db: Path = DATA_DIR / "checkpoints.db"

    # Model configuration (see docs/EVALS.md for the selection rationale)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    extraction_model: str = "gpt-4o"          # vision-capable frontier model: only place we need it
    fast_model: str = "gpt-4o-mini"           # classification, structuring, digest
    answer_model: str = "gpt-4o-mini"         # Ask Ihtama answers (A/B tested vs gpt-4o)
    transcribe_model: str = "whisper-1"
    embedding_model: str = "text-embedding-3-small"
    temperature: float = 0.0                  # extraction/classification: determinism first
    answer_temperature: float = 0.2
    max_tokens: int = 2048

    # RAG (variant A defaults; variant B toggled per-request for the A/B experiment)
    rag_chunk_tokens: int = 400
    rag_chunk_overlap: float = 0.15
    rag_top_k: int = 6
    rag_hybrid: bool = True

    langchain_tracing_v2: str = ""
    langchain_api_key: str = ""
    langchain_project: str = "ihtama"

    class Config:
        env_file = str(REPO_ROOT / ".env")
        extra = "ignore"


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.chroma_dir.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

#: True when no OpenAI key is configured — the app then runs with deterministic
#: fixtures so the whole product can be demoed offline (also used by CI smoke tests).
DEMO_MODE = settings.openai_api_key == ""
