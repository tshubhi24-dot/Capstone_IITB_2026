# Analyst Desk — Windows Setup & Handover

IIT Bombay Agentic AI Capstone · Project 5  
Picking up from Mac → Windows. Read this top to bottom before starting a session.

---

## Where we are

**Phases complete:** 0 (scope), 1 (EDGAR XBRL), 2 (ingestion + hybrid retrieval + C0 pipeline + Gradio UI)  
**Next phase:** Phase 3 — MCP Servers (FastMCP)

All code lives in `jayshree/analyst_desk/` in the shared repo.

---

## 1. Clone the repo

```bash
git clone https://github.com/jayshree-rajan/Capstone_IITB_2026.git
cd Capstone_IITB_2026/jayshree/analyst_desk
```

> Use the personal fork — push there first, then PR to tshubhi24-dot when ready.

---

## 2. Python environment

Requires Python 3.12.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

If `requirements.txt` is missing, install manually:
```bash
pip install gradio plotly beautifulsoup4 rank-bm25 chromadb \
            sentence-transformers openai python-dotenv pdfminer.six fastmcp
```

---

## 3. Create your .env file

Create `jayshree/analyst_desk/.env` (never commit this):

```
OPENROUTER_API_KEY=<paste key — ask Jayshree or check OpenRouter dashboard>
C0_MODEL=openai/gpt-4.1-mini
```

OpenRouter account: sign in at openrouter.ai — the key is in the dashboard.  
$10 credit loaded. Model prescribed by capstone PDF: `openai/gpt-4.1-mini` for specialists.

---

## 4. GitHub auth

```bash
gh auth login
# Choose: GitHub.com → HTTPS → Login with a web browser
```

---

## 5. Re-run ingestion (first time on new machine)

The `data/` folder is gitignored (169MB). You need to rebuild it:

```bash
cd jayshree/analyst_desk
python -m analystdesk --mode ingest
```

This downloads 10-K filings from SEC EDGAR (free, no key needed) and builds:
- `data/passages/` — 7,701 JSONL passage files (14 companies × 3 years)
- `data/edgar_cache/` — XBRL facts JSON cache
- `data/index/` — Chroma vector store (BM25 + embeddings)

Takes ~10–15 min first run, cached after that.

---

## 6. Run the app

```bash
python app.py
# Opens at http://127.0.0.1:7861
```

---

## Architecture summary (for VIVA)

```
User question
    │
    ▼
Hybrid Retriever  ←── BM25 (keyword) + Chroma vectors (semantic)
    │                   └── RRF merge → cross-encoder reranker
    ▼
C0 Fixed Pipeline
    ├── Retrieved passages  (10-K Item 1A + Item 7 text)
    ├── EDGAR XBRL numbers  (annual + quarterly, fact_id per number)
    └── Fixed prompt → gpt-4.1-mini (single LLM call, no agent loop)
    ▼
Cited answer  +  Plotly chart (Python-generated, NOT LLM-generated)
```

**Key design rule (capstone Rule 1):** The model selects and explains; code computes.  
Numbers, margins, and charts are always produced by Python from EDGAR data — never by the LLM.

---

## Company scope

| Sector | Companies |
|--------|-----------|
| Technology (8) | MSFT, GOOGL, AAPL, AMZN, META, NVDA, AMD, ORCL |
| Finance (7) | JPM, GS, BAC, V, MS, MA, WFC |

**C0 baseline pair:** MSFT + GOOGL (as per PDF example)  
**Known gap:** Morgan Stanley (MS) = 0 passages — HTML uses `<td>` cells for item headings, not inline text. Fix planned before Phase 3.

---

## Key files

| File | What it does |
|------|-------------|
| `analystdesk/scope.py` | 15 companies, sectors, ResearchRequest schema |
| `analystdesk/edgar.py` | EDGAR XBRL fetch — annual + quarterly facts, local cache |
| `analystdesk/ingest.py` | Downloads 10-K HTML, splits by Item, chunks, saves JSONL |
| `analystdesk/retrieve.py` | HybridRetriever — BM25 + Chroma + RRF + cross-encoder |
| `analystdesk/c0_pipeline.py` | C0 fixed RAG: retrieve → numbers → prompt → LLM |
| `app.py` | Gradio UI — Dashboard, Chat (with chart), Data Explorer |
| `docs/plan.md` | Full phase-by-phase build plan with VIVA Q&A |

---

## What to build next — Phase 3: MCP Servers

**Goal:** Wrap all data access behind FastMCP servers so agents never touch storage directly.

Four servers to write in `analystdesk/servers/`:

| Server | Tools |
|--------|-------|
| `filings_kb.py` | `search(query, k)`, `get_passage(passage_id)` |
| `edgar.py` | `get_xbrl_fact(cik, concept, year)`, `get_quarterly(cik, year)` |
| `python_sandbox.py` | `run_calc(code)` — no network, pandas only |
| `research_portal.py` | `get_past_notes(company)`, `publish_note(note)` [write-gated] |

Start the session by asking Claude:  
*"Let's build Phase 3 MCP servers for the Analyst Desk capstone. Read HANDOVER.md and docs/plan.md first."*

---

## Reminders

- Never commit `.env`
- Always push to personal fork first (`git push personal main`), then PR to shared repo when ready
- Run tests before pushing: `python -m pytest tests/`
- Shared repo: https://github.com/tshubhi24-dot/Capstone_IITB_2026
