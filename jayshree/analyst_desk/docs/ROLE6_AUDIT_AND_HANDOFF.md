# Analyst Desk: Role 6 delivery and existing-work audit

**Basis:** Project 5, *Analyst Desk*, pages 15–16 of the supplied capstone guide, plus the general minimum bar (page 3), evaluation protocol and six-role split (pages 4–6). This review is limited to the uploaded repository snapshot; it is not a full acceptance test of a live Docker deployment.

## Delivered in this update

1. **MCP deployment integration:** changed the Gradio research flow (`agent_ui.py`) and FastAPI research runner (`analystdesk/api.py`) from `transport="inprocess"` to `transport="auto"`. In Compose the configured `MCP_URL_*` variables now route calls to the four HTTP MCP services. Without those variables, local development uses stdio; the evaluation harness may still explicitly use in-process MCP.
2. **Operational health smoke test:** added `scripts/ops_smoke.py`. It checks FastAPI liveness and readiness, in-app alerts, actual Prometheus scraping, presence of the `VerifiedShareBelow98` alert, and Grafana health. It makes no model calls or writes. Any failed check produces a nonzero exit status.
3. **CI:** standardized Python dependencies on `requirements.lock` plus CPU-only `torch==2.15.0+cpu` in CI and live-evaluation workflows, matching the Dockerfile. Added Prometheus rule checking and alert-rule tests on every push/PR. Enabled the live C1 development evaluation on same-repository PRs and `main` pushes, in addition to manual triggering; fork PRs cannot access the OpenRouter secret and use the offline CI only.
4. **Alert regression correction:** the Prometheus test fixture records 97 verified / 100 total numbers at 1h, so corrected its expected description from 97.32% to 97%.
5. **Publication safety safeguard (cross-role):** found that the final human gate signed notes even if `check.ok == false`. Updated the graph to reject an `approve` decision for a failed check, the API to return HTTP 409, and the UI to disable the approval button until checks pass. The server-side graph guard remains authoritative regardless of UI/API clients. This does not implement the broader claim-level reviewer and publication-recovery policies.
6. **Tests and documentation:** added tests for the smoke check, HTTP MCP routing and UI approval lockout; corrected the SSE API test parser to ignore valid keep-alive comments; updated the README and architecture notes.

## Existing work audit by role

| Role / criterion | Evidence actually found | Assessment / remaining action |
|---|---|---|
| R1 — domain/product | Final policies, supported scope, acceptance criteria, workflow and work log under `docs/`; 15-company, FY2022–2024 coverage defined | **Specification substantially present.** Product checklist still explicitly calls for version-specific domain-expert inspection, verified review examples and measured real usefulness. Do not report these as completed. |
| R2 — knowledge/memory | 45 passage JSONL files covering 15 companies × 3 years; EDGAR cache; hybrid retrieval/rerank implementation; memory module/policy; 36 retrieval questions and saved retrieval results | **Implemented, partial verification.** Data-integrity tests pass locally. Recall@5 and memory behaviour require reproducing the saved experiments with the pinned full environment. Source eligibility and correction/withdrawal behaviour require more independent evidence. |
| R3 — agents/orchestration | LangGraph source for C1/C2, planning, typed states, parallel research, replan/critic loop, checkpointing and Reflexion playbook | **Code present, live run unverified here.** Fixed a critical failed-check approval bypass. The written policy calls for additional semantic review completeness and publication recovery that the current minimal gate should not be represented as fully implementing. |
| R4 — MCP/tools/control/security | Four FastMCP servers, typed tool results, hooks, HMAC note binding, sandbox runner with import/audit guards | **Code present, security incomplete.** In Compose `SANDBOX_MODE=local` executes model-authored code in a child of an MCP service attached to the internal `tools` network. Python import guards are not a reliable network isolation boundary. Use a genuinely networkless, separately restricted execution boundary before treating the sandbox as hardened. Threat model and a 30+ attack red-team report were not located in the ZIP. |
| R5 — evaluation/red team | 20 development cases, code evaluation, C0/C1/C2 saved development results, separate judge-calibration script | **Not complete for final rubric.** No protected 40+ held-out questions or final three-run held-out results supplied; they may deliberately be kept outside the agent's repository and should stay that way. No 20+ human-labelled judge agreement report, 30+ attack results, or full E2/E3/E4 experimental result set was verifiable from the snapshot. R5 must provide independently generated evidence. |
| R6 — deployment/operations | FastAPI + Gradio, streaming SSE API, Dockerfile, Compose with app/4 MCP/Prometheus/Grafana/Jaeger, metrics, 98% rule, GitHub Actions and dashboards | **Substantial implementation; integration and tests improved.** New automated checks and routing fix included here. Docker build, live HTTP MCP execution, alert firing, Grafana dashboard and OpenRouter-backed gate still require verification on a Docker host with API credentials. |

## Evaluation result interpretation (existing snapshots only)

The committed `docs/evaluation.md` and merged result JSON report **C0 16/20, C1 19/20, C2 20/20** task successes on the **development set**. The mean *number-verification share* was **31.7% / 96.6% / 80.2%** respectively. In the JSON, C1 has three cases with a verification share under 100%; C2 has ten. A task-success result means the scored request criteria were satisfied, **not** that every numeric statement is verified or that the resulting note is eligible for publication. These numbers must not be described as held-out performance. A 98% monitoring threshold is not a publication waiver.

## Checks actually performed in this environment

- `tests/test_api.py`: **23 passed** after the changes (streaming, health/readiness, alerts and approval rejection).
- `tests/test_ops_smoke.py`: **5 passed**, including smoke-check failure detection, configured API transport and UI approval lockout.
- `tests/test_data_integrity.py`: **3 passed** (committed data/value consistency).
- Python compilation checks passed for changed code.
- The final local full-suite discovery ran **131 tests with 17 errors**, all involving unavailable project dependencies (`langgraph`, `fastmcp`, `langchain_core`, `sentence_transformers`, etc.) or tests relying on them. The 114 other tests passed. Initial discovery before the fix had 125 tests with 18 errors, including one SSE test-fixture issue subsequently corrected. Dependency-related failures do **not** establish defects in the corresponding modules. Re-run the entire pinned suite on a complete environment.
- **Not run:** Docker Compose service startup, live FastMCP HTTP integration, `promtool`, actual Jaeger/Grafana/Prometheus dashboards, or OpenRouter model calls. Docker and the project's complete installed Python dependency set are unavailable in this environment. CI workflows were edited but have not been executed on GitHub.

## Role 6 handoff: verification sequence on a teammate's machine

1. Create `.env` from `.env.example`, replace the placeholder `OPENROUTER_API_KEY` locally, and use the repo's `jayshree/analyst_desk` directory. Keep this key out of the repository.
2. Use Docker Desktop and run `docker compose up --build -d` **to test the modified local code**. `docker compose pull` instead downloads the existing published image and will not contain these changes until merged/published. Wait for all services to reach healthy/completed status. Do not use `--volumes` when restarting, or the saved states/approval key will be lost.
3. Run `python scripts/ops_smoke.py` to verify service health, Prometheus scraping and alert configuration. Check Jaeger separately at `http://127.0.0.1:16686`.
4. Run one C1 and one C2 request through the actual Gradio UI: approve the plan, see progress, verify the draft and pause, edit and recheck, then approve **only a note with passing checks**. Inspect whether each tool call uses the intended MCP service. Confirm `published` only after the portal returns a receipt. Resume a paused run after restarting the app container.
5. Open Grafana at `http://127.0.0.1:3000`; inspect verified share, token/cost, latency, critic rejections, tool errors and EDGAR cache hits. Use Prometheus `/alerts` for the alert and an injected **test-only** metric stream or the alert-rule test for an under-98% proof. Record screenshots/short evidence clips from the real running stack; do not manufacture them.
6. Confirm required GitHub checks after pushing the branch: offline tests/Compose/`promtool` checks, the image build, and the live C1 gate with `OPENROUTER_API_KEY` configured. For rubric evidence, preserve a genuine failed CI run and explain the failure and subsequent fix. The 20-case development gate is not a substitute for the independently held-out result.

## Final submission blockers by owner

- **R4:** networkless sandbox hardening and real red-team/injection evidence; reviewer authorization and the broader write/recovery threat model.
- **R5:** independently held-out 40+ cases, three repeated comparisons, judge-vs-human agreement on at least 20 labels, attack suite of at least 30 cases, and E2/E3/E4 results. Protect these cases from agent and optimizer access.
- **R1/R3/R4:** reconcile the final implementation with strict acceptance/reviewer/reconciliation policies, including incomplete semantic review and unknown publication outcomes. Verify rather than assume that all published notes conform.
- **R6:** perform Docker and CI checks above on real infrastructure, then capture actual service/alert/trace evidence. Until this happens, the deployment should be labelled "implemented, not end-to-end validated".

## Additional Role 6 evaluation/CI corrections in the final handoff

This repository revision adds an offline auditor, three-live-run held-out spread tool,
report provenance hashes, an explicit empty-heldout error, strict case-selection checks,
atomic in-progress evaluation result snapshots, and a CI audit of all 20 committed
development cases. The live GitHub Actions C1 gate now also audits its own saved scores
and uploads its audit files. The CI success gate rejects run errors, even when the
aggregate 95% task-success threshold happens to pass.

The committed development evidence is in `docs/role6_development_evidence.md` and
`data/evaluation/results/role6_dev_audit.json`. It is not a fresh experiment. It
includes the important pooled-verification correction: C0 = 2/54 (3.7%),
C1 = 77/83 (92.8%), C2 = 143/200 (71.5%). Historical case means include
`0/0`-number notes as 100%, unlike the pooled operational metric.

After a genuine Docker run, use `python scripts/ops_smoke.py --output
 data/evaluation/results/role6_ops_smoke_local.json` to save an actual timestamped
six-check deployment record. Review its status before committing. A successful smoke
check is only one piece of L16 evidence and does not prove a successful agent run.

Before claiming final evaluation completion, obtain independently labelled 40+ held-out
cases, an OpenRouter key, three genuinely executed held-out result files per model
configuration, human judge labels and security evaluation from Role 5, and live Docker
and Actions logs. Do not include `.env`, API keys or private watchlists.
