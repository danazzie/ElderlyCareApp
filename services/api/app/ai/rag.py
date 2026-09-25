"""RAG pipeline.

Choices (rationale in docs/ARCHITECTURE.md and docs/EVALS.md):
- Chunking: section-aware ~400 tokens with 15% overlap; documents are chunked per
  page so every chunk carries an exact page number for citations; one chunk per
  confirmed care update (they are short and atomic).
- Embeddings: text-embedding-3-small baseline (cheap, multilingual); offline demo
  mode uses hashing embeddings and leans on the BM25 half of the hybrid.
- Vector store: Chroma embedded (zero-ops for the course); pgvector is the
  production target — the interface below is the seam where it swaps in.
- Retrieval: hybrid BM25 + vector with per-circle filtering (tenant isolation is a
  WHERE clause, not a prompt). Variant B (A/B experiment): wider candidate pool +
  rerank down to top-4.
"""
import re

import chromadb
from rank_bm25 import BM25Okapi

from ..config import DEMO_MODE, settings
from .model_router import router

_client = chromadb.PersistentClient(path=str(settings.chroma_dir))
_collection = _client.get_or_create_collection("ihtama", metadata={"hnsw:space": "cosine"})

CHARS_PER_TOKEN = 4
CHUNK_CHARS = settings.rag_chunk_tokens * CHARS_PER_TOKEN
OVERLAP_CHARS = int(CHUNK_CHARS * settings.rag_chunk_overlap)


def _tok(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def chunk_page(text: str) -> list[str]:
    """Split on section boundaries first (headings / blank lines), then merge
    into ~CHUNK_CHARS windows with overlap. Tables (lines with | or multiple
    columns) are kept whole."""
    text = text.strip()
    if not text:
        return []
    sections = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current = ""
    for section in sections:
        if len(current) + len(section) <= CHUNK_CHARS:
            current = f"{current}\n\n{section}".strip()
        else:
            if current:
                chunks.append(current)
            # carry overlap tail into the next chunk for context continuity
            tail = current[-OVERLAP_CHARS:] if current else ""
            current = f"{tail}\n\n{section}".strip() if tail else section
            while len(current) > CHUNK_CHARS * 1.5:  # very long single section
                chunks.append(current[:CHUNK_CHARS])
                current = current[CHUNK_CHARS - OVERLAP_CHARS:]
    if current:
        chunks.append(current)
    return chunks


def index_document(circle_id: str, doc_id: str, doc_name: str, pages: list[str], source_type: str = "document"):
    ids, docs, metas = [], [], []
    for page_no, page_text in enumerate(pages, start=1):
        for i, chunk in enumerate(chunk_page(page_text)):
            ids.append(f"{doc_id}:p{page_no}:c{i}")
            docs.append(chunk)
            metas.append({"circle_id": circle_id, "doc_id": doc_id, "doc_name": doc_name,
                          "page": page_no, "source_type": source_type})
    if not ids:
        return 0
    _collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=router.embed(docs))
    return len(ids)


def index_update(circle_id: str, update_id: str, text: str, author: str = ""):
    if not text.strip():
        return 0
    _collection.upsert(
        ids=[f"update:{update_id}"],
        documents=[text],
        metadatas=[{"circle_id": circle_id, "doc_id": update_id, "doc_name": f"Care update ({author})".strip(),
                    "page": 1, "source_type": "care_update"}],
        embeddings=router.embed([text]),
    )
    return 1


def remove_document(doc_id: str):
    got = _collection.get(where={"doc_id": doc_id})
    if got["ids"]:
        _collection.delete(ids=got["ids"])


def _circle_chunks(circle_id: str) -> list[dict]:
    got = _collection.get(where={"circle_id": circle_id})
    return [
        {"id": i, "text": d, **m}
        for i, d, m in zip(got["ids"], got["documents"], got["metadatas"])
    ]


def retrieve(circle_id: str, query: str, k: int | None = None, *, variant: str = "A") -> list[dict]:
    """variant A: hybrid top-6. variant B: hybrid top-12 candidates -> rerank -> top-4.
    Both are strictly filtered by circle_id (tenant isolation)."""
    k = k or settings.rag_top_k
    pool = _circle_chunks(circle_id)
    if not pool:
        return []
    n_candidates = 12 if variant == "B" else k

    # vector half
    q_emb = router.embed([query])[0]
    vec = _collection.query(query_embeddings=[q_emb], n_results=min(n_candidates, len(pool)),
                            where={"circle_id": circle_id})
    vec_scores: dict[str, float] = {}
    for cid, dist in zip(vec["ids"][0], vec["distances"][0]):
        vec_scores[cid] = 1.0 - dist  # cosine distance -> similarity

    # BM25 half
    bm25 = BM25Okapi([_tok(c["text"]) for c in pool])
    bm_raw = bm25.get_scores(_tok(query))
    bm_max = max(bm_raw) or 1.0
    bm_scores = {c["id"]: s / bm_max for c, s in zip(pool, bm_raw)}

    # reciprocal-rank-style fusion (simple weighted sum of normalised scores)
    by_id = {c["id"]: c for c in pool}
    fused = []
    for cid, chunk in by_id.items():
        score = 0.5 * vec_scores.get(cid, 0.0) + 0.5 * bm_scores.get(cid, 0.0)
        if score > 0:
            fused.append({**chunk, "score": round(score, 4)})
    fused.sort(key=lambda c: c["score"], reverse=True)
    candidates = fused[:n_candidates]

    if variant == "B":
        candidates = _rerank(query, candidates)[:4]
    return candidates[:k]


def _rerank(query: str, candidates: list[dict]) -> list[dict]:
    """Live mode: LLM pointwise rerank with the fast model (chosen over
    bge-reranker-v2-m3 to avoid a torch dependency in the course deployment;
    the seam allows swapping). Demo mode: keyword-overlap score."""
    if DEMO_MODE:
        q_tokens = set(_tok(query))
        for c in candidates:
            overlap = len(q_tokens & set(_tok(c["text"]))) / (len(q_tokens) or 1)
            c["rerank_score"] = round(overlap, 4)
    else:
        from .model_router import parse_json
        for c in candidates:
            out = router.complete(
                "rerank",
                "Rate 0-10 how useful the excerpt is for answering the question. Return JSON {\"score\": n}",
                f"Question: {query}\n\nExcerpt:\n{c['text'][:1200]}",
                tier="fast", json_mode=True,
            )
            try:
                c["rerank_score"] = float(parse_json(out).get("score", 0)) / 10
            except Exception:
                c["rerank_score"] = 0.0
    candidates.sort(key=lambda c: c["rerank_score"], reverse=True)
    return candidates
