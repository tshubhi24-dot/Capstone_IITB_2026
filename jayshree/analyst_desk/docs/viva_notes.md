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
