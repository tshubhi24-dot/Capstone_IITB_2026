# Analyst Desk: start here

**Current step-by-step build | Updated 24 October 2026**

This folder contains the current project preparation and the build that follows it. The first offline Docker research journey has completed with explicit plan and note approvals. The architecture describes a larger target system. Human scope ownership, independent evaluation and full capstone validation remain pending.

## Follow the work in order

| Step | Current preparation | Read next |
|---|---|---|
| 1. Define the project | Draft problem, users, scope and proposed acceptance criteria prepared. Team review and real-user/domain validation pending. | [Project definition](PROJECT_DEFINITION.md), [ownership and contributions](CONTRIBUTIONS.md). |
| 2. Plan evaluation | Evaluation protocol and public 20-case development authoring pack prepared. Independent protected cases and human labels remain pending. | [Evaluation plan](EVALUATION_PLAN.md), [kickoff preparation pack](../evaluation/kickoff/README.md). |
| 3. Define architecture | Proposed roles, four tool services, human gates, persistence, Docker and evaluation boundaries drawn. The first implementation covers a limited offline slice. | [Architecture v1](ARCHITECTURE_V1.md), [overview drawing](diagrams/architecture-v1-overview.png), [editable diagrams](diagrams/README.md), [proposed memory policy](MEMORY_POLICY.md). |
| 4. Build the first Docker journey | Fresh implementation running with two human gates, authenticated MCP tools, an isolated worker and persistent state. | [Journey runbook and limits](TWO_COMPANY_JOURNEY.md). |
| 5. Run and verify | Microsoft/Apple FY2023–2025 note explicitly approved and saved; 18 financial values checked, 18 MCP calls, zero model calls; persistence and runtime readiness verified. | [Journey receipt](../evidence/two_company_journey.json), [runtime checks](../evidence/runtime_checks.json), [restart/authentication evidence](../evidence/journey_verification.json). |
| 6–8. Add live AI capability | Provider/ledger, cited specialists, graph, optional Docker stack and review UI implemented and tested. Paid activation remains disabled; the first actual live run needs explicit spending authorization. | [Incremental steps](LIVE_AI_STEPS.md), [decision](ADR-002-LIVE_REASONING.md), [live runbook](LIVE_AI_RUNBOOK.md), [runtime evidence](../evidence/live_runtime_checks.json). |

Next expand verified source coverage and specialist behaviour; exercise safety, memory and reviewed learning; validate the complete Compose stack and monitoring; freeze and run independent comparisons; then prepare the report, slides, demo and viva from observed evidence.

## Read the evidence honestly

- Proposed targets and diagrams are design artifacts, not benchmark outcomes or deployment receipts.
- The public development pack contains source-derived expectations and blank authoring forms. It contains no independently authored final holdout or completed human labels.
- The originating cached SEC corpus is not included. Preserve the recorded origin hashes and independently verify imported source data before claiming equivalence.
- Record genuine decisions, reviews, contributions, failures and interpretation in [CONTRIBUTIONS.md](CONTRIBUTIONS.md).
- Course requirements are cited by page number; the course PDF is not redistributed here.
