"""Resolve the fictional sample-document pack for tests and evals.

CI checks out only this repo, so fixtures live in ``sample-documents/``.
Locally the original course folder ``../Sample documents`` is still accepted.
"""
from __future__ import annotations

import os
from pathlib import Path


def sample_documents_dir(repo_root: Path) -> Path:
    override = os.environ.get("IHTAMA_SAMPLES")
    if override:
        path = Path(override)
        if path.is_dir():
            return path
        raise FileNotFoundError(f"IHTAMA_SAMPLES is set but not a directory: {path}")
    inside = repo_root / "sample-documents"
    if inside.is_dir():
        return inside
    sibling = repo_root.parent / "Sample documents"
    if sibling.is_dir():
        return sibling
    raise FileNotFoundError(
        f"Sample documents not found at {inside} or {sibling}. "
        "Copy the course pack into sample-documents/."
    )
