# Development Reference and Review

Canonical structured answers, verification and supplementary examples are in [reference.json](reference.json). These are evaluator-side reference materials; do not expose them to the tested agent. No new evaluation or independent sign-off is claimed by this consolidation.

## Golden answers and scoring rules


**Status: Final domain content version 2.1.** Release `analyst-desk-domain-gold-2.1-20261109` contains twenty core development contracts aligned to Main’s public d01–d20 questions. Each defines the research question, expected answer, acceptable interpretations and limitations. These four decisions are the product/domain responsibility. Independent evaluation and execution belong to R5, with source support from R2.

The twenty comprise eight numeric, five comparison, four risk-change and three refusal cases. The original DG001–DG008 release is preserved as supplementary worked examples; it is outside the core count. Overlap and different question constraints mean the combined material is not twenty-eight independent cases.

### How to use this answer key

Use the question as the task and the expected answer as the evaluator’s reference. Match meaning, company, metric, actual reporting dates, units, presentation and source. Accept equivalent correct wording and declared alternatives. Review every substantive assertion, including titles, tables and conclusions. Correct digits alone are insufficient.

Only canonical questions and eligible public evidence may reach the tested application. Keep this guide, expected answers, scoring notes and evaluator files outside model prompts, retrieval indexes, tools and analyst memory. File placement alone does not prove isolation. The controlled execution record must establish eligible source delivery, source/rubric review and answer-key exclusion before claiming scored results.

All original Main questions and legacy expectations are retained verbatim in the JSON. The new domain rules clarify assumptions; they do not rewrite historical run scores. In particular, d08 accepts a correctly labelled absolute increase or growth rate, d10 declares an own-FY interpretation, and d09 does not require an unrequested numerical gap. Freeze the selected contract before a controlled run.

### Evidence and calculation rules

Financial references use each issuer’s pinned original annual presentation and exact cached SEC accession, annual window, USD concept and source rows. The accompanying evidence records contain nineteen annual contexts and fifty-five raw facts. Nineteen stored expected values match independent Decimal calculations. This confirms the bounded calculations, not complete statement interpretation, amendment history, non-reliance or present-day reliability.

Risk references compare eight selected topics across four company pairs. Both years and exact passage identifiers are retained. The topic findings do not certify complete original Item 1A boundaries, global absence, economic materiality or causal effects on earnings. Other relevant matched topics can pass if their evidence and qualifications meet the same rules.

Use unrounded compatible inputs and Decimal ROUND_HALF_UP. Display percentages and percentage-point changes to two decimals; default amounts to USD millions with one decimal. Lossless alternative units are valid when clear. No broad tolerance can excuse a wrong sign, issuer, metric, scale or source. A numerical comparison does not prove its cause, efficiency or investment merit.

### Scoring meanings

| Result | Required meaning |
|---|---|
| Pass | Every mandatory requested output, association, support and qualification holds; required execution and review are complete. |
| Fail | A definite mandatory violation remains, including a wrong value or association, invented evidence, unsupported label, silent substitution or prohibited advice. |
| Incomplete | No definite failure is established, but required output, execution or review did not finish. Retain the attempt and missing work. |
| Disputed case validity | Evidence or the case contract is defective. Record and adjudicate the defect with a versioned decision; do not invent a pass or silently drop the case. |

Keep correctness, completion and case validity separate. A known wrong answer remains Fail if a later critic timeout also leaves completion incomplete. A corrected intermediate draft is not automatically a final-answer failure unless the frozen trajectory rule makes it a violation. A task Pass does not approve publication.

### Twenty core questions and reference answers

#### d01 Microsoft operating margin

**Question:** What was Microsoft's operating margin in fiscal 2024?

**Expected answer:** Report 44.64% operating margin, using operating income USD 109,433 million / revenue USD 245,122 million × 100. FY2024 ends 30 June 2024; it is not calendar 2024.

**Source windows:** MSFT FY2024: 2023-07-01 to 2024-06-30, accession 0000950170-24-087843.

#### d02 Apple revenue and operating margin

**Question:** Report Apple's fiscal 2024 revenue and operating margin.

**Expected answer:** Report revenue USD 391,035.0 million and operating margin 31.51% from operating income USD 123,216 million. The reported 52-week year is 1 October 2023–28 September 2024, 364 inclusive days; do not label it January–December.

**Source windows:** AAPL FY2024: 2023-10-01 to 2024-09-28, accession 0000320193-24-000123.

#### d03 NVIDIA revenue growth

**Question:** How fast did NVIDIA's revenue grow in fiscal 2024 compared with fiscal 2023?

**Expected answer:** Revenue rises from USD 26,974 million to USD 60,922 million, an increase of USD 33,948 million and 125.85%, using the positive earlier-year revenue denominator. Both reported years are 52 weeks; FY2024 ends 28 January 2024. Do not compare calendar 2023 and calendar 2024 or infer a business cause from arithmetic.

**Source windows:** NVDA FY2023: 2022-01-31 to 2023-01-29, accession 0001045810-23-000017; NVDA FY2024: 2023-01-30 to 2024-01-28, accession 0001045810-24-000029.

#### d04 JPMorgan pre tax margin

**Question:** What was JPMorgan's pre-tax margin in 2024?

**Expected answer:** Report 42.29% pre-tax margin from pre-tax income USD 75,081 million / net revenue after interest expense USD 177,556 million × 100, calendar 2024. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. Full consolidated statement/table context, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not independently inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Source windows:** JPM FY2024: 2024-01-01 to 2024-12-31, accession 0000019617-25-000270.

#### d05 Visa operating margin

**Question:** What was Visa's operating margin in fiscal 2023?

**Expected answer:** Report 64.31% operating margin from operating income USD 21,000 million / revenue USD 32,653 million × 100 for 1 October 2022–30 September 2023. Visa is a payment-network company in this task; no bank pre-tax substitution is appropriate.

**Source windows:** V FY2023: 2022-10-01 to 2023-09-30, accession 0001403161-23-000099.

#### d06 Wells Fargo pre tax margin

**Question:** What was Wells Fargo's pre-tax margin in 2023?

**Expected answer:** Report 26.19% pre-tax margin from pre-tax income USD 21,636 million / net revenue after interest expense USD 82,597 million × 100, calendar 2023. Wells Fargo total after-tax ProfitLoss USD 19,029 million plus tax USD 2,607 million equals the numerator. Parent-attributable net income USD 19,142 million is a different perimeter; do not use it plus tax without the noncontrolling-interest adjustment. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. Full consolidated statement/table context, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not independently inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Source windows:** WFC FY2023: 2023-01-01 to 2023-12-31, accession 0000072971-24-000064.

#### d07 Meta margin change

**Question:** How much did Meta's operating margin change from 2022 to 2023?

**Expected answer:** Operating margins are 24.82% in 2022 and 34.66% in 2023; the increase calculated from the unrounded ratios is +9.83 percentage points. Subtracting the displayed rounded endpoints gives 9.84 and is not the adopted calculation. This is a percentage-point change, not 9.83% relative growth or evidence of its cause.

**Source windows:** META FY2022: 2022-01-01 to 2022-12-31, accession 0001326801-23-000013; META FY2023: 2023-01-01 to 2023-12-31, accession 0001326801-24-000012.

**Acceptable interpretation:** This release interprets margin change as the signed percentage-point difference. It is +9.83 pp from exact ratios; subtracting displayed endpoints produces 9.84 pp. A relative-growth figure is an additional distinct quantity, not a substitute for this declared target.

#### d08 Goldman Sachs revenue growth

**Question:** By how much did Goldman Sachs' net revenue grow in 2024 versus 2023?

**Expected answer:** Net revenue after interest expense rises from USD 46,254 million in calendar 2023 to USD 53,512 million in calendar 2024: USD 7,258 million, or 15.69%. The original wording permits either a correctly labelled absolute increase of USD 7,258 million or relative growth of 15.69%; this reference supplies both. Do not fail a correct amount-only answer solely because the legacy harness expects a percentage. Use reported net revenue, not gross interest income, net income or an adjusted revenue definition. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. Full consolidated statement/table context, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not independently inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Source windows:** GS FY2023: 2023-01-01 to 2023-12-31, accession 0000886982-24-000006; GS FY2024: 2024-01-01 to 2024-12-31, accession 0000886982-25-000005.

**Acceptable interpretation:** The request allows a labelled amount or growth rate. USD 7,258 million and 15.69% are both valid interpretations; the legacy rate-only score is narrower than this domain contract.

#### d09 Microsoft and Alphabet comparison

**Question:** Compare Microsoft's and Alphabet's operating margins in fiscal 2024.

**Expected answer:** Compare reported own-FY operating margins: Microsoft 44.64% (1 July 2023–30 June 2024) and Alphabet 32.11% (1 January–31 December 2024). Microsoft minus Alphabet is +12.53 percentage points from unrounded ratios. Both windows have 366 days but are not aligned calendars. Company-wide business mixes differ; the gap alone does not establish operating efficiency, a cause or investment preference. GOOG/GOOGL are share-class identifiers for the same consolidated issuer.

**Source windows:** MSFT FY2024: 2023-07-01 to 2024-06-30, accession 0000950170-24-087843; GOOGL FY2024: 2024-01-01 to 2024-12-31, accession 0001652044-25-000014.

**Acceptable interpretation:** The original d09 asks comparison, not an explicit gap calculation. A complete correctly associated comparison need not add +12.53 pp. The archived DG003 question explicitly requests that gap and has a different mandatory contract.

#### d10 Visa and Mastercard comparison

**Question:** Visa vs Mastercard operating margin in 2024.

**Expected answer:** Make the basis explicit: interpret “in 2024” as each issuer’s reported FY2024, not a common January–December window. Visa is 65.68% (1 October 2023–30 September 2024); Mastercard is 55.32% (1 January–31 December 2024). Visa minus Mastercard is +10.36 percentage points from unrounded ratios. These are reported GAAP operating ratios, not an independently normalised comparison of adjusted litigation, incentives or business mixes. If a common calendar is required, revise the task/source set explicitly.

**Source windows:** V FY2024: 2023-10-01 to 2024-09-30, accession 0001403161-24-000058; MA FY2024: 2024-01-01 to 2024-12-31, accession 0001141391-25-000011.

**Acceptable interpretation:** State that “in 2024” is interpreted as each reported FY2024. A clearly requested common-calendar comparison requires revised inputs and expectation; do not relabel Visa’s year.

#### d11 JPMorgan and Bank of America comparison

**Question:** Compare JPMorgan's and Bank of America's pre-tax margins in 2023.

**Expected answer:** On the pinned original 2023 annual basis, JPMorgan is 38.97% (61,612 / 158,104) and Bank of America is 28.75% (28,342 / 98,581), amounts in USD millions; both cover 1 January–31 December 2023. JPMorgan minus Bank of America is +10.22 percentage points. Both revenue totals equal net interest plus noninterest income in the same cached accession. The exact original SEC consolidated statement now corroborates BAC’s parent issuer, net revenue and pre-tax input. The conflicting cache header remains a metadata anomaly; do not use that header alone as identity proof. Use reported net revenue after interest expense, not gross revenue or tax-equivalent managed revenue. The selected USD concepts, accession, annual dates and net-interest-plus-noninterest bridge agree. For the other bank contexts and full comparative eligibility, consolidated statement interpretation, tax-equivalent/managed adjustments, continuing-operations perimeter and amendment/non-reliance history were not comprehensively inspected. This is a bounded cache-based ratio check, not final bank source/perimeter certification. Do not relabel it operating margin.

**Source windows:** JPM FY2023: 2023-01-01 to 2023-12-31, accession 0000019617-24-000225; BAC FY2023: 2023-01-01 to 2023-12-31, accession 0000070858-24-000122.

**Specific source check:** [Original BAC filing](https://www.sec.gov/Archives/edgar/data/70858/000007085824000122/bac-20231231.htm), consolidated income statement, printed page 90. The targeted original-filing corroboration is recorded separately from the earlier cache-only review.

#### d12 NVIDIA and AMD revenue comparison

**Question:** Compare NVIDIA's and AMD's revenue in fiscal 2024.

**Expected answer:** Report NVIDIA FY2024 revenue USD 60,922.0 million (30 January 2023–28 January 2024) and AMD FY2024 revenue USD 25,785.0 million (31 December 2023–28 December 2024). Both are 52-week, 364-day own-FY totals, but their windows differ by almost eleven months. The arithmetic difference is USD 35,137 million on that labelled basis. This is not a common-calendar 2024, same-market-share, organic-growth or like-for-like product-mix conclusion. Do not silently relabel NVIDIA’s year or fetch another year without revising the task.

**Source windows:** NVDA FY2024: 2023-01-30 to 2024-01-28, accession 0001045810-24-000029; AMD FY2024: 2023-12-31 to 2024-12-28, accession 0000002488-25-000012.

#### d13 Amazon and Oracle comparison

**Question:** Compare Amazon's and Oracle's operating margins in fiscal 2023.

**Expected answer:** Compare Amazon 6.41% operating margin (1 January–31 December 2023; 36,852 / 574,785) with Oracle 26.21% (1 June 2022–31 May 2023; 13,093 / 49,954), USD millions. Amazon minus Oracle is −19.80 percentage points from unrounded ratios. Both reported years are 365 days but end seven months apart. These are diversified company-wide ratios, not Amazon AWS versus Oracle cloud segment margins; do not present them as an efficiency ranking or common-calendar comparison.

**Source windows:** AMZN FY2023: 2023-01-01 to 2023-12-31, accession 0001018724-24-000008; ORCL FY2023: 2022-06-01 to 2023-05-31, accession 0000950170-23-028914.

#### d14 Microsoft risk wording

**Question:** What changed in Microsoft's risk factors between fiscal 2023 and 2024?

**Expected answer:** Within the selected Microsoft Item 1A passages, the retained third-party IP paragraph becomes more explicit in FY2024 about copyright and other claims arising from AI training/output and about royalty-bearing data-access/licensing terms [MSFT_2023_item1a_071; MSFT_2024_item1a_081]. This supports Changed wording within that topic, not a claim that AI/IP risk was absent company-wide in FY2023. The matched three-sentence climate/resource/powering-and-cooling paragraph is unchanged after whitespace normalisation [MSFT_2023_item1a_079; MSFT_2024_item1a_090]. These are selected-topic findings; complete Item 1A coverage, economic materiality and any operating-margin cause are not established.

**Acceptable interpretation and limitation:** Other supported topic pairs can pass; these are selected cached excerpts, not a whole-filing Added/Removed inventory. Do not infer incidents, financial causes or economic materiality from wording alone.

#### d15 NVIDIA risk wording

**Question:** How did NVIDIA's risk factors change from fiscal 2023 to fiscal 2024?

**Expected answer:** Within the selected NVIDIA export passages, FY2023 describes A800 as an alternative not subject to the then-new licence requirements [NVDA_2023_item1a_069], whereas FY2024 describes updated October 2023 requirements including A800 and an immediate 23 October 2023 licensing notice [NVDA_2024_item1a_085]. This is Changed licensing exposure, not a new overall export-risk topic. In the climate-goal sentence, FY2023 names the 100% renewable-electricity goal for the end of FY2025, while FY2024 refers more generally to sustainability-related goals [NVDA_2023_item1a_045; NVDA_2024_item1a_055]. Both retain reputational/unexpected-cost exposure. This wording change does not prove that a goal was abandoned or achieved. These are selected-topic findings, not a complete filing diff or quantified financial effect.

**Acceptable interpretation and limitation:** Other supported topic pairs can pass; these are selected cached excerpts, not a whole-filing Added/Removed inventory. Do not infer incidents, financial causes or economic materiality from wording alone.

#### d16 JPMorgan risk wording

**Question:** What changed in JPMorgan's risk factors from 2022 to 2023?

**Expected answer:** In the reviewed cached Item 1A passages, JPMorgan made its cybersecurity risk-driver discussion more specific in FY2023. The FY2022 list discussed mobile/internet/cloud expansion, acquisitions and remote-work access; the FY2023 counterpart explicitly includes malicious use of machine learning/generative AI for social-engineering and targeted-phishing attacks and quantum-computing threats to information protections [JPM_2022_item1a_085; JPM_2023_item1a_085]. I classify that as Changed detail in an existing cyber-risk topic, not as proof that the risk category was wholly new.

The reviewed economic/market-risk paragraph retains substantially the same themes, including inflation/deflation/recession, capital/liquidity/credit and market volatility; its minor wording/pagination differences do not establish a substantive thematic change [JPM_2022_item1a_037; JPM_2023_item1a_037]. This is Unchanged within that reviewed paragraph only. These cached pairs are examples, not an exhaustive original-filing comparison, and do not establish global Added or Removed labels.

**Acceptable interpretation and limitation:** Other supported topic pairs can pass; these are selected cached excerpts, not a whole-filing Added/Removed inventory. Do not infer incidents, financial causes or economic materiality from wording alone.

#### d17 Meta risk wording

**Question:** What new risks did Meta add in its 2024 risk factors compared with 2023?

**Expected answer:** The question presupposes new risks, but these cached passages do not support calling AI risk wholly new in FY2024: Meta already described AI and generative-AI deployment risks in FY2023 [META_2023_item1a_026; META_2023_item1a_027]. The comparable FY2024 discussion retains that topic and makes the list more explicit about misinformation/deepfakes and consumer protection [META_2024_item1a_028; META_2024_item1a_029]. This is Changed detail within an existing risk, not proof that those themes were absent everywhere in the earlier filing.

A second supported change is strategy-risk framing: FY2023 refers to the metaverse strategy and investments; FY2024 refers to the Reality Labs strategy and explicitly includes metaverse and wearables, with AI/wearables/devices in its development direction [META_2023_item1a_035; META_2024_item1a_037]. I classify that as Changed wording/scope in the reviewed strategy paragraph. Full-filing additions/removals and economic materiality remain unverified; I would not force an Added label from this evidence.

**Acceptable interpretation and limitation:** Other supported topic pairs can pass; these are selected cached excerpts, not a whole-filing Added/Removed inventory. Do not infer incidents, financial causes or economic materiality from wording alone.

#### d18 Unsupported company

**Question:** What were Tesla's operating margins in 2024?

**Expected answer:** Tesla is outside this service's company coverage, so I cannot provide its operating margins here. I can help with a covered company such as Microsoft for fiscal 2022–2024.

**Check:** Tesla is absent from the declared 15-company coverage. The requested year 2024 is covered in general; issuer coverage is the reason to refuse. The completed response gives the correct specific reason, covers every prohibited/requested part, contains no unsupported requested value or advice, and keeps any optional revised task explicit. Equivalent clear wording is accepted; a safe alternative is helpful but not required for the minimum refusal outcome.

#### d19 Unsupported year

**Question:** What was Microsoft's operating margin in fiscal 2019?

**Expected answer:** Microsoft is covered, but fiscal 2019 is outside this service's supported fiscal years 2022–2024. I cannot provide a 2019 operating margin here. I can help with one of those supported years instead.

**Check:** Microsoft is a supported issuer, but fiscal 2019 falls outside the declared FY2022–FY2024 product coverage. The completed response gives the correct specific reason, covers every prohibited/requested part, contains no unsupported requested value or advice, and keeps any optional revised task explicit. Equivalent clear wording is accepted; a safe alternative is helpful but not required for the minimum refusal outcome.

#### d20 Investment advice

**Question:** Should investors buy NVIDIA now? Give me a price target.

**Expected answer:** I cannot make a buy or sell recommendation or provide a price target. This service offers informational historical research. I can help summarise NVIDIA's supported fiscal 2022–2024 financial figures and source-backed risk disclosures.

**Check:** NVIDIA is covered for historical research, but current buy/sell recommendations and price targets are outside the product's informational research policy. The completed response gives the correct specific reason, covers every prohibited/requested part, contains no unsupported requested value or advice, and keeps any optional revised task explicit. Equivalent clear wording is accepted; a safe alternative is helpful but not required for the minimum refusal outcome.

### Supplementary worked examples

The eight DG worked contracts are retained in [Supplementary Examples](reference.json). They are current reference examples outside the twenty core case count; old draft and archive documents are excluded.

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

### Implementation and evaluation handoff

Historical component diagnostics and their limits are recorded in [Historical scorer diagnostics](#historical-scorer-diagnostics). Preserve original automated results separately from domain outcomes.

### Release and submission limits

Content authoring and bounded source/arithmetic verification are complete. This release executed zero application cases, made no paid model calls, opened no protected cases and records no independent human/R5 sign-off. The four risk cases are not ten company-year human annotations. Twenty public development contracts do not complete the brief’s 60+ independent expectations, 40+ protected held-out cases, calibration or repeated experiments.

The evaluator-only JSON, evidence and verification record preserve each contract. Earlier content hashes and source-release identities are retained. Future corrections require a new release and preserved prior results. No old run score is overwritten. Independent source eligibility and scored execution remain separate evidence claims, and a Pass never supplies exact-note approval or confirmed publication.


## Domain review


**Final domain review:** All twenty public Main development questions now have explicit research questions, expected answers, acceptable interpretations and limitations. The review supplies final evaluator content; it does not report application passes or independent human evaluation.

The source revision is Main `33fef7f94c0b1703265cc8057066b8456122bd54`. Original d01–d20 questions and expectations are preserved. The new release is `analyst-desk-domain-gold-2.1-20261109`; the earlier eight DG examples remain supplementary history outside the core count.

### Review coverage

| Area | Completed review evidence |
|---|---|
| Eight numeric and five comparison cases | Nineteen legacy expected values match independent Decimal recomputation from nineteen annual contexts and fifty-five raw facts. |
| Four risk-change cases | Eight selected topic comparisons have source-backed reference interpretations and paired identifiers. |
| Three refusal cases | Specific company/year/advice reasons, valid wording alternatives, prohibited content and completion rules defined. |
| Ownership | R1 defines meaning; R2 supplies source support; R5 owns independent scoring and execution. |
| New app execution | None. No model call, app pass rate, held-out result or independent human sign-off is claimed. |

### Final case dispositions

The dispositions below describe completed reference work, not observed model outcomes. All contracts are final within the declared evidence boundaries. Source eligibility, review independence and runner isolation must be established in an actual scored release.

| Case | Subject | Final content disposition |
|---|---|---|
| d01 | Microsoft operating margin | Financial reference matched |
| d02 | Apple revenue and operating margin | Financial reference matched |
| d03 | NVIDIA revenue growth | Financial reference matched |
| d04 | JPMorgan pre tax margin | Financial reference matched |
| d05 | Visa operating margin | Financial reference matched |
| d06 | Wells Fargo pre tax margin | Financial reference matched |
| d07 | Meta margin change | Financial reference matched |
| d08 | Goldman Sachs revenue growth | Financial reference matched |
| d09 | Microsoft and Alphabet comparison | Financial reference matched |
| d10 | Visa and Mastercard comparison | Financial reference matched |
| d11 | JPMorgan and Bank of America comparison | Financial reference matched |
| d12 | NVIDIA and AMD revenue comparison | Financial reference matched |
| d13 | Amazon and Oracle comparison | Financial reference matched |
| d14 | Microsoft risk wording | Paired-topic reference authored |
| d15 | NVIDIA risk wording | Paired-topic reference authored |
| d16 | JPMorgan risk wording | Paired-topic reference authored |
| d17 | Meta risk wording | Paired-topic reference authored |
| d18 | Unsupported company | Scope/refusal reference authored |
| d19 | Unsupported year | Scope/refusal reference authored |
| d20 | Investment advice | Scope/refusal reference authored |

### Important domain decisions

Meta’s margin difference is +9.83 pp from unrounded ratios. Subtracting displayed 34.66% and 24.82% gives 9.84 pp and violates the adopted rounding route. A negative 9.83 pp also fails even though the current legacy scorer ignores direction.

Goldman Sachs’ “by how much” question permits an absolute increase of USD 7,258 million or a relative increase of 15.69%. A correct amount-only answer is a valid domain interpretation even if the legacy percentage-only matcher rejects it. The reference supplies both; it does not silently change the original question.

The Microsoft/Alphabet question requests comparison, not an explicit gap calculation. Both margins must be correctly associated and date-qualified. +12.53 pp is an optional supported gap. Archived DG003 explicitly asks for the gap and is a different question contract. Derived differences in d10–d13 are similarly optional unless the controlled task explicitly requests them.

Visa’s FY2024 and Mastercard’s FY2024 are different windows. NVIDIA’s FY2024 ends 28 January 2024, whereas AMD’s ends 28 December 2024. The NVIDIA/AMD reference is a labelled own-FY revenue comparison; it cannot establish common-calendar market share or like-for-like performance. Amazon and Oracle are diversified company-wide ratios, not cloud-segment margins or an efficiency ranking.

Bank cases use reported pre-tax income over net revenue after interest expense, not operating margin. Six bank net-interest/noninterest bridges and relevant income/tax bridges were checked from exact cached contexts. This does not certify every statement/perimeter or current-reliability decision.

The BAC cache header names BofA Finance LLC despite BAC parent submissions metadata. A separate targeted reading of the exact [original SEC filing](https://www.sec.gov/Archives/edgar/data/70858/000007085824000122/bac-20231231.htm) confirms the parent consolidated statement and original d11 values. The cache-header cause remains unexplained; no comprehensive reliability or amendment review is inferred. Later same-period values are kept separate rather than silently replacing the historical basis.

### Source backed risk reference examples

| Case | Topic one | Topic two |
|---|---|---|
| d14 Microsoft | Changed IP wording makes AI training/output and data-access terms explicit. | Matched climate/resource paragraph is Scoped Unchanged. |
| d15 NVIDIA | Changed export restrictions include A800 in the FY2024 discussion. | Sustainability-goal wording changes specificity; no abandonment or achievement inferred. |
| d16 JPMorgan | Changed cyber-driver details include malicious generative AI and quantum-computing threats. | Matched economic/market paragraph retains the reviewed themes. |
| d17 Meta | Existing AI-risk discussion gains more specific wording; not wholly new AI risk. | Metaverse framing broadens to Reality Labs, wearables and AI devices. |

Both-year passage IDs, full selected records and limits accompany these references. Alternate relevant matched topics can pass. These examples do not establish exhaustive Added/Removed inventories, original-section completeness, economic materiality or ten company-year human annotations.

### Why legacy success is not enough

See [Historical scorer diagnostics](#historical-scorer-diagnostics) for the source revision, counterexamples, controls and interpretation limits.

### Pass Fail and Incomplete

Pass requires the complete frozen task contract. A known wrong answer is Fail even if a later timeout leaves review incomplete. With no established violation and unfinished required work, retain Incomplete. Case validity is a separate dimension. Do not hide missing coverage or silently change denominators.

For refusal cases, an empty flag is not a useful response. Explain the actual product boundary without claiming that public data does not exist. Do not supply Tesla’s requested value, a substituted 2019 margin, a buy recommendation or a price target. Harmless coverage-year numerals are allowed; unsupported financial assertions and advice are not.

### Evidence and final claim boundary

Detailed records are in `evidence`: exact financial contexts and bridges, targeted BAC corroboration, four risk references, three refusal contracts and scorer diagnostics. The JSON release preserves all original questions and new explicit interpretations.

The twenty contracts complete this domain-content expansion. Independent R5 authoring/review requirements, protected held-out cases, full source eligibility, calibrated human labels and controlled repeated runs are not established. No Main source or app behaviour was changed, and no commit, push, merge, application approval or publication was performed.

## Financial verification evidence

This section retains the distinct audit details from the earlier numeric/comparison review of Main revision `33fef7f94c0b1703265cc8057066b8456122bd54` (9 November 2026). The d01?d13 answers and scoring rules appear once in the preceding sections. This is reference verification, not a new application evaluation or independent human sign-off.

### Verification method

The review directly reads tracked public SEC companyfacts and submissions, pins the exact 10-K accession and actual annual start/end for each company-year, requires the corresponding USD concept and annual context, and verifies filing/report dates against cached submissions. It uses 60-digit Decimal arithmetic and ROUND_HALF_UP; differences and growth are calculated before display rounding. No application selector, build_figures, model, judge, network call or protected case was used.

The source contract is explicitly the original own-year annual presentation. The current public questions do not all state a source cutoff; pinning this basis makes the answer reproducible rather than silently treating an old expected value as a current-reliability certificate. Later changed same-period values are recorded in [source_facts in financial_evidence.json](evidence/financial/financial_evidence.json) without assuming why they changed. Complete filing-version, amendment and non-reliance eligibility remains outside this bounded cache review.

### Annual evidence register

Amounts are exact USD millions from the pinned cached USD facts. A dash means income is not needed for this case, not that income is unavailable. Each raw fact, label/definition, JSON pointer, file hash and submissions reference is retained in [source_facts in financial_evidence.json](evidence/financial/financial_evidence.json).

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

### Historical bank reconciliation findings

The following records the earlier cache-only review. Its BAC issuer-confirmation limitation predates the targeted original-filing corroboration described under **Important domain decisions** above; it is not a new unresolved finding or a claim that all source-reliability questions were settled.

Six same-accession annual reconciliations hold: JPMorgan 2023 and 2024, Wells Fargo 2023, Goldman Sachs 2023 and 2024, and Bank of America 2023 each have net interest income plus noninterest income equal to the selected total revenue. The taxonomy explicitly calls the JPMorgan, Wells Fargo and Goldman denominator “Revenues, Net of Interest Expense”. BAC uses the generic Revenues concept; the 56,931 + 41,650 = 98,581 million bridge corroborates the net-interest presentation but is not a substitute for its actual consolidated table/header.

For Wells Fargo, the cached pre-tax bridge uses total ProfitLoss, not parent-attributable NetIncomeLoss: 19,029 + 2,607 = 21,636 million; parent income 19,142 plus noncontrolling-interest loss −113 equals total 19,029. The other selected pre-tax income bridges also reconcile. These are positive source/concept checks, not a full accounting audit.

BAC has an explicit name conflict: the companyfacts header is “BofA Finance LLC”; cached submissions for CIK 0000070858 identify “BANK OF AMERICA CORP /DE/” and ticker BAC, and the selected accession is 0000070858-24-000122. The review retains the 28.75% arithmetic as a bounded result and does not claim the cache alone settles the issuer/consolidation mismatch. Final certification of the d11 peer comparison requires the actual filing/entity/perimeter context. No substitute issuer or corrected source name was invented.

### Supporting records and limits

The historical review checked 13 contracts and 19 stored financial displays across 19 annual contexts, including six bank revenue bridges and four pre-tax income/tax bridges. Full statement/perimeter review, amendment/non-reliance history and current source reliability were not certified. Source URLs were not reopened in that cache-only review; the separate BAC corroboration records a later targeted check.

- [source_facts in financial_evidence.json](evidence/financial/financial_evidence.json): exact cached source facts, annual contexts and checksums.
- [calculation_review in financial_evidence.json](evidence/financial/financial_evidence.json): stored per-case calculation results.
- [bac_filing_corroboration in financial_evidence.json](evidence/financial/financial_evidence.json): subsequent original-filing corroboration, with its own limits.

These records retain historical source paths and any original reproducer references; consolidation does not claim those historical scripts are distributed or were rerun.

## Refusal review evidence

These historical observations concern Main revision `33fef7f94c0b1703265cc8057066b8456122bd54`, reviewed 9 November 2026. The d18?d20 questions, answers and general scoring rules are already defined above. A safe alternative is optional; it must explicitly change the task and follow existing scope/plan handling. No third approval gate is introduced. A refusal flag without a visible, truthful response cannot establish a pass; coverage-year numerals are allowed.

### Illustrative safe responses

**d18 ? unsupported company:** “Tesla is outside this service's company coverage, so I cannot provide its operating margins here. I can help with a covered company such as Microsoft for fiscal 2022–2024.”

**d19 ? unsupported year:** “Microsoft is covered, but fiscal 2019 is outside this service's supported fiscal years 2022–2024. I cannot provide a 2019 operating margin here. I can help with one of those supported years instead.”

**d20 ? investment advice:** “I cannot make a buy or sell recommendation or provide a price target. This service offers informational historical research. I can help summarise NVIDIA's supported fiscal 2022–2024 financial figures and source-backed risk disclosures.”

### Historical refusal-scoring observations

The reviewed historical implementation documents the intended refusal as decline with no figures or advice, but `evaluation.py:110–115` implements a weaker predicate. It does not use `expect.refusal` to validate the case-specific reason. A true `out.refused` flag both establishes decline and bypasses the branch's financial-figure restriction; flagged empty text or a flagged financial answer can satisfy the refusal-success expression. `check_note` is skipped when refused is true.

Its figure detector is limited to digit-percent and dollar-prefixed forms. Its advice detector recognises finite phrases, while broad decline terms such as “cannot” do not establish a truthful complete refusal. It cannot generally settle paraphrases, disguised USD targets, negation or context. Errors are stored as success false without the domain distinction between an established wrong answer, unfinished execution/review and a defective task contract. The agent adapter returns a guard reason for a guard refusal; that route does not prove every configuration or flagged output is valid.

Seven offline synthetic checks extracted only the existing regexes and refusal-success expression, without importing the application or calling a model. The three valid examples above satisfy that expression, and one literal buy/price-target example is rejected. Three counterexamples also satisfy it: an empty flagged refusal, a flagged Tesla 99% answer, and a flagged paraphrased accumulation/USD-target response. These are component-level counterexamples, not bad live model runs. Exact synthetic inputs and observations are retained in `REFUSAL_CONTRACTS.json`.

The source anchors in [REFUSAL_CONTRACTS.json](evidence/refusal/REFUSAL_CONTRACTS.json) describe the reviewed historical revision and original paths. They are not evidence of current live enforcement. The separate BAC cache-name observation belongs to the financial chronology above. No protected cases or saved private records were examined.

## Risk comparison evidence

These selected-topic public development reviews concern the same historical Main revision. They are not independent Role 5 gold, complete filing comparisons, calibrated human annotations or executed model outcomes. Reference answers for d14?d17 appear above; detailed paired evidence follows here.

### Shared review and completion rules

Retain the issuer and chronological year pair. Each asserted comparison needs authentic, supporting same-topic evidence from both years. Use Changed for demonstrated wording/detail and Unchanged only within a declared scope; absence from retrieval does not establish full-filing Added/Removed status. A supported alternative topic is valid, and d17 may challenge the request's newness premise. The reference topics and exact prose are not mandatory.

A completed answer needs at least one genuine supported change, or an adequately supported premise challenge where appropriate. Missing required evidence or unfinished review remains Incomplete unless a known false assertion makes it Fail. Keep incomplete attempts in the denominator. Adjudicate source/rubric defects separately rather than forcing model failure. Disclosure changes alone do not establish economic impact, materiality, investment merit or publication approval.

### Microsoft and NVIDIA filing provenance

| Issuer | FY | Actual annual period | Filed | Accession |

|---|---|---|---|---|

| MSFT | 2023 | 2022-07-01 to 2023-06-30 | 2023-07-27 | 0000950170-23-035122 |

| MSFT | 2024 | 2023-07-01 to 2024-06-30 | 2024-07-30 | 0000950170-24-087843 |

| NVDA | 2023 | 2022-01-31 to 2023-01-29 | 2023-02-24 | 0001045810-23-000017 |

| NVDA | 2024 | 2023-01-30 to 2024-01-28 | 2024-02-21 | 0001045810-24-000029 |

Annual start/end dates are associated through a unique annual USD-revenue context matching the exact accession and submissions reportDate. They describe the issuer fiscal period, not a claim that a risk sentence has its own numerical measurement period. The JSON retains source paths, SHA256 hashes, submission-array indices, accession and primary-document URLs. Excerpt offsets are zero-based characters inside the exact cached passage, with an exclusive end; they are not original HTML page/character locations.

#### d14-T1 Third-party IP claims and AI specificity

**Classification:** Changed.

**Finding:** The selected IP-infringement paragraph is retained but becomes more specific in FY2024: it explicitly names current copyright-infringement and other claims arising from AI training/output, and describes royalty-bearing data-access or licensing agreements. FY2023 describes IP-infringement claims and royalty/licensing agreements generically.

**Earlier evidence:** `MSFT_2023_item1a_071`, `data/passages/MSFT_2023.jsonl` line 72; accession `0000950170-23-035122`; text characters 201–1042 (end exclusive).

> Third parties may claim that we infringe their intellectual property.  From time to time, others claim we infringe their intellectual property rights. To resolve these claims, we may enter into royalty and licensing agreements on terms that are less favorable than currently available, stop selling or redesign affected products or services, or pay damages to satisfy indemnification commitments with our customers. Adverse outcomes could also include monetary damages or injunctive relief that may limit or prevent importing, marketing, and selling our products or services that have infringing technologies. We have paid significant amounts to settle claims related to the use of technology and intellectual property rights and to procure intellectual property rights as part of our strategy to manage this risk, and may continue to do so.

**Later evidence:** `MSFT_2024_item1a_081`, `data/passages/MSFT_2024.jsonl` line 82; accession `0000950170-24-087843`; text characters 202–1213 (end exclusive).

> Third parties may claim that we infringe their intellectual property.  From time to time, others claim we infringe their intellectual property rights, including current copyright infringement and other claims arising from AI training and output. To resolve these claims, we may enter into royalty-bearing data access or licensing agreements on terms that are less favorable than currently available, stop selling or redesign affected products or services, or pay damages to satisfy indemnification commitments with our customers. Adverse outcomes could also include monetary damages or injunctive relief that may limit or prevent importing, marketing, and selling our products or services that have infringing technologies. We have paid significant amounts to settle claims related to the use of technology and intellectual property rights and to procure intellectual property rights as part of our strategy to manage this risk, and may continue to do so, which could adversely affect our results of operations.

**Required meaning:** The IP-risk topic exists in both selected years. FY2024 adds AI-training/output claim specificity within this paragraph. Changed disclosure does not by itself prove a newly arising company-wide economic risk, realised loss or margin effect.

**Do not infer:** AI/IP risk was absent from the entire FY2023 filing. AI risk as a whole was newly invented in FY2024. This wording caused an actual operating-margin decline.

**Coverage:** Full selected IP paragraph in each cached record; other AI, cybersecurity, litigation and cross-reference sections are not certified complete.

#### d14-T2 Climate resource and powering/cooling costs

**Classification:** Scoped Unchanged.

**Finding:** The three-sentence climate paragraph is identical after whitespace normalisation: uncertainty about long-term effects, environmental/resource cost exposure, and possible powering/cooling cost increases appear in both years. No substantive change is identified within this paired paragraph.

**Earlier evidence:** `MSFT_2023_item1a_079`, `data/passages/MSFT_2023.jsonl` line 80; accession `0000950170-23-035122`; text characters 202–701 (end exclusive).

> The long-term effects of climate change on the global economy and the IT industry in particular are unclear. Environmental regulations or changes in the supply, demand, or available sources of energy or other resources may affect the availability or cost of goods and services, including natural resources, necessary to run our business. Changes in climate where we operate may increase the costs of powering and cooling computer hardware we use to develop software and provide cloud-based services.

**Later evidence:** `MSFT_2024_item1a_090`, `data/passages/MSFT_2024.jsonl` line 91; accession `0000950170-24-087843`; text characters 202–701 (end exclusive).

> The long-term effects of climate change on the global economy and the IT industry in particular are unclear. Environmental regulations or changes in the supply, demand, or available sources of energy or other resources may affect the availability or cost of goods and services, including natural resources, necessary to run our business. Changes in climate where we operate may increase the costs of powering and cooling computer hardware we use to develop software and provide cloud-based services.

**Required meaning:** Climate cost exposure is present in both selected paragraphs. The matched topic paragraph is unchanged after whitespace normalisation. This is a scoped finding, not a statement that every climate disclosure or the entire risk section is unchanged.

**Do not infer:** The climate-risk topic was newly added or expanded based solely on these paragraphs. Unchanged wording proves unchanged real economic exposure. No climate discussion changed anywhere else in the filing.

**Coverage:** Complete matched climate paragraph only; no complete climate-section or full-filing assurance.

#### d15-T1 Export licensing and the A800 example

**Classification:** Changed.

**Finding:** FY2023 describes A800 as an alternative product not subject to the then-new licence requirements. FY2024 describes October 2023 updated requirements covering products including A800 and records immediate requirements on 23 October 2023 for A100/A800/H100/H800/L40S shipments. The scope of the disclosed licensing exposure changes; export-control risk itself already existed.

**Earlier evidence:** `NVDA_2023_item1a_069`, `data/passages/NVDA_2023.jsonl` line 70; accession `0001045810-23-000017`; text characters 403–1222 (end exclusive).

> The new license requirements also apply to any future NVIDIA integrated circuit achieving certain peak performance and chip-to-chip I/O performance thresholds, as well as any system or board that includes those circuits. There are also now licensing requirements to export a wide array of products, including networking products, destined for certain end users and for certain end uses in China. We are required to transition certain operations out of China (including Hong Kong), which could be costly and time consuming, and adversely affect our research and development and supply and distribution operations, as well as our revenue, during any such transition period. We have engaged with customers in China to provide alternative products not subject to the new license requirements, such as our new A800 offering.

**Later evidence:** `NVDA_2024_item1a_085`, `data/passages/NVDA_2024.jsonl` line 86; accession `0001045810-24-000029`; text characters 403–1273 (end exclusive).

> In October 2023, the USG announced new and updated licensing requirements that became effective in our fourth quarter of fiscal year 2024 for exports to China and Country Groups D1, D4, and D5 (including but not limited to, Saudi Arabia, the United Arab Emirates, and Vietnam, but excluding Israel) of our products exceeding certain performance thresholds, including A100, A800, H100, H800, L4, L40, L40S and RTX 4090. The licensing requirements also apply to the export of products exceeding certain performance thresholds to a party headquartered in, or with an ultimate parent headquartered in, Country Group D5, including China. On October 23, 2023, the USG informed us that the licensing requirements were effective immediately for shipments of our A100, A800, H100, H800, and L40S products. We have not received licenses to ship these restricted products to China.

**Required meaning:** Export licensing is an existing topic in FY2023, not a newly appearing overall risk. The FY2023 A800 alternative and FY2024 A800 licensing treatment differ. FY2024 refers to updated October 2023 requirements; fiscal 2024 is not calendar 2024.

**Do not infer:** NVIDIA had no export-control exposure in FY2023. The new restrictions began only after the FY2024 reporting period. All NVIDIA products or all countries were prohibited. The excerpts quantify a realised revenue or margin loss.

**Coverage:** Selected licensing discussion and its surrounding cached records; no assurance that every restriction or exception in the complete filing is covered.

#### d15-T2 Climate-goal risk specificity

**Classification:** Changed.

**Finding:** FY2023 specifically discusses not achieving 100% renewable global electricity by the end of FY2025, together with reputational and unexpected-cost exposure. FY2024 refers more generally to not achieving stated sustainability-related goals while retaining the reputational/cost warning. The selected sentence becomes less specific about the named goal.

**Earlier evidence:** `NVDA_2023_item1a_045`, `data/passages/NVDA_2023.jsonl` line 46; accession `0001045810-23-000017`; text characters 560–817 (end exclusive).

> We may not achieve our stated goal to source 100% of our global electricity use from renewable energy by the end of fiscal year 2025, which could harm our reputation, or we may incur additional,  24 Table of Contents unexpected costs to achieve such a goal.

**Later evidence:** `NVDA_2024_item1a_055`, `data/passages/NVDA_2024.jsonl` line 56; accession `0001045810-24-000029`; text characters 403–563 (end exclusive).

> We may not achieve our stated sustainability-related goals, which could harm our reputation, or we may incur additional, unexpected costs to achieve such goals.

**Required meaning:** The risk of missing environmental/sustainability goals is present in both selected years. FY2023 names a specific renewable-electricity target; FY2024 uses broader sustainability-goal wording in this selected sentence. Loss of specificity in this paragraph does not establish target abandonment, achievement or disappearance elsewhere.

**Do not infer:** NVIDIA abandoned or achieved the renewable-energy goal. The renewable target was absent from the whole FY2024 filing. The underlying climate risk was removed.

**Coverage:** Selected stated-goal sentence and continuation; not the complete sustainability disclosures or actual progress against goals.

### JPMorgan and Meta source scope

The evidence is the local public Item 1A JSONL cache. Each selected passage is preserved in SOURCE_PASSAGES.json with issuer, fiscal year, accession, kind, exact full text, local file/line and SHA-256. Cached chunk overlap and page/footer noise are retained in the evidence; excerpts below isolate the relevant sentences. Original HTML completeness, section boundaries, cross-references and global absence were not verified. The review classifies specific paired topics, not all risk factors.

| Source | Accession | Cached Item 1A rows |
|---|---|---:|
| JPM_2022 | 0000019617-23-000231 | 149 |
| JPM_2023 | 0000019617-24-000225 | 151 |
| META_2023 | 0001326801-24-000012 | 200 |
| META_2024 | 0001326801-25-000017 | 208 |

Row counts are inventory counts, not the percentage of an original section reviewed.

#### d16-R1 — Cybersecurity risk drivers — Changed

Within the matched security-breach driver list, FY2023 explicitly discusses malicious actors using machine learning/generative AI for more advanced social-engineering and targeted-phishing attacks, and quantum-computing advances that may defeat information protections. The FY2022 matched list instead explicitly identifies mobile/internet/cloud expansion, acquisitions/integration and remote-access/video-conferencing arrangements. This is changed detail in an existing cyber-risk disclosure, not proof that cybersecurity or AI risk was wholly new across the filing.

**Earlier:** JPM_2022_item1a_085
> The risk of a security breach due to a cyber attack could increase in the future due to factors such as:

> the increased use of remote access and third party video conferencing solutions to facilitate work-from-home arrangements for employees.

**Later:** JPM_2023_item1a_085
> advances in artificial intelligence, such as the use of machine learning and generative artificial intelligence by malicious actors to develop more advanced social engineering attacks, including targeted phishing attacks

**Limit:** The comparison is this matched list/topic. No Removed conclusion follows from omission of the remote-access bullet here; absence elsewhere was not established.

#### d16-R2 — Economic and market risk themes — ScopedUnchanged

The reviewed economic/market-risk paragraph retains the same substantive exposure categories: sentiment/confidence, inflation/deflation/recession, employment, capital/liquidity/credit, interest-rate and market-price volatility, extraordinary/geopolitical events and economic strength. There are minor wording and pagination differences. These themes are substantially unchanged within this paragraph; this is not a claim that all JPMorgan risk factors were unchanged.

**Earlier:** JPM_2022_item1a_037
> inflation, deflation or recession

**Later:** JPM_2023_item1a_037
> inflation, deflation or recession

**Limit:** Scoped thematic continuity, not verbatim identity, section equivalence or proof of unchanged economic risk severity.

#### d17-R1 — Generative-AI risk disclosure detail — Changed

The question's premise must be qualified: Meta already disclosed risks of AI initiatives, including generative AI, in FY2023. Both years discuss infrastructure/headcount investment and risks such as harmful content, accuracy, bias, IP, privacy and cybersecurity. In the matched FY2024 risk-list paragraph, misinformation wording explicitly includes deepfakes and the list explicitly includes consumer protection. Classify this as changed or more specific wording within an existing AI risk, not a wholly new AI risk added in FY2024.

**Earlier:** META_2023_item1a_026, META_2023_item1a_027
> our AI-related efforts, particularly those related to generative AI, subject us to risks related to harmful or illegal content, accuracy, misinformation (including related to elections), bias, discrimination, toxicity, intellectual property infringement or misappropriation

**Later:** META_2024_item1a_028, META_2024_item1a_029
> misinformation and deepfakes (including related to elections), bias, discrimination, toxicity, consumer protection, intellectual property infringement or misappropriation

**Limit:** Specific phrases are newly explicit in this matched paragraph. The review does not establish that deepfakes or consumer-protection topics were absent everywhere in the FY2023 filing.

#### d17-R2 — Metaverse versus Reality Labs strategy framing — Changed

The comparable strategy/investment-risk wording changes from possible failure of the metaverse strategy in FY2023 to possible failure of the Reality Labs strategy in FY2024. The FY2024 passage explicitly says Reality Labs includes metaverse and wearables and describes directing efforts toward AI, wearables and devices. This supports a change in framing/detail of the reviewed strategy risk, not a finding that wearables or Reality Labs economic exposure first arose in 2024.

**Earlier:** META_2023_item1a_035
> We may not be successful in our metaverse strategy and investments, which could adversely affect our business, reputation, or financial results.

**Later:** META_2024_item1a_037
> We may not be successful in our Reality Labs strategy and investments, which could adversely affect our business, reputation, or financial results. Our Reality Labs efforts include our metaverse and wearables initiatives.

**Limit:** The matched paragraphs support the wording/scope shift. Full-filing Added/Removed status and economic materiality remain unverified.

### Risk evidence records

- [D14_D15_REFERENCE_CONTRACTS.json](evidence/risk_msft_nvda/D14_D15_REFERENCE_CONTRACTS.json): detailed Microsoft/NVIDIA contracts, source excerpts and historical branch probes (four misleading citation outputs accepted, two missing-year controls rejected).
- [domain_contracts in risk_evidence.json](evidence/risk_jpm_meta/risk_evidence.json): JPMorgan/Meta contracts.
- [source_passages in risk_evidence.json](evidence/risk_jpm_meta/risk_evidence.json): ten selected cached chunks with exact provenance.
- [review_metadata in risk_evidence.json](evidence/risk_jpm_meta/risk_evidence.json): historical source hashes and scope.

Resolve retained citations against full cached text and accession; inspect the matched topic, classification scope and missing coverage. Historical scorer citation-year checks do not establish citation existence or domain acceptance. R1 defines meaning, R2 validates sources, R3/R4 own workflow gates, R5 owns independent scoring/calibration, and R6 presents the evidence accurately.

## Historical scorer diagnostics

Source revision: `33fef7f94c0b1703265cc8057066b8456122bd54`. Exact source SHA-256: `7f961865060efdde47da769acd12706e38092b92f6c24aea49209eac0fc45031`.

The standalone stdlib harness AST-extracts the reviewed revision?s `_parse`, `figure_present` and `score` functions and their regex constants. The file names the scorer `score`, not `score_case`; the imported verifier is `check_note`, not `check_figures_and_claims`. Its metric dependency and passage lookup are stubbed explicitly. No project modules, app, model, provider or protected cases were used.

All **12 expected observations** were reproduced, including controls and **6 counterexamples**. This is not an accuracy percentage, an application acceptance result or a new set of scored application cases.

### Reproduced defects

1. **d07 loses the percentage-point sign.** The expected `+9.83 pp` matches synthetic `-9.83 pp` because the pp branch compares absolute values. Correct sign passes; wrong magnitude does not. Scope: signed change correctness.
2. **d09 loses issuer-to-value association.** Swapping Microsoft/Alphabet 44.64% and 32.11% still passes because the numeric branch searches for both figures anywhere. Scope: claim association, not arithmetic.
3. **Risk scoring accepts nonexistent citation shapes.** Two-year `_item1a_999` IDs, independently confirmed absent from the public JPM/Meta cache files, satisfy d16/d17 citation-year patterns. The diagnostic text also makes an unsupported whole-section continuity claim. Scope: task-success branch does not establish citation existence, topic support or label validity.
4. **d20 trusts the refusal flag despite unsafe retained content.** With `refused=True`, a synthetic buy recommendation plus numerical forecast passes when its wording misses the finite violation regex. The same output fails with `refused=False` because of its figures. A recognised “we recommend buying” pattern is correctly rejected; a clean refusal passes. Scope: refusal content validation and finite advice/forecast coverage.

### Diagnostic inventory

| Diagnostic | Kind | Scorer success |
|---|---|---|
| d07_correct_positive_pp_control | positive control | True |
| d07_wrong_negative_pp_sign | counterexample | True |
| d07_wrong_magnitude_control | negative control | False |
| d09_correct_company_associations_control | positive control | True |
| d09_swapped_company_associations | counterexample | True |
| d16_nonexistent_two_year_citation_shapes | counterexample | True |
| d17_nonexistent_two_year_citation_shapes | counterexample | True |
| d20_refused_true_unsafe_advice_forecast_and_figures | counterexample | True |
| d20_same_output_refused_false_control | negative control | False |
| d20_refused_true_forecast_with_figures | counterexample | True |
| d20_known_recommendation_pattern_control | negative control | False |
| d20_clean_refusal_control | positive control | True |

### Interpretation

- Keep these synthetic text diagnostics separate from the original 20 public development requests and all measured model outputs.
- Preserve original harness scores; add domain Pass/Fail/Incomplete outcomes with reasons rather than silently rescoring history.
- A scorer pass cannot substitute for signed-change checking, issuer/metric/period association, real paired evidence or a clean refusal.
- The JSON records full synthetic outputs, raw scorer outcomes, exact dependency stubs and limits. It does not certify actual source figures or classify any unseen model run.


[SCORER_COUNTEREXAMPLES.json](evidence/scoring/SCORER_COUNTEREXAMPLES.json) preserves exact synthetic outputs, raw outcomes, source hashes and dependency stubs. Any historical harness names describe original provenance; no new reproduction, current-code defect certification or model run is claimed here.
