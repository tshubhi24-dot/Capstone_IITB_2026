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
- **FinanceBench external check:** ⏳ not run. If it isn't run before submission, state it as a limit here.

## 3. E1: does the agent justify its cost?

### 3.1 Development set (20 cases, one run)

| Metric | C0 | C1 | C2 |
|---|---|---|---|
| Task success | 16/20 | 19/20 | **20/20** |
| — numeric (8) | 6 | 8 | 8 |
| — comparison (5) | 5 | 5 | 5 |
| — risk change (4) | 3 | 3 | 4 |
| — refusal (3) | 2 | 3 | 3 |
| Policy violations | 0 | 0 | 0 |
| Numbers verified, pooled | 3.7% (2/54) | **92.8%** (77/83) | 71.5% (143/200) |
| Errors / timeouts | 0 | 0 | 0 |
| Cost per case (est.) | $0.0013 | $0.0063 | $0.0198 |
| Median / p95 latency | 3.8 / 5.6 s | 14.2 / 29.2 s | 50.9 / 71.0 s |

**Reading:**
- **Both agents beat the fixed pipeline on success,** and only the agents produce traceable numbers. C0 writes free text, so 96% of its numbers can't be traced even when they are right.
- **The team is the most reliable:** it completes every risk-change case, because a dedicated risk-diff agent searches both years.
- **But the team costs about 3× C1** and is slower.
- **The team's verified share is lower:** its writer types some figures itself (growth rates, segment amounts) instead of using the code-rendered placeholders. The checker catches every one, so the note can't be approved until it is fixed. That makes it a cost in analyst time, not a correctness failure.
- **Both agents sit below the 98% alert threshold** on this snapshot.

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

## 6. E4: signature ablation ⏳

| | C2 critic loop on | Critic loop off | Plain-text chunks |
|---|---|---|---|
| Task success | | | |
| Numbers verified | | | |
| Notes with unresolved issues at the gate | | | |
| Cost per case | | | |

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
