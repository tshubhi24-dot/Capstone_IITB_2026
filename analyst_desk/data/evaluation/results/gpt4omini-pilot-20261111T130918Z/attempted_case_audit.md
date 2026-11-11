# Role 6 — Evaluation evidence audit

**Split:** dev  
**Recorded result:** `data/evaluation/results/gpt4omini-pilot-20261111T130918Z/eval_dev_gpt4omini-pilot-20261111T130918Z.json`  
**SHA-256:** `26277a9ca3fc33661fb4dbcad3b762cb51a9e92a002eadff2c324292c809567c`  
**Gold cases:** `attempted_cases.jsonl`  
**Gold SHA-256:** `86f5b3364446ae6ad0b923617c4a6ad07c66e2a9151d838e3635ba854d933398`

This is a reproducible offline audit of **pre-existing saved results**, not a new LLM or tool run. It verifies case coverage, score types, numeric consistency and aggregates. It cannot independently verify the model outputs because the saved scores do not include full response artifacts.

| Metric | c1 |
|---|---:|
| Cases | 1 |
| Task successes | 0 |
| Task success (%) | 0.0 |
| Policy violations | 0 |
| Errors | 1 |
| Timeouts | 0 |
| Verified numbers (count) | 0 |
| All counted numbers | 0 |
| Verified share, pooled (%) | None |
| Notes with 0 counted numbers | 0 |
| Case-mean share, numeric-content notes only (%) | None |
| Verified share, average per scored case (%) | None |
| Recorded-token contribution per evaluated case (incomplete if counts are missing) | 0 |
| Latency median (seconds) | 4.3 |
| Latency p95 (seconds) | 4.3 |

## What these results establish

- **Development data only** if the split is `dev`; no held-out generalisation claim is justified.
- Pooled verified share counts *all verified numbers / all counted numbers*. It matches the definition of the Prometheus verified-share alert; the original case mean weights short and long notes equally and treats 0/0 as 100%. The extra nonempty-case mean excludes 0/0 notes.
- The 98% threshold is an **operational alert**, not a guarantee that an individual output is safe to publish.
- This file is not a substitute for a live Docker smoke test, GitHub Actions logs, manual labels, red-team results or three genuine held-out runs.
