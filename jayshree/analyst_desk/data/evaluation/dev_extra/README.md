# Extra development cases

| File | Cases | Why it is development |
|---|---|---|
| `former_heldout_v1.jsonl` | 24 | Held-out set v1 (committed `c5f06ff` before any run). Its first run exposed a bug: C2 replanned on FY2022-only questions, because the risk-diff looked for the uncovered FY2021, and the evaluation runner did not approve the revised plan. The agent and the runner were fixed after seeing those results, so, as the brief requires, these cases now count as development. Held-out set v2 replaces them |

`analystdesk.evaluation.load_cases("dev")` loads these together with `../dev_cases.jsonl`.
