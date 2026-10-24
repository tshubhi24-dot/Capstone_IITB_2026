# Analyst Desk: proposed memory policy

**Current build proposal | 24 October 2026**

This policy defines the intended local implementation. Persistence, access controls, deletion and isolation must be demonstrated before they are reported as working. The initial deployment serves one local analyst; production multi-user privacy is outside this version.

## What to retain

**Current research:** a SQLite-backed LangGraph checkpointer stores the question, approved scope, plan/version, evidence identifiers, completed steps, remaining budget, draft hash and pending human decision. Resume revalidates limits and approval expiry. Bounded context sent to a model contains relevant evidence and summaries; a checkpoint is not unlimited model memory.

**Long-term context:** a namespaced LangGraph store saves explicit formatting preferences, the coverage list and human-reviewed lessons. Retrieve only relevant, bounded records. Private watchlists remain system-side: they must never enter model prompts, external queries or outbound traces. Store no provider keys, credentials or unrelated personal details.

**Approved research:** the portal stores the exact approved note version, citations, calculation references and approval/publication receipt. Drafts become publication history only after exact-version approval. Corrections create a visibly superseding version and require renewed approval.

**Lessons:** proposals from actual development failures remain pending. Record applicability, evidence, reviewer and acceptance/rejection reason. Only relevant accepted lessons from a selected frozen version may influence research. Retain rejected proposals for evaluation traceability.

## Access and storage

Use persistent Docker volumes for the checkpoint, store and portal databases. Restrict host file access to the local account and give services only their required mounts and authenticated tools. Processes sharing a SQLite file do not gain separate operating-system isolation. The proposed setup does not claim encryption at rest or production tenancy.

## Retention, correction and deletion

Proposed development defaults: preferences expire after 30 days; completed unapproved run state and scrubbed operational logs expire after 30 days. Approved publications, review receipts and frozen experiment snapshots remain until deliberate deletion under a documented owner decision. These are defaults for team review, not implemented guarantees.

Provide inspection and correction of preferences, explicit preference deletion and a separately explained research-history deletion operation. Deleting a preference must not silently delete publications or audit records. Define backup deletion and any retained tombstone before claiming complete erasure. Credentials follow separate secret-management procedures.

## Evaluation boundary and required evidence

Keep private final questions, gold and labels evaluator-owned. An individual submitted question/output may enter its isolated evaluation run records, under evaluator-controlled retention; it must not become shared memory, a lesson or a published note. Reset state between treatments according to the frozen protocol.

Demonstrate restart/resume, preference inspection/correction/deletion, scoped history retrieval, watchlist non-disclosure, human lesson review, frozen lessons and memory-on/off comparisons. Record failures and remaining gaps in the [evaluation plan](EVALUATION_PLAN.md); implementation checks are still pending.
