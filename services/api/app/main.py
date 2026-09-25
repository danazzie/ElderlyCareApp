"""Ihtama API entrypoint.

Run: uvicorn app.main:app --reload  (from services/api)
Serves the built web app from apps/web/dist when present (single-service deploy).
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import DEMO_MODE, settings
from .db import Base, engine
from .routers import ask, auth, circles, documents, plan, updates
from .seed import seed

# LangSmith tracing: enabled purely via env (LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY)
if settings.langchain_tracing_v2:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", settings.langchain_tracing_v2)
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)

Base.metadata.create_all(engine)
seed()

app = FastAPI(title=settings.app_name, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev; restrict to the web origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, circles.router, documents.router, updates.router, ask.router, plan.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "demo_mode": DEMO_MODE,
            "tracing": bool(settings.langchain_tracing_v2)}


# --- serve the built frontend if it exists (single public URL deploy) ---
WEB_DIST = Path(__file__).resolve().parents[3] / "apps" / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = WEB_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")
