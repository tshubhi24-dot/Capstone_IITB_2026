# Analyst Desk Bank Metrics and Comparison Rules

**Status:** Proposed policy for review. Team adoption, company-specific source approval and implementation verification remain pending.

## Proposed decision

Retain operating-margin research as a core task. Support a separate bank pre-tax-margin task after the relevant financial inputs have been reviewed. An operating-margin request must never be answered by silently substituting pre-tax margin.

This policy applies to the retained company list and FY2022, FY2023 and FY2024. Company coverage does not establish that every metric is available for every company-year.

## Metric definitions

| Metric | Definition and application |
|---|---|
| Operating margin | Reported consolidated operating income divided by reported consolidated revenue, multiplied by 100. Use this for the eight retained technology companies, Visa and Mastercard only where compatible inputs are supported. |
| Bank pre-tax margin | Reported consolidated income before income taxes divided by reported consolidated total net revenue after interest expense, multiplied by 100. Proposed for JPMorgan Chase, Goldman Sachs, Bank of America, Morgan Stanley and Wells Fargo, subject to source review. |
| Margin change | Later-period margin minus earlier-period margin, expressed in signed percentage points. Both margins must use the same definition and accounting basis. |

For bank pre-tax margin, numerator and denominator must cover the same operations. If the numerator is income from continuing operations before income taxes and before deduction of income attributable to noncontrolling interests, retain that qualification and require corresponding revenue. Do not mix consolidated and segment figures, or continuing and discontinued operations.

Pre-tax income must retain credit-loss provisions and expenses included in the reported measure. Do not substitute pre-provision profit, net income, net interest income or EBITDA. The calculated ratio must be labelled as an Analyst Desk calculation unless the issuer explicitly reports that same ratio and basis.

## Worked numerical example

All amounts in this example are hypothetical USD millions. Technology Company A, Bank B and Bank C are fictional; these are not reported company results or evidence that the application implements the policy.

### Technology Company A

| Income statement step | USD millions |
|---|---|
| Revenue | 100 |
| Operating costs | -70 |
| Operating profit | 30 |
| Net interest and other non-operating expense | -5 |
| Pre-tax profit | 25 |
| Income tax | -5 |
| Net profit | 20 |

Operating margin = 30 / 100 x 100 = **30.00%**. Pre-tax margin = 25 / 100 x 100 = **25.00%**. These are different measures, even for the same company.

### Bank B

| Income statement step | USD millions |
|---|---|
| Interest income | 100 |
| Interest expense | -40 |
| Net interest income | 60 |
| Fees and other non-interest revenue | +40 |
| Total net revenue | 100 |
| Other expenses | -55 |
| Provision for credit losses | -10 |
| Pre-tax profit | 35 |
| Income tax | -7 |
| Net profit | 28 |

Pre-tax margin = 35 / 100 x 100 = **35.00%**. The corresponding operating-income input is unavailable in the supported evidence for this example. Interest expense has already been deducted when deriving total net revenue; do not deduct it again.

If the request asks for operating margins, displaying Company A at 30.00% and Bank B at 35.00% under one operating-margin heading is incorrect. Bank B's figure is a pre-tax margin. A claim that its operating margin is 5.00 percentage points higher is therefore invalid, despite correct arithmetic.

## Limitation message and pre tax alternative

When a selected bank lacks the required operating-income input, display the following message in the research flow and carry the limitation into any retained partial output:

**Operating-margin comparison unavailable for the selected bank.**

Our current dataset provides bank pre-tax income and net revenue, but does not provide the operating-income input required for this calculation. Pre-tax margin is a different metric and cannot replace operating margin in this comparison.

Offer these choices:

- Choose companies with supported operating-income data.
- Change the research question to a bank pre-tax-margin comparison.

This message describes current supported evidence. It does not claim that banks cannot be analysed. Apply it only when the required input is actually unavailable; missing pre-tax or revenue inputs must also be identified rather than implied to exist.

### Revised bank comparison

A suitable revised request is: "Compare Bank B and Bank C's pre-tax margins for the selected fiscal year."

| Figure | Bank B | Bank C |
|---|---|---|
| Total net revenue in USD millions | 100 | 80 |
| Pre-tax profit in USD millions | 35 | 24 |
| Pre-tax margin calculation | 35 / 100 x 100 | 24 / 80 x 100 |
| Pre-tax margin | 35.00% | 30.00% |

The permitted conclusion is: "Bank B's pre-tax margin is 35.00%, compared with Bank C's 30.00%, a difference of +5.00 percentage points."

That conclusion assumes compatible periods, operations and accounting bases. A higher margin alone does not establish that a bank is a better investment. The app must explain the proposed scope change, obtain approval of the revised plan and then perform the bank comparison. It must not treat the original operating-margin approval as approval of the alternative.

## Financial input requirements

Each input must identify the company, metric, actual period start and end, currency, scale, accounting basis and filing version. Preserve the original statement label, XBRL concept or table-cell location, and a source link.

Bank revenue means the supported reported total after interest expense. Net interest income alone is not total net revenue. Do not subtract interest expense again from an already net revenue figure. A familiar XBRL tag name alone does not establish the correct financial meaning.

Use reported U.S. GAAP consolidated inputs for this version. Do not mix reported amounts with managed, fully taxable-equivalent, adjusted or segment amounts. Later-presented or restated figures must be identified; do not mix reporting versions without reviewing their compatibility. The wider restatement policy remains a separate decision.

## Request handling

| Request or condition | Required behaviour |
|---|---|
| Operating margin for a supported non-bank company | Use verified operating-income and revenue inputs. State their definitions and actual dates. |
| Operating margin for one of the five covered banks | Explain that the supported bank metric is pre-tax margin and operating-margin inputs are unavailable in the current evidence. Offer a revised pre-tax request; obtain approval of the revised plan before proceeding. |
| Explicit bank pre-tax comparison | Name the metric, numerator and revenue basis in the plan and output. Proceed only when compatible inputs are available. |
| An ambiguous request for bank or mixed-company margins | Clarify the requested metric before plan approval. Do not infer consent to change it. |
| Mixed operating and pre-tax margins | Do not calculate a cross-company margin gap, common ranking or combined average. Explain the different definitions. Separate descriptive sections may be used in an explicitly approved plan. |
| Missing or incompatible inputs | Mark the result unavailable and explain why. Preserve the requested company-year row; do not invent, silently omit or substitute a value. |

Other bank ratios, including net interest margin, return on equity and capital ratios, require separate definitions, inputs and scope approval. They are not substitutes for the requested margin.

## Valid comparisons

Compare the same metric on a consistent basis. A broad Technology or Finance group does not establish that its members are suitable peers.

Visa and Mastercard are candidates for an operating-margin comparison. JPMorgan Chase, Bank of America and Wells Fargo are candidates for a banking comparison; Goldman Sachs and Morgan Stanley are candidates for an investment-banking and wealth-management comparison. These are proposed comparison sets, not adopted sector classifications or proof of identical business models. Each plan must explain material differences in business mix and reporting basis before drawing conclusions.

Show actual fiscal dates alongside fiscal-year labels. Different annual year ends may support a clearly qualified fiscal-year comparison; they must not be described as identical calendar periods. Do not create calendar-year figures by relabelling a fiscal year. A request requiring aligned calendar periods needs compatible evidence or clarification.

For year-to-year comparisons, retain the same metric, operations and reporting basis. Disclose acquisitions, disposals or presentation changes that materially affect comparability when supported by the evidence. Do not describe a reported change as organic growth without a supported reconciliation.

## Calculation and display rules

Calculate ratios and differences in code from the source values, then verify them independently in code. Match inputs by company, concept, period, units and basis; arithmetic correctness alone does not establish a valid comparison.

- Use a positive revenue denominator. For zero, negative or unavailable revenue, show the margin as unavailable for this version and explain the reason. A supported negative income numerator produces a negative margin.
- Retain source precision for calculations. Display financial amounts with a named currency and scale, and margins and percentage-point changes to two decimal places. Calculate changes before display rounding.
- Label growth in amounts as percentage change: (later amount / earlier amount - 1) multiplied by 100. Use the same metric and basis and a positive earlier amount. For a zero or negative earlier amount, show the reported amounts and signed amount change instead of a conventional growth percentage.
- Never describe a percentage-point change as percentage growth. A margin increasing from 30.00% to 32.00% changes by +2.00 percentage points.

## Acceptance examples

The cases below define expected behaviour. All numbers in the worked examples are illustrative and are not reported company results.

| Example | Expected result |
|---|---|
| Compare Microsoft and Alphabet operating margins for FY2022-FY2024 | Calculate from operating income and revenue; disclose fiscal dates and sources. |
| Compare JPMorgan Chase and Bank of America operating margins | Explain the unsupported metric and request a revised pre-tax plan. Do not relabel pre-tax figures as operating figures. |
| Compare JPMorgan Chase and Bank of America pre-tax margins for FY2023-FY2024 | Use compatible reported net-revenue and pre-tax inputs; cite both inputs and code calculations. |
| Rank Microsoft and JPMorgan Chase using their available margins | Decline the common ranking because the available metrics differ. Offer an explicitly scoped alternative. |
| Use managed revenue with reported pre-tax income | Reject the mixed basis and obtain compatible reported inputs. |
| A required input is missing or incompatible, or revenue is non-positive | Keep the requested row visible and explain why the margin is unavailable. Zero income with positive revenue is valid and produces a 0.00% margin. |
| A ratio matches its cited values but uses another company's input or the wrong metric | Fail the comparison check despite correct arithmetic. |

## Review and adoption

Apply the same metric and comparison rules to research notes, charts and exported reports. Unresolved metric substitution, incompatible inputs or missing required evidence blocks acceptance as a completed comparison. A partial draft may be reviewed, but exact-note approval does not resolve an incorrect metric.

Before adoption, agree the separate bank task, proposed comparison sets and precision rules. The implementation responsibilities below are proposed handoffs; the relevant owners must confirm them and supply verification evidence.

These rules remain a proposal until reviewed. Preparing this document does not establish implementation compliance or complete the wider financial and research policy.

## Rule implementation responsibilities

R1 reviews financial definitions, comparison rules, limitation wording, acceptance expectations and interpretation. R5 verifies every rule through development regressions and independent evaluation. The proposed implementation handoffs below require owner acknowledgement and reviewed evidence. Implementation remains pending.

| Rule | Roles | Implementation responsibility |
|---|---|---|
| Metric definitions and financial inputs | R2, R3, R4 | R2 validates source concepts and bank net-revenue meaning. R3 selects the intended metric. R4 validates the permitted tool inputs and outputs. |
| Source identity and accounting basis | R2, R3, R4 | R2 preserves source labels, periods, units, operations and filing versions. R3 matches compatible inputs; R4 adds validation checks. |
| No silent substitution or ambiguous margin choice | R3, R4 | R3 preserves requested metric intent and seeks clarification. R4 checks that the executed task matches the approved plan. |
| Limitation message and alternative choices | R6, R3 | R6 displays the exact message and choices. R3 supplies accurate availability and metric status and carries limitations into partial outputs. |
| Approval of a revised pre-tax plan | R3, R4, R6 | R3 creates the revised plan. R4 prevents reuse of the earlier approval. R6 presents the changed scope for analyst approval. |
| Same-metric comparisons and suitable peers | R3, R4 | R3 applies adopted comparison criteria and prevents mixed-metric rankings, gaps and averages. R4 validates comparison inputs. |
| Fiscal periods and year-to-year consistency | R2, R3, R6 | R2 supplies actual dates and presentation changes. R3 checks comparability; R6 displays fiscal dates and qualifications. |
| Calculations and independent verification | R3, R4 | R3 calculates ratios and differences from source values. R4 supplies isolated calculation tools and code checks for arithmetic and input identity. |
| Zero or negative denominators and growth bases | R3, R4 | R3 applies the specified margin and growth rules, including valid zero income. R4 checks invalid bases and prevents unsupported calculations. |
| Precision and percentage-point labels | R3, R6 | R3 calculates from unrounded inputs. R6 renders currency, scale, two-decimal margins and signed percentage-point changes consistently. |
| Missing data and incomplete coverage | R2, R3, R6 | R2 returns explicit missingness. R3 retains requested rows and incomplete status; R6 shows unavailable values with reasons. |
| Acceptance and consistent outputs | R3, R4, R6 | R3 and R4 block completion with unresolved metric or evidence errors and prevent unsupported investment recommendations. R6 applies labels and limitations to notes, charts and exports. |
