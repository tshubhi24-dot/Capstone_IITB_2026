# Independent financial review of the historical C2 note

**Result: all six tagged operating margins pass the bounded cached-fact and arithmetic review. No wrong margin was found.** This is an independent assistant inspection, not a human-expert label or whole-note acceptance.

Selected draft: `comparison-20261109-c2`, `output.values.draft`; status `waiting_note`. The historical run used revision `42e2298a26bffb918ac8320543f6bc0d9591405c`. It is not evidence that current Main `33fef7f` produced this result. No note was approved or published.

## Results

Amounts below are USD millions for readability. Calculation used the unrounded base-USD integers, Decimal precision 50 and `ROUND_HALF_UP` only for the final two-decimal margin display.

| Company | FY | Revenue USD millions | Operating income USD millions | Note margin | Independent margin | Actual annual window | Inclusive days | Filing date | Result |
|---|---|---|---|---|---|---|---|---|---|
| Microsoft | 2022 | 198,270 | 83,383 | 42.06% | 42.06% | 2021-07-01 to 2022-06-30 | 365 | 2022-07-28 | PASS |
| Microsoft | 2023 | 211,915 | 88,523 | 41.77% | 41.77% | 2022-07-01 to 2023-06-30 | 365 | 2023-07-27 | PASS |
| Microsoft | 2024 | 245,122 | 109,433 | 44.64% | 44.64% | 2023-07-01 to 2024-06-30 | 366 | 2024-07-30 | PASS |
| Alphabet | 2022 | 282,836 | 74,842 | 26.46% | 26.46% | 2022-01-01 to 2022-12-31 | 365 | 2023-02-03 | PASS |
| Alphabet | 2023 | 307,394 | 84,293 | 27.42% | 27.42% | 2023-01-01 to 2023-12-31 | 365 | 2024-01-31 | PASS |
| Alphabet | 2024 | 350,018 | 112,390 | 32.11% | 32.11% | 2024-01-01 to 2024-12-31 | 366 | 2025-02-05 | PASS |

Microsoft's July-to-June windows and Alphabet's January-to-December windows are genuine issuer fiscal years, with the expected leap-year durations. They are not identical calendar periods. A fiscal-year comparison needs that qualification. This inspection establishes the source periods; it does not establish that the draft prints every required date disclosure.

## Independent source method

Read the two cached SEC companyfacts JSON files directly. For each note tag, select the exact `us-gaap:OperatingIncomeLoss` numerator and `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` denominator using its filing accession, actual start/end dates and USD unit. Require a unique matching context and verify `fp=FY`, `form=10-K`, own filing fiscal year, equal input windows and positive revenue. Check the response CIK/entity name against the note issuer.

Corroborate each accession, annual report date, filing date and primary-document name against cached SEC submissions. Alphabet FY2022 uses its archived submissions block; the other five filings are in the cached recent blocks. Exact contexts, original raw rows, JSON pointers, concept descriptions, source-file hashes and primary-filing reference URLs are recorded in `financial_checks.json`. Filing URLs are references only and were not opened. No application selection or verification function was used.

## Interpretation and limits

- The CIK/entity records and standard operating-income/revenue concepts support issuer-level association. The cache does not preserve full statement presentation/context IDs, segment axes or consolidation footnotes; consolidated perimeter was not independently re-audited from statement cells.
- Cached companyfacts and submissions were not refreshed. Amendment/non-reliance checks, subsequent corrections, complete source eligibility and present-day reliability remain outside this review.
- Six correct ratios do not establish the truth of explanations, risk additions/removals, the critic's overall verdict or a final product acceptance decision.
- The selected draft may still require edits or HOLD for other findings. This financial result must remain separate from narrative review, domain acceptance and publication authority.

Only `financial_checks.json` and this review were written in the assigned evidence folder. No source, running database, credential, model, network service or protected evaluation asset was used or changed.
