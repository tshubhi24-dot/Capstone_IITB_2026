# Portal and run storage relocation

Moved local portal records and run checkpoints from `data/portal/` and `data/runs/` into Git-ignored, Docker-excluded `.runtime/portal/` and `.runtime/runs/`. Updated application defaults, Docker directory initialization and mount targets; existing named-volume identities are unchanged. No services or Docker volumes were modified.

Both saved files remain byte-identical after validation; database records were not inspected. External path overrides retain their behavior.

Offline validation: 538 tests, 533 passed, five unchanged skips, no failures/errors; test IDs unchanged. Dummy-environment Compose configuration validates successfully. No live evaluations, model calls or index rebuilds were performed. See `validation.json` and `test_results.json`.
