# Analyst memory: storage and use

## Problem

The desk persists research checkpoints and approved notes, but it has no editable analyst preferences or source coverage memory. Research reads the entire approved library late in drafting and only reports whether history exists. A follow-up needs relevant, bounded history and a clear distinction between an earlier note and current SEC evidence.

## Decision

Use an actor-namespaced LangGraph SQLite store in the existing persistent portal database. Keeping memory versions and publication records in one database allows the publisher to check current memory versions inside the same transaction that saves an approved note. Namespaces provide logical separation; the local app and portal still share operating-system access to that database.

Retain only these explicit preferences: default companies, default fiscal years, table-first or summary-first layout, and a history-reference limit of zero through three. Preferences expire after thirty days. Updates and deletion require the expected revision; deletion preserves a revision marker without retaining the old preference value in a separate audit log.

Save source-derived coverage records under the source fingerprint: available annual facts, section/passages/table counts and stated validation limits. Correct source coverage by importing corrected sources and producing a new fingerprint. Coverage counts do not establish that original SEC Item boundaries or table extraction are complete.

Select at most three approved-note references from a bounded candidate window after actor, issuer and fiscal-year filtering. Store exact note identifiers and payload hashes in the reviewed plan. Earlier source snapshots are labelled archival. Excluding a note from future memory keeps the original approved publication and its approval record in the library.

## Use and review

- Saved defaults help fill the local research form; submitting the form selects the actual request scope.
- Layout is applied by code. Preferences, full historical note bodies and private memory are not automatically added to model prompts or filing queries.
- The plan and final note show the selected local history references. They remain separate from current SEC fact/passage citations and model evidence.
- Current numeric comparisons use code and current canonical facts. Historical wording cannot establish a new, removed or economically material risk.
- Memory versions, expiry and selected note hashes are revalidated before resumed work, model use and approval. Publication repeats the checks inside its transaction. Changed memory requires a fresh plan.
- A memory-off request skips preference/history retrieval. It retains the normal source checks, budgets and human review gates.

## Correction, deletion and limits

The analyst can inspect, replace or delete preferences and exclude or restore a note's eligibility for future history retrieval. This does not silently alter signed publications or erase old checkpoints and backups. SQLite deletion is not a claim of forensic erasure. Publication correction and deliberate research-history erasure remain separate operations.

No provider credentials, conversations, free-text personal profiles or automatically accepted lessons belong in analyst memory. Human-reviewed lessons and protected evaluation remain separate future work.

## Verification

Verify real LangGraph store use, actor isolation, bounded approved-only retrieval, revision conflicts, expiry, correction/deletion, source changes, restart persistence and memory on/off. Test that historical instructions cannot change tools or publication rules, and that concurrent memory changes cannot bypass the final publication check. Deployed demonstrations must preserve existing notes and model-budget accounting and must not invent a human approval.

This decision supports the brief's L9 memory requirement and the Analyst Desk history/follow-up workflow. It does not claim independent evaluation results or completion of the reviewed-lesson requirement.
