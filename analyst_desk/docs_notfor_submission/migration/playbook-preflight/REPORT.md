# E3 after-playbook preflight

The evaluator now rejects the explicit lessons-enabled experiment when its frozen snapshot is missing, empty, malformed or lacks a nonblank version. It also rejects --no-lessons with that experiment. The check applies to dev overrides as well as held-out runs and happens before case loading or model execution. The before-playbook baseline still needs no snapshot; other experiment behavior is unchanged.

Added mocked runner regressions for invalid snapshots on both splits, conflicting CLI flags, a valid populated snapshot and the before-playbook baseline. All case loading/model execution is mocked in these tests. No real saved playbook was opened or modified.

Offline gate: 541 tests, 536 passed, five unchanged skips, zero failures/errors. All 538 prior tests remain present; three regression tests added. No provider calls or actual evaluation cases executed.
