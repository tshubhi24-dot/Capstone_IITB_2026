# Held-out cases

The agent never reads this folder: no tool can open it, and only `scripts/run_eval.py --split heldout` loads it.

## `heldout_v1.jsonl`: 24 cases

| Type | Cases |
|---|---|
| Numeric | 10 |
| Comparison | 6 |
| Risk change | 4 |
| Refusal | 4 |

**Who wrote them.** The brief asks that the held-out set be written by someone who does not tune the agent (Role 5). Role 5 was not available before submission, so the **build team** wrote this set, by a fixed rule rather than by hand ([scripts/make_heldout_cases.py](../../../scripts/make_heldout_cases.py)):

- every question comes from fixed templates over the 15 covered companies and FY2022–FY2024;
- anything the development set uses is excluded: the same figure, the same company pair, the same risk-change company and years, the same refusal kind;
- cases are drawn with a fixed seed (`20261110`), stratified by type, and by sector for numeric cases;
- expected figures are computed from XBRL by code;
- the file and its SHA-256 ([manifest.json](manifest.json)) were committed **before any agent ran on it**.

The evaluation report states this. If the agent is changed after viewing held-out results, the affected cases count as development cases from then on, and the report says so.

**Run** (frozen playbook required unless lessons are off):

```
python scripts/run_eval.py --experiment e1_c0_c1_c2 --tag e1-heldout-run1
```

Then run it again with the tags `-run2` and `-run3`.

More cases written independently (by Role 5) can be added as further `*.jsonl` files in this folder, in the same format as `../dev_cases.jsonl`.
