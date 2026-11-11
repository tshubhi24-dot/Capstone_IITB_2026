# Unified operations command

Merged deployment smoke checking and memory recovery into one implementation and entry point: `scripts/operations/ops.py`. Use `smoke` with existing URL/output options, or `backfill-memory --analyst NAME`. Explicit subcommands are required; help and invalid arguments never execute either workflow. Removed both old scripts without compatibility copies.

Preserved the smoke-check functions and memory recovery body. Recovery still opens portal rows read-only, skips withdrawn/superseded notes and notes deleted from memory, and writes eligible remembered-note data through the existing API. Dependency imports for recovery are deferred until that workflow is selected.

Updated UI recovery instructions, current docs, script references and mock imports. Root README explains the command and its parameters. Added mocked command regressions for smoke URL routing/failure status, recovery exclusions/analyst routing and side-effect-free help/invalid arguments. No live HTTP checks, saved-note recovery, model calls or Docker operations were performed.

Original scripts are recoverable from ignored `.migration-local/operations-cli/originals.zip`. Historical records retain original paths.

Offline gate: 550 tests, 545 passed, five unchanged skips, no failures/errors. All 547 previous test IDs retained, three command regressions added. Current script links verified. No actual recovery, live HTTP checks or API calls.
