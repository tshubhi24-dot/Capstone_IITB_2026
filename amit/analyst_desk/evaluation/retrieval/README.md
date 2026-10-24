# Retrieval development comparison

This pack compares BM25, hybrid retrieval and hybrid retrieval with reranking on the same twelve-company source snapshot. It supplies **36 public development questions** across Microsoft, Apple, AbbVie and Amgen, covering FY2023–2025. These are the four development issuers declared in the [evaluation plan](../../docs/EVALUATION_PLAN.md). The other eight issuers have no questions or relevance labels in this pack.

| File | Purpose |
|---|---|
| [development_queries.jsonl](development_queries.jsonl) | Frozen questions, scope, source-derived partial relevance labels, exact SEC links and evidence hashes. |
| [evaluate_retrieval.py](../../ops/evaluate_retrieval.py) | Offline paired comparison, admission checks, per-query results and aggregate metrics. |
| [test_retrieval_evaluation.py](../../tests/test_retrieval_evaluation.py) | Checks metric denominators, provenance, development boundaries and invalid-result accounting. |

## Questions and evidence

There are three questions for each of twelve company/year combinations: **24 narrative questions and 12 retained-table questions**. Questions ask about AI investment, customer security, concentrated manufacturing, continuity, patent/exclusivity erosion, development costs, clinical trials and financial tables. They paraphrase source topics rather than copying complete filing sentences. Related questions retain a common scenario ID across fiscal years; the 36 questions form twelve correlated topic families and are not 36 independent samples.

The builder inspected the cached filing passages and retained table cells to prepare the questions and **42 relevant passage labels before running retrieval**. Each label includes the exact original passage ID, filing URL, Item, content hash, short inspection excerpt and relevance rationale. These are source-derived development labels. Independent human relevance review remains pending.

The canonical evidence unit is the **original cached passage ID**. A retained table and its cell grid count as one passage. A label's evidence hash covers its ID, issuer, year, Item, SEC URL, text and actual table cells where present. Adjacent passages remain separate units when both are labelled relevant. The pack does not automatically merge similar passages or assume that unlabelled overlapping passages are irrelevant.

Labels describe a **partial relevant passage set**, rather than all relevant passages in the filing. Some relevant passages may be unlabelled. The report therefore calls its primary measure `sampled_label_recall_at_5`: the portion of the prepared relevant set returned in the first five results. Do not present it as exhaustive relevance recall, independently labelled gold, held-out performance, risk-interpretation accuracy or capstone completion.

## Frozen inputs

The following hashes were fixed before the first retrieval comparison:

| Asset | SHA256 |
|---|---|
| Twelve-company corpus | `14dd61761199082124b65c5600cd0a0629e636c6e36eec53b110a83ea4a80897` |
| Development query JSONL | `ab0e30ef73499e4adb8f1385e0f9af9f459e1504cc42c77be8a0107769d22d9a` |

Changing the source snapshot, questions or labels requires a new, declared development version and review. Do not edit a missed label, discard a difficult query or tune ranking after inspecting these results and then describe the replacement as the original frozen comparison. Source HTML boundaries and financial comparability still require the domain review described in the evaluation plan.

## Comparison protocol

1. Load all questions and validate their frozen hash before any search. Require at least thirty complete records, development issuer membership, FY2023–2025 scope, unchanged corpus hash and valid source evidence for every label.
2. Run each question through `bm25`, `hybrid` and `hybrid_rerank`, with the same source snapshot, table-aware document representation, issuer/year filters and `k=5`.
3. Keep every attempted query in each arm's denominator. Empty results have zero recall and zero hits. Exceptions, duplicate IDs, unknown IDs, more than five results or a scope escape count as errors and zero recall; the report preserves their safe error class.
4. Record the full paired results and hashes before interpreting averages. Compare every query and show improved, unchanged and regressed counts against BM25. Do not select only examples where the new method wins.

**Sampled-label Recall@5** for a question is `labelled relevant IDs retrieved / all labelled relevant IDs`. Its maximum is `min(5, label_count) / label_count`; the harness reports that ceiling rather than dropping labels to raise a score. **Hit@5** is one when any labelled relevant ID is retrieved and zero otherwise. Aggregate scores are macro-averages over all attempted questions. Results include separate narrative/table, issuer and topic-family breakdowns.

All three arms use text and retained table cells, so the paired comparison isolates retrieval/reranking changes from adding table text. It is not a comparison against the old text-only implementation. Local learned embedding and cross-encoder inference require the prepared retrieval artifacts; no paid generative model or OpenRouter request is involved. Initialization and cache warming differ by arm, so recorded elapsed times are diagnostic rather than a controlled latency benchmark.

## Run locally

From the Analyst Desk application directory, use the project's Python environment and prepared retrieval artifacts:

```sh
python ops/evaluate_retrieval.py \
  --corpus .runtime/journey/sources/corpus.json \
  --queries evaluation/retrieval/development_queries.jsonl \
  --expected-query-sha256 ab0e30ef73499e4adb8f1385e0f9af9f459e1504cc42c77be8a0107769d22d9a \
  --output .runtime/retrieval/development_comparison.json
```

The corpus and labels are read-only inputs. A failed admission check stops before retrieval; search errors remain in a written result and make the command exit unsuccessfully. The report records zero generative-model calls and external provider requests, while explicitly identifying local embedding and cross-encoder inference. Export only the public development receipt after confirming that it contains no private runtime context.

## Relationship to the capstone

The [evaluation plan](../../docs/EVALUATION_PLAN.md#2-datasets-and-preparation-order) calls for 30+ labelled retrieval questions and a before/after Recall@5 comparison. This pack implements a reproducible **development** comparison toward that requirement. A human relevance review, exhaustive annotation decisions, independent evaluation ownership and protected final cases remain separate work. The provisional 85% final target is not used as a pass/fail gate for these partial, builder-prepared labels.
