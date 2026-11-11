# Phase 4D ? Evaluation and Command Grouping

Complete: scoring/experiments/red-team modules grouped under evaluation. Eighteen utility scripts grouped into evaluation, data, operations and testing; direct callers, script-root bootstrap, import/patch targets, workflow commands and deployment import expressions updated. The mock gate is now `python scripts/testing/run_mock_tests.py`. No legacy script wrappers/copies remain. Protected cases/results were not opened or regenerated.

A first gate found one stale calibration-fixture filename; the failed log is retained. After correcting that path and finalizing package/deployment references, the full gate passed: 538 run, 533 passed, five unchanged skips, no failures/errors. Scoring semantics and experiment switches are unchanged. Redundancy review: twenty-one old implementation paths removed; package markers establish clear command ownership.
