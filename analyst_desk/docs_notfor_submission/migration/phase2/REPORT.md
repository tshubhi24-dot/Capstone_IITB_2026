# Phase 2 — Documentation and Presentation Cleanup

Starting source revision: `f813e4e61bfcb712d37756b98e1bbded92230f8e`. Phase 2 organizes documentation only. Application source, configuration, tests, protected evaluation assets, runtime stores, and earlier checkpoint artifacts remain unchanged.

## Changes

- Added repository-root navigation and a functional documentation index.
- Established [Setup and Run Analyst Desk](../../SETUP.md) as the canonical usage guide. Published-image launchers, local Docker source builds, Python development, and mock-only migration validation are distinct.
- Classified 22 existing documents. Six unbound architecture/policy documents moved into functional folders with legacy forwarding pages/heading anchors. Sixteen manifest-bound originals (nine Markdown and seven Word) remain unchanged at their original paths; grouped navigation points to them.
- Updated maintained Markdown links relative to their new locations; preserved historical public evidence ledgers and Phase 0/1 checkpoints.
- Extracted the cleanup plan's flowchart into [one maintained program-flow source](../../architecture/program_flow.md), linked from the plan, navigation, and submission checklist.
- Recorded editable sources/export limits and retained generated-report paths where scripts and CI currently expect them. Presentation source and existing deck remain in their established locations; no presentation tooling was installed or run.
- Recorded known absent historical targets without inventing policy originals or research evidence. No substantive document was deleted as redundant; old flat navigation is superseded by indexes/forwarding pages.

## Artifacts and recovery

| File | Purpose |
|---|---|
| [starting_git_status.txt](starting_git_status.txt) | Existing work before Phase 2. |
| [document_moves.json](document_moves.json) | Candidate/grouped paths, actual move versus retained-original decisions, pre-phase hashes, and canonical paths. |
| [source_export_manifest.csv](source_export_manifest.csv) | Seven original-path Word editions and their Markdown counterparts; export equivalence remains unverified. |
| [recovery.json](recovery.json) | Ignored local backup location/checksum and rollback instructions. |
| [preexisting_missing_links.json](preexisting_missing_links.json) | 41 inherited missing file targets. |
| `link_check.json` | Local target checks, scope, and newly introduced versus inherited gaps. |
| `test_ids.json`, `test_results.json`, `mock_tests.log` | Full offline regression results, recorded separately from earlier phases. |
| `validation.json` | Exact test-ID/skip comparison, unchanged frozen application files, and document-preservation checks. |

Rollback requires comparing only affected documentation with `.migration-local/phase2/documentation_before.zip` and consulting the movement register; restore original paths/content while preserving unrelated user edits. Remove only Phase 2-created navigation/forwarding artifacts after review. Do not reset the repository, touch runtime data, or overwrite Phase 0/1 evidence.

## Scope and verification limits

The baseline link scan identified 40 missing policy-original links in two historical records and one missing red-team report link in submission viva preparation. These are inherited checkout gaps; the source/export rules disclose them. File-target checks do not validate external URLs, binary-embedded links, or browser rendering. Legacy section anchors are retained for moved Markdown; programmatic checks focus on relative local file targets, with new-navigation fragment references reviewed separately.

No services, paid evaluations, live demos, model APIs, or dependency downloads are used for this phase. Mock-test success preserves existing behavior; it does not close independent product/domain evidence obligations. Phase 3 application-root migration has not started.

Final gate outcome is recorded in `validation.json` and the cleanup plan's execution table. Any new missing navigation target, changed frozen application hash, unexplained missing test, new skip, or failed test blocks completion.

## Completed gate

**Phase 2 complete.** The full offline suite ran 538 tests: 533 passed, five unchanged skips, zero failures/errors, exit 0. Test IDs and skip reasons exactly match Phase 0. All 123 frozen application/test/config/build files remain unchanged. Local checks covered 567 file targets with zero new missing targets; the 41 inherited gaps remain disclosed. All seven Word editions and 21 manifest-bound backup records are unchanged. See [validation.json](validation.json), [document preservation](document_preservation.json), [path checks](path_checks.json), and [link audit](link_check.json). No live/API-credit validation was used.

## Navigation consolidation follow-up

At the user's request, five navigation/source-guidance pages were merged into `docs/README.md`, nine redundant grouped aliases removed, the setup guide renamed to `docs/SETUP.md`, and phase summaries renamed to `REPORT.md`. This reduces the file count by 14 without deleting original evidence. Links in unbound navigation/reports were updated; original test snapshots and evidence records remain separate. The six legacy forwarding pages remain temporarily because source/historical consumers still use their paths; their removal is a later consumer-migration check.

The cleanup plan and contributor guide now require a redundancy review and safe consolidation in every phase. Actual code helper consolidation remains part of the affected module phase, with unchanged behavior and offline tests; no source merging was invented for a documentation-only change.

Follow-up gate: 538 tests, 533 passed, five unchanged skips, zero failures/errors; exact IDs/skips match Phase 0. No new missing links; 41 inherited gaps remain recorded. All 123 frozen source/test/config/build hashes remain unchanged. See [consolidation decisions](consolidation.json), [test results](consolidation_test_results.json), and [link check](consolidation_link_check.json). No API credits used.
