# Status against the implementation gap analysis

The team's *Current Implementation Gap Analysis* reviewed the app against the final specifications. It covers 77 rule groups and the 28 frontend messages. This page gives the status of every ID it raises. It also records what the app does now, and what is still open and who supplies it.

**Status meanings**

| Status | Meaning |
|---|---|
| **Implemented** | The required behaviour is in code and covered by a test (most are in `tests/test_gap_fixes.py`) |
| **Partly** | The core is in code; the line says what is not |
| **Scope limit** | Deliberately outside this capstone. It is stated in [product_spec.md §9](product_spec.md), the [threat model](threat_model.md) or the [memory policy](memory_policy.md), and the app does not claim it |
| **Evidence** | Needs data, labels or runs from a person, not code. The owner is named |
| **Preserved** | Already working; kept as is |

**Summary**

| Group | Implemented | Partly | Scope limit | Evidence | Preserved |
|---|---|---|---|---|---|
| Financial rules (38) | 16 | 8 | 6 | 5 | 3 |
| Evidence and approval rules (17) | 9 | 3 | 2 | 1 | 2 |
| Memory and scoring rules (22) | 9 | 4 | 5 | 3 | 1 |
| Frontend messages (28) | 17 | 7 | 3 | 0 | 1 |

The counts are per ID, as the analysis assigns them, and overlap in subject.

## Still open, and who supplies it

1. **Role 5 (independent of the builders):** the evidence for F06, F30, F31, F34, F37, AE17, L01, L04 and G05. That means:
   - 40+ held-out cases;
   - 30+ attacks;
   - human risk-change labels for 10 company-years;
   - 20+ judge-calibration labels.

   The harness for all of these is ready: `run_eval.py`, `run_redteam.py`, `calibrate_judge.py`, `experiments/`.
2. **The whole team:** run E1 ×3, E2, E3 and E4 on those cases, then write the evaluation report.
3. **Code, if time allows:** have the judge review uncited narrative lines (AE02), and add a typed per-section coverage record for risk comparisons (AE04/AE05).

---

## Financial rules

| ID | Status | What the app does / what remains | Where |
|---|---|---|---|
| F01 | Preserved | 15 companies, two sectors, FY2022–FY2024; tools refuse anything else | `scope.py`, `servers/common.py` |
| F02 | Implemented | The plan gate lists every requested company or year that the plan leaves out. An edited plan is held to coverage in the UI, the API (422) and the graph | `graph.plan_assumptions`, `plan_scope_errors` |
| F03 | Implemented | "Last three years" and "latest" are read at the plan gate as FY2022–FY2024 / FY2024, historical. The dashboard says the data is historical annual 10-Ks | `graph.plan_assumptions`, `app.py` |
| F04 | Implemented | For a bank, the plan gate says margins are pre-tax. If operating margin was asked for, it says banks don't report it and that approving uses pre-tax margin instead. The analyst can edit the plan | `graph.plan_assumptions` |
| F05 | Implemented | The checker rejects a line that sets an operating margin against a pre-tax margin. The Comparability section states the bases. The dashboard chart is captioned "not comparable, not ranked" | `checks.py`, `figures.comparability_notes`, `app.py` |
| F06 | Evidence | The bank concepts are mapped in code (net revenue, pre-tax income). Verifying the statement label and perimeter for each bank-year is a source review. **Owner:** Role 1/2 | `edgar.py` |
| F07 | Implemented | A `[calc]` ratio must use one company and one fiscal year. A `[growth]` must compare the same item with an earlier year, and a `[diff]` one company's margins | `checks._mismatch` |
| F08 | Implemented | An annual fact must cover 350–380 days, which rejects quarterly and multi-year tags. A 53-week year is 371 days. All 45 company-years are unchanged | `edgar.get_annual_fact` |
| F09 | Implemented | The Comparability section states each company's fiscal year-end and any 53-week year. The dashboard shows each period end | `figures.comparability_notes` |
| F10 | Preserved | Facts stay in raw USD until display | `edgar.py` |
| F11 | Implemented | A quoted amount must match the passage's scale: $2.2K or a bare $2.2 never matches "$2.2 billion" | `checks._unit_pattern` |
| F12 | Implemented | Display rounding is half away from zero (20.125% → 20.13%). The checker compares with the same rule | `figures.half_up` |
| F13 | Implemented | No margin is shown on zero or negative revenue; the checker refuses one | `figures.py`, `checks.py`, `baseline.py` |
| F14 | Scope limit | Every figure is as originally reported in that year's own 10-K, one fixed basis. A different later value is shown as a warning, never swapped in | `edgar.get_annual_fact` |
| F15 | Scope limit | Fixed historical corpus, no as-of cutoffs; stated in the product spec §9 | — |
| F16 | Implemented | Approval is refused while checks fail, in the graph, the API (409) and the UI. Only a passing note gets a signature, and the portal accepts only a signed note | `graph.review_note`, `api.py`, `portal.py` |
| F17 | Implemented | A loss renders as `-$1,234.5M`. The checker reads the sign and counts the number, so a dropped sign fails | `figures.money`, `checks.FACT` |
| F18 | Implemented | No growth rate is offered from a zero or negative earlier amount; the checker refuses one | `figures.py`, `checks.py` |
| F19 | Partly | The plan gate shows dropped companies. The writer must say when a figure is unavailable for a company in the plan. There is no per-row inventory check | `llm.toml` writer |
| F20 | Implemented | Margins are computed from raw dollars, not rounded millions, everywhere: the agents, the dashboard baseline and C0 | `baseline.py`, `c0_pipeline.py` |
| F21 | Partly | Margins show two decimals everywhere. No small-amount unit fallback is needed: every figure in the corpus is in the millions or more | `app.py` |
| F22 | Partly | Facts are USD only, and quotes must match their scale. "$" is taken as US dollars, which holds for US 10-Ks | `edgar_server.py`, `checks.py` |
| F23 | Implemented | A different later value is described as "a later 10-K reports … (reason not established)", never as a restatement | `memory.what_changed`, `edgar_server.py`, `baseline.py` |
| F24 | Scope limit | Passage ids carry company, year, Item and accession; facts carry accession and filing date. There are no checksums | `ingest.py` |
| F25 | Scope limit | 10-K/A scope is not reviewed; the original filing is used | — |
| F26 | Scope limit | No non-reliance handling; no covered company-year is known to be affected | — |
| F27 | Partly | One basis per note (as originally reported), so versions are never mixed in a calculation. Matching commentary to a later presentation is not checked | `edgar.py` |
| F28 | Preserved | An edit sends the note back to the checks and needs a fresh approval of the exact content | `approval.py` |
| F29 | Partly | Past-note follow-up works; a deleted note memory is not restored (see M07). No supersession links | `memory.py` |
| F30 | Evidence | The task families are implemented. The risk-diff compares the plan's own years (FY2022 with FY2024 when those are asked for). Demonstrating them is the demo and evaluation runs. **Owner:** team | `team.py` |
| F31 | Evidence | Item-aware parsing, table chunks and retrieval labels exist. Human risk labels for 10 company-years: **Owner:** Role 5 | `ingest.py`, `eval_retrieval.py` |
| F32 | Scope limit | Quarterly charts are a labelled dashboard extra, not part of the assessed annual core | `chat_chart.py` |
| F33 | Partly | Every number is checked by code; every cited claim is judged in C2, and a missing verdict blocks approval. Uncited lines are counted and shown to the analyst but not judged | `checks.py`, `team.make_judge` |
| F34 | Evidence | E1–E4 and the evaluation report. **Owner:** team | `run_eval.py`, `experiments/` |
| F35 | Partly | Advice requests and wording are refused, and the injection screen and output checks are in place. The injected-buy test is a Role 5 attack | `guards.py`, `checks.py` |
| F36 | Partly | Each result records its experiment switches, model config and frozen-playbook version. There is no policy hash | `run_eval.py` |
| F37 | Evidence | Role ownership is in the viva notes; the independent held-out and attack evidence is from Role 5 | `viva_notes.md` |
| F38 | Implemented | A margin change from zero income is kept: 0.00% → 5.00% is +5.00 pp | `figures.build_figures` |

## Evidence and approval rules

| ID | Status | What the app does / what remains | Where |
|---|---|---|---|
| AE01 | Implemented | Each figure is checked against its fact, with sign, scale, company and year (F07, F11, F17). An untagged number with no cited passage is an issue | `checks.py` |
| AE02 | Partly | Every cited claim goes to the judge, in batches of 10. Uncited substantive lines are counted and flagged to the analyst ("read them yourself") but not judged | `team.claim_lines`, `agent_ui._check_display` |
| AE03 | Implemented | Each claim needs exactly one true/false verdict. A judge outage, an empty or duplicate verdict, or a non-boolean one leaves the review incomplete. That is an issue, so approval is refused | `team.make_judge` |
| AE04 | Implemented | Risk-diff compares the plan's latest year with the plan's previous year, using Added / Removed / Changed / Unchanged / Insufficient evidence. Code adds a Limitations line when either year's Item 1A was not retrieved. Human labels: Role 5 | `team.py`, `graph.limitations`, `llm.toml` |
| AE05 | Partly | The writer and risk prompts forbid claims about length, word counts, correlations or causes that no passage states, and absence claims from excerpts. Tool errors become Limitations. There is no typed coverage record | `llm.toml`, `graph.limitations` |
| AE06 | Implemented | Dropped scope is shown at the plan gate; injected instructions are refused at input and withheld from tool results. The watchlist is kept out of tools and notes | `graph.py`, `guards.py` |
| AE07 | Preserved | At most two automated revisions | `graph.MAX_REVISIONS` |
| AE08 | Implemented | See F16 | `graph.review_note`, `api.py` |
| AE09 | Implemented | The note gate accepts only approve, edit or reject, and anything else raises. The API validates the action type | `graph.review_note`, `api.py` |
| AE10 | Preserved | Exact-content signature; an edit is re-checked and re-approved | `approval.py` |
| AE11 | Scope limit | Single-analyst demo with typed names; stated in the threat model | `threat_model.md` |
| AE12 | Partly | The signature binds the exact note and is issued only on a passing check. Plan, sources and policy are not in the signature | `approval.py` |
| AE13 | Implemented | Published only on a receipt with a note id; `ok` without an id is "save outcome unknown" | `graph.publish` |
| AE14 | Implemented | A lost response is `publish_unconfirmed`, never retried automatically. A duplicate save names the existing note id and time | `graph.publish`, `portal.publish_note` |
| AE15 | Implemented | A memory update that fails after a confirmed save leaves the note Published, says so and points to the backfill; it never republishes | `graph.publish`, `agent_ui._view` |
| AE16 | Scope limit | No correction or withdrawal workflow; product spec §9 | — |
| AE17 | Evidence | Calibration and labelling tooling exists; the labels come from Role 5 | `calibrate_judge.py` |

## Memory and scoring rules

| ID | Status | What the app does / what remains | Where |
|---|---|---|---|
| M01 | Preserved | Separate stores for public evidence, run checkpoints and long-term memory | `memory.py`, `runtime.py` |
| M02 | Partly | Preferences are added and deleted explicitly; a correction is delete-and-replace | `memory.py` |
| M03 | Scope limit | Single-analyst demo; typed names; threat model | — |
| M04 | Scope limit | Past-note memory is shared desk history, by design; memory policy | `memory_policy.md` |
| M05 | Implemented | Only a confirmed, approved and passing note is remembered; a memory-sync failure is reported separately (AE15) | `graph.publish` |
| M06 | Implemented | Memory off removes `get_past_notes` from the run, and evaluation runs are always memory-off | `runtime.research_tools` |
| M07 | Implemented | Deleting a past-note memory removes it from coverage and records it as deleted. Backfill and a later sync do not restore it | `memory.forget`, `backfill_memory.py` |
| M08 | Scope limit | A run keeps the memory snapshot it started with; changing settings needs a fresh run (the "Re-run without memory" button) | — |
| M09 | Implemented | Comparisons with a past note are recomputed from verified tags. A same-year difference is "a later presentation", never a restatement | `memory.what_changed` |
| M10 | Scope limit | No retention timers; memory policy | `memory_policy.md` |
| M11 | Implemented | The private watchlist is seen only by the planner; it is refused in tool calls and in notes | `guards.py`, `hooks.py`, `checks.py` |
| M12 | Partly | Bounded lookups. "No previous note" is stated only after a lookup that ran | `graph._changes` |
| L01 | Evidence | Lessons come only from development runs, as pending, with their source. A genuine accepted lesson and a rejected one with its reason: **Owner:** team | `reflect.py`, `lessons.py` |
| L02 | Partly | A separate review is required and the UI demands a reason for a rejection. The reviewer is a typed name | `lessons.review` |
| L03 | Implemented | Freezing snapshots the approved lessons with a version hash. Frozen runs read only that snapshot, results record the version, and a held-out run refuses to start unless the playbook is frozen | `lessons.set_frozen`, `run_eval.py` |
| L04 | Evidence | Memory on/off (`memory_compare.py`) and E3 before/after runs. **Owner:** team | `experiments/e3_*` |
| G01 | Scope limit | The development set is 20 code-frozen cases, not DG001–DG008. The held-out set comes from Role 5 | `dev_cases.jsonl` |
| G02 | Implemented | The scorer checks sign and correct rounding at the shown precision. It ties the figure to the right company and year, by its source tag or the company named on its line or table | `evaluation.figure_present` |
| G03 | Implemented | A case whose critic review is incomplete fails, whatever the figures | `evaluation.score` |
| G04 | Partly | Agents never see expected answers; held-out files are read only by the evaluation runner. They are not access-controlled from the app container | `evaluation.py` |
| G05 | Evidence | Expected figures are computed from XBRL by code (`make_dev_cases.py`); independent held-out expectations come from Role 5 | — |
| G06 | Implemented | The judge sees both passages a label was made on. An unavailable verdict is excluded and counted, not scored as "no", and an undefined kappa is reported as undefined | `calibrate_judge.py` |

## Frontend messages

| ID | Status | What the app shows |
|---|---|---|
| S01 | Implemented | The plan gate: "'latest' is read as FY2024 … historical annual 10-K filings"; the dashboard's coverage row |
| S02 | Implemented | Out of scope: the reason with the covered list. A mixed request: "Requested but NOT in this plan: …" at the plan gate |
| S03 | Partly | A replan shows the revised plan at the plan gate for approval; only a coverage contradiction triggers it |
| B01 | Implemented | The plan gate, for a bank asked for operating margin: banks don't report it; approving uses pre-tax margin |
| B02 | Implemented | Same as B01; the note labels every bank figure as pre-tax |
| B03 | Implemented | The checker issue on a mixed-basis line; the Comparability line; the dashboard caption |
| F01 | Implemented | Comparability: "Fiscal years end on different dates: …" |
| F02 | Implemented | Comparability: "…FY2023 had 53 weeks … growth involving FY2023 is not fully like-for-like" |
| F03 | Scope limit | Calendar alignment is not offered; the plan gate says each company's own fiscal year |
| F04 | Partly | Checker issues name the reason (unknown fact, wrong company or year, non-positive revenue, growth from a loss) |
| V01 | Partly | The basis ("as originally reported") is in the tool output and the methodology; it is not a banner on every note |
| V02 | Partly | A later 10-K's different value is a warning in tool results |
| E01 | Implemented | Limitations: "No Item 1A risk-factor passage for … was retrieved, so added or removed risks … are not established" |
| E02 | Partly | The judge flags unsupported cited claims; the writer may not state causes or correlations without a passage |
| E03 | Implemented | "Review incomplete: the judge gave no valid verdict for N of M cited claims … Re-check before approval" |
| A01 | Implemented | "Approval unavailable until these are fixed" with the issues; Approve is disabled |
| A02 | Implemented | "Ready for your review: approving publishes exactly this note" |
| A03 | Preserved | An edit returns the note to the checks and needs a new approval |
| A04 | Implemented | "Save outcome unknown … Check the portal's Recent notes before trying again" |
| A05 | Implemented | "Published as note #N"; a separate warning if the memory update failed |
| M01 | Implemented | The run status: "saved memory off: no preferences, past notes or past-note tool in this run" |
| M02 | Scope limit | Single-analyst demo; no access-denied state |
| M03 | Partly | A lookup error stops the run with its error; there is no separate "history unavailable" banner |
| M04 | Implemented | "Removed note #N … from memory and coverage … The published note itself stays in the portal, and saved runs … are not changed" |
| L01 | Partly | Pending lessons are listed for review; no banner text |
| L02 | Implemented | "Playbook FROZEN version `…` (N lessons; runs use only this snapshot)" |
| R01 | Scope limit | A provider error stops the run and is shown; tokens used so far stay in the run |
| R02 | Implemented | Limitations: "The … step ended with BUDGET_EXCEEDED; its part of the note may be incomplete" |
