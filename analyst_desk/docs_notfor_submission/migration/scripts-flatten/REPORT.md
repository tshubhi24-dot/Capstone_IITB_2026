# Flat submission script directory

Moved evaluation/run.py, evaluation/report.py, operations/ops.py and testing/run_mock_tests.py directly into scripts/. Only the package marker and four entry points remain; the three old subdirectories and their obsolete markers/bytecode were removed. Team-only authoring utilities remain under not_for_submission/scripts/ as previously requested.

Adjusted each moved entry point's application-root calculation by one level. Updated imports, UI instructions, CI commands, contributor guidance, setup and current README examples. Implementations and workflow options are unchanged; historical checkpoint/evidence text retains historical paths. Original scripts are recoverable in ignored .migration-local/scripts-flatten/originals.zip.

Syntax/AST comparison confirms only root and documented command paths changed. Direct help checks pass for the three command entry points. The full network-blocked mock runner now executes from its flat path. No live evaluation, HTTP smoke check, memory recovery or provider call was launched.

Offline gate: 550 tests, 545 passed, five unchanged skips, zero failures/errors; test IDs unchanged.
