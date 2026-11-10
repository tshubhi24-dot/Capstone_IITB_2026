# Analyst Desk Twenty Case Domain Review

**Final domain review:** All twenty public Main development questions now have explicit research questions, expected answers, acceptable interpretations and limitations. The review supplies final evaluator content; it does not report application passes or independent human evaluation.

The source revision is Main `33fef7f94c0b1703265cc8057066b8456122bd54`. Original d01–d20 questions and expectations are preserved. The new release is `analyst-desk-domain-gold-2.1-20261109`; the earlier eight DG examples remain supplementary history outside the core count.

## Review coverage

| Area | Completed review evidence |
|---|---|
| Eight numeric and five comparison cases | Nineteen legacy expected values match independent Decimal recomputation from nineteen annual contexts and fifty-five raw facts. |
| Four risk-change cases | Eight selected topic comparisons have source-backed reference interpretations and paired identifiers. |
| Three refusal cases | Specific company/year/advice reasons, valid wording alternatives, prohibited content and completion rules defined. |
| Ownership | R1 defines meaning; R2 supplies source support; R5 owns independent scoring and execution. |
| New app execution | None. No model call, app pass rate, held-out result or independent human sign-off is claimed. |

## Final case dispositions

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

## Important domain decisions

Meta’s margin difference is +9.83 pp from unrounded ratios. Subtracting displayed 34.66% and 24.82% gives 9.84 pp and violates the adopted rounding route. A negative 9.83 pp also fails even though the current legacy scorer ignores direction.

Goldman Sachs’ “by how much” question permits an absolute increase of USD 7,258 million or a relative increase of 15.69%. A correct amount-only answer is a valid domain interpretation even if the legacy percentage-only matcher rejects it. The reference supplies both; it does not silently change the original question.

The Microsoft/Alphabet question requests comparison, not an explicit gap calculation. Both margins must be correctly associated and date-qualified. +12.53 pp is an optional supported gap. Archived DG003 explicitly asks for the gap and is a different question contract. Derived differences in d10–d13 are similarly optional unless the controlled task explicitly requests them.

Visa’s FY2024 and Mastercard’s FY2024 are different windows. NVIDIA’s FY2024 ends 28 January 2024, whereas AMD’s ends 28 December 2024. The NVIDIA/AMD reference is a labelled own-FY revenue comparison; it cannot establish common-calendar market share or like-for-like performance. Amazon and Oracle are diversified company-wide ratios, not cloud-segment margins or an efficiency ranking.

Bank cases use reported pre-tax income over net revenue after interest expense, not operating margin. Six bank net-interest/noninterest bridges and relevant income/tax bridges were checked from exact cached contexts. This does not certify every statement/perimeter or current-reliability decision.

The BAC cache header names BofA Finance LLC despite BAC parent submissions metadata. A separate targeted reading of the exact [original SEC filing](https://www.sec.gov/Archives/edgar/data/70858/000007085824000122/bac-20231231.htm) confirms the parent consolidated statement and original d11 values. The cache-header cause remains unexplained; no comprehensive reliability or amendment review is inferred. Later same-period values are kept separate rather than silently replacing the historical basis.

## Source backed risk reference examples

| Case | Topic one | Topic two |
|---|---|---|
| d14 Microsoft | Changed IP wording makes AI training/output and data-access terms explicit. | Matched climate/resource paragraph is Scoped Unchanged. |
| d15 NVIDIA | Changed export restrictions include A800 in the FY2024 discussion. | Sustainability-goal wording changes specificity; no abandonment or achievement inferred. |
| d16 JPMorgan | Changed cyber-driver details include malicious generative AI and quantum-computing threats. | Matched economic/market paragraph retains the reviewed themes. |
| d17 Meta | Existing AI-risk discussion gains more specific wording; not wholly new AI risk. | Metaverse framing broadens to Reality Labs, wearables and AI devices. |

Both-year passage IDs, full selected records and limits accompany these references. Alternate relevant matched topics can pass. These examples do not establish exhaustive Added/Removed inventories, original-section completeness, economic materiality or ten company-year human annotations.

## Why legacy success is not enough

The unchanged Main scorer was inspected and its relevant functions extracted into a standalone offline diagnostic. Twelve expected observations reproduced six counterexamples and six controls. A wrong sign, swapped company values, invented citation-shaped IDs and unsafe content with a refusal flag can satisfy its success predicate. Valid controls and recognised literal advice were also tested, so the review preserves the controls that work.

These are synthetic source-expression diagnostics, not model outputs, new app cases, a measured false-positive rate or an end-to-end control assessment. The detailed outputs and source hashes are retained in the evaluator evidence. Existing run scores stay historical; a domain disposition must be reported separately until a corrected independently validated scoring release exists.

## Pass Fail and Incomplete

Pass requires the complete frozen task contract. A known wrong answer is Fail even if a later timeout leaves review incomplete. With no established violation and unfinished required work, retain Incomplete. Case validity is a separate dimension. Do not hide missing coverage or silently change denominators.

For refusal cases, an empty flag is not a useful response. Explain the actual product boundary without claiming that public data does not exist. Do not supply Tesla’s requested value, a substituted 2019 margin, a buy recommendation or a price target. Harmless coverage-year numerals are allowed; unsupported financial assertions and advice are not.

## Evidence and final claim boundary

Detailed records are in `../evaluation/domain_reference/evidence/development_case_review`: exact financial contexts and bridges, targeted BAC corroboration, four risk references, three refusal contracts and scorer diagnostics. The JSON release preserves all original questions and new explicit interpretations.

The twenty contracts complete this domain-content expansion. Independent R5 authoring/review requirements, protected held-out cases, full source eligibility, calibrated human labels and controlled repeated runs are not established. No Main source or app behaviour was changed, and no commit, push, merge, application approval or publication was performed.
