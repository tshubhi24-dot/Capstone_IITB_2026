# Step 13: analyst memory

Analyst memory saves research defaults, shows source coverage and finds relevant approved research. Profiles and historical note bodies stay local. Current SEC evidence and deterministic arithmetic continue to support each new note's claims.

## Use it in the research desk

1. Connect with the existing local analyst credential. **Analyst memory** loads saved preferences, coverage and note-reuse choices.
2. Select companies and fiscal years in **Prepare research**. Choose **Financial table first** or **Research summary first**, then choose how many approved notes new research may use, from zero through three.
3. Click **Save current defaults**. Active defaults load into the research form on the next connection. They expire thirty days after the latest save. The form still enforces the covered catalogue and request limits.
4. Click **Find relevant approved notes** to search with the current question and scope. **Read approved note** opens the exact local original; **Compare current facts** produces a separate checked numeric comparison.
5. Leave **Use saved analyst memory for this request** selected to freeze relevant memory into the new plan. Clear it to skip saved memory. Review **Memory selected for this research** alongside the plan and final note.

Saving defaults is separate from starting research. Memory does not approve a plan, authorize a model call or approve publication. Both existing human review gates remain in place.

## What is saved

| Preference | Accepted value |
|---|---|
| Default companies | One through four distinct tickers from the current catalogue. |
| Default fiscal years | One through three covered years, unique and ascending. |
| Report layout | `table_first` or `summary_first`. |
| Approved-history limit | Integer zero through three; zero omits history from new research memory. |

The API accepts only typed declared fields. Saving replaces the profile. Company/year defaults fill the visible form; the analyst's submitted selection supplies the actual scope.

**Company coverage and source limits** describes twelve companies for FY2023–2025. Records derive from the frozen corpus: financial-input, section, passage and retained-table counts. Original Item boundaries and complete table extraction remain unverified. Counts do not establish economic risk interpretation.

## Approved history and current SEC facts

History search first restricts candidates to the actor and overlapping company/year pairs, then ranks bounded local text with BM25. It inspects at most fifty eligible recent notes and returns at most three references. References contain code-owned titles, approved-note IDs and hashes, scope, source identity and archive status. Historical prose does not enter reasoning-model context.

A note whose source fingerprint differs from the current corpus is marked **Earlier source snapshot**. Its original approved version remains historical context. New SEC claims still require evidence from the active source snapshot.

**Compare current facts** reads up to twelve historical financial rows and finds the current cached revenue/operating-income pair for each company/year. Code verifies current inputs, annual periods, currency and margins. It calculates differences only when historical and current period dates and units match and historical arithmetic is valid. Results cite the exact historical note version and current canonical fact IDs. Missing data or incompatible periods are explicit. This operation makes no generative-model request, refreshes no SEC source and infers no cause for a change.

The comparison view is separate from a new approved research note. Historical approval does not verify an old amount against the current SEC snapshot.

## Correct, delete or exclude memory

- Change selections or layout/history controls and save again to correct preferences. Saving increments the revision and restarts the thirty-day expiry.
- **Delete saved preferences** clears current values. A revision tombstone remains; prior requests, checkpoints, publications and approvals are retained.
- **Forget for future research** excludes a note from future memory selection and numeric memory comparison. Its original publication stays readable. The policy holds at most 256 excluded IDs.
- Expand **Notes excluded from future memory** and choose **Restore to memory** to make a note eligible again.
- Import corrected source data to correct coverage. The new fingerprint receives a separate immutable record.

Changes or expiry can make a pending plan stale. Create a fresh plan when the desk reports that memory changed. The publisher rechecks the current policy inside its transaction; recomputing a snapshot hash cannot bypass exclusions, history limits or revisions.

These controls provide logical deletion of the current profile. Existing research records, SQLite WAL files, filesystem snapshots and backups can retain earlier data. They do not promise forensic erasure or delete approved history. The [memory policy](MEMORY_POLICY.md) defines exact retention.

## Local storage and external boundaries

The actual `langgraph.store.sqlite.SqliteStore` is attached to the compiled workflow. Actor namespaces for preferences, coverage, exclusions and audit share persistent `/runtime/portal.sqlite` with publications. This permits atomic memory validation and approval consumption in one SQLite write transaction. The checkpointer uses `/runtime/checkpoints.sqlite`.

Saved defaults, revisions and historical prose remain local. The live writer receives public SEC evidence and the requested scope; code removes saved memory context from its model plan. Layout and history references are applied locally. Chroma stores public filing vectors; private profiles and approved-note history are not embedded into it.

Credentials and conversation transcripts are not memory fields. Actual profiles, history records and databases stay outside Git. Routes use existing authentication and a fixed local-analyst identity. The deployment does not claim production multi-user isolation or encryption at rest.

## API and implementation files

All routes require local analyst authentication; callers cannot select another actor. Writes carry `expected_revision`. A stale revision returns HTTP 409.

| Route | Purpose |
|---|---|
| `GET /api/memory/preferences` | Inspect active, absent or expired preferences and revision. |
| `PUT /api/memory/preferences` | Replace the profile using `values` and `expected_revision`. |
| `DELETE /api/memory/preferences` | Clear values using `expected_revision`. |
| `GET /api/memory/coverage` | Inspect or remember coverage for the active source fingerprint. |
| `GET /api/memory/note-policy` | Inspect excluded IDs and policy revision. |
| `POST /api/memory/history/search` | Find references using `query`, `tickers`, `years` and `k`. |
| `PUT /api/memory/notes/{note_id}/eligibility` | Set `excluded` with policy `expected_revision`. |
| `GET /api/memory/notes/{note_id}/comparison` | Compare historical values with checked current cached facts. |

| File | What it implements |
|---|---|
| [memory.py](../desk/memory.py) | Actual LangGraph SQLite store, typed profiles, expiry, revisions, coverage, exclusions and transaction-time version checks. |
| [history.py](../desk/history.py) | Bounded ranking, metadata references, frozen snapshots and code-owned history text. |
| [memory_comparison.py](../desk/memory_comparison.py) | Decimal calculations and source-period checks for historical/current figures. |
| [store.py](../desk/store.py) | Actor-filtered approved-note reads and atomic memory/publication validation. |
| [workflow.py](../desk/workflow.py) | Graph store, per-request switch, snapshot binding, stale-memory rejection and local layout. |
| [api.py](../desk/api.py), [memory.js](../web/memory.js), [index.html](../web/index.html) | Authenticated controls, defaults, history inspection, exclusion/restore and comparisons. |
| [test_memory.py](../tests/test_memory.py), [test_memory_history.py](../tests/test_memory_history.py) | Expiry, revision, concurrency, rollback, namespaces, history and publication boundaries. |
| [test_memory_workflow.py](../tests/test_memory_workflow.py), [test_memory_comparison.py](../tests/test_memory_comparison.py) | On/off fixtures, model boundaries, stale approvals and numeric comparisons. |

## Capstone relationship and verification status

This step implements the preferences, coverage and approved-history portions of the [policy](MEMORY_POLICY.md) and the [architecture's durable-data path](ARCHITECTURE_V1.md#6-memory-and-durable-data). Unit and integration fixtures cover correction/deletion, expiry, actor scope, cold-start concurrency, rollback, graph store use and publication revalidation.

Step 13 verification passed:

- All 910 automated tests.
- Nine Docker preparation checks, eleven checks after an actual service restart and eight cleanup checks.
- An authenticated planner history call returning three approved-note references.
- Browser inspection of approved history and a six-row comparison with current cached facts.
- Existing analyst preferences, note-reuse policy, runs and approved notes unchanged across all three Docker verification phases.

Fixture memory-on/off checks remain implementation checks. Independent L9 memory comparison remains pending. [Step 14](REVIEWED_LESSONS.md) implements lesson review and reuse; genuine lesson decisions and the separate E3 lesson experiment remain pending. The [evaluation plan](EVALUATION_PLAN.md) defines remaining final cases, ownership and measurements.
