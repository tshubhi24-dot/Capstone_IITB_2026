# First two-company research journey

This step builds a fresh Docker Compose workflow for Microsoft and Apple, fiscal years 2023–2025. It uses actual cached SEC annual facts and filing passages. Research is deterministic and offline: BM25 lexical retrieval, fixed calculations and text comparisons, with **zero language-model calls and a zero-dollar model budget**.

**Current verification status:** the local Docker journey completed on 24 October 2026. Both version-bound human review gates completed; one note was saved. The run made 18 actual MCP calls, verified 18 displayed financial values and made zero model calls. All 53 local automated tests and eleven runtime-readiness checks passed. The note survived an application restart; all four running MCP services rejected unauthenticated requests. See the [journey receipt](../evidence/two_company_journey.json), [runtime checks](../evidence/runtime_checks.json) and [restart/authentication evidence](../evidence/journey_verification.json).

## 1. Prepare the source snapshot

Open a terminal in `amit/analyst_desk` within this repository. Docker Desktop must be installed and running; the launcher uses its `desktop-linux` context without changing the global context. A local Python interpreter runs the setup helpers; application dependencies are installed in the Docker image.

A fresh clone needs a **reviewed public SEC corpus** matching the [source schema](../data/README.md). The helper extracts MSFT and AAPL for 2023–2025, checks annual revenue/operating-income pairs, and records source hashes. It does not download filings or independently certify original Item boundaries.

```sh
python3 ops/start_journey.py --prepare --source-corpus /absolute/path/to/reviewed-sec-corpus.json
```

If the prepared source snapshot already exists, use `python3 ops/start_journey.py --prepare`. Preparation validates configuration and creates the private analyst credential; it does not start containers. Missing sources cause a clear failure.

The local snapshot stays in ignored `.runtime/journey/sources/`. The shareable [source manifest](../data/source_manifest.json) identifies twelve annual facts, source URLs and provenance hashes. Public source data can be extracted from an existing reviewed cache; no older application code or historical results are imported.

## 2. Build and start Docker Compose

```sh
python3 ops/start_journey.py --start
```

The first start downloads images and installs dependencies. Services start individually after successful credential initialization, with bounded waits and a short readiness retry for transient proxy errors. If macOS or Docker displays a permission/setup prompt, complete the on-screen step; do not enter passwords into chat. The launcher uses the dedicated `analyst-desk-journey` project and loopback-only addresses:

- Research desk: <http://127.0.0.1:18080>
- Monitoring dashboard: <http://127.0.0.1:13080>

The research desk's Connection settings need the local analyst token from `.runtime/journey/credentials.env`. Keep this file private; do not put its value in Git, screenshots, chat, or a URL. The launcher preserves existing credentials. It does not copy provider keys into this offline stack.

The app calls four authenticated MCP services. Financial calculations run through a separate pandas worker with no network access, a queue-only mount, a read-only root filesystem and bounded resources. Prometheus scraping and Grafana readiness were verified in the recorded run. Alert firing remains untested.

## 3. Create the research request and inspect its plan

```sh
python3 ops/journey_session.py prepare
python3 ops/journey_session.py status
```

The first command submits the two-company request and stops at the plan gate. Repeating it reuses the saved session unless a new run is explicitly requested. The second command reports the current stage. Neither command approves anything.

Review the complete pending plan in the desk or the private session snapshot. It covers original annual facts and actual fiscal periods, operating margins, adjacent-year risk-section text comparisons, citations and comparability limits. The helper records the run ID and exact pending payload hash. A plan edit creates a new version requiring review again.

## 4. Human gate one: decide on the exact plan

The analyst must explicitly **approve, edit or reject** the displayed plan. A general request to build the application is not an approval of a particular research plan.

The manual client's `decision` operation requires the run ID, `--kind`, `--action`, the exact `--expected-hash`, and explicit `--human-confirmation`. An edit also requires `--edits-file` containing a JSON object. Consult `python3 ops/journey_session.py decision --help` after reviewing the payload. This runbook does not provide an executable approval command or prefilled confirmation.

An operator may relay the analyst's actual decision; the helper records that supplied confirmation and does not independently authenticate human identity. A stale hash or mismatched stage is rejected.

## 5. Research, calculate and inspect the draft

After explicit plan approval, LangGraph dispatches company research branches in parallel. The workflow reads source facts through MCP, calculates six company-year margins in the isolated worker, independently checks source values and arithmetic, compares cached risk-section text, and assembles a cited draft.

Use `python3 ops/journey_session.py status` to wait for the next pause. Inspect the full draft, source evidence, actual fiscal periods, calculation checks and caveats in the desk. An error is surfaced without silently substituting invented facts or a host-side calculation.

## 6. Human gate two: decide on the exact note

Publication requires a separate explicit approval of the checked note's exact payload hash. The analyst can edit or reject it. An edit invalidates the previous approval, reruns code checks and requires a new review. Failed checks block approval.

Only the publisher role can call the publication tool. The portal verifies an expiring, exact-payload capability against the stored human approval and saves a note once per run. Repeating the same valid publication is idempotent; different content cannot reuse that run's publication identity. Plan approval alone never authorizes publication.

## 7. Inspect memory and retain evidence

Named Docker volumes retain SQLite run history, audit events, LangGraph checkpoints, approvals and approved notes across container restarts. Paused reviews keep their exact payload hash. Removing volumes deletes that persisted state. Only approved notes enter the reusable note library; a checkpoint is not an approved research result. This first slice does not implement the architecture's full preferences or reviewed-lessons memory.

A process failure during an active tool operation currently needs manual recovery; there is no automatic startup recovery scan. Persistence tests cover paused review gates.

The helper saves full run snapshots and supplied confirmation text privately in `.runtime/journey/session.json`. Its shareable `evidence/two_company_journey.json` receipt contains stage, hashes and measured usage without credentials or full private outputs. A receipt proves only the events it records; it must not be presented as evidence of unperformed approvals, publication or full capstone evaluation.

## Limits and team handoff

- BM25 is lexical retrieval. Learned embeddings, a vector/reranker workflow, live agent reasoning and semantic claim evaluation are not active.
- Risk comparisons detect text changes in all available cached Item 1A chunks. Original Item boundaries still require domain review. Text differences do not establish economic materiality or added/removed risks.
- Different issuer fiscal calendars remain visible. The note is a research rehearsal and provides no investment recommendation.
- This is an ordinary learning run. Protected final questions, hidden gold labels and final benchmark scoring are outside this workflow.
- Six-person team integration, ingestion adapters and the remaining full-capstone requirements need separate work and review.

Steps 1–4 were pushed as separate commits on `Amit/analyst_desk`: `9702d65` (definition), `fb01fc2` (evaluation preparation), `586e747` (architecture), and `478d05e` (fresh implementation). Step 5 records startup recovery, live readiness and the actual human-approved journey. Work stays under `amit/analyst_desk`; no direct merge to `main` is authorized. See the [step log](../STEP_LOG.md) and [contribution record](CONTRIBUTIONS.md).
