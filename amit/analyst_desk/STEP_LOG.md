# Analyst Desk: our step-by-step build

This is the implementation sequence we followed to build Analyst Desk. It explains what each step adds, where to find it, and how it supports the capstone. These are **our build steps**, not the brief's numbered request walkthrough.

**Current result:** a Docker Compose application covers twelve companies in two sectors with BM25/vector fusion, local reranking and persistent analyst memory. Editable defaults, coverage and scoped approved history support follow-up research. Reviewed-lesson controls add development admission, reflection, exact decisions and frozen opt-in guidance. Its completed Microsoft/Apple research journey for FY2023–2025 includes plan review, parallel retrieval, code-calculated margins, cited writing, AI criticism, exact-note approval and local publication.

**Reading the brief references:** general requirements are on pages 2–6. The Analyst Desk section is printed pages **15–16**, which are **PDF pages 7–8** in the supplied extract. The final-review questions are printed p.17 (PDF page 9). References below use the printed page numbers.

## Step 1 — Define the research problem and scope

**What this step does:** makes the product concrete before implementation. It defines the analyst, supported questions, source and fiscal-year boundaries, publication controls, proposed success measures and six areas of team ownership. The target is twelve companies across technology and healthcare; the current working slice covers Microsoft and Apple.

| Files | Purpose |
|---|---|
| [docs/PROJECT_DEFINITION.md](docs/PROJECT_DEFINITION.md) | Problem, users, coverage, task boundaries and proposed acceptance targets. |
| [docs/CONTRIBUTIONS.md](docs/CONTRIBUTIONS.md) | Team ownership and contribution record. |

**Capstone connection:** p.15, “In one line” and “Who it is for”; p.16, company/sector coverage; pp.4–5, six team roles. Proposed project targets are separate from the brief's mandatory requirements.

## Step 2 — Plan how we will measure success

**What this step does:** defines evidence of correctness before using system outputs as results. It separates development from protected held-out questions, numeric checking from semantic review, and implementation tests from evaluation. It specifies E1–E4 comparisons and provides development questions and blank annotation forms.

| Files | Purpose |
|---|---|
| [docs/EVALUATION_PLAN.md](docs/EVALUATION_PLAN.md) | Datasets, metrics, experiment controls, review responsibilities and freeze rules. |
| [evaluation/kickoff/development_cases.jsonl](evaluation/kickoff/development_cases.jsonl), [development_expected.jsonl](evaluation/kickoff/development_expected.jsonl) | Twenty development questions and source-derived expected numeric rows. |
| [evaluation/kickoff/README.md](evaluation/kickoff/README.md), [dataset_manifest.json](evaluation/kickoff/dataset_manifest.json) | Preparation instructions and source provenance. |
| [evaluation/kickoff/retrieval_labels_template.csv](evaluation/kickoff/retrieval_labels_template.csv), [risk_labels_template.csv](evaluation/kickoff/risk_labels_template.csv), [judge_labels_template.csv](evaluation/kickoff/judge_labels_template.csv), [independent_attack_template.csv](evaluation/kickoff/independent_attack_template.csv), [protected_case_template.json](evaluation/kickoff/protected_case_template.json) | Structures for independent labels, attacks and protected cases. |

**Capstone connection:** p.3, L13/L15; pp.5–6, golden set, judge calibration and E1–E4; p.16, XBRL truth, hand-labelled risk changes and signature ablation. The protocol and preparation kit are ready; final evaluation is pending.

## Step 3 — Draw the architecture and define memory

**What this step does:** assigns responsibilities and trust boundaries before connecting services. The design traces a request through planner, researchers, quant, risk comparison, writer, critic and publisher. It identifies human review gates and distinguishes checkpoints, preferences, reviewed lessons and approved notes.

| Files | Purpose |
|---|---|
| [docs/ARCHITECTURE_V1.md](docs/ARCHITECTURE_V1.md) | Components, hand-offs, control boundaries and design decisions. |
| [docs/diagrams/architecture-v1-workflow.mmd](docs/diagrams/architecture-v1-workflow.mmd), [architecture-v1-deployment.mmd](docs/diagrams/architecture-v1-deployment.mmd) | Editable request-flow and deployment diagrams. |
| [docs/diagrams/architecture-v1-overview.svg](docs/diagrams/architecture-v1-overview.svg) | Presentation overview. |
| [docs/MEMORY_POLICY.md](docs/MEMORY_POLICY.md) | What memory should retain, access rules, correction and deletion. |

**Capstone connection:** p.2, reference architecture; p.3, L8/L9/L14; pp.15–16, Analyst Desk diagram and memory. The design includes capabilities beyond the current build.

## Step 4 — Build the first complete Docker workflow

**What this step does:** creates a working path through the architecture using deterministic processing before paid model reasoning. Four authenticated MCP services retrieve filing evidence, supply cached annual facts, calculate margins in an isolated worker and publish approved notes. LangGraph manages parallel company research and persistent review pauses.

| Files | Purpose |
|---|---|
| [compose.yaml](compose.yaml), [Dockerfile](Dockerfile), [requirements.txt](requirements.txt) | Services, isolation, persistent volumes and dependencies. |
| [desk/workflow.py](desk/workflow.py), [desk/store.py](desk/store.py) | Typed graph state, checkpoints, review decisions and exact-version publication. |
| [desk/tools.py](desk/tools.py), [desk/worker.py](desk/worker.py), [desk/data.py](desk/data.py) | MCP permissions, networkless calculation and source/period verification. |
| [desk/api.py](desk/api.py), [web/app.js](web/app.js), [web/index.html](web/index.html), [web/style.css](web/style.css) | Research API, streamed events and review interface. |
| [ops/prepare_sources.py](ops/prepare_sources.py), [data/source_manifest.json](data/source_manifest.json), [data/README.md](data/README.md) | Source-snapshot preparation and provenance. |

**Capstone connection:** p.3, L7/L8/L14/L16; pp.15–16, four MCP services and numeric traceability. This slice uses cached SEC data and BM25.

## Step 5 — Run the workflow and verify the controls

**What this step does:** proves that the assembled system can finish a real source-backed journey. The analyst reviews the exact plan and note; publication follows approval. Runtime checks test service readiness, authentication and persistence, rather than relying only on mocked tests.

| Files | Purpose |
|---|---|
| [ops/start_journey.py](ops/start_journey.py), [ops/bootstrap.py](ops/bootstrap.py) | Prepare and start the stack with bounded readiness checks. |
| [ops/journey_session.py](ops/journey_session.py), [docs/TWO_COMPANY_JOURNEY.md](docs/TWO_COMPANY_JOURNEY.md) | Operate a run and review its pending decisions. |
| [ops/verify_runtime.py](ops/verify_runtime.py), [evidence/two_company_journey.json](evidence/two_company_journey.json), [evidence/journey_verification.json](evidence/journey_verification.json) | Actual usage, publication, authentication and restart evidence. |
| [ops/prometheus.yml](ops/prometheus.yml), [ops/alerts.yml](ops/alerts.yml), [ops/grafana/dashboards/journey.json](ops/grafana/dashboards/journey.json) | Metrics, alert rule and dashboard. |

**Capstone connection:** p.3, resume, approval and deployment evidence; pp.15–16, walkthrough steps 2, 4, 6–8; p.16, operational metrics. The offline journey verified all eighteen displayed financial values and saved a note without model calls.

## Step 6 — Add the live-model gateway and budget ledger

**What this step does:** gives the application a controlled route to model reasoning. The gateway enforces approved models, structured output, prompt/output bounds and spending limits. A persistent ledger reserves possible cost before each call, records known usage and retains uncertain reservations after ambiguous failures.

| Files | Purpose |
|---|---|
| [desk/provider.py](desk/provider.py), [desk/model_gateway.py](desk/model_gateway.py) | Provider adapter, local validation and durable usage accounting. |
| [docs/ADR-002-LIVE_REASONING.md](docs/ADR-002-LIVE_REASONING.md) | Why live reasoning uses a separate gateway and bounded policy. |
| [ops/check_secrets.py](ops/check_secrets.py), [tests/test_provider.py](tests/test_provider.py), [tests/test_secret_guard.py](tests/test_secret_guard.py) | Credential exclusion and provider/ledger failure tests. |

**Capstone connection:** p.3, L13/L14/L15; p.15, token budget and hooks; p.6, excluding secrets from the submission. The gateway foundation is implemented.

## Step 7 — Connect evidence-grounded AI specialists

**What this step does:** adds model-generated plans, retrieval queries, disclosure comparisons, writing and semantic criticism to the graph. Models select from supplied evidence; code checks identifiers, exact quotations, company/year scope and all arithmetic. A failed critique can send the draft through a bounded repair loop. Edits invalidate earlier semantic checks and note approval.

| Files | Purpose |
|---|---|
| [desk/reasoning.py](desk/reasoning.py) | Role prompts, output schemas, evidence choices and claim validation. |
| [desk/workflow.py](desk/workflow.py) | Live specialist stages, critic/repair routing and review gates. |
| [tests/test_reasoning.py](tests/test_reasoning.py), [tests/test_live_workflow.py](tests/test_live_workflow.py) | Grounding, wrong-source, edited-note and failed-output regression checks. |

**Capstone connection:** p.3, L8/L10/L11; pp.15–16, parallel research, critic loop and code-checked numbers. These are bounded specialist functions, rather than unrestricted ReAct agents. Internal criticism is separate from independent evaluation.

## Step 8 — Deploy live reasoning and expose review evidence

**What this step does:** adds an optional live Compose deployment while preserving the offline path. Only the gateway receives provider access; its ledger is separate from research history. The UI displays model mode, accounting and criticism. Missing authorization or an unavailable live service blocks the request.

| Files | Purpose |
|---|---|
| [compose.live.yaml](compose.live.yaml), [ops/start_live.py](ops/start_live.py), [ops/prepare_live.py](ops/prepare_live.py) | Live overlay, configuration preparation and explicit activation. |
| [desk/api.py](desk/api.py), [web/app.js](web/app.js) | Safe configuration, budget and review information. |
| [ops/verify_live_runtime.py](ops/verify_live_runtime.py), [docs/LIVE_AI_RUNBOOK.md](docs/LIVE_AI_RUNBOOK.md) | Deployed boundary checks and operating instructions. |

**Capstone connection:** p.3, L14–L16; p.5, common serving stack; p.16, cost-per-note monitoring. Nineteen runtime checks cover the deployed live stack.

## Step 9 — Make provider failures visible and recoverable

**What this step does:** tests the first live route and makes failure handling explicit. Access failures stop research before a plan can be approved. Diagnostics expose bounded error categories, preserve uncertain cost and retain state across restart. A failed request cannot silently become a successful run.

| Files | Purpose |
|---|---|
| [desk/provider.py](desk/provider.py), [desk/model_gateway.py](desk/model_gateway.py) | Safe failure categories and authoritative accounting. |
| [evidence/openrouter_access_diagnosis.json](evidence/openrouter_access_diagnosis.json), [evidence/live_attempt_verification.json](evidence/live_attempt_verification.json) | Technical failure and persistence receipts. |
| [tests/test_provider.py](tests/test_provider.py), [tests/test_secret_guard.py](tests/test_secret_guard.py) | Failure parsing, retained reservations and disclosure prevention. |

**Capstone connection:** p.3, L13/L15; p.6, including failed runs; p.17, explaining missing evidence and failed tools. The original route stopped without publication. Provider failure evidence is operational evidence, not a research benchmark.

## Step 10 — Complete the live research journey

**What this step does:** finishes the same research workflow with supported models, stronger source constraints and bounded continuation. Annual coverage grounds the plan; finite quotation choices preserve provenance; the writer revises provisional claims; code and the AI critic inspect the exact final note before the analyst signs it.

| Files | Purpose |
|---|---|
| [desk/model_profiles.py](desk/model_profiles.py), [docs/ADR-003-SUPPORTED_MODEL_SWITCH.md](docs/ADR-003-SUPPORTED_MODEL_SWITCH.md) | Explicit model/provider profiles and switching rules. |
| [desk/reasoning.py](desk/reasoning.py), [desk/workflow.py](desk/workflow.py) | Source-grounded writer, exact-draft criticism and controlled continuation. |
| [desk/provider.py](desk/provider.py), [ops/critic_extension.py](ops/critic_extension.py) | Retained accounting, private output diagnostics and exact-call allowances. |
| [evidence/live_critic_review.json](evidence/live_critic_review.json), [evidence/live_publication_verification.json](evidence/live_publication_verification.json), [evidence/live_pilot_status.json](evidence/live_pilot_status.json) | Actual critic, publication and persistence results. |

**Capstone connection:** pp.15–16, numeric traceability, critic loop and exact-note sign-off; p.3, durable state and budget hooks. The live journey completed: **18/18 financial values checked, seven claims supported by the internal critic, approved note saved and restart persistence verified**. The suite passed 500 local tests and nineteen runtime checks. Selected risk excerpts and unverified original section boundaries limit conclusions; this is a development pilot.

### Technical refinements within steps 9 and 10

The lettered increments preserve the build sequence; detailed receipts remain in `evidence/`.

| Increment | Engineering purpose |
|---|---|
| 9a–9c | Activate spending, preserve failed calls and verify restart persistence without resetting accounting. |
| 9d–9e | Strengthen diagnostics/secret scanning and stop the refused route. |
| 10a–10c | Add reviewed model profiles and catch an annual-scope error before approval. |
| 10d–10f | Ground the plan in annual facts; constrain quotations; resume only the approved run. |
| 10g–10i | Correct temporal validation, extend secret scanning and preserve the writer checkpoint. |
| 10j–10l | Constrain writer prose, refine provisional claims and bind citations to comparison periods. |
| 10m–10o | Preserve the checked draft and bind critic retries/replacement to exact reviewed inputs. |
| 10p–10s | Add a different-provider critic, exact-request allowances and private rejected-output diagnostics. |
| 10t–10u | Pass the critic, obtain exact-note sign-off, save and verify persistence. |

## Step 11 — Expand source coverage to twelve companies

**What this step does:** extends the research catalogue from two companies to six Technology and six Healthcare companies for FY2023–2025. A declared scope drives import and validation, so each company/year needs matching annual revenue and operating income plus cached Item 1A and Item 7 sections. Research requests retain their existing size and spending limits.

| Files | Purpose |
|---|---|
| [data/coverage_scope.json](data/coverage_scope.json) | Twelve issuer identities, sectors, fiscal years and required concepts/sections. |
| [ops/prepare_sources.py](ops/prepare_sources.py) | Validate the complete financial/section matrix and install a reproducible snapshot. |
| [tests/test_prepare_sources.py](tests/test_prepare_sources.py) | Missing/duplicate coverage, source identity, annual-period, synthetic-data and failed-installation checks. |
| [data/README.md](data/README.md) | Source schema, import commands and safe snapshot replacement. |
| [data/source_manifest.json](data/source_manifest.json), [data/sec_cache_manifest.json](data/sec_cache_manifest.json) | Installed financial/section inventory and pinned original SEC response identities. |
| [ops/verify_source_coverage.py](ops/verify_source_coverage.py), [tests/test_source_provenance.py](tests/test_source_provenance.py) | Match normalized data to original cached XBRL/submissions and detect changed or missing source bodies. |
| [evidence/source_coverage_verification.json](evidence/source_coverage_verification.json) | Observed coverage and cached-source verification results. |
| [web/index.html](web/index.html), [web/app.js](web/app.js), [desk/api.py](desk/api.py), [desk/workflow.py](desk/workflow.py) | Select covered companies/years, enforce request limits and reject stale source approvals. |
| [ops/verify_runtime.py](ops/verify_runtime.py), [ops/verify_live_runtime.py](ops/verify_live_runtime.py), [ops/verify_catalogue_tools.py](ops/verify_catalogue_tools.py) | Verify loaded scope, deployed source identity and all financial/section tool paths. |
| [ops/start_journey.py](ops/start_journey.py), [ops/start_live.py](ops/start_live.py), [Dockerfile](Dockerfile), [.dockerignore](.dockerignore) | Reload source readers and refresh ingress after rebuilding the app; include only the required operator check. |
| [tests/test_coverage_scope.py](tests/test_coverage_scope.py), [tests/test_coverage_runtime.py](tests/test_coverage_runtime.py), [tests/test_deployment.py](tests/test_deployment.py), [tests/test_live_deployment.py](tests/test_live_deployment.py) | Selection, stale-source, capacity and deployment regressions. |
| [evidence/catalogue_tools_verification.json](evidence/catalogue_tools_verification.json), [evidence/coverage_expansion_runtime.json](evidence/coverage_expansion_runtime.json) | Actual deployed tool checks and preserved library/budget verification. |

**Capstone connection:** p.16, Retrieval requires 10–15 companies in two sectors over three years; Tools and Signature A require cached original facts with source IDs and comparable periods. This increment expands coverage; hybrid retrieval, reranking and full Item/table validation remain later work.

| Increment | Result |
|---|---|
| 11a — Declare and validate scope | Importer supports the twelve-company target and explicit subsets. Fifty-two importer/data tests pass; real-cache validation confirms the target matrix. Installing and deploying the expanded snapshot follows. |
| 11b — Load and verify SEC coverage | Installed 36 company-years, 72 financial facts, 4,073 passages and 72 section groups. All 72 numeric memberships and 36 annual filing identities match 61 cached SEC responses, including one historical submissions index. No network/model calls were needed. |
| 11c — Expose and verify the deployed catalogue | The UI selects from twelve companies, grouped by sector. Requests retain a four-company ceiling; live three-year risk comparisons allow two companies. Source changes invalidate old approvals. Deployment refreshes ingress without clearing notes or budgets. |

**Verified expansion result:** all 36 deployed margin rows (108 displayed financial values), 72 section groups and twelve search scopes passed. The full suite passed 613 tests and all nineteen runtime checks passed. The three existing notes and spending records remained unchanged; this expansion made zero model calls.

## Step 12 — Add hybrid retrieval and reranking

**What this step does:** combines exact keyword matching with learned semantic retrieval, merges candidate ranks and reranks the shortlist while keeping original passage identifiers and source quotations. Development comparisons use a frozen question set and report the limitations of partial, source-derived labels.

| Files | Purpose |
|---|---|
| [web/app.js](web/app.js), [tests/test_provider_error_ui.py](tests/test_provider_error_ui.py) | Explain provider HTTP 429 failures and stopped-run behavior without automatic paid retries or changing budget records. |
| [evaluation/retrieval/README.md](evaluation/retrieval/README.md), [development_queries.jsonl](evaluation/retrieval/development_queries.jsonl) | Frozen development questions, partial relevance labels, source hashes and comparison rules. |
| [ops/evaluate_retrieval.py](ops/evaluate_retrieval.py), [tests/test_retrieval_evaluation.py](tests/test_retrieval_evaluation.py) | Paired Recall@5/Hit@5 comparisons; retain errors and misses in the denominator. |
| [desk/retrieval.py](desk/retrieval.py), [desk/data.py](desk/data.py), [data/retrieval_config.json](data/retrieval_config.json) | Scoped table-aware BM25, pinned MiniLM vectors, query decomposition, RRF and cross-encoder reranking. |
| [ops/prepare_retrieval.py](ops/prepare_retrieval.py), [tests/test_retrieval.py](tests/test_retrieval.py) | Build and verify frozen local artifacts; test scope, changed artifacts, ranking, table cells and concurrent first use. |
| [desk/vector_store.py](desk/vector_store.py), [ops/prepare_vector_store.py](ops/prepare_vector_store.py), [tests/test_vector_store.py](tests/test_vector_store.py) | Populate Chroma explicitly, validate stored vectors and apply issuer/year/allowed-ID filters before ranking. |
| [evidence/retrieval_development_comparison.json](evidence/retrieval_development_comparison.json) | Complete paired host comparison, missed labels, model/index identities and diagnostic timings. |
| [requirements.retrieval.txt](requirements.retrieval.txt), [Dockerfile](Dockerfile), [.dockerignore](.dockerignore), [compose.yaml](compose.yaml), [compose.live.yaml](compose.live.yaml) | CPU dependencies, shared current service images, read-only retrieval artifacts and internal Chroma connectivity. |
| [desk/tools.py](desk/tools.py), [desk/api.py](desk/api.py), [web/app.js](web/app.js) | Authenticated retrieval readiness, accurate search status and a preflight block for unavailable indexes. |
| [ops/start_journey.py](ops/start_journey.py), [ops/start_live.py](ops/start_live.py), [ops/verify_runtime.py](ops/verify_runtime.py), [ops/verify_live_runtime.py](ops/verify_live_runtime.py) | Prepare Chroma before starting readers and match deployed retrieval identities to frozen artifacts. |
| [ops/verify_retrieval_tools.py](ops/verify_retrieval_tools.py), [tests/test_retrieval_tools_verification.py](tests/test_retrieval_tools_verification.py), [tests/test_retrieval_runtime.py](tests/test_retrieval_runtime.py) | Exercise frozen questions through authenticated search and test fail-closed readiness, provenance and result accounting. |
| [evidence/retrieval_deployed_verification.json](evidence/retrieval_deployed_verification.json), [evidence/retrieval_deployment_runtime.json](evidence/retrieval_deployment_runtime.json) | Actual deployed question results, service checks, restart persistence and unchanged research/budget records. |
| [docs/HYBRID_RETRIEVAL.md](docs/HYBRID_RETRIEVAL.md), [data/README.md](data/README.md), [README.md](README.md), [docs/START_HERE.md](docs/START_HERE.md) | Pipeline explanation, reproducible model/index preparation, operating instructions and qualified results. |

**Capstone connection:** p.3, hybrid BM25/vector retrieval, RRF, reranker, query-side improvement and Recall@5 comparison; p.16, scoped company/year retrieval and preserved table evidence. Provider failure handling supports the observable failure requirement on p.6.

| Increment | Result |
|---|---|
| 12a — Explain a rate-limited run | The interface explains HTTP 429, retains the diagnostic and reserved-budget display, and offers explicit next actions. Three browser-helper checks pass. |
| 12b — Freeze the retrieval comparison | Thirty-six questions and 42 source-derived passage labels cover four development issuers, twelve company/year groups and both narrative/table evidence. Thirty-two harness checks pass. Labels were frozen before running retrieval; human review and protected evaluation remain pending. |
| 12c — Implement and compare local retrieval | Prepared 4,073 × 384 vectors and real pretrained CPU models. Twenty-eight retrieval tests pass. Sampled-label Recall@5 is 75.0% for BM25, 77.8% for hybrid and 98.6% with reranking. Hybrid improves five/regresses five questions; reranking improves nine/regresses none against BM25. These are partial development labels, not independent gold. Docker/Chroma verification follows. |
| 12d — Deploy the hybrid search service | Docker selects hybrid retrieval with reranking and loads an index-specific Chroma collection. Source, model-file and vector identities are checked; stored float32 vectors allow a measured absolute roundoff tolerance of 0.0000001. Missing or stale retrieval blocks new research before paid planning. All Python services use the newly built image; 780 tests pass. Deployed retrieval and persistence receipts follow. |
| 12e — Verify deployed retrieval and persistence | All 36 development questions pass source/scope/ranking checks through 37 authenticated MCP calls, with 98.6% sampled-label Recall@5 and 100% Hit@5. Every top-five result order matches the host reranked arm. All twelve company tool paths, 36 margin rows and nineteen runtime checks pass. After restarting Chroma and the search service, the collection is reused and searches in both sectors return the same evidence. Existing research records, three notes and model-budget accounting remain unchanged; zero generative-model calls, new research runs, human decisions or note publications were made. |

**Verified retrieval result:** hybrid search and trained reranking are active in Docker over all 4,073 passages. The 36-question comparison is development evidence with partial, source-derived labels. Independent human relevance review, protected final evaluation and original SEC Item/table validation remain outstanding.

## Step 13 — Add analyst memory

**What this step does:** adds editable analyst preferences, source-derived coverage memory and relevant approved-note references for follow-up research. Memory stays in persistent local storage, with bounded retrieval, revision checks, expiry and explicit correction/deletion controls. Earlier notes remain separate from current SEC evidence.

| Files | Purpose |
|---|---|
| [docs/ADR-004-ANALYST-MEMORY.md](docs/ADR-004-ANALYST-MEMORY.md) | Storage decision, permitted memory, review boundaries and verification contract. |
| [desk/memory.py](desk/memory.py), [tests/test_memory.py](tests/test_memory.py) | Actual namespaced LangGraph SQLite storage, expiring preferences, revision checks, coverage records and note exclusion controls. |
| [desk/history.py](desk/history.py), [desk/store.py](desk/store.py), [tests/test_memory_history.py](tests/test_memory_history.py) | Scoped approved-note selection, frozen references and transactional publication checks against current memory versions. |
| [desk/workflow.py](desk/workflow.py), [tests/test_memory_workflow.py](tests/test_memory_workflow.py) | Bind memory to the reviewed plan, revalidate before resumed work/model use, apply layout by code and keep historical content out of model prompts. |
| [desk/api.py](desk/api.py), [desk/tools.py](desk/tools.py), [tests/test_memory_api.py](tests/test_memory_api.py) | Authenticated preference/history controls, bounded portal reads and fixed local-analyst access. |
| [desk/memory_comparison.py](desk/memory_comparison.py), [tests/test_memory_comparison.py](tests/test_memory_comparison.py) | Compare immutable approved numeric history with current canonical facts only when dates and units match. |
| [web/memory.js](web/memory.js), [web/app.js](web/app.js), [web/index.html](web/index.html), [web/style.css](web/style.css) | Save/delete defaults, inspect coverage, search cited history, compare facts and exclude/restore future note reuse. |
| [ops/verify_memory_runtime.py](ops/verify_memory_runtime.py), [tests/test_memory_runtime_verifier.py](tests/test_memory_runtime_verifier.py), [Dockerfile](Dockerfile), [.dockerignore](.dockerignore) | Isolated operator checks for persistent memory and authenticated portal search, packaged explicitly into the shared image. |
| [docs/ANALYST_MEMORY.md](docs/ANALYST_MEMORY.md), [docs/MEMORY_POLICY.md](docs/MEMORY_POLICY.md), [evidence/analyst_memory_verification.json](evidence/analyst_memory_verification.json) | Team usage guide, precise retention/correction rules and observed Docker/API/browser verification. |

**Capstone connection:** p.3, L9 persistent memory and memory policy; pp.15–16, coverage, analyst preferences, prior research and follow-up questions; p.3, L8/L14 checkpoint and exact-version review. Reviewed lessons and independent memory evaluation remain separate work.

| Increment | Result |
|---|---|
| 13a — Define memory storage and controls | Choose actor-namespaced LangGraph SQLite memory alongside publication records so final publication can atomically check memory versions. Define allowlisted preferences, source coverage, bounded approved history and deletion semantics before implementation. |
| 13b — Build durable memory and approved-history selection | Save typed preferences with thirty-day expiry and revision-based correction/deletion. Persist source coverage under its fingerprint. Select up to three approved references after actor/company/year filtering, within a fifty-candidate window; excluded notes remain in the approved library. Memory versions and selected note hashes are checked inside the publication transaction. Core storage/history tests cover isolation, rollback, expiry, restart and concurrent changes. |
| 13c — Connect memory to research and the interface | Reviewed plans bind preference versions and selected note hashes; changes or expiry block stale approvals and resumed work. Code applies table-first/summary-first layout. Historical references remain local, separate from current SEC evidence and model prompts. The interface exposes preference correction/deletion, coverage, cited history and fact comparison. Memory-off tests preserve verified figures; all 910 tests pass. |
| 13d — Verify deployed memory and document team usage | Nine preparation checks, eleven checks after a service restart and eight cleanup checks pass using a separate operator namespace. One authenticated planner history call returns three approved references. Sixteen deployed API/preservation checks and nineteen general runtime checks pass. The browser shows scoped history, the exact compared note, six verified margin rows, source buttons and limitations. Existing preferences, note policy, research runs, three approved notes and spending records remain unchanged. No model calls, new research runs, human decisions or note publications are made. |

**Verified memory result:** preferences and source coverage persist locally; approved history is bounded, versioned and separate from current evidence. Analyst controls cover correction, deletion, exclusion and restoration. Independent L9 memory comparison and genuine lesson-review evidence remain outstanding; Step 14 implements the lesson controls.

## Step 14 — Add human-reviewed development lessons

**What this step does:** turns actual critic rejections or analyst edits on registered public development questions into bounded lesson proposals. A person reviews each exact proposal before it can enter an explicitly frozen playbook. Later research can opt into relevant accepted guidance while retaining current-source checks and separate plan/note approvals.

| Files | Purpose |
|---|---|
| [docs/ADR-005-REVIEWED-LESSONS.md](docs/ADR-005-REVIEWED-LESSONS.md) | Development admission, reflection, exact-version review, frozen reuse and verification boundaries. |
| [desk/development.py](desk/development.py), [data/development_cases.json](data/development_cases.json), [tests/test_development.py](tests/test_development.py) | Admit only exact registered public questions and scope, without expected answers or labels. Bind admission to the active source; reject production relabelling and private analyst memory. |
| [desk/lessons.py](desk/lessons.py), [tests/test_lessons.py](tests/test_lessons.py) | Persist immutable proposals and reasoned decisions in LangGraph SQLite. Invalidate superseded pending proposals, freeze accepted versions and select at most three applicable code-owned hints. Revocation is rechecked transactionally. |
| [desk/reflection.py](desk/reflection.py), [desk/reasoning.py](desk/reasoning.py), [tests/test_lesson_api.py](tests/test_lesson_api.py) | Prepare pending proposals using code-category reflection or bounded optional AI reflection after checking development and original plan-approval evidence. |
| [desk/workflow.py](desk/workflow.py), [desk/store.py](desk/store.py), [tests/test_lesson_workflow.py](tests/test_lesson_workflow.py) | Bind reviewed lesson context to plans/notes, apply fixed hints only to producers, reject stale/revoked context and forbid development publication. |
| [desk/api.py](desk/api.py), [web/lessons.js](web/lessons.js), [web/app.js](web/app.js), [web/index.html](web/index.html) | Authenticated development-case selection, exact proposal review/edit/rejection, explicit playbook freezing and opt-in reuse. |
| [ops/verify_lessons_runtime.py](ops/verify_lessons_runtime.py), [tests/test_lessons_runtime_verifier.py](tests/test_lessons_runtime_verifier.py), [Dockerfile](Dockerfile), [.dockerignore](.dockerignore) | Package an isolated, explicitly synthetic persistence/revocation check without copying evaluator answers or touching analyst records. |
| [docs/REVIEWED_LESSONS.md](docs/REVIEWED_LESSONS.md), [evidence/reviewed_lessons_verification.json](evidence/reviewed_lessons_verification.json) | Team usage guide, retention/review limits and observed deployed API/browser/restart checks. |

**Capstone connection:** p.3, L12 development-only Reflexion and reviewed/frozen playbook; pp.15–16, lessons from critic rejections and analyst edits; L9 durable storage and L14 exact-version control. Genuine accepted/rejected human decisions and independent E3 results require separate observed evidence.

| Increment | Result |
|---|---|
| 14a — Define development learning and review | Separate registered public development cases from production research. Define immutable proposals, reasoned human decisions, explicit playbook freezing, bounded relevant guidance and revocation checks. Protected evaluation assets remain outside the application. |
| 14b — Build admitted origins and immutable lesson storage | Bundle twenty public question/scope records with no expected answers; nineteen are within the cached fiscal coverage. Sixteen admission tests and thirty-four core lesson tests pass. Proposals require a persisted failed critic or actual changed-note event from a registered development run. Exact decisions, pending-proposal supersession, frozen versions, actor/source/scope checks and revocation are implemented. Fixture decisions are explicitly synthetic and do not count as human capstone evidence. |
| 14c — Connect reflection, review and research reuse | Add code-category reflection and an optional schema-constrained AI proposal stage under the originating live run's approved plan and remaining budget. Keep acceptance, freezing and use separate. Plans and notes bind the selected versions; producers receive fixed hints while the critic receives no lesson guidance or metadata. Development scopes remain exact and publication is blocked in both workflow and portal storage. All 1,005 tests pass, including stale-version, revocation, legacy-run and provider-boundary checks. |
| 14d — Verify persistence and document team use | Fourteen isolated preparation checks, thirteen checks after an app service restart and ten cleanup/revocation checks pass. Twenty-four deployed checks and nineteen runtime checks pass. Browser checks confirm the exact public question/scope, locked development controls and private memory off. Existing runs, preferences, note policy, three approved notes and spending remain unchanged. No paid requests, genuine human decisions, real research runs or publications are made. Synthetic review fixtures remain separate from analyst data and are not capstone review evidence. |

**Verified lesson result:** review, freezing, bounded reuse and revocation controls are implemented and deployed. The real lesson bank remains empty. Genuine development-derived accepted/rejected lessons, an actual live reflection and independent E3 improvement evidence have not been produced by these checks.

## Step 15 — Run a genuine development case and review its lessons

**What this step does:** runs registered public development cases through live planning, evidence-backed risk comparison and criticism, then reviews only proposals supported by actual critic rejections or analyst edits. KDEV017 records the first genuine run; KDEV018 exercises the analyst's web workflow. Every plan and lesson decision remains an exact human review. Development notes cannot enter the approved library.

| Files | Purpose |
|---|---|
| [docs/FIRST_DEVELOPMENT_CASE.md](docs/FIRST_DEVELOPMENT_CASE.md) | Exact case, baseline controls, review sequence and honest treatment of clean runs or unsupported lesson proposals. |
| [data/development_cases.json](data/development_cases.json), [desk/development.py](desk/development.py) | Existing public question registry and server-created admission for the selected source/company/year scope. |
| [desk/workflow.py](desk/workflow.py), [desk/reflection.py](desk/reflection.py), [desk/lessons.py](desk/lessons.py) | Existing research/critic gates, event-bound reflection and exact-version human decisions. |
| [evidence/development_case_verification.json](evidence/development_case_verification.json) | Sanitized observed checks and progress; complete runtime records and human confirmation text stay outside Git. |
| [docs/WEB_DEVELOPMENT_WALKTHROUGH.md](docs/WEB_DEVELOPMENT_WALKTHROUGH.md), [web case receipt](evidence/web_development_case_verification.json) | Reproduce KDEV018 through the analyst interface and distinguish UI evidence, genuine lessons and the separate planted-error demo. |
| [web/app.js](web/app.js), [tests/test_run_selection_ui.py](tests/test_run_selection_ui.py) | Keep responses, polling and exact actions tied to the selected run; preserve open evidence on unchanged polls and refresh the saved-run label. Test delayed responses, continuation and stable display. |
| [web/index.html](web/index.html), [desk/reasoning.py](desk/reasoning.py), [tests/test_temporal_provenance.py](tests/test_temporal_provenance.py) | Expose supported continuation in the UI and validate two-period narrative wording from canonical citations without weakening quantity or source checks. |
| [evidence/frozen_playbook_use_verification.json](evidence/frozen_playbook_use_verification.json) | Verify the immutable accepted lesson/playbook before a separately opted-in research run; distinguish frozen readiness, actual guidance use and improvement evidence. |

**Capstone connection:** p.3 L12 and pp.15–16 require real development failures/edits, reflection, reviewed lessons and frozen reuse. This public development case is not a protected evaluation or proof of improvement.

| Increment | Result |
|---|---|
| 15a — Select and prepare the first genuine case | KDEV017 compares MSFT risk disclosures for FY2024–2025 without a planted failure. The registered scope is available, hybrid retrieval is ready and live research is available under the original limits. A private preservation baseline is saved; no active operation or existing lesson is present. Research and human review are still pending. |
| 15b — Run the live planner and present the exact plan | One real planner call succeeds. Sixteen checks validate registered admission, source/scope, exact pending hash, disabled memory/lessons, visible source limitations and preservation of existing runs/library/preferences. The complete plan is available privately for human review. Research is paused at the required plan gate; no critic outcome, lesson or publication is claimed. |
| 15c — Execute the approved case and review the result | After the actual exact-plan approval, research completes in five total model calls. Twenty-two checks pass; both annual rows, 6/6 displayed financial values and all eight citation instances match the canonical source. The model critic supports 4/4 claims and remains labelled model-assisted, not gold. The analyst reviews the full exact note and requests no correction. No critic rejection or analyst edit has occurred, so there is no eligible proposal to reflect on, accept, reject or freeze. The private receipt records the clean review; the application retains its development review pause without publishing or falsely rejecting the note. Earlier work and the empty lesson bank are preserved. |
| 15d — Prepare the next case through the web interface | Select KDEV018 for AAPL FY2024–2025 in the running research UI. The exact question and locked scope are visible, memory is off, lessons are off and development publication is blocked. Seven baseline checks pass under the existing limits; earlier runs, approved notes and lesson versions are saved privately for preservation checks. The walkthrough explains the UI, human gates and its connection to the brief. No new research run or human decision has occurred yet. |
| 15e — Observe the real web plans and preserve a connection failure | The first web planner pauses for review. An additional web attempt receives exact-plan approval, then stops at an upstream provider connection failure during researcher query selection. Across both attempts, two planner responses complete and one failed call retains its reservation. Sixteen admission/version/preservation checks pass. No draft, critic rejection, analyst edit, lesson or publication is produced. The first plan remains unapproved. A web polling/error-display race is identified for correction before the walkthrough continues; the operational failure is not relabelled as a research lesson. |
| 15f — Fix and verify web run selection | Ignore stale responses and old poll callbacks, clear errors from a previously selected run and lock review controls until the selected payload is loaded. Preserve same-version unsaved edits and block overlapping form submissions. Thirty-nine targeted tests pass, including nine synthetic race cases. The deployed app preserves all runs, notes, preferences, note policy, lessons and budget records across six checks. Browser verification confirms that switching from the failed attempt to the original plan clears its old error and shows the correct exact plan. No model call, approval, retry or lesson is created by the fix. This strengthens the L14 human-review interface and L16 deployment evidence. |
| 15g — Add explicit web continuation for supported failures | The original plan receives web approval, then its paid writer response is stopped by a temporal-phrase quantity-guard false positive before the critic. Add a Resume approved research control that uses only the backend's existing content-validation continuation and exact original plan hash. Earlier charges/holds and original limits remain in force; no provider retry or extension flags are exposed. Nineteen UI cases and 144 combined targeted checks pass. At this increment the control awaits the validator correction; deployment and actual continuation are recorded below. The failed response is preserved and is not relabelled as a critic rejection or lesson. |
| 15h — Correct the temporal-wording false block | Validate canonical citations before allowing the existing narrow two-period phrase in summary claims. The evidence must identify one issuer and exactly two distinct fiscal years. Financial quantities, durations, invalid quotes and comparison-scope mismatches remain blocked. All 257 targeted tests pass, including 29 new provenance/quantity cases and a synthetic continuation that reuses the identical cached writer request. Prompts, schemas and model request construction are unchanged; this increment establishes fixture replay, while actual web continuation and criticism are recorded in 15i. |
| 15i — Complete the web continuation and stabilize note review | An explicit web continuation resumes the original human-approved research without creating another human approval. The identical cached writer request/response is reused without a new writer charge; only one new critic response is requested and charged. Thirty actual completion checks pass, including 6/6 verified financial values and 4/4 model-supported claims. The primary attempt pauses at note review with five unique completed responses. Both attempts remain recorded: seven call attempts, six unique completed responses and one connection failure with its held reservation. There are zero critic rejections, analyst note edits, eligible lesson origins, proposals or lesson decisions; human note review remains pending and development publication remains blocked. The display fix preserves open evidence and unsaved same-version text during unchanged polls and updates the saved-run status. Fifty-two targeted tests pass, including 22 UI cases and three new display cases; deployment preserves all six runtime groups. Browser verification confirms unchanged exact-note identity, correct status, open citations across more than twenty seconds of polling, preserved unsaved text and blocked development publication. The UI change makes no model call or human decision. This supports L14 readable exact-version review and L16 deployment evidence; it does not establish L12 learning or independent improvement. |
| 15j — Apply the authorized source-precision correction | A user-selected correction is applied by an operator in the web editor: the existing natural-disaster bullet now identifies the later quotation's explicit reference to retail stores while preserving uncertainty about economic materiality. The financial table, citation identifiers, other claims, headings and limits stay unchanged. An actual note_edit event invalidates the previous verdict. All 31 actual correction checks pass, including 6/6 financial values and 4/4 fresh claims bound to the new exact note; prior usage, held budget, other runs, library, memory, lessons and original caps are preserved. Only one new critic response is used, bringing the primary attempt to six model calls; writer and retrieval do not rerun. The note remains awaiting review, with one eligible edit origin and zero proposals, lesson decisions, frozen playbooks or publications at this checkpoint. This supports L14 exact-version correction and creates a genuine L12 development origin; it is not an independent human quality label, accepted lesson or measured improvement. |
| 15k — Prepare and refine the genuine edit-derived proposal | Select the actual note_edit event and use code reflection without a model call. The generic verify_current_facts proposal is inspected and refined in the web interface to cite_exact_evidence, describing the observed retail-stores wording difference. Applicability is limited to AAPL FY2024–2025 against the same cached source; counterexamples retain partial-evidence, economic-materiality and no-demonstrated-financial-error limits. All 27 actual proposal-preparation checks pass. Saving creates two immutable versions: one pending and the original superseded, not rejected; origin/source bindings and supersession links verify, while runs, library, memory and budget stay unchanged. Code-category reflection does not read before/after prose, so operator refinement is not autonomous AI learning. No additional model call or charge, human lesson decision, frozen playbook or publication occurs. The user must review the exact pending proposal and provide a separate reasoned acceptance or rejection. Only a fixed allowlisted hint can later reach producers after acceptance, freezing and explicit opt-in; explanation text remains local. This demonstrates the L12 origin/proposal/review boundary without claiming accepted learning or independent improvement. |
| 15l — Verify the existing exact-proposal acceptance | Web and persisted-state inspection find the refined proposal already accepted before the verification action; its existing decision is preserved and zero additional decisions are submitted. All 24 actual acceptance-verification checks pass: exact proposal/decision and origin/source/scope bindings verify, the bank advances once, and research, library, memory and budget remain unchanged. The bank contains one accepted version, one superseded version and no pending proposal. Acceptance is reasonable for the source-backed wording omission: both quotations support the retail-stores distinction, AAPL FY2024–2025 and the cached source bound applicability, and explicit limits preserve uncertainty about materiality and full-section coverage. The reusable cite_exact_evidence hint is a modest generic checklist; the specific explanation stays local, and usefulness across its four producing stages remains unmeasured. No model call, frozen playbook, lesson reuse or development publication occurs. This records an L12 review outcome and L14 exact-version preservation; frozen reuse and independent improvement evidence remain separate. |
| 15m — Verify the frozen accepted playbook before reuse | Initial inspection finds one existing frozen playbook containing the exact accepted lesson; preserve it without submitting a duplicate freeze request. All 22 actual freeze checks pass: playbook identity/hash, accepted proposal/decision, current source and unrevoked membership verify; the bank advances once since the acceptance checkpoint without extra lessons. All runs, library, memory, note policy and budget records remain unchanged, live research and retrieval are ready, and no operation is active. No fresh plan, model call, lesson reuse or development publication occurs at this checkpoint. Next explicitly select the book for a new registered KDEV018 AAPL FY2024–2025 run with private memory off, then verify actual producer guidance and obtain the new exact-plan review. This satisfies the L12 frozen-playbook boundary and preserves L14 controls; it does not establish reuse or independent improvement. |
| 15n — Verify live planner guidance and retain the upstream stop | Create a new exact KDEV018 AAPL FY2024–2025 run in the web app with private memory off and the frozen playbook explicitly selected. The live planner completes. Twenty-one local reconstruction checks and 25 runtime-preservation checks make no provider call. Request reconstruction proves the fixed hint was in the actual completed planner request: its request identity matches the response/event, while removing guidance changes that identity. The human approves the new exact plan; the researcher retrieves canonical facts, then query selection stops on upstream HTTP 429. Retain both model attempts, the completed planner response and the failed reservation without automatic retry, offline substitution or model-configuration change. No new risk analysis, writer draft, critic result, proposal or publication is produced; the originating learning case remains preserved. This demonstrates L12 guidance delivery to the planner and observable failure handling, not semantic adherence, later-stage use, full journey completion or independent held-out improvement. |

## Step 16 — Add bounded live-model fallbacks

**What this step does:** removes the single Mistral producer route as a required dependency. A reviewed profile tries GPT-4.1 Mini first, with Mistral Medium 3.1 as backup inside one OpenRouter request. Gemini remains the separate critic. Only fixed model/provider lists can be used, with structured-output, privacy, context and price requirements.

| Files | Purpose |
|---|---|
| [desk/model_profiles.py](desk/model_profiles.py), [desk/provider.py](desk/provider.py) | Define fixed role routes, reserve the highest allowed token rates, validate actual returned models and preserve uncertain holds. |
| [ops/prepare_live.py](ops/prepare_live.py) | Prepare an inactive replacement profile while archiving the previous policy and retaining original limits and credentials. |
| [tests/test_provider_fallbacks.py](tests/test_provider_fallbacks.py), [tests/test_provider.py](tests/test_provider.py), [tests/test_live_deployment.py](tests/test_live_deployment.py) | Exercise routing, accounting, cache/replay behavior, role separation, legacy profiles and exact-version preparation with simulated providers. |
| [desk/api.py](desk/api.py), [web/app.js](web/app.js), [tests/test_live_api.py](tests/test_live_api.py), [tests/test_model_route_ui.py](tests/test_model_route_ui.py) | Validate fixed route metadata and distinguish available backup models from actual completed response models. |
| [README.md](README.md), [docs/LIVE_AI_RUNBOOK.md](docs/LIVE_AI_RUNBOOK.md), [evidence/model_fallback_verification.json](evidence/model_fallback_verification.json) | Explain setup, exact-version activation, 429 troubleshooting and the evidence/limits of fallback checks. |

**Capstone connection:** L14 cost and review controls, and L16 operational reliability and reproducible setup. Fallbacks improve route availability; they do not establish research quality or independent learning improvement.

| Increment | Result |
|---|---|
| 16a — Implement fixed producer fallbacks and conservative accounting | Add opt-in profile `live-step16-fallbacks-v1`: GPT-4.1 Mini then Mistral Medium 3.1, through only OpenAI/Azure/Mistral ZDR providers, with the separate Google critic. Reserve the maximum producer rate across both models, record requested/returned models, and retain full reservations for uncertain route/accounting failures. Accounting breaches block further spending across policies. One router request has no application retry loop; completed responses replay from cache. All 148 focused provider tests pass without live calls, including primary/backup success, wrong-role models, overprice/token breaches, exhausted 429 routes and legacy behavior. Profile preparation preserves existing spending limits and ledger files; activation and a successful live fallback remain unverified at this checkpoint. |
| 16b — Expose route choices and document teammate setup | The API checks route metadata against fixed reviewed definitions before enabling live creation. The web app shows producer priority/backup and lists actual completed-response models without implying that a configured backup was used. README and live runbook explain the fallback switch, exact activation, pricing/privacy bounds, 429 diagnosis, retained holds and explicit next actions. All 370 selected provider/workflow/deployment/API/browser checks pass without real model requests. A disabled replacement configuration is prepared; its activation and live provider availability remain unverified at this checkpoint. |
| 16c — Activate the exact reviewed route and preserve runtime state | Reload only the model gateway, app and ingress with the authorized fixed profile, retaining every persistent volume. All 25 read-only activation checks pass: the API and web app expose the reviewed routes, live AI and hybrid retrieval are available, source identity is unchanged, and all prior runs, approved notes, preferences, note policy, lessons, charges, holds, token/call totals and original caps are preserved. Activation itself creates no model request. This verifies deployment and control preservation; live model access and successful backup use remain separate checks. |
| 16d — Verify a live primary response with frozen guidance | Create one fresh registered Apple KDEV018 plan in the web app with private memory off and the frozen playbook selected. GPT-4.1 Mini completes the single planner call: 938 reported tokens and US$0.0006152. Twenty runtime checks preserve earlier records, all old uncertain holds and the unchanged limits; 21 request-reconstruction checks verify fixed lesson guidance in the completed planner request. An operator edits the outline to compare available excerpts instead of promising complete risk-disclosure extraction; this adds no model call and pauses for a new exact-plan review. Mistral is not used in this live call, so live failover remains unexercised. No research execution, draft, critic result, new lesson or publication occurs at this checkpoint; no independent learning improvement is claimed. |

## What the team builds next

1. **Continue genuine development learning:** preserve the accepted lesson, review further evidence-backed proposals, record a genuine rejection with its reason, and freeze selected accepted versions before protected evaluation.
2. **Source validation and robustness:** validate original Item/table ingestion, obtain independent relevance labels, prove specialist ReAct/replanning and active-operation recovery, and run independently authored attacks.
3. **Independent evaluation:** protected cases, human risk labels, calibrated outcome judge, L9 memory comparison, fair baselines and repeated E1–E4 comparisons.
4. **Submission and demo:** named ownership/domain review, evaluation report, working alert/CI gate, clean-machine installation, slides, backup recording and individual architecture walkthroughs.

These remaining requirements come from p.3's minimum bar, pp.5–6's evaluation/submission rules and p.16's Analyst Desk build/demo. [docs/START_HERE.md](docs/START_HERE.md) is the entry point; [docs/EVALUATION_PLAN.md](docs/EVALUATION_PLAN.md) tracks the evaluation protocol.

## Team onboarding — Reproduce the desk on another machine

**What this update does:** makes the repository usable by a teammate starting with a fresh checkout. The README explains the branch/folder, Python/Docker installation, the public source seed included in Git, pinned model downloads, credential files, offline checks, optional live authorization, first research and safe restart/update steps. A separate source-data handoff is no longer needed.

| Files | Purpose |
|---|---|
| [README.md](README.md), [repository entry point](../../README.md) | Detailed teammate setup and a direct entry link from GitHub. |
| [data/README.md](data/README.md), [docs/HYBRID_RETRIEVAL.md](docs/HYBRID_RETRIEVAL.md) | Distinguish original source import from exact prepared-data handoff and use an explicit matching model cache. |
| [docs/LIVE_AI_RUNBOOK.md](docs/LIVE_AI_RUNBOOK.md), [docs/TWO_COMPANY_JOURNEY.md](docs/TWO_COMPANY_JOURNEY.md) | Align live image/model setup and label historical two-company instructions. |
| [data/seed/public-sec-fy2023-2025.zip](data/seed/public-sec-fy2023-2025.zip), [seed inventory](data/seed/manifest.json), [seed guide](data/seed/README.md) | Include the exact public normalized snapshot and source manifest in the branch, with checksums and source-update rules. |
| [evidence/public_seed_verification.json](evidence/public_seed_verification.json) | Record isolated installation, corruption, preservation and public-only archive checks. |

**Observed result:** the included archive is about 1.4 MB and contains only the normalized public corpus and matching manifest: twelve companies, 36 company-years, 72 canonical facts and 4,073 passages. Eight isolated installation/privacy checks pass, including repeat installation, rejection of corruption and preservation of a different existing snapshot. All 41 checked local document links resolve. Existing running source bytes and modification time are unchanged; this setup change makes no model calls. Model weights remain a separate pinned public download.

**Capstone connection:** L16 installation/reproducibility and L14 explicit spending/research review. The guide uses each teammate's own local credentials; public data is included in the branch. Commands are checked against the implementation, the seed installation and isolated dummy-credential preparation. A complete clean-machine Docker installation on another teammate's hardware remains a separate validation.
