# Evaluation reference consolidation

## Final organization

- `evaluation/development/reference.json`: original golden-case, verification and supplementary-example JSON objects grouped into named sections; all source fields preserved, with original artifact hashes.
- `evaluation/development/review.md`: two complete human-readable guides combined under one title; local links rebased.
- `evaluation/development/evidence/{financial,risk_msft_nvda,risk_jpm_meta,refusal,scoring}/`: detailed evidence grouped by purpose, byte-identical.
- `evaluation/heldout/`: original historical Role 5 review/manifest, byte-identical.
- `evaluation/README.md`: one reference index replacing the former nested index.

Five answer/review files became two. The old `domain_reference/` directory and the two former documentation guides were removed. Current Markdown consumers and the active held-out metadata pointer now target the new paths. Artifact-manifest keys/hashes describe the consolidated layout; original release hashes embedded in evidence remain historical. Original source files are recoverable in the ignored `.migration-local/reference-consolidation/originals.zip` archive. Historical evidence/checkpoint text was not rewritten.

This is packaging only: no new cases, expected answers, scoring rules, functionality, evaluation scores or independence claims. Runnable datasets remain in `data/evaluation/`. JSON sections were compared structurally against the original archived files; detailed evidence hashes and new guide/index links were checked. No live evaluations or API-credit tests were run.

Offline gate: 538 tests, 533 passed, five unchanged skips, zero failures/errors. Test IDs match the preceding checkpoint. All 16 moved detailed evidence/historical held-out files remain byte-identical.
