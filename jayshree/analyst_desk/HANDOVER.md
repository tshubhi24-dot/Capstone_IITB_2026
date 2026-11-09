# Analyst Desk — Setup

IIT Bombay Agentic AI Capstone · Project 5

Two ways to run it. **Option A (Docker)** needs only Docker Desktop; **Option B
(Python)** is for developing and running the tests.

---

## Option A — Docker (recommended for trying it out)

1. Install Docker Desktop (Windows: keep "Use WSL 2"; Mac: Intel or Apple
   Silicon). No Docker account needed. Start it and wait for "Engine running".
2. Clone and enter the project:

   ```bash
   git clone https://github.com/tshubhi24-dot/Capstone_IITB_2026.git
   cd Capstone_IITB_2026/jayshree/analyst_desk
   ```

3. Create `.env` from `.env.example` with **your own** OpenRouter key (never commit it).
4. Start everything:

   ```bash
   docker compose up --build
   ```

   Open <http://127.0.0.1:7861>. The first start builds the image (~10 min,
   ~2–3 GB download) and then the vector index (~10 min on CPU); later starts
   take seconds. Stop with Ctrl+C, or `docker compose down`.

What starts: the app, the four MCP servers (filings-kb, edgar, python-sandbox,
research-portal), a one-off index builder, and the observability stack:
Jaeger traces <http://127.0.0.1:16686>, Prometheus <http://127.0.0.1:9090>
(alerts at /alerts), Grafana <http://127.0.0.1:3000> (dashboard "Analyst Desk").
The MCP servers sit on an internal network with no internet access; only the
app can reach OpenRouter.

## Tour of the app

| Tab | What it is |
|---|---|
| 📈 Dashboard | EDGAR-verified revenue, margins and income |
| 💬 Research Chat | C0 baseline (fixed pipeline, one model call), with "How this answer was built" |
| 🤖 Research Agent | C1 single agent or C2 team: plan gate → live team board and tool calls → checked note → approve/edit/reject → publish. Also: your runs, 🧠 Memory, 📘 Playbook (review lessons), 📚 Published notes |
| 📏 Evaluation | Golden set, run C0/C1/C2 on it, results (E1 table, per-case grid), ⚖️ judge calibration (label claims, Cohen's kappa) |
| 🔍 Data Explorer | Search the 10-K passages directly |

Reasoning behind every design decision: `docs/viva_notes.md`. Results so far:
`docs/evaluation.md` (dev set), `docs/retrieval_eval.md` (Recall@5).

## For role 5 (evaluation and red team)

- Write the **held-out** cases in `data/evaluation/heldout/` (see the README
  there). Whoever tunes the agent must not write or see them.
- Label the judge-calibration items in the Evaluation tab (⚖️), then compute kappa.
- The red-team suite (30+ attacks, defences on vs off) is yours too: the
  person who built the defences must not write the attacks.

## Option B — Python (development and tests)

Tested with Python 3.14 on Windows (3.12+ should work).

```bash
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` as in step 3 above, then:

```bash
python -m unittest discover -s tests                      # all tests
python -m analystdesk --companies MSFT GOOGL JPM --years 2022 2023 2024 --mode baseline
python scripts/eval_retrieval.py                          # Recall@5 report
python app.py                                             # http://127.0.0.1:7861
```

With Docker Desktop running, build the code-sandbox image once so
`run_python` uses a locked-down container (otherwise it falls back to a local
guarded process and the Docker tests are skipped):

```bash
docker build -t analystdesk-sandbox -f docker/sandbox/Dockerfile .
```

## Data — already in the repo

`data/passages/` (table-aware 10-K chunks), `data/passages_plain/` (plain-text
chunks for the E4 ablation) and the EDGAR XBRL/submissions JSON in
`data/edgar_cache/` are committed, so a fresh clone needs **no** SEC download.

Built locally on first use (not in git): the Chroma vector index
(`data/index/`, or a Docker volume) and raw 10-K HTML
(`data/edgar_cache/filings/`, only needed to re-chunk:
`python -c "from analystdesk.ingest import ingest_all; ingest_all()"`).

## Security fixes (branch `pranoti-security`)

Numbered fixes made against the gaps in `docs/security_summary.md`. Every line
this module touches carries `# Fix for Module 4 - Security`, and each fix also
carries its own number, so the module as a whole and any single fix are both
greppable:

```bash
grep -rn 'Fix for Module 4 - Security' analystdesk/ tests/ --include='*.py'
grep -rn 'Fix 1 -' analystdesk/ --include='*.py'
```

The first is the one to run before a merge: it lists every change this module
made, including the four files in `analystdesk/agent/` that sit outside this
branch's `servers/ docs/ tests/` remit and the one line it adds to
`requirements.txt`.

**Fix 1 — `UNSOURCED_ADVICE`, a guardrail on every write tool.** A
`wrap_tool_call`-style middleware (`analystdesk/servers/guardrails.py`) reads
`publish_note`'s own arguments and refuses the call when a sentence takes a
position on the security and cites nothing — the tool never runs, and the
agent gets an ordinary `ok: false` result it can read. It answers use case 3
(injected recommendation), where a recommendation reworded out of
`check_note`'s eleven-word filter passed every automated layer.

One part of it sits **outside** this branch's `servers/ docs/ tests/` remit
and is worth knowing about if you own the agent package: `agent/runtime.py:42-58`
now calls `servers.client.load_guarded_tools` instead of langchain-mcp-adapters'
`load_mcp_tools`. The adapter takes its interceptors per call, so without that
change the guardrail would be installed on `make_client()` and still missing
from every real run. Three lines and an import, all marked `# Fix 1 - use case
3`; reverting them disables Fix 1 and nothing else.

The guardrail is **author-blind on purpose**: it refuses a sentence the analyst
typed at the gate exactly as it refuses the writer's, because `publish_note`
carries no author and the one authenticated name in the call is bound by hash to
the text being judged. Ordinary commentary is untouched — only a position on the
security with nothing cited is refused. If a desk needs it softer while it
adopts the citation rule, `ADVICE_GUARD_MODE=warn` lets the write through and
returns the same finding under `warnings` on the result instead; `enforce` is
the default, and an unset or misspelt value enforces. One thing for whoever owns
the UI:
`agent_ui.py:109` reports every failed publish as *"refused by the portal"*,
which is wrong for this one — it comes from the interceptor, before the portal
is reached.

**Fix 2 — `APPROVAL_UNSIGNED`, the approver's own signature.** The approval
token is an HMAC, and HMAC is symmetric: `research-portal` must hold
`APPROVAL_SECRET` to *check* a token, so it can also *mint* one, and the app
holds it because the note gate is where it signs. Fix 2 keeps that token and
adds the half it cannot give — an Ed25519 signature from a key this project
only ever holds the public half of (`analystdesk/servers/signing.py`). It
answers use case 2 (forced approval injection).

**It is off until a public key is registered, and the repo registers none**, so
nothing changes on a fresh checkout. To turn it on, the approver runs this on
their own machine and sends only the `.pub`:

```bash
python -m analystdesk.servers.signing keygen jayshree --out ~/keys
# copy ~/keys/jayshree.pub into data/approval/approvers/ (or APPROVER_KEYS_DIR)
# the .key never leaves their device
python -m analystdesk.servers.signing sign --key ~/keys/jayshree.key --note note.json
python -m analystdesk.agent resume RUN_ID --approve --approver jayshree --signature <sig>
```

Once any key is registered every publish needs a valid signature, including
from approvers with no key — so there is no unregistered name to hide behind.
Two things it touches outside the remit: `agent/graph.py` and
`agent/__main__.py` carry the signature from the gate to the tool call (marked
`# Fix 2 - use case 2`), and `cryptography` is a new direct dependency — the
stdlib has no asymmetric signatures. The Gradio gate in `app.py` has no
signature field yet, so register keys only after that is added.

**Fix 3 — only typed fields cross the C2 hand-off.** A specialist used to hand
the writer up to 6,000 characters of its own prose, so anything it read could
arrive in the specialist's voice — an injection never had to survive as a
quote, it only had to be obeyed once. The hand-off now carries spans copied
verbatim out of a passage the specialist cites, each checked against that
passage by code, plus `fact_id`s whose values code looks up. No sentence a
specialist wrote reaches the writer (`analystdesk/servers/quarantine.py`). It
answers use cases 3 and 4. Each claim is checked on its own, so one that fails —
not verbatim, too long, past the twelve-claim cap — is dropped with a counted
reason while its neighbours still cross, and the limits are in the prompt the
specialist is given rather than being rules it can only find by breaking.

**This one changes behaviour, not just defences.** It is the only fix that is
not a guardrail beside the pipeline: most of its diff is in `agent/team.py` and
`agent/graph.py` (marked `# Fix 3 - use cases 3 and 4`), and because it changes
what C2's writer is given, **C2's numbers in `docs/evaluation.md` need
re-measuring** — `CLAUDE.md` makes C0/C1/C2 sharing retrieval an invariant so
E1 measures orchestration, and quoted spans may read worse than a fluent
summary. That trade was taken deliberately.

Verify all three, offline and in about twenty seconds:

```bash
python -m tests.security.test_injected_recommendation          # verdict matrix, 58 tests
python -m unittest tests.security.test_forced_approval_injection   # 35 tests
python -m unittest tests.security.test_quarantined_handoff     # 35 tests
python -m unittest discover -s tests                           # whole suite: 279 tests
```

Full reasoning for all three, what they deliberately do *not* claim, and the
list of gaps still open: `docs/security_summary.md` — section **Fixes made** at the end.
The slide deck is `docs/presentation.pptx`, section **Additional guardrails**
(rebuild: `cd docs/presentation && node build.js`).

## Next phase

Phase 4: C1 single agent in LangGraph over the MCP tools (plan shown to the
analyst, SQLite checkpointer, stop and resume). See `docs/plan.md`; tool
schemas are in `docs/tools.md`; reasoning for every decision so far is in
`docs/viva_notes.md`.

---

Shared repo: https://github.com/tshubhi24-dot/Capstone_IITB_2026  
Personal fork: https://github.com/jayshree-rajan/Capstone_IITB_2026
