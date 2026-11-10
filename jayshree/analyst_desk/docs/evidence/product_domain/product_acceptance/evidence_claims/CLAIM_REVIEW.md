# Historical C2 note narrative and causality review

**Outcome: needs correction and fresh checks. The note remains unapproved.** This review does not change the draft or its original failed critic result.

The selected note is the historical MSFT/GOOGL FY2022–FY2024 C2 output from `42e2298`, not a run of latest Main `33fef7f`. Evidence is limited to the ten captured cited passages. No original complete filing, new model response, credential or protected evaluation content was inspected.

## What the original result means

The preserved result is `check.ok=false`, `verified=7`, `total=7`, and judge `supported=2`, `checked=8`, with six issues. The six tagged margin ratios and the quoted 17% account for the detected numeric checks. This narrative review does not independently recompute those ratios or approve their input eligibility. Eight judge line-items are not eight atomic claims: compound driver and risk sentences contain several assertions, while two source-list lines were also judged.

The original six issues include false or overbroad objections against the full captured sources, but deterministic evidence truncation explains important omissions. Historical source provides only the first 900 characters of the first two citations per line: Microsoft’s 17% sentence begins at character 1067, and Alphabet’s FY2024 passage is the third citation on its driver line. Neither reaches the reconstructed judge evidence. This is not proof the judge ignored text it received. The two risk paragraphs counted as supported still lack captured paired-year topic evidence. Preserve the raw failure and separately record the adjudication; do not turn this manual review into a new automatic critic pass.

## Essential corrections

1. Retain Microsoft’s 17% statement with precise scope: management reports gross-margin dollars increased $25.0 billion, or 17%. The source explicitly states this; it is not a 17-percentage-point gross-margin-rate increase.

2. Remove or support the FY2023 productivity-cost explanation and the causal bridge to Microsoft’s operating-margin decline. The captured passage supports Cloud cost-of-revenue growth and segment revenue growth only.

3. Separate Alphabet’s FY2024 Google Services and Cloud drivers. Services compensation fell; Cloud compensation rose. Remove the unverified G&A reduction and FY2023 workforce/cost-management explanations unless the correct passages are retrieved.

4. Replace New/Added/Expanded/Unchanged risk classifications with supported current-year descriptions until comparable earlier topic coverage is reviewed. Opening risk paragraphs do not establish absence elsewhere.

5. Limit negative causal-link claims to the captured excerpts. Do not claim a complete-filing absence finding from a small capture.

## Verdict meanings and counting

`Supported`: direct captured evidence within scope. `Partial`: a supported component with an unproved component, bridge or scope. `Unsupported`: contradicted or exceeding the direct meaning. `Unverified`: necessary evidence was not captured; it is not proof of falsehood.

Atomic narrative review: 33 entries; Supported 14, Partial 7, Unsupported 0, Unverified 12. This decomposition is diagnostic, not an acceptance score or a replacement for the original 2/8 automatic result. Missing evidence is marked Unverified rather than treating the assertion as factually false.

## Atomic claim record

### C01 Microsoft drivers

**Assertion:** FY2023 cost of revenue rose with Microsoft Cloud growth.

**Verdict:** Supported.

**Captured evidence:** `MSFT_2023_item7_020`: “Cost of revenue increased $3.2 billion or 5% driven by growth in Microsoft Cloud”

**Reason:** Direct management statement. This is narrower than the draft’s operating-margin explanation.

**Needed fix:** Attribute this to management and retain its cost-of-revenue scope.

### C02 Microsoft drivers

**Assertion:** Increased productivity-segment costs explain the FY2023 operating-margin decline.

**Verdict:** Unverified.

**Captured evidence:** `MSFT_2023_item7_020`: “Productivity and Business Processes revenue increased driven by Office 365 Commercial and LinkedIn.”

**Reason:** The captured paragraph discusses this segment’s revenue, not its costs. It does not establish the asserted cost driver.

**Needed fix:** Remove the productivity-cost attribution or retrieve the relevant expense and operating-income evidence.

### C03 Microsoft drivers

**Assertion:** The FY2023 operating-margin dip was caused by the cited cloud/productivity cost increases, partially offset by revenue growth.

**Verdict:** Partial.

**Captured evidence:** `MSFT_2023_item7_020`: “Revenue increased $13.6 billion or 7%” `MSFT_2023_item7_020`: “Cost of revenue increased $3.2 billion or 5%”

**Reason:** Revenue and cost growth are supported, but the excerpt does not bridge them to operating-margin movement or cover operating expenses. Total revenue growing faster than cost of revenue alone does not explain an operating-margin decline.

**Needed fix:** State the observed margin movement separately; report these management-attributed facts without asserting the missing causal bridge.

### C04 Microsoft drivers

**Assertion:** FY2024 revenue grew across Intelligent Cloud, Productivity and Business Processes, and More Personal Computing.

**Verdict:** Supported.

**Captured evidence:** `MSFT_2024_item7_017`: “Revenue increased $33.2 billion or 16% driven by growth across each of our segments.” `MSFT_2024_item7_017`: “Intelligent Cloud revenue increased driven by Azure.” `MSFT_2024_item7_017`: “Productivity and Business Processes revenue increased driven by Office 365 Commercial.” `MSFT_2024_item7_017`: “More Personal Computing revenue increased driven by Gaming.”

**Reason:** All named segments and their revenue drivers are explicit in the captured passage.

**Needed fix:** Retain with management attribution; do not automatically identify revenue growth as the complete operating-margin explanation.

### C05 Microsoft drivers

**Assertion:** FY2024 gross margin increased by 17%.

**Verdict:** Supported.

**Captured evidence:** `MSFT_2024_item7_017`: “Gross margin increased $25.0 billion or 17% driven by growth across each of our segments.”

**Reason:** The actual captured text states this exactly. The original critic’s claim that the passage does not mention 17% is false. Here the filing discusses an increase in the gross-margin dollar amount, not a 17-point margin-rate increase.

**Needed fix:** Clarify: “Management reported gross-margin dollars increased $25.0 billion, or 17%.” Do not interpret this as a gross-margin-rate change.

### C06 Microsoft drivers

**Assertion:** Broad FY2024 revenue growth establishes why Microsoft’s operating-margin rate rebounded.

**Verdict:** Partial.

**Captured evidence:** `MSFT_2024_item7_017`: “Revenue increased $33.2 billion or 16% driven by growth across each of our segments.” `MSFT_2024_item7_017`: “Gross margin increased $25.0 billion or 17% driven by growth across each of our segments.”

**Reason:** Revenue and gross-profit dollar growth are direct evidence; the excerpt does not fully reconcile the operating-income-to-revenue ratio or operating-expense leverage.

**Needed fix:** Separate the code-derived margin trend from management’s stated revenue and gross-profit drivers, or add the operating-expense evidence.

### C07 Alphabet drivers

**Assertion:** In FY2022 revenue grew while costs and operating expenses grew faster, accompanying lower operating margin.

**Verdict:** Supported.

**Captured evidence:** `GOOGL_2022_item7_023`: “Consolidated revenues | $257,637 | $282,836 | $25,199 | 10%” `GOOGL_2022_item7_023`: “Cost of revenues | $110,939 | $126,203 | $15,264 | 14%” `GOOGL_2022_item7_023`: “Operating expenses | $67,984 | $81,791 | $13,807 | 20%” `GOOGL_2022_item7_023`: “Operating margin | 31% | 26% | (5)%”

**Reason:** The consolidated table supports this accounting description. It does not identify an underlying business cause for those expenses.

**Needed fix:** Use the accounting description, with the comparison identified as FY2021 to FY2022; avoid inventing the underlying cause.

### C08 Alphabet drivers

**Assertion:** FY2023 was marked by workforce reductions.

**Verdict:** Unverified.

**Captured evidence:** `GOOGL_2023_item7_000`: “The following section generally discusses 2023 results compared to 2022 results.”

**Reason:** The cited FY2023 excerpt is an introduction and reporting-structure description. It contains no workforce-reduction statement.

**Needed fix:** Remove the assertion or retrieve and cite the actual severance/headcount discussion. Do not infer reductions merely from a cross-reference.

### C09 Alphabet drivers

**Assertion:** FY2023 cost-management initiatives explain the operating-margin improvement.

**Verdict:** Unverified.

**Captured evidence:** `GOOGL_2023_item7_000`: “Alphabet is a collection of businesses — the largest of which is Google.”

**Reason:** No cost-management initiative or causal bridge appears in the captured FY2023 source.

**Needed fix:** Remove the explanation or supply the corresponding management evidence and ratio reconciliation.

### C10 Alphabet drivers

**Assertion:** FY2024 Google Services operating income increased, primarily driven by revenue growth.

**Verdict:** Supported.

**Captured evidence:** `GOOGL_2024_item7_048`: “Google Services operating income increased $25.4 billion from 2023 to 2024.” `GOOGL_2024_item7_048`: “The increase in operating income was primarily driven by an increase in revenues, partially offset by increases in content acquisition costs and TAC.”

**Reason:** Direct segment-level management explanation.

**Needed fix:** Retain as a Google Services operating-income explanation, including offsets.

### C11 Alphabet drivers

**Assertion:** FY2024 Google Cloud operating income increased, primarily driven by revenue growth.

**Verdict:** Supported.

**Captured evidence:** `GOOGL_2024_item7_048`: “Google Cloud operating income increased $4.4 billion from 2023 to 2024.” `GOOGL_2024_item7_048`: “The increase in operating income was primarily driven by an increase in revenues, partially offset by increases in usage costs for technical infrastructure as well as employee compensation expenses, largely driven by headcount growth.”

**Reason:** Direct segment-level management explanation, with material cost offsets.

**Needed fix:** Retain as a Google Cloud operating-income explanation, including infrastructure and compensation offsets.

### C12 Alphabet drivers

**Assertion:** Reduced employee compensation contributed to FY2024 Google Services operating-income growth.

**Verdict:** Supported.

**Captured evidence:** `GOOGL_2024_item7_048`: “Additionally, a reduction in employee compensation expenses contributed to the increase in operating income.”

**Reason:** The sentence belongs to Google Services, immediately before the Google Cloud heading.

**Needed fix:** Make the Services scope explicit.

### C13 Alphabet drivers

**Assertion:** Reduced employee compensation is an unqualified driver alongside the Services and Cloud revenue explanations.

**Verdict:** Partial.

**Captured evidence:** `GOOGL_2024_item7_048`: “increases in usage costs for technical infrastructure as well as employee compensation expenses, largely driven by headcount growth.”

**Reason:** The captured Services reduction is supported, but Cloud compensation increased. The draft does not explicitly say Cloud compensation fell, so it would be excessive to call that an established false claim. Its unqualified combined wording needs narrowing; a consolidated compensation decline is not established here.

**Needed fix:** Separate Services and Cloud. Preserve Services compensation reduction and Cloud compensation increase; do not infer a group-wide compensation-reduction claim.

### C14 Alphabet drivers

**Assertion:** Reduced general and administrative expenses contributed to FY2024 margin expansion.

**Verdict:** Unverified.

**Captured evidence:** `GOOGL_2024_item7_048`: “Alphabet-level activities included substantially all of the charges related to employee severance and our office spa
ce charges.”

**Reason:** The passage mentions charges but supplies no general-and-administrative expense reduction or comparison establishing the assertion.

**Needed fix:** Remove the G&A claim or obtain the correct consolidated expense evidence.

### C15 Alphabet drivers

**Assertion:** The cited segment explanations establish the complete cause of Alphabet’s consolidated FY2024 operating-margin expansion.

**Verdict:** Partial.

**Captured evidence:** `GOOGL_2024_item7_048`: “Google Services operating income increased $25.4 billion from 2023 to 2024.” `GOOGL_2024_item7_048`: “Google Cloud operating income increased $4.4 billion from 2023 to 2024.” `GOOGL_2024_item7_048`: “Other Bets operating loss increased $349 million from 2023 to 2024.”

**Reason:** The passage supports substantial segment operating-income drivers, not by itself the full consolidated margin-ratio reconciliation; Other Bets and Alphabet-level activities are also relevant.

**Needed fix:** Label the segment drivers and separate them from the code-derived consolidated margin change unless the full bridge is supplied.

### C16 Microsoft risk comparison

**Assertion:** FY2024 Microsoft disclosure discusses IP claims arising from AI training and output.

**Verdict:** Supported.

**Captured evidence:** `MSFT_2024_item1a_081`: “including current copyright infringement and other claims arising from AI training and output.”

**Reason:** Direct current-year disclosure.

**Needed fix:** Retain the current-year statement.

### C17 Microsoft risk comparison

**Assertion:** The AI-related IP risk was newly added in FY2024.

**Verdict:** Unverified.

**Captured evidence:** `MSFT_2023_item1a_000`: “We face intense competition across all markets for our products and services, which may lead to lower revenue or operating margins.”

**Reason:** The captured FY2023 source is the opening competition passage, not comparable IP/AI coverage. Its silence cannot establish prior-year absence.

**Needed fix:** Use “FY2024 discloses…” and mark change classification insufficiently evidenced until comparable earlier coverage is reviewed.

### C18 Microsoft risk comparison

**Assertion:** FY2024 climate disclosure identifies possible resource and powering/cooling cost effects.

**Verdict:** Supported.

**Captured evidence:** `MSFT_2024_item1a_090`: “Environmental regulations or changes in the supply, demand, or available sources of energy or other resources may affect the availability or cost of goods and services” `MSFT_2024_item1a_090`: “Changes in climate where we operate may increase the costs of powering and cooling computer hardware”

**Reason:** Direct conditional risk statement; not evidence that these costs actually rose.

**Needed fix:** Retain the conditional wording and current-year scope.

### C19 Microsoft risk comparison

**Assertion:** Climate-change risk was expanded in FY2024.

**Verdict:** Unverified.

**Captured evidence:** No direct paired or assertion-specific evidence was captured.

**Reason:** No comparable FY2023 climate-risk passage or reviewed section coverage was captured.

**Needed fix:** Do not classify Expanded/Changed without the paired evidence and relocation/coverage check.

### C20 Microsoft risk comparison

**Assertion:** Competition, IP, source-code leakage and pandemic risks were updated with broader results-of-operations language.

**Verdict:** Unverified.

**Captured evidence:** `MSFT_2024_item1a_081`: “Unauthorized access to or disclosure of source code or other intellectual property also could increase the security risks” `MSFT_2024_item1a_090`: “Measures to contain a global pandemic may intensify other risks described in these Risk Factors.”

**Reason:** Fragments show some FY2024 topics, but the corresponding prior-year passages and FY2024 competition comparison are absent.

**Needed fix:** Split into current-year supported topics or retrieve the paired passages before asserting broader language.

### C21 Alphabet risk comparison

**Assertion:** FY2024 Alphabet disclosure describes manufacturing/supply-chain reliance on contract manufacturers and third parties.

**Verdict:** Supported.

**Captured evidence:** `GOOGL_2024_item1a_020`: “We rely on contract manufacturers to manufacture or assemble our devices as well as servers and networking equipment” `GOOGL_2024_item1a_020`: “We rely on third parties to supply components and distribute our products and services.”

**Reason:** Direct current-year evidence.

**Needed fix:** Retain the current-year disclosure statement.

### C22 Alphabet risk comparison

**Assertion:** Manufacturing and supply-chain risk was a new FY2024 risk factor.

**Verdict:** Unverified.

**Captured evidence:** `GOOGL_2023_item1a_000`: “We generate a significant portion of our revenues from advertising.”

**Reason:** The sole earlier-year excerpt concerns advertising, not supply chain or complete Item 1A coverage.

**Needed fix:** Remove “new/introduced/added” or retrieve comparable earlier supply-chain coverage and confirm it was absent rather than relocated.

### C23 Alphabet risk comparison

**Assertion:** Advertising risks remained substantively consistent with only minor wording changes.

**Verdict:** Unverified.

**Captured evidence:** `GOOGL_2023_item1a_000`: “Reduced spending by advertisers, a loss of partners, or new and existing technologies that block ads online”

**Reason:** Earlier-year advertising evidence exists, but corresponding FY2024 advertising evidence is not captured.

**Needed fix:** Do not classify Unchanged/minor change without a comparable later-year passage.

### C24 Alphabet risk comparison

**Assertion:** Device-access, privacy/security and operating-results-fluctuation risks remained consistent with minor wording changes.

**Verdict:** Unverified.

**Captured evidence:** No direct paired or assertion-specific evidence was captured.

**Reason:** No paired topic passages for those assertions are captured.

**Needed fix:** Remove these comparisons or obtain and review both years’ topic evidence separately.

### C25 Risk-change limitations

**Assertion:** The AI risk is new and aligns with Microsoft’s increased focus on AI.

**Verdict:** Partial.

**Captured evidence:** `MSFT_2024_item1a_081`: “claims arising from AI training and output.”

**Reason:** Current AI/IP exposure is supported; newness and increased company focus are not established by this captured evidence.

**Needed fix:** Keep only the current disclosure or independently support both the change and company-focus assertion.

### C26 Risk-change limitations

**Assertion:** The captured AI/IP disclosure establishes no actual operating-margin effect.

**Verdict:** Supported.

**Captured evidence:** `MSFT_2024_item1a_081`: “which could adversely affect our results of operations.”

**Reason:** The captured source states a possible future risk and no measured operating-margin attribution.

**Needed fix:** Limit the conclusion explicitly to the captured excerpt; do not claim the complete filing was searched.

### C27 Risk-change limitations

**Assertion:** Expanded climate risk reflects broader environmental considerations affecting costs.

**Verdict:** Partial.

**Captured evidence:** `MSFT_2024_item1a_090`: “The long-term effects of climate change on the global economy and the IT industry in particular are unclear.”

**Reason:** Potential environmental/cost exposure is supported; the claimed year-over-year expansion is not.

**Needed fix:** Remove “expanded” and preserve the conditional present-year cost-risk description.

### C28 Risk-change limitations

**Assertion:** The captured climate passage lacks direct attribution of an observed operating-margin fluctuation to climate change.

**Verdict:** Supported.

**Captured evidence:** `MSFT_2024_item1a_090`: “Changes in climate where we operate may increase the costs of powering and cooling computer hardware”

**Reason:** Only hypothetical potential costs are discussed; no measured operating-margin effect appears in this passage. The note correctly avoids the positive causal inference.

**Needed fix:** Retain the note’s refusal to infer causality, with scope limited to the captured passage.

### C29 Risk-change limitations

**Assertion:** Alphabet’s added supply-chain risk corresponds with operational complexities.

**Verdict:** Partial.

**Captured evidence:** `GOOGL_2024_item1a_020`: “We face a number of risks related to manufacturing and supply chain management, which could affect our ability to supply both our products and our services.”

**Reason:** Present operational dependencies are supported; added/new is unverified.

**Needed fix:** Use the current-year risk description without an unsupported change label.

### C30 Risk-change limitations

**Assertion:** No causal link between the described risks and margin movement is established by the captured excerpts.

**Verdict:** Supported.

**Captured evidence:** No direct paired or assertion-specific evidence was captured.

**Reason:** None of the ten captured excerpts directly attributes the reported operating-margin movements to these risk-disclosure changes. This is an evidence-scope observation, not a full-filing absence finding.

**Needed fix:** Say “The captured excerpts do not establish…” rather than “the available filings establish no link.”

### C31 Risk-change limitations

**Assertion:** The complete available filings contain no explicit causal connection between risk changes and operating margins.

**Verdict:** Unverified.

**Captured evidence:** No direct paired or assertion-specific evidence was captured.

**Reason:** Only ten captured excerpts were reviewed; original complete filings and uncaptured passages were not inspected.

**Needed fix:** Narrow the statement to captured evidence or perform and document a broader review.

### C32 Risk-change limitations

**Assertion:** The captured MD&A passages contain operational revenue, cost and segment operating-income drivers.

**Verdict:** Supported.

**Captured evidence:** `MSFT_2024_item7_017`: “Cost of revenue increased $8.3 billion or 13% driven by growth in Microsoft Cloud and Gaming” `GOOGL_2024_item7_048`: “Google Services operating income increased $25.4 billion from 2023 to 2024.”

**Reason:** Direct evidence, with the accounting-level and segment boundaries described above.

**Needed fix:** Retain with management attribution and avoid calling every item a verified consolidated margin cause.

### C33 Conclusion

**Assertion:** Disclosures evolved with new or expanded AI, climate and supply-chain risks.

**Verdict:** Unverified.

**Captured evidence:** No direct paired or assertion-specific evidence was captured.

**Reason:** This repeats unverified comparative classifications C17/C19/C22. Repetition does not add paired evidence.

**Needed fix:** Replace with supported current-year risk topics and an explicit insufficient-comparative-evidence limitation.

## Original critic adjudication

### J01

**Original objection or result:** Microsoft operating-margin percentages do not appear in the cited narrative passages.

**Adjudication:** Wrong verification route for the tagged ratios; not evidence that the ratios are wrong.

Six ratios carry calc tags and the recorded code check reports all detected values verified. Their numerical source/period validation belongs to the separate financial audit. Narrative passages need not reproduce the computed ratio. Preserve the raw critic result; do not transform this adjudication into independent financial approval.

### J02

**Original objection or result:** Alphabet FY2023 and FY2024 margin percentages are absent from the narrative passages.

**Adjudication:** Same route mismatch as J01.

The figures are tagged code-derived ratios. Absence of the exact derived display percentage from an MD&A excerpt is not by itself a valid rejection. Separate source eligibility and arithmetic still need their own verification.

### J03

**Original objection or result:** The Microsoft passages do not mention gross margin increasing by 17% in FY2024.

**Adjudication:** Factually false objection against the captured passage.

MSFT_2024_item7_017 explicitly says “Gross margin increased $25.0 billion or 17%”. Historical source limits each passage to 900 characters; the sentence starts at zero-based offset 1067, so reconstructed critic evidence excludes it. This is an evidence-assembly omission, not proof that the source lacks the figure or that the judge ignored text it received. The compound sentence remains only partly supported because its FY2023 cost explanation and operating-margin causal bridge are not established.

### J04

**Original objection or result:** The Alphabet passages lack detailed FY2023/FY2024 margin-improvement and cost-management information.

**Adjudication:** Partly justified, but overbroad for FY2024.

The FY2023 excerpt is insufficient. The FY2024 passage does directly explain Services and Cloud operating-income changes and Services compensation reduction. It does not show G&A reduction; Cloud compensation increased. The driver line cites FY2022, FY2023 and FY2024 in that order, while historical source supplies only the first two cited passages: reconstructed critic evidence excludes FY2024 altogether. Do not discard the supported FY2024 detail or claim the model rejected evidence it actually saw.

### J05

**Original objection or result:** Microsoft bibliography entry is too broad to be a supported claim.

**Adjudication:** Bibliographic metadata was mistaken for a substantive assertion.

A source-list entry is not an independent business assertion requiring entailment. Citation existence, year/section provenance and sufficiency should be checked, but lack of a substantive proposition is not a false business claim.

### J06

**Original objection or result:** Alphabet bibliography entry is too broad to be a supported claim.

**Adjudication:** Same bibliographic category error as J05.

Exclude the source-list label from the semantic assertion denominator while retaining provenance/citation validation.

### J07

**Original objection or result:** The two risk paragraphs were counted as supported by the original 2-of-8 result.

**Adjudication:** Current disclosure presence is supported; comparative classifications remain unverified.

Neither earlier-year opening excerpt supplies the comparable AI/climate/supply-chain topic coverage. A positive compound verdict cannot establish newness, expansion or unchanged wording.

## Review and next-action boundary

This is a local read-only evidence review. It creates no approval, edited note, new model verdict or publication. A corrected exact draft needs fresh financial validation and complete claim review before the analyst makes the separate final-note decision. Full-filing risk-change conclusions require appropriate paired evidence and coverage, not invented corrections or a manufacture of lessons.

The accompanying `CLAIM_REVIEW.json` preserves the original check, source hashes, atomic claims and adjudications. Captured input files remain unchanged.
