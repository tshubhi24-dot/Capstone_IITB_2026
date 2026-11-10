# Analyst Desk Public Development Numeric and Comparison Review

**Status: Final domain review.** Reviewed Main revision 33fef7f94c0b1703265cc8057066b8456122bd54, 9 November 2026.

All **19 stored financial expectations across d01–d13 match** the independently recomputed displayed values on the pinned own-year annual basis. No numeric replacement is needed. The final answer contracts below add dates, metric/source associations and comparison qualifications that the current figure-only expectations do not encode. This is a bounded assistant review of public cached evidence, not independent human validation or 13 passed application cases.

## Method and evidence boundary

The review directly reads tracked public SEC companyfacts and submissions, pins the exact 10-K accession and actual annual start/end for each company-year, requires the corresponding USD concept and annual context, and verifies filing/report dates against cached submissions. It uses 60-digit Decimal arithmetic and ROUND_HALF_UP; differences and growth are calculated before display rounding. No application selector, build_figures, model, judge, network call or protected case was used.

The source contract is explicitly the original own-year annual presentation. The current public questions do not all state a source cutoff; pinning this basis makes the answer reproducible rather than silently treating an old expected value as a current-reliability certificate. Later changed same-period values are recorded in source_facts.json without assuming why they changed. Complete filing-version, amendment and non-reliance eligibility remains outside this bounded cache review.

## Stored values and independent results

| Case | Stored values and independent result | Review result |
|---|---|---|
| d01 | 44.64% | Match with stated qualifiers |
| d02 | $391,035.0M; 31.51% | Match with stated qualifiers |
| d03 | 125.85% | Match with stated qualifiers |
| d04 | 42.29% | Match with bank source limits |
| d05 | 64.31% | Match with stated qualifiers |
| d06 | 26.19% | Match with bank source limits |
| d07 | +9.83 pp | Match with stated qualifiers |
| d08 | 15.69% | Match with bank source limits |
| d09 | 44.64%; 32.11% | Match with stated qualifiers |
| d10 | 65.68%; 55.32% | Match with stated qualifiers |
| d11 | 38.97%; 28.75% | Match with BAC issuer/perimeter clarification |
| d12 | $60,922.0M; $25,785.0M | Match with stated qualifiers |
| d13 | 6.41%; 26.21% | Match with stated qualifiers |

## Annual evidence register

Amounts are exact USD millions from the pinned cached USD facts. A dash means income is not needed for this case, not that income is unavailable. Each raw fact, label/definition, JSON pointer, file hash and submissions reference is retained in source_facts.json.

| Issuer FY | Actual annual window | Days | Revenue | Income and metric | Filing date and accession |
|---|---|---:|---:|---|---|
| MSFT 2024 | 2023-07-01 to 2024-06-30 | 366 | 245,122 | 109433 operating | 2024-07-30; 0000950170-24-087843 |
| AAPL 2024 | 2023-10-01 to 2024-09-28 | 364 | 391,035 | 123216 operating | 2024-11-01; 0000320193-24-000123 |
| NVDA 2023 | 2022-01-31 to 2023-01-29 | 364 | 26,974 | — | 2023-02-24; 0001045810-23-000017 |
| NVDA 2024 | 2023-01-30 to 2024-01-28 | 364 | 60,922 | — | 2024-02-21; 0001045810-24-000029 |
| JPM 2023 | 2023-01-01 to 2023-12-31 | 365 | 158,104 | 61612 pre-tax | 2024-02-16; 0000019617-24-000225 |
| JPM 2024 | 2024-01-01 to 2024-12-31 | 366 | 177,556 | 75081 pre-tax | 2025-02-14; 0000019617-25-000270 |
| V 2023 | 2022-10-01 to 2023-09-30 | 365 | 32,653 | 21000 operating | 2023-11-15; 0001403161-23-000099 |
| V 2024 | 2023-10-01 to 2024-09-30 | 366 | 35,926 | 23595 operating | 2024-11-13; 0001403161-24-000058 |
| WFC 2023 | 2023-01-01 to 2023-12-31 | 365 | 82,597 | 21636 pre-tax | 2024-02-20; 0000072971-24-000064 |
| META 2022 | 2022-01-01 to 2022-12-31 | 365 | 116,609 | 28944 operating | 2023-02-02; 0001326801-23-000013 |
| META 2023 | 2023-01-01 to 2023-12-31 | 365 | 134,902 | 46751 operating | 2024-02-02; 0001326801-24-000012 |
| GS 2023 | 2023-01-01 to 2023-12-31 | 365 | 46,254 | — | 2024-02-23; 0000886982-24-000006 |
| GS 2024 | 2024-01-01 to 2024-12-31 | 366 | 53,512 | — | 2025-02-27; 0000886982-25-000005 |
| GOOGL 2024 | 2024-01-01 to 2024-12-31 | 366 | 350,018 | 112390 operating | 2025-02-05; 0001652044-25-000014 |
| MA 2024 | 2024-01-01 to 2024-12-31 | 366 | 28,167 | 15582 operating | 2025-02-12; 0001141391-25-000011 |
| BAC 2023 | 2023-01-01 to 2023-12-31 | 365 | 98,581 | 28342 pre-tax | 2024-02-20; 0000070858-24-000122 |
| AMD 2024 | 2023-12-31 to 2024-12-28 | 364 | 25,785 | — | 2025-02-05; 0000002488-25-000012 |
| AMZN 2023 | 2023-01-01 to 2023-12-31 | 365 | 574,785 | 36852 operating | 2024-02-02; 0001018724-24-000008 |
| ORCL 2023 | 2022-06-01 to 2023-05-31 | 365 | 49,954 | 13093 operating | 2023-06-20; 0000950170-23-028914 |

## Final case answer contracts

### d01

**Question:** What was Microsoft's operating margin in fiscal 2024?

**Answer and required qualifications:** Report 44.64% operating margin, using operating income USD 109,433 million / revenue USD 245,122 million × 100. FY2024 ends 30 June 2024; it is not calendar 2024.

**Disposition:** Bounded numerical match with stated annual/source/comparison qualifiers. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d02

**Question:** Report Apple's fiscal 2024 revenue and operating margin.

**Answer and required qualifications:** Report revenue USD 391,035.0 million and operating margin 31.51% from operating income USD 123,216 million. The reported 52-week year is 1 October 2023–28 September 2024, 364 inclusive days; do not label it January–December.

**Disposition:** Bounded numerical match with stated annual/source/comparison qualifiers. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d03

**Question:** How fast did NVIDIA's revenue grow in fiscal 2024 compared with fiscal 2023?

**Answer and required qualifications:** Revenue rises from USD 26,974 million to USD 60,922 million, an increase of USD 33,948 million and 125.85%, using the positive earlier-year revenue denominator. Both reported years are 52 weeks; FY2024 ends 28 January 2024. Do not compare calendar 2023 and calendar 2024 or infer a business cause from arithmetic.

**Disposition:** Bounded numerical match with stated annual/source/comparison qualifiers. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d04

**Question:** What was JPMorgan's pre-tax margin in 2024?

**Answer and required qualifications:** Report 42.29% pre-tax margin from pre-tax income USD 75,081 million / net revenue after interest expense USD 177,556 million × 100, calendar 2024. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. Full consolidated statement/table context, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not independently inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Disposition:** Bounded numerical match; bank statement/perimeter not certified. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d05

**Question:** What was Visa's operating margin in fiscal 2023?

**Answer and required qualifications:** Report 64.31% operating margin from operating income USD 21,000 million / revenue USD 32,653 million × 100 for 1 October 2022–30 September 2023. Visa is a payment-network company in this task; no bank pre-tax substitution is appropriate.

**Disposition:** Bounded numerical match with stated annual/source/comparison qualifiers. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d06

**Question:** What was Wells Fargo's pre-tax margin in 2023?

**Answer and required qualifications:** Report 26.19% pre-tax margin from pre-tax income USD 21,636 million / net revenue after interest expense USD 82,597 million × 100, calendar 2023. Wells Fargo total after-tax ProfitLoss USD 19,029 million plus tax USD 2,607 million equals the numerator. Parent-attributable net income USD 19,142 million is a different perimeter; do not use it plus tax without the noncontrolling-interest adjustment. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. Full consolidated statement/table context, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not independently inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Disposition:** Bounded numerical match; bank statement/perimeter not certified. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d07

**Question:** How much did Meta's operating margin change from 2022 to 2023?

**Answer and required qualifications:** Operating margins are 24.82% in 2022 and 34.66% in 2023; the increase calculated from the unrounded ratios is +9.83 percentage points. Subtracting the displayed rounded endpoints gives 9.84 and is not the adopted calculation. This is a percentage-point change, not 9.83% relative growth or evidence of its cause.

**Disposition:** Bounded numerical match with stated annual/source/comparison qualifiers. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d08

**Question:** By how much did Goldman Sachs' net revenue grow in 2024 versus 2023?

**Answer and required qualifications:** Net revenue after interest expense rises from USD 46,254 million in calendar 2023 to USD 53,512 million in calendar 2024: USD 7,258 million, or 15.69%. Include the absolute change because “by how much” permits either amount or rate; the current file checks only the rate. Use reported net revenue, not gross interest income, net income or an adjusted revenue definition. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. Full consolidated statement/table context, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not independently inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Disposition:** Bounded numerical match; bank statement/perimeter not certified. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d09

**Question:** Compare Microsoft's and Alphabet's operating margins in fiscal 2024.

**Answer and required qualifications:** Compare reported own-FY operating margins: Microsoft 44.64% (1 July 2023–30 June 2024) and Alphabet 32.11% (1 January–31 December 2024). Microsoft minus Alphabet is +12.53 percentage points from unrounded ratios. Both windows have 366 days but are not aligned calendars. Company-wide business mixes differ; the gap alone does not establish operating efficiency, a cause or investment preference. GOOG/GOOGL are share-class identifiers for the same consolidated issuer.

**Disposition:** Bounded numerical match with stated annual/source/comparison qualifiers. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d10

**Question:** Visa vs Mastercard operating margin in 2024.

**Answer and required qualifications:** Make the basis explicit: interpret “in 2024” as each issuer’s reported FY2024, not a common January–December window. Visa is 65.68% (1 October 2023–30 September 2024); Mastercard is 55.32% (1 January–31 December 2024). Visa minus Mastercard is +10.36 percentage points from unrounded ratios. These are reported GAAP operating ratios, not an independently normalised comparison of adjusted litigation, incentives or business mixes. If a common calendar is required, revise the task/source set explicitly.

**Disposition:** Bounded numerical match with stated annual/source/comparison qualifiers. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d11

**Question:** Compare JPMorgan's and Bank of America's pre-tax margins in 2023.

**Answer and required qualifications:** On the pinned original 2023 annual basis, JPMorgan is 38.97% (61,612 / 158,104) and Bank of America is 28.75% (28,342 / 98,581), amounts in USD millions; both cover 1 January–31 December 2023. JPMorgan minus Bank of America is +10.22 percentage points. Both revenue totals equal net interest plus noninterest income in the same cached accession. However, the BAC companyfacts header says “BofA Finance LLC” while same-CIK submissions says “BANK OF AMERICA CORP /DE/”; CIK/accession/arithmetic alignment does not explain this conflict. Final issuer/consolidation confirmation is required before certifying this as a fully validated peer comparison. Use reported net revenue after interest expense, not gross revenue or tax-equivalent managed revenue. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. Full consolidated statement/table context, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not independently inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Disposition:** Bounded numerical match; issuer/perimeter clarification required. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d12

**Question:** Compare NVIDIA's and AMD's revenue in fiscal 2024.

**Answer and required qualifications:** Report NVIDIA FY2024 revenue USD 60,922.0 million (30 January 2023–28 January 2024) and AMD FY2024 revenue USD 25,785.0 million (31 December 2023–28 December 2024). Both are 52-week, 364-day own-FY totals, but their windows differ by almost eleven months. The arithmetic difference is USD 35,137 million on that labelled basis. This is not a common-calendar 2024, same-market-share, organic-growth or like-for-like product-mix conclusion. Do not silently relabel NVIDIA’s year or fetch another year without revising the task.

**Disposition:** Bounded numerical match with stated annual/source/comparison qualifiers. The content review is complete; this records the evidence boundary and does not invent an application outcome.

### d13

**Question:** Compare Amazon's and Oracle's operating margins in fiscal 2023.

**Answer and required qualifications:** Compare Amazon 6.41% operating margin (1 January–31 December 2023; 36,852 / 574,785) with Oracle 26.21% (1 June 2022–31 May 2023; 13,093 / 49,954), USD millions. Amazon minus Oracle is −19.80 percentage points from unrounded ratios. Both reported years are 365 days but end seven months apart. These are diversified company-wide ratios, not Amazon AWS versus Oracle cloud segment margins; do not present them as an efficiency ranking or common-calendar comparison.

**Disposition:** Bounded numerical match with stated annual/source/comparison qualifiers. The content review is complete; this records the evidence boundary and does not invent an application outcome.

## Bank source and perimeter findings

Six same-accession annual reconciliations hold: JPMorgan 2023 and 2024, Wells Fargo 2023, Goldman Sachs 2023 and 2024, and Bank of America 2023 each have net interest income plus noninterest income equal to the selected total revenue. The taxonomy explicitly calls the JPMorgan, Wells Fargo and Goldman denominator “Revenues, Net of Interest Expense”. BAC uses the generic Revenues concept; the 56,931 + 41,650 = 98,581 million bridge corroborates the net-interest presentation but is not a substitute for its actual consolidated table/header.

For Wells Fargo, the cached pre-tax bridge uses total ProfitLoss, not parent-attributable NetIncomeLoss: 19,029 + 2,607 = 21,636 million; parent income 19,142 plus noncontrolling-interest loss −113 equals total 19,029. The other selected pre-tax income bridges also reconcile. These are positive source/concept checks, not a full accounting audit.

BAC has an explicit name conflict: the companyfacts header is “BofA Finance LLC”; cached submissions for CIK 0000070858 identify “BANK OF AMERICA CORP /DE/” and ticker BAC, and the selected accession is 0000070858-24-000122. The review retains the 28.75% arithmetic as a bounded result and does not claim the cache alone settles the issuer/consolidation mismatch. Final certification of the d11 peer comparison requires the actual filing/entity/perimeter context. No substitute issuer or corrected source name was invented.

## Scoring and interpretation

Treat a wrong value, sign, company, concept, annual window, USD scale, filing basis or source association as a failure. Silent issuer/year omission, income substitution, percentage-versus-percentage-point confusion, premature rounding, an unsupported common-calendar label or an invented cause also fails the answer contract. A supplied source conflict is not resolved by repeating the expected digits. Missing required source review must remain visible; it is not an automatic correct-answer pass.

The file’s current expect.figures records only 19 target displays. It does not encode all these associations, dates, coverage requirements or peer limitations; matching its strings alone cannot establish acceptance. Optional comparison gaps above are independently calculated teaching detail, not extra quantities already required by the current stored file. No unsupported exact-string-only requirement is introduced: equivalent USD scales and trailing zeros are acceptable if quantities and labels remain correct.

Reported own-FY comparisons are allowed with visible windows; different year ends alone do not require refusal. A common-calendar request needs compatible evidence or an explicit task revision. Bank pre-tax ratios must retain their pre-tax label and reported net-revenue denominator. Arithmetic establishes movements and differences, not financial causes, economic risk changes, investment merit or business-model normalisation.

## Recorded checks and limits

- 13 public case contracts reviewed; 19 stored figure displays independently recomputed and matched.
- 19 exact annual company-year contexts pinned; 6 bank revenue bridges reconciled; 4 pre-tax income/tax bridges reconciled, including Wells Fargo noncontrolling-interest handling.
- No live application cases executed; no model, judge, publication, protected evaluation inspection or independent human expert sign-off.
- Full statement cells, consolidation/continuing-operation footnotes, adjusted-versus-reported bank presentation, complete amendment/non-reliance history and current source reliability were not certified.
- Source URLs are preserved from submissions metadata but were not reopened. Reproduce the offline calculations with reproduce_financial_review.py; financial_review.json contains per-case results and source_facts.json contains exact primary-cache evidence and checksums.
