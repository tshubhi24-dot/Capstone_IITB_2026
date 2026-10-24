# Analyst Desk — Build Plan

> IIT Bombay Agentic AI Capstone · Project 5
> Build incrementally. Each phase is independently testable before moving on.
> VIVA requires understanding every box in the architecture — build to understand, not just to run.

---

## Company Scope

**PDF requirement:** 10–15 companies in two sectors over three fiscal years.

| Sector | Companies (8) | Tickers |
|--------|--------------|---------|
| Technology | Microsoft, Alphabet, Apple, Amazon, Meta, NVIDIA, AMD, Oracle | MSFT, GOOGL, AAPL, AMZN, META, NVDA, AMD, ORCL |
| Finance | JPMorgan Chase, Goldman Sachs, Bank of America, Visa, Morgan Stanley, Mastercard, Wells Fargo | JPM, GS, BAC, V, MS, MA, WFC |

**Total:** 15 companies × 3 fiscal years (2022, 2023, 2024) = **45 company-years**

**C0 baseline pair:** Microsoft + Alphabet (fixed, as per PDF example request)
**C1/C2 scope:** All 15 companies, both sectors, dynamic company selection

---

## Phase 0 — Foundation ✅ DONE

**Lecture:** Pre-L4
**What was built:**
- `analystdesk/scope.py` — validates ResearchRequest (Microsoft + Alphabet, 3 fiscal years, fixed metrics)
- `analystdesk/__main__.py` — CLI entry point
- `tests/test_scope.py` — boundary checks

**VIVA question:** Why does scope validation come before any data fetching?
> Answer: Fail fast on invalid input before spending API quota or compute. Also defines the typed contract
> (`ResearchRequest`) that every subsequent module consumes — so later stages never need to re-validate.

---

## Phase 1 — Real Data Pipeline (C0 Baseline)

**Lecture:** L4 (data ingestion), L13 (XBRL as ground truth)
**Goal:** End-to-end pipeline that produces a research note with real numbers, zero LLM calls.
This becomes the C0 experiment baseline — the fixed workflow everything else is compared against.

**Files to write:**
```
analystdesk/
  edgar.py          # EDGAR XBRL API client + local JSON cache
  note.py           # ResearchNote + MetricRow typed schema
  baseline.py       # C0 pipeline: fetch → compute → fill note
tests/
  test_edgar.py     # cache reuse, missing years, unit handling
  test_baseline.py  # every row has a fact_id, margin computed correctly
```

**Key decisions:**
- Operating margin = operating_income / revenue, computed in Python, never by an LLM
- Each number carries a `fact_id` = `{concept}/{fiscal_year}/{accession_number}`
  — this traces every figure back to the exact SEC filing
- EDGAR requires a `User-Agent` header with name + contact email; cache all responses locally
  to stay under the 10 req/s limit
- Microsoft fiscal year ends June; Alphabet ends December — must not mix periods

**Evidence at review:** Run `python3 -m analystdesk --years 2022 2023 2024 --mode baseline`
and show a note where every number has a fact_id.

**VIVA questions:**
- Why do we cache EDGAR responses? (rate limits + reproducibility)
- What is a fact_id and why does every number need one? (compliance critic verifies against it)
- Why calculate margin in code and not in the LLM? (rule 1: code and people decide)

---

## Phase 2 — 10-K Ingestion + Hybrid Retrieval

**Lecture:** L4 (chunking, metadata), L5 (BM25, vectors, RRF), L6 (reranking, HyDE)
**Goal:** Parse 10-K filings, build a searchable index, measure retrieval quality.

**Files to write:**
```
analystdesk/
  ingestion.py      # download 10-K HTML, split by Item, keep tables, attach metadata
  retrieval.py      # BM25 + Chroma vectors + RRF + cross-encoder reranker
  query.py          # query-side technique: HyDE or query decomposition
data/
  10k/              # cached 10-K HTML files
  index/            # Chroma vector store
tests/
  test_retrieval.py # Recall@5 on 30+ labelled queries, before + after one change
```

**Key decisions:**
- Split 10-K HTML by Item number (Item 1A Risk Factors, Item 7 MD&A) — not arbitrary chunks
- Keep tables as tables (not flattened to text) — needed for numeric comparison
- Attach metadata per chunk: company, fiscal_year, item, passage_id
- BM25 (`rank-bm25`) + vector search (Chroma + local MiniLM or bge on CPU)
- Combine with **Reciprocal Rank Fusion (RRF)** — not just picking one score
- Cross-encoder reranker re-scores the top-k results
- HyDE: generate a hypothetical answer, embed it, search with that — tests if it improves Recall@5

**Retrieval stack (exact libraries):**
- `rank-bm25` for BM25
- `chromadb` for vector store
- `sentence-transformers` with `cross-encoder/ms-marco-MiniLM-L-6-v2` for reranker
- Local embeddings: `BAAI/bge-small-en` or `all-MiniLM-L6-v2` (no API cost)

**Evidence at review:** Recall@5 table before and after one change (e.g. adding reranker).

**VIVA questions:**
- What is RRF and why combine BM25 + vectors instead of just one?
  (BM25 handles exact keyword matches; vectors handle semantic similarity; RRF merges ranks without tuning weights)
- What does a cross-encoder reranker do that RRF doesn't?
  (reranker scores query+passage jointly — more accurate but slower, so only used on top-k)
- Why split by Item rather than fixed-size chunks?
  (10-K sections have natural semantic boundaries; Item 1A is always risk factors, Item 7 is always MD&A)

---

## Phase 3 — MCP Servers

**Lecture:** L7
**Goal:** Wrap all data access behind FastMCP servers so agents never access storage directly.

**Servers to write:**
```
analystdesk/servers/
  filings_kb.py     # search(query, k) + get_passage(passage_id) over hybrid index
  edgar.py          # list_filings(cik), get_section(cik, item, year), get_xbrl_fact(...)
  python_sandbox.py # run_calc(code) — no network, time limit, pandas only
  research_portal.py# get_past_notes(company), publish_note(note) [write-gated]
tests/
  test_tools.py     # one test per tool (minimum bar requirement)
```

**Key decisions:**
- Every tool has typed inputs and outputs
- Errors returned as structured results, not exceptions (agents can handle them)
- Each tool marked read or write — write access only to the agent that needs it
- `publish_note` is write-only and sits behind the approval gate — agents cannot call it directly
- Use `stdio` transport during development, `HTTP` inside Docker

**Tech:** `fastmcp`, `langchain-mcp-adapters` (to load MCP tools into LangGraph)

**Evidence at review:** Tool list with schemas + one test per tool.

**VIVA questions:**
- Why do we use MCP servers instead of calling functions directly?
  (separation of concerns, typed contracts, easy to mock in tests, matches real deployment where tools run on separate servers)
- Why does `publish_note` require write access and sit behind the approval gate?
  (rule 3: a person approves each exact change to the outside world)
- What is `langchain-mcp-adapters` doing?
  (converts FastMCP tool schemas into LangChain/LangGraph tool objects so the agent can call them)

---

## Phase 4 — Single Agent C1 (LangGraph)

**Lecture:** L8 (orchestration), L10 (planning, ReAct)
**Goal:** One LangGraph agent with all 4 MCP servers, a plan shown to the user, SQLite checkpointer,
stop-and-resume demo. This is C1 — the single-agent experiment configuration.

**Files to write:**
```
analystdesk/
  state.py          # AnalystState TypedDict: plan, messages, note_draft, fact_ids, token_budget
  graph.py          # LangGraph graph: planner → researcher ReAct loop → writer → approval gate
  agent.py          # SupportAgent facade (same pattern as HW2)
```

**Graph structure:**
```
START → input_guardrails → planner → [show plan to analyst, allow edit]
     → researcher (ReAct over filings-kb + edgar)
     → quant (ReAct over edgar + python-sandbox)
     → risk_diff (ReAct over filings-kb)
     → writer → output_guardrails → approval_gate → END
```

**Key decisions:**
- Typed state with `Annotated[list, operator.add]` for messages (same as HW2)
- SQLite checkpointer (`langgraph-checkpoint-sqlite`) — enables stop and resume
- `interrupt()` at approval gate, `Command(resume=...)` to continue
- ReAct loop inside researcher node: think → tool call → observe → repeat
- Planner writes a plan object; analyst can edit it before agents start
- Self-correction: if a tool result contradicts the plan, the planner replans

**Evidence at review:** Graph diagram + live demo of stop-and-resume.

**VIVA questions:**
- What is a checkpointer and why does resume need it?
  (saves graph state to SQLite; without it, you can't restore the mid-run state)
- What is the plan object and why show it to the user?
  (transparency + human oversight; analyst can correct the research direction before agents spend tokens)
- What is ReAct?
  (Reasoning + Acting — agent thinks, calls a tool, observes the result, thinks again)

---

## Phase 5 — Memory

**Lecture:** L9
**Goal:** Short-term context trimming + long-term LangGraph store for preferences, notes, lessons.

**Files to write:**
```
analystdesk/
  memory.py         # LangGraph store reads/writes: preferences, coverage list, past notes
docs/
  memory_policy.md  # one page: what's stored, when, who reads it, how to delete
```

**Memory types:**
| Store | What | When saved | Who reads |
|-------|------|-----------|-----------|
| Short-term | Conversation messages | Each turn | Current agent only |
| Long-term | Analyst preferences | After analyst edits | All agents in session |
| Long-term | Coverage list | After note published | Research lead |
| Long-term | Past notes | After publish | Risk-diff agent ("what changed?") |
| Long-term | Reflexion lessons | After human review | Planner (dev cases only) |

**Tech:** LangGraph store (SQLite-backed, separate from checkpointer)

**Evidence at review:** Memory-on vs memory-off comparison + one-page memory policy.

**VIVA questions:**
- What is the difference between the checkpointer and the LangGraph store?
  (checkpointer = short-term graph state for one run; store = long-term, persists across runs)
- How does the system answer "what changed since our last note?"
  (retrieves past note from store, compares current findings against it)

---

## Phase 6 — Multi-Agent Team C2

**Lecture:** L11 (multi-agent), L14 (hooks, human control)
**Goal:** Supervisor + 5 specialists, parallel fan-out, critic loop, typed hand-offs, approval gate
with approve/edit/reject. This is C2 — the full experiment configuration.

**Files to write:**
```
analystdesk/agents/
  supervisor.py     # makes plan, fans out, runs critic loop (max 2 rounds), token budget
  researcher.py     # one per company, parallel, uses filings-kb
  quant.py          # XBRL → ratios in python-sandbox
  risk_diff.py      # Item 1A this year vs last year
  critic.py         # numbers vs fact_ids (code) + claims vs passages (judge)
  writer.py         # drafts note, publishes only after approval
analystdesk/
  hooks.py          # pre-tool: permission + budget; post-tool: trace + EDGAR rate limit
```

**Typed hand-off message:** each specialist returns a `HandoffMessage` TypedDict with
`agent`, `findings`, `passage_ids`, `fact_ids`, `confidence`.

**Hooks:** pre-tool checks permission and token budget; post-tool logs to trace and enforces EDGAR rate limit.
Hooks apply to every tool call across all agents.

**Approval gate:** uses `interrupt()`. Analyst can:
- **Approve** — publishes the exact note
- **Edit** — changes invalidate the prior approval, must re-approve
- **Reject** — note is not published, reason logged

**Evidence at review:** Comparison of C0 vs C1 vs C2 on same queries (E1).

**VIVA questions:**
- What is a typed hand-off message and why do specialists use them?
  (structured contract between supervisor and specialist — prevents miscommunication, easier to test)
- Why does an edit invalidate the prior approval?
  (rule 3 from the guide: approval is tied to the exact payload — any change makes it invalid)
- What do hooks do that middleware doesn't?
  (hooks are per-tool, not per-request; they enforce budget before and log after every individual tool call)

---

## Phase 7 — Improvement Loop (Reflexion)

**Lecture:** L12
**Goal:** Agent runs on dev cases, reflects on failures, writes lessons. Human reviews each lesson.
Freeze playbook before held-out run.

**Files to write:**
```
analystdesk/improvement/
  reflexion.py      # agent + evaluator + reflection step
  playbook.py       # store/retrieve lessons from LangGraph store
data/evaluation/
  dev_cases.jsonl   # ~20 cases for lesson generation
  heldout_cases.jsonl  # 40+ cases in a folder agents cannot read
```

**Reflexion loop:**
1. Run agent on a dev case
2. Evaluator scores the output (code checks numbers, judge checks explanations)
3. If score fails, reflection step writes a lesson: "when X happens, do Y instead"
4. Human reviews the lesson before it is added to the playbook
5. Next run: planner retrieves only lessons relevant to the current case

**Rules:**
- Lessons only built from dev cases (never held-out)
- Every lesson reviewed by a human before adding
- Playbook frozen before the held-out evaluation run
- DSPy optimiser is optional

**Evidence at review:** Held-out results before vs after playbook + one rejected lesson with reason.

**VIVA questions:**
- Why can't you use held-out cases to generate lessons?
  (data leakage — lessons tailored to held-out cases would inflate results artificially)
- Why does a human review each lesson?
  (lessons may contain incorrect generalisations; human keeps the playbook reliable)

---

## Phase 8 — Evaluation + Monitoring

**Lecture:** L13
**Goal:** 60+ golden cases, judge calibration with Cohen's kappa, Grafana dashboard, alert at <98% verified.

**Files to write:**
```
analystdesk/eval/
  runner.py         # JSONL runner over dev and held-out cases
  judge.py          # judge model (Gemini/Llama family), calibration vs human labels
  checker.py        # code checks: fact_ids present, amounts match XBRL, tools called correctly
data/evaluation/
  dev_cases.jsonl
  heldout_cases.jsonl
  human_labels.jsonl  # 20+ human-labelled outputs for judge calibration
docs/
  evaluation.md     # 4-6 page evaluation report
```

**Dashboard metrics (Grafana):**
- Verified numbers % (alert if < 98%)
- Critic rejections per run
- Cost per note (USD)
- EDGAR cache hit rate
- Median + p95 latency
- Errors and timeouts

**4 experiments:**
- E1: C0 vs C1 vs C2 — same model, tools, budget
- E2: Guardrails off vs on — attack success + false block rate
- E3: Before vs after Reflexion playbook
- E4: Critic loop on vs off + table-aware parsing vs plain text

**Evidence at review:** Evaluation report + judge agreement (Cohen's kappa) + dashboard screenshot.

**VIVA questions:**
- What is Cohen's kappa and why is a high value important?
  (measures judge agreement beyond chance; low kappa means the judge is unreliable as a metric)
- Why must held-out cases be in a folder agents cannot read?
  (prevents any path where retrieval or memory could leak held-out answers into agent responses)

---

## Phase 9 — Security

**Lecture:** L15
**Goal:** Input/output guardrails, threat model, red-team suite of 30+ attacks.

**Files to write:**
```
analystdesk/security/
  guardrails.py     # Llama Guard 4 (input + output) + Prompt Guard 2 (injection)
docs/
  threat_model.md   # one page
tests/red_team/
  test_attacks.py   # 30+ attacks
```

**Attack categories:**
- Injected "news article" that tries to put "buy this stock" in the note
- Search query that attempts to leak the private watchlist
- Sandbox code that tries to reach the network
- Prompt injection through retrieved 10-K passages
- Forged XBRL facts with inflated numbers

**Guardrail layers:**
1. Llama Guard 4 (`meta-llama/llama-guard-4-12b` on OpenRouter) — input + output
2. Llama Prompt Guard 2 on CPU — injection detection in retrieved text
3. Per-agent tool restrictions — agents only have the tools they need
4. `python-sandbox` — no network access, time-limited

**Evidence at review:** Attack success rate with defences off vs on + false block rate on clean cases.

**VIVA questions:**
- What is prompt injection through your own data path?
  (attacker embeds instructions in a filing or article that retrieval surfaces to the agent)
- Why does each agent get only the tools it needs?
  (least-privilege: a compromised researcher agent cannot call publish_note)

---

## Phase 10 — Deployment

**Lecture:** L16
**Goal:** One command starts the whole system. CI fails if eval drops below threshold.

**Files to write:**
```
main.py                   # FastAPI entry point with streaming
docker-compose.yml        # app + 4 MCP servers + Chroma + Prometheus + Grafana
.github/workflows/ci.yml  # runs eval, fails below threshold
config.py                 # all prompts + model IDs in one versioned file
.env.example              # required env vars without secrets
```

**`docker compose up` starts:**
1. FastAPI app (the research UI backend)
2. 4 MCP servers (filings-kb, edgar, python-sandbox, research-portal)
3. Chroma (vector store)
4. Prometheus (metrics scraping)
5. Grafana (dashboards + alerts)

**Evidence at review:** Install on a clean machine + one failed CI run with explanation.

**VIVA questions:**
- Why keep all prompts and model IDs in one versioned config file?
  (reproducibility — you can rerun any experiment with the exact same prompts and models)
- What does the CI eval gate do?
  (runs the evaluation harness on every push; fails the build if task-success rate drops below threshold)

---

## Summary

| Phase | Lecture | Key deliverable | Status |
|-------|---------|----------------|--------|
| 0 | Pre-L4 | Scope validation | ✅ Done |
| 1 | L4, L13 | EDGAR + C0 baseline | ✅ Done (15 companies, as-reported facts, bank pre-tax margin) |
| 2 | L4–L6 | Hybrid retrieval (BM25+vectors+RRF+reranker) | ✅ Built + Recall@5 measured; labels need team review |
| 3 | L7 | 4 FastMCP servers | — |
| 4 | L8, L10 | C1 single agent + LangGraph | — |
| 5 | L9 | Memory + policy | — |
| 6 | L11, L14 | C2 multi-agent + hooks + approval gate | — |
| 7 | L12 | Reflexion + playbook | — |
| 8 | L13 | Eval (60+ cases) + Grafana | — |
| 9 | L15 | Security + red team | — |
| 10 | L16 | Docker + CI/CD | — |

---

## Contribution log

> Record who built what from day one. The viva requires each person to explain their own part
> and redraw the full architecture from memory.

| Date | Author | Phase | What was done |
|------|--------|-------|--------------|
| Oct 2026 | Team | 0 | Scope validation, project structure |
| Oct 2026 | Jayshree (with Claude Code) | 1 | EDGAR client and cache, C0 baseline, note schema, Gradio demo |
| 2026-10-24 | Jayshree (with Claude Code) | 1 | Windows setup; as-reported XBRL facts with restatement warnings; full-year filter; bank pre-tax margin |
| 2026-10-24 | Jayshree (with Claude Code) | 2 | 10-K parser fixes (MA, MS, WFC, BAC, JPM, V); table-aware parsing + plain variant; retrieval switches; query decomposition; 36 labelled queries; Recall@5 ladder |
