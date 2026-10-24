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
| 6–9. Add live AI capability | Provider/ledger, cited specialists, graph, optional Docker stack and review UI implemented. The original route reported a Terms of Service refusal and remains stopped; its specific policy is unverified. | [Incremental steps](LIVE_AI_STEPS.md), [decision](ADR-002-LIVE_REASONING.md), [live runbook](LIVE_AI_RUNBOOK.md), [historical diagnosis](../evidence/openrouter_access_diagnosis.json). |
| 10. Completed live AI journey | Google critic supported seven claims; code verified 18/18 values. The human gate approved the exact note and it was saved with restart persistence verified. Library contains three notes; both old notes and all uncertain holds remain. 500 tests and 19 runtime checks pass. | [Current pilot status](../evidence/live_pilot_status.json), [actual critic](../evidence/live_critic_review.json), [publication verification](../evidence/live_publication_verification.json). |
| 11. Expand source coverage | Twelve companies across Technology/Healthcare for FY2023–2025, with 72 original financial inputs and 4,073 cached passages. Source and deployed-tool checks cover the complete catalogue. | [Source/import guide](../data/README.md), [source verification](../evidence/source_coverage_verification.json), [runtime verification](../evidence/coverage_expansion_runtime.json). |
| 12. Add hybrid retrieval and reranking | Combine scoped lexical and MiniLM vector search, fuse candidates, then rerank locally. The 36-query development comparison records 75.00% BM25 and 98.61% reranked sampled-label Recall@5; deployed Chroma/MCP search reproduced the result without errors. All 780 local tests and 19 runtime checks passed. Restart preserved retrieval results, runs, spending records and three notes. Independent human relevance review remains pending. | [Pipeline, setup and limits](HYBRID_RETRIEVAL.md), [development protocol](../evaluation/retrieval/README.md), [comparison receipt](../evidence/retrieval_development_comparison.json), [deployed search check](../evidence/retrieval_deployed_verification.json), [runtime/persistence check](../evidence/retrieval_deployment_runtime.json). |

Prepare the [pinned model/index bundle](HYBRID_RETRIEVAL.md#prepare-a-fresh-machine) before starting a fresh Docker installation. Next improve memory and reviewed learning, exercise robustness and specialist behaviour, run independent comparisons, then prepare the report, slides, demo and viva from observed evidence.

## Read the evidence honestly

- Proposed targets and diagrams are design artifacts, not benchmark outcomes or deployment receipts.
- The public development pack contains source-derived expectations and blank authoring forms. It contains no independently authored final holdout or completed human labels.
- The originating cached SEC corpus is not included. Preserve the recorded origin hashes and independently verify imported source data before claiming equivalence.
- Record genuine decisions, reviews, contributions, failures and interpretation in [CONTRIBUTIONS.md](CONTRIBUTIONS.md).
- Course requirements are cited by page number; the course PDF is not redistributed here.
