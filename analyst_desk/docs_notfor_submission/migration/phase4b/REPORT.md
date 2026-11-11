# Phase 4B ? Finance and Retrieval Grouping

Complete: six finance/retrieval modules moved, all consumers/mock targets updated, and path-dependent data locations preserved with APP_ROOT. Review-policy fingerprint paths were migrated to the new module locations; existing saved review snapshots must be rechecked after source/policy changes, never silently accepted.

The first gate found seven errors caused by stale policy-file paths; its log is retained. After fixing those references, the full gate passed: 538 run, 533 passed, five unchanged skips, no failures/errors. No algorithm, corpus IDs, prompts or financial rules changed. Old implementation files were removed, not copied or wrapped. See changes.json and test artifacts.
