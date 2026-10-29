# Analyst Desk: viva notes

These notes explain what was built, why it was built that way, what else was considered, and the questions an examiner is likely to ask. Each section ends with evidence you can show. The notes grow as the project grows.

Read [architecture.md](architecture.md) for the diagram and [plan.md](plan.md) for the phases. These notes explain the reasoning behind both.

---

## 0. The project in one minute

**What it does.** An equity research analyst asks something like "Compare Microsoft's and Alphabet's operating margins over the last three years and tell me what changed in their risk factors." A team of agents reads the companies' annual reports (10-Ks) and pulls the exact reported numbers from SEC XBRL data. It calculates ratios in code, compares years and companies, and drafts a note. Every number in the note links to its source. The analyst signs the exact note before anything is published.

**Why it is hard.** A single wrong number destroys trust in a research note. Language models are bad at arithmetic, and they mix up fiscal years and units. The design therefore keeps numbers and arithmetic out of the model entirely: the model only chooses and explains.

**The three rules** (from the brief; quote them):
1. The model proposes; code and people decide.
2. Outside text is data, never instructions.
3. A person approves each exact change to the outside world.

**Scope.** 15 companies in two sectors, three fiscal years each (2022–2024), giving 45 company-years.
- **Technology:** MSFT, GOOGL, AAPL, AMZN, META, NVDA, AMD, ORCL.
- **Finance:** JPM, GS, BAC, V, MS, MA, WFC.

---

## 1. Numbers: where they come from and why we trust them

### 1.1 XBRL from SEC EDGAR

**What.** Every US-listed company files its financial statements with machine-readable tags (XBRL). SEC publishes them free as JSON, one file per company ("companyfacts"). Each fact has a concept name (for example `OperatingIncomeLoss`), a value in dollars, a period (start and end dates), and the accession number of the filing it came from.

**Why.** This is exact ground truth that needs no labelling. The brief says "XBRL gives exact truth". It is also what makes signature challenge A possible: every number can be checked by code.

**Code:** [analystdesk/edgar.py](../analystdesk/edgar.py), functions `fetch_company_facts` and `get_annual_fact`.

### 1.2 The fact_id

**What.** Every number carries an ID of the form `{concept}/{fiscal_year}/{accession}`, for example `OperatingIncomeLoss/2024/0000950170-24-087843`.

**Why.** The accession number identifies one exact SEC filing. Anyone can open it on EDGAR and check the number by hand. The compliance critic (built later) checks every number in a draft against its fact by code, not by asking an LLM.

### 1.3 Fiscal-year alignment (signature challenge A)

**What.** We match a fact to a fiscal year by the year in which the reporting period **ends**, not by EDGAR's own `fy` field.

**Why.** Fiscal years differ between companies:

| Company | Fiscal year ends |
|---|---|
| Microsoft | June |
| Apple | September |
| Oracle | May |
| NVIDIA | late January |

EDGAR's `fy` field describes the *filing*, not the period, so it can point at the wrong year. "FY2024" for NVIDIA means the year that ended January 2024. The same rule is used when picking which 10-K to read text from, so numbers and text always come from the same year.

**Likely question:** "Microsoft's FY2024 and Alphabet's FY2024 cover different months. Is comparing them fair?"
**Answer:** They are each company's own fiscal year, which is the standard basis analysts use. We never relabel periods. Each row shows its `period_end` so the reader can see the difference, and the note must say so whenever fiscal years don't line up.

### 1.4 Full-year facts only

**What.** A fact only counts if its period is at least 350 days long.

**Why.** 10-Ks also tag quarterly tables. BAC's 10-K tags quarterly revenue with the same `FY` marker. Without this check the code could quietly return one quarter's revenue as the annual figure. A test locks this behaviour in.

### 1.5 As originally reported vs restated

**What.** When several 10-Ks report a value for the same year, we take the **earliest**, which is that year's own 10-K. If a later filing restated the value, we keep the original and add a warning to the note.

**Why (real example).**
- BAC's FY2024 10-K reports total revenue of **$101,887M**.
- Its FY2025 10-K restated FY2024 to **$105,856M** after an accounting change.
- The old code took the latest value. That gave a number different from what the analyst sees in the FY2024 filing, and a fact_id pointing at a different document from the passages we retrieve.

Restatements found: BAC FY2023 and FY2024, WFC FY2022.

**The same rule applies across concept names.** Alphabet tagged its FY2024 revenue as `RevenueFromContractWithCustomer...` in the FY2024 10-K, but as `Revenues` only in a 2026 filing. We take the earliest-filed fact across all of a company's revenue concepts, so the citation still points at the FY2024 10-K. A test ([tests/test_data_integrity.py](../tests/test_data_integrity.py)) checks that all 90 fact_ids (45 company-years × revenue and income) cite that year's own 10-K, the same document the passages come from.

**Alternative considered:** always use the latest (restated) values, so every year sits on one accounting basis. It was rejected as the default because citations must match the document we quote. Restated values are still shown, as warnings.

**Likely question:** "Which is right, the original or the restated number?"
**Answer:** Both are right for different purposes. As-reported matches the filing being cited. Restated gives like-for-like trends. We cite the as-reported figure and make the restatement visible, so the analyst can choose. Code never silently swaps them.

### 1.6 Banks use pre-tax margin

**What.**
- **Tech companies, Visa and Mastercard:** operating margin = operating income ÷ revenue.
- **JPM, GS, BAC, MS and WFC:** pre-tax margin = pre-tax income ÷ net revenue.
- Each row records its `margin_basis`, which is fixed per company in [scope.py](../analystdesk/scope.py).

**Why.**
- Banks don't report an "operating income" line. Their income statement is built around net interest income, so the XBRL concept simply isn't there.
- Pre-tax income is reported by all 15 companies.
- For banks, net revenue (revenue after interest expense) is the meaningful top line.

**Rule:** margins on different bases are never compared with each other. The basis is fixed per company in code, so it can't switch from one year to the next.

**Likely question:** "Why not just compare everyone on pre-tax margin?"
**Answer:** The brief's example request is about operating margin, and for tech companies operating margin is the standard measure. Using pre-tax for everyone would lose that. We chose correctness per sector over one number for everyone.

### 1.7 Arithmetic lives in code

`baseline.py` converts dollars to millions and computes margins in Python. The LLM never computes. The brief's "watch out for" list says it directly: "Do not calculate numbers inside the LLM."

**Evidence to show:** run the C0 baseline across all 15 companies. Verification is 100% (all 45 rows have fact_ids), and the restatement warnings appear.

---

## 2. Reading the 10-Ks (ingestion, L4–L5)

### 2.1 What we extract and why

We extract only **Item 1A (Risk Factors)** and **Item 7 (MD&A: Management's Discussion and Analysis)**.
- Item 1A answers "what changed in their risk factors" (the risk-diff agent).
- Item 7 explains the numbers.

The other items are not needed for the brief.

**Code:** [analystdesk/ingest.py](../analystdesk/ingest.py).

### 2.2 Splitting by Item, not fixed-size chunks

**Why.**
- Items are natural meaning boundaries; Item 1A is always risk factors.
- Every passage gets `item` metadata, which retrieval can filter on.
- The risk-diff agent can compare Item 1A this year against last year.

### 2.3 Real-world filings are messy: the problems we found and fixed

This makes a good viva story, because it shows we checked the output rather than trusting it.

| Company | Problem | Fix |
|---|---|---|
| Mastercard | Every page repeats "ITEM 1A. RISK FACTORS" as a header, and the parser restarted the section each time, so only the last page survived | A heading for the section you're already in is a running header and continues the section |
| Morgan Stanley | No "Item 1A" headings at all; sections are only titled "Risk Factors" | Fall back to section titles when numbered headings aren't found |
| Wells Fargo | The 10-K says "see our Annual Report", and the text is in a separate exhibit | If a section is too short, parse the largest exhibit in the filing |
| Visa | Cross-reference links render as bare "Item 8" lines | A heading must be followed by "." or a space |
| Bank of America | "Item 1A. Risk Factors" appears as a link inside MD&A | Items run in order, so a backward jump deep inside a section is a reference, not a heading |
| JPMorgan | No numbered body sections, so MD&A ran on into the financial statements | MD&A ends at the auditor's report heading |

**Result:** before the fixes, MS had 0 passages and WFC had 1. After them, all 45 company-years have both items. Each case has a unit test in [tests/test_ingest.py](../tests/test_ingest.py).

### 2.4 Tables kept as tables

**What.** HTML tables become rows like `Revenue | $245,122 | $211,915`. Each table is its own passage, with `kind: "table"`, prefixed by the line above it (usually its title). A large table is split by rows, repeating the header row, and never cut mid-row.

**Why.**
- When tables are flattened, numbers lose their labels; JPM chunks looked like `7 // 6 // — // ( // 1 // )`.
- The brief asks for "keep tables as tables". It is also half of the E4 ablation: table-aware vs plain-text chunks.
- Signature challenge A says every number links to "an XBRL fact or cited table cell". A table passage is what makes a cell citable.

**Nice demo:** Microsoft's FY2024 MD&A segment table ends with `Total | $245,122`, exactly the XBRL revenue fact. Text and structured data agree.

**Layout vs data tables.** 10-Ks also use tables just for layout (an item heading in a two-cell table). Only tables with 2+ rows and 2+ numeric cells are treated as data. Otherwise heading detection would break.

**The plain variant** (tables flattened) is kept in `data/passages_plain/` for E4.

### 2.5 Passage metadata

Each passage stores: `passage_id`, `company`, `fiscal_year`, `item`, `kind` (text or table), `accession` (which filing), and `text`.
- The passage_id is cited in answers.
- The accession ties a quote to the exact filing.

### 2.6 Caching and being polite to SEC

SEC asks automated users to identify themselves (a User-Agent with contact email) and to stay under 10 requests per second. Everything is cached on disk: companyfacts JSON, filing lists and 10-K HTML. Only the first run touches the network.

**Committed to git for the team:** passages and the JSON. Not committed: the 284 MB of raw HTML and the vector index, which are rebuilt locally.

**Why commit the passages?** Everyone gets identical inputs, so evaluation numbers are reproducible across the team.

---

## 3. Retrieval (L5–L6)

**Code:** [analystdesk/retrieve.py](../analystdesk/retrieve.py), [analystdesk/query.py](../analystdesk/query.py).

### 3.1 BM25 (keyword search)

BM25 scores passages by shared words. Rare words weigh more, and very long passages are penalised. It is good at exact terms: "Cerner", "asset cap", "First Republic", and exact numbers.

### 3.2 Vector search (semantic)

Each passage is turned into an embedding with `all-MiniLM-L6-v2`, a small local model that needs no API cost or GPU. Embeddings are stored in Chroma. A query finds passages that are close in meaning even when the wording differs ("healthcare company Oracle acquired" finds "Cerner").

### 3.3 Reciprocal Rank Fusion (RRF)

**What.** Merge the BM25 list and the vector list with score = Σ 1/(60 + rank).

**Why.** BM25 scores and cosine similarities are on different scales and can't be added. RRF only uses rank positions, so nothing needs tuning. A passage ranked high by either method rises to the top.

### 3.4 Cross-encoder reranker

**What.** `cross-encoder/ms-marco-MiniLM-L-6-v2` reads the query and a passage *together* and scores how relevant the passage is.

**Why only on the top 50?** It is much more accurate than comparing separate embeddings, but slow, because it runs once per pair. The cheap retrievers shortlist 50 candidates and the reranker orders them.

### 3.5 Query decomposition (the query-side technique)

**What.** "Compare Visa and Mastercard net revenue 2024" becomes one sub-query per (company, year), each filtered on metadata. The results are merged round-robin (first of each, then second of each).

**Why.** Searched as one query, all five results can come from one company, leaving the other with no evidence. Round-robin guarantees every company and year named gets evidence.

**Rewrite.** Each sub-query has the company name, ticker and year removed ("What was Goldman Sachs' provision for credit losses in 2023?" becomes "What was provision for credit losses in"), because the metadata filter already covers them. See 3.8 for why this matters.

**Why code, not an LLM?** Company names and years can be found exactly from our supported list. That makes it deterministic, free and unit-tested (rule 1). An LLM technique such as HyDE can be compared later.

### 3.6 Engineering fixes made along the way

- **Filter before BM25 ranking.** BM25 used to take the global top 50 and then filter by company, so a filtered search could end up with almost nothing.
- **Index tied to its passages.** The Chroma collection name now includes a fingerprint of the passages. Previously, re-ingesting silently reused embeddings of the old passages.
- **Punctuation-safe tokens.** "revenue," and "revenue" are now the same word.

### 3.7 How retrieval is evaluated

**Labelled set.** [data/evaluation/retrieval_queries.jsonl](../data/evaluation/retrieval_queries.jsonl) has 36 queries:
- 14 table look-ups (exact figures)
- 17 text questions (risk factors and MD&A)
- 5 comparisons across two companies

**A label is evidence, not a passage ID.** Each target names a company, a year, an item, and an evidence string, such as `201,183` for iPhone revenue. A target is found if any of the top 5 passages comes from that company, year and item and contains the evidence.

**Why not label passage IDs?** IDs change whenever chunking changes, and E4 compares two chunkings. Evidence labels work for both.

**Recall@5** is the share of a query's targets found in the top 5, averaged over all queries.

**Honesty points for the viva:**
- The labels were drafted with AI help from the actual filing text. Each evidence string was checked by script to exist in the passages. **A team member must review them** (role 5 in the brief).
- This retrieval set is separate from the 60-case golden set for the full system.

**Results:** see [retrieval_eval.md](retrieval_eval.md) (filled in by `scripts/eval_retrieval.py`). Interpretation is in section 3.8 below.

### 3.8 Results and what they mean

**Final numbers** (Recall@5, 36 queries, v2 labels). Full table: [retrieval_eval.md](retrieval_eval.md).

| Step added | Table-aware passages | Plain passages |
|---|---|---|
| BM25 only | 0.361 | 0.472 |
| Vector only | 0.264 | 0.417 |
| Hybrid (RRF) | 0.389 | 0.472 |
| + cross-encoder reranker | 0.472 | 0.514 |
| + decomposition (filters only) | 0.792 | 0.778 |
| + sub-query rewrite | **0.903** | **0.944** |

**The "before and after one change" required by the minimum bar.** Adding decomposition with rewrite to hybrid+rerank raised Recall@5 from **0.472 to 0.903** (table-aware). That is our query-side technique.

**What each step teaches you (say these in the viva):**

1. **Hybrid beats either method alone.** BM25 and vectors find different things, and RRF keeps the best of both.
2. **Vectors are weakest on numbers.** A small embedding model doesn't "understand" that 201,183 is iPhone revenue. Exact-match search (BM25) and metadata filters matter more for financial look-ups.
3. **The reranker helps** (+0.08), but it's the slowest step: about 0.7–1 s per query on CPU against about 0.06 s without it.
4. **Decomposition is the biggest single gain** (+0.32). Most questions name a company and a year. Filtering on that metadata removes thousands of wrong passages before ranking even starts.
5. **Rewrite adds another +0.11.** Inside a filtered search, the company name and year in the query match the footer on every page ("Goldman Sachs 2023 Form 10-K"), which drowns out the topic. Stripping them lets the real topic words count. We found this by tracing a failure step by step, not by trial and error.

**Table-aware vs plain (the E4 question).** On this set, table-aware parsing did **not** improve Recall@5 (0.903 vs 0.944):
- On table questions both reach 1.000.
- The gap is entirely in the 5 comparison queries (0.5 vs 0.8), which is 3 targets out of 10. That is too small a sample to claim either way.
- Honest reading: table-aware parsing doesn't make passages easier to *find*. Its value is that a found table is *usable*: every number keeps its row and column label, so a number can be cited as a specific cell and checked by code (signature challenge A).
- Recall@5 doesn't measure that. E4 should therefore also be measured downstream: the share of numbers in a generated note that are correct and correctly labelled, with table-aware vs plain passages.

**Two caveats you must volunteer:**

1. **Labels were revised after the first run.** The first run's results are saved in `data/evaluation/results/`, and the original labels in `retrieval_queries_v1.jsonl`. The revision followed one rule, applied to all 36 queries rather than only the failing ones:
   - A target matches on company, year and evidence, without requiring a particular Item. The same fact legitimately appears in both Item 1A and Item 7.
   - A figure in millions also accepts its rounded billions form (`1,028` → `1.03 billion`), because the prose states figures that way.
   - Two abbreviation and paraphrase additions (DMA, export rule).

   Every relaxation came from reading a "miss" that actually *was* a correct answer. Example: the retriever found "Provision for credit losses was $1.03 billion", but the label only accepted "1,028".
2. **This is development data.** The labels were drafted with AI help, and I tuned retrieval while looking at them. A teammate (role 5) should write a fresh held-out retrieval set to confirm the numbers.

**First-run (v1) numbers, for the record:** best configuration 0.653 (table) / 0.694 (plain), before the label rule and the rewrite.

### 3.9 C0 uses the same retrieval as C1 and C2

**What.** The C0 pipeline ([c0_pipeline.py](../analystdesk/c0_pipeline.py)) now retrieves with decomposition and rewrite. It also fetches EDGAR numbers for the companies named in the question, instead of always Microsoft and Alphabet.

**Why.** E1 asks whether agents justify their cost (C0 fixed workflow vs C1 single agent vs C2 team, "same model, tools and budget"). If C0 had weaker retrieval, the agents would look better for the wrong reason. With identical retrieval, any difference comes from orchestration.

**Is C0 still "fixed"?** Yes. Decomposition is deterministic code: the same question always produces the same searches. No model decides what to retrieve. That is the line between C0 and C1.

**Before and after.** Asked "Compare Microsoft and Alphabet operating margins", the old C0 cited Apple passages. The new C0 cites MSFT and GOOGL MD&A. A JPM-vs-GS question used to receive Microsoft's numbers; it now receives JPM's and GS's.

**Likely questions:**
- *"Isn't changing labels after seeing results cheating?"* It would be if we only relaxed the failing ones, or if this were the held-out set. We applied one written rule to every query, kept the original labels and results, and the held-out check is still to be done by someone who didn't tune the system.
- *"Why is the reranker so slow?"* It runs a transformer on each (query, passage) pair: 50 pairs per query, on CPU. A GPU or a smaller candidate pool would cut it.
- *"Why does decomposition help so much?"* Metadata filtering. "Goldman Sachs 2023" narrows about 12,600 passages down to about 560 before any ranking happens.

---

## 4. Practice questions (retrieval and data)

1. Why combine BM25 and vectors instead of using one?
2. What does RRF do, and why not just add the scores?
3. Why rerank only the top 50?
4. Why split 10-Ks by Item?
5. Why keep tables as tables? How would you show it matters? (E4)
6. What is a fact_id, and who checks it?
7. MSFT's year ends in June and GOOGL's in December. How do you compare them?
8. BAC restated its revenue. Which number do you show, and why?
9. Why pre-tax margin for banks?
10. Why are your Recall@5 labels evidence strings rather than passage IDs?
11. Who wrote your labelled queries, and how do you know they're correct?
12. Why is query decomposition done in code and not by the LLM?

---

## 5. Tools over MCP (L7)

**Code:** [analystdesk/servers/](../analystdesk/servers/). Tool list with schemas: [tools.md](tools.md), generated by `scripts/list_tools.py`. Tests: [tests/test_tools.py](../tests/test_tools.py).

### 5.1 What MCP is, in one paragraph

MCP (Model Context Protocol) is a standard way to offer tools to an agent.
- A tool lives in a **server**: a separate process.
- The server publishes each tool's **schema**: its name, description, typed inputs and typed outputs.
- The agent side is a **client**. `langchain-mcp-adapters` reads the schemas and turns each tool into a LangChain tool the LLM can call.
- Messages are JSON-RPC, over stdio during development and HTTP inside Docker.

### 5.2 Why use servers instead of plain Python functions

1. **Least privilege.** Each agent is handed only its tools ([servers/__init__.py](../analystdesk/servers/__init__.py), `AGENT_TOOLS`). A researcher cannot even *see* `publish_note`.
2. **One controlled path to data.** Agents never touch files, the index or SEC directly. Every access goes through a typed, tested interface, which is also where hooks (L14) and traces (L13) attach. The adapter's `tool_interceptors` is that hook point.
3. **Isolation.** The sandbox runs LLM-written code in its own process or container, away from the app and its API key.
4. **Same tools for every configuration.** C1 and C2 use identical servers, so E1 compares orchestration, not tools.

### 5.3 The four servers and eight tools

| Server | Tools | Notes |
|---|---|---|
| filings-kb | `search_filings`, `get_passage` | Hybrid search + rerank + decomposition (section 3); `item` filter so risk-diff can search Item 1A only |
| edgar | `list_filings`, `get_financials`, `get_fact` | Cache only, never calls SEC during a run; as-reported values; no ratios computed here |
| python-sandbox | `run_python` | All arithmetic happens here (rule 1) |
| research-portal | `get_past_notes`, `publish_note` | `publish_note` is the only write in the whole system |

**`get_fact` is the compliance critic's tool.** It takes the exact fact_id cited in a draft and returns the value from **that exact filing** (concept + year + accession). The critic then compares the numbers in code. That is how signature challenge A gets enforced, not just promised.

**Why does the edgar server not compute margins?** The brief puts calculation in the sandbox (the quant agent computes ratios from facts). Keeping the edgar server as raw facts only gives each number a single source.

### 5.4 Errors as results, not crashes

Every tool returns `{"ok": true, ...}` or `{"ok": false, "error": {"code": ..., "message": ...}}`, with codes such as NOT_IN_COVERAGE, NOT_FOUND, BLOCKED and APPROVAL_INVALID ([common.py](../analystdesk/servers/common.py)).

**Why.** An agent that asks for TSLA or FY2019 gets a readable "not covered" answer and can re-plan; an exception would end the run. Unexpected bugs are also caught and returned as INTERNAL, so a broken tool never kills an agent run.

### 5.5 Read vs write marking

Each tool carries MCP's standard annotations (`readOnlyHint`, `destructiveHint`) in its published schema. A test checks that every tool is marked, and that only `publish_note` is a write. A second test checks that only the publisher agent holds a write tool.

### 5.6 Approval enforced on the server (rule 3, L14)

**How it works** ([approval.py](../analystdesk/approval.py)):
- When the analyst approves, the approval gate signs the **exact note** (SHA-256 of title + body + tickers) with a secret key. This is an HMAC.
- `publish_note` re-hashes the note it receives and checks the signature.

**What this guarantees:**
- **An edit after approval fails**, with "note differs from the approved version; it must be approved again". This is the L14 demo.
- **An agent cannot approve itself.** Making a token needs the secret key, which never enters a prompt or reaches an agent.
- **Enforced in the server, not only in the graph.** Even if a bug or an injected instruction skipped the approval step, the write is still refused.

**Likely question:** *"Why not just compare a hash of the note?"* Anyone, including a hijacked agent, can compute a hash, so a plain hash proves nothing. The secret key is what turns it into a signature that only the approval gate can produce.

### 5.7 The sandbox: two layers, and honesty about each

**Layer 1: in the process** ([sandbox_runner.py](../analystdesk/servers/sandbox_runner.py)):
- **An import guard.** User code may import only pandas, numpy, math and similar.
- **Python audit hooks.** These refuse network connections, starting processes, loading native libraries and writing or deleting files, at the moment it happens.

**Why both are needed (a finding worth telling).** pandas itself loads `socket` and `ctypes`. A later `import socket` in user code therefore raises no import event, so an audit-hook-only design has a hole. Hence the import guard for user code, *plus* hooks on the actions themselves. Example: `pd.read_csv("http://...")` is caught at the network lookup, even though no import happened.

**Results of the local attack checks:** `import socket`, `import os`, urllib, reading a URL through pandas, writing a file, and code that catches the block and carries on were all blocked and reported as BLOCKED. Infinite loops are stopped by the time limit. The sandbox process starts with an empty environment, so it never sees the API key.

**Layer 2: the container** ([docker/sandbox/Dockerfile](../docker/sandbox/Dockerfile)): no network at all, read-only filesystem, non-root user, all Linux capabilities dropped, plus memory, CPU and process limits.

**Say this in the viva:** layer 1 is a *guard*, not a security boundary, because Python code can find ways around in-process checks. The container is the boundary. `SANDBOX_MODE=auto` uses Docker when it's available, and every result reports which mode ran, so traces show it.

**Proof that the container is a boundary on its own.** We ran *unguarded* Python inside the container: our runner and its import guard were bypassed entirely, with the same `docker run` settings. Results:

| Attack | Result |
|---|---|
| DNS lookup / connect to 1.1.1.1 / HTTP request | Failed: "Network is unreachable" (`--network none`) |
| Overwrite the runner or `/etc/passwd` | Failed: read-only filesystem / permission denied |
| Write to `/tmp` | Allowed, as intended (16 MB scratch, discarded afterwards) |
| Who am I? | uid 65534 (`nobody`), not root |
| Start 65 processes (fork bomb) | Refused at the limit of 64 |
| Look for secrets in the environment | Only `GPG_KEY`, the official Python image's public signature fingerprint; the API key never enters the container |

So the two layers are independent. The guard catches attacks early, with clear BLOCKED errors for the trace. The container stops them even if the guard is bypassed. That's **defence in depth**.

**Cost:** each `run_python` call in Docker takes about 2–3 seconds (container start-up), against about 0.5 seconds locally. That's acceptable for 5–10 calculations per note, and it can be reduced later with a warm container.

### 5.8 Engineering problems found and fixed

- **Version conflict.** fastmcp 4.x moved to MCP SDK 2, but langchain-mcp-adapters still needs SDK 1. Both are pinned in `requirements.txt` (fastmcp 3.4.11, mcp < 2, adapters 0.3.2).
- **stdout is the protocol.** Over stdio, anything a server prints to stdout corrupts the JSON-RPC stream and the client hangs. The retriever's progress messages now go to stderr.
- **Loading models inside a tool thread hung.** filings-kb now loads its index at startup, in the main thread. That also makes the first search fast (~30 s startup, then ~1 s per search).
- **A process per call.** By default the adapter starts a new server process for every tool call. Phase 4 must hold persistent sessions for a run.

### 5.9 Practice questions (MCP)

1. What is an MCP server, and why not just import the functions?
2. How does an agent end up with only some tools? Where is that defined, and how is it tested?
3. What happens when an agent asks for TSLA, or for FY2019?
4. Which tool changes the outside world, and what stops it being misused?
5. Why is a plain hash not enough for approval?
6. Show that an edit invalidates an approval. (`test_edit_after_approval_invalidates_it`)
7. Why is the local sandbox "a guard, not a boundary"? What is the boundary?
8. Why can't the audit hook alone stop `import socket`?
9. Why does the edgar server return facts but not margins?
10. How does the critic verify a number? (`get_fact` on the cited fact_id)

---

## 6. Running it in Docker (early part of L16)

**Code:** [compose.yaml](../compose.yaml), [Dockerfile](../Dockerfile), [docker/sandbox/Dockerfile](../docker/sandbox/Dockerfile).

**What `docker compose up` starts:**

| Service | Role | Network |
|---|---|---|
| `index` | Builds the vector index once, then exits | internal |
| `filings-kb`, `edgar`, `python-sandbox`, `research-portal` | The MCP servers, over HTTP on port 8000 | **internal only, no internet** |
| `app` | The Gradio UI on port 7861 | internal + outside (needs OpenRouter) |

**Design decisions and why:**

1. **One image, many services.** The app and all four servers share one image, and only the start command differs. That means one build, and identical code and library versions everywhere.
2. **Models baked into the image.** The embedding and reranker models are downloaded at build time, and containers run offline (`HF_HUB_OFFLINE=1`). Every teammate gets byte-identical models, and the internal-only servers never need the internet.
3. **CPU-only PyTorch.** The default Linux PyTorch download bundles GPU (CUDA) libraries, about 3 GB extra. We have no GPU, and the brief says none is needed.
4. **A one-shot `index` service.** Chroma stores its index in a database file. Two processes building it at the same time could corrupt it, so the app and filings-kb wait until `index` has finished (`service_completed_successfully`).
5. **An internal network for the tools.** The MCP servers can talk to the app but have no route to the internet. Even a compromised tool can't send data out. That's least privilege at the network level, matching least privilege at the tool level (section 5.2).
6. **The sandbox container is itself the boundary.** It is read-only, drops all capabilities, runs non-root, has memory and process limits, and has no internet. Code runs in a guarded child process inside it, so we don't need to give the server control of Docker (mounting the Docker socket would effectively hand it the whole machine).
7. **Data mounted read-only from the repo.** Passages and XBRL JSON come from git, so the image never goes stale. Only the index and the portal database live in Docker volumes.
8. **The app port is bound to 127.0.0.1.** Only this machine can open it, not others on the Wi-Fi.
9. **Secrets stay in `.env`,** read by the app container only. The MCP servers never receive the OpenRouter key.

**Two things found while testing:**
- **Docker Desktop's "Resource Saver"** pauses its VM after a few idle minutes, and the next command takes 10–30 s to wake it. Our sandbox originally allowed only 5 s, so tests failed or skipped at random. The startup allowance is now 30 s.
- **One timed-out container kept running for 29 minutes,** because the host-side kill failed while Docker was waking. Fixes:
  - The runner now **stops itself** at the time limit (an alarm signal inside the container).
  - The host removes the container with `docker rm -f` as a backstop.

  Two independent stops, again defence in depth.

**Likely questions:**
- *"Why not mount the Docker socket so the sandbox server can start a fresh container per call?"* Access to the socket is effectively root on the host. A bug or injection in the sandbox server would then control the whole machine. A single locked-down container with a guarded child process is safer.
- *"What still needs adding for the full L16 bar?"* Prometheus, Grafana and an alert (Phase 8), the agent graph (Phases 4–6), CI with an evaluation gate, and a test install on a clean machine.

---

## 7. The C1 agent: one agent, all tools (L8, L10)

**Code:** [analystdesk/agent/graph.py](../analystdesk/agent/graph.py), [checks.py](../analystdesk/agent/checks.py), [figures.py](../analystdesk/agent/figures.py), and the command-line runner [__main__.py](../analystdesk/agent/__main__.py). Diagram: `python -m analystdesk.agent graph` prints it (Mermaid).

```
input_guard → plan → [analyst: approve/edit plan] → research ⇄ tools (ReAct)
   tools ─(NOT_IN_COVERAGE)→ replan → plan → [analyst sees revised plan]
→ write → check ─(issues, max 2)→ write
→ [analyst: approve / edit / reject exact note] ─edit→ check
→ publish (signed approval; portal verifies) → END
```

**How each minimum-bar item is met:**

| L8/L10 requirement | Where |
|---|---|
| Typed state | `AgentState` (TypedDict), `Plan` and `Draft` (pydantic) |
| Conditional edges | after_guard, after_research, after_tools, after_check, after_review |
| A self-correction loop | `check` sends code-found issues back to `write`, at most 2 times |
| Persistent checkpointer, stop and resume | `AsyncSqliteSaver` at `data/runs/checkpoints.sqlite`. Each CLI command exits at a gate, and the next resumes from a **new process** |
| A plan object shown to the user | `review_plan` interrupt. The analyst approves or edits it (`--edit-plan plan.json`) |
| Replanning when a tool contradicts the plan | A NOT_IN_COVERAGE tool result triggers `replan`, and the analyst sees the revised plan |
| ReAct inside the specialist | `research`: the model calls tools, observes, and repeats, within a budget of 24 tool calls and 120k tokens |
| Human approval of the exact payload (L14) | `review_note` signs the exact note. An edit goes back through `check`, then needs a fresh approval |

**Live run evidence (gpt-4.1-mini via OpenRouter):**
- `demo1` / `demo2` (first design): the plan gate worked; the run was stopped and resumed from a new process; 14–18 real tool calls (XBRL facts, 6 sandbox calculations, filing searches); the checker **rejected the draft 3 times**. The numbers were right, but the writer kept putting citations in the wrong place, so 0 of 37 verified.
- `demo3` (placeholder design): **14 of 14 numbers verified on the first draft**, 14 tool calls, about 28k tokens. It is waiting at the note gate for your approval: `python -m analystdesk.agent resume demo3 --approve --approver Jayshree`.

**The key design lesson (tell this in the viva).**
- Asking the LLM to *type* each number and place its citation correctly failed even with explicit wrong/right examples.
- The fix applies rule 1 literally: **the model never types a key figure.** Code builds a table of figures from XBRL, each with a key such as `{MSFT_2024_margin}`. The writer chooses *which* figure to mention by writing its placeholder, and code inserts the exact value plus its `[fact: …]` or `[calc: …]` source.
- Any other number must be quoted from a filing, and code checks that it really occurs in the passage cited on the same line.
- Result: numbers can't be mistyped or invented, and the verified share went from 0% to 100%.

**What the checker verifies (all in code):**
- Fact values match XBRL.
- Margins equal numerator ÷ denominator.
- Quoted numbers appear in the cited passage.
- Cited passages exist.
- No advice wording.

That verified share is the dashboard metric for the "alert below 98%" (Phase 8).

**Likely questions:**
- *"Where is the model deciding and where is code?"* The model plans, chooses tools and writes the prose. Code checks scope, enforces coverage on the plan, computes and inserts every key figure, verifies every number, and signs approvals. People approve the plan and the note.
- *"What happens if the check still fails after 2 revisions?"* The note goes to the analyst **with the issues listed**. Nothing is hidden, and the analyst can edit or reject.
- *"How does resume work?"* Every step's state is saved under the run's `thread_id` in SQLite. `Command(resume=decision)` continues from the exact interrupt, even in a different process.

### 7.1 Demoing it in the app (Research tab, C1/C2)

**Code:** [agent_ui.py](../agent_ui.py), and [runtime.py](../analystdesk/agent/runtime.py), which the CLI and the app share.

**In the app:**
1. Type a request and press **Start**.
2. The **plan** appears. **Approve** it, or edit the JSON and approve the edited plan.
3. The **activity log** streams every step live, including each MCP tool call with its arguments (`get_financials(ticker='V', fiscal_year=2024)`) and its result (✔/✖).
4. The **note** appears, with numbered sources and the code check (e.g. "10/11 numbers verified" with the flagged number listed).
5. **Approve** (it's signed and published), **edit** (it's re-checked and needs a fresh approval), or **reject**.
6. **Published notes** lists everything in the research portal.
7. **Load run** resumes any run by its id, even after restarting the app.

**Tool transport in the app.** The app uses MCP's in-memory transport: the same protocol and schemas as stdio or HTTP, but no subprocesses, and filings-kb reuses the app's already-loaded index.

In the **Research** tab, choose **C0 · No-Agent (Baseline)** for the fixed baseline. It shows "How this answer was built": the per-company searches, the EDGAR facts and the model. Choose C1 or C2 for agent runs with plan and note approval gates.

**Live run through the app** (Visa vs Mastercard, run `51e25127`): 18 tool calls, all successful; 95 s; 48k tokens. The checker sent the draft back twice: first two margins the writer had typed itself, then one stray "55%". The final draft reached the gate at 10/11 verified, with the issue shown to the analyst. **That's the design: code flags it, and a person decides.**

---

## 8. Memory (L9): your role

**Code:** [analystdesk/memory.py](../analystdesk/memory.py). Policy: [memory_policy.md](memory_policy.md). Comparison script: [scripts/memory_compare.py](../scripts/memory_compare.py). Tests: [tests/test_memory.py](../tests/test_memory.py).

### 8.1 Two kinds of memory

| | Short-term | Long-term |
|---|---|---|
| What | The research conversation inside one run | Preferences, coverage list, past-note memory |
| Where | The run's state (checkpointer) | LangGraph **store** (SQLite, `data/memory/`) |
| How managed | **Trimmed** to a size budget (`trim_context`): keeps the system prompt, the request and the most recent tool rounds. The cut always starts on an AI message, so no tool result loses the call that asked for it | Written only after the analyst acts: adding a preference, or approving a note that then gets published |
| Lifetime | Ends with the run | Until the analyst deletes it |

**Likely question:** *"Checkpointer vs store: what's the difference?"* The checkpointer holds one run's working state, which is what makes stop-and-resume work. The store holds what the desk remembers *across* runs.

### 8.2 What's remembered, and why it's trustworthy

- **Past-note figures are parsed from the published note's own `[fact]` and `[calc]` tags.** Those numbers were already verified by code against XBRL, so memory never holds an unverified number.
- **Only approved and published notes are remembered.** Drafts and rejected notes never are.
- **"What changed since our last note" is computed by code** (`memory.what_changed`): previous value → current value, with margin moves in percentage points. The model only comments on the result.

### 8.3 Memory on vs off (the required comparison)

Request: *"What changed in Microsoft's and Alphabet's operating margins since our last note? Cover fiscal 2022–2024."* It was run twice to the note gate (nothing published), with one stored preference ("Always include a peer comparison table") and note #1 in memory. The results were scored by code:

| | Memory ON | Memory OFF |
|---|---|---|
| Refers to the previous note (#1) | ✅ | ❌ |
| Includes the code-computed comparison | ✅ | ❌ |
| Follows the preference (peer table) | ✅ | ❌ |
| Numbers verified | 14/14 | 6/6 |
| Tokens / time | 9.6k / 17 s | 9.4k / 14 s |

Result file: `data/evaluation/results/memory_compare_20261025-112601.json`. You can rerun it with `python scripts/memory_compare.py`.

**Be honest about this in the viva:**
- The comparison said **"unchanged since the last note"**. That's correct, because both notes use the same FY2022–2024 filings. With a new 10-K the lines would show real moves; the unit test shows "+2.87 pp".
- Memory costs almost nothing: +2% tokens, about the same time.
- It's one request, so it's a demonstration, not a statistical result.
- The scorer was first written to look for one exact heading, and the writer used its own heading. The scorer was fixed to look for the code-computed lines instead, and the runs were re-scored, not re-run.

### 8.4 Correction and deletion (policy in practice)

- **🧠 Memory panel** (Research tab, C1/C2): view preferences, the coverage list and past-note memory, and delete any item.
- **Use memory** switch: a run with it off neither reads nor writes memory.
- `scripts/backfill_memory.py` rebuilds past-note memory from the portal. It was used once, for note #1, which was published before memory existed.

**Likely questions:**
- *"Can the agent change its own memory?"* No. No tool writes memory. Only two code paths do: the analyst's "Add preference", and publish-after-approval.
- *"What if a stored preference is wrong?"* Delete it in the panel. Each run's activity log shows which preferences were used.
- *"How do you stop memory from leaking private data?"* Memory holds only the analyst's own preferences and published, verified figures. The private watchlist (L15) gets its own namespace that never reaches a prompt or search tool; that's in the security phase.

---

## 9. C2: the team of agents, hooks and the compliance critic (L11, L14)

**Code:** [analystdesk/agent/team.py](../analystdesk/agent/team.py), [hooks.py](../analystdesk/agent/hooks.py). The nodes shared with C1 are in [graph.py](../analystdesk/agent/graph.py) (`common_nodes`). In the app, pick **C2 · team** next to the request box.

```
input_guard → plan → [analyst: plan gate] → fan-out in parallel (LangGraph Send):
   researcher[each company]  MD&A drivers        tools: search_filings, get_passage
   quant                     facts + sandbox     tools: get_financials, get_fact, run_python
   risk_diff[each company]   Item 1A, Y vs Y-1   tools: search_filings, get_passage, get_past_notes
 → typed HandoffMessage from each → gather ─(NOT_IN_COVERAGE)→ replan
 → writer → compliance critic (code checks + judge) ─(issues, max 2)→ writer
 → [analyst: note gate] → publish (only the publisher holds publish_note)
```

### 9.1 What each L11 requirement maps to

| Requirement | Where |
|---|---|
| A supervisor + 3 or more specialists | Research lead (plan, fan-out, gather) + researcher, quant, risk_diff, critic, writer, publisher |
| Each with its own tools | `servers.AGENT_TOOLS`; each specialist is bound to only its own tools, and the hooks re-check every call |
| A typed hand-off message | `HandoffMessage` (pydantic): agent, company, findings, passage_ids, fact_ids, confidence, tool_calls, errors, round |
| Parallel researchers (the brief's signature challenge B) | `Send` fan-out: one researcher and one risk-diff per company, plus the quant, all running concurrently |
| Critic loop of at most 2 rounds | `check` → `count_revision` → `write`, with `MAX_REVISIONS = 2` |
| Single-agent baseline with the same tools and budget | C1 (`graph.py`): same model, same MCP tools, same checker; only the orchestration differs |

**The hand-off's ids are extracted by code** from the tool results, not claimed by the model. A specialist can't say it read a passage it never fetched. Confidence is also set by code: low if no evidence was gathered, medium if a tool errored.

### 9.2 Hooks (L14)

Every tool call in C2, and in C1 via `ToolNode(awrap_tool_call=...)`, passes through:
- **Pre-tool:**
  - *permission*: is the tool in this agent's allow-list? If not, `PERMISSION_DENIED`;
  - *budget*: each agent instance has its own tool-call budget (researcher 6, quant 14, risk_diff 6). When it's used up, `BUDGET_EXCEEDED`;
  - *EDGAR rate limit*: at most 10 calls per second.
- **Post-tool:** a trace event (agent, tool, arguments, ok or error code, duration), streamed live to the app's activity log.

Denials go back to the agent as normal tool results, so it adapts instead of crashing. In the live C2 run you can see `risk_diff[JPM]` hitting `BUDGET_EXCEEDED` and still handing off what it had.

**Likely question:** *"Why hooks if each agent is only given its own tools anyway?"* Defence in depth. Binding decides what the model *sees*; the hook decides what *runs*. A bug, a mis-wired agent, or a prompt injection that names a tool the agent shouldn't have is stopped at the hook.

### 9.3 The compliance critic

1. **Code checks every number** (`checks.py`):
   - facts match XBRL;
   - `calc`, `growth` and `diff` values are recomputed;
   - quoted numbers must appear in the cited passage **with the same unit** (a bare "5" no longer counts as a quote of "5%");
   - no advice wording.
2. **A judge from a different model family** (`meta-llama/llama-3.3-70b-instruct`, while the writer is `gpt-4.1-mini`) checks each cited claim against its passage text. Unsupported claims become issues for the writer.
3. **Issues go back to the writer** for up to 2 revisions. Whatever remains is shown to the analyst at the gate; nothing is hidden.

**Why a different family for the judge?** A model judging its own family's output tends to share its blind spots. The brief asks for this, and also for checking the judge against 20+ human labels with Cohen's kappa (Phase 8). Until then, the judge's verdicts are advisory: they're shown and sent back, but never silently trusted.

### 9.4 Fixes found by tracing real runs (good viva stories)

- **An invented figure caught.** In the first C2 run the writer wrote "$15.3 billion", which appeared in no cited passage and in nothing the quant returned. The critic flagged it, and it reached the gate as the only unverified number (34/35).
- **A loose quote check, tightened.** "margin declined 5%" had passed because the digit 5 appeared somewhere in the passage. Quotes now must match number *and* unit.
- **Changes now come from code too.** Writers kept inventing growth rates and margin moves. New code-computed placeholders were added:
  - `{T_Y_revenue_growth}`, rendered with `[growth: A / B]`;
  - `{T_Y_margin_change}`, rendered with `[diff: …]` in percentage points.

  The checker recomputes both, and flags any "pp" number without a source.
- **Result in the next C2 run** (JPM vs GS): 18/18 numbers verified; the judge supported 3 of 4 claims, and the 4th went to the analyst.

### 9.5 Memory became automatic (from your design question)

- **The memory checkbox is gone.** Memory is per analyst (by name) and on by default.
- **Evaluation runs force memory off** (`AGENT_EVAL=1`), so experiments stay reproducible and held-out cases never benefit from memory.
- **Restated figures are detected by code.** If the same fiscal year now has a different value, the note says "restated since the last note" instead of calling it a change.
- **A missing previous note is stated plainly.** If the analyst asks "what changed since our last note" and there isn't one, the note says so.
- **"↻ Re-run this request without memory"** covers independent views, second opinions and debugging, in one click.

### 9.6 Showing it: the team board (app)

The Research tab in **C2 · Team** mode has a **👥 Team board** with one row per agent: research lead, each researcher and risk-diff agent, the quant, writer, critic, you (the note gate) and the publisher. Each row shows status (queued → working → handed off), tool calls, last action and details (passages, facts, confidence, errors). It updates live as hook events stream in; in a test run it refreshed 40 times. Mid-run you can see some specialists already handed off while others are still working, which is the parallel fan-out made visible. Loaded runs rebuild the board from their history, because each hand-off now saves that agent's tool calls.

**Demo tip:** start a C2 run, approve the plan, and narrate the board: "five specialists start at once; the quant only has EDGAR and the sandbox; the risk-diff agent hit its budget, and the hook stopped it; the critic verified every number and the judge flagged one claim for me to decide on."

---

## 10. Evaluation, Reflexion and observability (L12, L13, L16)

### 10.1 The golden set and how it's scored

- **Development cases:** [data/evaluation/dev_cases.jsonl](../data/evaluation/dev_cases.jsonl), 20 cases:
  - 8 numeric, 5 comparison, 4 risk-change, and 3 refusals (an uncovered company, an uncovered year, an investment-advice request).
  - Expected figures were **computed from XBRL by code and frozen in the file before any agent ran** ([scripts/make_dev_cases.py](../scripts/make_dev_cases.py)).
- **Held-out cases:** [data/evaluation/heldout/](../data/evaluation/heldout/README.md) is empty on purpose. The brief says the person who tunes the agent must not write them, so **a teammate (Role 5)** writes 40+. No agent tool can read that folder.
- **Scoring is code first** ([analystdesk/evaluation.py](../analystdesk/evaluation.py)):
  - **numeric / comparison:** every expected figure appears in the output with the same unit, within rounding. So C0's free text and the agents' code-rendered figures are judged alike.
  - **risk_change:** the note cites the company's Item 1A passages for **both** years.
  - **refusal:** it declines, with no figures and no advice.
  - **Recorded for every run:** policy violations (advice wording), verified share, tools used, tokens, cost and latency.
- **Runner** ([scripts/run_eval.py](../scripts/run_eval.py)):
  - C0, C1 and C2 on the same cases, with the same model and tools; the plan gate is auto-approved and runs stop at the note gate (nothing is published);
  - **memory is forced off**, so runs are reproducible;
  - failed and timed-out runs are counted, not hidden.

### 10.2 Reflexion (L12)

- [scripts/reflect.py](../scripts/reflect.py) reads a **development** evaluation result (it refuses held-out results). For each agent run it collects what went wrong: failed scoring, and critic issues across revisions. A reflection prompt then turns these into at most 2 lessons per run: *"When <situation>: <what to do>"*, with tags.
- Lessons are **pending** until a person approves them in the app (Research tab, C1/C2 → 📘 Playbook). Rejections are kept with their reason, and the brief asks for one rejected lesson as evidence.
- Approved lessons are **retrieved only when relevant** (tag and word overlap, top 3) and shown to the planner, researchers and specialists, and writer. Each run's log says how many lessons it used.
- **Freeze** the playbook before the held-out run; a frozen playbook refuses new approvals. `run_eval.py --no-lessons` gives the "before" runs for E3.
- Code: [analystdesk/lessons.py](../analystdesk/lessons.py).

### 10.3 Judge calibration (L13)

[scripts/calibrate_judge.py](../scripts/calibrate_judge.py):
1. `sample` writes about 30 real claim + passage pairs to a CSV, **without** the judge's verdict.
2. A person labels each one yes/no.
3. `score` runs the judge on the same rows and reports agreement and **Cohen's kappa**.

**Why kappa, not plain agreement?** If almost every claim is supported, a judge that always says "yes" scores 90%+ agreement while being useless. Kappa subtracts the agreement expected by chance. In our sanity test, 9 of 10 agreeing still gave kappa −0.11.

### 10.4 Observability (following your L14 lecture notebook)

- **Traces:** OpenTelemetry with OpenLLMetry's `LangchainInstrumentor`, exactly as in the lecture, plus a business span `analystdesk.run` (run id, mode, outcome, verified share, tokens), exported over OTLP to **Jaeger**.
  - A verified test trace had 48 spans: every graph node, every model call and every tool execution.
  - **Prompt and response text is not captured** (`TRACELOOP_TRACE_CONTENT=false`). That's the lecture's warning that traces can leak what hooks redact.
- **Metrics:** `prometheus_client` on `/metrics` (port 9464): runs by outcome, latency histogram, tokens and cost, verified/unverified numbers, critic rejections, tool calls by agent, hook denials, and EDGAR cache vs network.
- **Grafana dashboard** ([docker/grafana/dashboards/analyst_desk.json](../docker/grafana/dashboards/analyst_desk.json)) shows the verified share against the 98% line, cost per note, latency (median and p95), rejections and tokens, tool calls by agent, and denials and EDGAR lookups.
- **Alert:** Prometheus rule `VerifiedShareBelow98` (the brief's exact alert) ([docker/prometheus/alerts.yml](../docker/prometheus/alerts.yml)).
- `docker compose up` now also starts **Jaeger (:16686), Prometheus (:9090) and Grafana (:3000)**.
- **Known gap:** the MCP servers' own spans form separate traces, because trace context isn't propagated over the in-memory MCP connection. The lecture's `traceparent` header approach would fix this over HTTP.
