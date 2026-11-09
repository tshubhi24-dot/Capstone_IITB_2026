# Role 6 — Evaluation evidence audit

**Split:** dev  
**Recorded result:** `data/evaluation/results/eval_dev_merged.json`  
**SHA-256:** `d6bb893b0007efef2a0a0290956de9b64521560917a07d25825ca12d665aac5e`  
**Gold cases:** `data/evaluation/dev_cases.jsonl`  
**Gold SHA-256:** `926212f391ca3d08e73b30bb43e59a047c01159b32f8551c5724d6934fe17ff3`

This is a reproducible offline audit of **pre-existing saved results**, not a new LLM or tool run. It verifies case coverage, score types, numeric consistency and aggregates. It cannot independently verify the model outputs because the saved scores do not include full response artifacts.

| Metric | c0 | c1 | c2 |
|---|---:|---:|---:|
| Cases | 20 | 20 | 20 |
| Task successes | 16 | 19 | 20 |
| Task success (%) | 80.0 | 95.0 | 100.0 |
| Policy violations | 0 | 0 | 0 |
| Errors | 0 | 0 | 0 |
| Timeouts | 0 | 0 | 0 |
| Verified numbers (count) | 2 | 77 | 143 |
| All counted numbers | 54 | 83 | 200 |
| Verified share, pooled (%) | 3.7 | 92.8 | 71.5 |
| Notes with 0 counted numbers | 6 | 4 | 3 |
| Case-mean share, numeric-content notes only (%) | 2.4 | 95.6 | 76.0 |
| Verified share, average per scored case (%) | 31.7 | 96.6 | 80.2 |
| Tokens per case (mean) | 2471 | 12073 | 38155 |
| Latency median (seconds) | 3.8 | 14.2 | 50.9 |
| Latency p95 (seconds) | 5.6 | 29.2 | 71.0 |

## What these results establish

- **Development data only** if the split is `dev`; no held-out generalisation claim is justified.
- Pooled verified share counts *all verified numbers / all counted numbers*. It matches the definition of the Prometheus verified-share alert; the original case mean weights short and long notes equally and treats 0/0 as 100%. The extra nonempty-case mean excludes 0/0 notes.
- The 98% threshold is an **operational alert**, not a guarantee that an individual output is safe to publish.
- This file is not a substitute for a live Docker smoke test, GitHub Actions logs, manual labels, red-team results or three genuine held-out runs.
