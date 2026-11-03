# Analyst Desk — start here (team)

This folder is the team's shared base for the capstone (Project 5, Analyst Desk). Clone it, run it, then build your part on top.

**Repo:** https://github.com/tshubhi24-dot/Capstone_IITB_2026 · project folder `jayshree/analyst_desk/`

---

## 1. Get it running

### Option A — Docker (easiest, runs everything)

Install Docker Desktop (no Docker account needed). Start it and wait for "Engine running". Then:

```bash
git clone https://github.com/tshubhi24-dot/Capstone_IITB_2026.git
cd Capstone_IITB_2026/jayshree/analyst_desk
copy .env.example .env          # Mac/Linux: cp .env.example .env
# open .env and put YOUR OWN OpenRouter key in OPENROUTER_API_KEY
docker compose up --build
```

| What | Where |
|---|---|
| App | http://127.0.0.1:7861 |
| Grafana dashboard ("Analyst Desk") | http://127.0.0.1:3000 |
| Jaeger traces | http://127.0.0.1:16686 |
| Prometheus (+ alerts at /alerts) | http://127.0.0.1:9090 |

The first start takes about 20 minutes: it builds the image, then builds the search index once. After that, starting takes seconds. Stop with Ctrl+C or `docker compose down`.

### Option B — Python (for coding and running tests)

Python 3.12 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # then add your OpenRouter key
python app.py                   # http://127.0.0.1:7861
python -m unittest discover -s tests
```

Optional, with Docker Desktop running: build the locked-down code sandbox once.

```bash
docker build -t analystdesk-sandbox -f docker/sandbox/Dockerfile .
```

The data is already in the repo: 10-K passages and SEC XBRL facts for 15 companies, FY2022–2024. There's no SEC download. The first search builds the vector index (about 10 minutes on CPU, once).

---

## 2. Tour of the app

| Tab | What it is |
|---|---|
| 📈 Dashboard | EDGAR-verified revenue, margins and income |
| 💬 Research Chat | **C0** baseline: a fixed pipeline with one model call; "How this answer was built" shows its steps |
| 🤖 Research Agent | **C1** (one agent) or **C2** (team). Flow: plan → approve → 👥 team board and live tool calls → checked note → approve, edit or reject → publish. Also: your runs (click to resume), 🧠 Memory, 📘 Playbook, 📚 Published notes |
| 📏 Evaluation | Golden set; run C0/C1/C2; results (E1 table, per-case grid); ⚖️ judge calibration |
| 🔍 Data Explorer | Search the 10-K passages directly |

**Try it:** Research Agent → choose **C2 · team** → click an example → **Start** → **Approve plan** → watch the team board → review the note.

---

## 3. Read before you build

| File | What's in it |
|---|---|
| [docs/architecture.md](docs/architecture.md) | The architecture and data flow |
| [docs/viva_notes.md](docs/viva_notes.md) | **Why** every part is built the way it is, with likely viva questions per section |
| [docs/evaluation_guide.md](docs/evaluation_guide.md) | How evaluation works and how to read results |
| [docs/evaluation.md](docs/evaluation.md) | Current results (dev set: C0 16/20, C1 19/20, C2 20/20) |
| [docs/memory_policy.md](docs/memory_policy.md) | What memory keeps, who reads it, how to delete it |
| [docs/tools.md](docs/tools.md) | The 8 MCP tools with their schemas |
| [docs/plan.md](docs/plan.md) | Phases, status and contribution log |
| [HANDOVER.md](HANDOVER.md) | Setup details |

---

## 4. Where the code is

| Area | Code |
|---|---|
| Scope, EDGAR facts, numbers | `analystdesk/scope.py`, `edgar.py`, `baseline.py`, `agent/figures.py` |
| 10-K ingestion, retrieval | `analystdesk/ingest.py`, `retrieve.py`, `query.py` |
| MCP servers (tools) | `analystdesk/servers/` (filings-kb, edgar, python-sandbox, research-portal) |
| Agents | `analystdesk/agent/graph.py` (C1 and shared nodes), `team.py` (C2), `hooks.py`, `checks.py`, `runtime.py` |
| Memory, lessons | `analystdesk/memory.py`, `lessons.py` |
| Evaluation | `analystdesk/evaluation.py`, `scripts/run_eval.py`, `scripts/eval_report.py`, `scripts/calibrate_judge.py`, `scripts/reflect.py` |
| Observability | `analystdesk/observability.py`, `docker/prometheus/`, `docker/grafana/` |
| App UI | `app.py`, `agent_ui.py`, `eval_ui.py` |
| Tests | `tests/` |

---

## 5. Working together (please follow)

1. **Pull before you start:** `git pull`
2. **Work on your own branch** and open a pull request to `main`:
   `git checkout -b <yourname>/<feature>` → commit → `git push -u origin <yourname>/<feature>` → open a PR on GitHub.
3. **Run the tests before every PR:** `python -m unittest discover -s tests`
4. **Never commit `.env` or any API key.** Everyone uses their own OpenRouter key.
5. **Keep to your role's area** where you can, and log your work in the contribution log in `docs/plan.md`; the viva asks each person about their own part.

### Independence rules (from the brief, they keep results honest)

| Task | Who |
|---|---|
| Held-out evaluation cases (`data/evaluation/heldout/`) | **Role 5 only.** Whoever tunes the agents must not write or see them |
| Judge calibration labels (📏 Evaluation → ⚖️) | Role 5, checked by role 1 |
| Red-team attacks (E2) | **Role 5.** The person who built the defences must not write the attacks |
| Tuning prompts, agents, lessons | Development cases only |

---

## 6. What's open (pick up from here)

| Item | Lecture | Notes |
|---|---|---|
| Held-out cases (40+) and judge labels (20+) | L13 | Role 5. See `data/evaluation/heldout/README.md` |
| Security: threat model, guardrails, red-team suite (30+ attacks), E2 | L15 | Defences by role 4, attacks by role 5 |
| Review Reflexion lessons, then E3 before/after | L12 | `python scripts/reflect.py data/evaluation/results/eval_dev_merged.json`, then review in 📘 Playbook |
| E4 ablation (critic on/off; table-aware vs plain passages) | L13 | |
| CI with the evaluation gate; clean-machine install check | L16 | GitHub Actions |
| Held-out comparison run 3 times, with the spread | L13 | After the held-out cases exist |
