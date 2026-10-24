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

On 24 October 2026 the human spending gate authorized the prepared US$1 policy; subsequent diagnostic attempts remained within that policy. Five application planner attempts stopped. One direct operator diagnostic used the same persistent ledger and research scope, and recovered a provider-reported Terms of Service refusal. It did not identify the specific rule. Both approved models were listed in the catalogue. Six total attempts retain their reservations within the original policy. See the [access diagnosis](../evidence/openrouter_access_diagnosis.json). That route remains stopped. Step 10 activated the reviewed Mistral pair within the same original cap, retaining every old hold. The grounded live plan is now explicitly approved; the writer stopped before criticism, human note review or publication. See the [current pilot status](../evidence/live_pilot_status.json). [Restart verification after the second attempt](../evidence/live_attempt_verification.json) remains historical evidence.

This increment adds bounded model-assisted planning, query choice, disclosure interpretation, writing and internal criticism. It retains BM25 retrieval and the cached SEC snapshot. It does not establish full capstone completion or independent semantic accuracy.
