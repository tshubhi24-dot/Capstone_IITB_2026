# Analyst Desk — Amit's step-by-step contribution

This folder contains the current capstone work prepared from the beginning. It does not import the earlier generated reference application, old reports or old benchmark results. This branch's current tree is scoped to Amit's contribution; other contributors' work remains in `main`. See [branch scope](docs/BRANCH_SCOPE.md).

**Working branch:** `Amit/analyst_desk`. Push work to this branch for team review. Do not push or merge these changes directly into `main`; integration is a separate team decision.

## Steps

| Step | Deliverable | Status |
|---|---|---|
| 1 | [Problem, users, scope and proposed success criteria](docs/PROJECT_DEFINITION.md) | Prepared for team review. |
| 2 | [Evaluation plan](docs/EVALUATION_PLAN.md) and [public development preparation](evaluation/kickoff/README.md) | Prepared; independent final cases and human labels remain pending. |
| 3 | [Architecture v1](docs/ARCHITECTURE_V1.md), [drawings](docs/diagrams/README.md) and [memory policy](docs/MEMORY_POLICY.md) | Proposed design prepared for team review. |
| 4 | [Fresh Docker journey implementation](docs/TWO_COMPANY_JOURNEY.md) | Built and running; 53 local automated checks pass. |
| 5 | [Human-reviewed two-company journey](evidence/two_company_journey.json) | Version-bound plan and note approvals recorded; one note saved. [Runtime checks](evidence/runtime_checks.json) and [restart/authentication evidence](evidence/journey_verification.json) pass. |
| 6 | [Live AI foundation and staged plan](docs/LIVE_AI_STEPS.md) | Provider gateway, persistent spending ledger and known-secret checks prepared and tested. |
| 7 | Evidence-grounded live specialist workflow | AI plan/query/disclosure/writer/critic stages integrated with source checks and existing human gates; mocked tests pass. |
| 8 | [Optional live deployment and review UI](docs/LIVE_AI_RUNBOOK.md) | Validated with spending disabled: 153 local tests, 116 networkless-image tests and 19 runtime checks passed. Current [runtime evidence](evidence/live_runtime_checks.json) also records the authorized state. |
| 9 | Original route diagnosis | Five application planner attempts and a direct diagnostic stopped. The provider reported a Terms of Service refusal; the specific rule remains unknown. Six attempts retain US$0.1688064 in uncertain holds. [Historical diagnosis](evidence/openrouter_access_diagnosis.json). That route remains stopped. |
| 10 | [Completed live research journey](docs/ADR-003-SUPPORTED_MODEL_SWITCH.md) | Google Gemini 2.5 Flash supported all seven claims; code passed 18/18 financial values. Amit separately approved the exact note, which was saved and survived an app/gateway restart. Both prior notes and all uncertain holds remain. 500 local tests and 19 final runtime checks pass. [Current status](evidence/live_pilot_status.json), [publication verification](evidence/live_publication_verification.json). |
| 11 | [Twelve-company SEC coverage](data/README.md) | Six Technology and six Healthcare companies, FY2023–2025; 72 source-matched financial inputs and 4,073 passages. The UI selects covered companies and years. [Source checks](evidence/source_coverage_verification.json) and [deployed checks](evidence/coverage_expansion_runtime.json). |
| 12 | [Hybrid retrieval and reranking](docs/HYBRID_RETRIEVAL.md) | Scoped BM25 and local MiniLM vectors, reciprocal-rank fusion, bounded query decomposition and local cross-encoder reranking implemented. Sampled-label Recall@5 rose from 75.00% to 98.61% on 36 development queries; [deployed Chroma/MCP search](evidence/retrieval_deployed_verification.json) reproduced the result with zero errors. [Final checks](evidence/retrieval_deployment_runtime.json): 780 local tests, 19 runtime checks and restart persistence passed; runs, spending records and three notes unchanged. Partial relevance labels await independent human review. |
| 13 | [Analyst memory](docs/ANALYST_MEMORY.md) | Editable local defaults with expiry, source coverage and bounded approved history are attached to reviewed research. Exact-note citations, current-fact comparison and exclusion/restore controls are available in the desk. [Verification](evidence/analyst_memory_verification.json): 910 tests, 19 runtime checks, 16 deployed memory checks and restart persistence pass. Existing notes, runs and spending are unchanged. Independent memory comparison and actual lesson-review evidence remain pending. |
| 14 | [Reviewed development lessons](docs/REVIEWED_LESSONS.md) | Registered public development cases, bounded reflection, exact proposal decisions, frozen playbooks and scoped producer guidance are implemented. [Verification](evidence/reviewed_lessons_verification.json): 1,005 tests, 24 deployed checks, 19 runtime checks and 37 isolated fixture checks pass, including restart/revocation. Actual human acceptance/rejection and independent E3 results remain pending. |

Each completed step has its own commit. Commit timestamps reflect when work was committed; they do not backdate human reviews or experiments. See [step history](STEP_LOG.md) and [contribution provenance](docs/CONTRIBUTIONS.md).

The six students own problem framing, design, evaluation and interpretation. Proposed targets, AI-assisted preparation and actual measured results are labelled separately. Credentials, runtime databases, downloaded source caches and protected final evaluation assets must stay outside Git.

The first offline journey and the first live AI journey are complete for Microsoft and Apple, FY2023–2025. The live producer was Mistral Medium 3.1; Google Gemini 2.5 Flash provided the passing internal critique. The exact plan and final note received separate human approvals. All three approved notes remain unchanged. Twelve-company retrieval, local analyst memory and reviewed-lesson controls are implemented. Genuine development lesson decisions, original SEC Item/table validation, robustness and independent evaluation remain outstanding. A fresh clone needs the [source snapshot](data/README.md) and [pinned local retrieval bundle](docs/HYBRID_RETRIEVAL.md#prepare-a-fresh-machine) before Docker startup.

Local research desk: <http://127.0.0.1:18080>. Monitoring: <http://127.0.0.1:13080>. The research desk requires the private analyst credential; it is not included in this repository.
