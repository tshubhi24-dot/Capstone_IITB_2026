# Submission work log

Dated record of the work towards submission on 12 November: what was fixed, checked or produced, by whom, and where it is. Newest first. Add a row whenever something lands; link the PR or file.

| Date | Who | What | Where |
|---|---|---|---|
| 2026-11-09 | Jayshree | FinanceBench external retrieval check (`scripts/eval_financebench.py`): 9 of the 150 open-sample questions are about a 10-K we cover; the evidence for 4 is in our Item 1A/7 corpus (the rest is in the financial statements or Item 1). Search found 1 of 4 in the top 5. Cause: "FY22" was not read as a year. Fixed `find_years` (two-digit fiscal years) → 2 of 4. No development case uses two-digit years, so the E1/E4 runs are unaffected | `scripts/eval_financebench.py`, `query.py`, `results/financebench_check.json` |
| 2026-11-09 | Jayshree | Judge strictness fixed: figures code already verified are shown to the judge as "[code-verified figure]", so it judges the wording against the passage, not numbers the passage never states. Test added (289 pass). Done before the E4 runs so their C2 numbers use the final judge | PR #14, `team.claim_lines`, `llm.toml` judge |
| 2026-11-09 | Jayshree | PR #14 review requested from Shubhi (GitHub review request and comment) | PR #14 |
| 2026-11-09 | Jayshree | Started the submission folder: deliverables checklist against the brief, evaluation report draft, experiment log, demo script, slides outline, failed-CI explanation, request to Role 5 | `submission/` |
| 2026-11-09 | Jayshree | Live check of the running app (image `a71f887`): one C2 request passed every number check (18/18). The judge flagged 2 lines that combine code-verified figures with a passage that doesn't state them, so approval was refused (409) and the note rejected. Logged as a judge-strictness issue to fix | experiment log, 2026-11-09 |
| 2026-11-09 | Jayshree | Closed the gap-analysis items code can close: complete claim review that blocks when incomplete; number edge cases (rounding, sign, scale, denominators, company/year mixing); plan-gate scope; Limitations section; truthful publish outcomes; deletion that stays deleted; versioned frozen playbook; stricter scorer. Status of every ID in `docs/gap_closure.md`. 288 tests; live smoke C1/C2 on d01, d09, d14 | PR #14 |
| 2026-11-09 | Jayshree | Found and fixed a race: two parallel first searches both built the search index and one failed (seen in the live smoke run) | PR #14, `retrieve.py` |
| 2026-11-09 | Jayshree | Live evaluation gate in CI made on-demand only, so it doesn't spend OpenRouter credit or fail without a key | PR #12 (merged) |
| 2026-11-09 | Jayshree | Capstone gaps: guardrails, private watchlist, experiment configs, red-team harness, like-for-like checks, memory off removes the past-notes tool | PR #11 (merged) |
| 2026-11-09 | Nidhi (Role 6) | HTTP MCP in Docker, approval refused while checks fail, CI on the lock file with Prometheus rule checks, evaluation-results audit, `ops_smoke.py` | PR #10 (merged) |
| 2026-11-09 | Amit (R1), Jayshree | R1 specifications folded into the product spec, memory policy and evaluation guide | PR #9 (merged) |

## Open issues found during submission prep

| Found | Issue | Plan |
|---|---|---|
| 2026-11-09 | The C2 judge marks lines with code-verified figures as unsupported when the cited passage doesn't state that figure. Notes are held for the analyst more often than they should be | **Fixed** the same day (see above); measured in the E1/E4 development runs |
| 2026-11-09 | The writer sometimes types its own numbers (growth rates, segment amounts) instead of using placeholders; the checker catches them, but the note needs an edit | Tighten the writer prompt; count it in the report as a known failure mode |
| 2026-11-09 | No FinanceBench external retrieval check | **Done** the same day: 2 of 4 findable questions in the top 5 (see above) |
