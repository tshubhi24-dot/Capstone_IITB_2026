# Analyst Desk User Needs and Workflow

**Status:** Final project specification v1.0.

## Purpose and intended user

Analyst Desk supports an equity research analyst preparing or updating company research. The intended output is an inspectable note containing relevant financial findings, disclosure comparisons, specific source references, code-checked calculations and visible limitations. The analyst uses that evidence within an existing research and modelling process and retains responsibility for forecasts, valuation and investment decisions.

## Practitioner findings

Charles Cheng's written feedback describes a workflow of reading news, company filings and reports, updating an Excel earnings and valuation model, and using that model to form or update an investment thesis. He identifies collecting, updating and communicating information as slow activities that constrain company coverage. He places greater weight on expectations versus actual findings than on filing differences alone, and requires assertions to trace to original documents or figures.

Reported informal input from Klemens Loeffler highlights changes in commentary, section length and recurring wording that disappears. These are useful investigation checkpoints. They do not establish that every wording change is economically important or that an omission proves a new business event.

Separate workplace input describes ticker-based financial-data refresh through a Capital IQ Excel plug-in. This vendor choice is not attributed to Charles. His feedback identifies Excel modelling, without naming a data vendor or connector.

These inputs describe reported practice and inform the product requirements below. Baseline and product measurements must use recorded task runs rather than treating practitioner comments as timing evidence.

## Analyst needs and product responses

| Analyst need | Required product response | Verification method |
|---|---|---|
| Efficient information preparation | Assemble relevant evidence and findings for the analyst's existing process. | Measure total task effort, including checking and corrections. |
| Relevant interpretation | Distinguish financial movements, disclosure changes, expectations surprises and supported explanations. | Human review of relevance, important omissions and unsupported conclusions. |
| Inspectable evidence | Link factual claims to specific documents or figures and derived numbers to code calculations. | Check source identity, periods, units, version basis and claim support. |
| Useful comparisons | Show both periods and disclose missing evidence or incompatible inputs. | Review completeness and comparison rules on representative tasks. |

## Current workflow

The sequence below combines the reported broad workflow with the annual-filing research checkpoints. It identifies the product's contribution within the analyst's wider process; forecasts, valuation and the investment thesis remain the analyst's work.

| Stage | Analyst activity and product role |
|---|---|
| 1 Frame the question | Select companies, reporting periods and the question. Identify the comparison basis and any separately available expectations. |
| 2 Read relevant sources | The wider workflow includes news, filings and reports. Analyst Desk's agreed research boundary remains the supported annual SEC evidence. |
| 3 Update the model | The analyst updates an Excel earnings/valuation model. No spreadsheet connector or automatic forecasting capability is established by this document. |
| 4 Inspect disclosures | Review financial statements, management commentary and risk disclosures. Inspect relevant wording changes with both-period evidence. |
| 5 Reconcile inputs | Check fiscal dates, metrics, units, reporting perimeter and filing versions before accepting calculations or comparisons. |
| 6 Prepare and review findings | Review source-linked figures, relevant narrative findings, attributed explanations and limitations. The human analyst updates the thesis or other research output. |
| 7 Retain and revisit | Save the reviewed note through the agreed approval process and use its identifiable evidence for later follow-up research. |

## Evidence and interpretation

A financial movement, an expectations surprise and its cause are different claims. Correct arithmetic establishes the calculated movement; it does not establish the business explanation. Management's stated reason should be attributed to management. A proposed explanation without suitable evidence remains an unverified hypothesis.

Likewise, changed risk wording is evidence of a disclosure difference. A claim that a risk was added or removed requires sufficient comparable-section coverage. A claim about a newly arising economic exposure needs evidence beyond the fact that wording changed.

The research note should make each accepted factual assertion inspectable. A raw generated assertion does not establish an accepted fact. Missing or contradictory evidence must remain visible for review under the project's adopted acceptance rules.

## Illustrative analyst scenario

The following figures are hypothetical, in USD millions. They are not company results or an example supplied by a practitioner. Assume the analyst's expectation was recorded before the actual result became available and uses a compatible period and accounting basis.

| Input | Amount |
|---|---|
| Previous-year reported revenue | 80 |
| Analyst expectation for the current year | 100 |
| Current-year reported revenue | 90 |

Year-over-year growth is `(90 - 80) / 80 x 100 = 12.50%`. The difference from the analyst's expectation is `90 - 100 = -10 million`, or `(90 - 100) / 100 x 100 = -10.00%`.

Revenue grew while falling below the stated expectation. Both findings can matter to the analyst. Neither calculation proves that fewer units sold or margin pressure caused the outcome. A supported explanation needs its own source and careful attribution.

## Product boundaries

The supported annual-filings scope governs company, period and source coverage. The wider practitioner workflow does not automatically add news ingestion, a consensus-data feed, private-model access, Excel integration, forecasting or valuation automation.

An expectations comparison requires an identified, dated baseline with a compatible metric, period, currency, units and accounting basis. This is a separate input and scope decision; no expectation dataset or implemented forecast-comparison feature is established here. Without an eligible baseline, report supported actual trends and state that an expectations comparison is unavailable.

Capital IQ or another vendor can form part of an analyst's existing process. Access, licensing, source reconciliation and integration require separate decisions. Analyst Desk's research output remains informational and does not provide investment recommendations or promises of returns.

## Outcome measures

Evaluate the same supported task with the existing process and Analyst Desk. Measure collection, updating and communication effort together with review time, corrections, source-checking effort and model cost. Assess relevance, important omissions and any increase in useful company coverage separately; no improvement is claimed before measurement.

Record the task, product/source version, method, corrections, total elapsed research/review time and measured cost for each comparison. Keep practitioner feedback, version-specific expert inspection and product-run evidence identifiable as different inputs to acceptance.
