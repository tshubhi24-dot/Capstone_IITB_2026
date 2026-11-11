# Retrieval Dataset Rename

Renamed data/evaluation/retrieval_queries.jsonl to retrieval_cases.jsonl. Dataset bytes and labels are unchanged. Updated evaluator input/report-generation references and current documentation links. Historical archived runs/query snapshots remain untouched. The fresh pre-submission retrieval run is still pending.

The offline suite outcome is recorded in test_results.json and validation.json. No retrieval/index build, provider request, fresh benchmark, commit or push was executed. Reverse the rename and reference changes to recover; changes.json records the unchanged dataset hash.
