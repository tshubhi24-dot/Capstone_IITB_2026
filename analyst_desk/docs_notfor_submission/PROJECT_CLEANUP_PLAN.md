# Analyst Desk: Cleanup, Consolidation, and Presentation Plan

## 1. Purpose and evidence boundary

Prepared 11 November 2026 against checkout `f813e4e`. All cleanup phases 0-6 are complete within the offline migration scope. This document retains the original plan and execution register; the [final report](migration/phase6/REPORT.md) records the implemented outcome and remaining verification limits.

Primary reference: [Current Implementation Gap Analysis](../not_for_submission/documents/CURRENT_IMPLEMENTATION_GAP_ANALYSIS.docx). It reviews revision `875438652f2230103175332a7519064ecb482d02`, with observations from 6–7 November. Its 77 rule groups and 28 frontend messages describe that historical review, not the current application's verified status. Compare every relevant finding with [gap_closure.md](gap_closure.md), current code, and independent tests before declaring closure. Do not convert overlapping findings into a compliance percentage.

The cleanup must improve navigation and maintainability while preserving source evidence, financial correctness, exact-note approval, privacy boundaries, and reproducible C0/C1/C2 experiments.

## 2. Findings from the current repository

| Observation | Planning decision |
|---|---|
| The application, tests, Dockerfile, and Compose stack live under `analyst_desk/` | Establish one contributor-neutral application root through a separate migration PR. |
| `shubhi/analyst_desk/` currently contains a local `.env`; no tracked files were found under `shubhi/` | Treat it as local configuration, not a second application. Compare variable names locally without exposing values; retain until its owner confirms migration. |
| `app.py`, `agent_ui.py`, and `eval_ui.py` are separate UI components | Group by UI responsibility; do not delete them as duplicate entry points. |
| C0, C1, and C2 share financial and retrieval concerns but implement different experimental workflows | Consolidate common contracts and helpers while preserving the three execution paths and budgets. |
| Numerous specification/review documents have both Markdown and Word editions | Choose an editable source and document export provenance. Similar titles or extensions alone do not justify deletion. |
| `requirements.txt` expresses dependency intent; `requirements.lock` pins deployment versions | Keep both and document the lock update process. |
| `data/passages/` and `data/passages_plain/` serve retrieval/comparison purposes | Preserve until retrieval ablations and all consumers have been checked. |
| Local `.venv/`, `__pycache__/`, and a `~$presentation.pptx` lock file are present | Generated/temporary cleanup candidates; exclude from submission and remove only when unused. |

A SHA-256 comparison of nonempty tracked Python, Markdown, shell/batch, YAML, TOML, and text files found no byte-identical duplicates in the inspected set. Protected held-out/red-team/reference directories were excluded. This does not establish semantic uniqueness or cover binary documents and datasets.

## 3. Target structure by functionality

Original design target retained for traceability. The implemented structure is documented in the application README: manifest-bound reviews remain at their original paths, redundant category indexes were consolidated, and setup/phase summaries use SETUP.md/REPORT.md.

```text
Capstone_IITB_2026/
  README.md                      # project overview and three-command quick start
  AGENTS.md                      # contributor conventions
  .github/workflows/             # CI, image publication, evaluation gate
  analyst_desk/                  # single application root
    README.md
    Dockerfile
    compose.yaml
    .env.example
    requirements.txt
    requirements.lock
    app.py                       # thin compatible launch wrapper
    start.bat / start.sh          # simple teammate launchers
    stop.bat / stop.sh
    setup.bat
    analystdesk/
      ui/                        # dashboard, research, evaluation interfaces
      research/                  # C0 and chart/conversation helpers
      agent/                     # C1/C2 orchestration, hooks, runtime
      finance/                   # facts, periods, units, figures, source review
      retrieval/                 # ingestion, query decomposition, retrieval
      governance/                # approval, checks, review snapshots
      memory/                    # memory lifecycle and reviewed lessons
      evaluation/                # scorers, experiments, red-team harness
      api.py
      observability.py
      scope.py
      llm_config.py
      servers/                   # MCP adapters; retain module launch contracts
    config/                      # prompts and model configuration
    scripts/
      evaluation/                # runners, reports, calibration, audits
      data/                      # corpus preparation utilities
      operations/                # smoke checks and memory backfill
    experiments/
    tests/
      unit/
      integration/
      security/
      fixtures/
    data/                        # keep existing data paths initially
      passages/                  # immutable reviewed inputs
      passages_plain/            # retrieval comparison corpus
      edgar_cache/
      evaluation/                # controlled cases and traceable results
    docker/                      # sandbox and monitoring configuration
    docs_notfor_submission/
      getting-started/
      architecture/
      policies/
      reviews/
      evidence/
      assets/
      archive/
    submission/                  # curated final deliverables and index
```

Avoid a simultaneous `src/` packaging conversion. Moving packages already changes imports and module commands; introducing installation semantics at the same time adds unnecessary migration work. Runtime databases/indexes remain outside submission bundles, in their existing ignored directories or named volumes, until a separately tested storage-path migration is necessary.

## 4. File movement and consolidation register

Paths below are relative to the current application root unless stated otherwise.

| Pre-migration location | Destination or action | Required checks |
|---|---|---|
| Repository `jayshree/analyst_desk/` | Repository `analyst_desk/` | Update workflow working directories/path filters, image contexts, README links, and contributor instructions together. Keep the package name `analystdesk`. |
| Root `app.py`, `agent_ui.py`, `eval_ui.py` | `analystdesk/ui/dashboard.py`, `research.py`, `evaluation.py`; retain thin `app.py` | Update imports and Docker COPY instructions. Verify UI mounts and API routes. |
| `baseline.py`, `c0_pipeline.py`, `chat_chart.py`, `chat_context.py` | `analystdesk/research/` | Preserve C0 output, charts, and conversation behavior. |
| `edgar.py`, `source_review.py`, `agent/figures.py` | `analystdesk/finance/` | Inventory callers; preserve period, metric, sign, source, and unit semantics. |
| `ingest.py`, `query.py`, `retrieve.py` | `analystdesk/retrieval/` | Keep corpus fingerprints, index rebuild rules, and labelled retrieval measurements stable. |
| `approval.py`, `agent/checks.py`, `agent/review_snapshot.py` | `analystdesk/governance/` | Preserve graph/API/portal enforcement and exact-content binding. |
| `memory.py`, `lessons.py` | `analystdesk/memory/store.py`, `playbook.py` | Preserve database namespaces, deletion suppression, frozen versions, and resume rules. |
| `evaluation.py`, `experiments.py`, `redteam.py` | `analystdesk/evaluation/` | Update evaluator imports without changing scoring or exposing expected answers. |
| Flat utility scripts | Functional `scripts/` groups | Update all invocation examples, CI commands, and ROOT calculations; keep temporary wrappers where needed. |
| Flat policy, review, and architecture documents | Corresponding `docs_notfor_submission/` groups | Maintain a link map and distinguish authoritative policies from historical reviews. |
| Original brief and audit DOCX | `docs_notfor_submission/reviews/source/` with provenance | Preserve originals; add a readable summary and link to them from the evidence index. |
| Slide decks and demo assets | Canonical presentation under `submission/`; supporting assets under `docs_notfor_submission/assets/` | Review revisions, notes, screenshots, and links before retiring an older copy. |

Potential shared helpers should cover raw-value calculations, source identifiers, display formatting, claim inventories, eligibility checks, and UI status messages. First compare behavior and test seams; extract one shared implementation only where semantics match. Keep specialist prompts, orchestration, evaluation isolation, and platform-specific launchers separate where they have distinct responsibilities.

## 5. Removal rules and evidence preservation

Create a reviewed manifest before removal: `path`, `tracked/untracked`, `hash`, `purpose`, `consumers`, `canonical replacement`, `owner`, and `decision`. Check imports, subprocess/module commands, Docker COPY/mounts, CI, documentation links, and generated reports. A text search alone cannot prove dynamically loaded code is unused.

- **Temporary candidates:** inactive Office lock files, Python caches, and abandoned build outputs. Close the owning application first. A virtual environment can be regenerated but is not source duplication.
- **Conditional candidates:** superseded report exports, stale generated summaries, unused compatibility wrappers, and unreachable helper code. Remove only after comparison, reference updates, and verification.
- **Preserve:** original policy/audit records, accepted source caches, experiment configurations, canonical evaluation results, human labels, and evidence needed to reproduce published claims. An unsuccessful run is still evidence; archive it with its status instead of deleting it to improve presentation.
- **Keep outside the bundle:** `.env`, keys, local databases, indexes, review tooling such as `.review_dependencies/`, and scratch outputs. Do not delete runtime data or Docker volumes as ordinary cleanup.
- **Respect evaluation ownership:** inventory protected assets by metadata and manifests. Agent/prompt tuners must not read protected answers or consolidate them into application-readable fixtures. Role 5 decides how exposed historical cases are classified and how independent evidence is retained.

## 6. Ordered implementation plan

### Mandatory scope and test policy

This migration cleans up existing files and code only. Do not add product functionality, change financial/scoring semantics, rewrite prompts, close unrelated policy gaps, or regenerate evaluation evidence. Track such findings separately. No paid evaluations, live model calls, SEC requests, model downloads, live publication, or credit-consuming demo cases are required or authorized for migration validation. Section 7 describes operational usage; its live startup/evaluation commands are **not migration test steps**.

Use the existing `unittest` suite with mocks, scripted models, committed local fixtures, and temporary databases. The repeatable migration gate is:

```powershell
# From the application root; macOS/Linux: python scripts/run_mock_tests.py
.\.venv\Scripts\python.exe scripts/run_mock_tests.py
```

`scripts/run_mock_tests.py` disables dotenv loading, installs dummy provider keys, disables telemetry/model downloads, and blocks Python socket connections, DNS resolution, and datagram sends in the test process. Only construction of internal socket pairs is allowed so Windows asyncio can create its wakeup pipe. Real Docker sandbox integration variants are skipped; local sandbox checks remain. Existing dependency/platform skips must be recorded, not presented as passed coverage. The runner is not an OS network sandbox for arbitrary child processes: retain the execution environment's network restriction and never add live child-process clients to this gate.

Run this **full gate before any migration and after every phase and subphase**. Focused tests help diagnosis but cannot replace it. Do not automatically skip failing tests or relax assertions to make a move pass. If the baseline fails, record the failure and stop structural migration until the cause is resolved or explicitly reviewed; do not label the baseline green. Dependency installation or missing platform coverage is an environment issue, not permission to spend API credit.

For each checkpoint record: revision/diff, command, interpreter, discovered/executed count, failures, errors, skips with reasons, duration, log location, and decision. Preserve a stable test-ID inventory; after package moves map renamed IDs explicitly so a reduced discovery count cannot masquerade as success. A phase passes only with no failures/errors, no unexplained missing tests or new skips, and its specific checks below satisfied. Revert only that phase's changes when needed, preserving user files. Do not begin the next phase while its gate is unresolved.

### Redundancy review required in every phase

Before closing each phase/subphase, inspect its changed files for duplicate explanations, navigation wrappers, repeated helpers, dead code, and temporary migration files. Merge overlapping material into a named canonical file and remove redundant files in that same checkpoint when consumers are updated and preservation tests pass. Record what was merged/removed and why each remaining helper or compatibility file is still needed. Do not defer ordinary redundancy cleanup wholesale to Phase 5.

Use one repository overview and one documentation index. Give specialized documents descriptive names such as `SETUP.md` and `REPORT.md`; do not create a README for every category or phase. Keep specialized pre-existing build instructions where they serve a distinct purpose. Keep test/audit artifacts distinct when they record different facts. Code consolidation must preserve behavior and responsibilities; file count alone does not establish duplication. Evidence-manifest-bound originals cannot be removed to improve appearance.

The five retained legacy document forwarding pages are temporary compatibility files while source comments and historical records still use their paths. Review/remove each when its consumers and historical entry points have been safely addressed; do not create further forwarding layers. Apply the full mock gate after consolidation as after any migration change.

Role suggestions follow the gap analysis; confirm assignments in the team work log.

| Phase | Work and deliverable | Suggested owners | Exit condition |
|---|---|---|---|
| 0. Baseline | Record commit, dirty/untracked files, dependency versions, mock test results, and existing evidence locations. Build movement/removal manifest. | R6 with module owners | Recoverable baseline and passing offline gate; no private values in logs. |
| 1. Safety review | Revalidate high-priority gap IDs against current code and tests; track remaining findings separately from cleanup. | R3/R4, independent R5 | No refactor weakens known acceptance or privacy boundaries. |
| 2. Documentation and presentation | Add root navigation, canonical setup/run pages, architecture chart, evidence index, and editable-source/export rules. | R1/R6 | A new teammate can identify entry points and complete setup from one guide. |
| 3. Repository root migration | Move application root and update workflows, build contexts, documentation, and path-based scripts in one PR. | R6 | Full offline gate passes at new paths; CI/build references resolve without image downloads. |
| 4. Functional grouping | Move one package group per PR; preserve imports with short-lived wrappers when necessary. Reorganize tests with discovery support. | R2/R3/R4 | Existing offline tests discover and pass; external module/API contracts remain usable. |
| 5. Consolidation and removal | Extract verified common helpers, archive superseded evidence, remove approved manifest entries. | Module owners; R5 reviews evidence changes | No unresolved consumers, missing evidence, or silent scoring changes. |
| 6. Release rehearsal | Validate mocked C0/C1/C2 journeys, failure paths, monitoring handlers, documentation, and submission links. | Whole team | Final offline gate passes; release checklist records unexecuted live checks explicitly. |

Do not combine behavioral fixes, directory moves, scoring changes, and historical evidence regeneration into one PR. Record failing baseline checks honestly rather than presenting pre-existing failures as refactor success.

### Phase 0 — Establish the offline baseline

1. Inventory tracked/untracked files and protect `.env`, local stores, and original audit/evidence files. Record the starting revision and intended changed paths.
2. Establish the network-blocked runner above using installed dependencies; discover all existing tests, including `tests/security/`.
3. Record test identities/counts and skip reasons. Retain failure output and distinguish environment errors from existing product/test failures.
4. Create the move/removal manifest described in section 5; mark each candidate as keep, move, consolidate, archive, or remove.

**Gate:** run the full offline suite. Baseline failures block phases 1–6; test tooling and documentation may still be prepared. No live smoke/evaluation commands.

### Phase 1 — Freeze existing contracts and safety expectations

1. Map current callers, public imports, CLI/module commands, API routes, graph states, file-path assumptions, database locations, and Docker/CI references.
2. Map existing mocked regressions to financial calculations, claim review, two-revision limits, approval/edit invalidation, portal receipts, memory-off/deletion, private watchlists, and scoring.
3. Preserve C0/C1/C2 differences, tool budgets, schema fields, prompts, source data, and experiment configurations. List uncovered behavior as a limitation; do not implement features to fill it.
4. Record reviewed checkpoint/rollback procedure and unchanged data boundaries.

**Gate:** full offline suite plus review of the contract inventory. No policy-fix work is bundled here.

### Phase 2 — Documentation and presentation cleanup

1. Add root navigation and canonical setup/run instructions; distinguish published images from local source execution.
2. Group architecture, policy, review, and submission documents using the section 4 map. Preserve original audit documents and export provenance.
3. Link the flowchart, demo story, contribution guide, and evidence index. Identify superseded documents without deleting evidence.
4. Check relative links, command paths, document references, and which Markdown source owns each export.

**Gate:** full offline suite plus local link/path checks. No API-backed rehearsal or regenerated Word/slide assets unless separately needed for documentation consistency.

### Phase 3 — Move the application root

1. Move the tracked application tree to `analyst_desk/`; handle ignored/untracked local files separately so secrets and local state are preserved.
2. Update workflow working directories and path filters, Docker build/COPY contexts, contributor instructions, and all documented application paths.
3. Keep package name `analystdesk`, launch wrappers, data-relative paths, environment-variable names, and persistent-volume identities stable. Check Compose project naming before any future live deployment; a directory rename must not silently select fresh volumes.
4. Update the offline runner's root calculation if necessary and run it from the new application root.

**Gate:** full offline suite at the new root; resolve every referenced build/script path locally. Validate Compose configuration only with dummy values and without outputting secrets. Do not build/pull images or start services as a phase requirement.

### Phase 4 — Group code and tests by functionality

Apply these as separate subphases, in order; finish the full gate after **each**:

- **4A: UI and research:** move dashboard/research/evaluation UI and C0/chart/context modules; retain thin launch wrappers.
- **4B: Finance and retrieval:** move facts, source review, figures, ingestion, query, and retrieval modules; update imports and fixture paths without changing algorithms or corpus fingerprints.
- **4C: Governance and memory:** move checks, approval, review snapshots, memory, and playbook modules; preserve signatures, schemas, lifecycle behavior, and storage paths.
- **4D: Evaluation and scripts:** group scoring/harness modules and utility scripts; update module commands, patch targets in tests, and `__file__`-based root calculations. Do not open protected answers or rerun evaluations.
- **4E: Test organization:** group unit/integration/security tests only after application imports stabilize. Preserve recursive discovery with package markers or equivalent loader support and compare test IDs against the baseline.

**Gate:** full offline suite after 4A, 4B, 4C, 4D, and 4E, with no unexplained test loss. Mocked import, CLI, UI/API handler, and path checks cover the moved interfaces.

### Phase 5 — Consolidate and remove approved redundancy

1. Compare candidate helpers by behavior; extract one shared implementation only where input/output/error semantics already match.
2. Update consumers and remove temporary compatibility wrappers only after all references migrate.
3. Archive superseded reports with provenance. Remove only manifest-approved temporary, duplicate, or unused files; preserve failed experiment records and original evidence.
4. Keep dependency intent/lock files, retrieval ablation corpora, C0/C1/C2 paths, and platform launchers where their roles differ.

**Gate:** full offline suite after each shared-helper extraction and after the removal batch; review deleted paths against the manifest, imports, links, and Docker/CI references. Any behavior change is out of scope.

### Phase 6 — Final offline migration sign-off

1. Repeat the full gate from the final layout and compare counts, IDs, results, and skips with phase 0.
2. Exercise existing scripted-model journeys and mocked failure handling: plan review, draft edits, rejected approval, incomplete checks, confirmed/unknown publication, and memory-sync failure. Use temporary stores only.
3. Check root documentation, setup commands, module paths, flowchart, evidence links, exclusion rules, and submission structure against the final tree.
4. Record moved/deleted/consolidated files, compatibility decisions, remaining baseline limitations, and rollback instructions. Mark live deployment/model quality checks as unexecuted and outside this migration.

**Gate:** full offline suite and reviewed manifest/checklist. No new product functionality, paid calls, or live publication.

### Phase execution record

Append one row after each checkpoint; link a locally retained test log and record exact counts. Do not mark future phases complete based on the baseline run.

| Checkpoint | State | Tests / errors / failures / skips | Evidence and decision |
|---|---|---|---|
| 0: baseline | Complete | 538 discovered/run; 533 passed; 0 errors; 0 failures; 5 skipped | [Phase 0 checkpoint](migration/phase0/REPORT.md): repository/dependency inventories, 476-entry candidate manifest, recovery reference, test IDs/results/log, and evidence locations. |
| 1: contract inventory | Complete | 538 run; 533 passed; 5 skips | [Phase 1 report](migration/phase1/REPORT.md). |
| 2: documentation grouping | Complete | 538 run; 533 passed; 5 skips | [Phase 2 report](migration/phase2/REPORT.md); redundant navigation consolidated. |
| 3: application root | Complete | 538 run; 533 passed; 5 skips | [Phase 3 report](migration/phase3/REPORT.md); dummy Compose config validated. |
| 4A-4E: functional groups | Complete | Each gate: 538 run; 533 passed; 5 skips | [Phase 4 report](migration/phase4/REPORT.md); one-to-one renamed test-ID map retained. |
| 5: consolidation/removal | Complete | 538 run; 533 passed; 5 unchanged skips | [Phase 5 report](migration/phase5/REPORT.md); helper and removal gates, preservation checks. |
| 6: final sign-off | Complete (offline scope) | 538 run; 533 passed; 5 unchanged skips; no failures/errors | [Final report](migration/phase6/REPORT.md); baseline comparison, preservation/rollback review, and final local checks passed. |

**Baseline notes:** `.venv/Scripts/python.exe scripts/run_mock_tests.py` reported 538 tests in 33.079 seconds (exit code 0): 533 passed and 5 skipped. Four skips are the deliberately excluded `DockerSandboxTests` variants; one is `test_keygen_writes_a_private_key_only_its_owner_can_read`, a Unix-mode check not applicable on Windows. The canonical log is `docs_notfor_submission/migration/phase0/mock_tests.log`; the superseded root scratch log was archived in Phase 5. It is a local checkpoint artifact, not a replacement for independent product-evaluation evidence. CI targets Python 3.12; this local run used the already installed Python 3.13.11 environment and does not establish Python 3.12/Linux coverage. An initial runner trial blocked Windows asyncio's internal socketpair and was corrected in test tooling; its errors were not application regressions. Phase 0 is now complete: see the [checkpoint](migration/phase0/REPORT.md) and [machine-readable results](migration/phase0/test_results.json). The detailed contract inventory is now recorded in the [completed Phase 1 checkpoint](migration/phase1/REPORT.md). At the baseline checkpoint no structural migration had begun; all subsequent verification remains offline.

### Gap-analysis priorities that constrain cleanup

| Reference | Required preservation or verification |
|---|---|
| F07–F13, F17–F23, F38; AE01 | Correct company/metric/period/unit/source association; raw precision; signed and zero cases; compatible filing versions. |
| F16/F28/F33; AE02–AE10 | Complete required review, failure blocking, maximum two automated revisions, fresh checks after edits, exact-note approval at graph/API/portal boundaries. Current `graph.review_note` already rejects failed checks; independently verify the full path. |
| AE04–AE06; F30/F31 | Every requested risk pair and honest missing/excerpt-only coverage. Retrieval success is not proof of whole-section absence, materiality, or economic novelty. |
| AE13–AE16 | Distinguish confirmed publication, unknown outcome, and memory-sync failure; never republish just to repair memory. |
| M01–M12; L01–L04 | Genuine memory-off behavior, private-watchlist boundary, deletion/resume behavior, reviewed development lessons, immutable evaluated playbook. |
| F34/F37; AE17; G01–G06 | Independent labels, meaningful scoring, protected held-out evaluation, fair experiments, and retained failures. Source code alone does not prove measured completion. |

## 7. Setup and run instructions: current working paths

The maintained instructions are now in [Setup and Run Analyst Desk](SETUP.md). They cover prerequisites, shared published images, local Docker builds, Python development, troubleshooting, and offline migration tests.

The application now lives at `analyst_desk/`. Published-image launchers do not run local edits. Setup/run commands are usage documentation and were not executed for this migration; only the network-blocked mock test gate is permitted as phase validation. The canonical instructions have been updated and their local paths verified at the new root.

## 8. Program flowchart for the team

This describes the principal current flow and the acceptance behavior that restructuring must preserve. C0 produces a baseline response; the gated publication flow belongs to C1/C2. See `analystdesk/agent/graph.py`, `analystdesk/agent/team.py`, `analystdesk/research/c0_pipeline.py`, and `analystdesk/servers/` for implementation details.

The maintained Mermaid diagram is in [Program Flow](architecture/program_flow.md). Keep that single diagram source current; this plan links to it rather than duplicating it.

Tool access crosses MCP permission/budget hooks: filings-kb reads passages; EDGAR reads facts; Python sandbox computes; research-portal alone publishes. Checkpoints support resumable runs. Optional memory supplies permitted preferences/history; reviewed frozen lessons guide eligible runs. Traces, metrics, and alerts observe execution without granting publication permission. Keep these boundaries visible in the final architecture diagram; do not merge memory, protected evaluation answers, and public retrieval into one store.

## 9. Verification and presentable delivery

For every move, verify imports, command entry points, path calculations based on `__file__`, Docker COPY paths, Compose mounts, workflow filters, document links, and test discovery. Nested unittest folders need package/discovery support; confirm discovered test counts do not drop.

Final acceptance checklist:

- [x] Setup instructions and script paths match the final layout; platform checks not executed locally are disclosed.
- [x] Network-blocked offline suite passes after every phase/subphase; counts, skips, and results match the reviewed baseline.
- [x] Build/COPY/mount paths resolve locally; Compose validation uses dummy configuration. Image builds, pulls, and running-service smoke checks remain outside the migration gate.
- [x] Existing C1/C2 scripted journeys and C0 baseline/chart/context/refusal tests pass; mocked fiscal confirmation and edits work. Full C0 provider-response integration was not exercised.
- [x] Mocked failed/incomplete checks cannot publish; edits invalidate approval; two-revision bound holds.
- [x] Risk evidence limitations, signed/zero financial cases, memory-off, and private-watchlist tests retain behavior.
- [x] Mocked unknown save outcomes and memory-sync failures remain distinguishable.
- [x] Evidence manifests, protected-case boundaries, frozen lessons, and experiment provenance remain intact.
- [x] Root README links to setup, architecture, policies, evidence, demo, and explicit remaining limitations.
- [x] Submission tree, ignore patterns and Docker COPY inputs reviewed for excluded credentials/caches/runtime stores; an actual archive/image was not built.
- [x] Removal manifest and offline checklist reviewed; no API-credit tests or new product functionality introduced.
- [ ] Independent module-owner/team release acceptance: not performed by this automated migration; outside the offline gate.

The final presentation should follow one story: supported question → approved plan → traceable evidence → checked note → exact human approval → confirmed publication. Link each claimed capability to its current test or demonstration evidence; keep deferred scope and outstanding verification visible.
