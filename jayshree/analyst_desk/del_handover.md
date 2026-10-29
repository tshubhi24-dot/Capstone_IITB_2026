# Analyst Desk — Setup

IIT Bombay Agentic AI Capstone · Project 5

Two ways to run it. **Option A (Docker)** needs only Docker Desktop; **Option B
(Python)** is for developing and running the tests.

---

## Option A — Docker (recommended for trying it out)

1. Install Docker Desktop (Windows: keep "Use WSL 2"; Mac: Intel or Apple
   Silicon). No Docker account needed. Start it and wait for "Engine running".
2. Clone and enter the project:

   ```bash
   git clone https://github.com/tshubhi24-dot/Capstone_IITB_2026.git
   cd Capstone_IITB_2026/jayshree/analyst_desk
   ```

3. Create `.env` from `.env.example` with **your own** OpenRouter key (never commit it).
4. Start everything:

   ```bash
   docker compose up --build
   ```

   Open <http://127.0.0.1:7861>. The first start builds the image (~10 min,
   ~2–3 GB download) and then the vector index (~10 min on CPU); later starts
   take seconds. Stop with Ctrl+C, or `docker compose down`.

What starts: the app, the four MCP servers (filings-kb, edgar, python-sandbox,
research-portal), a one-off index builder, and the observability stack:
Jaeger traces <http://127.0.0.1:16686>, Prometheus <http://127.0.0.1:9090>
(alerts at /alerts), Grafana <http://127.0.0.1:3000> (dashboard "Analyst Desk").
The MCP servers sit on an internal network with no internet access; only the
app can reach OpenRouter.

## Tour of the app

| Tab | What it is |
|---|---|
| 📈 Dashboard | EDGAR-verified revenue, margins and income |
| 💬 Research Chat | C0 baseline (fixed pipeline, one model call), with "How this answer was built" |
| 🤖 Research Agent | C1 single agent or C2 team: plan gate → live team board and tool calls → checked note → approve/edit/reject → publish. Also: your runs, 🧠 Memory, 📘 Playbook (review lessons), 📚 Published notes |
| 📏 Evaluation | Golden set, run C0/C1/C2 on it, results (E1 table, per-case grid), ⚖️ judge calibration (label claims, Cohen's kappa) |
| 🔍 Data Explorer | Search the 10-K passages directly |

Reasoning behind every design decision: `docs/viva_notes.md`. Results so far:
`docs/evaluation.md` (dev set), `docs/retrieval_eval.md` (Recall@5).

## For role 5 (evaluation and red team)

- Write the **held-out** cases in `data/evaluation/heldout/` (see the README
  there). Whoever tunes the agent must not write or see them.
- Label the judge-calibration items in the Evaluation tab (⚖️), then compute kappa.
- The red-team suite (30+ attacks, defences on vs off) is yours too: the
  person who built the defences must not write the attacks.

## Option B — Python (development and tests)

Tested with Python 3.14 on Windows (3.12+ should work).

```bash
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` as in step 3 above, then:

```bash
python -m unittest discover -s tests                      # all tests
python -m analystdesk --companies MSFT GOOGL JPM --years 2022 2023 2024 --mode baseline
python scripts/eval_retrieval.py                          # Recall@5 report
python app.py                                             # http://127.0.0.1:7861
```

With Docker Desktop running, build the code-sandbox image once so
`run_python` uses a locked-down container (otherwise it falls back to a local
guarded process and the Docker tests are skipped):

```bash
docker build -t analystdesk-sandbox -f docker/sandbox/Dockerfile .
```

## Data — already in the repo

`data/passages/` (table-aware 10-K chunks), `data/passages_plain/` (plain-text
chunks for the E4 ablation) and the EDGAR XBRL/submissions JSON in
`data/edgar_cache/` are committed, so a fresh clone needs **no** SEC download.

Built locally on first use (not in git): the Chroma vector index
(`data/index/`, or a Docker volume) and raw 10-K HTML
(`data/edgar_cache/filings/`, only needed to re-chunk:
`python -c "from analystdesk.ingest import ingest_all; ingest_all()"`).

## Next phase

Phase 4: C1 single agent in LangGraph over the MCP tools (plan shown to the
analyst, SQLite checkpointer, stop and resume). See `docs/plan.md`; tool
schemas are in `docs/tools.md`; reasoning for every decision so far is in
`docs/viva_notes.md`.

---

Shared repo: https://github.com/tshubhi24-dot/Capstone_IITB_2026  
Personal fork: https://github.com/jayshree-rajan/Capstone_IITB_2026
