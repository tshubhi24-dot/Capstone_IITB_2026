# Analyst Desk Frontend Messages and Trigger Conditions

**Status:** Final project specification v1.0.

The catalogue specifies 28 banners in seven groups. Each banner is a short status message, accompanied by the necessary evidence, limitation or action detail. Use its ID to connect the displayed copy, backend trigger and verification case.

## Ownership and display contract

- **R6 owns every banner, expanded explanation, accessible status, button and layout.** The backend owners listed for each message supply and enforce the state; a frontend label cannot create that state.
- **R1 reviews domain meaning and wording. R5 independently verifies the agreed behaviour.** R2 supplies source/memory metadata, R3 orchestrates scope and recovery, and R4 enforces permissions, compatibility, review and write boundaries.
- Show status only from trusted, typed backend results for the authorised viewer. A language-model statement, tool success, approval token or signature alone does not prove complete research review or publication.
- Buttons are conditional on current server-side permissions, scope, version and authorisation. Their presence must not bypass a gate. A retry or resume that can make model calls must stay within the valid run authorisation; a materially changed task needs the appropriate new decision.
- Populate placeholders only from validated, authorised context. Escape displayed text and keep credentials, private watchlists, other users' identifiers and raw sensitive diagnostics out of banners and exports. Treat retrieved text as evidence rather than UI or operating instructions.
- Banner templates use at most 140 characters and short trigger labels at most 60. Runtime substitutions still require responsive layout and accessibility checks; do not truncate a material qualification or use a tooltip as the only disclosure.
- Display essential expanded information beside the relevant result or control. In particular, a memory-off banner alone is insufficient without its storage/deletion explanation, and a Published banner must show any required memory-sync failure separately.
- A blocker takes precedence over a ready state. Numerical checking, semantic review, source coverage, approval and persistence are separate facts. A justified limited answer may become eligible after its retained claims, scope and limitations receive the required review; not every unavailable value requires a permanent whole-note HOLD.
- Source links below identify the governing project specifications on R1_role. Implement each message's trigger and permitted action; displaying the text alone does not establish compliance. Runtime messages R01/R02 apply the same control rules without prescribing a particular provider integration.

## How to read the catalogue

The table provides exact banner copy and a short trigger. The detailed trigger and permitted action below each table are part of the contract. For example, F01 is an informative warning for a valid reported-fiscal-year comparison; it must not be repurposed as a reason to reject all different-year-end comparisons.

## 1. Scope and metric choice

| ID | Exact banner | Show when | Backend owners |
|---|---|---|---|
| S01 | Annual evidence available: {years}. Select explicit fiscal years. | Verified annual coverage is available. | R2/R3/R4 |
| S02 | {selection} is outside supported coverage. Choose a supported selection or revise the request. | Requested company or year is unsupported. | R2/R3/R4 |
| S03 | Research scope changed. Review and approve the revised plan before continuing. | Material research scope or basis changed. | R3/R4 |
| B01 | Which margin do you want? Operating and pre-tax margins use different inputs. | Requested margin is ambiguous. | R2/R3/R4 |

### S01

**Trigger:** The authoritative coverage catalogue identifies the annual evidence window for this workspace. Populate years from that catalogue, not a language-model guess or the present calendar year.

**Permitted action:** Show before planning; offer explicit covered periods and clarify latest or relative-year requests.

**Expanded explanation and limits:** This is a historical evidence window. Latest or last three years must not silently default to it. Configured company-year names alone do not establish complete source or metric availability.

**Policy:** [SUPPORTED_RESEARCH_SCOPE.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/SUPPORTED_RESEARCH_SCOPE.md).

### S02

**Trigger:** Scope validation finds an unsupported requested public company or period, including a mixed supported/unsupported request. Do not derive unsupported status from a source-tool outage.

**Permitted action:** Identify all affected requested rows and offer supported choices; never silently discard the unsupported portion.

**Expanded explanation and limits:** This message describes the supported project evidence, not whether the issuer exists or SEC evidence could be obtained elsewhere. New source coverage requires an explicit scope decision.

**Policy:** [SUPPORTED_RESEARCH_SCOPE.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/SUPPORTED_RESEARCH_SCOPE.md).

### S03

**Trigger:** The proposed or executed task would materially change companies, periods, metric definition, currency basis, source presentation, snapshot/cutoff or another approved scope boundary.

**Permitted action:** Present the changed plan and its implications. Continue only after a valid revised-plan decision; note approval does not substitute.

**Expanded explanation and limits:** Keep the original plan and prior charges/attempts identifiable. The revised plan is a separate authorisation, not approval of the eventual note.

**Policy:** [ACCEPTANCE_AND_PUBLICATION_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/ACCEPTANCE_AND_PUBLICATION_POLICY.md).

### B01

**Trigger:** A bank or mixed-company margin request does not specify a metric clearly enough to select compatible inputs. Availability of a configured pre-tax ratio is not consent to use it.

**Permitted action:** Ask for the metric before plan approval; offer only choices whose metric support and required input availability are accurately described.

**Expanded explanation and limits:** Operating margin uses operating income and compatible revenue. The bank pre-tax task uses reviewed pre-tax income and corresponding total net revenue after interest expense. These are distinct measures.

**Policy:** [BANK_METRICS_AND_COMPARISON_RULES.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/BANK_METRICS_AND_COMPARISON_RULES.md).

## 2. Comparison and period boundaries

| ID | Exact banner | Show when | Backend owners |
|---|---|---|---|
| B02 | Operating-margin comparison unavailable for the selected bank. | Bank operating-income input is unavailable. | R2/R3/R4 |
| B03 | Different margin definitions: a common ranking, gap or average is unavailable. | Requested ranking or gap mixes margin definitions. | R3/R4 |
| F01 | These figures cover different annual reporting windows. | Valid own-FY comparison has different annual windows. | R2/R3/R4 |
| F03 | Requested period unavailable for {company}. Review the evidence limit or a revised plan. | Selected evidence lacks the requested aligned period. | R2/R3/R4 |

### B02

**Trigger:** The selected bank lacks the reviewed operating-income input required for the requested company-period calculation. Establish actual input availability before choosing the expanded explanation.

**Permitted action:** Retain the unavailable company-period row. Offer supported operating-margin companies or a revised pre-tax task only when its support is accurately described; obtain revised-plan approval before substitution.

**Expanded explanation and limits:** Use the policy's dataset-specific body only when reviewed pre-tax income and net revenue really are available. Otherwise describe the actual missing inputs without implying that a pre-tax alternative is ready.

**Policy:** [BANK_METRICS_AND_COMPARISON_RULES.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/BANK_METRICS_AND_COMPARISON_RULES.md).

**Conditional expanded copy for the selected bank**

Use the following existing policy body only after the selected company-period's reviewed pre-tax income and compatible net revenue are actually available, while the required operating-income input is unavailable:

> Our current dataset provides bank pre-tax income and net revenue, but does not provide the operating-income input required for this calculation. Pre-tax margin is a different metric and cannot replace operating margin in this comparison.

When those alternative inputs are missing or unverified, keep the exact B02 banner but use an accurate body such as:

> The operating-income input required for {company}/{period} is unavailable. {additional_missing_input_summary} Pre-tax margin is a different measure and cannot replace the requested operating margin.

Offer the policy choices only with accurate support labels: choose companies with supported operating-income data, or propose a bank pre-tax-margin task. A revised comparison needs compatible inputs for every company it includes and approval of the revised plan; do not invent missing alternative values.

### B03

**Trigger:** The requested common comparison would combine operating-margin and pre-tax-margin results or another incompatible metric basis.

**Permitted action:** Decline the mixed ranking, gap or average. Offer one compatible metric or explicitly approved separate descriptive sections.

**Expanded explanation and limits:** Correct subtraction does not make different definitions comparable. A separately labelled descriptive section is not permission to rank or average the mixed metrics.

**Policy:** [BANK_METRICS_AND_COMPARISON_RULES.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/BANK_METRICS_AND_COMPARISON_RULES.md).

### F01

**Trigger:** Each company's revenue and income form a compatible annual input pair, and the approved question asks for each issuer's own reported fiscal year, but the companies' annual windows differ.

**Permitted action:** Show both actual date windows and the fiscal-year qualification; proceed with the valid approved comparison rather than blocking solely for different year ends.

**Expanded explanation and limits:** These figures can be compared as the stated reported fiscal years, but do not represent an identical calendar period. An explicit aligned-calendar request needs matching evidence instead.

**Policy:** [FISCAL_PERIODS_AND_UNITS_RULES.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/FISCAL_PERIODS_AND_UNITS_RULES.md).

**Required visible qualification:**

> The annual windows are {actual_windows}. These figures can be compared as the stated reported fiscal years, but they do not represent the same calendar period.

Validate each company's own revenue/income pair first. An annual/quarter mismatch within one calculation is F04; a missing explicitly requested aligned period is F03. Neither should be confused with an otherwise valid own-FY comparison.

### F03

**Trigger:** The approved question requests an aligned calendar or other specific period that the selected annual evidence cannot support for an affected company.

**Permitted action:** Keep the requested row visible with its reason. Offer compatible evidence within authorised scope or a revised reported-fiscal-year plan; do not estimate missing months.

**Expanded explanation and limits:** For example, July-to-June FY2024 inputs must not be relabelled January-to-December 2024. Unavailable in the selected evidence does not mean unavailable from every possible source.

**Policy:** [FISCAL_PERIODS_AND_UNITS_RULES.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/FISCAL_PERIODS_AND_UNITS_RULES.md).

## 3. Period, unit and filing validation

| ID | Exact banner | Show when | Backend owners |
|---|---|---|---|
| F02 | Reporting durations differ: {weeks}. Reported growth is not a calendar-adjusted or organic-growth measure. | Reviewed periods have different annual durations. | R2/R3 |
| F04 | Calculation unavailable: {reason}. Check the input periods, units and financial basis. | Calculation inputs are incompatible or unverified. | R2/R3/R4 |
| V01 | Source basis: {basis}. Selected filing: {filing_date}. {cutoff_summary} | Approved basis and eligible filing are selected. | R2/R3/R4 |
| V02 | Filing-version comparison unavailable: {reason}. The affected result is on hold. | Required version is unresolved or unreliable. | R2/R3/R4 |

### F02

**Trigger:** Reviewed consecutive issuer fiscal years have different durations, such as 52 and 53 weeks, while the reported inputs otherwise support the requested comparison.

**Permitted action:** Show week counts or actual durations alongside reported growth. Do not silently prorate or normalise; any separate method requires its own supported scope.

**Expanded explanation and limits:** Revenue of USD 104 million over 52 weeks and USD 106 million over 53 weeks gives 1.92% reported growth. Equal USD 2 million weekly amounts illustrate the duration effect; they do not authorise automatic normalisation.

**Policy:** [FISCAL_PERIODS_AND_UNITS_RULES.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/FISCAL_PERIODS_AND_UNITS_RULES.md).

### F04

**Trigger:** Inputs within the same calculation have mismatched annual/quarter/YTD dates, unverified currency or scale, incompatible operations/basis, or an invalid denominator under the financial rules.

**Permitted action:** Show the specific affected input and limitation. Obtain compatible source-supported values or revise the task; do not invent a conversion or replace missing values with zero.

**Expanded explanation and limits:** Different companies' own-FY windows alone are not this error. This version does not assume FX conversion. A positive revenue denominator is required for the operating or pre-tax margin task; supported zero income with positive revenue remains valid.

**Policy:** [FISCAL_PERIODS_AND_UNITS_RULES.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/FISCAL_PERIODS_AND_UNITS_RULES.md).

### V01

**Trigger:** The workflow has a declared approved original-as-reported or later-reviewed basis, identified filing and applicable historical cutoff, with source metadata established.

**Permitted action:** Show selected filing/version details and the cutoff or a clear no-as-of-cutoff label. Keep source identity separate from the target financial period.

**Expanded explanation and limits:** Informational source selection does not establish final-note eligibility or current/latest reliability. A later filing may present an earlier target year; post-cutoff evidence must not enter an as-of calculation.

**Policy:** [FILING_VERSION_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/FILING_VERSION_POLICY.md).

### V02

**Trigger:** A required source version is missing, input presentations cannot be reconciled, or known non-reliance makes the selected figures unsuitable for the intended conclusion.

**Permitted action:** Review the version chain and explanation. Use compatible reviewed evidence under an approved basis or hold the affected comparison; human approval cannot waive the evidence failure.

**Expanded explanation and limits:** A later numeric difference alone is not a confirmed restatement. Clearly labelled historical evidence remains distinct from a reliable current conclusion, and any present-day caveat must remain separate from an earlier as-of calculation.

**Policy:** [FILING_VERSION_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/FILING_VERSION_POLICY.md).

## 4. Evidence review and blockers

| ID | Exact banner | Show when | Backend owners |
|---|---|---|---|
| E01 | Insufficient evidence for the year-over-year risk classification. | Paired disclosure coverage is insufficient. | R2/R3/R4 |
| E02 | Explanation unsupported: {claim}. Correct arithmetic does not establish its business cause. | Evidence does not support a causal explanation. | R3/R4 |
| E03 | Review incomplete. Final approval is unavailable. | Required semantic review is incomplete. | R3/R4 |
| A01 | HOLD: {reason}. Correct and recheck before final approval. | An authoritative acceptance blocker remains. | R3/R4 |

### E01

**Trigger:** The requested earlier/later topic comparison lacks sufficient reviewed comparable evidence, including relocated content, cross-references or section-boundary checks where needed.

**Permitted action:** Show the missing scope and any separately supported current passage. Obtain evidence or review a legitimate limited answer; material narrowing requires a revised plan.

**Expanded explanation and limits:** A failed earlier search does not establish absence. Do not label Added, Removed, Changed or Unchanged without the evidence required for that specific finding; identical snippets do not establish whole-section equivalence.

**Policy:** [EVIDENCE_RISK_CHANGE_AND_UNCERTAINTY_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/EVIDENCE_RISK_CHANGE_AND_UNCERTAINTY_POLICY.md).

A separately reviewed current passage may support a narrowly worded current-disclosure observation. Do not say that observation is verified unless the applicable support review completed. Failure to retrieve the earlier passage never establishes that the earlier filing omitted the topic.

### E02

**Trigger:** Review of the actual evidence finds that a retained causal or business-explanation assertion is unsupported, partly supported or contradicted.

**Permitted action:** Remove, correct or narrow the assertion, or obtain supporting evidence and review it. Attribute a supported management explanation to management.

**Expanded explanation and limits:** Do not imply that numerical checks passed unless they actually did. Merely adding possibly to a known unsupported assertion does not make it an accepted factual conclusion.

**Policy:** [EVIDENCE_RISK_CHANGE_AND_UNCERTAINTY_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/EVIDENCE_RISK_CHANGE_AND_UNCERTAINTY_POLICY.md).

### E03

**Trigger:** Required claim review is missing, unavailable, malformed, sampled beyond its justified scope, or cannot be associated completely with the exact note's claim inventory.

**Permitted action:** Show outstanding claims/review scope and preserve the automated failure. Offer further automated work only within authorised bounds, or a permitted recorded claim-level human review route.

**Expanded explanation and limits:** Ordinary final approval is not claim review. A permitted human completion route needs exact claims, evidence, decisions, rationale, reviewer and version; it cannot fabricate missing evidence or retroactively turn failed automated review into a successful critic/evaluation run.

**Policy:** [EVIDENCE_RISK_CHANGE_AND_UNCERTAINTY_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/EVIDENCE_RISK_CHANGE_AND_UNCERTAINTY_POLICY.md).

### A01

**Trigger:** Trusted eligibility checks identify a known unresolved numerical, source, evidence, scope, authority or security blocker affecting the exact candidate note.

**Permitted action:** Present the blocker and permitted correction/review action; refuse publication at the server boundary. Bounded repair exhaustion is not acceptance.

**Expanded explanation and limits:** An approval click does not waive a known error. A valid limited answer may later become eligible after its retained claims and limitations are reviewed; do not treat a justified unavailable result as an automatic permanent whole-note failure.

**Policy:** [ACCEPTANCE_AND_PUBLICATION_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/ACCEPTANCE_AND_PUBLICATION_POLICY.md).

## 5. Approval and publication

| ID | Exact banner | Show when | Backend owners |
|---|---|---|---|
| A02 | Ready for your review. Approve this exact note to save it. | Backend eligibility permits exact-note final review. | R3/R4 |
| A03 | Approval no longer covers this version. Review the rechecked note and approve it again. | Approved content or material context changed. | R3/R4 |
| A04 | Save outcome unknown. Check the original save before retrying. | Portal write may have committed but is unconfirmed. | R3/R4 |
| A05 | Published as {note_id}. | Matching durable portal publication is confirmed. | R2/R3/R4 |

### A02

**Trigger:** The backend confirms the exact note's applicable numerical/source checks and required claim review are complete, requested scope is accounted for, and no blocker remains.

**Permitted action:** Show the full note, citations, limitations, destination/audience, check results and exact version; provide explicit permitted approve/edit/reject/cancel actions.

**Expanded explanation and limits:** Ready is not Approved or Published. A model's success statement, signature alone or incomplete review sample cannot establish eligibility. Any permitted human completion route remains visible.

**Policy:** [ACCEPTANCE_AND_PUBLICATION_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/ACCEPTANCE_AND_PUBLICATION_POLICY.md).

### A03

**Trigger:** Title/body/citations/company coverage or material source, review, policy or approved-plan context changed, or approval was revoked before a confirmed write.

**Permitted action:** Invalidate the affected decision, run relevant fresh checks and obtain approval for the exact changed version/context. Preserve the earlier decision and attempts.

**Expanded explanation and limits:** A page reload alone does not invalidate an unchanged eligible decision or require duplicate publication. If write outcome is uncertain, reconcile the original operation before assuming it can be cancelled or retried.

**Policy:** [ACCEPTANCE_AND_PUBLICATION_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/ACCEPTANCE_AND_PUBLICATION_POLICY.md).

### A04

**Trigger:** A timeout or lost response prevents determining whether the original approved publication operation durably committed.

**Permitted action:** Reconcile the original operation and approved version against the authorised portal record. Do not announce success, regenerate content or create a duplicate to bypass uncertainty.

**Expanded explanation and limits:** A matching durable record/receipt can resolve uncertainty. Retry only through the defined retry and reconciliation controls while approval and eligibility remain valid; cancellation cannot undo an already committed write.

**Policy:** [ACCEPTANCE_AND_PUBLICATION_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/ACCEPTANCE_AND_PUBLICATION_POLICY.md).

### A05

**Trigger:** The portal's durable record/receipt matches the approved operation, exact version and destination, and the viewer is authorised to see the result.

**Permitted action:** Open the authorised saved record. Reconcile any derived-memory update separately, using that same note identity rather than saving another copy.

**Expanded explanation and limits:** When an expected memory update is pending or failed, append: The note is saved. Memory synchronisation is {pending_or_failed}. Repair the memory update; do not save another copy. A deliberately disabled derived update is not a sync failure.

**Policy:** [ACCEPTANCE_AND_PUBLICATION_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/ACCEPTANCE_AND_PUBLICATION_POLICY.md).

**Conditional memory-sync variant:**

> Published as {note_id}. The note is saved. Memory synchronisation is {pending_or_failed}. Repair the memory update; do not save another copy.

Use this variant only when a derived-memory update was expected and its status is actually pending or failed. If saved analyst memory was deliberately off, do not label the disabled update a failure. Publication outcome unknown remains A04 until reconciled; a preview, approval click or successful model response is not a durable portal receipt.

## 6. Private memory and deletion

| ID | Exact banner | Show when | Backend owners |
|---|---|---|---|
| M01 | Saved analyst memory is off for this run. | Backend accepted and enforces saved-memory off. | R2/R3/R4 |
| M02 | Saved context is unavailable for this request. | Saved context is missing or not authorised. | R2/R4 |
| M03 | Saved-history retrieval did not complete. An eligible prior note may or may not be available. | Permitted history retrieval failed. | R2/R3/R4 |
| M04 | Deletion result: {removed_scope}. {retained_or_pending_summary}. | Authorised deletion returned verified results. | R2/R3/R4 |

### M01

**Trigger:** The server accepted the requested setting and enforces disabled optional preference/history reads, including indirect tools, and disabled automatic derived-memory updates for this run.

**Permitted action:** Show the expanded disclosure before execution. Keep public-source search, declared current-run persistence and portal publication separate; require a permitted choice if history is essential.

**Expanded explanation and limits:** Optional saved preferences/history will not be used or automatically updated. Existing records have not been deleted. Run state/checkpoints may still persist under the declared settings; portal saving and reviewed-playbook use are separate. Off does not mean no storage or no external processing.

**Policy:** [MEMORY_AND_PRIVACY_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/MEMORY_AND_PRIVACY_POLICY.md).

**Required visible expanded disclosure:**

> Optional saved preferences/history will not be used or automatically updated for this run. Existing records have not been deleted. Current-run state or checkpoints may still be stored under the declared settings. Portal saving and reviewed-playbook use are separate operations. Memory off does not mean no storage or no external processing.

Show this promise only after the server accepted and can enforce the setting, including indirect history tools and already-loaded context. If applying the setting fails, do not claim memory is off or start the run under an assumed off state. On resume/replan, reconcile current settings, permissions and deleted/withdrawn context before reuse; preserve the historical record without silently reviving obsolete context.

### M02

**Trigger:** A requested private record is not available to the trusted requester, including missing or unauthorised targets. Do not expose which of those conditions applies to a guessed identifier.

**Permitted action:** Offer permitted sources or the appropriate access/settings route without revealing another owner's identity, record existence, contents, counts or private interests.

**Expanded explanation and limits:** Use non-disclosing observable behaviour for missing/unauthorised targets. For an authorised empty bounded history search, report only no eligible note found within the reviewed scope, not that no prior note exists anywhere.

**Policy:** [MEMORY_AND_PRIVACY_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/MEMORY_AND_PRIVACY_POLICY.md).

Do not offer a different visible result that confirms a guessed private record exists, names its owner or reveals its contents. R4 must enforce non-disclosing access behaviour at the data boundary; hiding the UI panel alone is insufficient. M03 is reserved for a history operation whose requester and scope were already authorised.

### M03

**Trigger:** After identity and access checks succeed, a permitted history operation fails or returns an indeterminate result; this is not an unauthorised guessed-record response.

**Permitted action:** Offer permitted retrieval recovery or a scope/settings decision. Continue only when the approved question can honestly be answered without the missing context.

**Expanded explanation and limits:** Do not turn a tool failure into no earlier note exists. A top-k panel or partial result is not a complete inventory. Keep private-record non-disclosure controls in effect.

**Policy:** [MEMORY_AND_PRIVACY_RULES_AND_EXAMPLES.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/MEMORY_AND_PRIVACY_RULES_AND_EXAMPLES.md).

### M04

**Trigger:** An authorised deletion operation returns verified results for its declared owner/workspace, record category and affected stores.

**Permitted action:** Show what was removed, retained for a documented permitted purpose, pending or outside this operation. Reconcile indexes, loaded state, backfill and restore paths; offer only permitted follow-up actions.

**Expanded explanation and limits:** Deleting derived memory does not itself withdraw a portal note or erase checkpoints, logs, exports, backups or previously sent external data. Do not promise universal erasure; deleted context must not silently reactivate from a stale copy.

**Policy:** [MEMORY_AND_PRIVACY_RULES_AND_EXAMPLES.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/MEMORY_AND_PRIVACY_RULES_AND_EXAMPLES.md).

Report the authorised operation's scope rather than a blanket 'everything is forgotten' claim. Withdrawal, correction, deletion of derived memory and deletion of a run/checkpoint are separate operations. Apply current deletion/suppression decisions before restored copies or backfilled portal records become active, and do not retain the deleted sensitive content merely to log its deletion. Retention and third-party erasure promises require documented, verified arrangements.

## 7. Lessons and recovery

| ID | Exact banner | Show when | Backend owners |
|---|---|---|---|
| L01 | Lesson proposed. It is not active. Review its evidence before accepting or rejecting it. | A genuine development lesson awaits exact review. | R2/R3/R4 |
| L02 | Frozen playbook {version} selected. Only accepted, applicable lessons from this version may guide this run. | An applicable frozen reviewed release is selected. | R2/R3/R4 |
| R01 | This operation stopped after AI-provider rate limiting. Earlier usage remains recorded. | Operation stopped after allowed provider recovery. | R3/R4 |
| R02 | A required evidence step failed. Review the affected missing evidence before continuing. | A required evidence or tool operation failed. | R2/R3/R4 |

### L01

**Trigger:** A genuine development failure, critic rejection or analyst correction produced a candidate lesson, but no authorised exact-version acceptance has made it usable.

**Permitted action:** Show the development evidence, proposed procedure, applicability, counterexamples and possible harm; record an actual accept/reject decision and reason.

**Expanded explanation and limits:** A successful case need not invent a lesson. Note approval is separate. Pending, rejected or retired lessons must not become active via an old prompt snapshot, and synthetic teaching rejections do not count as genuine project review evidence.

**Policy:** [MEMORY_AND_PRIVACY_RULES_AND_EXAMPLES.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/MEMORY_AND_PRIVACY_RULES_AND_EXAMPLES.md).

### L02

**Trigger:** A permitted identifiable frozen release is selected, its lessons were accepted, and retrieval is restricted to relevant applicable versions under the run's declared setting.

**Permitted action:** Show the selected release and permitted lesson-use details. Keep it reproducible; changes require a distinct version and the appropriate evaluation/approval decision.

**Expanded explanation and limits:** A mutable frozen flag alone is insufficient. Reconcile current permissions and retired/withdrawn status before reuse; do not silently replace an invalid release during evaluation. Protected answers and other cases must not enter prompts or lessons.

**Policy:** [MEMORY_AND_PRIVACY_RULES_AND_EXAMPLES.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/MEMORY_AND_PRIVACY_RULES_AND_EXAMPLES.md).

### R01

**Trigger:** Trusted provider diagnostics identify rate limiting, and the operation really stopped after its allowed fallback/recovery policy was exhausted or no automatic recovery was permitted.

**Permitted action:** Show only currently authorised recovery options. Explain any model-call effect; retain earlier usage/charges/reservations and do not make a hidden retry or reset counters.

**Expanded explanation and limits:** Do not show a stopped/no-retry state while an approved fallback is still running. Do not label authentication, billing or unrelated gateway errors as HTTP 429. Available models, offline mode or changed configuration are separate permitted choices, not automatic consent to change the approved plan.

**Policy:** [ACCEPTANCE_AND_PUBLICATION_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/ACCEPTANCE_AND_PUBLICATION_POLICY.md).

A rate-limit banner does not itself authorise a model/configuration change, an offline run, a retry, a changed budget or a new research scope. Display only the recovery options the backend currently permits, and explain any required plan/configuration decision. An operation still performing an authorised fallback must instead show its actual running state.

### R02

**Trigger:** A required authorised source/tool operation failed, was refused or returned unusable evidence, leaving an affected research requirement unresolved.

**Permitted action:** Show sanitised diagnostics, affected outputs and the permitted resume/replan action. Preserve successful prior evidence and earlier attempts without inventing a substitute or missing value.

**Expanded explanation and limits:** A failed search is not proof of absence, and a tool error is not zero. Resume only under valid scope and current authorisation; obtain a revised plan when the intended task materially changes.

**Policy:** [ACCEPTANCE_AND_PUBLICATION_POLICY.md](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/R1_role/jayshree/analyst_desk/docs/ACCEPTANCE_AND_PUBLICATION_POLICY.md).

## Review examples for the implementation handoff

These are required development expectations, not executed tests or evidence that the controls already work.

| Situation | Expected frontend and backend behaviour |
|---|---|
| Valid own-FY results end in June and December | Show F01 with both windows; do not block solely for different year ends. |
| A bank has pre-tax inputs but lacks operating income | Show B02 and its conditional body; do not silently relabel the ratio or execute a revised task under the old approval. |
| The bank's alternative inputs are also missing | Keep the limitation accurate; do not claim a pre-tax result is available. |
| Earlier cyber search failed | Show E01; no Added/Removed/Changed/Unchanged verdict is created from failure. |
| A required critic response is missing | Show E03 and unresolved review; a generic approval cannot turn it into a pass. |
| Correct revenue 100 and income 20, but the note says 25% | Show A01 until the affected version is corrected and checked; an approval click cannot waive the error. |
| Approval exists but the save response is lost | Show A04 and reconcile the original operation; do not show Published or create another note. |
| Portal receipt is confirmed and expected memory sync fails | Show A05 plus the sync variant; repair memory using the saved-note identity. |
| Saved memory is off | Show M01 plus the expanded disclosure only after enforcement is confirmed; do not claim deletion or no checkpointing. |
| Another analyst guesses a private note ID | Use M02 without disclosing whether the note exists. |
| An authorised history lookup fails | Use M03 rather than claiming no earlier note exists. |
| A delete operation removes only a derived-memory entry | Show M04's actual scope; do not imply the portal note or backups were erased. |
| An allowed provider fallback is still running | Do not show R01's stopped state yet. |

## Golden answers and evaluation display boundary

A development scoring result is not a research-publication decision. If evaluation results are displayed, R5 must supply the verdict from the declared frozen target: final answer, component output or required workflow/control behaviour. A permitted correction of an intermediate draft is not automatically a final-answer failure.

Keep correctness, completion and case validity separate. An established mandatory failure remains aggregate Fail even if a later timeout also makes completion incomplete. If no definite failure is established but required work did not complete, the aggregate is Incomplete. A disputed expectation requires documented adjudication, not a convenient pass or silent exclusion.

Before scoring any public development case or supplementary boundary fixture, complete the required human/source review, scoring agreement, adapter validation and version freeze. Synthetic fixture correctness is separate from issuer-source retrieval and end-to-end performance; a legitimate production refusal of a fictional company is not a financial-calculation failure. The hypothetical ten-attempt example of six Pass, two Fail and two Incomplete means 60%, 20% and 20% of all attempts, not an observed result for the golden pack.

Do not expose expected answers, protected records or evaluator files to the evaluated application's prompts, tools, retrieval or analyst memory merely to display a scoring panel. A case Pass never supplies exact-note approval or proof of portal persistence.

## Implementation and verification responsibilities

R1 reviews the copy and domain distinctions; R2 confirms metadata and lifecycle inputs; R3 specifies state transitions and allowed recovery; R4 enforces authority and boundaries; R5 independently verifies negative and legitimate-use cases; R6 implements the visible messages and conditional controls. Implement against this versioned contract and retain configuration and execution evidence before claiming a message is implemented.
