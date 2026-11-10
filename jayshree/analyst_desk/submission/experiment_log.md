# Experiment log

Every evaluation run, in order. The brief asks that each experiment be a config file rather than a code branch (`experiments/*.toml`), that failed and timed-out runs are included, and that any change made after viewing held-out results is recorded here and those cases are treated as development cases from then on.

**Fixed across all runs unless stated:**
- agent model `openai/gpt-4.1-mini`;
- judge `meta-llama/llama-3.3-70b-instruct`;
- the same tools and tool budget for C1 and C2 (12 + 12 per company);
- memory off (`AGENT_EVAL=1`);
- the plan gate auto-approved, and runs stop at the note gate, so nothing is published.

Cost is estimated at $0.52 per million tokens.

| # | Date | Experiment / config | Split, cases | Result file | Outcome | What we learned / changed |
|---|---|---|---|---|---|---|
| 1 | 2026-10-24 | Retrieval, Recall@5 | 36 labelled queries | `results/retrieval_20261024-*.json`, [docs/retrieval_eval.md](../docs/retrieval_eval.md) | Hybrid 0.389 → +rerank 0.472 → +decompose +rewrite 0.903 (table-aware passages) | Query decomposition into company/year filters gives the largest gain; the reranker adds about +0.08 but costs about 0.7 s per query |
| 2 | 2026-10-25 | Memory on vs off | 1 follow-up request | `results/memory_compare_20261025-112601.json` | Memory on: previous note found, "what changed" section, peer table (preference) used, 14/14 verified. Memory off: none of those, 6/6 verified | Memory changes what the note contains, not its accuracy |
| 3 | 2026-10-25 | E1 development: C0 vs C1 vs C2 | dev, 20 | `results/eval_dev_merged.json`, [docs/evaluation.md](../docs/evaluation.md) | Success C0 16/20, C1 19/20, C2 20/20; pooled numbers verified C0 3.7%, C1 92.8%, C2 71.5%; cost per case $0.0013 / $0.0063 / $0.0198; median latency 3.8 / 14.2 / 50.9 s | The team is most reliable but 3× the cost of C1 and lower on verified share: the writer types some numbers itself. Development set only: tuned on, so not a generalisation result |
| 4 | 2026-11-09 | Smoke after the gap fixes (PR #14) | dev d01, d09, d14 × C1, C2 | not kept (smoke) | 6/6 passed. C2 judge reviewed up to 16 claims per note; 3 C2 notes held for unsupported claims or unsourced numbers | Found the parallel-search race (fixed); Limitations listed recovered errors (fixed) |
| 5 | 2026-11-09 | Smoke rerun after those two fixes | dev d09, d14 × C1, C2 | not kept (smoke) | 4/4 passed; no search errors; no recovered errors listed | — |
| 7 | 2026-11-09 | FinanceBench external retrieval check | 9 open-sample questions in our coverage (AMD FY2022 ×7, JPM FY2022, MSFT FY2023) | `results/financebench_check.json` | Evidence in our corpus for 4; top-5 hit 1/4, then **2/4** after the year fix | "FY22" was not parsed as a year, so searches ran over all of a company's years: fixed. This check was used to make that fix, so it is now a development check, not an untouched test. The other 5 questions need the financial statements or Item 1, which we don't index |
| 6 | 2026-11-09 | Live app check (Docker, image `a71f887`) | 1 request, C2 | — | 18/18 numbers verified; judge flagged 2 lines; approval refused (409); rejected | The judge treats code-verified figures in a line as claims the passage must support: too strict (open issue in the work log) |

| 8 | 2026-11-10 | E1 development, on the PR #14 code | dev, 20 | `results/eval_dev_e1-dev-final.json` | C0 16/20, C1 18/20, C2 20/20. Pooled verified: C0 3.0%, C1 91.4%, C2 86.1%. Notes passing every check at the gate: C1 12/17, C2 4/17 | The new stricter scorer fails C0 on d07 (sign of a percentage-point change). C2's judge now reviews every claim and flags many, so few C2 notes reach the analyst clean. Superseded by run 11 |
| 9 | 2026-11-10 | E4 critic off, on the PR #14 code | dev, 20 × C1, C2 | `results/eval_dev_e4-critic-off-dev.json` | C1 20/20, 78.9% verified, gate 9/17; C2 20/20, 74.6% verified, gate 7/17 | The critic loop adds about 12 points of verified share (C1 +12.5, C2 +11.5) for about 30% more tokens. Superseded by run 12 |
| 10 | 2026-11-10 | E4 plain chunks, on the PR #14 code | dev, 20 × C0, C1, C2 | `results/eval_dev_e4-plain-dev.json` | C0 15/20 (1 timeout); C1 20/20, 82.2% verified; C2 20/20, 71.3% verified | Table-aware chunks add 9 points of verified share (C1) and 15 (C2). Superseded by run 13 |
| 11 | 2026-11-10 | E1 development, on merged main `72ce461` (quarantine, year confirmation, gap fixes) | dev, 20 | `results/eval_dev_e1-dev-main.json` | C0 14/20, 3.6% verified. C1 19/20, 88.7% verified, gate 13/17. C2: **15 cases valid** (d14–d17 hit HTTP 402, d08 timed out); on those, 89.3% verified and gate 5/12 | **The key's $10 limit ran out mid-run** (402). The 5 failed C2 cases were re-run with a new key (run 14) |
| 12–13 | 2026-11-10 | E4 critic off; E4 plain chunks, on merged main (first attempt) | dev | deleted | Every agent call returned 402 (key limit). Only E4-plain C0 completed (16/20) | The result files held only errors, so they were deleted rather than reported |
| 14 | 2026-11-10 | E1 C2, the 5 failed cases re-run with the new key | dev d08, d14–d17 | `results/eval_dev_e1-dev-main-c2rest.json`, combined into `eval_dev_e1-dev-main-combined.json` | C2 overall 18/20, 89.6% verified, gate 7/17, $0.0213 per case, median 43.5 s | — |
| 15 | 2026-11-10 | E4 critic off, on merged main | dev, 20 × C1, C2 | `results/eval_dev_e4-critic-off-dev-main.json` | C1 19/20, 92.3% verified, gate 12/17; C2 19/20, 82.7% verified, gate 7/17 | |
| 16 | 2026-11-10 | E4 plain chunks, on merged main | dev, 20 × C1, C2 (C0 from run 13) | `results/eval_dev_e4-plain-dev-main.json` | C1 19/20, 95.5% verified; C2 19/20, 88.2% verified | Runs 15–16 contradict runs 9–10 on effect size: on 20 cases × 1 run, E4 effects are within noise. The held-out ×3 comparison decides |
| 17 | 2026-11-10 | Held-out set v1 created | 24 cases | `data/evaluation/heldout/` | Generated by a fixed rule (`scripts/make_heldout_cases.py`), committed `c5f06ff` before any run | — |

## To run (in this order)

| Experiment | Command | Needs |
|---|---|---|
| E4 critic off; plain passages | `python scripts/run_eval.py --experiment e4_critic_off` and `--experiment e4_plain_passages` | Development set is enough to start; held-out once available |
| E1 ×3 | `python scripts/run_eval.py --experiment e1_c0_c1_c2 --split heldout --tag e1-run1` (then run2, run3) | Held-out cases; frozen playbook |
| E2 | `python scripts/run_redteam.py --experiment e2_defences_on` and `e2_defences_off` | 30+ attacks |
| E3 | `python scripts/run_eval.py --experiment e3_before_playbook` and `e3_after_playbook` | Held-out cases; reviewed, frozen playbook (record its version) |
| Judge calibration | `python scripts/calibrate_judge.py sample`, label, then `score` | 20+ human labels |
