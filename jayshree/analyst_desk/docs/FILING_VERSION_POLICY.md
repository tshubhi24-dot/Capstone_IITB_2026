# Analyst Desk Filing Version Policy

**Status:** Proposed policy for review. Team adoption, implementation and verification remain pending.

## Purpose and proposed defaults

The same company's financial figure for the same fiscal period can appear differently in later filings. Analyst Desk must identify which version it uses, preserve the alternatives and avoid mixing incompatible inputs.

For the historical FY2022-FY2024 project, propose **original-as-reported** as the default: reproduce the selected year's original annual filing using a frozen source snapshot. This supports a traceable historical account linked to the filing's financial statements and commentary. It does not imply that original figures are always the best basis for a current comparison.

A **later-reviewed presentation** may be used when explicitly requested or needed for a consistent comparison, after the supporting statements and explanation have been reviewed. Name this basis in the approved plan. It means the most recent eligible, reviewed presentation within the recorded snapshot and knowledge cutoff, not an unqualified claim to the latest SEC information.

Known non-reliance or a confirmed error correction affecting the selected figures overrides routine default use: retain originals as historical evidence, but do not treat them as reliable support for a current financial conclusion. Use reviewed corrected inputs under the approved basis, or hold the affected comparison.

## Meaning of version labels

| Label | Meaning and use |
|---|---|
| Original as reported | The value in the issuer's original annual filing for the target period. The earliest value found in an incomplete cache is not sufficient proof of this status. |
| Later reported value | A value for the same target period presented in a later filing. A difference alone does not establish its cause or make it a confirmed restatement. |
| Confirmed error correction or restatement | Apply this label only when supported by the issuer's disclosure or relevant audit evidence. Identify the affected figures, periods and explanation. |
| Recast or presentation change | A supported change in classification, accounting presentation, reporting perimeter or similar basis. Preserve the issuer's description; do not automatically call it an error. |
| Amended filing | A filing such as 10-K/A. Inspect what it amends; an amendment limited to governance disclosures does not automatically replace financial statements. |

Use "later reported difference; reason not yet verified" when the classification is uncertain. Do not infer fraud, worsening business performance or a new economic event from a version difference alone.

## Version selection and evidence rules

1. Record the selected basis in the plan: original-as-reported or later-reviewed presentation, target periods, source snapshot identifier and any knowledge cutoff. Preserve the cutoff separately from the retrieval date. For an as-of request, exclude filings not available by that cutoff from the calculation.
2. Identify each fact by company, concept or statement label, actual reporting dates, currency, scale, operations/accounting basis, filing accession, form, filing date and source location. Retain the source file or cached response identifier and checksum. A bare fiscal year and number are insufficient.
3. Verify the original annual filing from the filing record and statement. Inspect all relevant cached versions, including applicable amendments and later comparative statements. Do not decide authority solely by earliest/latest filing date, array order or a different numeric value. Unresolved duplicate or same-date conflicts must be reviewed.
4. Preserve the version chain and the source explanation. Keep intermediate changes even if the newest value equals the original. A later filing with an unchanged amount remains a separate source record. Do not overwrite the earlier evidence when the cache is refreshed.
5. An amendment affects only the information it actually changes. A later annual filing may present revised prior-period figures without a separate amendment to the original annual filing. Confirm the affected statement, period and basis rather than treating every amendment as a financial correction.
6. If an original filing or needed later presentation is unavailable or unreviewed, state that limitation. Do not label the earliest cached value original, the latest cached value authoritative, or an unexplained difference a restatement.

A later filing may supply a figure for a covered earlier year. Record both the target financial period and the source filing period. Using that evidence does not silently add the later financial year to the research question; its source version must be covered by the approved snapshot and plan.

## Consistent calculations and interpretation

Use the same reviewed statement presentation for related calculation inputs wherever possible. Match company, operations, dates, units and accounting basis. When inputs come from different filings, demonstrate compatibility before calculating; unresolved compatibility makes the result unavailable.

For original-as-reported year comparisons, check whether the original presentations remain comparable. If definitions or reporting perimeter changed, disclose the difference and withhold an unsupported like-for-like growth or margin conclusion. Offer a later-reviewed comparison when the evidence supports it.

For later-reviewed mode, prefer compatible comparative columns from the same reviewed presentation. Do not combine a revised revenue denominator with an earlier income numerator simply because both carry the same fiscal-year label.

Different companies need not have the same filing date or accession. Apply the approved basis and cutoff consistently to each company and disclose the selected filings. Do not require a single shared document across companies.

Calculate all ratios and version differences in code from unrounded inputs. Recheck every selected value against its specific filing and source context. Apply the existing bank metric and fiscal-period/unit rules; a version change does not resolve an incompatible metric or period.

A same-period change caused by a new reporting presentation is a source-version change, not year-to-year business growth. Financial interpretations must follow the supported explanation. Link commentary to the appropriate source version; original management commentary does not automatically explain a later recast figure.

## Worked numerical examples

All figures, companies and filing dates below are hypothetical. They illustrate the proposed rules and are not reported company results.

### One period with two presentations

Both presentations concern the same company's FY2023. Amounts are USD millions.

| Figure | Original filing dated 15 February 2024 | Later presentation dated 20 February 2025 |
|---|---|---|
| FY2023 revenue | 100 | 95 |
| FY2023 operating income | 20 | 18 |
| FY2023 operating margin | 20 / 100 x 100 = 20.00% | 18 / 95 x 100 = 18.95% |

The later presentation changes the calculated margin by **-1.05 percentage points** after rounding the change from unrounded ratios. This concerns two presentations of FY2023; it is not a move from FY2023 to FY2024 performance.

Using the original income of 20 with the later revenue of 95 produces **21.05%**. That mixes incompatible versions in this example and must be rejected. The approved basis determines which compatible pair is used.

If the later presentation corrects an error and the original figures should no longer be relied on, the original pair may be shown as labelled historical evidence. It must not support a current financial conclusion.

### A growth comparison affected by the earlier version

Suppose FY2024 revenue is 110. Comparing it with FY2023 revenue of 100 gives **10.00%**; comparing it with the later-presented FY2023 revenue of 95 gives **15.79%**.

Both arithmetic results are reproducible, but the appropriate comparison depends on compatible reporting bases. If the FY2024 statement presents FY2023 at 95 on a reviewed consistent basis, the later-reviewed comparison uses 95. Do not silently choose whichever growth rate looks preferable or describe an incompatible original-basis result as like-for-like growth.

### Knowledge cutoff and nonfinancial amendments

For an as-of date of 31 December 2024, the hypothetical filing dated 20 February 2025 is not eligible for the historical calculation. A present-day caveat about a subsequently corrected historical figure must be separately labelled and must not enter the historical calculation or evaluation answer.

A hypothetical 10-K/A that only adds executive-compensation disclosures leaves the existing financial figure unchanged. Preserve the amendment and its scope; do not assume it revises revenue.

## Messages to the analyst

### Original basis with a later difference

**Original filing basis with a later reported difference.**

This note uses FY2023 figures from the original filing dated 15 February 2024: revenue USD 100 million and operating income USD 20 million. A later filing dated 20 February 2025 presents USD 95 million and USD 18 million for the same period. The later presentation and its explanation require review before use as an alternative comparison basis.

Use this message only when that review is actually pending. If the cause is confirmed, state the supported reason and source. If non-reliance applies, use the affected-figure message below instead of presenting the original as a reliable current result.

### Approved later presentation

**Later-reviewed presentation selected.**

For this approved comparison, FY2023 uses the presentation in the filing dated 20 February 2025: revenue USD 95 million, operating income USD 18 million and calculated operating margin 18.95%. The original figures remain visible in the version history with their sources.

### Unresolved or unreliable evidence

**Filing-version comparison unavailable.**

The available records contain an unresolved version difference, incompatible inputs or an affected original figure that should no longer be relied on. The comparison remains on hold until compatible reviewed evidence is available. Historical figures may be shown with clear labels, but will not be presented as a verified current result.

Offer a supported reviewed basis or a clearly labelled historical request where appropriate. Changing basis, cutoff or source snapshot requires approval of the revised plan. A changed final note requires fresh checks and exact-note approval.

## Persistence and acceptance rules

Keep earlier approved notes and their source references identifiable. A cache refresh, revised source or new note must not silently rewrite their figures or approval record. Record a correction or superseding note as a separate version linked to the earlier note; follow the adopted privacy and retention policy rather than inventing a new deletion rule here.

Where possible, show the original amount, selected later amount, source dates, reason and calculated difference together. If no later difference is detected, say "no difference detected in the reviewed snapshot"; do not claim that no later filing or correction exists anywhere.

Hold a completed comparison when the selected original is known to be unreliable for the intended conclusion, the required version is missing, classification is unresolved in a way that affects comparability, or inputs cannot be reconciled. Human approval does not resolve those evidence failures.

For evaluation, R5 fixes the source snapshot, cutoff, version basis and expected answer before scored runs. A changed dataset or policy requires an explicit new evaluation version. Do not introduce later filings into an earlier as-of answer or silently change expected values after seeing model outputs.

## Acceptance examples

These are development examples, not protected held-out questions or completed verification evidence.

| Case | Expected behaviour |
|---|---|
| Default historical FY2023 question | Identify the actual original filing and use its compatible inputs, with source and version disclosures. |
| Latest cached value differs from the original | Preserve both and inspect the explanation; do not automatically call it a restatement. |
| Requested later-reviewed basis is unavailable | Explain the limitation; do not silently fall back to the original basis. |
| Original income 20 and later revenue 95 are mixed | Reject the 21.05% result for the worked example; select a compatible pair. |
| Original figures have a non-reliance notice | Retain as historical evidence; require reviewed corrected inputs for a current conclusion or hold. |
| Filing dated after the approved as-of cutoff | Exclude it from the historical calculation. |
| A 10-K/A changes only governance disclosures | Retain the financial basis; record what the amendment actually changes. |
| Same-period values change 100 to 95 to 100 | Preserve the intermediate version and explanation; do not report an unchanged version history. |
| Source snapshot, basis or final note changes | Recheck, obtain the relevant fresh approval and preserve the earlier version. |

## Rule implementation responsibilities

R1 reviews the default, interpretation, classifications, messages and acceptance expectations. R5 independently verifies the agreed rules and controls evaluation versions. The handoffs below are proposed and do not record team acknowledgement or implementation completion.

| Rule | Roles | Implementation responsibility |
|---|---|---|
| Filing identity and complete history | R2, R4 | R2 preserves filing records, fact context, snapshot identifiers, checksums and all relevant versions. R4 validates the evidence contract. |
| Original and later basis selection | R2, R3, R4 | R2 establishes eligible sources. R3 selects the approved basis and cutoff; R4 prevents silent fallbacks and post-cutoff use. |
| Amendment scope and change explanation | R2, R3 | R2 retrieves the statement and explanatory disclosures. R3 preserves the supported classification and uncertainty in the note. |
| Compatible inputs and calculations | R2, R3, R4 | R2 provides version/basis metadata. R3 matches inputs; R4 independently checks facts, compatibility and arithmetic. |
| Commentary and same-period change meaning | R2, R3 | R2 supplies the appropriate source versions. R3 distinguishes changed reporting from changed business performance. |
| Analyst messages and version displays | R3, R6 | R3 supplies selected/alternative facts and status. R6 shows source dates, basis, reason, differences and supported choices. |
| Snapshot changes and approvals | R3, R4, R6 | R3 revises the plan and reruns checks. R4 binds approvals to the changed scope/content; R6 presents changes for review. |
| Prior notes and reproducibility | R2, R4, R6 | R2 retains source/note links and separate versions. R4 preserves approval integrity; R6 presents correction and supersession history. |
| Hold rules and acceptance | R3, R4, R6 | R3/R4 block completed results with unresolved version failures. R6 makes hold status visible instead of allowing an ordinary approval to bypass it. |

The default and later-reviewed mode remain policy proposals. Their presence in this document does not establish that the application implements either mode or that any source review has occurred.
