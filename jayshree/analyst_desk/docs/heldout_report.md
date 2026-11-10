# Held-out evaluation: repeated run report

3 distinct recorded live-run tags; each configuration covers the same gold cases.
These are score-file audits, not independent replays of raw model outputs.

Values are medians across runs [minimum, maximum], except case-type rows, which list each run's success count.
| Metric | c0 | c1 | c2 |
|---|---:|---:|---:|
| Task success (%) | 80 [77.5, 80] | 95 [95, 97.5] | 65 [50, 72.5] |
| Pooled verified share (%) | 8.7 [8.1, 10.5] | 79.3 [75.7, 83.9] | 95.7 [95.6, 97.7] |
| Policy violations | 0 [0, 0] | 0 [0, 0] | 0 [0, 0] |
| Errors | 0 [0, 0] | 0 [0, 0] | 0 [0, 10] |
| Timeouts | 0 [0, 0] | 0 [0, 0] | 0 [0, 0] |
| Recorded-token contribution per case | 2467 [2466, 2470] | 14188 [13547, 14598] | 30918 [23123, 31914] |
| Rows with token counts | 40 [40, 40] | 40 [40, 40] | 40 [30, 40] |
| Rows without token counts | 0 [0, 0] | 0 [0, 0] | 0 [0, 10] |
| Cases with numeric checks | 26 [26, 27] | 23 [23, 26] | 16 [14, 18] |
| Verified numeric items | 9 [8, 10] | 153 [142, 156] | 125 [109, 134] |
| Numeric items assessed | 99 [95, 103] | 186 [179, 202] | 128 [114, 140] |
| Median latency (s) | 8 [7.5, 8.4] | 15.4 [14.9, 16.6] | 38.8 [32.2, 40.5] |
| p95 latency (s) | 11 [10.3, 11.3] | 33.8 [31.8, 36.4] | 67 [66.2, 73.2] |
| False blocks | 0 [0, 0] | 0 [0, 0] | 0 [0, 0] |
| Recorded-token cost contribution per case (USD) | 0.0013 [0.0013, 0.0013] | 0.0074 [0.007, 0.0076] | 0.0161 [0.012, 0.0166] |

## Success by case type

Each cell lists the three success counts, followed by median [minimum, maximum]; denominators are fixed across runs.

| Case type | c0 | c1 | c2 |
|---|---:|---:|---:|
| comparison | 10/10, 10/10, 10/10; median 10/10 [10/10, 10/10] | 10/10, 10/10, 10/10; median 10/10 [10/10, 10/10] | 4/10, 4/10, 4/10; median 4/10 [4/10, 4/10] |
| numeric | 8/12, 8/12, 7/12; median 8/12 [7/12, 8/12] | 11/12, 12/12, 11/12; median 11/12 [11/12, 12/12] | 9/12, 9/12, 9/12; median 9/12 [9/12, 9/12] |
| refusal | 2/6, 2/6, 2/6; median 2/6 [2/6, 2/6] | 5/6, 5/6, 5/6; median 5/6 [5/6, 5/6] | 5/6, 5/6, 5/6; median 5/6 [5/6, 5/6] |
| risk_change | 12/12, 12/12, 12/12; median 12/12 [12/12, 12/12] | 12/12, 12/12, 12/12; median 12/12 [12/12, 12/12] | 8/12, 11/12, 2/12; median 8/12 [2/12, 11/12] |

## Execution errors

- `role5_v1_run3` / c2: 10 failed case(s) (10 APIStatusError (402)); IDs: h-r04, h-r05, h-r06, h-r07, h-r08, h-r09, h-r10, h-r11, h-r12, h-x04.
  This configuration's task-success score is retained but incomplete; token-count and cost metrics exclude unavailable token counts.

## Limitations

- Audits saved model scores; does not replay or independently score raw model outputs.
- The risk-change scorer checks Item 1A citation coverage for both years, not semantic support for the interpretation.
- A run with provider errors is retained as recorded and is not a complete successful repeat.
- Per-case token and cost contributions divide recorded totals by all rows; unavailable token counts are omitted, so these metrics are lower-bound contributions, not provider billing records.
- Sanitization: 20 provider credential-bearing URL(s) were redacted from saved reason/error strings; case outcomes and score fields were preserved.

## Run provenance

- Frozen playbook: `8f1608da4cec` (3 approved lessons).
- `role5_v1_run1`: `data/evaluation/results/eval_heldout_role5_v1_run1.json` (SHA-256 `5e2bc773373688e41fc69554abd396fcd49844efb8a4ffd7764e85826490488b`)
- `role5_v1_run2`: `data/evaluation/results/eval_heldout_role5_v1_run2.json` (SHA-256 `bd4e031b390a4e6a842f744fd536357f8ca1c9004f893ec715f78aeb80904880`)
- `role5_v1_run3`: `data/evaluation/results/eval_heldout_role5_v1_run3.json` (SHA-256 `7107aae847a826e1a4c160e439a1adc0a9eb6216022823595a548efb98517a5f`)
- Held-out cases SHA-256: `3d602f20b4d08d5e0b55ea3f7d409c0e1439baf6b70d097d64a88ca10dfdfd2f`
