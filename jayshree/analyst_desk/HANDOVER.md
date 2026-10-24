# Analyst Desk — Windows Setup

IIT Bombay Agentic AI Capstone · Project 5

---

## 1. Clone

```bash
git clone https://github.com/jayshree-rajan/Capstone_IITB_2026.git
cd Capstone_IITB_2026/jayshree/analyst_desk
```

## 2. Python environment (Python 3.12)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install gradio plotly beautifulsoup4 rank-bm25 chromadb sentence-transformers openai python-dotenv pdfminer.six fastmcp
```

## 3. Create .env

Create `jayshree/analyst_desk/.env` — never commit this file:

```
OPENROUTER_API_KEY=<get from openrouter.ai dashboard>
C0_MODEL=openai/gpt-4.1-mini
```

## 4. GitHub auth

```bash
gh auth login
# GitHub.com → HTTPS → Login with a web browser
```

## 5. Re-run ingestion (builds data/ folder, gitignored)

```bash
python -m analystdesk --mode ingest
```

Downloads 10-K filings from SEC EDGAR and builds passages + vector index (~10–15 min, free).

## 6. Run the app

```bash
python app.py
# Opens at http://127.0.0.1:7861
```

## 7. Start the next Claude session

Tell Claude:  
*"Let's build Phase 3 MCP servers for the Analyst Desk capstone. Read docs/plan.md for the full plan."*

---

Shared repo: https://github.com/tshubhi24-dot/Capstone_IITB_2026  
Personal fork: https://github.com/jayshree-rajan/Capstone_IITB_2026
