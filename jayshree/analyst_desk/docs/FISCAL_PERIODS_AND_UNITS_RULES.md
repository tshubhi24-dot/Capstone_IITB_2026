# Analyst Desk Fiscal Periods and Units Rules

**Status:** Final project specification v1.0.

## Purpose and scope

A financial comparison must use the intended reporting periods and compatible units. Correct arithmetic does not make a comparison valid when the inputs cover different periods or use different scales.

This policy covers annual research for the retained companies and FY2022, FY2023 and FY2024. It complements the bank metric rules: matching periods and units does not make operating and pre-tax margins interchangeable. Apply the Filing Version Policy to select the original-as-reported default or an explicitly approved later-reviewed basis and to retain the required version history.

## Fiscal period rules

1. Identify each period using the issuer's fiscal-year label, actual start and end dates, and annual duration or reported week count. Preserve the filing identifier and source location. Do not assume a fiscal-year label is a calendar year or derive it solely from the filing date or period-end year without source confirmation.
2. Confirm that annual revenue and income cover the same company, operations, actual start/end dates and accounting basis before calculating a margin. A matching period-end date alone is insufficient. Do not mix annual, quarter-only, year-to-date or point-in-time values.
3. Recognise normal calendar-year, non-calendar-year, leap-year and 52/53-week annual reporting periods. Validate annual status against the issuer's filing. Duration thresholds are sanity checks, not a substitute for that review. A transition or unusual period needs clarification before it is treated as a comparable full year.
4. A request to compare FY2024 normally means each company's own reported FY2024, unless the analyst specifies another basis. Different year ends alone do not require stopping or clarification. State the company-specific windows in the plan, calculate each margin from its matching inputs and disclose the difference. Do not present the result as identical calendar periods.
5. A request for aligned calendar periods requires evidence for those periods. If the annual snapshot cannot support it, explain the limitation and offer a revised fiscal-year comparison. Do not relabel a June-ending fiscal year as January-December or estimate missing months.
6. For year-to-year changes, verify consecutive issuer fiscal years and a consistent metric and basis. Disclose a 52/53-week or other duration difference. Do not automatically annualise, prorate or call a reported change organic or calendar-aligned growth.
7. Clarify "latest", "last three years" and fiscal-versus-calendar ambiguity against the historical coverage window. Unsupported periods must not silently default to FY2022-FY2024. Quarterly and year-to-date research require separate scope and validation, even if a chart component can produce them.

## Worked period examples

All company figures below are hypothetical. They illustrate required behaviour and are not reported company results or evidence of implemented controls.

### Different annual calendars

Request: "Compare Company A and Company B's FY2024 operating margins."

| Figure | Company A | Company B |
|---|---|---|
| Fiscal-year label | FY2024 | FY2024 |
| Actual annual period | 1 July 2023 to 30 June 2024 | 1 January 2024 to 31 December 2024 |
| Revenue in USD millions | 100 | 200 |
| Operating income in USD millions | 20 | 50 |
| Operating margin | 20 / 100 x 100 = 20.00% | 50 / 200 x 100 = 25.00% |

Use each company's own FY2024. Within Company A, match its revenue and income to July 2023-June 2024; within Company B, match both inputs to January-December 2024. The two companies' windows may differ.

**Message to the analyst:** "Company B's reported FY2024 operating margin was 25.00%, compared with Company A's 20.00%, a difference of +5.00 percentage points. Company A's figures cover 1 July 2023 to 30 June 2024; Company B's cover 1 January to 31 December 2024. These results cover different annual reporting windows."

The workflow is: retrieve each company's FY2024 facts, validate each input pair, calculate independently, compare and disclose the dates. Do not stop solely because the year ends differ.

If the request instead says "Compare both companies for January-December 2024", display: "Company A's available FY2024 figures cover July 2023-June 2024. They do not cover the requested January-December 2024 period. Choose a reported fiscal-year comparison or revise the request."

Do not relabel Company A's year or estimate missing months.

### Same end date with incompatible durations

Suppose Company A's annual revenue is USD 100 million for 1 July 2023 to 30 June 2024. Its quarter-only operating income is USD 8 million for 1 April to 30 June 2024.

Calculating 8 / 100 x 100 = 8.00% is arithmetically correct but is not an annual or quarterly operating margin. The periods differ. Use the annual operating income of USD 20 million for the matching annual period to calculate 20.00%, or obtain matching quarterly revenue under a separately supported task.

### A longer reporting year

A fictional company reports revenue of USD 104 million over 52 weeks and USD 106 million over 53 weeks. Reported revenue growth is (106 / 104 - 1) x 100 = **1.92%**. Revenue per week is USD 2 million in each illustrative period.

The reported increase therefore does not by itself establish improved underlying performance. Disclose the different lengths. The per-week calculation explains the example; it does not introduce an automatically supported normalization method.

## Units and calculation rules

Each financial input must preserve its currency, unit type, scale, sign, source value and reporting context. Monetary totals, per-share figures, share counts and percentages are different unit types and must not be interchanged.

Use base USD monetary values for this version. A companyfacts value in the USD unit bucket is already in dollars: do not apply the filing table's displayed millions scale again. When extracting a table, interpret its header, row and footnotes before converting the displayed cell into base dollars. Preserve the conversion factor and original evidence.

Normalise compatible scales in code before arithmetic. For example, thousands multiply by 1,000; millions by 1,000,000; billions by 1,000,000,000. Scale conversion does not resolve a different currency or accounting definition.

Calculate and independently verify from unrounded normalised inputs. Display amounts by default in USD millions to one decimal place and margins/percentage-point changes to two decimals. Use decimal `ROUND_HALF_UP` for final display rounding. If that amount display conceals a meaningful nonzero value, use a clearly labelled smaller unit or sufficient precision. Display rounding must never feed back into calculations.

A computed ratio of 0.20 is displayed as 20.00%. A value already expressed as 20% must not be multiplied by 100 again. Distinguish percentage growth from percentage-point changes as specified in the bank metric rules.

This version does not convert foreign currencies. A non-USD or mixed-currency request needs an explicit limitation and revised scope, unless a separate currency-conversion method, supporting evidence and revised research scope are explicitly approved. A dollar symbol alone does not establish USD.

For quoted values, verify currency and scale from the cited passage or its preserved table context. Matching digits alone is insufficient. Missing or ambiguous units require clarification or an unavailable result; do not infer that a bare 2.2, 2.2 thousand and 2.2 billion represent the same amount.

## Worked unit examples

All figures in these examples are hypothetical.

### Conversion reference

| Source unit | Equivalent base amount |
|---|---|
| USD 1 thousand | USD 1,000 |
| USD 1 million | USD 1,000,000 |
| USD 1 billion | USD 1,000,000,000 |

USD 20,000 thousand = USD 20,000,000 = USD 20 million. Convert both calculation inputs to the same currency and scale.

### Different scales with the same currency

| Metric | Source presentation | Normalised value |
|---|---|---|
| Annual revenue | 100 in a table headed USD millions | USD 100,000,000 |
| Annual operating income | 20,000 in a table headed USD thousands | USD 20,000,000 |

The correct margin is 20,000,000 / 100,000,000 x 100 = **20.00%**. Equivalently, convert both inputs to millions and calculate 20 / 100 x 100.

Dividing the displayed cells without reading their units gives 20,000 / 100 x 100 = **20,000.00%**, which is wrong. Normalise first.

An XBRL API fact of USD 100,000,000 displays as USD 100.0 million. It must not be interpreted as 100,000,000 million dollars merely because a source statement is presented in millions.

### Different currencies or missing scale

USD 20 million of income divided by EUR 100 million of revenue is not a valid margin for this task. The apparent 20% mixes currencies. Stop and obtain compatible inputs; do not invent an exchange rate.

USD 2.2 thousand equals USD 2,200. USD 2.2 billion equals USD 2,200,000,000. The second is one million times the first. A quote check must reject one as support for the other, even when the digits 2.2 match.

## Limitation messages and response choices

### Different annual windows

**Different fiscal reporting periods.**

These figures cover different annual windows: [Company A actual start and end] and [Company B actual start and end]. They can be compared as the stated reported fiscal years, but do not represent the same calendar period.

Use this message only when a qualified fiscal-year comparison answers the approved question. An explicit aligned-calendar request requires the next message instead.

### Requested period unavailable

**Requested reporting period unavailable.**

The current annual snapshot does not provide compatible inputs for the requested period. Choose a supported fiscal-year comparison or revise the request. The app will not estimate missing periods or substitute years without approval.

### Currency or scale unresolved

**Financial units cannot be verified.**

The selected inputs have incompatible currencies or an unresolved unit or scale. This calculation is unavailable until compatible, source-supported inputs are selected. The app will not assume a currency conversion or infer an unknown scale.

Retain the requested company-period row with its limitation. Clarify the task before plan approval where possible. A later change to the period, metric or currency basis requires a revised approved plan. Show actual dates, unit labels and qualifications consistently in notes, charts, accessible chart details and exports.

## Acceptance examples

These are development acceptance examples. They do not define protected held-out cases or establish that the current implementation passes.

| Example | Expected behaviour |
|---|---|
| Compare Company A and B's reported FY2024 margins with June and December year ends | Proceed using each company's own FY2024; show actual dates and qualify the comparison. Do not stop solely because year ends differ or call the windows identical. |
| Request calendar 2024 using only a June-ending annual fact | Explain unavailable calendar coverage and offer a revised fiscal-year plan. |
| Annual revenue and quarterly income share an end date | Reject the ratio until start dates and durations match. |
| Compare 52-week and 53-week annual revenue | Show reported growth and the duration difference; do not silently prorate. |
| Revenue is in USD millions and income in USD thousands | Convert scales in code; retain sources and factors; the worked example yields 20.00%. |
| Raw companyfacts USD is displayed beside a table headed millions | Keep the raw USD fact unchanged; convert only for display. |
| A quote says USD 2.2K but cites USD 2.2 billion | Fail currency/scale verification despite matching digits. |
| Input currency or table scale cannot be established | Keep the result unavailable with an explanation. |
| An amount is rounded for display | Verify ratios against unrounded inputs; do not reuse rounded display amounts. |

## Rule implementation responsibilities

R1 owns policy meaning, examples, limitation wording and acceptance expectations. R5 verifies every rule through development regressions and independent evaluation. The implementation responsibilities below are required handoffs; record implementation and verification evidence separately from this specification.

| Rule | Roles | Implementation responsibility |
|---|---|---|
| Issuer fiscal labels and annual status | R2, R4 | R2 validates fiscal labels, actual dates and annual durations against filings. R4 validates the tool metadata contract. |
| Matching calculation periods and units | R2, R3, R4 | R2 supplies complete input metadata. R3 matches issuer, operations, dates and units; R4 checks identity and compatibility before calculation. |
| Fiscal versus calendar and relative requests | R3, R4, R6 | R3 uses company-specific reported FY periods for ordinary FY requests and clarifies actual ambiguity. R4 prevents silent substitutions; R6 displays dates, qualifications and supported choices. |
| Different year ends and 52 or 53 weeks | R2, R3, R6 | R2 provides dates and week counts. R3 qualifies interpretation; R6 displays windows and duration differences. |
| Currency and scale extraction | R2, R4 | R2 preserves currency, source units, headers and scale factors. R4 rejects unresolved or incompatible tool values. |
| Normalisation and arithmetic | R3, R4 | R3 calculates from normalised unrounded inputs. R4 provides isolated calculations and independent code checks. |
| Display precision and unit labels | R3, R6 | R3 supplies values and metadata. R6 renders explicit currency, scale and precision using `ROUND_HALF_UP` without changing the calculation inputs. |
| Quoted value verification | R3, R4 | R3 preserves source context for cited quantities. R4 validates currency, scale and value instead of digits alone. |
| Missing evidence and revised approval | R3, R4, R6 | R3 retains unavailable rows and revises scope. R4 requires approval of the changed plan; R6 displays the reason and approval choices. |
| Consistency and acceptance | R3, R4, R6 | R3/R4 block completed comparisons with unresolved period or unit errors. R6 applies the rules across notes, charts and exports. |

## Execution requirements

Apply these period, currency, scale and rounding rules consistently to plans, calculation tools, checks, notes, charts, accessible chart details and exports. Preserve the effective policy version and the input metadata used for each result. The responsible roles must supply implementation and verification evidence; publication of this specification alone does not establish application compliance. Unresolved period or unit failures remain visible and block the affected completed comparison, even when arithmetic is correct or a draft has received ordinary analyst approval.
