# Phase 1 — Existing Contracts and Safety Expectations

Prepared 11 November 2026 against `f813e4e61bfcb712d37756b98e1bbded92230f8e`. Scope: static contract inventory, preservation decisions, mapping to existing regressions, and the full offline gate. No production code, prompts, calculations, scoring, data, or feature behavior is changed. This is an engineering preservation review, not independent product-policy certification or owner approval for deletions.

## Recorded artifacts

- [interfaces.json](interfaces.json): static AST inventory of 103 Python files, public function signatures, imports/callers, 41 annotated schemas, and six HTTP routes. Imports inside functions are included; runtime-generated consumers are not proven complete.
- [build_launch_references.json](build_launch_references.json): 114 lexical references from launchers, Compose, Dockerfile, and workflows, including working-directory and COPY dependencies.
- [frozen_hashes.json](frozen_hashes.json): 123 source/test/tooling/configuration/deployment hashes, frozen before this phase's documentation changes.
- [safety_test_map.csv](safety_test_map.csv): preservation categories mapped to actual Phase 0 discovered test IDs; a relevance map, not proof that every clause is covered.
- [starting_git_status.txt](starting_git_status.txt): existing user changes and Phase 0 artifacts, retained as the starting checkpoint.
- `test_ids.json`, `test_results.json`, `mock_tests.log`: this phase's separate full offline test evidence.
- `validation.json`: Phase 0 test-ID/skip comparison and frozen-file verification.

## Public entry points and caller contracts

| Surface | Existing contract to preserve | Main consumers / move risk |
|---|---|---|
| `python app.py` | Builds Gradio UI and FastAPI service; defaults to `127.0.0.1:7861`; reads application-root `.env` | Docker CMD/Compose, README, local users. Preserve a thin compatible wrapper and update UI imports rather than starting multiple apps. |
| `agent_ui.py`, `eval_ui.py` | Research/run-history/memory UI and evaluation UI helpers | `app.py` and tests patch module-qualified names. A file move requires updating both runtime imports and mock patch targets. |
| `python -m analystdesk` | `--companies`, required integer `--years`, `--mode scope\|baseline`; scope validates without proving source availability | `analystdesk/__main__.py`; baseline may fetch uncached sources, so do not execute it for migration validation. |
| `analystdesk.agent.runtime` | `run_until_gate`, `get_run`, `list_runs`; resumed runs retain stored mode/memory setting; snapshots contain `values`, `interrupts`, `next` | API, UI, evaluator, mocked graph tests. Preserve async signatures and checkpoint interpretation. |
| `analystdesk.servers.*` | Four registered `python -m` server modules; stdio/HTTP and in-process test transport | `SERVERS`, `servers/client.py`, Compose commands, runtime. Changing package names alone can break subprocesses even when direct imports pass. |
| Utility scripts | Existing command flags and root discovery | CI, documentation, evaluation/report tools. Inventory CLI arguments statically; never execute paid runners to check moves. |

The AST import inventory is the caller map for Python consumers. The launch-reference inventory covers executable/configuration references. Neither replaces later searches for dynamic imports, strings used by patches, generated links, or platform-specific invocations before a particular move.

### HTTP and event-stream compatibility

Preserve `create_app` dependency injection so tests can supply fake runners, loaders, readiness checks, and alert readers.

| Method / route | Request/response behavior |
|---|---|
| `GET /healthz` | `{"status":"ok"}`. |
| `GET /readyz` | `ready` on success; injected readiness failure gives 503 with `not_ready` reason. |
| `GET /api/alerts` | Available alerts; unavailable Prometheus yields 503 without pretending the alert list is empty. |
| `POST /api/research` | `ResearchRequest`: nonblank request and analyst, `mode=c1\|c2`, `memory_on`; returns SSE. C0 remains a UI/fixed-pipeline path, not a new API mode. |
| `POST /api/research/{run_id}/decision` | `ResearchDecision`: approve/edit/reject plus plan/note/year confirmation/approver/reason. Preserve gate-specific validation, 404 missing runs, 409 invalid state/failed approval, and 422 invalid payloads. |
| `POST /api/notes/{note_id}/lifecycle` | Withdraw/supersede decision, reason, actor, optional replacement/signature; lifecycle conflict yields 409. |

SSE uses `started`, `progress`, `result`, and `error`; retain event framing and run IDs. Summary fields include status, plan, assumptions, year-confirmation requirement, draft, and check. Preserve error/stale-review and disconnect cancellation behavior. Do not add API fields/actions during cleanup. In particular, do not assume every graph/portal optional field is already accepted by `ResearchDecision`; schema parity is a separate behavior question.

## Workflow and data contracts

- **C0:** fixed retrieval, numerical preparation, model answer, optional charts/context. Preserve its result shape and limitations. It is not the gated C1/C2 publication workflow.
- **C1:** one tool-using agent with bounded research and shared plan/check/note/publish nodes.
- **C2:** lead plus per-company research/risk specialists and quant; typed evidence handoffs; preserve parallel accumulation and quarantine verification instead of introducing free-form specialist prose.
- **Budgets:** `tool_budget(n)` defaults to `12 + 12 * max(1,n)` unless overridden by `AGENT_MAX_TOOL_CALLS`; C2 specialist shares sum to the same budget. `MAX_REVISIONS=2`, `MAX_REPLANS=1`, token default 120000, context default 60000 characters. Preserve switches and shared experiment conditions.
- **Plan:** companies, fiscal years, subquestions, outline. **Draft:** title, Markdown body, tickers. **AgentState:** preserve keys, reducers, interrupts, counters, review context, mode/memory fields, and outcome interpretation recorded in the AST snapshot. Do not silently migrate old checkpoints by renaming fields.
- **Handoffs:** agent/company, claims/facts, dropped evidence, passage/fact IDs, risk coverage, confidence, errors, round, tool/token/call counts. Preserve `RiskPairCoverage` and honest missing/excerpt-only states.
- **Identifiers/calculations:** preserve passage/fact tags, period/metric identity, raw-value calculations, rounding, signs, currency/scale, and existing source-version handling. Hashes freeze current behavior, not certify financial adequacy.

### MCP permission and result boundaries

Keep the eight tools and their signatures: `search_filings`, `get_passage`, `list_filings`, `get_financials`, `get_fact`, `run_python`, `get_past_notes`, `publish_note`. The AST inventory records their arguments. Retain result envelopes (`ok`, typed `error`, tool-specific fields), MCP annotations, transport URLs, and server IDs.

`SERVERS` and `AGENT_TOOLS` remain the permission authority. Only the publisher receives `publish_note`; writer has no tools; researcher uses filing reads; quant uses financial reads/sandbox; risk uses filing/history reads subject to memory filtering. `research_tools` removes history access when memory is off or evaluation is on. Keep hooks' allowlists/budgets, guarded tool loading, quarantine, and secret filtering. No MCP server needs the model provider key; approval-secret access remains restricted to the portal.

## Storage, signatures, and path-sensitive contracts

| Resource | Current path/default and preservation requirement |
|---|---|
| Checkpoints | `data/runs/checkpoints.sqlite`, override `AGENT_CHECKPOINTS`; runtime computes application root with three parent levels. Preserve thread IDs, schemas, and saved state semantics. |
| Memory/playbook | `data/memory/memory.sqlite`, override `MEMORY_DB`; `memory.py` computes root with two parent levels. Keep namespace keys, suppression, lifecycle handling, and frozen lesson identity. |
| Portal | `data/portal/portal.db`, override `PORTAL_DB`; portal computes three parent levels. Retain notes, approval-context, and lifecycle tables without rebuilding production stores. |
| Approval | `data/approval/approval.key` or `APPROVAL_SECRET`; optional registered approver keys under `data/approval/approvers`, override `APPROVER_KEYS_DIR`. Moving approval modules must not generate a different key path. |
| Corpus/index | `ingest.py`: `data/edgar_cache`, `data/passages`, `data/passages_plain`; `retrieve.py`: `data/index`. Preserve IDs, fingerprints, corpus selection and cache behavior. |
| Config | `config/llm.toml`, loaded relative to package; preserve validation, prompts, models, output caps, and environment overrides. |
| Sandbox | `sandbox_runner.py` located beside `sandbox.py`; preserve this relationship or explicitly update the runner path. |
| MCP subprocesses | `servers/client.py` derives `PROJECT_DIR` by three parents and launches registered modules with that cwd. Update coherently after grouping. |
| Compose | Source mounts, application `/app` layout, named volumes `index`, `runs`, `memory`, `portal`, `approval`, `evaluation-work`, service names, internal tool network, ports and readonly boundaries must retain their meaning. Do not start services to validate this phase. |

Signed content is canonical JSON of title/body and sorted uppercase tickers. HMAC claims include note hash, approver, timestamp, and optional review context. Edits require fresh checks/approval. Preserve legacy/current context handling instead of issuing new tokens during migration. Graph/API checks block ordinary approval of failed notes; portal independently verifies applicable signatures/context. A confirmed publication requires `ok=true`, a positive integer note ID, and the matching note hash. Unknown outcomes and memory-sync failures remain distinct; no automatic republish is introduced.

Credentials, live databases, approval keys, Docker volumes, protected evaluation contents, and case ownership remain outside this phase. No reads of `.env` values or production stores are needed to inventory their source-defined paths.

## Safety regression mapping and limits

The CSV maps discovered IDs to categories using existing test modules/names. Review these anchor tests when moving their implementations:

| Preserve | Existing test anchors |
|---|---|
| Financial associations/precision | `test_gap_fixes`: ratio company/year/concept/window checks, reversed years, negative revenue, signed/zero values, scale mismatches; `test_checks`, `test_figures`, `test_edgar`, `test_baseline`. |
| Full required claim review | `test_gap_fixes`: empty/duplicate/invalid verdicts, judge outage, uncited/short/title claims, missing passages, required live judge. `test_risk_semantic` preserves fake-judge scoring behavior. |
| Bounded revisions and approval | `test_experiments`, `test_graph`, `test_api.test_unverified_note_cannot_be_approved`; graph gates, edit invalidation and portal checks in `test_tools` and security tests. |
| Source/lifecycle freshness | `test_review_snapshot`: missing evidence, stale sources, changed review context, old checkpoint snapshots; `test_source_review` and portal lifecycle tests. |
| Receipt and recovery truthfulness | `test_gap_fixes`: positive matching receipt, lost response, memory failure retains publication. |
| Memory/privacy/playbook | `test_memory_off`, `test_memory`, `test_lessons`, deleted-memory suppression and frozen-playbook tests; private-watchlist checks in `test_gap_fixes`, `test_guards`, `test_secrets`, security tests. |
| Fair orchestration/budgets | `test_graph.SameBudgetTests`, scripted `test_team_e2e` C1/C2 paths and hook enforcement. |
| Evaluation integrity | `test_eval_gate`, `test_role6_evaluation`, `test_experiments`, `test_redteam`; wrong associations/signs and incomplete review in `test_gap_fixes`. Tests use mock/local fixtures; no new protected case inspection. |

Passing mocks does not certify live model quality, whole-section risk coverage, filing authority, independent human labels, isolation across OS accounts, production identity, end-to-end deployment security, or measured benefit. The Windows gate does not exercise Docker isolation or Unix file modes; Python 3.12/Linux parity remains a CI/platform verification boundary. No uncovered policy behavior is implemented here. Retain these as separate review obligations, not cleanup acceptance claims.

## Checkpoint, review, and rollback decisions

1. Preserve Phase 0 artifacts; Phase 1 writes to its own directory. Freeze source/test/configuration/launch hashes and compare them after validation.
2. Run the existing network-blocked runner using `--report-dir docs/migration/phase1`. Compare exact test-ID lists, executed counts, skip IDs/reasons, failures, and errors with Phase 0. No unexplained disappearance or new skip is acceptable.
3. Review static inventories against the tables above: routes, schemas, storage expressions, imports, and launcher references are captured. Dynamic and platform consumers remain explicit limitations for each later move. No owner sign-off is fabricated.
4. If this phase fails, stop before Phase 2. Preserve logs and revert only Phase 1 documentation/log-row changes. There are no production changes to roll back; never reset unrelated dirty/untracked user files or restore runtime databases.
5. Before later package moves, consult both inventories, update all affected imports/patch targets/path calculations, and run the full gate after each subphase. Do not regenerate corpus, evaluation results, approvals, or frozen lessons merely to make changed paths pass.

Completion requires a passing full gate, unchanged frozen hashes, identical test discovery/skips, completed inventory review, and explicit limits above. The cleanup plan's execution record and `validation.json` record the final decision; future phases remain separate.

## Completed checkpoint

**Phase 1 complete.** Full offline gate: 538 discovered/run, 533 passed, five unchanged skips, no failures/errors, exit 0. Test IDs exactly match Phase 0. All 123 frozen file hashes are unchanged. Static review confirmed six HTTP routes and mapped 462 existing test IDs to preservation categories. See [validation.json](validation.json) and [test_results.json](test_results.json). No application behavior, source locations, prompts, experiment configurations, or scoring changed. Independent domain/deployment verification remains outside this checkpoint. Phase 2 has not started.
