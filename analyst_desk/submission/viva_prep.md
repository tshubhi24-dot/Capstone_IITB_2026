# Viva prep: the brief's eight questions

Everyone must redraw the architecture from memory ([../docs_notfor_submission/architecture.md](../docs_notfor_submission/architecture/architecture.md) §1) and explain their own part. ⏳ = answer depends on a run in progress.

## 1. Trace one request through the architecture

Request: *"Compare Microsoft's and Alphabet's operating margins over the last three fiscal years, and tell me what changed in their risk factors."*

| # | Box | What it decides | Decided by |
|---|---|---|---|
| 1 | UI + FastAPI | Starts a run, streams events | Code |
| 2 | Input guard | Covered companies and years? Advice request? Injected instructions? | Code |
| 3 | Planner (research lead) | Sub-questions, outline, companies, years | Model |
| 4 | Plan gate | "Last three years" read as FY2022–FY2024; analyst confirms the years, edits or cancels | Person |
| 5 | Fan-out | One researcher and one risk-diff per company, one quant, in parallel | Code |
| 6 | Specialists (ReAct) | Which tools to call, which passages to quote | Model |
| 7 | Hooks (every tool call) | Permission, budget, watchlist, EDGAR rate limit; trace; injection screen | Code |
| 8 | MCP servers | filings-kb (hybrid search + rerank), edgar (XBRL facts), python-sandbox, research-portal | Code |
| 9 | Writer | Wording; uses figure placeholders, never types numbers | Model |
| 10 | Code renders figures | Every number from XBRL, with its fact id; Comparability and Limitations sections | Code |
| 11 | Critic | Numbers checked by code; each cited claim judged by another model family; at most 2 revisions | Code + judge model |
| 12 | Note gate | Approve exact note (signed), edit (re-checked), or reject. Refused while checks fail | Person |
| 13 | Publish | Portal verifies the signature over the exact note | Code |
| 14 | Memory | Remembers the published note for "what changed since our last note?" | Code |

## 2. Model vs code vs person

| Decided by the model | Decided by code or rules | Decided by a person |
|---|---|---|
| The plan's sub-questions and outline | Coverage (companies, years), advice and injection refusal | Approve, edit or cancel the plan; confirm the years |
| Which tools to call, with what query | Every number: fetched from XBRL, computed, rendered | Approve, edit or reject the exact note |
| Which passages to quote | Units, signs, rounding, like-for-like checks | Approve or reject each lesson (with a reason) |
| Note wording | Permissions, budgets, watchlist, rate limits | Freeze the playbook |
| Whether a cited passage supports a claim (judge) | Publishing only with a valid signature | Delete memory |

One line: **the model proposes; code and people decide.**

## 3. Single agent vs team (E1)

| | C1 single agent | C2 team |
|---|---|---|
| Development success | 19/20 | 18/20 |
| Held-out success (mean of 3 runs) | ⏳ | ⏳ |
| Numbers verified | 88.7% | 89.6% |
| Notes passing every check | 13/17 | 7/17 |
| Cost per case | $0.0080 | $0.0213 (2.7×) |
| Median latency | 14 s | 44 s (3×) |

Answer: **on our questions the team did not beat the single agent, and it costs 2.7× as much.** Its value is parallel evidence-gathering and a stricter critic, which matter more for longer, multi-company notes. Show [evaluation_report.md](evaluation_report.md) §4.

## 4. Which experiment changed the design?

| Experiment | What it showed | Change made |
|---|---|---|
| Held-out v1, run 1 | C2 replanned on FY2022-only questions (risk-diff searched the uncovered FY2021); no note | Risk-diff skipped without a covered earlier year; the runner approves a revised plan. v1 moved to development; fresh held-out v2 |
| FinanceBench check | "FY22" was not read as a year | Two-digit fiscal years parsed: 1 → 2 of 4 found |
| Live app check | The judge rejected lines because a code-verified figure wasn't in the passage | The judge sees "[code-verified figure]" and judges only the wording |
| Retrieval ladder | Query decomposition gave the biggest gain (0.47 → 0.79) | Decomposition and rewrite kept in the pipeline |
| Gap analysis | Approval was possible with failed checks | Approval refused while any check fails |

## 5. Traces: missing evidence, a failed tool, an injected instruction

| Situation | What the system does | Where to show it |
|---|---|---|
| Missing evidence | Code adds a Limitations line ("No Item 1A passage for … was retrieved, so added or removed risks are not established") | Note's Limitations section; ⏳ run id |
| Failed tool | Tool returns a structured error (e.g. EXEC_ERROR, NOT_IN_COVERAGE); the specialist retries, or the plan is revised and shown again | Activity log in the Research tab; Jaeger trace; ⏳ run id |
| Injected instruction | Input guard refuses typed injections; the injection screen withholds instructions found in a filing ("withheld" in the tool log); output checks reject advice | E2 red-team table ([redteam_results.md](redteam_results.md)) ⏳; demo step 2 |

## 6. Memory: what, why, how deleted

| Store | Holds | Why | Delete |
|---|---|---|---|
| Checkpointer (SQLite) | One run's working state | Stop and resume a run | Per run (not long-term) |
| Preferences | e.g. "always include a peer table" | Notes follow the analyst's style | 🧠 Memory panel → delete |
| Coverage list | Which companies the analyst covers | "What changed since our last note?" | Panel |
| Past-note memory | Verified figures from published notes only | Compare with the last note | Panel; stays deleted after a backfill |
| Private watchlist | Tickers the analyst watches | Planner context only; never in tools or notes | Edit and save |
| Playbook lessons | Reviewed procedures | Improvement loop | Reject; frozen as a versioned snapshot |

Memory off removes the past-notes tool from the run. Policy: [../docs_notfor_submission/memory_policy.md](../docs_notfor_submission/policies/memory_policy.md).

## 7. Lessons learned, and do they help on unseen cases?

| Step | What happened |
|---|---|
| Failure on development cases | d16, d17 (risk change): the notes cited Item 1A for only one of the two years |
| Reflection (`scripts/run.py reflect`) | Turned those failures into 3 pending lessons ("When … : do …", tagged) |
| Human review (📘 Playbook) | `3d7fde3a` **approved**: "When citing risk factors from multiple years in a comparative note, cite each year's own Item 1A section" |
| | `0d88a4f7` **rejected**: "Too generic" |
| | `d54102f1` **rejected**: "Duplicate of 3d7fde3a" |
| Freeze | Playbook version `05cce831b31d` (1 lesson), a fixed snapshot for the held-out runs |
| Applied | Only to relevant requests (tag and word match, top 3); the activity log shows "📘 1 playbook lesson(s) applied" |
| Help on unseen cases? | ⏳ E3: held-out risk-change cases with vs without the playbook. If it can't be run in time, say so: the loop and review are shown; the benefit is not yet measured |

Viva point: reflection produced near-duplicates; the human review is what kept the playbook clean.

## 8. Before a supervised pilot with real users

| Need | Why |
|---|---|
| Sign-in and per-analyst access | Names are typed today; memory and approvals need real identities |
| A sandbox container per call, no network | Today's sandbox guard is in-process in Docker |
| A trained injection classifier (e.g. Llama Prompt Guard) | The screen is a pattern list; a paraphrase can pass |
| Judge every line, not only cited ones | Uncited lines are flagged, not judged |
| Correction and withdrawal of published notes | Not supported |
| Larger held-out set, measured analyst time saved | 24 held-out cases; no user study yet |
| Live filings and as-of dates | Corpus is fixed at FY2022–FY2024 |

## Who answers what

| Question | Lead | Backup |
|---|---|---|
| 1, 2 (architecture, model vs code) | Everyone | — |
| 3, 4 (experiments) | Jayshree | Sachin |
| 5 (traces) | Pranoti (security), Nidhi (ops) | Jayshree |
| 6 (memory) | Jayshree | Amit |
| 7 (lessons) | Sachin | Jayshree |
| 8 (pilot) | Amit | Shubhi |
