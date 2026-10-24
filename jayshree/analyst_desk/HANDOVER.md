# Analyst Desk — Windows Setup

IIT Bombay Agentic AI Capstone · Project 5

---

## 1. Clone

```bash
git clone https://github.com/tshubhi24-dot/Capstone_IITB_2026.git
cd Capstone_IITB_2026/jayshree/analyst_desk
```

## 2. Python environment

Tested with Python 3.14 on Windows (3.12+ should work).

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Create .env

Copy `.env.example` to `.env` in this folder and fill in your key — never commit `.env`:

```
OPENROUTER_API_KEY=<get from openrouter.ai dashboard>
C0_MODEL=openai/gpt-4.1-mini
```

## 4. Data — already in the repo

`data/passages/` (table-aware 10-K chunks), `data/passages_plain/` (plain-text
chunks for the E4 ablation) and the EDGAR XBRL/submissions JSON in
`data/edgar_cache/` are committed, so a fresh clone needs **no** SEC download.

Built locally on first use (gitignored):
- the Chroma vector index in `data/index/` — first retrieval call embeds all
  passages (~10 min on CPU, once);
- raw 10-K HTML in `data/edgar_cache/filings/` — only needed to re-chunk:

```bash
python -c "from analystdesk.ingest import ingest_all; ingest_all()"
```

## 5. Check it works

```bash
python -m unittest discover -s tests                      # all tests
python -m analystdesk --companies MSFT GOOGL JPM --years 2022 2023 2024 --mode baseline
python scripts/eval_retrieval.py                          # Recall@5 report
```

## 6. Run the app

```bash
python app.py
# Opens at http://127.0.0.1:7861
```

## 7. Next phase

Phase 3: MCP servers (filings-kb, edgar, python-sandbox, research-portal).
See `docs/plan.md`; reasoning for every decision so far is in `docs/viva_notes.md`.

---

Shared repo: https://github.com/tshubhi24-dot/Capstone_IITB_2026  
Personal fork: https://github.com/jayshree-rajan/Capstone_IITB_2026
