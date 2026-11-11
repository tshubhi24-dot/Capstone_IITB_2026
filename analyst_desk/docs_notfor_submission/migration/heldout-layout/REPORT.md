# Held-out Dataset Consolidation

Created one active `data/evaluation/heldout/heldout_cases.jsonl` with all 64 records: 22 numeric, 16 comparison, 16 risk-change, 10 refusal. IDs/types were inspected for integrity; expected-answer fields and question semantics were not inspected. All IDs are unique; no records were dropped or semantically deduplicated. Previous filename-sorted loading order is preserved.

The manifest records the two source releases, original checkout and normalized checksums, source byte ranges, combined checksum and release limitations. Physical CRLF line endings were normalized to LF without changing JSON record contents. Git attributes enforce LF for the canonical file. Historical source hashes used different line-ending conventions; original bytes/metadata remain in the ignored local backup.

Removed the two old active JSONL files. Merged the old dataset README into the existing documentation index; the folder now contains only the canonical dataset and manifest. The source-v2 generator writes ignored evaluator candidates outside the active folder, preventing accidental duplicate inputs. No candidate generation or model evaluation was run.

Historical primary manifests and scored results are unchanged and refer to their original releases. Their old source filenames are historical, recoverable from the source-range/line-ending metadata or local archive; they are not additional active input files. The combined release is not newly certified blind evidence and has not received a new 64-case score. The application remains unable to mount held-out inputs through Compose.

Recovery: repository `.migration-local/heldout-layout/before.zip`, checksum in changes.json. Final byte/ID/type preservation, local references and offline-suite checks are recorded in validation.json.
