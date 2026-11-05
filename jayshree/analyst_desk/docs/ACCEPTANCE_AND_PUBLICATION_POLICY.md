# Analyst Desk Acceptance and Publication Policy

**Status:** Final project specification v1.0.

This policy defines when a research note is acceptable, who must approve it and how the application confirms that it was saved. A note must satisfy its financial, evidence and scope requirements before final approval. An approved note becomes Published only when its matching portal record is confirmed.

## Simple walkthrough

Consider a hypothetical Company A with revenue of USD 100 million and operating income of USD 20 million for the same verified annual period, operations and filing basis. These are teaching examples, not company results or completed application checks.

**Start with the plan.** The analyst asks: "Calculate Company A's operating margin and compare its risk disclosures with the previous year." Approval of that plan permits the specified research. It does not approve the result for saving to the research library.

**Step 1 Correct the number.** A draft reports operating margin of 25.00%. Code calculates `20 / 100 x 100 = 20.00%`. The known wrong result puts the note on HOLD. Clicking Approve cannot make 25.00% acceptable.

**Step 2 Complete the evidence review.** The number is corrected to 20.00%, but two risk claims remain unreviewed. The note Needs Review. Every outstanding claim must be supported, revised, removed or replaced by an accurately reviewed limitation before the note can be ready.

**Step 3 Prepare the exact version.** All required checks and evidence reviews are complete, scope is accounted for and no blocking finding remains. The note is Ready for Approval. It has not yet been approved or published.

**Step 4 Record the human decision.** An authorised analyst reviews the exact note and explicitly approves that version. It becomes Approved. A later edit from 20.00% to 21.00% creates a changed version: correct/recheck it and obtain fresh approval before writing it to the portal.

**Step 5 Confirm publication.** The portal stores the approved version and returns an identifiable record matching it. Only then show Published. If the response times out, show Publication Outcome Unknown and reconcile the original operation before declaring success or creating another note.

This policy governs saving a research note to the research portal/library. Approval to prepare research is separate from approval to publish its exact result.

## Readiness and outcome states

Readiness, approval and persistence are related but different decisions. Keep the reason, outstanding work and next permitted action visible. Implement the states below and verify their transitions against this specification.

| State | Meaning and permitted next action |
|---|---|
| Draft | Content exists, but its inventory/checks/review are not complete. Continue research, checks or editing; no publication. |
| Needs Review | Specific evidence or semantic review remains. A named authorised reviewer may complete that work under this policy; ordinary final approval does not substitute for it. |
| HOLD | A known blocking error, unresolved evidence conflict, missing required source or unavailable review route prevents acceptance. Resolve it, narrow the answer legitimately or stop; no approval bypass. |
| Ready for Approval | Required checks and claim review are complete for the exact note, scope is accounted for and no blocking finding remains. Present it for the explicit final human decision. |
| Approved | A valid authorised human decision is bound to the exact eligible version and its evidence/review context. Publication may proceed while that approval and eligibility remain valid. |
| Published | The portal's durable record and receipt are confirmed to match the approved operation/version. A preview, approval token or model statement alone does not establish this state. |
| Rejected | The reviewer declined the version. Do not publish it. Any deliberate reopening or revised draft must retain that decision and undergo the applicable checks and new approval. |
| Cancelled | Further work was stopped. A retained draft/checkpoint does not become approved or published by being stored. Cancellation cannot undo an already committed write; reconcile any uncertain publication outcome separately. |

Where Needs Review and HOLD conditions coexist, show HOLD and list the review work too. Ready for Approval means only the final sign-off remains; it is not an automatic approval.

Track the publication operation separately as pending, confirmed, failed or outcome unknown. An Approved note can have an unknown write outcome. A confirmed portal write with a failed memory update remains a published record with a visible memory-sync failure, rather than an assumed failed write.

## Acceptance conditions and blockers

Apply the companion financial, filing-version and evidence/risk policies to the entire note, including title, summary, tables, citations and conclusions. The claim/quantity inventory must account for every substantive assertion and requested company, period and metric.

| Acceptance condition | Blocking example and required response |
|---|---|
| Financial quantities and calculations pass | A value is wrong, unverified, associated with another company/period, or based on incompatible units/versions. Correct, remove or mark the result unavailable with a supported reason; recheck. |
| Research claims have adequate support | A cause, event or risk-change label lacks suitable evidence or contradicts it. Correct/narrow the claim, obtain the evidence or withhold the conclusion. A citation's existence alone is insufficient. |
| Required review is complete | Claims are skipped, verdicts are missing/invalid, or the critic is unavailable without an accepted completion route. Record incomplete review; do not count it as a pass. |
| Requested coverage is accounted for | A requested company, year or comparison disappears. Display what is available/missing; a material change to the research scope requires revised-plan approval. |
| Scope and content rules pass | An output contains prohibited investment recommendations, promises of returns, private-data disclosure or instructions copied from retrieved evidence. Remove/refuse the prohibited content and apply the relevant controls. |
| Versions and authorisation remain valid | The note, source/review context or applicable policy changed, the approval was revoked, or the reviewer/action is not authorised. Recheck and obtain the required valid decision before publication. |

No known false or unsupported assertion may be accepted because most other checks passed. A verified-number share of 98% is a monitoring alert threshold, not permission to publish the remaining known errors. For example, 490 verified numbers out of 500 gives 98.00%; ten unresolved numbers still require action.

Do not turn a tool error into zero, missing source text into absence, or an unchecked financial value into a reviewed fact. An unexplained contradiction remains visible until resolved or the affected conclusion is withheld.

## Limited answers and human evidence review

### When an unavailable result can be valid

A transparent limited answer can be ready when every assertion it does make is supported and reviewed, requested coverage is explicitly accounted for, and no misleading implication remains. Publishing such an answer requires the analyst's explicit acceptance of those visible limitations.

For example, the note may report a verified margin and state: "Comparable earlier Item 1A coverage is unavailable, so we cannot determine whether this risk was added or removed." That reviewed limitation is different from leaving an asserted risk conclusion unreviewed.

**Worked risk example.** A draft states: "Cybersecurity risk was newly added this year." Finding cybersecurity in the current filing does not establish that it was absent from the earlier filing. The reviewer needs sufficient comparable coverage of both years, including relevant relocated content and cross-references. If review is still pending, show Needs Review. If essential evidence or a permitted review route is unavailable, show HOLD for that unresolved assertion.

When supported by reviewed current evidence, the note may instead say: "The current filing discloses cybersecurity risk. Earlier-year coverage is insufficient to determine whether this disclosure was newly added." Keep the requested comparison and limitation visible. This can be an eligible limited answer only after the applicable review and explicit limitation acceptance; a material narrowing of the plan still needs revised-plan approval.

Keep the original question and missing comparison identifiable. Do not silently omit it to improve completion counts. If the plan's intended task, companies, periods, metric basis or source scope is materially narrowed or changed, present the revised plan for approval before continuing under it.

### Completing an unavailable semantic review

An authorised analyst/domain reviewer may complete an unavailable semantic review by inspecting each outstanding claim against its actual evidence and relevant context. Configure verified reviewer identities and permitted review actions before enabling this route. Record the claim, evidence, decision, rationale, reviewer, time and exact note version. A generic Approve click is not that review record.

Preserve the automated critic's failed/incomplete status and costs. Human evidence review can resolve the live note's support questions; it does not retroactively turn a failed automated critic into a passing run or complete a required evaluation experiment. All mandatory numerical/source checks, adequate evidence coverage and other blockers still apply. If neither automated review nor an authorised recorded human review can complete the requirement, keep HOLD.

A reviewer may perform both evidence review and final approval when authorised; this policy does not impose a second-person quota. Record the two distinct decisions. Do not treat seniority, a confident model answer or urgency as evidence that an unresolved assertion is correct.

### Bounded repair and stopping

Keep the automated critic/writer loop at no more than two automated revisions and within the applicable run authorisations. Exhaustion does not confer acceptance. Stop on unresolved blockers, explain them and permit only an authorised correction/review/resume path. Do not reset counters or erase prior failures to make the next attempt appear compliant.

## Exact version approval and invalidation

Plan approval authorises the specified research scope and applicable run conditions. Final note approval authorises the exact eligible note to be written to the intended research portal. One decision does not replace the other.

Before final approval, show the full title/body, companies, citations, limitations, check results, semantic review completion and any human completion route used. Provide access to the approved plan, source versions/snapshot and current policy basis. A summary alone is insufficient when it hides content being approved.

Record an explicit Approve, Edit, Reject or Cancel action from an authorised reviewer for the relevant run and version. Empty, unknown, stale or mismatched actions must not become implicit approval. Edit returns the changed version to checks/review; it does not publish in the same action.

Bind approval to the exact note content and company list, the intended operation/destination, approved plan, source evidence/snapshot, policy version and review/check records. Use a consistent declared company format before preview and binding. The reviewer identity and decision must be verified through the application's trust boundary, rather than accepted solely because a model or request field supplies an approver name.

The publisher and portal must validate both the approval and current eligibility at write time. A valid content signature alone does not prove completed evidence review or passing checks. Models, retrieved text and tool outputs cannot supply the human decision or change what an existing approval covers.

| Change after approval | Required response |
|---|---|
| Title, body, company coverage or citation content changes | Invalidate approval for the changed version; perform relevant checks and obtain exact-version approval again. |
| A source version, material evidence, review result or effective policy changes | Reassess affected claims and overall eligibility, preserve the earlier record and obtain fresh approval for the changed context. |
| A wrong number is corrected | Recalculate dependent results, rebuild the inventory, review affected claims and obtain approval for the corrected note. |
| Approval is revoked before the write | Refuse publication under it; record the revocation and applicable next action. |
| UI reload or restart with the same approved version/context | Recover and validate the existing decision/operation. Do not create a new approval requirement or duplicate publication solely because the page reloaded. |

Reuse earlier check/review results only where their exact content, inputs, context and policy applicability are demonstrably unchanged. Recheck edited content and dependencies, rebuild full-note coverage and re-evaluate eligibility. An unchanged body does not preserve approval when its material source/review basis changed.

## Publication confirmation retries and memory

Send only the eligible approved payload through the permitted publisher/portal boundary. Give each publication operation a stable identity tied to its run, approved version and destination. Enforce one durable result for a retry of that operation, including concurrent attempts; do not rely on the model to avoid duplicates.

Confirm the saved note identifier, approved content/version and destination from the portal's durable record/receipt. Do not announce Published before confirmation. An explicit refusal or invalid approval leaves the note unpublished by that attempt; it must not be retried with altered content under the old decision.

If a timeout or lost response leaves the outcome unknown, reconcile the original operation and approved version against the portal. A matching stored record can resolve the uncertainty. A duplicate response must be linked to the appropriate record/context before treating it as confirmation. Do not change the title or body merely to bypass duplicate detection.

For example, the save request times out after the portal may have stored the approved 20.00% margin note. Show Publication Outcome Unknown, find the original operation's matching saved record and confirm that result. Do not create another copy merely because the response was lost.

Retrying an identical operation is permitted only through versioned retry and reconciliation controls while approval and eligibility remain valid. It does not authorise new research, new model calls or a changed payload. Retain failures and attempts in the operation record; do not claim a successful write solely because no error is displayed.

Only confirmed published notes should enter approved-note history and derived follow-up memory. Draft/checkpoint storage for resuming work must remain labelled with its actual status. If the portal write succeeds but memory synchronisation fails, report both facts and retry/reconcile that derived update separately; do not create a second portal note to repair memory.

For the same example, if the portal returns a confirmed saved-note record but its memory update fails, display Published with a separate memory-sync error. Repair the memory update using that saved-note identity. Do not display an unqualified publication failure or republish the note.

Published history provides prior research context. It does not automatically establish current source facts; revalidate relevant evidence and any superseded/withdrawn status for a new question.

## Corrections supersession and withdrawal

Preserve the identity, decision and status of earlier versions in accordance with the configured privacy and retention rules. A cache refresh or correction must not silently rewrite an earlier approval. This policy does not set a new permanent-retention or deletion rule.

For a published error, create a linked corrected/superseding version, perform the relevant checks and obtain fresh exact-version approval. Mark the earlier note's status visibly and propagate that status to retrieval and follow-up memory. A later source correction may make a prior conclusion unsuitable for current use even if the stored original note remains identifiable as historical research.

An authorised withdrawal changes the note's availability/status under the configured lifecycle rules. Record its reason and connection to any replacement. Do not describe withdrawal as deletion from every database, checkpoint, index or backup unless that action is actually performed and verified under the memory/privacy policy.

## Development acceptance examples

The examples below define required behaviour. They are not completed tests or protected evaluation results.

| Situation | Expected result |
|---|---|
| All financial values pass; two asserted risk claims are unreviewed | Needs Review, or HOLD if no permitted review route exists; no completed-note pass. |
| The margin is known wrong but the analyst clicks Approve | Refuse publication eligibility until the error is corrected and the revised note is approved. |
| Missing data is displayed as N/A with a reviewed reason and no unsupported conclusion | May become ready after required review and explicit scope/limitation acceptance; no silent omission. |
| The final review action is empty or unrecognised | No approval is issued. Show the unresolved decision. |
| Approved text is edited, or its evidence/review basis materially changes | Relevant fresh checks/review and new approval are required. |
| Two requests retry the same approved publication operation | One durable portal result; reconcile and return/identify that record. |
| Portal write times out after it may have committed | Publication Outcome Unknown until the original operation is reconciled. |
| Portal saves successfully but memory update fails | Keep the published receipt/status, show memory sync pending/failed and reconcile that update separately. |

## Implementation responsibilities

| Role | Required responsibility |
|---|---|
| R1 Domain and product | Review acceptance criteria, valid limited answers, blockers, reviewer expectations, correction/withdrawal meaning and examples. |
| R2 Knowledge and memory | Preserve source/version context, missing-data reasons and note lineage; keep corrected/withdrawn status consistent in retrieval and follow-up memory. |
| R3 Agents and orchestration | Implement the state transitions, bounded repair, explicit decisions, review completion, invalidation and publication/memory reconciliation flow. |
| R4 Tools control and security | Verify reviewer/action authority, bind approval/context, enforce eligibility at the write boundary, reject stale decisions and make retries/revocation safe. |
| R5 Evaluation and red team | Independently check numerical/semantic blockers, invalid/stale actions, edits, concurrent retries, uncertain writes and legitimate limited-answer acceptance. |
| R6 Deployment and operations | Display truthful states, outstanding work, sources/checks and durable receipts; preserve recovery and trace visibility across failures/restarts. |

Before enabling publication, configure verified reviewer identities and action permissions, the approval/context contract, claim-level human review records, correction/withdrawal controls and retry/reconciliation responsibilities. Record the effective policy/configuration version and actual decisions. Verify enforcement at the publisher and portal boundaries; a published specification alone does not establish these controls.
