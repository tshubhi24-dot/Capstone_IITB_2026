# Experiment split alignment

Changed both E4 presets from development to held-out defaults to match E1. CLI overrides remain supported: use `--split dev` for both baseline and ablation during development. Configurations, switches and historical scores remain unchanged.

Existing archived baseline and E4 metadata inspected for this issue both name development and contain 20 rows per configuration. This does not prove all other experiment conditions matched, and no historical results were regenerated.

Validation: 538 offline tests, 533 passed, five unchanged skips, zero failures/errors; test IDs unchanged. Parsed E1 and both E4 files all default to held-out. No live evaluations or API calls.
