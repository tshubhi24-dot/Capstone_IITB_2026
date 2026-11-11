# Role 5 held-out set review record

- **Release:** `role5-heldout-v1`
- **Status:** Executed in three recorded runs; C2 run 3 contains 10 provider credit errors
- **Source code revision:** `72ce461ae8f3b66c4bb1af148c041cb57bf01b7c`
- **Case file:** [`role5_heldout_v1.jsonl`](../../data/evaluation/heldout/role5_heldout_v1.jsonl)
- **Release manifest:** [`HELDOUT_ROLE5_V1_MANIFEST.json`](HELDOUT_ROLE5_V1_MANIFEST.json)

## Coverage

The release contains 40 cases: 12 numeric, 10 comparisons, 12 paired risk
disclosure questions, and 6 refusal/scope checks. Together with the 20
development cases, this satisfies the 60-case count. Supplementary examples
are not included in that count.

Numeric and comparison targets span all supported company groups, multiple
fiscal years, operating and pre-tax margins, reported amounts, growth, and
percentage-point changes. Comparison cases include differing fiscal year ends
and bank metric labels. Refusal cases cover an unsupported issuer, unsupported
years, an unsupported bank ratio, valuation, and investment advice.

## Reference and source validation

- All 34 expected numeric/comparison figures were regenerated from the
  project's `build_figures` code and pinned SEC XBRL cache. Each target key,
  normalized display value, and recorded source tag matched.
- All 24 risk anchor passage IDs resolve to the stated ticker, fiscal year,
  and Item 1A in the corresponding cached passage file. The selected topics
  and expected interpretations are recorded in each case's evaluator-only
  `expect.risk_change` contract.
- `load_cases("heldout")` accepted the full split, with 40 unique IDs and the
  declared type counts before the separate held-out execution described below.
- The expected-value checks and source lookups are reproducible offline. They
  do not constitute an independent human domain sign-off or prove complete
  filing-section coverage.

## Automated scoring boundary

For numeric and comparison cases, the existing scorer checks expected figures,
units, company association, and fiscal year association. For refusal cases it
checks for a decline without prohibited advice or unsupported financial
figures.

For risk-change cases, the current scorer checks only that cited Item 1A
passage identifiers cover both requested years. It does **not** score the
case's `expected_interpretation` or validate semantic support for a
Changed/Unchanged label. The paired source anchors and interpretations are
provided for blinded human review; do not report those 12 cases as
semantically validated from code scores alone. A domain owner should review
the anchors and contracts before making semantic risk-change claims. If
semantic risk-change scoring is required, add and test a versioned
rubric/scorer before any future held-out run.

## Independence and freeze

Role 5 prepared this release against the pinned source snapshot and the
project's written domain rules, before any held-out model run. The set and key
are evaluator-side; the application receives only the question string from
the runner. The separation is enforced by the current runner's input shape,
not by filesystem permissions, so preserve that boundary in future tools and
runner edits.

The project owner has been shown the case proposals and this release for
review. If the owner participates in agent tuning, these cases are no longer
blind to that tuning workflow. In that event, replace the exposed set with a
new independently authored set or label the affected cases as development
cases; do not claim independent held-out performance.

The manifest records the case file hash. Changes to a frozen question,
answer, source tag, or risk contract require a new release ID and hash before
scored execution. The case file was not changed after the run. The report
audits the three saved result files; it is not a replay of model outputs or an
independent semantic review. A later one-case diagnostic retry is recorded
separately and is not included in the three-run report.

## Execution outcome

The three run tags used the same frozen playbook snapshot (`8f1608da4cec`,
three approved lessons). Each result file contains all 40 rows for C0, C1, and
C2. C2 run 3 recorded 10 HTTP 402 insufficient-credit errors (nine
risk-change cases and one refusal case); its task-success and token/cost
figures are incomplete and must not be treated as a full comparable repeat.
No retries or between-run tuning were performed during those three formal
repeats.

At the project owner's request, C2 case `h-r04` was retried once afterward
under tag `role5_v1_retry_hr04_20261110`. It also returned HTTP 402
insufficient credits, with no model answer. The separate result is
`data/evaluation/results/eval_heldout_role5_v1_retry_hr04_20261110.json`; it
does not replace or alter the original case result or three-run report.

See the [three-run report](../../docs/heldout_report.md) and its
[machine-readable data](../../docs/heldout_report.json). Credential-bearing
provider URL strings were redacted from error/reason text in the saved result
records; error status, scores, and case outcomes were preserved. Revoke the
exposed provider credential before further evaluation runs.

## HTTP 402 recovery and reporting plan

The original report counts provider errors as unsuccessful attempts rather
than removing them from the 40-case denominator:

| Configuration | Run 1 successes | Run 2 successes | Run 3 successes | Execution errors |
|---|---:|---:|---:|---|
| C0 | 32/40 | 32/40 | 31/40 | None |
| C1 | 38/40 | 39/40 | 38/40 | None |
| C2 | 26/40 | 29/40 | 20/40 | 10 HTTP 402 errors in run 3 |

The 10 failed C2 cases were `h-r04` through `h-r12` and `h-x04`.
The later one-case retry of `h-r04` also received HTTP 402. In that retry,
the provider reported a requested maximum of 65,536 tokens and a lower
affordable limit. This shows why that request was rejected; it does not
establish that every other case would succeed or cost the same. Token counts
were unavailable for the failed rows, so the recorded token and cost
contributions are incomplete and do not establish actual provider billing.

Possible paths before another run:

1. **Restore sufficient provider credit or raise the key's spending limit.**
   This is the preferred path for a comparable evaluation: retain the
   original models, settings, case set, and frozen playbook. Revoke and
   replace the previously exposed credential first; do not record the key.
2. **Reduce the maximum output-token setting.** This may avoid the provider's
   affordability rejection, but requires a code/configuration change and
   may cause truncated answers or other behavioral changes. Test it
   separately, document the changed limit and model roles affected, and
   do not assume it guarantees success. Results under the changed limit
   are a separate configuration, not an unchanged C2 repeat.
3. **Use a cheaper model or another provider.** This changes the evaluated
   system and possibly its cost and behavior. Treat the results as a
   separate experiment, recording model identifiers, provider, settings,
   and pricing; do not mix them into the original C2 results.

For any future attempt, use a new unique tag, preserve the original three
result files and this report, and record the case-file hash, playbook version,
model/provider configuration, changes, errors, and costs. Credential-bearing
error text must be sanitized before sharing or committing results.

A retry of only the 10 failed cases is a **diagnostic**, not a complete
40-case repeat: report its results separately and do not replace failed
rows or combine selected successes with the original run. For a new
comparable C2 repeat after restoring credit, run all 40 cases under the
unchanged configuration and report it alongside, not in place of, the
original incomplete run. A C2-only repeat occurs at a different time from
the original C0/C1 runs; a new paired comparison would require running the
other configurations under the same protocol as well. If a revised aggregate
is produced, predefine which complete repeats it includes, retain the
original error-inclusive report, and disclose all attempts and exclusions.

The team has already seen these cases and results. Do not tune against them
and then describe a rerun as an independently blind evaluation; follow the
independence conditions above or prepare a new independent held-out set.
