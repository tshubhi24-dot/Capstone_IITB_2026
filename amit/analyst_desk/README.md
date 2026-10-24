# Analyst Desk — Amit's step-by-step contribution

This folder contains the current capstone work prepared from the beginning. It does not import the earlier generated reference application, old reports or old benchmark results. Other team members' folders remain unchanged.

**Working branch:** `Amit/analyst_desk`. Push work to this branch for team review. Do not push or merge these changes directly into `main`; integration is a separate team decision.

## Steps

| Step | Deliverable | Status |
|---|---|---|
| 1 | [Problem, users, scope and proposed success criteria](docs/PROJECT_DEFINITION.md) | Prepared for team review. |
| 2 | [Evaluation plan](docs/EVALUATION_PLAN.md) and [public development preparation](evaluation/kickoff/README.md) | Prepared; independent final cases and human labels remain pending. |
| 3 | [Architecture v1](docs/ARCHITECTURE_V1.md), [drawings](docs/diagrams/README.md) and [memory policy](docs/MEMORY_POLICY.md) | Proposed design prepared for team review. |
| 4 | [Fresh Docker journey implementation](docs/TWO_COMPANY_JOURNEY.md) | Built and running; 53 local automated checks pass. |
| 5 | [Human-reviewed two-company journey](evidence/two_company_journey.json) | Version-bound plan and note approvals recorded; one note saved. [Runtime checks](evidence/runtime_checks.json) and [restart/authentication evidence](evidence/journey_verification.json) pass. |
| 6 | [Live AI foundation and staged plan](docs/LIVE_AI_STEPS.md) | Provider gateway, persistent spending ledger and known-secret checks prepared and tested. Paid activation remains disabled; workflow/deployment integration follows. |

Each completed step has its own commit. Commit timestamps reflect when work was committed; they do not backdate human reviews or experiments. See [step history](STEP_LOG.md) and [contribution provenance](docs/CONTRIBUTIONS.md).

The six students own problem framing, design, evaluation and interpretation. Proposed targets, AI-assisted preparation and actual measured results are labelled separately. Credentials, runtime databases, downloaded source caches and protected final evaluation assets must stay outside Git.

The first journey uses actual cached SEC data for Microsoft and Apple, FY2023–2025, with deterministic calculations and BM25 retrieval. It makes zero model calls. Learned semantic retrieval, live agent reasoning and full capstone evaluation remain future work. See the [source preparation requirements](data/README.md) before starting a fresh clone.

Local research desk: <http://127.0.0.1:18080>. Monitoring: <http://127.0.0.1:13080>. The research desk requires the private analyst credential; it is not included in this repository.
