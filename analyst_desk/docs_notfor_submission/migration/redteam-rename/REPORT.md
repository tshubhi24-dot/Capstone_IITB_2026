# Red-team Dataset Rename

Renamed `attacks_v1.jsonl` to `redteam_attacks_cases.jsonl` as requested. The contents are byte-identical; no attack records or expected conditions were inspected or modified. The existing directory-based JSONL loader requires no change. Manifest filename, generator output and maintained documentation references now use the new name. Historical evidence records retain their original context.

The original manifest is saved locally under `.migration-local/redteam-rename/`; the dataset itself can be recovered by reversing the rename. changes.json records the unchanged data hash. Final offline gate results are in test_results.json and validation.json. No attacks/model evaluations, paid API calls, service starts, commits or pushes.
