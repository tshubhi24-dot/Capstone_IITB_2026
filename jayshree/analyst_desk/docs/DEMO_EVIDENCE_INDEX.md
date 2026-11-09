# Analyst Desk Demonstration Evidence Index

This index supports the [three-story demo](THREE_STORY_DEMO_SCRIPT.md). It distinguishes historical public-company development evidence, captured UI controls, current-source component results and worked examples. It does not establish a complete latest-release live rehearsal.

## Version and decision boundaries

The selected MSFT/Alphabet development case used 42e2298; the reviewed Main source is 33fef7f; the policy baseline is c640912. The selected note is **not accepted for publication as submitted; assessment complete**. Its original numerical check is 7/7, selected judge result 2/8 and aggregate check failed after two revisions. No application approval or publication is established by this assessment.

## Project evidence

| Exhibit | Repository record | What it establishes |
|---|---|---|
| Exact case fingerprint and original checks | [Case metadata](evidence/product_domain/product_acceptance/CASE_METADATA.json) | Task, revision, note fingerprints and preserved check state; no raw runtime/approval body |
| Completed acceptance decision | [Product acceptance review](PRODUCT_ACCEPTANCE_REVIEW.md) and [ledger](evidence/product_domain/product_acceptance/ACCEPTANCE_LEDGER.json) | Criterion-specific decision and required corrections |
| Six financial references | [Financial review](evidence/product_domain/product_acceptance/evidence_financial/FINANCIAL_REVIEW.md) | Exact cached contexts and Decimal ratios, with source limits |
| Narrative and critic assessment | [Claim review](evidence/product_domain/product_acceptance/evidence_claims/CLAIM_REVIEW.md) | Decomposed assertions, excerpts and critic-context limitations; not independent human labels |
| Risk and requested scope | [Risk review](evidence/product_domain/product_acceptance/evidence_risk_scope/RISK_SCOPE_REVIEW.md) | Newness and missing paired-source coverage limits |
| Captured public passages | [Provenance](evidence/product_domain/product_acceptance/PASSAGE_PROVENANCE.json) | Ten exact captured-text matches, issuer/year/Item/accession/line/hash; not full-section coverage |
| Current-source verification | [Status ledger](evidence/product_domain/reverification/CURRENT_STATUS_LEDGER.json) | 117 selected passes/three skips and bounded verification context |
| Numerical and critic diagnostics | [Results](evidence/product_domain/reverification/evidence_critic_numeric_scope/probe_results.json) | 37 targeted observations, including positive controls and counterexamples; the synthetic wrong-margin example is25% versus20% |
| Fiscal version and risk diagnostics | [Results](evidence/product_domain/reverification/evidence_financial_risk/results.json) | 28 targeted observations, including known selection limits |
| Memory security and approval diagnostics | [Results](evidence/product_domain/reverification/evidence_memory_security_readiness/probe_results.json) | 18 synthetic observations, not real publication or an end-to-end attack result |

The 83 diagnostic assertions include counterexamples; reproducing an expected observation does not close the corresponding finding. The 117-test count is a separate selected-test result, not an accuracy score or release-image certification.

## Public screenshots

| Figure | Image | What is visible and its limit |
|---|---|---|
|1 | [Dashboard](assets/demo/01_dashboard.jpg) | Selected Microsoft/Alphabet scope and stored verification summary; not note acceptance |
|2 | [Research controls](assets/demo/03_research_controls.jpg) | C0/C1/C2 selectors, C2 selected, empty request; not a running job |
|3 | [Financial rows](assets/demo/02_financial_table.jpg) | Six financial rows, actual year ends and one-decimal display; two-decimal references are separate calculations |

These are unchanged historical 8 November UI captures. Their bytes match the inspected originals. Screenshots containing unrelated previous-note lists or older saved-run details are excluded; no image was redacted, composited or simulated.

## Outcomes not demonstrated

The evidence does not demonstrate a complete current live run of all stories, parallel-execution timing, live restart/replan, the 45.64% planted-error correction trajectory, end-to-end injection resistance with legitimate task completion, a live stale-approval race, an eligible previous-note memory-on/off comparison or a full backup video. Keep these limitations visible; do not substitute component tests for those outcomes.

Raw research-history/plan exports, signing material, personal preparation and duplicate review drafts are not part of this repository evidence bundle.
