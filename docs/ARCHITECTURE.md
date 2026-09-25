# Ihtama — Architecture

## System overview

```
 +-------------------------------+      +-------------------------------+
 |   Phone browser (PWA)         |      |  Desktop browser              |
 |   bottom tabs, camera, mic    |      |  sidebar, two-pane review     |
 +---------------+---------------+      +---------------+---------------+
                 +------------------+-------------------+
                                    v  HTTPS + JWT (role from Membership)
                       +-------------------------+
                       |  FastAPI (services/api) |  auth, roles, uploads, static web
                       +------------+------------+
          +-------------------+-----+------------------+
          v                   v                        v
 +----------------+  +----------------------+  +-------------------------+
 | Core services  |  |  LangGraph graphs    |  |  Ihtama MCP server      |
 | circles, plan, |  |  A: document->plan   |  |  get_care_record        |
 | tasks, audit   |  |  B: voice update     |  |  search_care_documents  |
 +-------+--------+  |  C: ask w/ guardrail |  |  propose_care_plan_ch.  |
         |           +--------+-------------+  |  create_task            |
         v                    v                +-------------------------+
 +---------------+  +----------------+  +--------------+  +--------------+
 | SQLite (dev)/ |  | Chroma (dev)/  |  | Local files/ |  |  LangSmith   |
 | Postgres      |  | pgvector (prod)|  | S3 (prod)    |  |  tracing     |
 +---------------+  +----------------+  +--------------+  +--------------+
        ModelRouter: OpenAI (primary) -> Anthropic (fallback) -> offline demo fixtures
```

## Path of one request (discharge letter -> approved plan)

1. `POST /api/circles/{id}/documents` — JWT resolved to a user, Membership checked,
   file stored, `Document(status=processing)` created; **Graph A** starts in the
   background with `thread_id = doc:{id}`.
2. `ingest` extracts PDF page text (photos go to the vision model directly).
3. `guard_document` scans raw text for prompt-injection patterns (documents are
   untrusted input too).
4. `classify` (gpt-4o-mini) -> **branch**: `non_medical` -> `reject` -> END with a polite
   explanation; a bill's due date never becomes an appointment.
5. `extract_items` (gpt-4o vision) — the prompt embeds the **care-document-review
   Skill**; every item carries `source_page` + verbatim `source_quote`.
6. `validate_items` — deterministic re-checks on top of the model: missing doses,
   internal conflicts, dose changes vs the current plan. Trust but verify.
7. `draft_plan_diff` persists draft `ExtractedItem`s and computes new/changed/flagged.
8. `human_review` — **LangGraph `interrupt()`**. The state is checkpointed in SQLite;
   the app shows item cards with quotes. Days later, from any device,
   `POST /documents/{id}/review` resumes the thread with the family's decision.
9. **Branch on decision**: `approved` -> `commit_to_plan` (items flagged
   `conflict`/`missing_field` are *blocked* regardless — the doc-09 rule);
   `edited` -> `apply_edits` -> back to `validate_items` (**bounded loop**, max 3);
   `rejected` -> nothing written.
10. `commit_to_plan` upserts medications (STOPPED deactivates), matches appointments
    (SMS reschedule *amends* instead of duplicating), creates tasks, then indexes the
    approved content into the per-circle RAG corpus. `write_audit` records everything.

Graph B (voice): transcribe -> structure -> red-flag detection -> *urgent branch*
notifies the owner before confirmation -> caregiver confirm (interrupt) -> save + index.
A `wrong_patient` red flag can never be saved even if confirmed.

Graph C (ask): input guardrail -> classify -> clinical questions get a *redirect that
quotes the record*; record questions get retrieve -> answer-with-citations ->
faithfulness check with **one regeneration loop** -> output guardrail (facts without
citations are rewritten to "not in the records").

## Deliberate decisions (and what we'd answer at Q&A)

**Why LangGraph** (vs CrewAI / Parlant): the core of this product is not a crew of
chatty agents — it is a *stateful approval workflow*: pause at a human gate, survive
restarts, resume from another device, bounded edit loops. LangGraph's explicit state
machine + `interrupt()` + SQLite checkpointer models this directly. CrewAI optimises
role-based agent collaboration we don't have; Parlant optimises conversational
policies, but our HITL is a REST-resumable workflow, not a conversation.

**Coupling chosen deliberately:** graph nodes write to the same Postgres/SQLite the
API reads — one source of truth for "what is approved", at the cost of the graphs
knowing the schema. Decoupled seams: the frontend only sees REST; models sit behind
`ModelRouter` (provider switch = config); the vector store is wrapped in `rag.py`
(Chroma -> pgvector is one file); MCP tools mirror the internal capability layer so
external clients (Claude Desktop) and internal agent nodes hit the *same*
authorisation path.

**Tenancy is not a prompt concern.** `circle_id` is on every row and every vector
chunk; retrieval filters it in a WHERE clause; MCP tools check Membership per call.
A prompt injection cannot cross a WHERE clause. (Eval qa-14 asserts this.)

**Human-in-the-loop is a hard boundary, not UX polish.** The only code path that
writes to the care plan is `commit_to_plan`, which is only reachable after an
`interrupt()` resume carrying a family decision — and it still refuses items with
blocking flags. The MCP `propose_care_plan_change` tool encodes the same rule at the
external boundary: it can only create pending items.

**Model choice** (details + table in EVALS.md): gpt-4o only where vision quality on
handwriting matters (extraction); gpt-4o-mini for classification/structuring/answers
(10x cheaper, quality sufficient on the golden set); Whisper for STT;
text-embedding-3-small (multilingual, cheap). Fallback chain OpenAI -> Anthropic on
5xx/timeout, tagged in traces; with no key at all the app degrades to deterministic
demo fixtures rather than dying — CI runs on exactly that mode.

**Cost per request** (live mode, estimated): document extraction ~2-4k input +
~1k output tokens on gpt-4o = **$0.02-0.04 per document**; Ask question =
~1.5k tokens on gpt-4o-mini + embedding = **<$0.001**; voice note = Whisper
$0.006/min + mini structuring = **<$0.01**. The expensive call (vision extraction)
happens once per document, is human-reviewed, and its output is reused forever via
RAG — that is the cost-optimising architecture, before any caching.

**Failure modes:** primary model down -> fallback provider (same prompts); both
down -> uploads queue as `processing` and can be retried; graph crashes mid-run ->
checkpoint means the approval state is not lost; a wrong extraction -> can only reach
the plan through a human who sees the source quote next to every item.

**Trade-offs accepted:** SQLite+Chroma instead of Postgres+pgvector for the course
(zero-ops local run; the seams to swap are one file each); LLM rerank instead of a
torch reranker (no GPU dependency in deploy; swappable); background-task extraction
instead of a real queue (Celery/Arq is the production path); web PWA instead of
native Expo builds for iteration 1 (the plan's explicit deadline fallback — the same
API is designed for the Expo client in iteration 2).

## Data model (platform-ready)

A **User is not a role** — roles live in `Membership(user_id, circle_id, role)`, so a
caregiver can serve many circles and a family member can be a caregiver elsewhere.
Iteration-2 marketplace tables (`CaregiverProfile`, `CareRequest`) are already in the
schema so the pivot needs no migration. Every care row carries `circle_id`.

Key tables: `User, CareCircle, Membership, Document, ExtractedItem (draft items with
source page/quote/flags), Medication (dose as written), Appointment, Task, CareUpdate,
Message (citations), AuditEvent`.

## Where things are

| Concern | File |
|---|---|
| Graphs A/B/C | `services/api/app/ai/graphs/{document,voice,ask}_graph.py` |
| Model routing / fallback / demo mode | `services/api/app/ai/model_router.py` |
| RAG (chunking, hybrid retrieval, rerank) | `services/api/app/ai/rag.py` |
| Guardrails | `services/api/app/ai/guardrails.py` |
| Prompts (v1 + v2 history) | `services/api/app/ai/prompts.py` |
| Skill | `skills/care-document-review/SKILL.md` |
| MCP server | `services/mcp/server.py` |
| Evals | `evals/run.py`, `evals/golden/*.json`, `evals/judges.py` |
