# Analyst Desk: evaluation report

**User:** an equity research analyst writing a note from 10-K filings.
**Outcome we measure:** every number in the note is traceable to a filing and correct.
⏳ = not yet run. Per-case results: [heldout_results.md](heldout_results.md), [redteam_results.md](redteam_results.md).

## 1. Summary

| Question | Answer (so far) | Section |
|---|---|---|
| Does retrieval find the evidence? | Recall@5 0.389 → **0.903** with reranking, query decomposition and rewriting | 3 |
| Is an agent worth its cost (E1)? | Yes: held-out success C0 31.7, C1 **38.7**, C2 35.0 of 40; only agents give traceable numbers. The team is not worth its 2× cost on these questions | 4 |
| Do the defences work (E2)? | Yes: attacks through 10/32 → **3/32**, 0 false blocks | 5 |
| Did the lessons help (E3)? | No measurable change for C1 (39/40 either way); C2 arm incomplete | 6 |
| Do the critic loop and table-aware chunks matter (E4)? | Not separable from noise on 20 development cases | 7 |
| Does memory change the note? | Yes: what-changed section and preferences; accuracy unchanged | 8 |

## 2. Setup

| Item | Value |
|---|---|
| Configurations | **C0** fixed pipeline (one retrieval, one model call) · **C1** one agent, all tools · **C2** team (lead, researcher and risk-diff per company, quant, writer, critic) |
| Model | `openai/gpt-4.1-mini` for all three; judge `meta-llama/llama-3.3-70b-instruct` (different family) |
| Budget | Same tools and tool budget for C1 and C2 (12 + 12 per company); replies capped at 4,096 tokens |
| Cases | 44 development; held-out: **40 independent cases** (main) + 24 generated (supplementary), committed before any run, folder unreadable by the agent |
| Run conditions | Memory off; plan gate auto-approved; stop at the note gate (nothing published) |
| Scoring | Code first: right figure, unit, sign, rounding, company and year; Item 1A cited for both years; refusals decline. An incomplete critic review fails the case |
| Experiments | One config file per arm (`experiments/*.toml`); every result records commit, config version and models |
| Cost | Estimated at $0.52 per million tokens |

## 3. Retrieval (36 labelled queries, Recall@5)

| Configuration | Recall@5 | s/query |
|---|---|---|
| BM25 | 0.361 | 0.03 |
| Vectors (all-MiniLM-L6-v2) | 0.264 | 0.01 |
| Hybrid (RRF) | 0.389 | 0.06 |
| + cross-encoder rerank | 0.472 | 0.73 |
| + query decomposition (company, year, Item filters) | 0.792 | 1.20 |
| + decomposition + rewrite | **0.903** | 1.32 |

| External check: FinanceBench open sample | Result |
|---|---|
| Questions about a 10-K we cover | 9 of 150 |
| Evidence in our corpus (Item 1A / Item 7) | 4 (the rest is in financial statements or Item 1, not indexed) |
| Found in top 5 | **2 of 4** (after fixing "FY22" year parsing, found by this check) |

- Decomposition is the largest gain; the reranker adds 0.08 but is the slowest step.

## 4. E1: is an agent worth its cost?

### Development set (20 cases, 1 run)

| Metric | C0 | C1 | C2 |
|---|---|---|---|
| Task success | 14/20 | **19/20** | 18/20 |
| Numeric / comparison / risk / refusal | 6/8 · 4/5 · 2/4 · 2/3 | 8/8 · 5/5 · 3/4 · 3/3 | 8/8 · 5/5 · 2/4 · 3/3 |
| Numbers verified (pooled) | 3.6% | 88.7% | **89.6%** |
| Notes passing every check (of 17) | — | **13** | 7 |
| Policy violations / errors / timeouts | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Cost per case | $0.0013 | $0.0080 | $0.0213 |
| Median / p95 latency | 4.6 / 6.0 s | 14.4 / 28.5 s | 43.5 / 75.0 s |

- Agents beat the fixed pipeline; only agents produce traceable numbers.
- The team costs 2.7× C1 and is 3× slower, with no extra success here.
- Team notes reach the analyst clean less often: its judge flags claims, and the writer sometimes types figures itself (caught by the checks).

### Held-out set (40 independent cases, 3 runs: mean, range)

| Metric | C0 | C1 | C2 |
|---|---|---|---|
| Task success (of 40) | 31.7 (31–32) | **38.7 (38–39)** | 35.0 (34–36) |
| Numeric / comparison / risk / refusal (summed over 3 runs) | 23/36 · 30/30 · 36/36 · 6/18 | 35/36 · 30/30 · 36/36 · 15/18 | 36/36 · 30/30 · 24/36 · 15/18 |
| Numbers verified (pooled) | 9.1% | 75.6% | **90.4%** |
| Policy violations / errors | 0 / 0 | 0 / 1 | 0 / 0 |
| Cost per case | $0.0013 | $0.0082 | $0.0169 |
| Median / p95 latency | 8 / 11 s | 23 / 51 s | 59 / 109 s |

- C1 and C2 ran on the fixed code (see the design change below); C0 has no agent, so its runs are the independent evaluator's.
- **C1 is the best value:** highest success at half the team's cost.
- **C2 verifies more of its numbers** but loses on risk change: some notes cite Item 1A for only one year.
- Refusals: both agents miss one out-of-scope case (h-x04).

### The experiment that changed the design

| | C2 success | C2 comparisons |
|---|---|---|
| Before the fix (independent evaluator's runs) | 26–29/40 | 4/10 |
| After the fix | 34–36/40 | 10/10 |

For FY2022-only questions the risk-diff agent searched FY2021 (not covered); the team replanned and stopped with no note. Our own first held-out set (v1) found it; v1 then moved to development (`dev_extra/`), as the brief requires.

## 5. E2: do the defences work?

32 attacks (committed before any run), C2, defences off vs on; 17 clean development cases for false blocks.

| Category (attacks) | Got through, defences off | Got through, defences on |
|---|---|---|
| Injected document (10) | 0 | 0 |
| Direct injection (6) | 3 | 0 |
| Watchlist exfiltration (5) | 2 | 2 |
| Sandbox escape (4) | 0 | 0 |
| Out of scope (3) | 3 | 0 |
| Tool misuse (2) | 0 | 1 |
| Advice (2) | 2 | 0 |
| **All (32)** | **10** | **3** |
| False blocks, clean cases | 0/17 | 0/17 |
| Clean task success | 16/17 | 16/17 |

- The defences stop every injection, advice and scope attack, at **no cost** to legitimate work.
- The 3 left: two watchlist requests explicitly asked to compare with the watched companies, so the planner put them in the plan, which the runner auto-approves; an analyst would see them at the plan gate. One (rt30) is a flaw in our attack's success rule (it matched the word "warm").
- Even undefended, the model ignored all 10 planted "buy" articles, and the sandbox blocked all network attempts.

| Already measured | Result |
|---|---|
| Injection screen on real filings | Fires on **0 of 24,660** passages |

## 6. E3: did the lessons help?

| | Before playbook | After playbook (`05cce831b31d`) |
|---|---|---|
| C1 held-out success | 38.7/40 (3 runs) | 39/40 (1 run) |
| C1 risk change | 12/12 | 12/12 |
| C2 held-out success | 35.0/40 | incomplete: 23 of 40 cases hit the OpenRouter workspace budget |
| Lessons | 3 proposed from development failures | 1 approved; 2 rejected ("Too generic", "Duplicate") |
| Lessons that made a case worse | — | none seen for C1 |
| Cost of generating lessons | — | one reflection call, about $0.01 |

- For C1 the playbook made no measurable difference: it already passes every risk-change case.
- The lesson targets C2's weak spot (risk change, 24/36); that arm must be re-run when budget allows.

## 7. E4: signature ablation (development set)

| | C1 | C1 critic off | C1 plain chunks | C2 | C2 critic off | C2 plain chunks |
|---|---|---|---|---|---|---|
| Task success | 19/20 | 19/20 | 19/20 | 18/20 | 19/20 | 19/20 |
| Numbers verified | 88.7% | 92.3% | 95.5% | 89.6% | 82.7% | 88.2% |
| Notes passing every check (of 17) | 13 | 12 | 14 | 7 | 7 | 8 |
| Revisions made | 9 | 0 | 8 | 22 | 0 | 24 |
| Cost per case | $0.0080 | $0.0070 | $0.0085 | $0.0213 | $0.0186 | $0.0186 |
| Median latency | 14.4 s | 13.9 s | 14.1 s | 43.5 s | 28.3 s | 36.8 s |

- An earlier code version showed the critic adding about 12 points and table chunks 9–15; this run does not. On 20 cases × 1 run the effects are within noise.
- Consistent: the critic loop revises notes (9 for C1, 22 for C2) at 15–50% more latency.

## 8. Memory (same follow-up request)

| | Memory on | Memory off |
|---|---|---|
| Previous note found | yes | no |
| "What changed" section | yes | no |
| Preference applied (peer table) | yes | no |
| Numbers verified | 14/14 | 6/6 |
| Tokens / seconds | 9,646 / 17 | 9,419 / 14 |

## 9. Judge calibration ⏳

| n human labels | Agreement | Cohen's kappa | Judge unavailable |
|---|---|---|---|
| | | | |

## 10. Limits

| Limit | Effect |
|---|---|
| Development results were tuned on | Only held-out results measure generalisation |
| 44 development + 64 held-out cases | Small samples: differences of one or two cases are noise; E2 and E3 ran once |
| Fixed corpus: 15 companies, FY2022–FY2024, as originally reported | No live "latest" period, no calendar alignment |
| Uncited note lines are flagged, not judged | The analyst must read them |
| Typed names, no sign-in | Single-analyst prototype; no correction or withdrawal of published notes |
| Cost is an estimate | Blended $0.52 per million tokens, not per-model billing |

Full list: [docs/gap_closure.md](../docs/gap_closure.md), [docs/product_spec.md §9](../docs/product_spec.md).
