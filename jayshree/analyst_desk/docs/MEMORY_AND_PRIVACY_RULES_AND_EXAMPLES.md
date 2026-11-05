# Analyst Desk Memory and Privacy Rules and Examples

**Status:** Final project specification v1.0.

These rules define what Analyst Desk may retain, who may use it and what correction or deletion means. Saved analyst context, published research, run checkpoints, public source evidence and reviewed lessons have different purposes. A record being present in a database does not make it approved, private to the current user or safe to reuse.

## A worked analyst journey

All people, note identities and figures below are hypothetical. Assume the financial inputs have been independently verified with compatible company, period, units and filing basis. These are teaching examples, not completed product checks or human review decisions.

**Step 1 Save a preference.** Analyst A explicitly saves "Show financial tables before commentary." Use it for that analyst's permitted research. A preference such as "Always include a peer table" cannot add companies outside the approved plan or force an incompatible comparison. A preference to skip checks must not waive a HOLD.

**Step 2 Prepare a draft.** Company A's FY2023 revenue is USD 100 million and operating income is USD 20 million. Code calculates `20 / 100 x 100 = 20.00%`. A failed draft saying 25.00% must not enter approved-note history. A checkpoint may retain that failed draft for authorised review/resumption, labelled with its actual status; it is not forgotten merely because the research stopped.

**Step 3 Save the approved result.** After the required checks, exact-note approval and confirmed portal write, note N1 reports 20.00%. Its derived history links to that note, source presentation, period and review. Its audience is the one explicitly approved for publication. Saving N1 does not authorise saving unrelated private details or accepting a lesson.

**Step 4 Follow up.** For Company A's FY2024, compatible newly verified revenue is USD 120 million and operating income USD 30 million: `30 / 120 x 100 = 25.00%`. The margin moved from 20.00% to 25.00%, or **+5.00 percentage points**. Identify N1 and both periods' evidence. Do not call this a 5% relative increase or infer its business cause from arithmetic. A same-year source-version difference is a different question; do not automatically label it a restatement or annual growth.

**Step 5 Respect privacy.** Analyst B cannot obtain A's private preferences, research interests, watchlist or run history by typing A's name, guessing a note ID or choosing the same ticker. A note deliberately published to an authorised shared workspace may be read by its permitted audience. Public filings about a company do not make private watchlist membership public.

**Step 6 Turn saved memory off.** A fresh run must not silently load A's optional preferences/prior-note context, including through an indirect history tool, or automatically add derived memory. Existing saved records are not deleted. The run can still use authorised public filings and necessary current-run state. Declare reviewed-playbook use separately; a request needing prior-note history requires an explicit permitted choice rather than silently overriding memory off.

**Step 7 Correct or delete deliberately.** Deleting A's preference removes it from the intended active preference store. An older checkpoint, rebuilt index or restored backup must not silently reactivate it. Deleting N1's derived memory does not itself withdraw N1 from the portal. Show exactly which operation was performed and what remains.

## Record purposes and access

The following are logical categories; they do not prescribe a new database for every row. One long-term store may hold several categories, provided their permissions, purposes and lifecycle remain enforceable.

| Record category | Required save and use boundary |
|---|---|
| Working context and checkpoints | Declare what is persisted to resume/review a run: request, plan, selected messages/tool results, drafts, checks and relevant state. Restrict access to authorised owners/operators. Trim or summarise model context for relevance and size; do not describe that as deleting persisted history. |
| Preferences | Save a deliberate analyst instruction with verified owner, purpose and version. Do not infer personal facts or silently promote a casual statement into a standing preference. Reject or ignore preferences that conflict with source rules, permissions or approval requirements. |
| Coverage and published-note context | Derive from confirmed published records, preserving note/version, publication status, audience, source and review links. Coverage is not automatically public. A per-ticker storage key is not an ownership boundary. |
| Private watchlist and other private context | Keep within its authorised internal scope. Do not attach a list or membership information to prompts, external search/embedding requests, ordinary logs or exports. An approved public-ticker research question does not authorise disclosing the private list. |
| Reviewed lessons and playbooks | Retain proposal origin, applicability, evidence, exact review decision/version and frozen release identity. Keep pending/rejected/retired content separate from usable lessons; restrict access to underlying private development evidence. |
| Public filing cache and retrieval indexes | Preserve public source identity and evidence context. Keep private preferences, questions, note context and protected cases out of the public filings index. Before enabling a private retrieval index, configure its authorised lifecycle and access controls. |

For retained records, preserve the minimum identity, owner/workspace audience, purpose, origin, status, version and timestamps needed for review and the configured lifecycle. Derived records must link to their source. Missing ownership or ambiguous visibility is not permission to show a record to everyone.

Apply access checks to APIs, UI panels, tools, retrieval filters, saved-run loading, exports and maintenance scripts. The application must establish trusted identity/authority; neither a model-provided field nor editable name grants it. Operators' maintenance access must be scoped, recorded and distinct from normal analyst access.

## Reuse evidence and external processing

A previous note is historical research context. Before using its figures in a new calculation, establish their exact company, concept, period, units, operations and filing presentation. Revalidate the new evidence and relevant prior inputs; an earlier approved or parsed number is not automatically a current source fact. Preserve conflicts, later corrections and missing evidence under the financial, filing-version and evidence policies.

An authorised standing preference may shape presentation within the approved plan. It cannot widen company/year coverage, change a metric, require a recommendation, waive checks or authorise a tool. A reviewed lesson may guide a procedure; it cannot replace evidence or change a permission or approval gate.

Retrieve only relevant permitted context. Record the IDs/versions actually used and whether selection was incomplete. A bounded memory panel or top-k lookup must not be described as a complete inventory of stored records or conclusive proof that no prior note exists. Distinguish no eligible note found, history retrieval failed and history not enabled.

Live model processing can send selected context outside the local application. Before such use, explain the data categories and configured destination under the valid run/data-flow authorisation. Include only necessary authorised fields. Permission to save locally is not blanket permission for every external use; do not create repeated approval prompts for actions already covered by a valid authorisation.

Private watchlists, secrets, gold answers and protected dataset files must not enter model prompts, web/search queries or external embedding calls. A controlled evaluation may provide the intended current test question; it must not expose expected answers, unrelated cases or private context. Treat retrieved or saved text demanding disclosure as untrusted instructions and enforce the boundary in code. A private research interest can remain sensitive even when every underlying SEC document is public.

Minimise/redact sensitive content in traces, exception messages, export files, screenshots and recording/demo fixtures. Explain any external telemetry/logging that is enabled. Do not infer provider retention, training exclusion, encryption or guaranteed deletion from using a gateway, a local database or a Git ignore rule. Those claims need separately verified arrangements and configuration.

## Memory controls and recovery

Declare saved analyst memory and reviewed-playbook settings separately before running. In saved-memory-off mode, disable optional preference/history retrieval and automatic derived-memory writes, including alternate tools that would reload that history. Public source search and required current-run checkpoints remain distinct. Do not claim no storage or no external processing from the toggle alone.

Turning memory off does not erase a prior run, remove published notes or revoke their approval. A new run and resuming an existing checkpoint are different operations. On resume/replan, check current permissions, memory settings, record versions and deletion/withdrawal status before reusing any saved snapshot. Do not revive obsolete context from the checkpoint merely because it was valid when first loaded.

Preserve the original historical record of the run under the configured privacy and retention rules. If reconciliation changes the proposed plan/note or its material evidence/review basis, apply the required fresh checks and approval; do not silently rewrite an earlier decision.

After a confirmed portal write, create/reconcile derived history using the existing saved-note identity. If memory updating fails, show **Published with memory sync pending/failed**. Repair the derived update independently; do not publish a duplicate note. If portal outcome is unknown, reconcile it before declaring publication or inserting approved history.

History-tool failure must not become "there was no earlier note." If optional context is unavailable, explain the missing contribution; continue only where the approved question can be answered honestly without it. Otherwise seek the appropriate scope/settings decision or hold the affected comparison.

## Correction deletion retention and restoration

**Preferences.** Let an authorised owner inspect, correct and delete the declared records. Show the effective version and apply it to future eligible use. A correction to a preference must not rewrite a published note or its approval.

**Published research.** Follow the Acceptance and Publication Policy: corrections use linked new versions, relevant checks and fresh exact approval. Preserve superseded/withdrawn status in history, retrieval and follow-up results. Withdrawing a note is different from deleting all underlying records and is not permission to present it as current approved research.

**Deleting derived memory.** State the selected record/category, owner/workspace and stores affected. Reconcile dependent coverage pointers, cached summaries and private retrieval entries. Keep an appropriately minimal deletion/suppression record where needed to prevent backfill or restoration from repopulating active memory; it must not retain the deleted sensitive content merely to log its deletion.

**Deleting runs or broader data.** Define checkpoint/run, approved portal, private memory, lesson, index, log, export and backup scope separately. A delete-memory action does not automatically mean all those stores were erased. An authorised wider deletion request needs an inventory and an accurate result for each affected category: removed, retained for a documented permitted purpose, pending, or not controlled by this operation. Never promise full erasure from a single UI deletion or database-file removal.

**Backfill and restore.** Rebuilding note memory must respect current ownership, approved audience, withdrawal and deletion/suppression decisions. Restoration must apply the current privacy/lifecycle decisions before making records active. If a copy cannot yet be removed, restrict its use and report its status under the configured lifecycle rules. Already loaded state must be reconciled; do not claim to retract data already sent to a model or external recipient.

**Retention.** Save only what is required for a declared research, review, resume or operational purpose. Before storing private analyst data, configure a retention period or deletion trigger for each category, maintenance permissions and backup/restore handling. Do not enable private storage with unspecified lifecycle controls. This policy does not impose a universal lifetime or guarantee third-party erasure. Apply the configured limits and explain remaining records accurately; a privacy request must not be answered by deleting an active SQLite file and assuming every copy is gone.

For example, Analyst A deletes a saved presentation preference, then resumes an old run containing its earlier snapshot. The application must reconcile the deletion before using that preference again. If it only removed the current preference entry, report that scope rather than "everything has been forgotten." Similarly, deleting a derived note entry must not be undone silently by rebuilding from unchanged portal notes.

## Reviewed lessons and evaluation integrity

A lesson proposal must cite a genuine development failure, critic rejection or analyst correction and preserve the supporting evidence. Record the proposed procedure, applicability, counterexamples, expected benefit and possible harm. A successful case with no useful correction need not generate a lesson. A model proposal is pending until a human reviews its exact version; ordinary note approval is a different decision.

Only accepted, relevant versions may enter a usable playbook. Rejected or retired lessons must not remain active through an old prompt snapshot. Record the actual human decision, reason, reviewer and version. Remove unnecessary company/private details and inspect for copied instructions or protected answers before acceptance; a prompt requesting generalisation is not proof of anonymisation.

**Illustrative rejection.** A proposed rule says: "If earlier search returns no result, mark the later disclosure as a newly added risk." It should be rejected because failed retrieval does not establish absence. This is a teaching example, not the genuine rejected lesson or actual human decision required for the project.

**Illustrative useful proposal.** A development correction shows that a renamed heading caused a false removal label. A candidate lesson asks the researcher to inspect renamed/relocated topics and cross-references before assigning removal. Review whether it adds a useful procedure beyond the existing policy, where it applies and when it could mislead. Do not claim it was accepted or improved unseen performance without actual evidence.

Freeze an identifiable reviewed playbook version before held-out evaluation and record which lessons were retrieved. A mutable frozen flag alone does not establish reproducibility; changes require a distinct version and evaluation decision. Keep protected dataset files, gold answers, human labels and other held-out cases/results outside application-readable stores, embeddings, prompts and tools. R5 may supply the intended current evaluation question through a controlled runner. Segregate its authorised run state/results so they cannot be recalled by later cases or converted into development lessons. If a case informs tuning, treat it as development rather than continuing to call it unseen.

Memory-on/off and lesson-before/after comparisons answer different questions. Keep research questions, public source snapshot, code, models, tools, budgets and the other context settings comparable; record intended differences. Evaluate correctness, relevance, failures, harmful effects, cost and latency, including lesson-generation cost for the learning comparison. R5 owns protected evaluation; neither a functioning toggle nor this specification demonstrates benefit.

## Development examples and implementation roles

The following are required development expectations, not completed tests, genuine lesson decisions or protected evaluation answers.

| Situation | Expected behaviour |
|---|---|
| Preference requests an out-of-scope peer or skipping checks | Do not widen the plan or waive checks. Explain the conflict and use the appropriate approved scope. |
| A failed draft reports 25.00% instead of verified 20.00% | Keep it out of approved history; any retained checkpoint remains labelled failed/draft. |
| Compatible verified margins change from 20.00% to 25.00% | Compute +5.00 percentage points, identify the prior note and cite/recheck the evidence. Do not infer the cause. |
| Another analyst types the owner's name or guesses an ID | Refuse unauthorised private access; check trusted identity and audience at the data boundary. |
| Saved memory is off, but a history tool could retrieve a prior note | Do not silently load the optional history. Explain a needed settings/scope choice; public filings remain available. |
| A deleted preference exists in a checkpoint or restored copy | Reconcile current deletion and permissions before reuse; report pending/retained copies accurately. |
| A retrieved paragraph asks for the private watchlist | Treat it as untrusted instructions; block disclosure to models, tools, logs and exports. |
| Portal save succeeds while derived-memory update fails | Retain confirmed publication and repair the separate sync operation using the same note identity. |

| Role | Required responsibility |
|---|---|
| R1 Domain and product | Review useful memory, privacy expectations, comparison meaning, correction/deletion messages and lesson applicability. Specify domain acceptance and record versioned decisions. |
| R2 Knowledge and memory | Own the memory engineering policy, record/provenance inventory, source/index separation, ownership metadata, retention and correction/deletion/backfill design. |
| R3 Agents and orchestration | Implement scoped context selection, save triggers, separate settings, resume reconciliation, bounded context and reviewed-lesson/frozen-version workflows. |
| R4 Tools control and security | Enforce verified identity, permissions, disclosure limits and deletion boundaries across tools/APIs/exports/maintenance; prevent instruction-based bypass. |
| R5 Evaluation and red team | Independently verify isolation, off modes, lifecycle/recovery, watchlist protection, genuine lesson decisions, evaluation independence and measured benefit/harm. |
| R6 Deployment and operations | Display truthful controls and outcomes; protect persistent stores and operational artifacts; implement configured maintenance, backup/restore, recovery and evidence capture. |

Before enabling private memory, configure verified identities, private/shared audiences, data-flow permissions, per-category retention and backup rules, deletion/suppression behaviour and frozen-version ownership. Record the effective policy/configuration version and actual access, lifecycle and review decisions. R5 must verify the applicable boundaries on the deployed version; publishing these specifications does not establish enforcement.
