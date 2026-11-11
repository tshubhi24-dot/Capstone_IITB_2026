# Development Case Folder Consolidation

Moved the two existing development datasets into `data/evaluation/development/`: `core_cases.jsonl` (20 original benchmark cases) and `former_heldout_v1.jsonl` (24 reclassified development cases). Their bytes, contents and combined loading order are unchanged. The original dev_extra README initially became `PROVENANCE.md`; its contents have since been merged into the main [documentation README](../../README.md#development-cases), and that standalone file was removed. No duplicate dataset copy is retained.

Updated the development loader, case-generator output/deduplication paths, unit fixture input, CI/audit case paths, and the read-only Compose development mount. The frozen core-only audit still uses only core_cases.jsonl. Existing audit JSON/Markdown gold-source metadata was rebased to the new path; all outcomes, counts and source hashes remain unchanged. No evaluation results were regenerated, held-out v2 files opened/changed, or cases executed against models.

Recovery copy is repository `.migration-local/development-layout/before.zip`. See changes.json, case_preservation.json, test_results.json and validation.json. The evaluator continues loading 44 development cases, core first.

The recorded core-only audit and offline CI still use the 20-case core file. The manually triggered full-development workflow audits the development directory, matching the 44-case set its runner loads; that workflow was not executed.

Documentation consolidation: development-case counts and origins now have one maintained source in docs/README.md. This Markdown-only change preserves both JSONL hashes; no model cases or test suite were rerun for it.

Naming clarification: the 24 formerly held-out development cases now use `supplementary_cases.jsonl`. Their classification and contents are unchanged. The only active held-out file is `heldout/heldout_cases.jsonl` (64 records); exposed development cases were not relabelled as blind held-out evidence.

Filename-clarification gate: 533 passed, five unchanged skips, no failures/errors. See rename_test_results.json; no API credits used.

Requested final names: `dev_cases.jsonl` (20) and `additonal_dev_cases.jsonl` (24), spelling as requested. Live loaders/generators, audit/CI paths and current documentation are updated; case contents and primary-first order are unchanged. Gate: 533 passed, five unchanged skips, no failures/errors; no API calls. See requested_renames.json and requested_rename_test_results.json.
