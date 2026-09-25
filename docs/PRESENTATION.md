# Demo Day presentation outline (10 minutes, 12 slides)

1. **The 60-second story.** "My mother coordinates my grandfather's care through three
   WhatsApp chats, a paper notebook and her memory. Nobody is sure what the doctor
   said, what was given today, what is next." Ahtama: one parent, many carers, one
   trusted care record.
2. **The user.** The adult child who coordinates a parent's care (owner), siblings
   (members), a caregiver. How they cope today: chat scroll + retyping prescriptions.
3. **The promise + the hard rule.** Every fact linked to its source; nothing enters
   the plan without family approval; never clinical advice — always "here is what the
   record says, ask the doctor".
4. **Live demo (4 min, golden path).** Upload discharge letter -> review cards with
   page-quoted sources -> approve -> plan fills. Voice note -> structured update ->
   confirm. Ask "what did the doctor say about the follow-up?" -> cited answer. Ask
   "should we increase the pills?" -> redirect card. Show the conflict document
   (doc-09): the Bisoprolol item is blocked from approval.
5. **Architecture** (diagram from ARCHITECTURE.md): two frontends -> FastAPI -> three
   LangGraph graphs -> ModelRouter (OpenAI -> Anthropic -> offline fixtures) ->
   SQLite/Chroma; MCP server as the external capability layer.
6. **Why LangGraph.** The product is a stateful approval workflow: `interrupt()` at
   the human gate, SQLite checkpointing, resume from any device, bounded edit loops.
   Alternatives considered: CrewAI (role collaboration we don't have), Parlant
   (conversation policies, not REST-resumable workflows).
7. **MCP + Skill.** Same tools serve the agent, Claude Desktop and evals — one
   authorisation path; `propose_care_plan_change` encodes "no write without human
   approval" at the boundary. The care-document-review Skill drives the extraction
   node AND the desktop demo AND the eval expectations.
8. **RAG + guardrails.** Section-aware chunks with page metadata (citations are the
   product); hybrid BM25+vector, circle_id as a WHERE clause (tenancy is not a prompt
   concern); input/output guardrails; faithfulness check with one regeneration loop.
9. **Evals** (from EVALS.md): 39 golden cases from the course sample pack; med F1
   0.906, branch accuracy 100%, blocking correctness 100%, safety refusals 100%
   (CI gate). Show the LangSmith trace of the discharge-letter run.
10. **A/B experiments.** RAG A vs B (kept A: rerank cost not justified yet) and
    extraction prompt v1 vs v2 (v2 + deterministic validation killed the four trap
    failures: invented dose, silent conflict pick, merged duplicates, confident
    blur).
11. **Cost + failure story.** ~$0.03 per document once, <$0.001 per question;
    fallback chain; offline demo mode = CI without spend.
12. **What did not confirm + next.** Hypotheses we're tracking (approval-vs-edit
    rate, voice share, handwriting as top failure); iteration 2 = caregiver
    marketplace (schema already supports it — a User is not a role).

**Q&A prep:** every "deliberate decision" paragraph in ARCHITECTURE.md is an answer
to a listed mentor question — coupling, cost, fallback, trade-offs, edge cases.
