# Current-source reverification of F01 F02 and F07

**Revision reviewed:** `33fef7f94c0b1703265cc8057066b8456122bd54`.

**Scope:** Read-only source, public documentation and relevant test review, plus 37 isolated offline probes. Sixteen positive controls and 21 counterexamples reproduced their specified results. These are diagnostic probes, not 37 product acceptance passes. No application modules, credentials, private history, protected evaluation assets or live models were used. No real approval, publication or runtime write occurred. The only created files are in this evidence directory.

## Status

| Finding | Status | Conclusion |
|---|---|---|
| F01 Incomplete claim review | Open | The gate rejects a known failed aggregate check, but judge coverage and response completeness can still produce a false green aggregate. |
| F02 Unconditional numerical guarantee | Open | Supported patterns are checked, but omitted numeric forms and missing semantic associations make the guarantee broader than the checker. |
| F07 Request and mixed-basis enforcement | Open | Specific rejection patterns work; mixed covered/uncovered requests and other mixed-basis comparisons escape them. |

“Open” does not deny the working controls below. No corrective source change after the original review is established by this reverification; the checked revision remains the same latest Main revision.

## F01 Incomplete claim review

### Current anchors

- `docs/product_spec.md:135–136`: two writer revisions and a final gate blocking remaining issues.
- `docs/product_spec.md:175`: explicitly acknowledges the ten-cited-claim cap, unjudged uncited narrative and non-blocking judge failure.
- `docs/viva_notes.md:878–881`: presents sampling as acceptable because code checks numbers.
- `analystdesk/agent/team.py:140–146`: selects cited lines over 30 characters; limits claim text to 500 characters, evidence to the first two passages and 900 characters each, then limits the list to ten items.
- `analystdesk/agent/team.py:147–160`: no selected items and judge exceptions return an empty issue list. Exceptions include malformed output and missing `verdicts`.
- `analystdesk/agent/team.py:161–165`: no schema, unique-index, complete-coverage or strict-boolean validation. Supported count is computed by subtracting unsupported entries from the number of selected items.
- `analystdesk/agent/graph.py:371–385`: aggregate `ok` depends on issue lists, not critic error or completion state.
- `analystdesk/agent/graph.py:387–392`: two-revision bound.
- `analystdesk/agent/graph.py:398–417`: unknown actions rejected and a false aggregate check blocks approval; a true aggregate reaches signing.

### Working controls verified

1. A proper unsupported verdict becomes an issue and sets aggregate `ok=False`.
2. With a failed aggregate, revisions zero and one route to the writer; revision two routes to note review. Thus automated corrections are bounded at two.
3. Attempting approval with a known failed aggregate raises `ValueError` before signing. This is a useful control and must remain.

### Counterexamples observed

| Offline fixture | Observed current-source result |
|---|---|
| Twelve substantive cited lines | Only ten `ITEM` entries are sent to the fake judge. Claims eleven and twelve are absent. |
| Two claims; empty verdict array | `checked=2`, `supported=2`, `issues=[]`. |
| Two claims; only verdict one supplied | `checked=2`, `supported=2`, `issues=[]`. |
| Two claims; two duplicate positive verdicts for item one | `checked=2`, `supported=2`, `issues=[]`; item two has no verdict. |
| Two claims; unsupported verdict with index 99 | `checked=2`, `supported=1`, `issues=[]`; the invalid index suppresses issue creation. |
| A substantive uncited causal assertion | `checked=0`, `supported=0`, `issues=[]`. |
| Timeout, malformed JSON or missing `verdicts` | Judge records an error and `supported=None`, but the aggregate is `ok=True` and the isolated note gate returns `outcome=approved`. |
| Empty verdict array for the one selected claim | No error is recorded; aggregate `ok=True` and isolated note approval succeeds. |

The approval probe uses a local fake signer returning an explicit non-token string. It demonstrates the executed gate decision, not a real signature or published note.

### Minimum correction and assurance boundary

Inventory all retained substantive assertions, validate one complete verdict per required claim, and distinguish review complete from supported. Missing, invalid, duplicated or unavailable required verdicts must leave review incomplete and block final approval. Keep the known-failure block and two-revision limit. Merely approving the displayed note cannot establish that automatic review occurred. A separately permitted, recorded claim-level human review must preserve the automatic critic's incomplete or failed status and cannot be counted as the required automatic evaluation evidence.

## F02 Numerical inventory and meaning

### Current anchors

- `docs/product_spec.md:119–123,135,182`: numerical and narrative checking descriptions, including the unconditional guarantee at line 182.
- `analystdesk/agent/checks.py:39–49`: supported fact/calc/growth/diff and dollar, percentage and percentage-point patterns.
- `analystdesk/agent/checks.py:56–65`: zero detected numbers reports a verified share of `100.0`.
- `analystdesk/agent/checks.py:68–72`: fact lookup returns the amount; no assertion-level issuer/concept/period binding.
- `analystdesk/agent/checks.py:75–108`: quoted matching strips signs and checks digit/unit occurrence; the unit matcher has no thousands branch.
- `analystdesk/agent/checks.py:125–170`: tagged arithmetic checks.
- `analystdesk/agent/checks.py:182–202`: quoted occurrence on the same line and passage-existence checks.
- `analystdesk/agent/graph.py:371–379`: only the draft body is supplied to code checking and the judge, although the exact signed note includes the title at lines 414–415.

### Working controls verified

- A correctly tagged $100 million revenue and 20% ratio passes, counting both assertions.
- A tagged 25% ratio where synthetic income/revenue is 20/100 is rejected.
- An uncited dollar amount is rejected.
- A quoted amount with the expected unit in its same-line source passes.

### Counterexamples observed

| Offline fixture | Observed current-source result |
|---|---|
| “Revenue was USD 100 million. Unit sales were 800 million.” | `ok=True`, detected total `0`, verified `0`, verified share `100.0`. Neither assertion is inventoried. |
| Output calls $100 million consolidated FY2024 revenue; its cited passage says FY2023 European segment revenue was $100 million | `ok=True`, `1/1` verified. The wrong period and perimeter are not bound to the asserted number. |
| A synthetic issuer-A revenue fact is labelled as issuer B, or as operating income | Each passes. These probes test the absence of narrative-to-fact issuer/concept binding, not actual company data. |
| Positive operating income $20 million is printed as “Operating loss -$20.0M” with its positive fact tag | Passes: the dollar matcher begins after the minus sign. |
| Output `$2.2K`, cited source `$2.2 billion` | Passes. The unhandled K unit produces an empty unit constraint. |
| Title contains “Operating margin 99% with $999 million revenue”; body has one correct tagged 20% margin | Aggregate passes `1/1`; title numbers are excluded from the checked denominator. |

### Minimum correction and assurance boundary

Require an explicit inventory and association for numerical assertions, covering title, tables and narrative. Bind issuer, fiscal period, concept/perimeter, sign, currency, scale and filing basis. Reject unsupported numeric forms or constrain and enforce the permitted output grammar. Separate “no numerical assertions” from “all assertions verified.” State current coverage limits until demonstrated. The probes do not establish that any actual published company margin is wrong; they establish counterexamples to the universal guarantee.

## F07 Scope and comparison enforcement

### Current anchors

- `docs/product_spec.md:71`: says an uncovered company stops planning.
- `docs/product_spec.md:90`: says the checker rejects any line comparing operating and pre-tax margins.
- `analystdesk/query.py:26–34,44–64`: only covered aliases/tickers are returned; unknown entities have no accounting record.
- `analystdesk/agent/graph.py:217–236`: no covered company and unsupported years are rejected; the presence of one known company is enough to pass the company check.
- `analystdesk/agent/graph.py:280–283`: planner-company output is filtered to covered tickers; requested but uncovered companies are not preserved as unresolved entities.
- `analystdesk/agent/checks.py:208–213`: mixed-basis rejection inspects only `CALC` tags sharing one line, using numerator concepts.

### Working controls verified

1. Microsoft and Alphabet FY2024 produces both companies and passes.
2. Tesla alone fails with no covered company.
3. Microsoft FY2025 fails the supported-year guard.
4. One line containing tagged operating 20% and pre-tax 35% fails the mixed-basis rule.
5. Separate clearly labelled operating and pre-tax margin lines pass, which is valid if no common-metric ranking or gap is asserted.

### Counterexamples observed

| Offline fixture | Observed current-source result |
|---|---|
| “Compare Microsoft and Tesla FY2024.” | Guard `ok=True`, company list `['MSFT']`. |
| “Compare MSFT and TSLA FY2024.” | Guard `ok=True`, company list `['MSFT']`. |
| Separate correct 20% operating and 35% pre-tax lines, followed by “The bank has the stronger operating margin.” | `ok=True`, `2/2` numerical values verified, despite the false common-metric ranking. |
| Tagged difference `(35/100 − 20/100) × 100 = +15 pp` across pre-tax and operating concepts | `ok=True`. The difference is arithmetically correct but uses incompatible metric bases. |

The scope probes execute the parser and input guard, not a live planner. They demonstrate that unsupported entities are unaccounted for before planning. They do not claim every live model will actually omit Tesla: the model could ask for clarification, and the analyst could notice an omission at the gate. No deterministic enforcement of complete requested scope was found in the cited path.

### Minimum correction and assurance boundary

Preserve requested entities, years and metrics as covered, unsupported or unresolved. Clarify or obtain an explicit revised scope before research, rather than silently narrowing it. Check metric basis at the comparison/derivation level, including `DIFF`, cross-line prose, rankings and aggregates. State that the current mixed-basis detector covers selected patterns until the broader enforcement is implemented and tested.

## Relevant tests and probe limits

Reviewed `tests/test_checks.py:9–47` (seven ordinary numeric, passage and advice tests), `tests/test_query.py:6–51` (known entities, years and decomposition) and `tests/test_team_e2e.py:130–134` (fake judge supplies complete positive verdicts for every selected item). Those cited tests do not exercise the counterexamples above. This is not a claim that every test file was exhaustively audited.

The reproducible harness is `probe_critic_numeric_scope.py`; structured observations and source hashes are in `probe_results.json`. Execution used the bundled Python runtime. AST extraction retained the function logic while stripping type annotations and replacing external dependencies with in-memory fixtures. The guard probe disables only the unrelated injection matcher; privacy helpers are synthetic and do not validate privacy behaviour. Fact amounts are synthetic, so no SEC cache or current filing selection was read. No live semantic-judge quality, UI session, full application graph, provider handling or full-suite result is claimed by this harness.
