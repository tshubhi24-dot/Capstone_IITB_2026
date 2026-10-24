# Kickoff evaluation pack

**Prepared 22 October 2026; portable export 24 October 2026 | Public development material | Not a final holdout**

Use this pack with the [project definition](../../docs/PROJECT_DEFINITION.md) and [evaluation plan](../../docs/EVALUATION_PLAN.md). It prepares development questions and source-derived expectations before running the system. It does not contain independently authored final questions or completed human labels.

## What is ready

| File | Purpose | Status |
|---|---|---|
| `development_cases.jsonl` | Twenty public development questions: ten numeric, six comparison and four risk cases. | AI-assisted preparation; review with the domain owner before use. |
| `development_expected.jsonl` | Prewritten numerical expectations and risk evidence/checklists. | Numerical values derived from the cached real-source facts; risk judgments require human annotation. |
| `dataset_manifest.json` | Sources, provenance, issuer allocation and eligibility. | Development only; no claim of final evaluation eligibility. |
| `preparation_validation.json` | Recorded static checks of counts, arithmetic, source references, hashes and links. | Passed; this is preparation integrity, not model performance or independent human validation. |
| `retrieval_labels_template.csv` | Thirty slots for questions and independently checked relevant passage IDs. | Blank labels; prepare before measuring Recall@5. |
| `risk_labels_template.csv` | Ten company-year annotation slots for comparison with the prior year. | Blank labels; inspect the original Item 1A evidence. |
| `judge_labels_template.csv` | Twenty slots for distinct actual outputs, human labels and different-family judge labels. | Blank; existing outputs and model judgments must be captured and genuinely labelled. |
| `independent_attack_template.csv` | Thirty attack slots, each paired with a legitimate clean control. | Blank; give to the independent attack author. |
| `protected_case_template.json` | Blank record structure for the independent evaluator's case authoring. | Contains no protected question or expected answer. |

The development allocation is **MSFT, AAPL, ABBV and AMGN**. The proposed reserved issuers are **GOOGL, ORCL, ADBE, CRM, GILD, ABT, UNH and TMO**. Reserving issuer names does not create an unseen benchmark: the independent evaluator must author new questions and expectations, document any prior exposure, and review the split. Prior exposed practice questions across the baseline companies must not be reused as final evidence.

## How to use the pack

1. Assign actual domain, tuning, defence and independent evaluation owners. The tuner does not author protected questions; the defence builder does not author the attacks.
2. Have the domain owner check the development questions, source facts, annual periods, currency/scale and expected formulas. A prepared expectation is not a completed human review.
3. Complete risk and retrieval relevance annotations against the exact frozen source versions. Keep materiality judgments separate from mechanical text differences.
4. Run development checks only after preserving these expectations and the chosen configuration. These files are an authoring handoff. The current implementation must add a deliberate, validated evaluation adapter before treating them as runnable inputs.
5. Give the independent evaluator a copy of the blank protected-case/attack structures. That person works in a separately controlled location outside application images, mounts, agent tools and builder access. Do not put completed protected questions or gold answers in this public pack or in `docs/`.
6. Prepare at least forty protected cases, keep related variants together, verify expected outcomes before execution, record authors/reviewers, freeze and hash the assets, and follow the final admission checks in the evaluation plan.

## Interpretation and integrity

- Numeric expectations are grounded in the cached facts; independent verification must still check the original filing/XBRL source and period/unit selection.
- A margin uses operating income divided by revenue, multiplied by 100. Financial-year labels and actual dates must both remain visible.
- Risk evidence windows identify source material to inspect. Null semantic labels mean **unreviewed**, not supported, unchanged or passed.
- Blank template rows do not satisfy the required query, attack, calibration or risk-label counts.
- This preparation makes no model calls, runs no final experiments, approves no note and creates no human review record. Costs and performance remain unmeasured.
- Gold answers remain evaluator-side. Final evaluation stops at note review and cannot publish the benchmark outputs into memory or generate development lessons from them.

Use the [protected execution protocol](../../docs/EVALUATION_PLAN.md#6-freeze-protected-execution-and-reporting) and [judge calibration rules](../../docs/EVALUATION_PLAN.md#2-datasets-and-preparation-order) for the new evaluator. Runtime admission checks remain implementation work.

## Portable source provenance

Only this public development preparation pack is included. The originating cached SEC corpus and ingestion manifest are not committed here. `source_corpus_sha256` and source-manifest hashes identify that original frozen preparation snapshot; they are not hashes of an included repository file. Public filing URLs, accessions, exact annual periods and XBRL concepts remain attached to the expected rows so independent source review is possible.

The current build will import source data separately, retain the original provenance and record its newly imported snapshot hash. A newly constructed parser/index may produce different passage IDs or corpus bytes; map references explicitly and rerun source review instead of replacing origin hashes or silently claiming equivalence. The FY2022 refusal is relative to the declared FY2023–FY2025 frozen coverage, not a claim that a public FY2022 filing does not exist.

`preparation_validation.json` separates the original source-backed preparation checks from portable-export checks. Export validation does not revalidate a raw corpus that is absent from this repository.
