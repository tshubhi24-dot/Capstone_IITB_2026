# Analyst Desk C0 C1 and C2 Comparison

The capstone brief requires all three configurations in experiment E1 to test whether agent decisions and a team justify their additional cost. C2 is not required to win; the comparison must be fair and the findings accurate.

| Aspect | C0 Fixed workflow | C1 Single agent | C2 Agent team |
|---|---|---|---|
| Structure | Predetermined retrieval and answer pipeline. | One research agent with the research tools. | Supervisor with company researchers and specialist roles. |
| Next action | Code determines the sequence; no agent research decisions. | The agent chooses research tools and next actions. | The lead and specialists coordinate actions within assigned permissions. |
| Company research | Preset searches and financial lookups. | One agent investigates the companies. | Company branches can run concurrently, supported by quant and risk work. |
| Draft and review | Answer from the fixed evidence workflow. | Research findings feed shared drafting and checking stages. | Findings feed a writer, code checks and a separate AI claim critic. |
| Tradeoff to measure | Simpler execution; less adaptive investigation. | Adaptive investigation; one research worker. | Specialist coverage and possible concurrency; added coordination and calls. |

**One agent does not mean one model call.** C1 can make multiple tool and model calls. These descriptions explain the designs, not measured performance or a claim that every current path meets all product policies.

## Same question across three designs

"Compare Microsoft and Alphabet operating margins for FY2022-FY2024 and explain supported changes in risk disclosures."

- **C0:** Run predefined searches and financial lookups, then generate the answer.
- **C1:** Let one research agent select tools and gather evidence before drafting.
- **C2:** Distribute company, quantitative and risk research, then combine and review findings.

## Conditions for a fair comparison

- Use the same questions, permitted sources, model, research tools and total run budget. C2 must share that allowance across its workers. Identify and report any design differences.
- Control memory, prior chat context and playbook settings; keep scoring and source snapshots fixed. A selector in the UI alone does not prove equivalence.
- Report correctness, coverage, policy violations, corrections, errors/timeouts, cost per case and median/p95 latency. Include failures; repeat the final held-out comparison three times and report variation.

**Interpretation:** Choose conclusions from observed quality, cost and time. Parallel architecture does not automatically make C2 faster or better. A verified final advantage is not claimed in this comparison sheet.

Brief references: E1 on printed page 6; Analyst Desk signature challenge B on printed page 16. The brief also separately requires E2 security, E3 lessons and E4 critic/table-parsing ablations. The web choices help run configurations; they do not replace those experiments.

## Observed Results from the Same Prompt

One development run per mode on 9 November 2026, using application revision `42e2298`. Exact shared prompt: "Compare Microsoft and Alphabet operating margins for FY2022-FY2024 and explain supported changes in risk disclosures."

All used GPT-4.1 Mini for research/answer generation; C2 also used Llama 3.3 70B as its critic. Automatic memory and lessons were off, with no prior notes for these two companies. C1/C2 used the deployed HTTP MCP services, user-approved plans with a common evidence/date clarification, and isolated checkpoints. No final note was approved or published.

| Observed measure | C0 Fixed workflow | C1 Single agent | C2 Agent team |
|---|---|---|---|
| Result | Answer returned | Unapproved draft; code check passes | Unapproved draft; aggregate check fails |
| Execution time | 38.22 seconds | 92.34 seconds | 117.10 seconds |
| Model requests | 1 | 15 | 24 |
| Reported tokens | 3,601 | 87,023 | 101,150 |
| Usage cost USD | Up to 0.0058 estimated | Up to 0.0204 mixed basis | 0.0366 provider-reported |
| Margins matching reference | 6 of 6 | 6 of 6 | 6 of 6 |
| Code-verified items | 0 of 6 recognised items | 15 of 15 recognised items | 7 of 7 recognised items |
| Separate AI claim review | Not run | Not run | 2 of 8 selected lines supported; 6 objections |
| Writer revisions | None | None | Two; objections remain |

**What the outputs show**

- **C0:** Correct margin values, but income-only citations omit the revenue/calculation chain, so the checker cannot verify them. Risk themes are presented without an adequate change analysis; performance explanations exceed the retrieved evidence.
- **C1:** Calculation references and a June/December fiscal-year caveat improve inspectability. Risk changes remain under-analysed and several summary explanations lack direct citations. A 15/15 numerical result is not a complete-note pass.
- **C2:** After two revisions it reached the note gate with failed checks. The guard disallows approval in that state; no approval/publication was attempted. The judge mixes genuine gaps with false objections: the disputed 17% exists in the full cited passage, and valid fact-based margins need not appear in narrative text. Claimed "new" risks exceed comparative coverage. The judge's 2/8 is not ground-truth accuracy.

**Measurement limits:** Times include original planning but exclude human approval wait; C0 includes retriever startup. C0 used temperature 0.1 and an 800-token output cap; agents used temperature 0 and a 4,096-token cap per call. No automatic retries were used. Initial C0/C1-plan costs use conservative token-price estimates; later costs use provider usage metadata, not a reconciled invoice. The first two request counts are inferred from successful single-call phases; remaining requests were observed. Recognised-item counts have different denominators. Tracing emitted non-blocking callback warnings. This is one illustrative comparison, not a matched, repeated E1 benchmark or a demonstration of all review controls.

**Decision:** No overall winner or product acceptance is established. Preserve all outputs and investigate narrative support, risk coverage and critic calibration before relying on these notes.
