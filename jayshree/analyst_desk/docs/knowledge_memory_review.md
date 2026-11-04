# Knowledge and memory: best practices vs Analyst Desk

A review of role 2 (knowledge and memory) against widely used practices for retrieval-augmented generation and agent memory. For each practice it records what Analyst Desk does now, where in the code, and whether it is worth adding.

The last column is blank on purpose: tick it when the technique is covered in the course lecture notes (L4–L6 retrieval, L9 memory). That shows which gaps matter for the brief and the viva.

**Status:** ✅ done · 🟡 partly · ❌ not done · ➖ deliberately not done

---

## 1. Knowledge: ingestion and retrieval

| # | Practice | What it means | Analyst Desk | Status | Worth adding? | In notes? |
|---|---|---|---|---|---|---|
| K1 | Structure-aware chunking | Split by document structure (sections, headings), not fixed token windows | Split by 10-K Item, then by heading; six parser fixes for real filings ([ingest.py](../analystdesk/ingest.py)) | ✅ | — | ☐ |
| K2 | Keep tables as tables | Preserve row and column labels so numbers stay meaningful | Each data table is its own passage of `label \| value` rows, titled, split by row with the header repeated | ✅ | Measured on answers ([e4_tables.md](e4_tables.md)): no improvement over plain passages on 18 table questions; kept for citable, captioned table chunks | ☐ |
| K3 | Rich metadata + filtering | Store company, year, section, type, source id on each chunk; filter before ranking | `company`, `fiscal_year`, `item`, `kind`, `accession`; filters applied before BM25 and vector ranking | ✅ | — | ☐ |
| K4 | Hybrid sparse + dense search | Combine keyword (BM25) and embedding search | BM25 + MiniLM/Chroma, fused with Reciprocal Rank Fusion | ✅ | — | ☐ |
| K5 | Reranking | A cross-encoder re-scores a shortlist | `ms-marco-MiniLM-L-6-v2` over the top 50 | ✅ | Its cost: about 0.7–1 s per query on CPU. A smaller pool (top 20) could be measured | ☐ |
| K6 | Query transformation | Rewrite or split the query before searching | Decomposition per (company, year) with filters, plus a rewrite that strips names and years: the largest gain, 0.472 → 0.903 | ✅ | — | ☐ |
| K7 | HyDE / multi-query | An LLM writes a hypothetical answer, or several paraphrases, and each is searched | Not used: decomposition is deterministic code (rule 1) | ➖ | Optional comparison; costs a model call per query | ☐ |
| K8 | Contextual chunk headers ("contextual retrieval") | Prepend short context (document, section) to each chunk before embedding and BM25, so a chunk is findable without its neighbours | Tables get the line above them as a title; text chunks get nothing | 🟡 | **Yes, a cheap experiment.** Prefix each chunk with its Item and section heading (not company or year: metadata filters cover those, and names in text hurt, see viva notes 3.8). Measure Recall@5 before and after | ☐ |
| K9 | Small-to-big (parent-document) retrieval | Search small chunks, then give the model the surrounding section | Not done; `get_passage` returns a single passage | ❌ | Maybe: for MD&A answers that span two chunks. Measure on risk-change cases first | ☐ |
| K10 | Embedding model choice | Pick the embedder by measured recall | `all-MiniLM-L6-v2` (small, CPU, no cost) | 🟡 | Try `bge-small-en-v1.5` with the same Recall@5 script; it's a one-line change plus rebuilding the index | ☐ |
| K11 | Retrieval evaluation | Labelled queries; Recall@k, ideally also MRR or nDCG; held-out labels | 36 labelled queries, Recall@5, labels as evidence strings that work across chunkings | 🟡 | Add **MRR** (rank of the first hit) to `eval_retrieval.py`; a held-out set written by role 5 | ☐ |
| K12 | Index versioning | Rebuild when the source changes; never serve stale embeddings | The Chroma collection is named after a fingerprint of the passages | ✅ | — | ☐ |
| K13 | Provenance and citations | Every claim points to a source the reader can check | Passage ids and filing accession; XBRL fact_ids; the checker verifies quotes against the cited passage | ✅ | Table quotes are unit-aware (a "(In millions)" caption gives cells their unit). Next: **cell-level citation** (the passage id plus the row label) | ☐ |
| K14 | Retrieved text is data | Never follow instructions found in documents | Rule 2: passages are given to the model as evidence only | 🟡 | Owned by the security work (red-team attacks hidden in filing text) | ☐ |
| K15 | Freshness | New filings flow in on a schedule | Fixed corpus (FY2022–2024), committed so results are reproducible | ➖ | Out of scope for the capstone; mention it as future work | ☐ |

---

## 2. Memory

A common way to classify agent memory is CoALA's four kinds (Sumers et al., 2023). Analyst Desk has all four, which is a good viva answer to "what kinds of memory does your agent have?":

| Kind | What it is | In Analyst Desk |
|---|---|---|
| **Working** | The current task's context | The run state, with the research conversation trimmed to a size budget (`trim_context`) |
| **Episodic** | Past experiences | Past-note memory: what was published, when, by whom, with which verified figures |
| **Semantic** | Facts about the world and the user | Analyst preferences; the coverage list |
| **Procedural** | How to do the task | The Reflexion playbook: approved "when … do …" lessons |

| # | Practice | What it means | Analyst Desk | Status | Worth adding? | In notes? |
|---|---|---|---|---|---|---|
| M1 | Separate short-term and long-term | Thread state vs a cross-session store | Checkpointer (per run) vs LangGraph store (across runs) | ✅ | — | ☐ |
| M2 | Explicit write policy | Decide *what* gets written and *who* triggers it | Written only by the analyst (preferences) or after an approved publication; no model-written memory | ✅ | Trade-off to mention: LLM-extracted memories (as in LangMem or MemGPT) capture more, but can store mistakes and injected text. We chose control | ☐ |
| M3 | Verified content only | Don't store unverified claims | Past-note figures are parsed from checked `[fact]` / `[calc]` tags | ✅ | — | ☐ |
| M4 | Provenance on every memory | Each entry says where it came from | Note id, title, approver, date; preferences have a date; lessons keep source cases and review history | ✅ | — | ☐ |
| M5 | Scoping and namespacing | Memory is per user or tenant where it should be | Preferences and coverage are per analyst. **Past-note memory is per ticker and shared by the whole desk** | 🟡 | **Make the decision explicit in the policy.** Desk-wide is defensible, because published notes are the desk's record. Otherwise key it by analyst | ☐ |
| M6 | Relevance-filtered recall | Retrieve only memories relevant to the request | Lessons: top 3 by tag and word overlap. Past notes: only for the plan's companies. Preferences: all of them | 🟡 | Fine at a few preferences. With many, select by relevance or let the analyst pin "always" ones | ☐ |
| M7 | Code-computed use of memory | Derived facts from memory computed deterministically | "What changed since our last note" and restatement detection are code (`memory.what_changed`) | ✅ | — | ☐ |
| M8 | Conflict handling and consolidation | Merge duplicates; detect contradictions | Lessons: duplicates merged, conflicting decisions return to pending. Preferences: none | 🟡 | **Yes:** flag a new preference that duplicates or contradicts an existing one when it is added | ☐ |
| M9 | Forgetting (TTL, staleness) | Old memories expire or are marked stale | Kept until deleted | ❌ | Mark a past note stale once a newer 10-K exists for that company (the comparison then says so) | ☐ |
| M10 | User control | View, correct, delete; opt out | 🧠 panel: view, add, delete (with confirmation); re-run without memory; API `memory_on` | ✅ | Export (a JSON download) would complete it | ☐ |
| M11 | Privacy | Sensitive memory never reaches prompts or tools | No personal data stored | 🟡 | The brief's **private watchlist** (L15) needs its own namespace, never sent to a model or tool, with a test. Shared with the security work | ☐ |
| M12 | Context-window management | Trim or summarise long histories | Trimming that keeps the system prompt, the request and recent tool rounds, with a note that earlier messages were cut | 🟡 | Summarising trimmed messages (LangGraph `summarize` pattern) instead of dropping them; measure whether it changes answers | ☐ |
| M13 | Memory off for evaluation | Experiments must not leak memory | `AGENT_EVAL=1` forces memory off | ✅ | — | ☐ |
| M14 | Evaluate memory itself | Measure that memory is used correctly and only when it should be | 11-case on/off suite, scored in code ([memory_eval.md](memory_eval.md)) | ✅ | Add cases as features are added (stale notes, conflicting preferences) | ☐ |

---

## 3. Suggested next steps for role 2

Ranked by value for the project and the viva, against effort:

| Step | Effort | Why |
|---|---|---|
| 1. Run and report the memory evaluation (M14) and E4 on answers (K2) | **Done:** memory ON 11/11, OFF 11/11 clean, one bug found and fixed; E4 showed no gain from table-aware passages but exposed the unit-aware quote gap, now fixed | Turns "memory helps" and "tables help" into measured claims |
| 2. Contextual chunk headers (K8), measured with Recall@5 | Small | A well-known technique with a clear before and after |
| 3. Preference conflict check (M8) + an explicit sharing decision (M5) | Small | Closes visible policy gaps an examiner may probe |
| 4. MRR in the retrieval report (K11) | Small | Shows *where* the first correct passage lands, not only whether it's in the top 5 |
| 5. Stale past notes (M9) | Medium | Makes "what changed" honest when filings move on |
| 6. Watchlist namespace (M11), with the security owner | Medium | Required by the brief's L15 scenario |
| 7. Embedding model comparison (K10), small-to-big (K9), summarising trim (M12) | Medium | Nice to have; each needs its own measurement |

---

## References

- Anthropic (2024). *Introducing Contextual Retrieval.* https://www.anthropic.com/news/contextual-retrieval: contextual chunk headers, plus hybrid search and reranking.
- Sumers, Yao, Narasimhan, Griffiths (2023). *Cognitive Architectures for Language Agents (CoALA).* arXiv:2309.02427: working, episodic, semantic and procedural memory.
- Packer et al. (2023). *MemGPT: Towards LLMs as Operating Systems.* arXiv:2310.08560: model-managed memory tiers, the contrast to our human-controlled writes.
- Shinn et al. (2023). *Reflexion: Language Agents with Verbal Reinforcement Learning.* arXiv:2303.11366: the playbook's basis.
- Gao et al. (2022). *Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE).* arXiv:2212.10496.
- Cormack, Clarke, Büttcher (2009). *Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods.* SIGIR.
- LangGraph documentation, *Memory* (short-term vs long-term, stores, namespaces): https://langchain-ai.github.io/langgraph/concepts/memory/
