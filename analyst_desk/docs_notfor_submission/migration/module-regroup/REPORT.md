# Core Module Regrouping

Moved five modules to their functional homes: `config/llm_config.py`, `research/note.py`, `research/scope.py`, `monitoring/observability.py`, and `monitoring/alerts.py`, all under `analystdesk/`. `paths.py` stays at package root. Old implementation files were removed rather than wrapped or copied.

Updated callers, test imports/mock targets, current source links, project structure/contributor instructions, and review-policy source fingerprints. Configuration still loads the existing application-level `config/llm.toml` through APP_ROOT; prompt/model data and environment-variable names are unchanged. Public signatures and annotated class fields were compared before/after and match.

The full network-blocked regression gate uses the same test IDs/skips as the preceding checkpoint. Final results are in test_results.json and validation.json. Recovery source copy is repository `.migration-local/module-regroup/before.zip`; changes.json records the exact paths. No new product functionality, duplicate legacy modules, paid calls, service starts, commits or pushes.
