# Analyst Desk: evaluation report

> **Draft, 9 November.** Sections marked ⏳ wait for Role 5's held-out cases, attacks and labels; their tables show the layout we will fill. Development-set numbers are final for that set, but the set was used while building, so they show what works, not how well the system generalises.

## 1. What we evaluated and why

**User and outcome.**
- **The user:** an equity research analyst writing a company note from 10-K filings.
- **What they need:** a cited note in which **every number is traceable to a filing and correct**. One wrong number undermines the whole note.
- **What we measure:**
  - **task success**, scored by code against XBRL ground truth;
  - **the share of a note's numbers that code can verify**;
  - **policy violations** (investment advice);
  - **cost, latency and errors** per case.

**Configurations (E1).** All three use the same model (`openai/gpt-4.1-mini`), the same tools and the same tool budget (12 + 12 per company):

| Config | What it is |
|---|---|
| C0 | Fixed pipeline: one retrieval with query decomposition, EDGAR figures and one model call; no agent decisions |
| C1 | One agent with all the tools in a ReAct loop: plan gate, code checks, at most 2 revisions, note gate |
| C2 | Team: research lead, one researcher and one risk-diff agent per company in parallel, a quant, a writer, and a compliance critic (code checks plus a judge from another model family, `meta-llama/llama-3.3-70b-instruct`) |

**Protocol.**
- **Cases:** a golden set split into 20 development cases and ⏳ 40+ held-out cases, written by Role 5 before any agent ran on them. The held-out folder can't be read by any agent tool.
- **Run conditions:** memory off; plan gate auto-approved; runs stop at the note gate, so nothing is published.
- **Scoring:** in code first (`analystdesk/evaluation.py`). Numeric and comparison cases need every expected figure with the right unit and sign, correctly rounded, and attached to the right company and year. Risk-change cases need Item 1A citations for both years. Refusals must decline without figures or advice. A case whose critic review didn't complete fails.
- **Experiments:** each one is a config file in `experiments/`, so every arm runs the same code. Failed and timed-out runs are counted.

## 2. Retrieval (L4–L6)

36 labelled queries, Recall@5 ([docs/retrieval_eval.md](../docs/retrieval_eval.md)):

| Configuration (table-aware passages) | Recall@5 | s/query |
|---|---|---|
| BM25 | 0.361 | 0.03 |
| Vectors (all-MiniLM-L6-v2) | 0.264 | 0.01 |
| Hybrid (RRF) | 0.389 | 0.06 |
| + cross-encoder rerank | 0.472 | 0.73 |
| + query decomposition (company/year/Item filters) | 0.792 | 1.20 |
| + decomposition + rewrite | **0.903** | 1.32 |

- **Decomposing the query into filters gives the largest single gain.** Financial questions name companies and years that pure similarity search mixes up.
- **The reranker adds 0.08,** but it is the slowest step.
- **FinanceBench external check** ([scripts/eval_financebench.py](../scripts/eval_financebench.py)): 9 of FinanceBench's 150 open-sample questions are about a 10-K we cover.
  - **4 in our corpus:** their evidence sits in Item 1A or Item 7, and search places it in the top 5 for **2 of those 4**. That is after one fix this check exposed: questions write "FY22", which we didn't read as a year.
  - **5 out of reach:** they need the balance sheet, cash-flow statement or Item 1 business overview, which we don't index. Numbers come from XBRL instead.
  - **Caveat:** the sample is small, and we fixed the parser after seeing it, so it is a development check, not an untouched test.

## 3. E1: does the agent justify its cost?

### 3.1 Development set (20 cases, one run, final code `72ce461`)

| Metric | C0 | C1 | C2 |
|---|---|---|---|
| Task success | 14/20 | **19/20** | 18/20 |
| — numeric (8) | 6 | 8 | 8 |
| — comparison (5) | 4 | 5 | 5 |
| — risk change (4) | 2 | 3 | 2 |
| — refusal (3) | 2 | 3 | 3 |
| Policy violations | 0 | 0 | 0 |
| Numbers verified, pooled | 3.6% (2/56) | 88.7% (86/97) | **89.6%** (146/163) |
| Notes passing every check at the gate (of 17) | — | **13** | 7 |
| Errors / timeouts | 0 | 0 | 0 |
| Cost per case (est.) | $0.0013 | $0.0080 | $0.0213 |
| Median / p95 latency | 4.6 / 6.0 s | 14.4 / 28.5 s | 43.5 / 75.0 s |

C2's d08 and d14–d17 were re-run after the key's spending limit stopped the first attempt (HTTP 402). The table combines both attempts (`results/eval_dev_e1-dev-main-combined.json`).

**Reading:**
- **Both agents beat the fixed pipeline:** 19 and 18 of 20 vs 14. Only the agents produce traceable numbers: C0 writes free text, so 96% of its numbers can't be traced even when they are right.
- **The team buys nothing on this set:** it costs 2.7× C1 and takes 3× as long, with no more successes.
- **The team's notes reach the analyst clean less often:** 7 of 17 vs 13. Its judge reviews every cited claim and flags some as unsupported, and the writer still sometimes types figures itself instead of using the code-rendered placeholders. The checks catch all of these, so no wrong number can be approved, but the analyst has to edit the note.
- **The risk-change misses** (d16, d17) are notes that cite Item 1A for only one of the two years.
- **Both agents sit below the 98% alert threshold** on this set.

### 3.2 Held-out set ⏳ (three runs; mean and range)

| Metric | C0 | C1 | C2 |
|---|---|---|---|
| Task success (mean, min–max over 3 runs) | | | |
| Policy violations | | | |
| Numbers verified, pooled | | | |
| Errors / timeouts | | | |
| Cost per case | | | |
| Median / p95 latency | | | |

## 4. E2: do the defences work? ⏳

**Defences:**
- input guard: scope, advice and injected instructions;
- tool-result injection screen;
- private-watchlist hook;
- output checks: advice wording and watchlist names;
- the approval gate.

**Run:** the red-team suite (⏳ 30+ attacks by Role 5, including injection through our own filings) with defences on and off (`AGENT_DEFENCES=0`), plus the clean development cases to count false blocks.

| | Defences off | Defences on |
|---|---|---|
| Attack success (all) | | |
| — injected document ("buy" article) | | |
| — watchlist exfiltration | | |
| — sandbox network escape | | |
| — direct injection | | |
| False blocks on clean cases | | |

**Already measured:** the injection screen fires on **0 of 24,660** real filing passages, so it costs no false blocks on our data. In one live check, gpt-4.1-mini ignored a planted "buy" article even with defences off. E2 has to measure that rather than assume it.

## 5. E3: did the lessons help? ⏳

- **Where lessons come from:** the reflection step, which turns development failures into pending lessons.
- **Review:** a person reviews each one; ⏳ record one accepted and one rejected lesson, with its reason.
- **Freeze:** the playbook is frozen as a versioned snapshot before the held-out run (version: ⏳).

| | Before playbook | After playbook (version …) |
|---|---|---|
| Held-out task success | | |
| Numbers verified | | |
| Cost per case | | |
| Lessons that made a case worse | | |
| Cost of generating the lessons | | |

## 6. E4: signature ablation (development set; held-out ⏳)

| | C1 | C1 critic off | C1 plain chunks | C2 | C2 critic off | C2 plain chunks |
|---|---|---|---|---|---|---|
| Task success | 19/20 | 19/20 | 19/20 | 18/20 | 19/20 | 19/20 |
| Numbers verified, pooled | 88.7% | 92.3% | 95.5% | 89.6% | 82.7% | 88.2% |
| Notes passing every check (of 17) | 13 | 12 | 14 | 7 | 7 | 8 |
| Revisions made | 9 | 0 | 8 | 22 | 0 | 24 |
| Cost per case | $0.0080 | $0.0070 | $0.0085 | $0.0213 | $0.0186 | $0.0186 |
| Median latency | 14.4 s | 13.9 s | 14.1 s | 43.5 s | 28.3 s | 36.8 s |

**On 20 cases and one run, the differences are within run-to-run noise.** The same ablation on the previous code version (experiment log, runs 8–10) found the critic loop adding about 12 points of verified share and table-aware chunks 9–15. Here the critic adds 7 points for C2 and none for C1, and plain chunks score slightly higher. So we don't claim either effect from development data. The held-out comparison, run three times with its spread, is the test.

**What the critic loop does show consistently:** it revises notes (9 revisions for C1, 22 for C2) at 15–50% more latency.

Retrieval alone doesn't separate the two chunkings. With decomposition and rewrite, table questions reach 1.00 recall either way, and overall recall is 0.903 table-aware vs 0.944 plain ([docs/retrieval_eval.md](../docs/retrieval_eval.md)). So E4 has to measure the effect on whole notes, where a table kept whole lets a quoted figure be checked against its row and header.

## 7. Judge calibration ⏳

- **Setup:** the judge (`llama-3.3-70b-instruct`) is compared with ⏳ 20+ claims labelled by hand by a teammate who did not build the critic.
- **Reported:** agreement and Cohen's kappa, with unavailable verdicts counted separately.

| n | Agreement | Cohen's kappa | Judge unavailable |
|---|---|---|---|
| | | | |

**Known issue, from a live run on 9 November:** the judge marks a line as unsupported when it combines a figure that code has verified with a passage that doesn't state that figure. It is too strict, not too lenient. We report it, and the fix is to judge only the line's wording.

## 8. Memory (L9)

The same follow-up request was run with memory on and off:

| | Memory on | Memory off |
|---|---|---|
| Previous note found | yes | no |
| "What changed" section | yes | no |
| Preference applied (peer table) | yes | no |
| Numbers verified | 14/14 | 6/6 |
| Tokens / seconds | 9,646 / 17 | 9,419 / 14 |

Memory changes what the note covers, not whether its numbers are right. Its cost is about 2% more tokens.

## 9. Limits (stated honestly)

- **Development vs held-out:** development results were tuned on. Only held-out results (⏳) measure generalisation.
- **Fixed corpus:** 15 companies, FY2022–FY2024, as originally reported; there's no live "latest" period and no calendar alignment.
- **Typed names, not logins:** a single-analyst prototype. There is no correction or withdrawal of published notes.
- **Judge coverage:** the C2 judge reviews cited claims only. Uncited lines are counted and shown to the analyst. C1 has no judge, but its numbers are still checked by code.
- **Cost:** estimated at a blended $0.52 per million tokens, not billed per model.
- **Full list:** [docs/gap_closure.md](../docs/gap_closure.md) and [docs/product_spec.md §9](../docs/product_spec.md).
