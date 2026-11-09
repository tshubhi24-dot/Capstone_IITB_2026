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
| 6 | 2026-11-09 | Live app check (Docker, image `a71f887`) | 1 request, C2 | — | 18/18 numbers verified; judge flagged 2 lines; approval refused (409); rejected | The judge treats code-verified figures in a line as claims the passage must support: too strict (open issue in the work log) |

## To run (in this order)

| Experiment | Command | Needs |
|---|---|---|
| E4 critic off; plain passages | `python scripts/run_eval.py --experiment e4_critic_off` and `--experiment e4_plain_passages` | Development set is enough to start; held-out once available |
| E1 ×3 | `python scripts/run_eval.py --experiment e1_c0_c1_c2 --split heldout --tag e1-run1` (then run2, run3) | Held-out cases; frozen playbook |
| E2 | `python scripts/run_redteam.py --experiment e2_defences_on` and `e2_defences_off` | 30+ attacks |
| E3 | `python scripts/run_eval.py --experiment e3_before_playbook` and `e3_after_playbook` | Held-out cases; reviewed, frozen playbook (record its version) |
| Judge calibration | `python scripts/calibrate_judge.py sample`, label, then `score` | 20+ human labels |
