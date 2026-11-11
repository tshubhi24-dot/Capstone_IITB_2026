# Financial and risk findings reverification

Reviewed revision: `33fef7f94c0b1703265cc8057066b8456122bd54` in the supplied Main checkout. This is source inspection and bounded offline execution of extracted source functions, not a live application or model run.

The reproducible harness is `probe_financial_risk.py`. Run with the bundled Python and `-B`. Its `results.json` records source hashes, 28 assertions, synthetic observations, policy expectations, anchors and limits. All 28 assertions reproduced the stated behavior: 14 positive controls, 12 counterexamples and 2 static checks. This is not 28 product acceptance passes. Existing unit-test source was inspected but the repository tests were not executed.

The harness imports only standard-library modules, extracts exact function ASTs and one exact prompt-construction expression, substitutes in-memory source inputs/company metadata and a fake interrupt, and refuses network/subprocess operations and writes outside this evidence directory. No application modules, credentials, source datasets, protected evaluation assets or running databases were loaded. No application source was edited, no model was called, and no portal write was attempted.

## F03 Bank metric task and consent

**Current status: PARTIALLY IMPLEMENTED; policy reconciliation remains open.** It would be inaccurate to describe the current pre-tax convention as wholly hidden, or to require a new third approval gate.

**Verified positive controls**

- The extracted `plan_assumptions` function names a bank's basis as “pre-tax margin, not operating margin” for an operating-margin request. The current UI renders these assumptions under “How your request was read.”
- The extracted existing plan-review node includes that disclosure in its interrupt, records an approval action, and permits cancellation. An appropriately worded plan and explicit approval of its revised scope can satisfy the project consent requirement.
- The synthetic figure builder labels the selected ratio as pre-tax, rather than relabelling it operating margin.

**Verified bounded counterexample**

With synthetic bank metadata fixed to `pretax`, revenue 100, pre-tax income 35 and an operating-income input of 30 supplied, `build_figures` selects 35.00% pre-tax and omits the operating-income placeholder. Selection depends on fixed company metadata, not the user's requested metric or the supplied alternative's eligibility. This does not establish that any real bank in the cache has eligible operating-income inputs.

**Source and tests**

- `analystdesk/scope.py:22-25,42-48`: fixed company margin basis.
- `analystdesk/agent/graph.py:85-89`: Plan has companies, fiscal years, subquestions and outline; no typed requested metric/basis.
- `analystdesk/agent/graph.py:169-181,292-307`: explicit assumptions and existing plan gate.
- `agent_ui.py:374-376`: assumptions displayed.
- `analystdesk/agent/figures.py:43-61`: metadata selects numerator and label.
- `config/llm.toml:30-35`: planner's bank convention.
- `docs/product_spec.md:89,159` versus `docs/evaluation_guide.md:199`: fixed bank convention versus unavailable requested operating metric in DG006.
- Existing test source: `tests/test_plan_assumptions.py:27-30`, `tests/test_figures.py:17-20`. These tests endorse the disclosed current convention; they were inspected, not run here.

**Limit and report wording**

Keep the finding as a task-definition/consent reconciliation, not proof of an undisclosed live substitution. Explicitly preserve per-company-year eligible-input checks and the decision accepting a revised task. A separate bank-only pre-tax comparison may be offered; the synthetic technology example supplies no technology pre-tax income and therefore cannot support a common pre-tax gap either. Accurate comparisons are core; the particular bank alternative and consent wording are adopted project rules.

## F04 Annual eligibility and calculation domains

**Current status: PARTIALLY IMPLEMENTED; multiple bounded counterexamples reproduced.**

**Verified positive controls**

- The exact annual selector accepts an ordinary annual USD fact and rejects a quarter-only entry even when `fp` is `FY`.
- The figure builder produces the ordinary positive margin, zero-income margin and negative-income margin correctly with positive revenue. Zero revenue produces no margin placeholder.
- Code emits differing-year-end and longer-year comparability notes.

**Verified bounded counterexamples**

- An approximately 18-month synthetic duration passes the `>=350` elapsed-day filter; there is no upper-bound or issuer-calendar check in that selector.
- Separately selected revenue for July 2023–June 2024 and operating income for January–December 2024 are both returned for FY2024 and divided into a 20.00% margin. The builder does not validate their matching start/end dates.
- Revenue −100 and income 20 produce −20.00%, rather than an unavailable margin required by the adopted policy.
- Prior income −10 and current income +5 produce a conventional −150.00% growth placeholder instead of amounts and signed change.
- A meaningful synthetic income of USD 1 is displayed as `$0.0M`; no smaller-unit exception is applied.
- Synthetic income 2,675 divided by revenue 100,000 displays 2.67%; decimal `ROUND_HALF_UP` from those exact inputs gives 2.68%.

**Source and tests**

- `analystdesk/edgar.py:179-195`: FY/form/end-year/minimum-duration filter and earliest filing selection.
- `analystdesk/edgar.py:210-216`: elapsed-day calculation.
- `analystdesk/edgar.py:331-338`: revenue and income selected independently.
- `analystdesk/agent/figures.py:44-77`: calculation and nonzero denominator/baseline tests, float formatting.
- `analystdesk/agent/figures.py:98-114`: comparability disclosures.
- `docs/product_spec.md:84-87,97-107,177`: stated formulas, annual/precision claims and acknowledged rounding difference.
- Existing test source: `tests/test_edgar.py:103-149`, `tests/test_figures.py:44-73`. These cover ordinary annual selection, short-quarter rejection and comparability notes; they were not run here.

**Limits and policy distinction**

The synthetic cases demonstrate missing isolated-function checks, not that a real cached issuer supplied one of those defective pairs. Source provenance, real table-unit extraction, NCI/perimeter compatibility, all report exports and a full note acceptance path were not exercised. Decimal rounding, smaller-unit exceptions and the positive-denominator/growth-baseline behavior are adopted project choices. Like-for-like source association and verifiable arithmetic remain core requirements.

## F05 Original and later versions

**Current status: PARTIALLY IMPLEMENTED; specific version-policy gaps remain.**

**Verified positive controls**

- With the original and a later different value supplied out of order, the selector retains the earliest filed original value and exposes the later amount in `restated` metadata.
- An unchanged same-year memory value is described as unchanged, rather than annual growth.

**Verified bounded counterexamples**

- The selector has only `cik`, `concept`, and `fiscal_year` parameters; the financial tool exposes no approved basis or cutoff contract. A synthetic cache containing only a later filing returns that record as the default selected fact even when the hypothetical task cutoff precedes its filing date.
- `what_changed` labels an unexplained same-year value difference “Restated since the last note” with no source explanation for its cause.

**Source and tests**

- `analystdesk/edgar.py:148,190-207`: selector interface, earliest/latest handling and changed-value classification.
- `analystdesk/servers/edgar_server.py:133-166`: financial tool interface and restatement warnings.
- `analystdesk/memory.py:166-193`: same-year interpretation.
- `docs/product_spec.md:111-113,176`: original default/later presentation wording, same-year distinction and admitted missing cutoff.
- `docs/memory_policy.md:51`: automatic restatement wording.
- Existing test source: `tests/test_edgar.py:153-169`, `tests/test_memory.py:67-77`. Tests cover original retention and the current automatic same-year label; inspected, not run here.

**Limits and report wording**

No real non-reliance notice, amendment, current issuer reliability decision or historical source snapshot was inspected. The non-reliance override is an unimplemented/unverified contract identified by source inspection, not a newly demonstrated bad live result. Preserve the historical exception: labelled original-as-reported reproduction may remain valid for a historical task. Known non-reliance or confirmed correction prevents treating affected originals as reliable support for a current financial conclusion; use approved compatible reviewed corrections or hold that conclusion. Do not insert later evidence into an earlier as-of calculation. The precise basis hierarchy and cutoff workflow are adopted project policy.

## F06 Requested risk pairs and coverage

**Current status: PARTIALLY IMPLEMENTED; prompt-level counterexamples reproduced, no bad model run claimed.**

**Verified positive control**

The exact prompt-construction expression maps an adjacent FY2023/FY2024 plan to prior 2023/latest 2024, includes both-year search instructions, and includes the complete plan text.

**Verified bounded counterexamples**

- An explicit `[2022, 2024]` plan is included in the prompt, but `prior=max(years)-1` directs the risk specialist to search 2023 and 2024 first, conflicting with the nonadjacent pair.
- A three-year plan's explicit task instruction still names only its latest/prior pair, without accounting for earlier requested transitions.
- The risk prompt's requested format names only Added/Removed/Changed. It has no explicit insufficient-evidence or scoped-unchanged outcome and does not enforce a reviewed-coverage record.

**Source and tests**

- `analystdesk/agent/team.py:192-218`: fan-out and latest/prior prompt construction.
- `config/llm.toml:83-88`: two-year search instruction, three-label format and complete plan.
- `analystdesk/agent/team.py:233-238`: handoff summary records passages/facts/errors, not a verified coverage decision.
- `docs/product_spec.md:63,124-126,174`: latest/prior scope, paired evidence rule and admitted missing coverage record.
- Existing test source: `tests/test_graph.py:222-270`, `tests/test_team_e2e.py:83-87`: ordinary adjacent-pair prompt/tool examples; inspected, not executed here. The harness did not open evaluation cases.

**Limits and report wording**

Because the full approved plan is also present, a model could follow its selected years despite the conflicting latest/prior instruction. These probes show the constructed prompt and lack of a deterministic coverage contract, not inevitable tool misuse or an actual false risk label. Actual paired-section coverage, economic significance and label quality require source review and independent evaluation. The capstone requires supported risk comparison; the exact five-state rubric and coverage record are adopted policy.

## Recommended status labels

| Finding | Current label | What this reverification establishes |
|---|---|---|
| F03 | Partial and policy reconciliation open | Disclosure and plan decision verified in isolated code; fixed numerator convention remains |
| F04 | Partial with reproduced gaps | Ordinary controls work; bounded period and numerical-policy counterexamples remain |
| F05 | Partial with reproduced gaps | Original retention works; cutoff/basis contract and unexplained restatement labelling remain |
| F06 | Partial with prompt conflict | Adjacent case works; nonadjacent/multiple-transition coverage is not guaranteed |

Do not relabel these findings Fixed without the relevant source change, policy decision and validation evidence. Do not label them all complete live failures: this exercise deliberately avoided paid calls and application runtime data.
