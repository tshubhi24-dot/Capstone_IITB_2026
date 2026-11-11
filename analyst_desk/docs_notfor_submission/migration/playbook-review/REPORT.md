# Development playbook review

Reviewed 35 pending and three previously approved development reflection records. Most repeat numeric citation advice; some incorrectly imply all code-derived quantities must be quoted verbatim from filings. Consolidated the useful guidance into six generic process lessons: registered figure placeholders, deterministic derived calculations, exact source quotations, claim-level support, paired-year risk evidence and bounded risk labels.

The source-linked review pack is `not_for_submission/playbook/development_lessons.json`. It contains generic workflow guidance rather than benchmark answers. Original lesson values, histories and the former frozen snapshot are recoverable in ignored `.migration-local/playbook-review/`; raw historical critic messages remain local. Approval is explicitly attributed to assistant-assisted review at the user's request, not independent human/Role 5 sign-off. The unmatched fiscal-year draft was retired rather than treated as supported by an unrelated risk-claim issue.

Prepared and validated the new snapshot in an isolated lesson-only store using existing playbook APIs, then activated lesson namespaces atomically with concurrency checks. Nonlesson preferences, notes, coverage and watchlist bytes were verified unchanged. Superseded records remain in rejected/review history with reasons; they were not erased. There are now six approved/frozen lessons, no pending records and 39 retained rejected/superseded records.

Six offline relevance probes confirm the intended lesson appears among the existing top-three retrieval results for numeric reporting, derived changes, quotations, narrative claims and risk comparisons. The existing plan/writer workflow consumes these frozen lessons without a code change. No model call, protected evaluation or independent learning-benefit claim was made.

This changes the local `.runtime/memory/memory.sqlite` store only. Docker's separate named memory volume was not opened or changed; the review pack is team material and is not automatically imported into other workstations or containers. Existing or resumed runs can retain their prior selected lessons; new runs use the newly frozen snapshot when lessons are enabled.

Final validation: 547 offline tests, 542 passed, five unchanged skips, no failures/errors. Test IDs unchanged. Active frozen lesson records match the validated staged snapshot after the suite. Previous version `8f1608da4cec`; new version `806f51dd6960`. No provider calls.
