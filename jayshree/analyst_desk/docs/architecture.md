# Analyst Desk: architecture

How the system is put together: its components, how one request flows through them, and how it is deployed and observed. The reasons behind each choice are in [viva_notes.md](viva_notes.md). Each component is tagged with the course lecture that covers it.

---

## 1. Overview

**What it does.** A team of research agents reads SEC 10-K filings, takes exact figures from XBRL, computes ratios in code, compares companies and years, and drafts a cited research note. The analyst approves the plan before research starts and signs the exact note before it is published.

**Who uses it.** An equity research analyst at an asset manager.

**Core guarantee.** Every key figure in a note carries a source tag that code can check: an XBRL `fact_id`, a calculation over fact_ids, or a quote from a cited passage. The checker verifies each one in code, not with a model.

**Three rules hold throughout:**

1. **The model proposes; code and people decide.** Scope, figures, arithmetic, permissions and approval are plain tested code.
2. **Outside text is data, never instructions.** Filing passages and tool results reach the model only as evidence.
3. **A person approves each exact change to the outside world.** The only write, `publish_note`, needs a signature over the exact note.

---

## 2. Components

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ Analyst                                                                        │
│   asks · approves/edits/cancels the plan · approves/edits/rejects the note     │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼─────────────────────────────────────────┐
│ Serving                                                              [L16]     │
│   FastAPI: /healthz /readyz /api/research (SSE) /docs                          │
│   Gradio UI mounted at "/": Dashboard · Research (C0/C1/C2) · Evaluation ·     │
│   Data Explorer · Raw Data                                                     │
└───────────┬──────────────────────────────┬─────────────────────────────────────┘
            │ C0                           │ C1 / C2
┌───────────▼───────────────┐  ┌───────────▼─────────────────────────────────────┐
│ C0 fixed pipeline         │  │ Agent graphs (LangGraph)          [L8][L10][L11]│
│ decompose → search →      │  │ input guard → plan → [plan gate] → research →  │
│ EDGAR facts → 1 model     │  │ write → check (+ judge) → [note gate] → publish │
│ call · chart · follow-ups │  │ AsyncSqliteSaver checkpoints · stop and resume  │
└───────────┬───────────────┘  └───────────┬─────────────────────────────────────┘
            │                              │ every tool call
            │                  ┌───────────▼─────────────────────────────────────┐
            │                  │ Hooks                                    [L14]  │
            │                  │ pre: permission · per-agent budget · EDGAR rate │
            │                  │ post: trace event (live activity, team board)   │
            │                  └───────────┬─────────────────────────────────────┘
            │                              │ MCP (in-memory · stdio · HTTP)
┌───────────▼──────────────────────────────▼─────────────────────────────────────┐
│ MCP servers                                                            [L7]    │
│  filings-kb             edgar                python-sandbox    research-portal │
│  search_filings         list_filings         run_python        get_past_notes  │
│  get_passage            get_financials                         publish_note    │
│                         get_fact                               (verifies HMAC) │
└─────┬──────────────────────┬───────────────────────┬──────────────────┬────────┘
      │                      │                       │                  │
┌─────▼────────────┐ ┌───────▼────────┐ ┌────────────▼─────┐ ┌──────────▼───────┐
│ Hybrid index     │ │ EDGAR cache    │ │ Sandbox          │ │ Portal DB        │
│ BM25 + MiniLM/   │ │ companyfacts + │ │ import guard +   │ │ published notes  │
│ Chroma, RRF,     │ │ submissions    │ │ audit hooks;     │ │ (SQLite)         │
│ cross-encoder    │ │ JSON (in git)  │ │ Docker: no net,  │ │                  │
│ [L5][L6]         │ │                │ │ read-only, nobody│ │                  │
└─────▲────────────┘ └────────────────┘ └──────────────────┘ └──────────────────┘
      │
┌─────┴──────────────────────────────────────────────────────────────────────────┐
│ Ingestion (offline)                                                  [L4][L5]  │
│ 10-K HTML → Items 1A and 7 → text and table passages (tables kept as tables)   │
│ → metadata (company, year, item, kind, accession) → embeddings and index       │
└────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────┐ ┌──────────────────────────────────────────┐
│ Long-term store (LangGraph)      │ │ Operate and measure          [L13][L16]  │
│ preferences · coverage ·         │ │ OTel traces → Jaeger · Prometheus metrics│
│ past-note figures         [L9]   │ │ → Grafana · alert: verified share < 98%  │
│ Reflexion lessons        [L12]   │ │ eval harness + judge kappa · CI + gate   │
└──────────────────────────────────┘ └──────────────────────────────────────────┘

config/llm.toml: every prompt and model ID, versioned and validated at start-up
```

---

## 3. The three workflows

All three use the same model (`openai/gpt-4.1-mini`, set in `config/llm.toml`), the same retrieval and EDGAR data, and the same tool-call budget. Only the orchestration differs, which is what experiment E1 compares.

### C0: fixed pipeline ([c0_pipeline.py](../analystdesk/c0_pipeline.py))

```
question ─► find companies and years (code) ─► one filtered sub-query per (company, year)
         ─► hybrid search + rerank ─► EDGAR facts for the named companies
         ─► one model call (c0_system + c0_answer prompts) ─► answer with citations
         ─► EDGAR chart for the metric asked about (chat_chart.py)
```

There is no tool choice and no loop: the same question always produces the same searches. A follow-up passes the last three exchanges as context, only to resolve references (`chat_context.py`).

### C1: single agent ([agent/graph.py](../analystdesk/agent/graph.py))

```
input_guard ─► plan ─► [plan gate: approve · edit · cancel]
                         └─► research ⇄ tools (ReAct, within the run's budget)
     tools ─(NOT_IN_COVERAGE)─► replan ─► plan ─► [analyst sees the revised plan]
─► write ─► check ─(issues, at most 2)─► write
─► [note gate: approve · edit · reject] ─edit─► check
─► publish (signed approval; the portal verifies it) ─► END
```

### C2: team ([agent/team.py](../analystdesk/agent/team.py))

```
input_guard ─► plan ─► [plan gate] ─► fan-out in parallel (LangGraph Send):
   researcher[each company]   MD&A drivers          search_filings, get_passage
   quant                      facts + calculations  get_financials, get_fact, run_python
   risk_diff[each company]    Item 1A, Y vs Y-1     search_filings, get_passage, get_past_notes
─► typed HandoffMessage from each ─► gather ─(NOT_IN_COVERAGE)─► replan
─► writer ─► compliance critic: code checks + judge (Llama 3.3 70B) ─(issues, ≤2)─► writer
─► [note gate] ─► publisher (the only agent holding publish_note)
```

- **Hand-offs** (pydantic `HandoffMessage`) carry the agent, company, findings, passage_ids, fact_ids, confidence, tool calls, errors and round. The ids and the confidence are set by code from the actual tool results, not claimed by the model.
- **The budget is split** by `specialist_budgets`. The quant gets 3 calls per company plus 3, which leaves room for a sandbox retry. The rest is shared evenly by each company's researcher and risk-diff agent. The shares add up to the C1 budget (`tool_budget`): 12 + 12 per company.

### Nodes shared by C1 and C2 (`common_nodes`)

| Node | What it does | Model or code |
|---|---|---|
| `input_guard` | Covered company named? Covered years only? No advice request? No instructions aimed at the system? | Code |
| `plan` | Sub-questions, outline, companies and years. Reads preferences, previous notes and relevant lessons. Coverage is then enforced by code. | Model (structured output) + code |
| `review_plan` | Interrupt: approve, edit or cancel. Relative or unspecified years require explicit confirmation; shows the proposed covered range ("last three years" → FY2022–FY2024) and records the confirmed range | Person + code |
| `write` | Draft with figure placeholders. Code renders every figure and adds the "what changed" and Comparability sections (fiscal year-ends, 53-week years, mixed margin bases). | Model + code |
| `check` | Every number, citation and placeholder; no operating vs pre-tax margin on one line; no advice wording; no private-watchlist company. Failed checks go back to the writer at most twice. C2 adds the judge. | Code (+ judge) |
| `review_note` | Interrupt: approve (signs the exact note; refused while checks fail), edit (re-checked) or reject | Person |
| `publish` | `publish_note` with the approval token. The portal re-hashes the note and verifies the token. | Code |

---

## 4. Data flow for one request

> *"Compare Microsoft's and Alphabet's operating margins in fiscal 2024, and tell me what changed in their risk factors."* (C2)

1. **Input guard:** MSFT and GOOGL are covered, 2024 is covered, and there is no advice request.
2. **Plan:** the research lead writes sub-questions and an outline. It reads the analyst's preferences, notes a previous MSFT note in memory, and retrieves up to 3 relevant approved lessons. The analyst approves the plan.
3. **Fan-out:**
   - one researcher per company searches Item 7 (MD&A) for margin drivers;
   - one risk-diff agent per company compares Item 1A for 2024 with 2023;
   - the quant fetches XBRL facts and runs any extra calculation in the sandbox.
   Every call passes through the hooks.
4. **Gather:** typed hand-offs are collected. A `NOT_IN_COVERAGE` result would trigger a replan, shown to the analyst.
5. **Write:** code builds the KEY FIGURES table from XBRL (revenue, operating or pre-tax income, margin, growth, margin change, period end). The writer refers to figures only by placeholder, and code fills in each value with its source tag. Code also computes the comparison with the previous MSFT note.
6. **Check:**
   - Code checks every tagged figure against XBRL and recomputes each calculation.
   - Each quoted number must appear, with its unit, in the passage cited on its line.
   - Every cited passage must exist, and no placeholder may remain.
   - The judge checks each cited claim against its passage.
   Issues go back to the writer, at most twice. Anything left is shown at the gate.
7. **Note gate:** the analyst approves, which signs the exact note, or edits (re-checked, re-signed) or rejects.
8. **Publish:** the portal verifies the signature and stores the note. Memory records the coverage and the note's verified figures for the next "what changed" comparison.

---

## 5. Numbers: from EDGAR to a verified note

### Where the data comes from

SEC EDGAR publishes XBRL financial data as free JSON, one file per company (`companyfacts`), keyed by CIK. Each fact has a concept, a value, start and end dates, the form, the filing date and the accession number of the filing. The files for all 15 companies are cached in `data/edgar_cache/` and committed, so runs never call SEC.

```
companyfacts.json
└── facts.us-gaap.OperatingIncomeLoss.units.USD → [ ~280 entries: annual + quarterly, back to 2008 ]
    { "start": "2023-07-01", "end": "2024-06-30", "val": 109433000000,
      "accn": "0000950170-24-087843", "fy": 2024, "fp": "FY", "form": "10-K", "filed": "2024-07-30" }
```

### From about 280 entries down to 1 ([edgar.py](../analystdesk/edgar.py))

```
fp == "FY" and form == "10-K"     annual report facts only
end[:4] == fiscal year             aligned by period END, not EDGAR's fy field
end − start ≥ 350 days             full year only (10-Ks also tag quarterly tables)
earliest filed                     as originally reported in that year's own 10-K;
                                   later restatements become warnings
```

- **Why the period end.** EDGAR's `fy` describes the filing, not the period, and is wrong for non-December year-ends. Year-ends differ: Microsoft June, Apple September, Oracle May, NVIDIA late January.
- **Why the earliest filing.** Later 10-Ks restate prior years. For example, BAC's FY2024 revenue went from $101,887M to $105,856M in its FY2025 10-K. The as-reported value matches the 10-K the passages come from, so the citation and the text agree.
- **Revenue concepts.** The earliest-filed fact is taken across all of a company's revenue concepts.
- **Banks use pre-tax margin.** JPM, GS, BAC, MS and WFC report no `OperatingIncomeLoss`. Their margin is pre-tax income ÷ net revenue. `margin_basis` is fixed per company in [scope.py](../analystdesk/scope.py), and margins on different bases are never compared.

### fact_id

```
format:   {concept}/{fiscal_year}/{accession}
example:  OperatingIncomeLoss/2024/0000950170-24-087843
```

The accession number identifies the exact filing, so anyone can check the figure on EDGAR by hand. `get_fact` returns the value from that exact filing, which is how the checker verifies it.

### Figures in a note ([agent/figures.py](../analystdesk/agent/figures.py), [agent/checks.py](../analystdesk/agent/checks.py))

| Placeholder | Rendered as | Checked by |
|---|---|---|
| `{MSFT_2024_revenue}` | `$245,122.0M [fact: RevenueFrom…/2024/0000950170-24-087843]` | Value matches the XBRL fact |
| `{MSFT_2024_margin}` | `44.64% [calc: OperatingIncomeLoss/… / RevenueFrom…/…]` | Recomputed numerator ÷ denominator |
| `{MSFT_2024_revenue_growth}` | `15.67% [growth: …/2024/… / …/2023/…]` | Recomputed year-on-year growth |
| `{MSFT_2024_margin_change}` | `+2.87 pp [diff: …]` | Recomputed margin change |
| Any other number | Must be a quote | Appears, with its unit, in a passage cited on the same line |

Placeholders not in the KEY FIGURES table (for example, a company outside the plan) are reported as issues and never published. Arithmetic always happens in Python: in `baseline.py` and `figures.py`, or in the sandbox for anything else.

---

## 6. Retrieval

- **Passages** ([ingest.py](../analystdesk/ingest.py)): Items 1A and 7 from each 10-K, 12,586 in total.
  - Prose passages are split by heading.
  - Each data table becomes its own passage (`kind: table`) of `label | value | value` rows, titled by the line above it. Large tables are split by row, repeating the header.
  - Metadata: `passage_id`, company, fiscal_year, item, kind, accession.
  - A plain-text variant (tables flattened) is kept in `data/passages_plain/` for the E4 ablation.
- **Search** ([retrieve.py](../analystdesk/retrieve.py)):
  1. BM25 and MiniLM-L6 vectors (Chroma), both filtered by metadata first.
  2. Reciprocal Rank Fusion (k = 60).
  3. A cross-encoder (`ms-marco-MiniLM-L-6-v2`) reranks the top 50.
- **Query side** ([query.py](../analystdesk/query.py)): decomposition into one sub-query per (company, year) with metadata filters, and a rewrite that strips names and years from the query text. Results are merged round-robin, so every company and year gets evidence.
- **Measured:** Recall@5 0.472 → 0.903 from decomposition and rewrite ([retrieval_eval.md](retrieval_eval.md)).

---

## 7. Tools, permissions and approval

| Server | Tools | Read / write | Used by |
|---|---|---|---|
| filings-kb | `search_filings`, `get_passage` | read | C1 agent, researchers, risk-diff; critic (`get_passage`) |
| edgar | `list_filings`, `get_financials`, `get_fact` | read | C1 agent, quant; critic (`get_fact`); planner (`list_filings`) |
| python-sandbox | `run_python` | read (no side effects) | C1 agent, quant |
| research-portal | `get_past_notes`, `publish_note` | `publish_note` is the **only write** | `get_past_notes`: C1 agent, risk-diff. `publish_note`: publisher only |

The writer has no tools: it drafts only from the hand-offs.

- **Least privilege at three levels:**
  - each agent is bound only to its tools (`servers.AGENT_TOOLS`);
  - the permission hook re-checks every call;
  - in Docker, the MCP servers sit on an internal network with no internet access.
- **Guardrails** ([agent/guards.py](../analystdesk/agent/guards.py), threats in [threat_model.md](threat_model.md)):
  - **input:** the input guard refuses uncovered companies or years, advice requests and instructions aimed at the system;
  - **tools:** the pre-tool hook refuses a call that names a company on the analyst's private watchlist the plan does not cover (`WATCHLIST_PRIVATE`); a tool result with instructions aimed at the model is withheld from it;
  - **output:** the note checks reject advice wording and private-watchlist companies;
  - `AGENT_DEFENCES=0` turns all of them off, for experiment E2 only.
- **Typed results:** every tool returns `{ok: true, …}` or `{ok: false, error: {code, message}}`, with codes such as `NOT_IN_COVERAGE`, `NOT_FOUND`, `BLOCKED`, `BUDGET_EXCEEDED`, `PERMISSION_DENIED` and `APPROVAL_INVALID`. Agents adapt instead of crashing.
- **Approval** ([approval.py](../analystdesk/approval.py)):
  - the note gate signs SHA-256(title + body + tickers) with an HMAC key the agents never see;
  - `publish_note` recomputes the hash and verifies the signature;
  - an edit after approval, or an agent trying to approve itself, is refused at the server.
- **Sandbox:**
  - **in the process:** an import allow-list for user code, plus audit hooks that block network, subprocesses, native libraries and file writes, plus a time limit;
  - **in Docker** (the real boundary): `--network none`, a read-only root filesystem, the `nobody` user, all capabilities dropped, and memory, CPU and process limits;
  - the sandbox never receives the API key.

Tool schemas: [tools.md](tools.md).

---

## 8. State, memory and lessons

| Store | Technology | Holds | Written by |
|---|---|---|---|
| Run checkpoints | LangGraph `AsyncSqliteSaver` (`data/runs/`) | Each run's full state at every step: plan, messages, hand-offs, draft, check, trace | The graph |
| Long-term memory | LangGraph SQLite store (`data/memory/`) | Preferences, coverage list, past-note figures | The analyst (preferences); publish-after-approval (coverage, figures) |
| Playbook | The same store, `("lessons", status)` namespaces | Pending, approved and rejected lessons with sources and review history | `reflect.py` (pending); the analyst (approve or reject); freeze flag |
| Portal | SQLite (`data/portal/`) | Published notes | `publish_note` only |
| Approval key | File (`data/approval/`) or `APPROVAL_SECRET` | HMAC secret | Created once |

- Within a run, the research conversation is trimmed to a size budget (`trim_context`). The cut always starts on a model message, so no tool result is separated from its call.
- Evaluation runs (`AGENT_EVAL=1`) never read or write memory.
- Policy: [memory_policy.md](memory_policy.md).

---

## 9. Deployment

`docker compose up` starts the services below. They all use one image; only the start command differs. The image is fully pinned: the base image, every Python package (`requirements.lock`), CPU-only PyTorch, the model snapshots, and a search index built from the committed passages. It runs offline. CI builds it from `main` and publishes it to `ghcr.io/tshubhi24-dot/analyst-desk`, so every teammate runs the identical build (`docker compose pull`).

| Service | Role | Network |
|---|---|---|
| `index` | Builds the vector index once, then exits; the others wait for it | internal |
| `filings-kb`, `edgar`, `python-sandbox`, `research-portal` | MCP servers over streamable HTTP (port 8000), with host allow-lists | **internal only** |
| `app` | FastAPI + Gradio on `127.0.0.1:7861`; health check on `/readyz` | internal + outside (OpenRouter) |
| `jaeger`, `prometheus`, `grafana` | Traces (`:16686`), metrics and alerts (`:9090`), dashboard (`:3000`) | internal + localhost |

- Passages, XBRL JSON and evaluation data are mounted from the repository.
- The index, runs, memory, portal notes and approval key live in named volumes.
- Only the app container receives the OpenRouter key.
- All ports are bound to 127.0.0.1.

The research UI and FastAPI now select MCP transport from the environment. With `MCP_URL_*` variables (Docker Compose), they use the separate MCP servers over HTTP. Without those variables, they launch local stdio MCP subprocesses; tests and the offline evaluation harness may use in-process MCP explicitly. These transports expose the same tool schemas, but do not provide equivalent process isolation.

---

## 10. Observability ([observability.py](../analystdesk/observability.py))

- **Traces:**
  - OpenTelemetry, with OpenLLMetry's `LangchainInstrumentor` covering graph nodes, model calls and tool calls;
  - a business span `analystdesk.run` (run id, mode, outcome, verified share, tokens);
  - exported over OTLP to Jaeger;
  - prompt and response text is not captured.
- **Metrics** (`/metrics` on port 9464):

| Metric | Meaning |
|---|---|
| `ad_runs_total{mode,outcome}` | Runs reaching a gate or the end |
| `ad_run_seconds{mode}` | Run step latency (histogram) |
| `ad_tokens_total`, `ad_cost_usd_total` | Tokens and estimated cost |
| `ad_numbers_total{status}` | Verified and unverified numbers at the note gate |
| `ad_critic_rejections_total` | Drafts sent back for revision |
| `ad_tool_calls_total{agent,tool,ok}`, `ad_tool_denied_total{agent,reason}` | Tool calls and hook denials |
| `ad_edgar_requests_total{source}` | EDGAR look-ups (cache or network) |
| `ad_notes_published_total` | Notes published after approval |

- **Grafana** dashboard `Analyst Desk`: verified share against the 98% line, cost per note, latency (median and p95), rejections, tokens, tool calls by agent, denials, EDGAR look-ups.
- **Alert** `VerifiedShareBelow98` ([alerts.yml](../docker/prometheus/alerts.yml)), with promtool unit tests ([alerts.test.yml](../docker/prometheus/alerts.test.yml)).

---

## 11. Evaluation and CI

- **Golden set and scorer:**
  - the cases are in [dev_cases.jsonl](../data/evaluation/dev_cases.jsonl);
  - the held-out cases live in `data/evaluation/heldout/`, written by role 5, and no agent tool can read them;
  - scoring is done in code by [evaluation.py](../analystdesk/evaluation.py).
- **Runner** (`scripts/run_eval.py`): C0, C1 and C2 on the same cases, with memory off, the plan auto-approved, and every run stopped at the note gate.
- **Judge calibration:** `scripts/calibrate_judge.py` and the ⚖️ panel compute Cohen's kappa against human labels.
- **Experiments:**

| ID | Question | Compare |
|---|---|---|
| E1 | Does the agent justify its cost? | C0 vs C1 vs C2 |
| E2 | Do the defences work? | Red-team suite, defences off vs on (attack success, false blocks) |
| E3 | Did the Reflexion lessons help? | Held-out with `AGENT_LESSONS=0` vs the frozen playbook |
| E4 | Signature ablation | Critic loop on vs off; table-aware vs plain passages |

Each experiment is a config file in [experiments/](../experiments/); `run_eval.py --experiment` and `run_redteam.py --experiment` run them with one harness.

- **CI** ([.github/workflows](../../../.github/workflows)):
  - `ci.yml` runs the offline test suite and validates the Compose file on every push and pull request;
  - `evaluation-gate.yml` runs on pushes to `main`, on pull requests from this repository and on demand: C1 on the 20 development cases, failing below 95% task success, on any run error or on any policy violation;
  - `docker-image.yml` publishes the team image on every merge to `main`, and test-builds it on pull requests.

---

## 12. Technology

| Layer | Technology |
|---|---|
| Models | OpenRouter: `openai/gpt-4.1-mini` (C0, agents, reflection); `meta-llama/llama-3.3-70b-instruct` (judge, a different family) |
| Configuration | `config/llm.toml` (prompts and model IDs), validated by `llm_config.py` |
| Orchestration | LangGraph: `StateGraph`, `Send`, `interrupt()`, `Command(resume=…)`, `AsyncSqliteSaver` |
| Memory | LangGraph `AsyncSqliteStore` |
| Tools | FastMCP 3.4 servers + `langchain-mcp-adapters` (MCP SDK 1.x) |
| Retrieval | `rank-bm25`, Chroma, `all-MiniLM-L6-v2`, `cross-encoder/ms-marco-MiniLM-L-6-v2` (CPU) |
| Sandbox | Python audit hooks + Docker (`docker/sandbox/Dockerfile`) |
| UI and serving | Gradio mounted in FastAPI (uvicorn), Plotly charts |
| Observability | OpenTelemetry + OpenLLMetry → Jaeger; `prometheus_client` → Prometheus → Grafana |
| Evaluation | Code scorer, JSONL golden set, Cohen's kappa |
| Deployment | Docker Compose; GitHub Actions |
