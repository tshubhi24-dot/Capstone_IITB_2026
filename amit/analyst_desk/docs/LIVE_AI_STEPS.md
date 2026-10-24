# Live AI increment: step-by-step commits

Work stays on `Amit/analyst_desk`, under this contribution folder. No direct merge to `main` is part of this task. Keep the first approved offline note and its evidence intact.

| Step | Deliverable | Verification before its commit |
|---|---|---|
| 6 | [Live reasoning decision](ADR-002-LIVE_REASONING.md), provider adapter, optional gateway and persistent spend ledger | Mocked provider responses, limits, concurrency, restart persistence, schema errors, missing usage and duplicate-call behavior; no paid calls |
| 7 | Evidence-grounded specialist reasoning in the existing graph | Schema, citation/quote/scope checks, qualitative prose checks, both review gates and verdict invalidation after edits; offline regression tests |
| 8 | Optional Docker deployment, private preparation/authorization tools, API and review UI | Merged Compose restrictions, disabled gateway readiness, actual transport, budget visibility and no provider key outside the gateway |
| 9 | First authorized live two-company journey | Explicit spending authorization, actual plan review, checked cited draft, separate note review, measured usage/cost and persistence evidence |
| 10 | Supported replacement-model journey under the original cap | Mistral profile, cumulative ledger migration, truthful API metadata, actual planner and separate human reviews; [ADR-003](ADR-003-SUPPORTED_MODEL_SWITCH.md) |

The first three steps can be prepared and tested without a paid call. Step 9 depends on the analyst's authorization of the exact prepared configuration. A refusal or missing key must be reported explicitly; synthetic responses cannot stand in for a live result.

On 24 October 2026 the original route reported a Terms of Service refusal; its specific rule and any location relationship remain unverified. Six stopped attempts retain their uncertain reservations; that route remains stopped. See the [historical diagnosis](../evidence/openrouter_access_diagnosis.json). The supported Mistral replacement produced a grounded, explicitly approved plan and a cited draft with 18/18 checked financial values, but three critic calls returned HTTP 429. Two separately authorized exact-call allowances then enabled Google criticism: call thirteen connected but failed local output validation, and call fourteen passed all seven claims after diagnostic/format fixes. Amit separately reviewed and approved the exact note. It was saved, and the note/library/budget survived app/gateway restart. All old holds and both dollar caps remain; 500 tests and nineteen final runtime checks pass. See the [current status](../evidence/live_pilot_status.json), [actual critique](../evidence/live_critic_review.json) and [publication verification](../evidence/live_publication_verification.json). Earlier failure/restart receipts remain historical evidence.

This increment adds bounded model-assisted planning, query choice, disclosure interpretation, writing and internal criticism. It retains BM25 retrieval and the cached SEC snapshot. It does not establish full capstone completion or independent semantic accuracy.
