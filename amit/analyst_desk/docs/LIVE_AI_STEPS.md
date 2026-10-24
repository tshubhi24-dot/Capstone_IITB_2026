# Live AI increment: step-by-step commits

Work stays on `Amit/analyst_desk`, under this contribution folder. No direct merge to `main` is part of this task. Keep the first approved offline note and its evidence intact.

| Step | Deliverable | Verification before its commit |
|---|---|---|
| 6 | [Live reasoning decision](ADR-002-LIVE_REASONING.md), provider adapter, optional gateway and persistent spend ledger | Mocked provider responses, limits, concurrency, restart persistence, schema errors, missing usage and duplicate-call behavior; no paid calls |
| 7 | Evidence-grounded specialist reasoning in the existing graph | Schema, citation/quote/scope checks, qualitative prose checks, both review gates and verdict invalidation after edits; offline regression tests |
| 8 | Optional Docker deployment, private preparation/authorization tools, API and review UI | Merged Compose restrictions, disabled gateway readiness, actual transport, budget visibility and no provider key outside the gateway |
| 9 | First authorized live two-company journey | Explicit spending authorization, actual plan review, checked cited draft, separate note review, measured usage/cost and persistence evidence |

The first three steps can be prepared and tested without a paid call. Step 9 depends on the analyst's authorization of the exact prepared configuration. A refusal or missing key must be reported explicitly; synthetic responses cannot stand in for a live result.

This increment adds bounded model-assisted planning, query choice, disclosure interpretation, writing and internal criticism. It retains BM25 retrieval and the cached SEC snapshot. It does not establish full capstone completion or independent semantic accuracy.
