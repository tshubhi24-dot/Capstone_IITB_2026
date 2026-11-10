# Main development risk cases d14 and d15

**Status: final bounded domain reference contracts.** These are actual source-backed development examples, not human annotations, independently accepted R5 gold, protected cases or executed model outputs.

Reviewed Main: `33fef7f94c0b1703265cc8057066b8456122bd54`. Four selected topic pairs use the complete relevant paragraph/sentence text from public cached Item 1A records. Original complete filing boundaries and full-filing eligibility were not independently validated.

## Current contract and scorer gap

Main stores only ticker and two fiscal years for each of these risk questions. The task-success branch at `analystdesk/evaluation.py:105–109` tests whether the output contains Item 1A-style IDs for both years. Six isolated branch probes reproduce the limitation: four citations-only/contradictory outputs pass, while two missing-earlier-citation controls fail. These are diagnostic branch observations, not task results or an accuracy score.

## Filing provenance

| Issuer | FY | Actual annual period | Filed | Accession |

|---|---|---|---|---|

| MSFT | 2023 | 2022-07-01 to 2023-06-30 | 2023-07-27 | 0000950170-23-035122 |

| MSFT | 2024 | 2023-07-01 to 2024-06-30 | 2024-07-30 | 0000950170-24-087843 |

| NVDA | 2023 | 2022-01-31 to 2023-01-29 | 2023-02-24 | 0001045810-23-000017 |

| NVDA | 2024 | 2023-01-30 to 2024-01-28 | 2024-02-21 | 0001045810-24-000029 |

Annual start/end dates are associated through a unique annual USD-revenue context matching the exact accession and submissions reportDate. They describe the issuer fiscal period, not a claim that a risk sentence has its own numerical measurement period. The JSON retains source paths, SHA256 hashes, submission-array indices, accession and primary-document URLs. Excerpt offsets are zero-based characters inside the exact cached passage, with an exclusive end; they are not original HTML page/character locations.

## d14 What changed in Microsoft's risk factors between fiscal 2023 and 2024?

**Source question:** `data/evaluation/dev_cases.jsonl`, line 14.

**Reference answer:** Within the selected Microsoft Item 1A passages, the retained third-party IP paragraph becomes more explicit in FY2024 about copyright and other claims arising from AI training/output and about royalty-bearing data-access/licensing terms [MSFT_2023_item1a_071; MSFT_2024_item1a_081]. This supports Changed wording within that topic, not a claim that AI/IP risk was absent company-wide in FY2023. The matched three-sentence climate/resource/powering-and-cooling paragraph is unchanged after whitespace normalisation [MSFT_2023_item1a_079; MSFT_2024_item1a_090]. These are selected-topic findings; complete Item 1A coverage, economic materiality and any operating-margin cause are not established.

### d14-T1 Third-party IP claims and AI specificity

**Classification:** Changed.

**Finding:** The selected IP-infringement paragraph is retained but becomes more specific in FY2024: it explicitly names current copyright-infringement and other claims arising from AI training/output, and describes royalty-bearing data-access or licensing agreements. FY2023 describes IP-infringement claims and royalty/licensing agreements generically.

**Earlier evidence:** `MSFT_2023_item1a_071`, `data/passages/MSFT_2023.jsonl` line 72; accession `0000950170-23-035122`; text characters 201–1042 (end exclusive).

> Third parties may claim that we infringe their intellectual property.  From time to time, others claim we infringe their intellectual property rights. To resolve these claims, we may enter into royalty and licensing agreements on terms that are less favorable than currently available, stop selling or redesign affected products or services, or pay damages to satisfy indemnification commitments with our customers. Adverse outcomes could also include monetary damages or injunctive relief that may limit or prevent importing, marketing, and selling our products or services that have infringing technologies. We have paid significant amounts to settle claims related to the use of technology and intellectual property rights and to procure intellectual property rights as part of our strategy to manage this risk, and may continue to do so.

**Later evidence:** `MSFT_2024_item1a_081`, `data/passages/MSFT_2024.jsonl` line 82; accession `0000950170-24-087843`; text characters 202–1213 (end exclusive).

> Third parties may claim that we infringe their intellectual property.  From time to time, others claim we infringe their intellectual property rights, including current copyright infringement and other claims arising from AI training and output. To resolve these claims, we may enter into royalty-bearing data access or licensing agreements on terms that are less favorable than currently available, stop selling or redesign affected products or services, or pay damages to satisfy indemnification commitments with our customers. Adverse outcomes could also include monetary damages or injunctive relief that may limit or prevent importing, marketing, and selling our products or services that have infringing technologies. We have paid significant amounts to settle claims related to the use of technology and intellectual property rights and to procure intellectual property rights as part of our strategy to manage this risk, and may continue to do so, which could adversely affect our results of operations.

**Required meaning:** The IP-risk topic exists in both selected years. FY2024 adds AI-training/output claim specificity within this paragraph. Changed disclosure does not by itself prove a newly arising company-wide economic risk, realised loss or margin effect.

**Do not infer:** AI/IP risk was absent from the entire FY2023 filing. AI risk as a whole was newly invented in FY2024. This wording caused an actual operating-margin decline.

**Coverage:** Full selected IP paragraph in each cached record; other AI, cybersecurity, litigation and cross-reference sections are not certified complete.

### d14-T2 Climate resource and powering/cooling costs

**Classification:** Scoped Unchanged.

**Finding:** The three-sentence climate paragraph is identical after whitespace normalisation: uncertainty about long-term effects, environmental/resource cost exposure, and possible powering/cooling cost increases appear in both years. No substantive change is identified within this paired paragraph.

**Earlier evidence:** `MSFT_2023_item1a_079`, `data/passages/MSFT_2023.jsonl` line 80; accession `0000950170-23-035122`; text characters 202–701 (end exclusive).

> The long-term effects of climate change on the global economy and the IT industry in particular are unclear. Environmental regulations or changes in the supply, demand, or available sources of energy or other resources may affect the availability or cost of goods and services, including natural resources, necessary to run our business. Changes in climate where we operate may increase the costs of powering and cooling computer hardware we use to develop software and provide cloud-based services.

**Later evidence:** `MSFT_2024_item1a_090`, `data/passages/MSFT_2024.jsonl` line 91; accession `0000950170-24-087843`; text characters 202–701 (end exclusive).

> The long-term effects of climate change on the global economy and the IT industry in particular are unclear. Environmental regulations or changes in the supply, demand, or available sources of energy or other resources may affect the availability or cost of goods and services, including natural resources, necessary to run our business. Changes in climate where we operate may increase the costs of powering and cooling computer hardware we use to develop software and provide cloud-based services.

**Required meaning:** Climate cost exposure is present in both selected paragraphs. The matched topic paragraph is unchanged after whitespace normalisation. This is a scoped finding, not a statement that every climate disclosure or the entire risk section is unchanged.

**Do not infer:** The climate-risk topic was newly added or expanded based solely on these paragraphs. Unchanged wording proves unchanged real economic exposure. No climate discussion changed anywhere else in the filing.

**Coverage:** Complete matched climate paragraph only; no complete climate-section or full-filing assurance.

### Completion and scoring contract

**Minimum completed answer:** At least one actual supported change must be explained with paired topic evidence. The second reference topic illustrates an acceptable additional finding; no exhaustive-diff claim is permitted.

**Mandatory qualifications:** Name the issuer and compare its own FY2023 and FY2024 filings. Cite authentic same-topic evidence from both years for each asserted comparison. Distinguish disclosure change from new economic exposure or realised loss. State selected-topic coverage and relevant missing/full-section limitations. Do not invent a causal connection to financial performance.

**Alternative answers:** Another true and adequately evidenced topic pair is acceptable. Evaluate its actual sources and meaning; do not require the literal phrases, passage IDs or all topics used by this exemplar.

**Pass meaningful outcome:** A completed answer explains at least one genuine supported change with correct paired evidence, attribution/dates and scope; any retained additional claim is supported or explicitly limited. Exact reference prose and both selected topics are not mandatory.

**Fail meaningful outcome:** A completed answer fabricates or contradicts a mandatory fact, labels an existing risk wholly new without adequate coverage, gives a false paired citation/issuer/year, or asserts unsupported economic causation/advice. A known mandatory violation remains Fail even if completion is also interrupted.

**Incomplete meaningful outcome:** No established mandatory failure, but execution or necessary review is incomplete, a complete comparative answer is absent, or only insufficient evidence is returned although these available source pairs were not examined. Such a cautious limited answer may be publication-safe while still failing to complete this case.

**Disputed or defective case meaningful outcome:** Conflicting source eligibility, genuine materially different paired coverage, extraction damage or a rubric defect must be adjudicated and versioned; do not force a model failure to protect the reference.

## d15 How did NVIDIA's risk factors change from fiscal 2023 to fiscal 2024?

**Source question:** `data/evaluation/dev_cases.jsonl`, line 15.

**Reference answer:** Within the selected NVIDIA export passages, FY2023 describes A800 as an alternative not subject to the then-new licence requirements [NVDA_2023_item1a_069], whereas FY2024 describes updated October 2023 requirements including A800 and an immediate 23 October 2023 licensing notice [NVDA_2024_item1a_085]. This is Changed licensing exposure, not a new overall export-risk topic. In the climate-goal sentence, FY2023 names the 100% renewable-electricity goal for the end of FY2025, while FY2024 refers more generally to sustainability-related goals [NVDA_2023_item1a_045; NVDA_2024_item1a_055]. Both retain reputational/unexpected-cost exposure. This wording change does not prove that a goal was abandoned or achieved. These are selected-topic findings, not a complete filing diff or quantified financial effect.

### d15-T1 Export licensing and the A800 example

**Classification:** Changed.

**Finding:** FY2023 describes A800 as an alternative product not subject to the then-new licence requirements. FY2024 describes October 2023 updated requirements covering products including A800 and records immediate requirements on 23 October 2023 for A100/A800/H100/H800/L40S shipments. The scope of the disclosed licensing exposure changes; export-control risk itself already existed.

**Earlier evidence:** `NVDA_2023_item1a_069`, `data/passages/NVDA_2023.jsonl` line 70; accession `0001045810-23-000017`; text characters 403–1222 (end exclusive).

> The new license requirements also apply to any future NVIDIA integrated circuit achieving certain peak performance and chip-to-chip I/O performance thresholds, as well as any system or board that includes those circuits. There are also now licensing requirements to export a wide array of products, including networking products, destined for certain end users and for certain end uses in China. We are required to transition certain operations out of China (including Hong Kong), which could be costly and time consuming, and adversely affect our research and development and supply and distribution operations, as well as our revenue, during any such transition period. We have engaged with customers in China to provide alternative products not subject to the new license requirements, such as our new A800 offering.

**Later evidence:** `NVDA_2024_item1a_085`, `data/passages/NVDA_2024.jsonl` line 86; accession `0001045810-24-000029`; text characters 403–1273 (end exclusive).

> In October 2023, the USG announced new and updated licensing requirements that became effective in our fourth quarter of fiscal year 2024 for exports to China and Country Groups D1, D4, and D5 (including but not limited to, Saudi Arabia, the United Arab Emirates, and Vietnam, but excluding Israel) of our products exceeding certain performance thresholds, including A100, A800, H100, H800, L4, L40, L40S and RTX 4090. The licensing requirements also apply to the export of products exceeding certain performance thresholds to a party headquartered in, or with an ultimate parent headquartered in, Country Group D5, including China. On October 23, 2023, the USG informed us that the licensing requirements were effective immediately for shipments of our A100, A800, H100, H800, and L40S products. We have not received licenses to ship these restricted products to China.

**Required meaning:** Export licensing is an existing topic in FY2023, not a newly appearing overall risk. The FY2023 A800 alternative and FY2024 A800 licensing treatment differ. FY2024 refers to updated October 2023 requirements; fiscal 2024 is not calendar 2024.

**Do not infer:** NVIDIA had no export-control exposure in FY2023. The new restrictions began only after the FY2024 reporting period. All NVIDIA products or all countries were prohibited. The excerpts quantify a realised revenue or margin loss.

**Coverage:** Selected licensing discussion and its surrounding cached records; no assurance that every restriction or exception in the complete filing is covered.

### d15-T2 Climate-goal risk specificity

**Classification:** Changed.

**Finding:** FY2023 specifically discusses not achieving 100% renewable global electricity by the end of FY2025, together with reputational and unexpected-cost exposure. FY2024 refers more generally to not achieving stated sustainability-related goals while retaining the reputational/cost warning. The selected sentence becomes less specific about the named goal.

**Earlier evidence:** `NVDA_2023_item1a_045`, `data/passages/NVDA_2023.jsonl` line 46; accession `0001045810-23-000017`; text characters 560–817 (end exclusive).

> We may not achieve our stated goal to source 100% of our global electricity use from renewable energy by the end of fiscal year 2025, which could harm our reputation, or we may incur additional,  24 Table of Contents unexpected costs to achieve such a goal.

**Later evidence:** `NVDA_2024_item1a_055`, `data/passages/NVDA_2024.jsonl` line 56; accession `0001045810-24-000029`; text characters 403–563 (end exclusive).

> We may not achieve our stated sustainability-related goals, which could harm our reputation, or we may incur additional, unexpected costs to achieve such goals.

**Required meaning:** The risk of missing environmental/sustainability goals is present in both selected years. FY2023 names a specific renewable-electricity target; FY2024 uses broader sustainability-goal wording in this selected sentence. Loss of specificity in this paragraph does not establish target abandonment, achievement or disappearance elsewhere.

**Do not infer:** NVIDIA abandoned or achieved the renewable-energy goal. The renewable target was absent from the whole FY2024 filing. The underlying climate risk was removed.

**Coverage:** Selected stated-goal sentence and continuation; not the complete sustainability disclosures or actual progress against goals.

### Completion and scoring contract

**Minimum completed answer:** At least one actual supported change must be explained with paired topic evidence. The second reference topic illustrates an acceptable additional finding; no exhaustive-diff claim is permitted.

**Mandatory qualifications:** Name the issuer and compare its own FY2023 and FY2024 filings. Cite authentic same-topic evidence from both years for each asserted comparison. Distinguish disclosure change from new economic exposure or realised loss. State selected-topic coverage and relevant missing/full-section limitations. Do not invent a causal connection to financial performance.

**Alternative answers:** Another true and adequately evidenced topic pair is acceptable. Evaluate its actual sources and meaning; do not require the literal phrases, passage IDs or all topics used by this exemplar.

**Pass meaningful outcome:** A completed answer explains at least one genuine supported change with correct paired evidence, attribution/dates and scope; any retained additional claim is supported or explicitly limited. Exact reference prose and both selected topics are not mandatory.

**Fail meaningful outcome:** A completed answer fabricates or contradicts a mandatory fact, labels an existing risk wholly new without adequate coverage, gives a false paired citation/issuer/year, or asserts unsupported economic causation/advice. A known mandatory violation remains Fail even if completion is also interrupted.

**Incomplete meaningful outcome:** No established mandatory failure, but execution or necessary review is incomplete, a complete comparative answer is absent, or only insufficient evidence is returned although these available source pairs were not examined. Such a cautious limited answer may be publication-safe while still failing to complete this case.

**Disputed or defective case meaningful outcome:** Conflicting source eligibility, genuine materially different paired coverage, extraction damage or a rubric defect must be adjudicated and versioned; do not force a model failure to protect the reference.

## Final evidence and implementation boundary

The two reference contracts are complete as bounded domain content. They do not replace the questions in Main or modify the scorer. A proper scoring adapter must check comparative meaning, paired evidence, source association, permitted alternatives and completion separately. R1 owns domain meaning, R2 source/coverage validation, R3/R4 workflow and gates, R5 independent scoring/calibration, and R6 accurate presentation.

A safe limited answer can correctly refuse an unsupported New/Removed classification yet remain Incomplete for the broad research task. A known false claim remains Fail even if a later outage also prevents completion. Case success is separate from exact-note approval and publication.

Reproduction and detailed provenance are in `D14_D15_REFERENCE_CONTRACTS.json`; this local review leaves application source, development cases, runtime data and all protected assets unchanged.
