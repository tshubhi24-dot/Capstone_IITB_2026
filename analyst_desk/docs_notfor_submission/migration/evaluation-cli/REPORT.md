# Unified evaluation commands

Nine standalone evaluation scripts now have two command entry points: `scripts/evaluation/run.py` (eval, redteam, retrieval, financebench, memory, calibrate, reflect) and `scripts/evaluation/report.py` (audit, repeats). Existing options remain available after the workflow name. Memory/calibration/reflection now have explicit argument parsing and safe help; unknown workflows/arguments fail before execution. No default command launches an evaluation.

Each existing implementation moved once to `analystdesk/evaluation/workflows/`, with its prior standalone entry block removed and application-root calculation adjusted. The two CLIs route to those implementations; they contain no duplicate scoring, retrieval or learning logic. This reduces user-facing scripts, not the number of distinct workflow implementations. No old script wrappers remain.

Updated UI imports, mock targets, CI, current docs and pending fresh-run commands. Docker copies both the application implementation and the two CLIs through its existing COPY rules. Historical checkpoint/evidence text remains historical. Recovery originals are in ignored `.migration-local/evaluation-cli/originals.zip`.

Added mocked routing tests for all workflows, forwarded arguments, exit codes, help, invalid commands and memory option conflicts. Real datasets, saved playbook records, provider calls and generators were not used by those tests. E3 preflight regressions remain in the suite.

Validation: 547 tests, 542 passed, five unchanged skips, no failures/errors. All 541 previous test IDs remain, with six new routing tests. All nine workflow help commands checked with network blocked; real unified audit CLI passed against the archived 20-case baseline read-only. Workflow function bodies match originals apart from updated command/import paths. No live evaluations/provider calls.
