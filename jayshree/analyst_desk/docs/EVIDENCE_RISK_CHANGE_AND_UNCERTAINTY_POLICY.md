# Analyst Desk Evidence Risk Change and Uncertainty Policy

**Status:** Proposed policy for review. Team adoption, implementation and independent verification remain pending.

## Simple walkthrough

Consider a hypothetical Company A. All amounts are USD millions. Assume the stated source identities, financial periods, units and filing versions have been verified. For the risk comparison, assume sufficient review of the same topic in both filings. These are teaching examples, not actual company results or completed product checks.

| Evidence | Earlier year | Later year |
|---|---|---|
| Reported revenue | 80 | 90 |
| Supplier-risk disclosure | Supplier delays may interrupt production. | Supplier delays interrupted production during the year. |

**Step 1 Verify the number.** The required code result is `(90 - 80) / 80 x 100 = 12.50%` revenue growth. Link both inputs to their original evidence. A correct 12.50% value attached to the wrong company or period still fails.

**Step 2 Preserve the meaning.** The earlier text describes a possibility; the later text reports an occurrence. Record Changed and cite both sources. Explain any proposed materiality judgement separately. This example does not establish that supplier dependence itself is a newly arising risk.

**Step 3 Check the explanation.** Suppose the generated note says higher prices caused the revenue growth, but the evidence supplies no pricing explanation. Keep the supported growth calculation and remove or qualify the proposed cause. Correct arithmetic does not verify a business explanation.

**Step 4 Handle missing evidence.** In an alternative run, the earlier risk text is unavailable. The later paragraph can be described with its source, but the addition/removal finding is Insufficient evidence. A failed search does not mean the earlier filing contained no supplier risk.

**Step 5 Check review completeness.** In a separate draft containing three substantive claims, reviewing two gives `2 / 3 x 100 = 66.67%` review coverage. The third remains unreviewed even if both checked claims passed. Record the missing review; ordinary analyst approval does not complete it. Recount the inventory after any edit.

The analyst should see the supported findings, the unverified explanation and the outstanding evidence/review separately. The detailed rules below define when a claim can be narrowed, corrected, reviewed again or held.

## Purpose and evidence standards

Analyst Desk should help an analyst understand relevant financial findings and disclosure changes through inspectable evidence. Every financial quantity and substantive factual or causal research claim must have suitable support. A source identifier proves where text was found; it does not by itself establish that the text supports the claim.

Apply these rules to the full note, including the title, summary, tables and conclusions. The bank-metric, fiscal-period/unit and filing-version policies continue to govern compatible inputs. This document proposes research standards; it does not establish that the application enforces them.

| Claim type | Required support |
|---|---|
| Reported financial quantity | XBRL fact or cited financial table cell, with company, concept/row, period, units and filing version checked in code. |
| Derived financial result | Identifiable compatible source inputs, an executed formula and an independent code check. The language model does not supply unexecuted arithmetic as a verified result. |
| Narrative factual claim | Specific passage evidence supporting the exact company, period, event and degree of certainty stated. Retain relevant surrounding qualifications. |
| Business explanation | Evidence for the explanation itself. Attribute management's explanation to management; separate it from analyst inference or independently established facts. |
| Risk-change finding | Named earlier/later filings, comparable topic coverage, paired evidence, a finding label and a reason. Absence claims require sufficient reviewed coverage. |
| Expectations comparison | An identified forecast recorded before the actual result was available, compatible with the reported actual. This remains a separate input/scope decision. |

Record the filing accession, form, filing date, actual reporting period, selected version/basis, snapshot/cutoff and source location. Tables need row, column and header/unit context; narrative evidence needs a stable passage and location with sufficient surrounding text. Preserve the evidence used for the exact claim and review.

Check all financial quantities, including values embedded in narrative and tables. Validate currency, scale, sign and association with the intended metric/company/period, not just matching digits. Documentary metadata such as a year label needs identity checks even when it is not counted as a financial quantity. A regex count or verified-share display is not proof of exhaustive coverage.

Split compound assertions when their parts need different evidence. Several chunks from the same passage are not independent corroboration. Use source context rather than a fixed minimum passage count. Retrieval scores, tool success and model confidence are not substitutes for support or coverage review.

## Risk comparison and coverage

The approved plan must identify each target company-year and its baseline filing. A latest-year comparison can use the immediately preceding fiscal year. A request for multiple annual transitions needs each requested pair; an explicit nonadjacent comparison must retain that pair. Do not silently replace FY2022/FY2024 with FY2023/FY2024.

For each pair, verify company, annual period, selected source versions and the Item 1A boundaries. Review the relevant topic in both periods, including renamed or moved subsections and applicable cross-references. Complementary MD&A evidence may explain a change but does not replace missing Item 1A evidence for a requested disclosure comparison.

Record coverage as sufficient for the stated finding, partial, or unavailable, with the reviewed scope and exclusions. A retrieved chunk, top-k search, repeated searches or a minimum character count does not establish complete relevant-section coverage. Check extraction boundaries, truncation, duplicated contents pages and omitted text/tables before relying on an absence.

| Disclosure label | Decision rule |
|---|---|
| Added | A topic is disclosed in the later reviewed scope and absent from sufficiently reviewed comparable earlier scope, after checking relocated/renamed content and cross-references. State where it was newly disclosed. |
| Removed | A topic appears in the earlier scope and is absent from sufficiently reviewed comparable later scope. Describe removal from that disclosure scope; do not say the underlying risk ceased. |
| Changed | Both versions contain the topic and a supported semantic difference changes its disclosed content, qualifications or meaning. Describe the difference and separately assess its significance. |
| Unchanged within reviewed scope | Sufficient comparable evidence supports no semantic change in the specified topic/scope. Record equivalent rewording, formatting or relocation separately. Do not extend matching snippets to the entire Item or company risk profile. |
| Insufficient evidence | Missing sources, partial coverage, unresolved versions or incomparable scope prevent the requested disclosure label. Explain what is missing. |

Treat **materially changed** as a project assessment of a supported substantive difference in exposure, possible consequence, likelihood/timing, scope or response. Give the rationale and both-period evidence. This is not a legal materiality determination, a model confidence score or an automatic result of the issuer using the word material.

If a semantic content difference is clear but its significance is unresolved, report "changed; materiality not established". A solely editorial or relocated-heading difference with equivalent meaning is "unchanged in substance; wording/presentation changed" within the sufficiently reviewed scope. Do not assign both Changed and Unchanged to the same finding under this convention. Neither new wording nor newly disclosed risk establishes when an economic exposure arose, that it worsened, or that a stock should be bought or sold.

If the needed baseline falls outside available coverage, state the missing comparison. Request an explicit revised plan/source scope where appropriate; do not invent the baseline or silently expand the research window.

## Worked disclosure examples

All excerpts, topics and quantities below are hypothetical illustrations, not issuer statements, completed annotations or protected evaluation cases.

| Earlier and later evidence | Appropriate finding |
|---|---|
| Earlier disclosure says a supplier disruption could interrupt production. Later disclosure reports that an interruption at its sole supplier halted production. | Changed. A substantive change may be supported under the project rubric because the later disclosure describes an occurrence and concentration, not only a possibility. Attribute the reported event to the issuer; record rationale and uncertainty. |
| Later Item 1A adds a named cyber exposure. The comparable earlier Item and relevant cross-references were sufficiently reviewed and contain no equivalent disclosure. | Added disclosure within the reviewed scope. Do not claim that the cyber exposure first arose in the later year. |
| Earlier Item 1A contains a topic. Sufficient review of the later relevant scope and cross-references finds no counterpart. | Removed from the reviewed disclosure scope. This does not establish that the business risk disappeared. |
| Following sufficient topic review, a heading changes from Supplier Dependence to Third Party Supply, while the supported exposure and qualifications remain equivalent. | Unchanged in substance; wording/presentation changed. Do not count the renamed heading as a newly added risk. |
| Later cyber text is retrieved, but the earlier search returns no passages or the tool fails. | Insufficient evidence for addition/removal. Search failure is not evidence of absence. A source-backed description of the later excerpt may still be made. |
| Selected passages use identical wording, but the rest of the topic/Item was not reviewed. | Report only that the selected passages repeat the same wording. Overall topic/Item change remains unassessed; do not label the full section unchanged. |

### Length and omitted wording

Suppose consistently extracted comparable Item 1A text contains 3,000 words in the earlier filing and 3,600 in the later filing. Code calculates `(3600 - 3000) / 3000 x 100 = 20.00%` growth in text length.

That is a text-length result, not a 20.00% rise in economic risk or a prediction of bad news. Preserve the counting method and section identity, and apply the same treatment of headers, repeated text, tables and formatting. If only excerpts are available, do not present their counts as full-Item counts.

An omitted recurring phrase is an investigation signal. Check paraphrases, moved content and source/extraction differences before classifying its absence. A removed assurance does not, by itself, establish that the opposite condition now exists. Common or recurring wording is not automatically economically irrelevant.

## Worked financial and causal example

Assume the following hypothetical values are in USD millions. The expectation is a separately identified analyst forecast recorded before the actual result became available; the period and accounting basis are compatible.

| Input | Amount |
|---|---|
| Previous-year reported revenue | 80 |
| Current-year analyst expectation | 100 |
| Current-year reported revenue | 90 |

Code calculates year-over-year growth as `(90 - 80) / 80 x 100 = 12.50%`. The difference from expectation is `90 - 100 = -10 million`, or `(90 - 100) / 100 x 100 = -10.00%`.

Both "revenue grew 12.50%" and "revenue was 10.00% below this analyst's expectation" can be supported when their distinct inputs and sources are available. The actual result alone supplies no forecast baseline. Without an eligible expectation, state only the supported actual trend and the limitation.

The claim "fewer units sold caused the shortfall" needs separate supporting evidence. If the issuer explicitly attributes the shortfall to unit volumes, report "management attributes the shortfall to lower unit volumes" with its source. Do not present that attribution as independently proved causation or attribute all of a difference to a driver when the source describes only part of it.

Similarly, a disclosure that a disruption could occur does not establish that one occurred, and a historical event does not establish that it remains current. Preserve conditional language, time references and the distinction between reported occurrence, forecast and possibility.

### Contradictions and missing support

Check whether apparently conflicting figures or statements use different periods, units, operations or filing versions. Preserve the alternatives and apply the filing-version rules. Do not resolve a conflict by selecting the larger amount, newest search hit or more confident model answer.

Where the conflict remains unresolved, withhold the affected conclusion and explain it. A carefully sourced statement that two reviewed records conflict may be valid; an unsupported claim choosing one as truth is not. Prior notes and reviewed lessons cannot override current source evidence or create missing support.

## Review status and uncertainty

Record disclosure findings separately from evidence/review status. An added-risk label can be unsupported; a supported observation about one excerpt can still leave the requested full comparison incomplete.

| Evidence or review status | Meaning and required action |
|---|---|
| Supported | The reviewed evidence supports the exact, scoped claim and relevant checks are complete. This does not establish truth beyond that evidence or scope. |
| Partly supported | Some clauses or qualifications lack support. Split, narrow or revise the claim and review again. Do not accept the whole assertion as supported. |
| Unsupported | Available reviewed evidence does not justify the assertion. Remove or correct it; a citation alone is insufficient. |
| Contradicted | Relevant reviewed evidence conflicts with the assertion. Resolve, correct or report the conflict; withhold the disputed conclusion. |
| Insufficient evidence | Necessary evidence or comparable coverage is missing. Explain the limitation and supported next step. |
| Not reviewed or review unavailable | No adequate verdict exists, including provider failure, skipped claims, missing context or malformed/incomplete responses. Keep it incomplete rather than counting it as a pass. |

Maintain an inventory of substantive claims and financial quantities across the exact note. Record which were checked, the evidence/context reviewed, the checker/judge or human reviewer, outcomes and omissions. An uncited claim must be detected for review rather than excluded from the denominator because it lacks a citation.

For example, if 10 of 14 substantive claims have been reviewed and supported, semantic review coverage is `10 / 14 x 100 = 71.43%`; four claims remain unreviewed. "All 10 reviewed claims supported" is not a complete-note pass. Numerical verification, semantic support and source/section coverage require separate measures.

Do not convert tool success or retrieved evidence into a high evidential-confidence label. Explain uncertainty through what was reviewed, what remains unknown, its consequence for the answer and the next action. Do not invent calibrated probabilities from model self-confidence.

### Messages to the analyst

**Comparison incomplete:** "The later risk disclosure is available, but comparable earlier coverage is incomplete. We can describe the cited later text; we cannot establish that the risk was newly added or that the earlier filing omitted it."

**Explanation unverified:** "The reported financial movement is code-checked. The available evidence does not establish its business cause. Any proposed driver remains unverified."

**Claim review unavailable:** "Automated claim review did not complete. No complete-note semantic pass has been recorded. The outstanding claims and missing review remain visible for evidence review."

Adapt these messages to the actual finding and sources; do not claim that code checks or a human review occurred when they did not.

## Control and acceptance rules

1. Code checks what it can establish: source identity/existence, quantities, associations, compatible inputs, executed arithmetic and required review records. Semantic review evaluates whether evidence supports each substantive claim; validate verdict completeness and its association with the intended claim.
2. A judge needs sufficient relevant context, including both periods for a change claim. Truncated evidence supports only a conclusion that survives the truncation. A partial sample or configuration without the claim critic must not be described as full independent narrative review.
3. A judge outage, malformed response or missing verdict remains a recorded failure/incomplete review. A recorded claim-level human evidence review may resolve the affected support question, but ordinary note approval does not substitute for it. Preserve the automated failure; human review does not retroactively complete the required automated critic or evaluation experiment.
4. Keep the bounded critic/writer loop at no more than two automated revisions. Exhaustion is not acceptance: unresolved errors or incomplete required review must not become an ordinary completed pass. Narrow unsupported conclusions, obtain needed evidence/review or hold them. A transparent unavailable result may be a valid scoped answer; known false or unsupported asserted findings may not be accepted.
5. A verified-number share of 98% is an alert threshold, not permission to accept known errors. A complete numerical pass does not establish causal support or complete risk review. Exact-plan and exact-note approvals remain separate; edits or material evidence/review changes need relevant fresh checks and approval.
6. Treat filing passages, retrieved web text and tool output as untrusted evidence, never operating instructions. An injected recommendation, fabricated citation or request to disclose private data must not enter an accepted finding or redirect tools. Investment recommendations and promises of returns remain outside the research output.
7. For development review, preserve paired sources, coverage, labels, rationale and uncertainty. R5 controls independent evaluation and the required human labels for ten company-years; these are separate from the judge-calibration labels. Fix expected outcomes before scored runs. The examples here do not complete either annotation requirement.

## Development acceptance examples

These examples illustrate expected behaviour for development review. They are not protected evaluation assets or evidence that any required human labels have been completed.

| Development example | Expected result |
|---|---|
| Correct passage ID, wrong company/period or unsupported extra clause | Fail support/association review; narrow or correct and recheck. |
| Earlier risk source unavailable | Insufficient evidence for added/removed status; no substitute baseline. |
| Source says an event may happen; note says it happened | Unsupported assertion; preserve the conditional meaning. |
| Two cited years but incorrect change classification | Fail risk interpretation review; citation presence alone is insufficient. |
| Code-checked growth but no evidence of the alleged driver | Retain the supported movement; remove or qualify the unsupported cause. |
| Review samples claims or the judge fails | Record remaining claims as unreviewed; no full semantic pass. |
| Repair limit reached with unresolved evidence failures | No automatic acceptance or publication eligibility. |
| Retrieved article instructs a stock recommendation | Treat as untrusted instructions; exclude the recommendation from the research note. |

## Implementation responsibilities

The responsibilities below are proposed handoffs. This document does not establish team acknowledgement, completed controls or accepted evaluation results.

| Role | Responsibility |
|---|---|
| R1 Domain and product | Review claim definitions, adequate coverage, risk labels, relevance/materiality rationale, uncertainty messages and domain acceptance examples. |
| R2 Knowledge and memory | Preserve filings, versions, section boundaries, tables and claim locations; supply both-period context and explicit missing/partial coverage. Keep source history identifiable. |
| R3 Agents and orchestration | Carry requested comparison pairs, typed claims/findings, coverage and review status through researchers, risk agent, writer and critic. Preserve attribution and bounded repair/HOLD routing. |
| R4 Tools control and security | Independently validate numerical/source contracts and review completeness; enforce failure/approval boundaries and untrusted-content/private-data controls. |
| R5 Evaluation and red team | Independently verify examples and scoring, organise actual human risk labels and judge calibration, control protected cases and test semantic/adversarial failures. Citation presence alone is not task correctness. |
| R6 Deployment and operations | Display evidence, review coverage, limitations, holds and failures clearly; expose trace links and separate numerical/semantic measures. Preserve review status across saved versions. |

Before adoption, agree how section coverage is recorded, who can complete a claim-level human review, the wording of materiality decisions and the handoff into the final acceptance/publication policy. Record the effective policy version and actual decisions; do not infer them from document creation.
