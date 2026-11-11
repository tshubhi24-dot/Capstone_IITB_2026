# Phase 4 ? Functional Grouping

Complete: UI/research, finance/retrieval, governance/memory, evaluation/commands, and unit/integration/security tests now have distinct functional homes. Seventy-two implementation/test paths moved with callers updated directly. Only the required app.py launch wrapper remains; no duplicate legacy implementations were retained.

Every subphase passed its own full offline gate (538 run, 533 passed, five skips, no failures/errors). Test regrouping has an explicit Phase 0 ID map. See [4A](../phase4a/REPORT.md), [4B](../phase4b/REPORT.md), [4C](../phase4c/REPORT.md), [4D](../phase4d/REPORT.md), [4E](../phase4e/REPORT.md) and validation.json. Diagnostic failures from stale path inventories are retained in the affected checkpoints.

APP_ROOT preserves runtime/corpus/config paths. Policy fingerprint paths follow moved code and include the shared locator; existing saved approvals/reviews are not rewritten or silently upgraded. Source changes require fresh verification under the existing stale-review guard. No model calls, paid evaluations, corpus rewrites or feature additions occurred.
