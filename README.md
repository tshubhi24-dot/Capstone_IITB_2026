# Analyst Desk

An SEC-filings research application for 15 companies across fiscal years 2022?2024. It retrieves filing evidence, calculates financial figures and drafts cited research notes. Compare a fixed pipeline (**C0**), a single agent (**C1**) and a specialist team (**C2**). C1/C2 require human plan review and approval of the verified final note before publication.

## Setup and start

Install **Git** and **Docker Desktop/Engine with Compose**. Research and live evaluations require a funded **OpenRouter API key**.

```text
git clone https://github.com/tshubhi24-dot/Capstone_IITB_2026.git
cd Capstone_IITB_2026/analyst_desk
```

Copy `.env.example` to `.env` (`Copy-Item .env.example .env` in PowerShell; `cp .env.example .env` on macOS/Linux), then set `OPENROUTER_API_KEY`. Preserve an existing `.env`; never commit credentials.

| Action | Windows PowerShell | macOS/Linux |
|---|---|---|
| Start | `.\deployment\start.bat` | `bash ./deployment/start.sh` |
| Stop | `.\deployment\stop.bat` | `bash ./deployment/stop.sh` |

Open **http://127.0.0.1:7861**. Start selects the published image for the latest `main` commit; stop preserves data volumes. To build and run the checked-out source instead:

```text
docker compose --project-directory . -f deployment/compose.yaml up --build
```

## Prepare Python commands

The commands below run from `analyst_desk/` in a local **Python 3.12** environment, separate from Docker. First local research may download models and build an index.

Windows:

```powershell
.\deployment\setup.bat
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Generate evidence

Replace `TAG` with a unique run label. Keep the code, model settings, input cases and frozen playbook fixed across comparisons. Live model runs use API credit; they stop at the note gate without publishing.

### Offline tests

```text
python scripts/run_mock_tests.py --report-dir docs_notfor_submission/migration/final-TAG
```

Uses mocks and blocks network access. Saves test IDs and pass/fail/skip metadata; this verifies regressions, not live model quality.

### Development ? 44 cases, C0/C1/C2

```text
python scripts/run.py eval --configs c0 c1 c2 --split dev --min-cases 44 --tag dev-TAG
python scripts/report.py audit --input data/evaluation/results/eval_dev_dev-TAG.json --cases data/evaluation/development --configs c0 c1 c2 --min-cases 44 --out-md submission/dev-TAG.md --out-json submission/dev-TAG.json
```

### Held-out ? 64 cases, three repeated runs

Held-out execution belongs to the independent evaluator. Before running, review and freeze development-derived lessons in the **local** app's Playbook. To propose lessons, run `python scripts/run.py reflect data/evaluation/results/eval_dev_dev-TAG.json`; to review them, stop Docker and launch `python deployment/app.py`. Local and Docker playbooks use separate stores. Never learn from held-out results.

```text
python scripts/run.py eval --experiment e1_c0_c1_c2 --split heldout --min-cases 64 --tag heldout-TAG-1
python scripts/run.py eval --experiment e1_c0_c1_c2 --split heldout --min-cases 64 --tag heldout-TAG-2
python scripts/run.py eval --experiment e1_c0_c1_c2 --split heldout --min-cases 64 --tag heldout-TAG-3
python scripts/report.py repeats --runs data/evaluation/results/eval_heldout_heldout-TAG-1.json data/evaluation/results/eval_heldout_heldout-TAG-2.json data/evaluation/results/eval_heldout_heldout-TAG-3.json --gold data/evaluation/heldout --configs c0 c1 c2 --min-cases 64 --out submission/heldout-TAG.md
```

Use the same frozen snapshot for all repeats. The report writes Markdown and JSON; the combined repository set is not automatically a newly certified blind benchmark.

### Red-team ? defences on/off, C1/C2

```text
python scripts/run.py redteam --experiment e2_defences_on --tag redteam-on-TAG
python scripts/run.py redteam --experiment e2_defences_off --tag redteam-off-TAG
```

Runs 32 attacks plus clean development cases to measure false blocks. Keep clean-case replay enabled. JSON files retain per-case outcomes and summaries.

### Retrieval ? table-aware versus plain passages

```text
python scripts/run.py retrieval --variant both
```

Runs 36 labelled queries using local retrieval models; first use may download models/build indexes. Saves timestamped JSON and updates the retrieval report.

Raw evaluation outputs live in `data/evaluation/results/`. Preserve failures, timeouts, model/configuration provenance and input hashes. **Fresh full submission runs remain pending; archived scores and the billing-blocked pilot are not final evidence.**

## Scripts and configuration

| Item | Purpose |
|---|---|
| `config/llm.toml` | Model IDs for research/judging/reflection, prompts and output-token limits. `.env` supplies credentials. |
| `scripts/run.py` | `eval`, `redteam`, `retrieval`, `financebench`, `memory`, `calibrate` and `reflect` workflows. |
| `scripts/report.py` | `audit` a recorded evaluation or summarize held-out `repeats`; no model calls. |
| `scripts/ops.py` | `smoke` checks deployment health; `backfill-memory --analyst analyst` restores eligible published-note memory. |
| `scripts/run_mock_tests.py` | Offline unit, integration and security regression suite. |
| `experiments/` | E1: C0/C1/C2; E2: defences; E3: playbook lessons; E4: critic and passage ablations. E1/E3/E4 default to held-out; override both comparison arms with `--split dev` when developing. |

Use `python scripts/run.py --help` or append `--help` after any workflow for available parameters. For a running deployment, `python scripts/ops.py smoke` checks health without model calls.

<a id="evaluation-reference-material"></a>

## Project layout

| Folder | Contents |
|---|---|
| `analystdesk/` | UI/API, agents, MCP tools, finance, retrieval, memory, verification and evaluation implementation. |
| `deployment/` | App launcher, Dockerfile, Compose and setup/start/stop scripts. |
| `docker/` | Monitoring configuration, dashboards, alert tests and sandbox image. |
| `data/` | Filing passages, SEC caches, runnable evaluation cases, new results and archived historical runs. |
| `evaluation/` | Evaluator-only reference answers and supporting reviews; excluded from agent prompts, tools, indexes and memory. |
| `tests/` | Python `unittest` cases grouped into unit, integration and security tests. |
| `submission/` | Evaluation reports and submission artifacts. |

`.runtime/` contains ignored local indexes, checkpoints, memory and portal state.
