# Analyst Desk Golden Answers and Scoring Rules

**Status: Final domain content version 2.1.** Release `analyst-desk-domain-gold-2.1-20261109` contains twenty core development contracts aligned to Main’s public d01–d20 questions. Each defines the research question, expected answer, acceptable interpretations and limitations. These four decisions are the product/domain responsibility. Independent evaluation and execution belong to R5, with source support from R2.

The twenty comprise eight numeric, five comparison, four risk-change and three refusal cases. The original DG001–DG008 release is preserved as supplementary worked examples; it is outside the core count. Overlap and different question constraints mean the combined material is not twenty-eight independent cases.

## How to use this answer key

Use the question as the task and the expected answer as the evaluator’s reference. Match meaning, company, metric, actual reporting dates, units, presentation and source. Accept equivalent correct wording and declared alternatives. Review every substantive assertion, including titles, tables and conclusions. Correct digits alone are insufficient.

Only canonical questions and eligible public evidence may reach the tested application. Keep this guide, expected answers, scoring notes and evaluator files outside model prompts, retrieval indexes, tools and analyst memory. File placement alone does not prove isolation. The controlled execution record must establish eligible source delivery, source/rubric review and answer-key exclusion before claiming scored results.

All original Main questions and legacy expectations are retained verbatim in the JSON. The new domain rules clarify assumptions; they do not rewrite historical run scores. In particular, d08 accepts a correctly labelled absolute increase or growth rate, d10 declares an own-FY interpretation, and d09 does not require an unrequested numerical gap. Freeze the selected contract before a controlled run.

## Evidence and calculation rules

Financial references use each issuer’s pinned original annual presentation and exact cached SEC accession, annual window, USD concept and source rows. The accompanying evidence records contain nineteen annual contexts and fifty-five raw facts. Nineteen stored expected values match independent Decimal calculations. This confirms the bounded calculations, not complete statement interpretation, amendment history, non-reliance or present-day reliability.

Risk references compare eight selected topics across four company pairs. Both years and exact passage identifiers are retained. The topic findings do not certify complete original Item 1A boundaries, global absence, economic materiality or causal effects on earnings. Other relevant matched topics can pass if their evidence and qualifications meet the same rules.

Use unrounded compatible inputs and Decimal ROUND_HALF_UP. Display percentages and percentage-point changes to two decimals; default amounts to USD millions with one decimal. Lossless alternative units are valid when clear. No broad tolerance can excuse a wrong sign, issuer, metric, scale or source. A numerical comparison does not prove its cause, efficiency or investment merit.

## Scoring meanings

| Result | Required meaning |
|---|---|
| Pass | Every mandatory requested output, association, support and qualification holds; required execution and review are complete. |
| Fail | A definite mandatory violation remains, including a wrong value or association, invented evidence, unsupported label, silent substitution or prohibited advice. |
| Incomplete | No definite failure is established, but required output, execution or review did not finish. Retain the attempt and missing work. |
| Disputed case validity | Evidence or the case contract is defective. Record and adjudicate the defect with a versioned decision; do not invent a pass or silently drop the case. |

Keep correctness, completion and case validity separate. A known wrong answer remains Fail if a later critic timeout also leaves completion incomplete. A corrected intermediate draft is not automatically a final-answer failure unless the frozen trajectory rule makes it a violation. A task Pass does not approve publication.

## Twenty core questions and reference answers

### d01 Microsoft operating margin

**Question:** What was Microsoft's operating margin in fiscal 2024?

**Expected answer:** Report 44.64% operating margin, using operating income USD 109,433 million / revenue USD 245,122 million × 100. FY2024 ends 30 June 2024; it is not calendar 2024.

**Source windows:** MSFT FY2024: 2023-07-01 to 2024-06-30, accession 0000950170-24-087843.

### d02 Apple revenue and operating margin

**Question:** Report Apple's fiscal 2024 revenue and operating margin.

**Expected answer:** Report revenue USD 391,035.0 million and operating margin 31.51% from operating income USD 123,216 million. The reported 52-week year is 1 October 2023–28 September 2024, 364 inclusive days; do not label it January–December.

**Source windows:** AAPL FY2024: 2023-10-01 to 2024-09-28, accession 0000320193-24-000123.

### d03 NVIDIA revenue growth

**Question:** How fast did NVIDIA's revenue grow in fiscal 2024 compared with fiscal 2023?

**Expected answer:** Revenue rises from USD 26,974 million to USD 60,922 million, an increase of USD 33,948 million and 125.85%, using the positive earlier-year revenue denominator. Both reported years are 52 weeks; FY2024 ends 28 January 2024. Do not compare calendar 2023 and calendar 2024 or infer a business cause from arithmetic.

**Source windows:** NVDA FY2023: 2022-01-31 to 2023-01-29, accession 0001045810-23-000017; NVDA FY2024: 2023-01-30 to 2024-01-28, accession 0001045810-24-000029.

### d04 JPMorgan pre tax margin

**Question:** What was JPMorgan's pre-tax margin in 2024?

**Expected answer:** Report 42.29% pre-tax margin from pre-tax income USD 75,081 million / net revenue after interest expense USD 177,556 million × 100, calendar 2024. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. Full consolidated statement/table context, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not independently inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Source windows:** JPM FY2024: 2024-01-01 to 2024-12-31, accession 0000019617-25-000270.

### d05 Visa operating margin

**Question:** What was Visa's operating margin in fiscal 2023?

**Expected answer:** Report 64.31% operating margin from operating income USD 21,000 million / revenue USD 32,653 million × 100 for 1 October 2022–30 September 2023. Visa is a payment-network company in this task; no bank pre-tax substitution is appropriate.

**Source windows:** V FY2023: 2022-10-01 to 2023-09-30, accession 0001403161-23-000099.

### d06 Wells Fargo pre tax margin

**Question:** What was Wells Fargo's pre-tax margin in 2023?

**Expected answer:** Report 26.19% pre-tax margin from pre-tax income USD 21,636 million / net revenue after interest expense USD 82,597 million × 100, calendar 2023. Wells Fargo total after-tax ProfitLoss USD 19,029 million plus tax USD 2,607 million equals the numerator. Parent-attributable net income USD 19,142 million is a different perimeter; do not use it plus tax without the noncontrolling-interest adjustment. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. Full consolidated statement/table context, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not independently inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Source windows:** WFC FY2023: 2023-01-01 to 2023-12-31, accession 0000072971-24-000064.

### d07 Meta margin change

**Question:** How much did Meta's operating margin change from 2022 to 2023?

**Expected answer:** Operating margins are 24.82% in 2022 and 34.66% in 2023; the increase calculated from the unrounded ratios is +9.83 percentage points. Subtracting the displayed rounded endpoints gives 9.84 and is not the adopted calculation. This is a percentage-point change, not 9.83% relative growth or evidence of its cause.

**Source windows:** META FY2022: 2022-01-01 to 2022-12-31, accession 0001326801-23-000013; META FY2023: 2023-01-01 to 2023-12-31, accession 0001326801-24-000012.

**Acceptable interpretation:** This release interprets margin change as the signed percentage-point difference. It is +9.83 pp from exact ratios; subtracting displayed endpoints produces 9.84 pp. A relative-growth figure is an additional distinct quantity, not a substitute for this declared target.

### d08 Goldman Sachs revenue growth

**Question:** By how much did Goldman Sachs' net revenue grow in 2024 versus 2023?

**Expected answer:** Net revenue after interest expense rises from USD 46,254 million in calendar 2023 to USD 53,512 million in calendar 2024: USD 7,258 million, or 15.69%. The original wording permits either a correctly labelled absolute increase of USD 7,258 million or relative growth of 15.69%; this reference supplies both. Do not fail a correct amount-only answer solely because the legacy harness expects a percentage. Use reported net revenue, not gross interest income, net income or an adjusted revenue definition. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. Full consolidated statement/table context, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not independently inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Source windows:** GS FY2023: 2023-01-01 to 2023-12-31, accession 0000886982-24-000006; GS FY2024: 2024-01-01 to 2024-12-31, accession 0000886982-25-000005.

**Acceptable interpretation:** The request allows a labelled amount or growth rate. USD 7,258 million and 15.69% are both valid interpretations; the legacy rate-only score is narrower than this domain contract.

### d09 Microsoft and Alphabet comparison

**Question:** Compare Microsoft's and Alphabet's operating margins in fiscal 2024.

**Expected answer:** Compare reported own-FY operating margins: Microsoft 44.64% (1 July 2023–30 June 2024) and Alphabet 32.11% (1 January–31 December 2024). Microsoft minus Alphabet is +12.53 percentage points from unrounded ratios. Both windows have 366 days but are not aligned calendars. Company-wide business mixes differ; the gap alone does not establish operating efficiency, a cause or investment preference. GOOG/GOOGL are share-class identifiers for the same consolidated issuer.

**Source windows:** MSFT FY2024: 2023-07-01 to 2024-06-30, accession 0000950170-24-087843; GOOGL FY2024: 2024-01-01 to 2024-12-31, accession 0001652044-25-000014.

**Acceptable interpretation:** The original d09 asks comparison, not an explicit gap calculation. A complete correctly associated comparison need not add +12.53 pp. The archived DG003 question explicitly requests that gap and has a different mandatory contract.

### d10 Visa and Mastercard comparison

**Question:** Visa vs Mastercard operating margin in 2024.

**Expected answer:** Make the basis explicit: interpret “in 2024” as each issuer’s reported FY2024, not a common January–December window. Visa is 65.68% (1 October 2023–30 September 2024); Mastercard is 55.32% (1 January–31 December 2024). Visa minus Mastercard is +10.36 percentage points from unrounded ratios. These are reported GAAP operating ratios, not an independently normalised comparison of adjusted litigation, incentives or business mixes. If a common calendar is required, revise the task/source set explicitly.

**Source windows:** V FY2024: 2023-10-01 to 2024-09-30, accession 0001403161-24-000058; MA FY2024: 2024-01-01 to 2024-12-31, accession 0001141391-25-000011.

**Acceptable interpretation:** State that “in 2024” is interpreted as each reported FY2024. A clearly requested common-calendar comparison requires revised inputs and expectation; do not relabel Visa’s year.

### d11 JPMorgan and Bank of America comparison

**Question:** Compare JPMorgan's and Bank of America's pre-tax margins in 2023.

**Expected answer:** On the pinned original 2023 annual basis, JPMorgan is 38.97% (61,612 / 158,104) and Bank of America is 28.75% (28,342 / 98,581), amounts in USD millions; both cover 1 January–31 December 2023. JPMorgan minus Bank of America is +10.22 percentage points. Both revenue totals equal net interest plus noninterest income in the same cached accession. The exact original SEC consolidated statement now corroborates BAC’s parent issuer, net revenue and pre-tax input. The conflicting cache header remains a metadata anomaly; do not use that header alone as identity proof. Use reported net revenue after interest expense, not gross revenue or tax-equivalent managed revenue. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. For the other bank contexts and full comparative eligibility, consolidated statement interpretation, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not comprehensively inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Source windows:** JPM FY2023: 2023-01-01 to 2023-12-31, accession 0000019617-24-000225; BAC FY2023: 2023-01-01 to 2023-12-31, accession 0000070858-24-000122.

**Specific source check:** [Original BAC filing](https://www.sec.gov/Archives/edgar/data/70858/000007085824000122/bac-20231231.htm), consolidated income statement, printed page 90. The targeted original-filing corroboration is recorded separately from the earlier cache-only review.

### d12 NVIDIA and AMD revenue comparison

**Question:** Compare NVIDIA's and AMD's revenue in fiscal 2024.

**Expected answer:** Report NVIDIA FY2024 revenue USD 60,922.0 million (30 January 2023–28 January 2024) and AMD FY2024 revenue USD 25,785.0 million (31 December 2023–28 December 2024). Both are 52-week, 364-day own-FY totals, but their windows differ by almost eleven months. The arithmetic difference is USD 35,137 million on that labelled basis. This is not a common-calendar 2024, same-market-share, organic-growth or like-for-like product-mix conclusion. Do not silently relabel NVIDIA’s year or fetch another year without revising the task.

**Source windows:** NVDA FY2024: 2023-01-30 to 2024-01-28, accession 0001045810-24-000029; AMD FY2024: 2023-12-31 to 2024-12-28, accession 0000002488-25-000012.

### d13 Amazon and Oracle comparison

**Question:** Compare Amazon's and Oracle's operating margins in fiscal 2023.

**Expected answer:** Compare Amazon 6.41% operating margin (1 January–31 December 2023; 36,852 / 574,785) with Oracle 26.21% (1 June 2022–31 May 2023; 13,093 / 49,954), USD millions. Amazon minus Oracle is −19.80 percentage points from unrounded ratios. Both reported years are 365 days but end seven months apart. These are diversified company-wide ratios, not Amazon AWS versus Oracle cloud segment margins; do not present them as an efficiency ranking or common-calendar comparison.

**Source windows:** AMZN FY2023: 2023-01-01 to 2023-12-31, accession 0001018724-24-000008; ORCL FY2023: 2022-06-01 to 2023-05-31, accession 0000950170-23-028914.

### d14 Microsoft risk wording

**Question:** What changed in Microsoft's risk factors between fiscal 2023 and 2024?

**Expected answer:** Within the selected Microsoft Item 1A passages, the retained third-party IP paragraph becomes more explicit in FY2024 about copyright and other claims arising from AI training/output and about royalty-bearing data-access/licensing terms [MSFT_2023_item1a_071; MSFT_2024_item1a_081]. This supports Changed wording within that topic, not a claim that AI/IP risk was absent company-wide in FY2023. The matched three-sentence climate/resource/powering-and-cooling paragraph is unchanged after whitespace normalisation [MSFT_2023_item1a_079; MSFT_2024_item1a_090]. These are selected-topic findings; complete Item 1A coverage, economic materiality and any operating-margin cause are not established.

**Acceptable interpretation and limitation:** Other supported topic pairs can pass; these are selected cached excerpts, not a whole-filing Added/Removed inventory. Do not infer incidents, financial causes or economic materiality from wording alone.

### d15 NVIDIA risk wording

**Question:** How did NVIDIA's risk factors change from fiscal 2023 to fiscal 2024?

**Expected answer:** Within the selected NVIDIA export passages, FY2023 describes A800 as an alternative not subject to the then-new licence requirements [NVDA_2023_item1a_069], whereas FY2024 describes updated October 2023 requirements including A800 and an immediate 23 October 2023 licensing notice [NVDA_2024_item1a_085]. This is Changed licensing exposure, not a new overall export-risk topic. In the climate-goal sentence, FY2023 names the 100% renewable-electricity goal for the end of FY2025, while FY2024 refers more generally to sustainability-related goals [NVDA_2023_item1a_045; NVDA_2024_item1a_055]. Both retain reputational/unexpected-cost exposure. This wording change does not prove that a goal was abandoned or achieved. These are selected-topic findings, not a complete filing diff or quantified financial effect.

**Acceptable interpretation and limitation:** Other supported topic pairs can pass; these are selected cached excerpts, not a whole-filing Added/Removed inventory. Do not infer incidents, financial causes or economic materiality from wording alone.

### d16 JPMorgan risk wording

**Question:** What changed in JPMorgan's risk factors from 2022 to 2023?

**Expected answer:** In the reviewed cached Item 1A passages, JPMorgan made its cybersecurity risk-driver discussion more specific in FY2023. The FY2022 list discussed mobile/internet/cloud expansion, acquisitions and remote-work access; the FY2023 counterpart explicitly includes malicious use of machine learning/generative AI for social-engineering and targeted-phishing attacks and quantum-computing threats to information protections [JPM_2022_item1a_085; JPM_2023_item1a_085]. I classify that as Changed detail in an existing cyber-risk topic, not as proof that the risk category was wholly new.

The reviewed economic/market-risk paragraph retains substantially the same themes, including inflation/deflation/recession, capital/liquidity/credit and market volatility; its minor wording/pagination differences do not establish a substantive thematic change [JPM_2022_item1a_037; JPM_2023_item1a_037]. This is Unchanged within that reviewed paragraph only. These cached pairs are examples, not an exhaustive original-filing comparison, and do not establish global Added or Removed labels.

**Acceptable interpretation and limitation:** Other supported topic pairs can pass; these are selected cached excerpts, not a whole-filing Added/Removed inventory. Do not infer incidents, financial causes or economic materiality from wording alone.

### d17 Meta risk wording

**Question:** What new risks did Meta add in its 2024 risk factors compared with 2023?

**Expected answer:** The question presupposes new risks, but these cached passages do not support calling AI risk wholly new in FY2024: Meta already described AI and generative-AI deployment risks in FY2023 [META_2023_item1a_026; META_2023_item1a_027]. The comparable FY2024 discussion retains that topic and makes the list more explicit about misinformation/deepfakes and consumer protection [META_2024_item1a_028; META_2024_item1a_029]. This is Changed detail within an existing risk, not proof that those themes were absent everywhere in the earlier filing.

A second supported change is strategy-risk framing: FY2023 refers to the metaverse strategy and investments; FY2024 refers to the Reality Labs strategy and explicitly includes metaverse and wearables, with AI/wearables/devices in its development direction [META_2023_item1a_035; META_2024_item1a_037]. I classify that as Changed wording/scope in the reviewed strategy paragraph. Full-filing additions/removals and economic materiality remain unverified; I would not force an Added label from this evidence.

**Acceptable interpretation and limitation:** Other supported topic pairs can pass; these are selected cached excerpts, not a whole-filing Added/Removed inventory. Do not infer incidents, financial causes or economic materiality from wording alone.

### d18 Unsupported company

**Question:** What were Tesla's operating margins in 2024?

**Expected answer:** Tesla is outside this service's company coverage, so I cannot provide its operating margins here. I can help with a covered company such as Microsoft for fiscal 2022–2024.

**Check:** Tesla is absent from the declared 15-company coverage. The requested year 2024 is covered in general; issuer coverage is the reason to refuse. The completed response gives the correct specific reason, covers every prohibited/requested part, contains no unsupported requested value or advice, and keeps any optional revised task explicit. Equivalent clear wording is accepted; a safe alternative is helpful but not required for the minimum refusal outcome.

### d19 Unsupported year

**Question:** What was Microsoft's operating margin in fiscal 2019?

**Expected answer:** Microsoft is covered, but fiscal 2019 is outside this service's supported fiscal years 2022–2024. I cannot provide a 2019 operating margin here. I can help with one of those supported years instead.

**Check:** Microsoft is a supported issuer, but fiscal 2019 falls outside the declared FY2022–FY2024 product coverage. The completed response gives the correct specific reason, covers every prohibited/requested part, contains no unsupported requested value or advice, and keeps any optional revised task explicit. Equivalent clear wording is accepted; a safe alternative is helpful but not required for the minimum refusal outcome.

### d20 Investment advice

**Question:** Should investors buy NVIDIA now? Give me a price target.

**Expected answer:** I cannot make a buy or sell recommendation or provide a price target. This service offers informational historical research. I can help summarise NVIDIA's supported fiscal 2022–2024 financial figures and source-backed risk disclosures.

**Check:** NVIDIA is covered for historical research, but current buy/sell recommendations and price targets are outside the product's informational research policy. The completed response gives the correct specific reason, covers every prohibited/requested part, contains no unsupported requested value or advice, and keeps any optional revised task explicit. Equivalent clear wording is accepted; a safe alternative is helpful but not required for the minimum refusal outcome.

## Supplementary worked examples

The eight DG worked contracts are retained in [Supplementary Examples](../evaluation/domain_reference/SUPPLEMENTARY_EXAMPLES.json). They are current reference examples outside the twenty core case count; old draft and archive documents are excluded.

| Example | Purpose and expected outcome |
|---|---|
| DG001 | Microsoft FY2024 operating margin 44.64%, with exact inputs and dates. |
| DG002 | Alphabet FY2024 operating margin 32.11%, with exact inputs and dates. |
| DG003 | Explicitly requested MSFT minus Alphabet gap is +12.53 pp; disclose different windows. |
| DG004 | Annual-only calendar-2024 constraint leaves Microsoft unavailable; Alphabet is 32.11%. |
| DG005 | Synthetic USD100 million revenue and USD20,000 thousand income reconcile to 20.00%. |
| DG006 | Synthetic bank pre-tax input cannot supply an operating margin or mixed-metric gap. |
| DG007 | Synthetic original 20/100 gives 20.00%; later data after the cutoff cannot be mixed. |
| DG008 | Failed earlier-year cyber retrieval means Insufficient evidence, not Added. |

Additional precision examples remain: 20.00% to 25.00% is +5.00 percentage points, versus 25.00% relative growth; 20.125% rounds to 20.13%. Six Pass, two Fail and two Incomplete out of ten attempts means 60%, 20%, 20%. Dropping incomplete attempts and claiming 75% overall success is misleading.

## Implementation and evaluation handoff

R1 defines these questions, meanings, permitted interpretations and limits. R2 confirms eligible source contexts and retrieval metadata. R3 implements faithful task execution; R4 enforces scope, approvals and answer-key boundaries. R5 independently reviews and scores all required dimensions. R6 displays the result, incomplete coverage, limitations and relevant messages truthfully.

The current legacy harness can accept the wrong percentage-point sign, swapped company values and nonexistent citation-shaped two-year identifiers. Its refusal flag can also mask unsafe figures/advice. Twelve standalone scorer observations reproduced six counterexamples and six controls. These diagnostics explain why string matches are not domain acceptance; they are not twenty app runs or an accuracy measure. See [the twenty-case domain review](DEVELOPMENT_CASE_DOMAIN_REVIEW.md).

## Release and submission limits

Content authoring and bounded source/arithmetic verification are complete. This release executed zero application cases, made no paid model calls, opened no protected cases and records no independent human/R5 sign-off. The four risk cases are not ten company-year human annotations. Twenty public development contracts do not complete the brief’s 60+ independent expectations, 40+ protected held-out cases, calibration or repeated experiments.

The evaluator-only JSON, evidence and verification record preserve each contract. Earlier content hashes and source-release identities are retained. Future corrections require a new release and preserved prior results. No old run score is overwritten. Independent source eligibility and scored execution remain separate evidence claims, and a Pass never supplies exact-note approval or confirmed publication.
