# Analyst Desk Golden Answers and Scoring Rules

**Status:** Proposed rules and worked development examples. Source-eligibility approval, independent human verification, scoring agreement, policy adoption, freeze and handoff remain pending. No application evaluation has been run for this pack.

A golden answer is the expected correct result fixed from evidence and written requirements before inspecting the tested system's answer. It includes the financial meaning, source associations, required qualifications and legitimate limitations, rather than just a matching number.

This initial pack contains eight development questions: four issuer-source questions and four explicitly synthetic boundary fixtures. The additional teaching examples explain the rules; they are not extra cases or observed application results. The pack does not complete the full development/held-out suite, ten human-labelled company-years, judge calibration or product acceptance. All cases remain development; related variants must not later be presented as independent unseen tests.

## Understanding a golden answer

A golden answer serves as an independently prepared answer key. First define the question, permitted evidence and expected result; then test the application against that definition. Do not change an expectation merely to match the application's output.

For a fictional Company A, suppose annual revenue is USD 100 million and operating income is USD 20 million, with the same period and consolidated reporting basis. Its operating margin is `20 / 100 x 100 = 20.00%`. A polished report that states 25.00% fails the arithmetic requirement. A report that states 20.00% still needs the correct company, metric, period, units and supporting source.

| Required association | What the reviewer checks |
|---|---|
| Company | The amount belongs to the requested company or consolidated group. Company A's 20.00% must not be attached to Company B. |
| Metric | Operating margin uses operating income and compatible revenue; net income or pre-tax income is not silently substituted. |
| Actual period | The fiscal label and start/end dates match the requested task. |
| Currency and scale | Dollars, thousands and millions are interpreted correctly before calculation. |
| Reporting basis | Consolidated, segment, adjusted and managed figures are not mixed. |
| Specific source | The cited filing, table, column and presentation support the inputs and assertion. |
| Calculation and limitations | Compatible inputs produce the result, and any material comparison or evidence limitation is stated. |

Correct digits alone do not establish correctness. Company A's 20.00% reported as Company B's margin fails the company association even if the arithmetic is correct. A citation that does not support the stated metric also fails the source requirement.

## Scoring outcomes and mandatory checks

Declare the evaluated target before scoring: a final answer, a specific component output or a workflow/control requirement. A wrong intermediate draft corrected through an allowed process does not automatically fail the final-answer calculation. Preserve the trajectory and score any separate control violations under their declared rules.

| Outcome | Meaning and teaching example |
|---|---|
| Pass | All mandatory requirements pass: values and associations, code arithmetic, coverage, qualifications and applicable controls. Company A's answer is 20.00% with the correct company, period, source and required explanation. |
| Fail | A definite wrong result or requirement violation occurs. Examples include 25.00% instead of 20.00%, the wrong company, fabricated values, silent substitution, an unsupported assertion or unwarranted refusal. |
| Incomplete | Execution or required review does not finish and no definite failure has been established. A required checker times out before the verdict. Preserve the reason and attempted-run record; do not count it as pass or discard it. |
| Disputed or defective case | The expected evidence or rubric is itself unresolved. If the answer key and the permitted source disagree, quarantine the case for documented R1/R2/R5 adjudication, retaining prior versions/results. Do not use this label to hide an application failure. |

Record component outcomes for input identity, arithmetic, display, source/claim support, requested coverage and control behaviour. A component pass does not compensate for a different mandatory failure. A malformed/unavailable judge remains incomplete; ordinary note approval is not a claim-review verdict.

Track correctness and execution/review completion separately. An established mandatory violation remains an aggregate Fail even if a later timeout or unavailable judge also leaves completion incomplete. If no definite failure is established and required execution/review is incomplete, record aggregate Incomplete. Preserve both facts rather than letting an outage hide a known wrong result.

For example, if Company A's known correct margin is 20.00% but the evaluated final response states 25.00% and the critic times out, record the known correctness failure and the incomplete critic review. The timeout does not erase the wrong answer.

An unavailable result can pass only where the frozen question/evidence permits that limitation and the response accounts for the requested scope. It cannot replace a readily answerable supported question to obtain a safe score. A completed answer that silently drops a company fails; a system timeout is recorded as incomplete with the omission still visible.

Every substantive assertion, including title, summary and table claims, needs review. Citation presence alone is insufficient. Accept meaning-preserving paraphrases; preserve attribution, conditional language and uncertainty. Correct financial numbers accompanied by an unsupported claim such as "cybersecurity risk caused profit to fall" fail the relevant mandatory claim check. A response with no recognised numerical values or only a partial review must not receive an automatic complete-note 100% pass.

Keep failed, timed-out and incomplete attempts in reported results. Any defective-case denominator change requires a recorded reason and evaluation version. Report correctness, policy violations, coverage, cost and latency separately; do not turn a single coarse score into a claim of complete accuracy.

A case Pass is an evaluation verdict. It does not approve a research plan, authorise publication or replace exact-note human review.

## Source basis and independent calculations

Both sources are original consolidated U.S. GAAP annual presentations. Use group totals, not segment, adjusted or managed figures. Revenue uses RevenueFromContractWithCustomerExcludingAssessedTax; operating income uses OperatingIncomeLoss. The Alphabet statement labels its numerator "Income from operations".

| Field | Microsoft MSFT | Alphabet GOOGL |
|---|---|---|
| Fiscal period | FY2024, 1 July 2023 to 30 June 2024 | FY2024, 1 January to 31 December 2024 |
| Revenue in USD millions | 245,122 | 350,018 |
| Operating income in USD millions | 109,433 | 112,390 |
| Independent margin | 109433 / 245122 x 100 | 112390 / 350018 x 100 |
| Two-decimal result | 44.64% | 32.11% |
| Original accession | 0000950170-24-087843 | 0001652044-25-000014 |
| SEC filing date | 30 July 2024 | 5 February 2025 |
| Statement location | Item 8, Income Statements, printed page 56, FY2024 column | Item 8, Consolidated Statements of Income, printed page 53, FY2024 column |

[Microsoft original report](https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/msft-20240630.htm) and [filing detail](https://www.sec.gov/Archives/edgar/data/789019/000095017024087843/0000950170-24-087843-index.html). [Alphabet original report](https://www.sec.gov/Archives/edgar/data/1652044/000165204425000014/goog-20241231.htm) and [filing detail](https://www.sec.gov/Archives/edgar/data/1652044/000165204425000014/0001652044-25-000014-index.html).

### Microsoft calculation example

Using the Microsoft inputs above, calculate `109433 / 245122 x 100 = 44.64429957327371676144940070658692406230%`, displayed **44.64%**. This is an independently calculated margin, not a quoted issuer ratio. The inputs are reported in millions; the extra calculation digits do not imply underlying ledger precision. Correct digits attached to Alphabet, net income or an identical-calendar-year claim still fail the relevant association.

These are pinned original annual presentations, not a claim about latest figures or current investment suitability. Amendment/non-reliance eligibility review remains required before freeze or production use.

Alphabet's filing detail distinguishes acceptance on 4 February 2025 from filing on 5 February 2025. Preserve the actual filing date separately from acceptance, fiscal period and any evaluation cutoff.

Alphabet's independent margin is `112390 / 350018 x 100 = 32.10977721145769646132484615076938900285%`. Microsoft minus Alphabet, calculated before display rounding, is **12.53452236181602030012455455581753505945 percentage points**, displayed **+12.53 percentage points**.

Public companyfacts rows tied to these exact accessions corroborate the date windows and raw USD amounts. These expectations were independently calculated from the source inputs, rather than copied from the tested application's generated answer or expected-answer files. Complete source eligibility and evidence archiving still require review before freeze.

## Issuer source development cases

DG001-DG004 form one related family, FY2024 annual margins. Keep this family together when controlling case partitions; all four are development questions. The quoted questions state the candidate task precisely. The evaluator must pin the questions, permitted evidence and acceptable output variants before freeze. All contracts remain subject to review.

**DG001 Microsoft margin.** Question: "Using Microsoft's original FY2024 annual filing, calculate its reported consolidated operating margin. State the reporting period, revenue, operating income and source." Expected amounts shown here in USD millions: revenue 245,122, operating income 109,433 and calculated margin 44.64%, covering 1 July 2023 to 30 June 2024. Fail wrong input associations, unsupported source links or an identical-calendar-year claim.

**DG002 Alphabet margin.** Question: "Using Alphabet's original FY2024 annual filing, calculate its reported consolidated operating margin. State the reporting period, revenue, operating income and source." Expected: revenue 350,018 million, income from operations 112,390 million and calculated margin 32.11%, covering 1 January to 31 December 2024. The company identity is Alphabet's consolidated group, not a share-class-specific income statement.

**DG003 Reported fiscal-year comparison.** Question: "Compare Microsoft's and Alphabet's reported FY2024 operating margins using their original annual filings. Calculate Microsoft's margin minus Alphabet's margin in percentage points and explain any difference in reporting windows." Expected: 44.64%, 32.11% and +12.53 percentage points, with each company's actual window and the explicit different-period qualification. Do not call the gap 12.53% relative growth, infer a cause or rank investment attractiveness.

To distinguish percentage points from relative growth, use a separate fictional margin that rises from 20.00% to 25.00%. The increase is `25 - 20 = +5.00 percentage points`. Relative growth is `(25 - 20) / 20 x 100 = 25.00%`. These are different measures; the requested margin gap uses percentage points. Calculate the Microsoft/Alphabet gap from the original inputs before rounding the final +12.53-point display.

## Calendar comparison limitation example

**DG004 Aligned calendar request with annual-only evidence.** Question: "Using only the provided original FY2024 annual sources, calculate Microsoft's and Alphabet's operating margins for 1 January through 31 December 2024. Do not estimate missing periods or obtain additional sources." Alphabet's 32.11% matches that window; Microsoft's supplied annual inputs do not. Retain Microsoft's requested row as unavailable for that aligned period and explain why. Offer a revised reported-FY comparison requiring the appropriate plan decision. Do not estimate missing months or imply calendar figures are unavailable from every possible source.

| Company | Supplied original FY2024 annual window | Requested January to December 2024 result |
|---|---|---|
| Microsoft | 1 July 2023 to 30 June 2024 | Unavailable from the permitted annual inputs for this aligned period. |
| Alphabet | 1 January to 31 December 2024 | 32.11% operating margin, with the specified source support. |

The appropriate analyst message is: "Microsoft's requested calendar-period margin cannot be calculated from the supplied annual evidence. A reported-FY comparison can be offered as a revised task, with the different date windows disclosed."

An unavailable Microsoft result can pass this constrained question because the limitation is required by the evidence. Silently dropping Microsoft, estimating missing months or labelling July-to-June figures as January-to-December fails. In a different question where compatible evidence is readily available, an unwarranted unavailable result does not earn a pass.

## Synthetic development boundary cases

These fixtures are invented inputs for component or controlled-fixture development checks, not issuer results, live SEC retrieval tests, observed product failures, human risk labels or protected cases. Fixture input records are separate from expected answers in the local case pack. R5/R3 must declare the fixture adapter and execution boundary before scoring; none is implemented or validated by this document. A legitimate production scope refusal of fictional companies must not be scored as an end-to-end financial failure.

**DG005 Scale conversion.** Company X's FY2024 annual revenue is 100 in a table headed USD millions; operating income is 20,000 in USD thousands. Both cover 1 January to 31 December 2024 on the same consolidated basis. Normalise to USD 100,000,000 and USD 20,000,000; expected margin is **20.00%**, not 20,000.00%. Check the table headers, conversion and associations, not merely the digits.

| Input | Reported amount | Normalised USD amount |
|---|---|---|
| Annual revenue | 100 million | 100,000,000 |
| Annual operating income | 20,000 thousand | 20,000,000 |

The correct formula is `20000000 / 100000000 x 100 = 20.00%`. Ignoring the headers and calculating `20000 / 100 x 100` produces the incorrect 20,000.00%.

**DG006 Unsupported bank operating metric.** Technology Company T has revenue 100 and operating income 30. Bank B has compatible net revenue 100 and pre-tax income 35, but no supported operating-income input. All fixture amounts are USD millions for the same annual period. Asked for operating margins, report T at **30.00%** and Bank B as unavailable for that metric, with the limitation. Do not call the bank's **35.00% pre-tax margin** an operating margin or produce a 5.00-point operating gap. Offer a revised pre-tax task; do not perform the substitution under the original plan.

| Input or result | Technology Company T | Bank B |
|---|---|---|
| Revenue or net revenue in USD millions | 100 | 100 |
| Operating income in USD millions | 30 | Unavailable |
| Pre-tax income in USD millions | Not provided | 35 |
| Requested operating margin | 30.00% | Unavailable with explanation |

The bank calculation `35 / 100 x 100 = 35.00%` is a pre-tax margin. A revised pre-tax comparison also needs compatible pre-tax inputs for Company T; the fixture does not provide them. Do not invent them or substitute the task automatically.

## Filing and risk evidence examples

**DG007 Filing version and cutoff.** A fictional FY2023 original filing dated 15 February 2024 has revenue 100 and operating income 20; a later presentation dated 20 February 2025 has 95 and 18. All figures are USD millions. Asked for the original FY2023 margin using information available by 31 December 2024, the eligible fixture pair gives **20.00%**. The later presentation is outside the cutoff. Reject mixing original income 20 with later revenue 95 to obtain 21.05%. Do not automatically call a same-year difference business decline or a confirmed restatement.

| Presentation | Date | Revenue | Operating income |
|---|---|---|---|
| Original FY2023 filing | 15 February 2024 | 100 | 20 |
| Later presentation of FY2023 | 20 February 2025 | 95 | 18 |

For this original-presentation task and cutoff, use `20 / 100 x 100 = 20.00%`. The mixed pair `20 / 95 x 100 = 21.05%` uses individually sourced figures from incompatible presentations. The arithmetic does not make that pairing valid.

**DG008 Missing earlier risk evidence.** The supplied fictional current-year passage discloses cybersecurity risk. Earlier-year search failed and comparable coverage is unavailable. Expected: the current disclosure may be described within its source scope, but evidence is insufficient to classify it as Added, Removed, Changed or Unchanged across years. Explain the missing comparison. Failed retrieval is not proof of absence, economic deterioration or a cause of a financial result.

For example, the reviewer receives a FY2024 cybersecurity passage but the FY2023 search fails. The appropriate finding is: "The supplied FY2024 passage discloses cybersecurity risk. Comparable earlier-year evidence is unavailable, so the year-over-year change cannot be classified." A statement that a new risk was added fails because the earlier disclosure has not been established as absent.

## Precision and reporting examples

Match each quantity by company, metric, actual period, currency, scale, operations, filing presentation and specific source. Normalised source values are exact inputs. Finding the same digits elsewhere in a response cannot satisfy that association. Check compatible input pairs before calculating.

Calculate using source precision without extra intermediate rounding. Proposed draft display uses USD millions to one decimal and margins/percentage-point changes to two decimals, with **ROUND_HALF_UP** for decimal ties. This tie convention is a proposal requiring agreement; the existing policies specify precision without resolving every tie. Unambiguous grouping and trailing-zero variants must not be confused with a different financial value. Where the exact question does not mandate a scale, an explicit mathematically equivalent USD scale conversion is acceptable; do not penalise a valid conversion as a wrong amount.

For a positive decimal tie, `20.125%` displays as **20.13%** under the proposed rule. Where a question does not fix the scale, **USD 100 million** and **USD 100,000,000** represent the same amount when labelled clearly. This flexibility does not permit an unapproved currency conversion.

Exact formulas and source inputs are authoritative; finite decimal reference strings are not a licence for premature rounding. Recompute ratios and differences independently at sufficient precision, then round the final display. Declare any narrowly justified computational tolerance before scoring. No blanket financial tolerance may excuse a wrong sign, unit, source association or rounding result.

The following ten-attempt illustration is hypothetical and separate from the eight development cases. It demonstrates reporting, not an observed product result.

| Outcome | Attempts | Share of all attempts |
|---|---|---|
| Pass | 6 | 60% |
| Fail | 2 | 20% |
| Incomplete | 2 | 20% |
| Total | 10 | 100% |

Report: "Of ten attempts, six passed, two failed and two were incomplete." Do not silently remove the incomplete attempts and headline `6 / 8 = 75%` success. If a completed-attempt metric is also useful, label its denominator and report it alongside all attempts and completion. Any defective-case exclusion needs a recorded reason and evaluation version. A numerical-check rate also does not establish full-note accuracy or analyst usefulness.

## Review and freeze requirements

Freezing means identifying a stable version of the question, permitted evidence, expected answer and scoring rules before a scored run. It does not prohibit corrections: a justified amendment creates a documented new version while preserving the earlier case and results. For example, if a frozen case changes its permitted filing presentation, re-review the compatible inputs and expected result under a new version; do not overwrite the old expectation to make an observed answer pass.

Before freeze, record case/version and related family, exact question, permitted inputs/source snapshot and checksums, all input associations, formulas and rounding, mandatory findings/qualifications, allowed limitations/refusals and unacceptable substitutions. Pin the proposed policy/rubric versions. Keep source disputes, reviewer decisions and any amendments explicit.

Specify the runner/adapter for issuer-source integration candidates and the separate controlled-fixture boundary for synthetic cases. Verify the intended evidence is supplied without expected-answer fields. Do not combine fixture correctness with live retrieval success or treat an unavailable test adapter as an application defect.

R1/R2 must confirm source eligibility for the stated historical task, including any applicable amendment/non-reliance concern; these drafts do not certify current/latest reliability. R5 independently verifies the expected answers and scoring contract before acknowledging the handoff and freezing an identified version. No scored result is implied here.

Development questions support practice and implementation feedback. Held-out questions test unseen performance; these eight cases and their close variants cannot later be claimed as independent unseen tests. The synthetic examples need a declared controlled test setup. A live app legitimately refusing fictional Company X is not a failed financial calculation, and a synthetic arithmetic pass is not proof of live SEC retrieval success.

Gold values, scoring records and protected assets belong evaluator-side. The controlled runner receives the question and allowed evidence, not the expected answer. Exclude this development answer guide and evaluator records from the evaluated application's prompts, tools, retrieval and analyst memory. Repository placement alone does not enforce isolation. Never use held-out answers or observed model outputs to rewrite a purportedly unseen expectation without a new case/version decision.

| Role | Required responsibility |
|---|---|
| R1 | Review domain meaning, expected conclusions and acceptable limitations. |
| R2 | Verify source provenance, periods, units, reporting basis and source eligibility. |
| R5 | Independently verify expectations and scoring; control protected cases, freeze the agreed version and acknowledge the handoff. |
| R3 and R4 | Implement the workflow, checking and controls against the agreed development expectations. |
| R6 | Provide reproducible configuration and diagnostic traces. |

Independent human review, disagreement resolution, source-eligibility decisions, adopted policy/rubric versions, validated execution adapters, freeze and R5 acknowledgement remain open. Publishing this specification does not establish a completed evaluation handoff, application compliance or measured analyst benefit.
