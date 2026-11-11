# Workflow, step by step — traced with Microsoft

One request followed from end to end, with the real data at each hop. The
request is dev case **`d01`** from `data/evaluation/dev_cases.jsonl`:

> "What was Microsoft's operating margin in fiscal 2024?"

Every number below was produced by running the code against the committed
data, not written by hand. Reproduce any step with the snippets given.

---

## Step 0 — Before any question: two ingest paths

Both run once and are committed, so query time never touches the network.

### Numbers — `edgar.py` → `data/edgar_cache/0000789019.json`

The whole XBRL `companyfacts` blob for CIK `0000789019`, saved verbatim from
the API (the only transformation is `json.loads` on the way back in):

| | |
|---|---|
| size | 5.4 MB |
| concepts | 572 (`us-gaap` 562, `dei` 3, `ecd` 7) |
| fact entries | 32,711 |
| periods ending | 2007 → 2026 |
| forms | 10-Q 20,032 · 10-K 10,429 · 8-K 1,770 · 10-Q/A 440 · DEF 14A 40 |

**One file per company, keyed only by CIK.** Nothing in it is scoped to a year
or a form. All narrowing happens at *read* time in `get_annual_fact`:
`fp == "FY"`, form in `("10-K", "10-K/A")`, `end[:4] == "2024"`, duration ≥ 350
days.

Why the filters matter — FY2024 revenue appears **three times** in the blob:

| value | filed | accession | |
|---|---|---|---|
| 245,122,000,000 | 2024-07-30 | `0000950170-24-087843` | ← FY24's own 10-K |
| 245,122,000,000 | 2025-07-30 | `0000950170-25-100235` | FY25 10-K, comparative column |
| 245,122,000,000 | 2026-07-29 | `0001193125-26-323660` | FY26 10-K, comparative column |

Identical period, identical value, three different filings, because each 10-K
restates two prior years as comparatives. `min(annual, key=filed)` resolves it
to the FY24 document — the same filing the passages were chunked from. This is
why the accession is in `fact_id` and not just `concept/year`: it names *which
of the three* was cited.

> EDGAR's own `frame: "CY2024"` annotation sits only on the **latest** of the
> three — EDGAR prefers the restated view. We deliberately go the other way and
> ignore `frame` entirely.

### Text — `ingest.py` → `data/passages/MSFT_2024.jsonl`

```
169 passages    item1a: 96, item7: 73    |    text: 160, table: 9
```

Tables are kept as tables. `MSFT_2024_item7_016` is literally:

```
SUMMARY RESULTS OF OPERATIONS
(In millions, except percentages and per share amounts) | 2024 | 2023 | Percentage Change
Revenue                     | $245,122 | $211,915 | 16%
Gross margin                | 171,008  | 146,052  | 17%
Operating income            | 109,433  | 88,523   | 24%
Net income                  | 88,136   | 72,361   | 22%
Diluted earnings per share  | 11.80    | 9.68     | 22%
```

Then `retrieve.py` builds `.runtime/index/` (Chroma, 296 MB) over those chunks.

**Note what this gives us: two independent witnesses to the same number.** The
XBRL fact says `245122000000`; the MD&A table cell says `$245,122`. That
redundancy is what `checks.py` exploits in Step 6.

---

## Step 1 — `input_guard` (code, no LLM)

`analystdesk/agent/graph.py` · `input_guard`

```python
find_companies("What was Microsoft's operating margin in fiscal 2024?")  # -> ["MSFT"]
find_years(...)                                                          # -> [2024]
```

Both in coverage, no advice wording, so:

```python
{"ok": True, "reason": None, "companies": ["MSFT"], "years": [2024]}
```

A question about Tesla or FY2019 ends the run here, before a single token is
spent — the Phase 0 answer ("fail fast before spending API quota") made real.
`find_companies` / `find_years` live in `query.py`, which is stdlib-only.

---

## Step 2 — `plan`, then the first human gate

The planner LLM returns a typed `Plan` (companies, fiscal_years,
sub_questions, outline). Then **code overrides the model**:

```python
p.companies    = [c.upper() for c in p.companies if c.upper() in _TICKERS] or state["guard"]["companies"]
p.fiscal_years = [y for y in p.fiscal_years if y in COVERED_YEARS]        or list(COVERED_YEARS)
```

The model proposes companies; code decides them. `review_plan` then calls
`interrupt()`, which suspends the graph on the SQLite checkpointer. The analyst
approves or edits; an edited plan is re-validated through the same `Plan` model.

---

## Step 3 — `research` (ReAct loop)

Recorded tool traces for this exact question
(`data/evaluation/archive/pre_cleanup_20261111/eval_dev_merged.json`):

| Config | Tool calls | Tokens | Seconds |
|---|---|---|---|
| C1 | `get_financials`, `get_financials`, `run_python` | 7,010 | 11.3 |
| C2 | 5× `search_filings`, `get_financials`, `run_python`, 2× `search_filings`, 6× `get_passage` | 27,345 | 35.7 |

C1 asked EDGAR twice (FY2024 and FY2023), then handed the division to the
sandbox. It never did the arithmetic itself — enforced two ways: the
`RESEARCHER` prompt says *"Never do arithmetic yourself"*, and the `quant`
agent's allow-list holds only `get_fact`, `get_financials`, `run_python`.

Every call passed through `hooks.pre()` first:

- **permission** — is this tool in the caller's `AGENT_TOOLS` entry?
- **budget** — `CALLS_PER_SPECIALIST` / `MAX_TOOL_CALLS`
- **rate limit** — `EDGAR_MIN_INTERVAL_S = 0.1`, i.e. ≤ 10 req/s as SEC asks

A denied call is returned as a normal tool result (`PERMISSION_DENIED`,
`BUDGET_EXCEEDED`), so the agent adapts instead of crashing. The hooks are
code, not prompt text: the model cannot talk its way past them.

What `get_financials(cik="0000789019", 2024)` returned:

```
revenue           245122000000   2023-07-01 → 2024-06-30   filed 2024-07-30
                  fact_id  RevenueFromContractWithCustomerExcludingAssessedTax/2024/0000950170-24-087843
operating_income  109433000000
                  fact_id  OperatingIncomeLoss/2024/0000950170-24-087843
pretax_income     107787000000
                  fact_id  IncomeLossFromContinuingOperationsBefore.../2024/0000950170-24-087843
restated          None  (all three)
```

All three facts come from XBRL. The **margin does not** — it is computed in
Python (Step 4). Rule 1: no arithmetic in a prompt, and none borrowed from
EDGAR either.

---

## Step 4 — `build_figures` (code) — the load-bearing step

`analystdesk/agent/figures.py`

Before the writer may type anything, code computes **every figure it could
legitimately want**. For `["MSFT"], [2022, 2023, 2024]` that is 18 placeholders:

```
{MSFT_2022_revenue}            Microsoft FY2022 revenue: $198,270.0M
{MSFT_2022_period_end}                                   2022-06-30
{MSFT_2022_operating_income}                             $83,383.0M
{MSFT_2022_margin}             operating margin:         42.06%
{MSFT_2023_revenue}            Microsoft FY2023 revenue: $211,915.0M
{MSFT_2023_period_end}                                   2023-06-30
{MSFT_2023_operating_income}                             $88,523.0M
{MSFT_2023_margin}             operating margin:         41.77%
{MSFT_2023_revenue_growth}     vs FY2022:                6.88%
{MSFT_2023_income_growth}      vs FY2022:                6.16%
{MSFT_2023_margin_change}      vs FY2022:                -0.28 pp
{MSFT_2024_revenue}            Microsoft FY2024 revenue: $245,122.0M
{MSFT_2024_period_end}                                   2024-06-30
{MSFT_2024_operating_income}                             $109,433.0M
{MSFT_2024_margin}             operating margin:         44.64%
{MSFT_2024_revenue_growth}     vs FY2023:                15.67%
{MSFT_2024_income_growth}      vs FY2023:                23.62%
{MSFT_2024_margin_change}      vs FY2023:                +2.87 pp
```

Reproduce with:

```python
from analystdesk.agent.figures import build_figures, figures_table
print(figures_table(build_figures(["MSFT"], [2022, 2023, 2024])))
```

`figures_table()` shows the writer only the placeholder, the label and the
value — **never the provenance tag**. The tag is added by code in Step 5.

Banks get `{T_Y_pretax_income}` instead of `{T_Y_operating_income}`, selected
by `Company.margin_basis`, so margins on different bases are never compared.

---

## Step 5 — `write` → `render`

The LLM emits placeholders, not numbers:

```markdown
## Microsoft FY2024

Revenue reached {MSFT_2024_revenue}, up {MSFT_2024_revenue_growth} on FY2023.
Operating margin was {MSFT_2024_margin}, a change of {MSFT_2024_margin_change}.
Gross margin rose 17% [MSFT_2024_item7_016].
```

`render()` then substitutes the value **plus its provenance**:

```markdown
## Microsoft FY2024

Revenue reached $245,122.0M [fact: RevenueFromContractWithCustomerExcludingAssessedTax/2024/0000950170-24-087843],
up 15.67% [growth: RevenueFromContract.../2024/0000950170-24-087843 / RevenueFromContract.../2023/0000950170-23-035122] on FY2023.
Operating margin was 44.64% [calc: OperatingIncomeLoss/2024/0000950170-24-087843 / RevenueFromContract.../2024/0000950170-24-087843],
a change of +2.87 pp [diff: OperatingIncomeLoss/2024/0000950170-24-087843 / RevenueFromContract.../2024/0000950170-24-087843
 - OperatingIncomeLoss/2023/0000950170-23-035122 / RevenueFromContract.../2023/0000950170-23-035122].
Gross margin rose 17% [MSFT_2024_item7_016].
```

**This is the central idea of the project: the model chooses *which* figure to
mention; code decides *what it says*.** A mistyped or invented reported number
is not a bug to be caught downstream — it is a state the pipeline cannot reach.

Note that `[diff: ...]` spans two accessions (`-24-087843` and `-23-035122`),
so even a *change* in margin is traceable to both filings it came from. Unknown
placeholders are returned as `render_issues` and fed to the checker.

---

## Step 6 — `check_note` (code, not an LLM)

`analystdesk/agent/checks.py`. Every number must be traceable in one of three
ways, each verified arithmetically:

1. `[fact: ...]` — the shown value equals the XBRL fact in $M to 1 decimal
2. `[calc: A / B]` (= A/B×100), `[growth: A / B]` (= (A/B−1)×100),
   `[diff: A/B − C/D]` (percentage points) — recomputed to 2 decimals
3. a quoted figure — must occur, **with the same unit**, in a passage cited on
   the same line

On the rendered note above:

```
ok=True   verified=5/5 (100.0%)
```

On a draft where the model misbehaved:

```
ok=False  verified=1/5 (20.0%)
  48.00% is wrong: OperatingIncomeLoss/2024/... / RevenueFromContract.../2024/... = 44.64%
  Number '$500' has no source: use a figure placeholder, or quote it from a filing
  Number '$31.0 billion' has no source
  Number '95%' does not appear in the passage(s) cited on its line (MSFT_2024_item7_017)
  Investment-advice wording 'We recommend' is not allowed in a research note
  Investment-advice wording 'buy' is not allowed in a research note
  Investment-advice wording 'price target' is not allowed in a research note
```

The `95%` case is the strongest: the checker opened the cited passage and
confirmed the figure is not in it. `_quoted_in` requires a unit match, so a
bare `95` elsewhere in the passage would not pass either.

Issues go back to `write` (`MAX_REVISIONS = 2`), then on to the gate regardless
— the human catches what the loop cannot fix. In C2 the same node also runs the
compliance critic: a judge from a different model family (`JUDGE_MODEL`,
default `meta-llama/llama-3.3-70b-instruct`) checking each cited claim against
its passage, *on top of* the code checks.

---

## Step 7 — the note gate → `approval.sign`

`interrupt()` again, with the exact draft and the check result. The analyst
approves, edits (→ back to `check`) or rejects (→ `END`). On approval:

```
token: eyJhcHByb3ZlZF9hdCI6ICIyMDI2LTEwLTI1VDA5OjA4OjI1KzAwOjAwIiwgImFwcHJvdmVy...

verify, unchanged    → {'approver': 'analyst', 'note_sha256': '9e7dfee55cce6281...'}
verify, "Buy." added → ApprovalError: note differs from the approved version;
                        it must be approved again
```

An HMAC over the note hash, so the signature binds to the exact bytes the human
read. One word added invalidates it.

---

## Step 8 — `publish`, then memory

`publish_note` is the only write tool anywhere, and `AGENT_TOOLS` gives it to
`publisher` alone:

```
single_agent   get_fact, get_financials, get_passage, get_past_notes, list_filings, run_python, search_filings
planner        list_filings
researcher     get_passage, search_filings
quant          get_fact, get_financials, run_python
risk_diff      get_passage, get_past_notes, search_filings
critic         get_fact, get_passage
writer         (none)
publisher      publish_note                                    ← the only WRITE
```

The portal **re-hashes the note and verifies the HMAC itself**, so a skipped
gate or an injected "publish this" still cannot write. On success,
`remember_published_note` stores it, and the next MSFT request gets a
code-computed "what changed since our last note" block.

---

## The same question through all three configs

### This question (`d01`)

| | C0 fixed | C1 single agent | C2 team |
|---|---|---|---|
| verified | **0/1** | 4/4 | 8/8 |
| tokens | 2,168 | 7,010 | 27,345 |
| seconds | 12.3 | 11.3 | 35.7 |

### All 20 dev cases

| | C0 | C1 | C2 |
|---|---|---|---|
| success | 16/20 | 19/20 | **20/20** |
| numeric | 6/8 | 8/8 | 8/8 |
| comparison | 5/5 | 5/5 | 5/5 |
| risk_change | 3/4 | 3/4 | **4/4** |
| refusal | 2/3 | 3/3 | 3/3 |
| verified share (mean) | 31.7% | **96.6%** | 80.2% |
| policy violations | 0 | 0 | 0 |
| cost / case | $0.0013 | $0.0063 | $0.0198 |
| latency median | 3.8 s | 14.2 s | 50.9 s |
| latency p95 | 5.6 s | 29.2 s | 71.0 s |

C2 buys the last `risk_change` case for ~3× the tokens and ~3.6× the latency of
C1.

---

## Open points to be ready for

1. **The 31.7% → 96.6% verified-share gap measures two things at once.** C0 has
   no placeholder/render step: `c0_pipeline.py` hands the model a context block
   tagged `[fact_id: ...]` and *asks* it to cite them, with no checker in the
   loop. So part of C0's score reflects "does not use the render mechanism"
   rather than "gets numbers wrong" — its own `ResearchNote.verification_pct()`
   is 100%. Honest framing: C0 → C1 measures **prompt-level vs code-enforced
   grounding**; the pure orchestration comparison is C1 → C2.

2. **C2 verifies worse than C1** (80.2% vs 96.6%) while succeeding more often —
   likely because the specialists surface segment figures that must be
   passage-quoted rather than placeholder-rendered. Worth a line in
   `viva_notes.md`.

3. **`edgar.py` is no longer third-party-free.** `fetch_company_facts` does
   `from .observability import EDGAR`, and `observability.py` imports
   `prometheus_client` at module level with no fallback — so
   `python -m analystdesk --mode baseline` (the Phase 1 evidence command) fails
   with `ModuleNotFoundError` in an environment that has not installed the
   Phase 8 dependencies. A `try/except ImportError` with no-op counters would
   restore both the command and the stated convention.

4. **Ingest artefact:** `MSFT_2024_item1a_000` begins `"K FACTORS"` — the
   splitter ate `RIS` from the `RISK FACTORS` heading. Cosmetic, but it is the
   first passage of every Item 1A, so it shows up in retrieval output.
