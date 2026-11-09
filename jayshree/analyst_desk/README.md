# Analyst Desk

**Multi-agent equity research over SEC filings, with every number verified and a person approving every note.**

IIT Bombay Agentic AI Capstone · Project 5

An equity research analyst asks a question such as *"Compare Microsoft's and Alphabet's operating margins in fiscal 2024 and tell me what changed in their risk factors."* Analyst Desk plans the research and shows the plan for approval. It reads the companies' 10-K filings, pulls the exact reported figures from SEC XBRL data and computes ratios in code. It then drafts a cited note and checks every number and claim. Nothing is published until the analyst approves that exact note.

The design follows three rules:

1. **The model proposes; code and people decide.** Figures, arithmetic, scope and permissions are plain tested code. The model plans, chooses tools and writes the prose.
2. **Outside text is data, never instructions.** Filing text and tool results are passed to the model as evidence only.
3. **A person approves each exact change to the outside world.** Approval is a signature over the exact note; any edit invalidates it.

## Quick start

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) running and your own [OpenRouter](https://openrouter.ai) API key.

```powershell
git clone https://github.com/tshubhi24-dot/Capstone_IITB_2026.git
cd Capstone_IITB_2026\jayshree\analyst_desk
Copy-Item .env.example .env      # then set OPENROUTER_API_KEY in .env (Mac/Linux: cp)
docker compose pull              # the team image, about 3.6 GB the first time
docker compose up -d
```

Open <http://127.0.0.1:7861> after about 5 minutes. After that you can start and stop it from Docker Desktop. Details and troubleshooting are in [5. Run it](#5-run-it).

---

## Contents

- [Quick start](#quick-start)

1. [Features](#1-features)
2. [Coverage](#2-coverage)
3. [Architecture](#3-architecture)
4. [Results](#4-results)
5. [Run it](#5-run-it)
6. [Using the app](#6-using-the-app)
7. [API](#7-api)
8. [Configuration](#8-configuration)
9. [Tests, evaluation and CI](#9-tests-evaluation-and-ci)
10. [Project structure](#10-project-structure)
11. [Documentation](#11-documentation)
12. [Working on the project](#12-working-on-the-project)

---

## 1. Features

### Three research workflows, compared like for like

| | Workflow | How it works |
|---|---|---|
| **C0** | Fixed pipeline (no agent) | Deterministic retrieval and EDGAR look-up, then one model call. Supports follow-up questions and draws an EDGAR chart for the metric asked about. |
| **C1** | Single agent | One LangGraph agent with all research tools: plan → approve → ReAct research → write → code check → approve → publish. |
| **C2** | Team of agents | A research lead fans out in parallel to a researcher and a risk-diff agent per company, plus a quant. Each sends back a typed hand-off; a writer drafts and a compliance critic reviews. |

All three use the same model, the same tools and the same tool-call budget. The only difference is how the work is organised, so the comparison measures orchestration alone.

### Numbers you can trust

- **Every figure comes from SEC XBRL** and carries a `fact_id` (`concept/fiscal_year/accession`) pointing at the exact filing.
- **The model never types a key figure.** It writes a placeholder such as `{MSFT_2024_margin}`, and code inserts the value with its source tag (`[fact: …]`, `[calc: …]`, `[growth: …]`, `[diff: …]`).
- **A code checker verifies every number** before the analyst sees the note:
  - facts are checked against XBRL;
  - margins, growth and changes are recomputed;
  - a quoted number must appear, with its unit, in the passage cited on the same line;
  - cited passages must exist;
  - no figure placeholder may be left unfilled;
  - no investment-advice wording is allowed.
- **Fiscal years are aligned** by each period's end date, which matters for June, September and January year-ends. Only full-year facts count.
- **Values are as originally reported**; later restatements are shown as warnings.
- **Banks are measured on pre-tax margin**, other companies on operating margin. The basis is fixed per company, and the two are never compared.

### Human in control

- **Plan gate:** approve, edit (as JSON) or cancel the research plan before any tool runs.
- **Note gate:** approve, edit or reject the exact note. An edit is re-checked and needs a fresh approval.
- **Signed approval:** the gate signs the exact note with an HMAC key. The publishing server verifies the signature, so a skipped or forged approval is refused at the server.
- **Stop and resume:** every run is checkpointed in SQLite. Any run can be reopened from the run list, even after a restart.

### Retrieval over 10-K filings

- 12,586 passages from Item 1A (Risk Factors) and Item 7 (MD&A). Tables are kept as tables, with their labels.
- Hybrid search: BM25 plus MiniLM vectors (Chroma), fused with Reciprocal Rank Fusion, then a cross-encoder reranker.
- Query decomposition in code: one filtered sub-query per company and year, with the names stripped from the query text.
- **Recall@5 = 0.903** on 36 labelled queries, up from 0.472 without decomposition.

### Tools over MCP, with least privilege

- Four MCP servers expose eight typed tools:
  - **filings-kb:** `search_filings`, `get_passage`;
  - **edgar:** `list_filings`, `get_financials`, `get_fact`;
  - **python-sandbox:** `run_python`;
  - **research-portal:** `get_past_notes`, `publish_note`.
- Each agent is bound only to its own tools.
- **Hooks wrap every tool call:**
  - before the call: the permission allow-list, a per-agent budget and an EDGAR rate limit;
  - after the call: a trace event.
- Errors come back as typed results, for example `NOT_IN_COVERAGE`, so the agent can re-plan instead of crashing.
- **Sandboxed Python** for arithmetic. An import guard and audit hooks catch attempts early; the Docker container is the real boundary, with no network, a read-only filesystem, a non-root user and resource limits.

### Memory

- **Long-term memory**, stored in a LangGraph SQLite store:
  - analyst preferences;
  - a coverage list;
  - past-note figures, parsed from the verified tags of published notes.
- **"What changed since our last note"** is computed by code from those figures, including restatements.
- **The analyst controls it:** view and delete entries in the app, or re-run any request without memory to compare.
- **Short-term memory** (the research conversation within a run) is trimmed to a size budget.

### Learning from mistakes (Reflexion playbook)

- `scripts/reflect.py` turns failures on development cases into short "when … do …" lessons.
- **A person reviews every lesson** in the 📘 Playbook. Only approved lessons are used, and only the 3 most relevant to each request. Rejected lessons are kept with their reason, and duplicates are merged.
- **The playbook can be frozen** before a held-out evaluation.

### Evaluation

- A golden set of 20 development cases: numeric, comparison, risk-change and refusal. Expected values are computed from XBRL by code and frozen beforehand.
- Scoring is done in code. A judge from a different model family (Llama 3.3 70B) checks claims against passages, and it is calibrated against human labels with Cohen's kappa.
- The **📏 Evaluation tab** shows the golden set, live runs, the results table, a per-case grid with drill-down, and the judge-calibration workflow.

### Operations

- **Observability:**
  - traces: OpenTelemetry → Jaeger;
  - metrics: Prometheus;
  - a Grafana dashboard: verified-number share, cost per note, latency, critic rejections, tool calls, hook denials;
  - an alert when the verified share drops below 98%.
- **FastAPI service:** health and readiness endpoints, plus a streaming research API, with the Gradio UI mounted on the same server.
- **Docker Compose** starts the app, the four MCP servers on an internal network with no internet access, and the observability stack.
- **One team image:** CI publishes a fully pinned image (base image, `requirements.lock`, torch, model snapshots, prebuilt search index) to GitHub Container Registry on every merge to `main`, so every teammate runs exactly the same build.
- **Versioned LLM configuration:** all prompts and model IDs live in `config/llm.toml`, validated at start-up.
- **GitHub Actions CI:**
  - offline tests, Compose validation and Prometheus rule tests on every push and pull request, using the same dependency lock as Docker;
  - a live C1 development evaluation gate for same-repository pull requests and `main` pushes (also manually runnable): at least 95% task success and zero policy violations; an OpenRouter repository secret is required;
  - the team Docker image, published on every merge to `main` (test-built on pull requests).

---

## 2. Coverage

15 companies × fiscal years 2022–2024 (45 company-years):

| Sector | Companies |
|---|---|
| Technology | MSFT, GOOGL, AAPL, AMZN, META, NVDA, AMD, ORCL |
| Financials | JPM, GS, BAC, MS, WFC (pre-tax margin), V, MA (operating margin) |

Requests outside this scope are declined with a reason, as are requests for investment advice ("Should I buy…", price targets).

---

## 3. Architecture

```
Analyst ──► Gradio UI + FastAPI ──► input guard (scope, advice) ──► plan ──► [plan gate]
                                                                              │
          C1: one ReAct agent ◄───────────────────────────────────────────────┤
          C2: researcher×N ‖ risk-diff×N ‖ quant  ──► typed hand-offs ──► gather
                                                                              │
                writer (placeholders) ──► code checks (+ judge in C2) ──► revise ≤2
                                                                              │
                                      [note gate: approve · edit · reject] ──► publish (signed)

Every tool call ──► hooks (permission · budget · rate limit · trace) ──► MCP servers
   filings-kb (hybrid index) · edgar (XBRL cache) · python-sandbox · research-portal

Memory + playbook (LangGraph store) · checkpoints (SQLite) · traces · metrics · alerts
```

Full description: [docs/architecture.md](docs/architecture.md). The reasoning behind each design choice: [docs/viva_notes.md](docs/viva_notes.md).

---

## 4. Results

Development set, 20 cases, same model (`openai/gpt-4.1-mini`), tools and budget for every configuration. Memory was off and runs stopped at the note gate. Details and the per-case grid: [docs/evaluation.md](docs/evaluation.md).

| | C0 fixed pipeline | C1 single agent | C2 team |
|---|---|---|---|
| Task success | 16/20 | 19/20 | 20/20 |
| Policy violations | 0 | 0 | 0 |
| Numbers verified (mean) | 32% | 97% | 80% |
| Cost per case (est.) | $0.0013 | $0.0063 | $0.0198 |
| Latency, median | 3.8 s | 14.2 s | 50.9 s |

Retrieval: Recall@5 0.903 on table-aware passages ([docs/retrieval_eval.md](docs/retrieval_eval.md)).

These are development results. Final claims use a held-out set written by a team member who does not tune the agents, run three times to show the spread.

---

## 5. Run it

You need your own [OpenRouter](https://openrouter.ai) API key. All data is in the repository: 10-K passages and XBRL facts, so there is no SEC download.

### Option A: Docker, the team image (everything, recommended)

Everyone runs **the same image**. CI builds it from `main` after every merge and publishes it to GitHub Container Registry as `ghcr.io/tshubhi24-dot/analyst-desk`. In that image, the base image, every Python package (`requirements.lock`), torch, the two models and the search index are all fixed, so it behaves the same on every machine.

**One-time setup:**

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), start it, and wait until the engine is running. The image is public, so no registry login is needed.
2. Get the code and create `.env` with **your own** key:

   ```powershell
   git clone https://github.com/tshubhi24-dot/Capstone_IITB_2026.git
   cd Capstone_IITB_2026\jayshree\analyst_desk
   Copy-Item .env.example .env     # Mac/Linux: cp .env.example .env
   notepad .env                    # set OPENROUTER_API_KEY; never commit or share .env
   ```

**Every time:**

```powershell
git checkout main         # the image is built from main; on another branch you would mix two versions
git pull                  # same code, config and data as the image
docker compose pull       # the exact image CI built from main
docker compose up -d      # starts in the background; ready in about 5 minutes, then open http://127.0.0.1:7861
```

Run these again whenever someone merges to `main`. CI publishes the new image about 30–40 minutes after the merge.

| Service | Address |
|---|---|
| App | <http://127.0.0.1:7861> |
| API docs | <http://127.0.0.1:7861/docs> |
| Grafana (dashboard "Analyst Desk") | <http://127.0.0.1:3000> |
| Jaeger traces | <http://127.0.0.1:16686> |
| Prometheus (alerts at `/alerts`) | <http://127.0.0.1:9090> |

- **In-app alerts:** the top of the Analyst Desk page shows active Prometheus alerts and refreshes every 30 seconds. Use **Refresh alerts** to check immediately. The panel distinguishes no active alerts from Prometheus being unavailable; `/api/alerts` provides the same status as JSON.
- **Check it is ready:** `curl.exe --fail http://127.0.0.1:7861/readyz` should return `{"status":"ready"}`.
- **Stop it** with ■ in Docker Desktop or `docker compose down`. Your runs, memory, published notes and approval key stay in Docker volumes. Don't use `--volumes` unless you want to delete them.
- **Run a specific version**, for example to compare with a teammate or before a change: each commit on `main` has an image tagged `sha-<first 7 characters of the commit>`.

  ```powershell
  $env:ANALYSTDESK_IMAGE = "ghcr.io/tshubhi24-dot/analyst-desk:sha-1a2b3c4"; docker compose up
  ```
- **Your own code changes:** `docker compose up --build` builds the image from your folder instead. It takes about 20 minutes the first time, and the index is built on first start if your passages changed. Run `docker compose pull` to go back to the team image.
- **Only host-loopback ports are published:** the app and monitoring UIs are bound to `127.0.0.1`; MCP servers have no published ports. The MCP servers share an internal Docker network. The model-created Python runs in a restricted subprocess inside the sandbox MCP service, but `SANDBOX_MODE=local` is not a full no-network sandbox; this is a remaining security limitation for Role 4. Your API key stays in `.env` and is not baked into the image.

**In Docker Desktop:** after the first `docker compose up -d`, the stack appears under **Containers** as the group **analyst_desk**.

- **Start and stop** with ▶ and ■ on the group row. This reuses the image you already have; to get a newer one, run the commands above again.
- **Open the app** with the **7861:7861** link on the **app** row. Only the app publishes a port; the MCP servers have none.
- **Logs:** click a container, then **Logs** (or run `docker compose logs -f app`).
- **"Exited" is normal** for `volume-init`, which sets up the data volumes and stops, and for `index`, which checks the search index and stops. The app and the four MCP servers stay running, and the app shows **(healthy)** when it is ready.

**Deployment smoke check:** Once Compose reports the app as healthy, run the read-only check below. It verifies the HTTP service, readiness, Prometheus scraping, the 98% alert rule and Grafana without making any model calls.

```powershell
python scripts/ops_smoke.py
```

A successful smoke check is not proof that a research note is correct. For an actual note, confirm the final verification status before approval. The Approve button is disabled when checks fail, and the backend also rejects that approval.

**Checking the dashboard:**
1. Run a C1 or C2 request in the app and approve the plan.
2. After about 15 seconds, Prometheus at <http://127.0.0.1:9090/graph> returns values for `sum(ad_runs_total)` and `sum(ad_tool_calls_total)`.
3. In Grafana, set the time range to *Last 6 hours*. The verified-share panel fills once a draft reaches the note gate.

**Troubleshooting:**

| Problem | Fix |
|---|---|
| `docker compose pull` says *denied* or *unauthorized* | The package has been made private. Create a GitHub token (classic) with only the `read:packages` scope, run `docker login ghcr.io -u <your-github-username>` and paste the token as the password, or ask the repository owner for **Read** access |
| Pull is slow | The image is about 3.6 GB (PyTorch, models, index). Only the first pull is large; later pulls fetch only the layers that changed |
| `port is already allocated` | Something else is using port 7861. Another Docker stack shows it in the **Port(s)** column in Docker Desktop: stop that group. A Python `app.py` does not appear there: `netstat -ano \| findstr :7861` gives its process ID to end in Task Manager. Then run `docker compose up -d` again |
| C1/C2 runs failed with *unable to open database file* (Docker runs from before this image) | Fixed automatically: the `volume-init` service gives the app user ownership of its data volumes on every start, keeping their data |
| The index service runs for about 10 minutes | Your checkout's passages differ from the image's. Run `git pull` so they match, or let it build once; it is reused afterwards |

**Package visibility:** the image is public, set by the repository owner at *github.com/tshubhi24-dot → Packages → analyst-desk → Package settings*. If it is ever made private, give each teammate **Read** access there.

### Option B: Python (development and tests)

Python 3.12 or newer.

```powershell
cd Capstone_IITB_2026\jayshree\analyst_desk
.\setup.bat                          # creates .venv and installs requirements
                                     # Mac/Linux: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
Copy-Item .env.example .env          # then set OPENROUTER_API_KEY
.\.venv\Scripts\python.exe app.py    # http://127.0.0.1:7861
```

The first search builds the vector index, which takes about 10 minutes on CPU, once.

Optionally, with Docker Desktop running, build the locked-down code sandbox so that `run_python` uses a container instead of the local guarded process:

```powershell
docker build -t analystdesk-sandbox -f docker/sandbox/Dockerfile .
```

Don't run the Python app and the Docker app at the same time, because both use port 7861.

---

## 6. Using the app

| Tab | What it is |
|---|---|
| 📈 **Dashboard** | EDGAR-verified revenue, margin and income charts and table for any of the 15 companies |
| 🔎 **Research** | Choose **C0 · No-Agent**, **C1 · Single agent** or **C2 · Team** |
| 📏 **Evaluation** | Golden set; run C0/C1/C2 on chosen cases; E1 results and per-case grid (click a row to see the note); ⚖️ judge calibration |
| 🔍 **Data Explorer** | Search the 10-K passages directly, filtered by company and year |
| 🗂️ **Raw Data** | The full C0 `ResearchNote` JSON, with every figure's fact_id |

**C0 in the Research tab:** ask a question, or choose *Follow-up* to use the last three exchanges as context. The answer cites passages and EDGAR figures. A chart is drawn for the metric asked about (quarterly if requested), and *How this answer was built* lists the searches, facts and model used.

**C1 and C2 in the Research tab:**
1. Type a request (or pick an example) and press **Start**.
2. **Approve**, edit or cancel the plan.
3. Watch the live **👥 Team board** (C2: one row per agent, with status, tool calls and hand-off details) and the **🔧 Agent activity** log (every step and tool call with its result).
4. Review the note: numbered sources and the code check (for example "18/18 numbers verified", with any issue listed).
5. **Approve** to sign and publish it, **edit** it (re-checked; needs a fresh approval) or **reject** it.

Also in this tab:
- **📂 Your runs:** click one to reopen or resume it.
- **↻ Re-run without memory:** compare the same request without memory.
- **🧠 Memory:** view, add and delete preferences, coverage and past-note figures.
- **📘 Playbook:** approve, reject or freeze lessons.
- **📚 Published notes:** everything in the research portal.

**Try it:** choose **C2 · Team** and ask *"Compare Microsoft's and Alphabet's operating margins in fiscal 2024."* Approve the plan and watch the team board. Then approve the note and ask again: the second note has a **"What changed since our last note"** section computed from the first.

---

## 7. API

The app is a FastAPI server with the Gradio UI mounted at `/`. Interactive docs are at `/docs`.

| Method and path | Purpose |
|---|---|
| `GET /healthz` | Liveness: `{"status": "ok"}` |
| `GET /readyz` | Readiness: returns 503 until the retriever and index are loaded |
| `POST /api/research` | Start a C1 or C2 run (`request`, `mode`, `analyst`, `memory_on`). Streams events (server-sent events) until the plan gate. |
| `POST /api/research/{run_id}/decision` | Resume at a gate: `approve`, `edit` (with `plan` or `note`) or `reject`. Streams until the next gate or the end. |

The API runs the same graph and gates as the UI, so publishing still requires a signed approval of the exact note.

---

## 8. Configuration

| Where | What |
|---|---|
| `.env` | **Only** `OPENROUTER_API_KEY`. Git-ignored; never commit it. |
| [`config/llm.toml`](config/llm.toml) | Every prompt and model ID: the `c0`, `agent`, `judge` and `reflection` models, and the C0, planner, researcher, writer, specialist, judge and reflection prompts. Version-controlled and validated at start-up (version, required entries and template placeholders); the app refuses to start with an invalid file. |

Optional environment variables:

| Variable | Default | Effect |
|---|---|---|
| `AGENT_CALLS_BASE`, `AGENT_CALLS_PER_COMPANY` | 12, 12 | Tool-call budget per run: 24 for one company, 36 for two, 48 for three. The same for C1 and C2; C2 splits it across its specialists. |
| `AGENT_MAX_TOOL_CALLS` | unset | Fixes the budget for experiments |
| `AGENT_TOKEN_BUDGET`, `AGENT_MAX_CONTEXT_CHARS` | 120000, 60000 | Token budget per run; size of the trimmed research context |
| `AGENT_LESSONS` | 1 | `0` disables the playbook (the "before" runs for E3) |
| `SANDBOX_MODE` | auto | `docker`, `local` or `auto` (Docker when available) |
| `METRICS_PORT` | 9464 | Prometheus `/metrics` port |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | unset | Send traces to Jaeger or any OTLP collector |
| `PRICE_PER_M_TOKENS` | 0.52 | Cost estimate used in metrics and evaluation |

---

## 9. Tests, evaluation and CI

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests          # offline tests; no API key needed
.\.venv\Scripts\python.exe scripts\run_eval.py --configs c0 c1 c2 --split dev
.\.venv\Scripts\python.exe scripts\eval_report.py data\evaluation\results\eval_dev_<tag>.json   # writes docs/evaluation.md
.\.venv\Scripts\python.exe scripts\eval_retrieval.py                # Recall@5 report
.\.venv\Scripts\python.exe scripts\reflect.py data\evaluation\results\eval_dev_merged.json      # pending lessons
.\.venv\Scripts\python.exe scripts\calibrate_judge.py sample        # judge calibration items
```

Evaluation runs use memory off, auto-approve the plan, stop at the note gate (nothing is published), and count failures and timeouts rather than hiding them.

**GitHub Actions:**
- **Analyst Desk CI** runs on every push and pull request. It runs the offline test suite, validates Docker Compose, and executes `promtool` rule tests without model API calls. Both this workflow and the live gate use the pinned `requirements.lock` and CPU-only torch to match the Docker image.
- **Analyst Desk Docker Image** runs on every merge to `main`. It builds the pinned image with the search index baked in and publishes it as `ghcr.io/tshubhi24-dot/analyst-desk:main` and `:sha-<commit>`. On pull requests it only test-builds the image, without the index and without publishing.
- **Analyst Desk Evaluation Gate** runs automatically for same-repository pull requests and changes to `main`. A maintainer can also launch it from **Actions → Analyst Desk Evaluation Gate → Run workflow**. Add the repository secret `OPENROUTER_API_KEY` first. It runs C1 on 20 development cases and fails below 95% task success or if any policy violation occurs; results are attached as an artifact. Fork pull requests cannot access this secret, so they run the offline CI only and need a maintainer to perform a separate live evaluation. This is a development-set gate, not a held-out/generalisation result.

**Alert rule test** (with Compose running):

```powershell
docker compose up -d prometheus
docker compose cp .\docker\prometheus\alerts.yml prometheus:/tmp/alerts.yml
docker compose cp .\docker\prometheus\alerts.test.yml prometheus:/tmp/alerts.test.yml
docker compose exec -T prometheus sh -c "cd /tmp && promtool test rules alerts.test.yml"   # prints SUCCESS
```

---

## 10. Project structure

```
analyst_desk/
├── app.py                 Gradio UI + FastAPI server (Dashboard, Research, Data Explorer, Raw Data)
├── agent_ui.py            C1/C2 panel: gates, team board, activity, runs, memory, playbook, notes
├── eval_ui.py             Evaluation tab
├── config/llm.toml        Prompts and model IDs (versioned)
├── analystdesk/
│   ├── scope.py           Companies, sectors, margin basis, covered years
│   ├── edgar.py           XBRL facts: fiscal-year alignment, full-year filter, as-reported values
│   ├── baseline.py        Figures and margins in Python
│   ├── ingest.py          10-K parsing: Items 1A and 7, tables kept as tables
│   ├── retrieve.py        Hybrid BM25 + vector search, RRF, cross-encoder reranker
│   ├── query.py           Query decomposition and rewrite
│   ├── c0_pipeline.py     C0 fixed pipeline
│   ├── chat_chart.py      C0 EDGAR charts; chat_context.py: C0 follow-ups
│   ├── servers/           The four MCP servers, the client, the sandbox runner
│   ├── approval.py        HMAC approval tokens
│   ├── agent/             graph.py (C1 + shared nodes), team.py (C2), hooks.py, checks.py,
│   │                      figures.py, runtime.py
│   ├── memory.py          Long-term memory and "what changed"
│   ├── lessons.py         Reflexion playbook
│   ├── evaluation.py      Scoring, runner, evaluation gate
│   ├── observability.py   Traces and metrics
│   ├── llm_config.py      Loads and validates config/llm.toml
│   ├── alerts.py          Prometheus alerts for the in-app panel
│   └── api.py             FastAPI endpoints
├── scripts/               Evaluation, reflection, judge calibration, retrieval eval, utilities
├── data/                  passages/, passages_plain/, edgar_cache/, evaluation/ (all committed)
├── docker/                Sandbox image, Prometheus rules and tests, Grafana dashboard
├── tests/                 Unit, integration and offline end-to-end tests
├── Dockerfile, compose.yaml, setup.bat
├── requirements.txt       Dependencies (human-edited; used by a local venv)
├── requirements.lock      Exact versions the Docker image installs
└── docs/                  See below
```

Built locally on first use and not in git: the Chroma index (`data/index/`), run checkpoints (`data/runs/`), memory (`data/memory/`), published notes (`data/portal/`) and the approval key (`data/approval/`).

---

## 11. Documentation

| Document | Contents |
|---|---|
| [docs/product_spec.md](docs/product_spec.md) | The problem, user, scope and domain rules, and where the app differs from them |
| [docs/architecture.md](docs/architecture.md) | Components, data flow, agent graphs, deployment |
| [docs/viva_notes.md](docs/viva_notes.md) | Why each part is built the way it is, with likely questions and evidence |
| [docs/tools.md](docs/tools.md) | The eight MCP tools and their schemas |
| [docs/memory_policy.md](docs/memory_policy.md) | What memory keeps, who reads it, privacy, how to correct or delete it |
| [docs/evaluation_guide.md](docs/evaluation_guide.md) | How evaluation works, how to read the results, and the reference answers |
| [docs/evaluation.md](docs/evaluation.md) | Current evaluation results |
| [docs/retrieval_eval.md](docs/retrieval_eval.md) | Retrieval Recall@5 results |
| [docs/plan.md](docs/plan.md) | Team build plan and contribution log |

---

## 12. Working on the project

1. `git pull`, then work on your own branch (`<name>/<feature>`) and open a pull request to `main`.
2. Run `python -m unittest discover -s tests` before every pull request; CI runs it too.
3. Never commit `.env` or any key. Everyone uses their own OpenRouter key.
4. Log your work in the contribution log in [docs/plan.md](docs/plan.md).

**Independence rules** (they keep the results honest):

| Task | Who |
|---|---|
| Held-out evaluation cases (`data/evaluation/heldout/`) | Role 5 only; whoever tunes the agents must not write or see them |
| Judge-calibration labels | Role 5, checked by role 1 |
| Red-team attacks | Role 5; whoever builds the defences must not write the attacks |
| Tuning prompts, agents and lessons | Development cases only |
