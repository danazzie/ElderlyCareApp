# Ahtama — Evals, A/B experiments and model selection

## 1. Golden dataset (39 cases)

Everything lives in `evals/golden/` and runs against the *real application stack*
(FastAPI in-process, real graphs, real RAG index, isolated temp DB) via
`python evals/run.py`.

| Slice | Cases | What it covers |
|---|---|---|
| Extraction (`extraction.json`) | 15 | the 15 sample documents: clean letters (baseline), prose doses ("forty milligrams"), handwritten + Latin abbreviations, blurry photo (must refuse rather than guess), internal dose conflict (must block), missing fields (must not infer), brand/generic duplicates (must not merge), 5-page letter (citations per page), SMS reschedule (amend, not duplicate), utility bill (reject), nurse handover (update, not plan change) |
| Voice (`voice.json`) | 9 | the 9 sample audio notes: clear updates, noisy audio (unclear vital -> clarification), chit-chat (no fabricated facts), wrong patient (must never save), ambiguous BP reading, medication refusal (red flag), correction note, accented speech |
| Q&A (`qa.json`) | 15 | answerable-with-citation facts, unanswerable question (honest "not in the records"), 4 clinical questions (must redirect), prompt injection, cross-circle attempt, out-of-scope |

Why these: each case encodes a *behaviour that would harm a family if it regressed*
(double dosing, invented doses, missed red flags, leaked data). The golden labels for
extraction come from the course-provided `Sample documents/manifest.json`.

## 2. Metrics

| Metric | What it measures | What it does NOT show |
|---|---|---|
| Medication field F1 (name+dose vs golden) | extraction quality | schedule wording nuance; appointment fields (covered by count + status checks) |
| Branch / status accuracy | did the graph take the right path (reject / review / clarify) | quality of the extracted payloads |
| Blocking correctness | conflicted/missing items never reach the plan even when a user hits "approve" | — safety invariant, must be 100% |
| Voice branch accuracy | red flags, clarifications, wrong-patient refusal | transcription word accuracy |
| Q&A route accuracy + citation coverage | guardrail routing; every stated fact carries a source | whether the cited chunk is the *best* one |
| Refusal correctness (safety gate) | 4 clinical + 2 injection/cross-circle cases refused correctly | — the eval runner exits non-zero below 100%, so CI fails |
| Faithfulness + relevance (LLM-as-judge, live mode) | unsupported claims in answers | judge bias; only as good as the judge model |
| Latency p50/p95, cost/case | ops | — |

## 3. Current results

### Offline demo mode (deterministic fixtures — what CI runs, zero spend)

Full run, 39 cases (`report-20260925-1314*`):

| Metric | Value |
|---|---|
| extraction med F1 (mean) | 0.906 |
| extraction status/branch accuracy | 100% |
| extraction flags accuracy | 100% |
| blocking correctness | 100% |
| voice branch accuracy | 100% |
| Q&A route accuracy | 100% |
| Q&A citation coverage | 100% |
| Q&A content accuracy | 80% * |
| safety refusal correctness | **100% (gate)** |
| latency p50 / p95 | 0.02s / 0.04s |

\* demo mode answers are *extractive* (top chunks stitched with citations); 3/15
questions retrieve a suboptimal chunk with hashing embeddings. This bounds what
offline mode can show; live embeddings + LLM answering is what variant A/B measures.
Faithfulness/relevance judges are disabled offline and reported as "n/a" — we never
fabricate metric values.

**What the eval loop caught during development** (real regressions fixed): documents
with open clarifications were surfaced as plain "review" instead of "clarify"
(status logic fixed); the question router misrouted "his potassium is low, what
should we give him" to record-lookup instead of clinical redirect (patterns v2);
"what is his shoe size" fell into general-care instead of honest record-lookup miss.

### Live mode (OPENAI_API_KEY set)

Run `python evals/run.py --ab` with keys; the same reports are written to
`evals/reports/` and traces land in LangSmith project `ahtama` with per-task tags
(`task:extract_items`, `tier:extraction`, fallback tags). CI has a manual-dispatch
job (`full-evals`) for this, so PRs stay budget-capped at the 10-case smoke run.

## 4. A/B experiment: RAG variant A vs B

- **A (baseline):** hybrid BM25+vector, top-6 chunks.
- **B:** hybrid top-12 candidate pool -> rerank -> top-4.
- **Hypothesis:** B improves citation precision and faithfulness on multi-document
  questions (qa-03, qa-05, qa-07 span 2+ documents) at higher latency/cost
  (12 rerank scoring calls).
- **How:** `python evals/run.py --ab` runs the full Q&A slice under both variants and
  writes paired reports; the `variant` field is also exposed in the product API
  (`POST /ask {"variant": "B"}`) so it can be flipped per-request.
- **Demo-mode result:** identical scores (expected — extractive answers change little
  when the candidate pool grows) with p95 0.05s vs 0.03s. **Decision:** keep A as the
  default; B stays behind the request flag until a live-mode run shows a
  faithfulness gain that justifies ~12x rerank calls per question.

## 5. A/B #2: extraction prompt v1 vs v2

Both prompts are preserved in `services/api/app/ai/prompts.py`.

- **v1** (naive): "Extract all medications, appointments and instructions ... as JSON".
  Observed failure modes on the golden docs: invented a Melatonin dose on doc-10,
  silently picked 5 mg for the conflicting Bisoprolol on doc-09, merged
  Panadol/Paracetamol on doc-11, and returned confident items from the blurry doc-05.
- **v2** (production): embeds the care-document-review **Skill** procedure + hard
  rules (never infer a dose; CONFLICT items block approval; duplicates flagged never
  merged; verbatim source quote required per item; unreadable -> refuse).
- **Measured on:** hallucinated-field rate over docs 05/09/10/11 (the four traps) and
  overall F1. v2's rules are also *enforced deterministically* in `validate_items`,
  so even a model regression cannot silently commit a conflicted dose — the eval
  metric "blocking correctness" pins this at 100%.

## 6. Model selection (documented choice)

| Task | Model | Why | Alternatives considered |
|---|---|---|---|
| Document extraction | gpt-4o | best vision quality on handwriting + Latin abbreviations (doc-04); one vendor for vision+STT+text simplifies iteration 1 | Claude 3.5 Sonnet (comparable vision, kept as fallback), Gemini 1.5 Pro (cheaper, weaker on handwritten dose digits in our spot checks), Tesseract (fails on handwriting/skew) |
| Classification / structuring / digest | gpt-4o-mini | 10-20x cheaper than 4o; classification and JSON structuring are easy for it — frontier quality is wasted here | keeping 4o everywhere (cost), local Llama (ops burden for a 3-person project) |
| Ask answers | gpt-4o-mini (A/B candidate: 4o) | answers are grounded in retrieved chunks, so the model mostly rephrases + cites | — |
| STT | whisper-1 | robust to accents/noise in our voice set | gpt-4o-transcribe (newer; same vendor, drop-in later) |
| Embeddings | text-embedding-3-small | multilingual (Arabic/Russian documents later), $0.02/1M tokens | -3-large (2x cost; upgrade path if retrieval recall becomes the bottleneck), multilingual-e5 (self-hosted ops) |
| Fallback | claude-3-5-sonnet | different provider = uncorrelated outages | — |

**Hyperparameters:** temperature **0** for extraction/classification/judging
(determinism and reproducibility beat creativity everywhere facts are copied from a
document); **0.2** for Ask answers (slight fluency without dose paraphrasing risk —
doses are quoted from chunks); top_p left at 1 (temperature already constrains);
max_tokens 2048 (p95 of golden extraction outputs ~1.4k tokens + headroom; hard cap
protects cost). These were validated by rerunning the extraction slice — at temp 0.7
extraction JSON occasionally reordered/reworded `dose_text`, which our exact-copy
rule forbids.

## 7. Reproducing

```bash
make evals            # full 39 cases, report in evals/reports/
make evals-ab         # A/B experiment
make smoke            # the 10-case CI subset (safety gate enforced)
```
