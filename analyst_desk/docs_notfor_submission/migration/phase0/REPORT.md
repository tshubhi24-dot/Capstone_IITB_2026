# Phase 0 — Migration Baseline

Completed 11 November 2026 on branch `shubhi-deployment-v1`, starting commit `f813e4e61bfcb712d37756b98e1bbded92230f8e`.

This checkpoint inventories the existing project and establishes an offline regression gate. It does not approve removals, verify all policy findings, or implement a structural migration. Phase 1 owns the detailed public-contract/safety inventory.

## Deliverables

| Artifact | Purpose |
|---|---|
| [git_status.txt](git_status.txt) | Working-tree state at capture, including existing untracked documents/results. |
| [file_inventory.json](file_inventory.json) | 476 tracked/untracked file entries, sizes, and eligible SHA-256 hashes. Generated Phase 0 artifacts excluded to avoid recursive snapshots. |
| [environment.json](environment.json) | Interpreter, platform, dependency-file hashes, and credential-file existence only. |
| [installed_packages.json](installed_packages.json) | 191 installed package names and versions, without index URLs or credentials. |
| [movement_removal_manifest.csv](movement_removal_manifest.csv) | Per-file candidate action, destination, owner, purpose, canonical replacement, and lexical consumer candidates. No deletion is approved. |
| [test_ids.json](test_ids.json) | Sorted discovery inventory for comparison after every phase/subphase. |
| [test_results.json](test_results.json) | Machine-readable counts, skips, duration, and success status. |
| [mock_tests.log](mock_tests.log) | Verbose test execution evidence. |
| [validation.json](validation.json) | Verified manifest count, recovery ZIP integrity/checksum, and 83 unchanged source/config/test hashes. |
| [recovery.json](recovery.json) | Baseline Git revision and local working-document backup location/checksum. |
| [evidence_locations.md](evidence_locations.md) | Corpus, evaluation, policy, submission, and runtime boundaries. |

## Test result and rerun

```powershell
# From jayshree/analyst_desk; use python in the activated venv on other platforms.
.\.venv\Scripts\python.exe scripts/run_mock_tests.py --report-dir docs/migration/phase0
```

Use a **new report directory for each later checkpoint** (for example `docs/migration/phase1`) instead of overwriting Phase 0. Keep all test IDs, including skipped tests; compare renamed IDs explicitly when organizing tests.

Result: **538 discovered/run; 533 passed; 0 failures; 0 errors; 5 skipped; exit 0**, in 40.341 seconds. Python 3.13.11 on Windows; CI's Python 3.12/Linux environment was not exercised. Four Docker sandbox variants were deliberately skipped; the Unix key-file permission check is platform-skipped. Exact IDs and reasons are in the result JSON. No extra test skips were introduced.

Tests used existing mocks/scripted models, cached fixtures, and temporary stores. The gate blocks normal sockets/DNS, prevents model downloads, disables dotenv and telemetry, and uses dummy provider keys. Windows asyncio's internal socketpair construction is permitted. This is a Python-process guard, not an OS sandbox for arbitrary subprocesses. No live smoke checks, paid evaluations, service startups, dependency downloads, or real publication were performed.

## Inventory and recovery limitations

- `git_status.txt` records the capture point, not subsequent Phase 0 documentation edits. Existing untracked files remain untracked; nothing was committed or pushed.
- Protected evaluation files were inspected by path/size only, without reading answers, labels, or case contents. Their hashes are intentionally absent. Consumer searches exclude those contents and secrets.
- Consumer entries are lexical leads, capped at 25 per file. Dynamic imports and generated consumers still require Phase 1 review. Candidate destinations are provisional; the manifest is not an executable move script.
- Ignored credential/runtime directories are outside the tracked/untracked file snapshot. Their presence and preservation rules are recorded in the evidence index. No keys or `.env` values were copied.
- Git reported permission-denied warnings for ignored `.review_dependencies/pypdf/` and its distribution directory. Their contents were not inspected or removed; they are outside application source and the migration baseline's scope.
- Tracked original source is recoverable from the recorded local Git commit. A ZIP of eligible pre-existing untracked working documents/tooling is stored under repository `.migration-local/phase0/`, excluded by `.gitignore`. The archive includes the pre-Phase-0 versions of planning documents, where present. Its checksum is recorded in `recovery.json`. It is a local recovery aid, not a remote backup.
- Untracked evaluation-result files, credentials, and runtime stores are excluded from that ZIP and remain in their original locations. Before any later phase changes them, its owner must arrange a suitable backup. No current phase changes them.

To recover a later failed phase, preserve its diff and user changes, recover only that phase's affected tracked paths from the recorded checkpoint, and restore eligible untracked documents from the ZIP to a separate comparison directory first. Never use a blanket hard reset, clean, or volume deletion. Do not restore this baseline over unrelated later work.

## Completion criteria

- [x] Starting revision and working-tree state recorded.
- [x] Installed interpreter/dependencies recorded without credentials.
- [x] Existing source/evidence locations and preservation boundaries recorded.
- [x] Movement/removal candidate manifest created; no removal approved.
- [x] Recovery reference and eligible untracked-document backup created.
- [x] Full offline suite passed; IDs/counts/skips retained.
- [x] No application behavior, directory structure, or source evidence changed.

**Decision:** Phase 0 complete. Phase 1 may begin separately; its contracts and safety review have not been marked complete.
