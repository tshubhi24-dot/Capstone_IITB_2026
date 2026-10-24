# Analyst Desk: memory policy

Analyst memory retains explicit research defaults, source-derived coverage and bounded references to approved notes. It serves one authenticated local analyst. Docker restart and persistence verification passed for this step; the implemented controls and storage limits are described below.

## What is retained

| Record | Implemented contents and use |
|---|---|
| Current research | SQLite-backed LangGraph checkpoints retain the request, reviewed scope, plan, evidence IDs, progress, usage, draft version and pending human decision. New plans also freeze the selected memory version. |
| Analyst preferences | Up to four covered default companies, three unique ascending covered fiscal years, `table_first` or `summary_first` report layout, and a history limit from zero through three. Arbitrary profile text and instructions are rejected. |
| Company coverage | Immutable metadata keyed by the source fingerprint: company/year rows, financial-input counts, section/passage counts, retained-table counts and source limitations, derived from the supplied corpus. |
| Approved history | The portal retains the exact approved note, source references, calculations, approval record and publication receipt. Memory selects at most three relevant references by actor, company/year scope and local lexical relevance. |
| Note-reuse policy | At most 256 excluded note IDs per actor, with a monotonic revision. Exclusion removes a note from future memory selection; its approved publication remains in the library. |
| Memory audit | Actions, revisions and timestamps. Audit entries do not copy prior preference values or historical note bodies. |

The profile, default selections and historical note prose remain local. When the analyst submits research, the companies and years explicitly selected in the form become the requested scope. The profile and saved default lists are not forwarded to reasoning models. Prior note references remain separate from current SEC evidence; saved history does not establish the correctness of a new financial claim.

Conversation transcripts, unrelated personal profiles, provider keys and credentials are not memory fields. Actual profiles, note records and runtime databases remain outside Git. Chroma continues to hold public filing vectors; private preferences and note history are not embedded into it.

## Storage and access

The actual `langgraph.store.sqlite.SqliteStore` supplies the namespaced memory store attached to the compiled graph. Its `store` tables share `/runtime/portal.sqlite` with portal runs, notes and approvals. Namespaces separate each actor's preferences, coverage, reuse policy and memory audit. The graph checkpointer remains in `/runtime/checkpoints.sqlite`.

Sharing the portal database lets the publisher validate memory revisions, preference expiry, layout, history limits, exclusions and approved-note references inside the same `BEGIN IMMEDIATE` transaction that consumes the exact-version publication approval. A transaction-aware store adapter preserves outer transactions and rolls back failed writes. Concurrent saves require the expected revision; stale edits return a conflict.

The authenticated API fixes the actor to the configured local analyst. Namespaces provide logical separation; processes sharing the database do not gain operating-system isolation from one another. The deployment does not claim production tenancy or encryption at rest. Existing scoped service credentials and the private runtime volume remain the storage boundary.

## Expiry, correction and deletion

| Action or record | Exact retention behavior |
|---|---|
| Preference expiry | Values become inactive 30 days after the latest save. Reads report `expired` and return no active values. This is logical expiry, not a purge of profiles, audits, SQLite pages or backups. |
| Preference correction | Saving replaces the allowlisted profile, increments its revision and starts a new 30-day lifetime. The caller supplies the current revision. |
| Delete saved preferences | Clears current values and expiry. A minimal revision tombstone remains to prevent an old save or snapshot becoming valid again. Prior requests, checkpoints, publications and audit records remain. |
| Forget an approved note for future research | Adds its ID to the bounded reuse-exclusion policy. The original note, approval receipt and earlier run remain. Eligibility can be restored later. |
| Coverage correction | Import corrected sources and create coverage under the new fingerprint. An older snapshot's coverage remains immutable. |
| Published-note correction | This feature does not overwrite approved publications. A new research version requires code checks, plan review and separate exact-note approval. |
| Runs, publications, logs and backups | This step adds no automatic 30-day deletion job for these records. Existing notes, runs/checkpoints, approval records and backups retain their existing local retention arrangements. |

Preference changes, deletion, expiry or reuse-policy changes invalidate pending research that used an earlier memory version. Create a fresh plan; a silent memory refresh cannot change a reviewed draft. Published notes preserve their exact approved content.

SQLite secure deletion is enabled on the memory connection, but it is not a complete-erasure guarantee. Earlier data may remain in WAL files, existing research records, filesystem snapshots or backups. Profile deletion and note exclusion do not remove those copies. Full research-history or backup erasure is a separate owner-controlled operation outside this step.

## Human review and evaluation boundary

Memory cannot approve a plan, authorize spending, bypass numeric/source verification or publish a note. Plans display frozen memory selections; final publication still requires separate approval for the exact note. Memory is revalidated before continuation and inside the publication transaction.

The per-request memory switch skips saved preference/history selection when off. Unit and integration fixtures check on/off behavior, stale revisions, actor isolation, expiry, deletion, restart and atomic publication. These checks are not the independent capstone E3 experiment or evidence of improved research quality.

Verification completed with 910 passing automated tests, nine Docker preparation checks, eleven checks after an actual service restart and eight cleanup checks. An authenticated planner history request returned three approved-note references. Browser inspection of history and a six-row comparison against current facts also passed. Existing analyst preferences, note-reuse policy, runs and approved notes remained unchanged across preparation, restart inspection and cleanup.

Human-reviewed lessons, frozen accepted-lesson versions and learning from development failures remain future work. Protected final cases, gold and labels remain evaluator-owned and must not become shared memory, lessons or published history. The production UI is not an independent evaluation runner; the [evaluation plan](EVALUATION_PLAN.md) defines the remaining separation and experiments.

See the [analyst memory guide](ANALYST_MEMORY.md) for UI controls, API routes and implementation files.
