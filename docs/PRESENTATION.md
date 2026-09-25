# Ihtama — Demo Day slide deck

**Format:** 12 slides spoken + 3 backup. 10 minutes. PDF / Google Slides.
**Talk shape (required):** problem → solution → demo → architecture → metrics → conclusions.
**Visual system:** warm off-white `#F7F5F2`, ink `#1C1A17`, brand green `#2FA36B`, coral `#F2705B`, amber `#F5B841`. Figtree. Logo + wordmark Ihtama. No emoji.
**Repo / run:** https://github.com/danazzie/ElderlyCareApp · `make install && make build && make api` · demo `danagul@ihtama.demo` / `demo1234`
**Before you walk on stage:** API live, LangSmith project `ihtama` open on a second tab, discharge letter and doc-09 ready, Ask tab pre-warmed.

Timing budget: 1–3 (2:00) · 4 demo (4:00) · 5–8 (2:20) · 9–11 (1:20) · 12 (0:20).

---

## Slide 1 — Title (0:20)

**Title:** Ihtama
**Subtitle:** One parent. Many carers. One trusted care record.
**Footer:** LLM Engineering Final Project · Danagul · September 2026

**On slide**
- Logo + wordmark
- One line: AI care coordinator for families looking after an elderly parent
- Not a diagnosis app. A shared, source-linked care record.

**Say**
"Ihtama is an AI care coordinator. It turns discharge letters, prescriptions and a caregiver's voice notes into one family record — where nothing is trusted until a person approves it, and every answer points at the page it came from."

---

## Slide 2 — The 60-second problem (0:40)

**Title:** Care is scattered. Nobody is sure.

**On slide** (three columns, then one line)

| Today | What goes wrong | Cost |
|---|---|---|
| WhatsApp groups | "What did the doctor say?" | The overloaded adult child |
| Photos of prescriptions | Dose changed and nobody noticed | Double-dosing, missed follow-ups |
| One notebook, one memory | Caregiver and sister have different truths | Trust breaks inside the family |

Bottom line: *The product is not "another chatbot". It is a single care record the family can trust.*

**Say**
"My user is the adult child who coordinates a parent's care. Today she screenshots letters into three chats, retypes doses, and is the only person who knows what happened this morning. Ihtama is for her — and for the sister and the caregiver who must see the same facts."

**If asked "who is the user in one sentence?"**
"The adult child who owns a parent's care circle."

---

## Slide 3 — Promise and three hard rules (0:40)

**Title:** What Ihtama will never do

**On slide**
1. **Every fact has a source.** Page + verbatim quote, or it is discarded.
2. **Nothing enters the plan without a family member.** LangGraph `interrupt()`. Conflicted or missing fields stay blocked even if someone hits Approve.
3. **No clinical advice.** "Should we increase the pills?" → show the recorded instruction → ask the doctor.

Positioning line: *Ihtama is not medical software. Emergencies go to the local emergency number.*

**Say**
"These are product rules, not UI copy. The write path to the care plan does not exist until a human resumes the graph. Mentors will ask where HITL lives — it is the only door into the plan."

---

## Slide 4 — Live demo script (4:00)  [keep this slide on screen as a checklist]

**Title:** Golden path (4 minutes)

**On slide** — numbered, large, leave it up while you demo

1. Danagul (owner) opens Ahmed's circle
2. Upload discharge letter → cards with page quotes → approve → Plan fills
3. Fatima records a morning voice note → structured update → confirm
4. Aisha asks: "What did the doctor say about the follow-up?" → citation chip
5. Aisha asks: "Should we increase the blood-pressure pills?" → redirect
6. Optional trap: doc-09 conflicting Bisoprolol — **Approve is blocked**

**Do**
- Use http://localhost:5173 (fresh UI) or the public URL if live.
- Login chip: Danagul / owner.
- Prefer a letter already extracted so you do not wait on gpt-4o. If you must upload live, talk over the spinner: "Graph A is classifying, extracting, validating, then it will pause."
- Click a citation so they see the source pane.
- For the clinical question, pause on the coral "ask the doctor" card.

**Say, while clicking**
"Watch the human gate: I can edit a date, I cannot silently invent a dose. Conflict items stay greyed. After approve, Ask answers only from this approved corpus — not from the raw PDF, not from another family."

**If the demo dies**
Screenshots of Home, Review (PDF + cards), Ask (cited + clinical). Offline fixtures still walk the same graph.

---

## Slide 5 — Architecture (0:50)

**Title:** One request, three graphs, one record

**On slide** — draw this (from `docs/ARCHITECTURE.md`)

```
Phone PWA  /  Desktop browser
            │  JWT + Membership role
            ▼
         FastAPI
     ┌─────┼──────┐
     ▼     ▼      ▼
  Circles  LangGraph     ihtama-mcp
  Plan     A document    get_care_record
  Audit    B voice       search_care_documents
           C ask         propose_care_plan_change
     │         │         create_task
     ▼         ▼
  SQLite    Chroma     LangSmith
  ModelRouter: OpenAI → Anthropic → offline fixtures
```

**Caption:** One responsive frontend (not two apps). 5173 = Vite; :8000 = API serving the same build.

**Say**
"Walk one request: upload hits FastAPI, Membership is checked, Graph A starts with `thread_id = doc:{id}`. Classify can reject a utility bill. Extract uses gpt-4o vision plus our Skill. Validate is deterministic. Then the graph *stops* on `interrupt()`. Resume from any device. Approve is the only path that writes medications and indexes Chroma."

**If asked "show the path of one request"**
Stay on this slide and narrate the 10 steps in ARCHITECTURE.md. Do not open code unless they ask.

---

## Slide 6 — Why LangGraph (0:40)

**Title:** This is a workflow, not a crew of chatbots

**On slide**

| We needed | LangGraph | Why not the others |
|---|---|---|
| Pause for a human, survive restart | `interrupt()` + SqliteSaver | CrewAI = role collaboration we do not have |
| Branches + bounded loops | reject / clarify / edit×3 | Parlant = conversation policy, not a REST-resumable graph |
| Resume tomorrow from the sister's phone | `thread_id` | A chat agent forgets the gate |

**Highlight:** HITL is a hard boundary, not a modal.

**Say**
"If I used a plain LLM chain, 'approve' would be a button that writes SQL. Here the button *resumes the graph*. The checkpointer is why a crash mid-review does not lose the draft. That is the whole reason LangGraph is in this product."

---

## Slide 7 — MCP + Skill (0:40)

**Title:** One capability layer, one specialised procedure

**On slide** (two columns)

**MCP `ihtama-mcp` — 4 tools**
- `get_care_record` — approved data only
- `search_care_documents` — circle-scoped RAG
- `propose_care_plan_change` — can only create *pending* items
- `create_task`
- Auth: `IHTAMA_TOKEN` → Membership. Tenancy is not a prompt.

**Skill `care-document-review`**
- `SKILL.md` with triggers (upload / "discharge" / "prescription")
- Never infer a dose; quote or discard; conflict → block
- Loaded into the extraction node, the evals, and Claude Desktop

**Say**
"Why MCP and not only REST? The same authorised tools are the contract for the app, for Claude Desktop, and for evals. `propose_care_plan_change` cannot write the plan — that rule is at the boundary. Why a Skill and not a hidden prompt? It is versioned, triggered, and reusable. v1 of the prompt invented a Melatonin dose. v2 *is* this Skill."

---

## Slide 8 — RAG, Chroma, guardrails (0:45)

**Title:** Citations are the product. Isolation is a WHERE clause.

**On slide**

**RAG choices (PDF §3.2 — reasoned, not default)**
- Chunking: section-aware ~400 tokens, 15% overlap, **per page** (so we can cite p.2)
- Embeddings: `text-embedding-3-small` (live) / hashing + BM25 (offline)
- Vector DB: **Chroma**, local, collection `ihtama` — on the PDF list (Qdrant / Chroma / Pinecone / pgvector)
- Retrieval: hybrid BM25 + vector, filter `circle_id`
- Rerank: optional variant B (kept off by default)

**Why not Pinecone?** Zero-ops + offline CI. Hosted index needs a key and kills demo mode. Prod seam: `rag.py` → pgvector.

**Guardrails**
- Input: injection + cross-circle heuristics (qa-13, qa-14)
- Documents are untrusted too
- Output: facts without citations rewritten to "not in the records"
- Clinical route: redirect, do not block the conversation

**Say**
"A prompt cannot cross a WHERE clause. Eval qa-14 is 'show me other families' — it is refused in the guardrail and would be empty in Chroma anyway."

---

## Slide 9 — Evals (0:50)

**Title:** 39 golden cases. Safety is a CI gate.

**On slide**

| Slice | n | What it protects |
|---|---|---|
| Extraction | 15 | invented dose, silent conflict pick, blur guess, utility bill |
| Voice | 9 | wrong patient, missed red flag, chit-chat → no fake vitals |
| Q&A | 15 | clinical redirect, injection, cross-circle, unanswerable |

**Offline results (what CI runs, zero spend)**

| Metric | Value | What it does *not* show |
|---|---|---|
| Med field F1 | 0.906 | schedule wording |
| Branch / flags / blocking | 100% | payload nuance |
| Voice branch | 100% | WER |
| Q&A route + citations | 100% | best chunk vs a good chunk |
| Q&A content | 80% * | live embeddings will move this |
| Safety refusals | **100% gate** | — |

\* hashing-embed extractive answers, 3/15 suboptimal chunks. Judges off offline — we do not invent scores.

**Visual:** screenshot of LangSmith project `ihtama`, one discharge-letter trace, tags `task:extract_items`.

**Say**
"The dataset is the course sample pack plus voice and Q&A traps. Each case is a behaviour that would harm a family if it regressed. Blocking correctness is 100% even if the user mashes Approve — that is deterministic `validate_items`, not hope in the model."

---

## Slide 10 — A/B experiments (0:40)

**Title:** We measured, then we chose

**On slide** (two experiments)

**1. RAG A vs B**
- A: hybrid top-6 (default)
- B: hybrid top-12 → LLM rerank → top-4
- Hypothesis: B wins on multi-doc questions (qa-03, 05, 07) at ~12× rerank cost
- Result (offline): same scores, B slower (p95 0.05s vs 0.03s)
- **Decision: keep A.** B stays behind `POST /ask {"variant":"B"}` until live faithfulness pays for it

**2. Extraction prompt v1 vs v2**
- v1 failed the four traps: invented Melatonin (doc-10), picked 5 mg on conflict (doc-09), merged Panadol/Paracetamol (doc-11), confident blur (doc-05)
- v2 = Skill rules + deterministic validation
- **Decision: ship v2.** Both prompts still live in `prompts.py`

**Say**
"An A/B that keeps the cheaper variant is a real result. We did not keep B because it looked more 'AI'."

---

## Slide 11 — Models, cost, fallback (0:40)

**Title:** Frontier only where handwriting is the product

**On slide**

| Task | Model | Why |
|---|---|---|
| Extraction | gpt-4o | vision + Latin abbreviations (doc-04) |
| Classify / structure / Ask | gpt-4o-mini | 10–20× cheaper, enough on the golden set |
| STT | whisper-1 | noise + accents in the voice pack |
| Embeddings | text-embedding-3-small | multilingual, $0.02 / 1M |
| Fallback | claude-3-5-sonnet | uncorrelated outage |
| No keys | demo fixtures | CI and the offline demo |

**Hyperparameters:** temp **0** for facts; **0.2** for Ask; top_p **1**; max_tokens **2048** (p95 extract ~1.4k). At 0.7, `dose_text` started getting paraphrased — forbidden.

**Cost (live, estimated)**
- One document, once: **$0.02–0.04** (then reused forever via RAG)
- One Ask: **<$0.001**
- One voice note: **<$0.01**

**If OpenAI dies:** Anthropic, same prompts, tagged `fallback:anthropic`. If both die: upload stays `processing`, checkpoint keeps the human gate.

**Say**
"The expensive call happens once per letter, a human checks it, and Ask never pays for vision again. That is the cost architecture — before any cache, which we did not ship."

---

## Slide 12 — What did not confirm, and next (0:20)

**Title:** Honest close

**On slide**

**Did not confirm (yet)**
- Families will approve more than they edit — not measured with real families
- Caregivers prefer voice — no field study
- Rerank helps multi-doc Ask — not on live embeddings
- Handwriting is the main failure — still the risk we watch (doc-04 / doc-05)

**Trade-offs we accepted**
- SQLite + Chroma, not Postgres + pgvector (zero-ops; one-file seams)
- Web PWA, not Expo store builds (deadline fallback; same API)
- No public URL until Render; local `make api` is the one-command demo

**Next (schema already allows it)**
- A User is not a role. Membership is per circle. Iteration 2 = caregiver marketplace without a migration.

**Last line:** Ihtama never diagnoses. It keeps the family's record honest.

**Say**
"Questions."

---

## Backup A — Graph A on one page (Q&A)

**Title:** Document graph (the mandatory multi-step workflow)

```
ingest → guard → classify
              ├─ non_medical → reject → END
              └─ extract (Skill + gpt-4o)
                    → validate (deterministic)
                    ├─ clear → draft → human_review ⏸
                    ├─ clarify → ask_user ⏸ → loop ≤3
                    └─ unreadable → human_review ⏸
human_review ⏸
  ├─ approved → commit (block conflict/missing) → RAG index → audit → END
  ├─ edited   → validate again (max 3)
  └─ rejected → audit → END
```

---

## Backup B — Mentor question crib

Keep this printed, not on the projector.

- **Why LangGraph?** Slide 6. Stateful HITL, not a crew.
- **Coupling?** Graphs write the same SQL the API reads (one truth). Decoupled: REST, ModelRouter, `rag.py`, MCP auth.
- **Cost of one request?** Slide 11.
- **LLM down?** OpenAI → Anthropic → fixtures / retry processing.
- **Prompt evolution?** v1 vs v2, slide 10. Show `prompts.py` if they insist.
- **Why these 15 docs?** They *are* the course pack: conflict, missing, duplicate, blur, bill, SMS amend.
- **What metrics miss?** F1 misses schedule wording; citation coverage misses "best chunk"; offline Q&A content is 80% because of hashing embeddings.
- **Why MCP?** One authorised capability layer; propose cannot write.
- **Why Skill?** Triggers + reusable procedure; better than a buried system prompt.
- **Why multimodality?** Without vision, families retype paper. Without Whisper, caregivers will not log. The product intake disappears.
- **LangSmith?** Project `ihtama`, one discharge trace, tags `task:` / `tier:` / `fallback:`.
- **Why Chroma not Pinecone?** Local, listed in the brief, offline CI. pgvector later.
- **Real users?** Not yet. Hypothesis list is slide 12. Do not pretend.

---

## Backup C — Build checklist (do this, not a spoken slide)

Screenshots to drop onto slides 1, 4, 9:
1. Login hero (Ihtama wordmark)
2. Home — Ahmed today, approvals
3. Review — PDF preview left, item cards right, blocked conflict
4. Ask — cited answer + clinical redirect
5. LangSmith — one real trace

Export 12 slides as PDF. Put the link or file with the GitHub handoff. `docs/PRESENTATION.md` is the script, not the artifact.
