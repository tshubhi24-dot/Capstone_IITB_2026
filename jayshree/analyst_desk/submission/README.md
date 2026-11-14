# Submission: Analyst Desk (Capstone Project 5, Group 22)

Team: Amit, Jayshree Rajan, Sachin Narang, Pranoti Deshmukh, Pushparag Vaidya, Shubhi Tiwari. Roles: [contribution_log.md](contribution_log.md).

Everything the brief asks for at submission (brief p.6). Code and design documents stay where they are; this page links to them.

| File | What it is |
|---|---|
| [evaluation_report.md](evaluation_report.md) | Evaluation report: retrieval, E1–E4, memory, limits |
| [heldout_results.md](heldout_results.md) | E1 held-out results, every case |
| [redteam_results.md](redteam_results.md) | E2 attack results, every attack |
| [experiment_log.md](experiment_log.md) | Every evaluation run: date, config, cases, result file, what we learned |
| [contribution_log.md](contribution_log.md) | Roles, members and pull requests |
| [work_log.md](work_log.md) | Dated log of work and fixes |
| [demo_script.md](demo_script.md) | The live demo, step by step |
| [demo/](demo/) | Demo-only Compose file that plants the injected "buy" article |
| [slides.pptx](slides.pptx) | Presentation (13 slides, speaker notes); source in [slides/](slides/) |
| [ci_failure.md](ci_failure.md) | The failed CI run, with its explanation |
| `Group 22 - Analyst Desk Demo.mp4` | Backup demo recording (submission folder only) |

Status key: ✅ done · 🟡 partly done · ⬜ not done.

## 1. What to submit (brief p.6)

| Deliverable | Where | Status |
|---|---|---|
| Repository with a README that starts everything with one command | [../README.md](../README.md) (`docker compose up`) | ✅ |
| Architecture diagram and numbered walkthrough | [../docs/architecture.md](../docs/architecture.md) §1 and §4 | ✅ |
| Threat model page | [../docs/threat_model.md](../docs/threat_model.md) | ✅ |
| Memory policy page | [../docs/memory_policy.md](../docs/memory_policy.md) | ✅ |
| Evaluation report | [evaluation_report.md](evaluation_report.md) | ✅ Judge calibration not done (§9) |
| Experiment log | [experiment_log.md](experiment_log.md) | ✅ |
| Contribution log | [contribution_log.md](contribution_log.md) | ✅ |
| Slides | [slides.pptx](slides.pptx) | ✅ |
| Backup demo recording | `Group 22 - Analyst Desk Demo.mp4` | ✅ |
| No API keys, private data or material we can't redistribute | `.env` is git-ignored; data is public SEC filings | ✅ |

## 2. Minimum bar (brief p.3)

| Lecture | Evidence the brief asks for | Where | Status |
|---|---|---|---|
| L4–L6 Retrieval | Recall@5 on 30+ labelled queries, before and after one change | [../docs/retrieval_eval.md](../docs/retrieval_eval.md): 36 queries; 0.472 → 0.903 with decomposition and rewrite | ✅ |
| L7 MCP | Tool list with schemas, one test per tool | [../docs/tools.md](../docs/tools.md), `tests/test_tools.py` | ✅ |
| L8 Orchestration | Graph diagram; resume | [architecture](../docs/architecture.md) §3; Load run ([demo_script](demo_script.md) §4) | ✅ |
| L9 Memory | Memory policy; memory on vs off | [memory policy](../docs/memory_policy.md); [report](evaluation_report.md) §8 | ✅ |
| L10 Planning | A replan | Replan path in both graphs (`tests/test_graph.py`); real replans in held-out v1 runs ([experiment_log](experiment_log.md) run 18, [report](evaluation_report.md) §4); [demo_script](demo_script.md) §5 | ✅ |
| L11 Multi-agent | Single agent vs team | [report](evaluation_report.md) §4: 40 held-out cases × 3 runs | ✅ |
| L12 Improvement | Before and after the playbook; one rejected lesson | [report](evaluation_report.md) §6: 1 lesson approved, 2 rejected with reasons; C1 arm done | 🟡 C2 arm incomplete (budget) |
| L13 Evaluation | Report, judge agreement, dashboard | [report](evaluation_report.md); Grafana dashboard | 🟡 Judge agreement: sheet ready, not labelled |
| L14 Human control | An edit invalidates an earlier approval | HMAC approval of the exact note ([architecture](../docs/architecture.md) §7); `tests/test_tools.py` `test_edit_after_approval_invalidates_it`; analyst override recorded with a reason | ✅ |
| L15 Security | Attacks with defences off and on; false-block rate | [report](evaluation_report.md) §5: 32 attacks, 10 → 3 through, 0/17 false blocks | ✅ |
| L16 Deployment | Clean-machine install; one failed CI run explained | Teammates install from the published, pinned image with `start.bat` / `start.sh` ([../README.md](../README.md)); [ci_failure.md](ci_failure.md) | 🟡 No separate clean-machine record |

## 3. Analyst Desk specifics (brief p.15–16)

| Item | Status |
|---|---|
| 10–15 companies, two sectors, three years; Item-aware parsing; tables kept | ✅ 15 companies (tech and banks), FY2022–FY2024 |
| Tools: filings-kb, edgar, python-sandbox, research-portal | ✅ |
| Signature A: every number linked to an XBRL fact or cited cell, checked by code; like-for-like | ✅ |
| Signature B: parallel fan-out, critic loop, token budget; compared with a single agent | ✅ [report](evaluation_report.md) §4 |
| Security tests: injected "buy" article, watchlist in a search query, sandbox reaching the network | ✅ [redteam_results.md](redteam_results.md) |
| 60 research questions | ✅ 44 development + 40 independent held-out + 24 generated held-out |
| Risk changes labelled by hand for 10 company-years | ⬜ |
| FinanceBench open sample as an external retrieval check | ✅ 2 of 4 findable in-coverage questions in the top 5 ([report](evaluation_report.md) §3) |
| Dashboard: verified share, critic rejections, tokens and cost per note, EDGAR cache hits, latency; alert below 98% verified | ✅ |
| E4 ablation: critic loop on and off; table-aware vs plain chunks | ✅ [report](evaluation_report.md) §7 (development set) |
| Demo: margin comparison; critic fixing a planted wrong number while the injected "buy" stays out; "What changed since our last note?" | ✅ [demo_script.md](demo_script.md), recording |
