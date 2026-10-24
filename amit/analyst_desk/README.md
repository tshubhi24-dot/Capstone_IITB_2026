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
| 10 | [Supported model replacement](docs/ADR-003-SUPPORTED_MODEL_SWITCH.md) | The approved plan produced a cited draft with 18/18 verified financial values. Three critic requests through Mistral returned HTTP 429, including a different model. The original twelve-call limit is reached. A different-provider critic and one exact extra-call approval are being prepared; no verdict, note approval or live publication yet. [Current status](evidence/live_pilot_status.json). |

Each completed step has its own commit. Commit timestamps reflect when work was committed; they do not backdate human reviews or experiments. See [step history](STEP_LOG.md) and [contribution provenance](docs/CONTRIBUTIONS.md).

The six students own problem framing, design, evaluation and interpretation. Proposed targets, AI-assisted preparation and actual measured results are labelled separately. Credentials, runtime databases, downloaded source caches and protected final evaluation assets must stay outside Git.

The first journey used actual cached SEC data for Microsoft and Apple, FY2023–2025, with deterministic calculations, BM25 retrieval and zero model calls. The live pilot is authorized within its original US$1 cap. The original route reported a Terms of Service refusal and remains stopped; its specific policy is unverified. The supported replacement produced a verified draft, but the internal critic has returned three rate-limit errors. Reported lifetime spend is US$0.0296596, uncertain holds are US$0.3506464, and US$0.6196940 remains. A further critic call requires an explicit run-limit extension; the dollar caps and all old holds remain intact. The note is unsaved pending a real critic verdict and separate human approval. Learned retrieval and independent capstone evaluation remain future work. See the [source preparation requirements](data/README.md) before starting a fresh clone.

Local research desk: <http://127.0.0.1:18080>. Monitoring: <http://127.0.0.1:13080>. The research desk requires the private analyst credential; it is not included in this repository.
