# Final Offline Migration Sign-off

Completed 11 November 2026 on `shubhi-deployment-v1`, starting from `f813e4e61bfcb712d37756b98e1bbded92230f8e`. All cleanup phases 0?6 are complete within the agreed offline scope. No new product functionality, paid evaluations, provider calls, deployment, commit, or push was performed.

## Result

The application now lives in repository-root `analyst_desk/`. UI/research, finance/retrieval, governance/memory, evaluation, maintenance commands, and tests are grouped by function. Seventy-two implementation/test paths moved with their consumers; old implementation copies were removed. `app.py` is the single thin launcher.

Documentation uses one repository overview and one main index, `docs/README.md`, with `docs/SETUP.md` and the program flowchart. Fourteen redundant navigation/alias pages were consolidated/removed during Phase 2. Phase reports retain their separate test/evidence records rather than duplicating logs into another combined folder.

Phase 5 reused the identical timestamp helper, removed redundant import/path glue, archived three obsolete files, and removed 65 orphan bytecode files. Five tiny historical document forwarders remain because original evidence references them; they are compatibility entries, not duplicate document bodies.

## Final gate

The full existing network-blocked suite ran from the final application layout. **538 tests: 533 passed, 5 unchanged skips, 0 failures/errors; exit 0**, in 65.732 seconds on Windows/Python 3.13.11. `test_results.json` records the final result; `validation.json` compares it with Phase 0 using Phase 4E's explicit test-ID map. No missing tests, new skips, relaxed assertions, or live cases were substituted for the gate.

Existing scripted C1/C2 journeys exercise plan review, bounded research, note edits/checks, publication, and budget handling. Existing mocked regressions cover failed/incomplete approval, stale evidence, unknown publication outcomes, memory-sync failure, memory-off, and frozen playbooks. C0 baseline, chart, context and refusal regressions passed; a complete mocked C0 provider-response integration is not present in this existing suite and was not invented as a claim of coverage.

Static review rechecked 243 public signatures, 41 annotated schemas, 72 move destinations, 251 original data paths/sizes, 191 nonprotected data hashes, 47 original manifest-bound file hashes, and 10 unchanged configuration/experiment/dependency files. Protected case/label contents were not inspected. All five recorded recovery archives passed integrity/checksum checks and exclude credentials/runtime stores. The original evidence and failed diagnostic logs remain available.

Local documentation targets, command paths, workflow/build contexts, Docker COPY sources, Compose mounts/modules, review-policy files, exclusion rules and submission-tree metadata were reviewed. The flowchart's plan-edit and bounded-repair arrows were aligned with the final graph code. Mermaid/browser rendering was not executed.

## Limits and remaining release work

- The five baseline skips remain: four real Docker sandbox variants and one Unix file-mode test on Windows. This run uses Python 3.13.11; Python 3.12/Linux parity is not established by the local gate.
- Forty-one pre-existing missing historical policy/report link targets remain disclosed. No replacement evidence or independent human labels were fabricated; there are no new missing local targets in maintained navigation.
- Dummy Compose validation checks configuration only. No images/services were built or started; no submission archive, clean-machine installation, real model-quality evaluation, or live demonstration was executed.
- Independent module-owner/team release acceptance is not claimed. This is technical offline migration sign-off, not independent product/domain certification.
- Local state and keys were preserved, not rewritten. Existing saved reviews may be stale after source/policy relocation and must use the existing recheck/restart behavior. Shared images must match the migrated revision; use local source while these changes are unmerged/unpublished.

## Evidence and handoff

[Final manifest](final_manifest.json) links the movement, removal, consolidation, compatibility and rollback records. [Preservation review](preservation_review.json), [test results](test_results.json), [local checks](local_checks.json), and [validation decision](validation.json) provide the final evidence. The [documentation index](../../README.md#migration-completion) links every phase report; the [cleanup plan](../../PROJECT_CLEANUP_PLAN.md) records completion.

To recover, compare only affected paths with the ignored local archives and movement maps. Archives before Phase 3 use the old `jayshree/analyst_desk/` prefix. Preserve unrelated user edits, credentials, stores and later records; do not use a blanket hard reset, clean, or volume deletion. The archives are local recovery aids, not remote backups.
