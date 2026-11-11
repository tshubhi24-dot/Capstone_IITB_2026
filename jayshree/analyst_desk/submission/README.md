# Submission: Analyst Desk (Capstone Project 5)

**Due: 12 November 2026.** The final review covers the presentation, the demo and individual vivas.

This folder holds everything the brief asks for at submission (brief p.6, "What to submit"), plus the checklist we work from until then. Code and design documents stay where they are; this page links to them.

| File | What it is |
|---|---|
| [README.md](README.md) | This checklist: every deliverable and minimum-bar item, with status and owner |
| [work_log.md](work_log.md) | Dated log of submission work and fixes, kept up to the deadline |
| [experiment_log.md](experiment_log.md) | Every evaluation run: date, config, cases, result file, what we learned |
| [evaluation_report.md](evaluation_report.md) | The 4–6 page evaluation report (draft) |
| [demo_script.md](demo_script.md) | The live demo, step by step, and the plan for the backup recording |
| [slides_outline.md](slides_outline.md) | Slide-by-slide outline for the presentation |
| [viva_prep.md](viva_prep.md) | Answers to the brief's eight viva questions, with evidence to show |
| [ci_failure.md](ci_failure.md) | The failed CI run the brief asks for, with its explanation |

Status key: ✅ done · 🟡 partly done · ⬜ not started · 🔴 blocked on someone else.

## 1. What to submit (brief p.6)

| Deliverable | Where | Status | Owner |
|---|---|---|---|
| Repository with a README that starts everything with one command | [../README.md](../README.md) (`docker compose up`) | ✅ | Shubhi, Jayshree |
| Our own architecture diagram and numbered walkthrough | [../docs/architecture.md](../docs/architecture.md) §1 and §4 | 🟡 Recheck the diagram matches the final code; export a picture for the slides | Jayshree |
| Threat model page | [../docs/threat_model.md](../docs/threat_model.md) | ✅ | Jayshree |
| Memory policy page | [../docs/memory_policy.md](../docs/memory_policy.md) | ✅ | Jayshree |
| Evaluation report (4–6 pages) | [evaluation_report.md](evaluation_report.md) | 🟡 Development results in; held-out E1, E2, E3 and judge sections to fill | Team |
| Experiment log | [experiment_log.md](experiment_log.md) | 🟡 Development and smoke runs logged; E1–E4 to add | Team |
| Contribution log | [../docs/plan.md](../docs/plan.md#contribution-log) | 🟡 Each teammate checks their rows are complete | Everyone |
| Slides | Deck (13 slides, speaker notes): https://claude.ai/artifact/Kw2KfS1Ab3H4wjiujQKfSb · source in [slides/](slides/) (`deck.json` + one HTML file per slide; edit these, don't start a new deck) · PowerPoint: [slides.pptx](slides.pptx) | ✅ Final numbers; team to rehearse | Jayshree; team to rehearse |
| Backup demo recording | [demo_script.md](demo_script.md) | ⬜ | Role 1 (owns the demo script) |
| No API keys, private data or material we can't redistribute | `.env` is gitignored; data is public SEC filings | ✅ Recheck before the final push | Everyone |

## 2. Minimum bar (brief p.3)

| Lecture | Evidence the brief asks for | Where | Status |
|---|---|---|---|
| L4–L6 Retrieval | Recall@5 on 30+ labelled queries, before and after one change | [../docs/retrieval_eval.md](../docs/retrieval_eval.md): 36 queries; 0.389 → 0.903 with rerank, decomposition and rewrite | ✅ |
| L7 MCP | A tool list with schemas and one test per tool | [../docs/tools.md](../docs/tools.md), `tests/test_tools.py` | ✅ |
| L8 Orchestration | A graph diagram and a live demonstration of resume | architecture §3; resume shown in the demo (Load run) | 🟡 Rehearse the resume step |
| L9 Memory | A one-page memory policy and a memory-on vs memory-off comparison | memory policy; `results/memory_compare_20261025-112601.json` | ✅ |
| L10 Planning | A trace showing a replan | `tests/test_graph.py` replan test; live trace to capture | 🟡 Capture one live replan trace for the slides |
| L11 Multi-agent | A comparison of the single agent and the team | [../docs/evaluation.md](../docs/evaluation.md) (development set); held-out E1 ×3 to run | 🟡 |
| L12 Improvement | Held-out results before and after the playbook; the playbook; one rejected lesson with its reason | Reflexion loop built; playbook review in the app | 🔴 Needs lessons reviewed (one rejected) and held-out cases |
| L13 Evaluation | An evaluation report, judge agreement and a dashboard | Grafana dashboard ✅; report draft 🟡; judge agreement needs 20+ human labels | 🔴 Judge labels to collect |
| L14 Human control | A live demonstration of an edit invalidating an earlier approval | In the app; part of the demo | 🟡 Rehearse |
| L15 Security | Attack success with defences off and on, and the false-block rate | Harness `scripts/run_redteam.py` ready | 🔴 Needs 30+ attacks |
| L16 Deployment | Installation on a clean machine; one failed CI run with an explanation | [ci_failure.md](ci_failure.md) ✅; clean-machine install ⬜ | 🟡 |

## 3. Analyst Desk specifics (brief p.15–16)

| Item | Status |
|---|---|
| 10–15 companies, two sectors, three years; Item-aware parsing, tables kept | ✅ 15 companies (tech and banks), FY2022–FY2024 |
| Tools: filings-kb, edgar, python-sandbox, research-portal | ✅ |
| Signature A: every number linked to an XBRL fact or cited cell, checked by code; like-for-like | ✅ ([../docs/gap_closure.md](../docs/gap_closure.md)) |
| Signature B: parallel fan-out, critic loop, token budget; compared with a single agent | ✅ Built; held-out comparison to run |
| Security tests: injected "buy" article, watchlist in a search query, sandbox reaching the network | 🟡 Defences built and unit-tested; attack runs to do |
| 60 research questions, including risk changes labelled by hand for 10 company-years | 🟡 20 development + 24 held-out cases; the 10 hand labels to do |
| FinanceBench open sample as an external retrieval check | ✅ `scripts/eval_financebench.py`: 2 of 4 findable in-coverage questions in the top 5 (report §2) |
| Dashboard: verified share, critic rejections, tokens and cost per note, EDGAR cache hits, latency; alert below 98% verified | ✅ |
| E4 ablation: critic loop on and off; table-aware vs plain chunks | 🟡 Configs ready (`experiments/e4_*`); runs to do |
| Demo: (1) margin comparison with linked facts (2) critic fixing a planted wrong number while the injected "buy" stays out (3) "What changed since our last note?" | 🟡 [demo_script.md](demo_script.md) |

## 4. Critical path to 12 November

1. **9 Nov:** merge PR #14 (gap fixes). Approve one real lesson and reject one, with a reason.
2. **10 Nov:** held-out cases and attacks ready. Freeze the playbook. Run E1 ×3, E2, E3 and E4 (about $5–10 of OpenRouter credit). Do the clean-machine install.
3. **11 Nov:** finish the evaluation report and experiment log, build the slides, record the backup demo.
4. **12 Nov:** final read-through, check nothing secret is committed, submit.

