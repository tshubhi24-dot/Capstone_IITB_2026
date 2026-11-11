# Slides outline

**Format:** about 12 slides for about 12 minutes, then the live demo ([demo_script.md](demo_script.md)).

**Marks:** the rubric weighs scope and impact, technical depth, presentation and the viva roughly equally. The brief asks the presentation to "trace one request through the architecture and present numbers with context".

| # | Slide | Content | Source |
|---|---|---|---|
| 1 | Title | Analyst Desk: research notes where every number checks out. Team of six, with roles | — |
| 2 | The user and the problem | An equity analyst writing a note from 10-Ks; one wrong number undermines the note. Today's workflow vs ours | [../docs_notfor_submission/product_spec.md](../docs_notfor_submission/policies/product_spec.md) §1–3 |
| 3 | What we built, in one picture | Our redrawn architecture diagram: UI/FastAPI → guardrails → LangGraph lead → specialists → MCP servers → approval gate → portal; the operate-and-measure band | [../docs_notfor_submission/architecture.md](../docs_notfor_submission/architecture/architecture.md) §1 |
| 4 | One request, start to finish | The brief's MSFT vs GOOGL request through steps 1–8, and who decides at each step: model, code or person | architecture §4 |
| 5 | Signature A: numbers you can trust | Placeholder → code-rendered figure with fact_id → checker (value, sign, scale, company/year, basis) → Comparability section (June vs December year-ends, 53-week years, pre-tax for banks) | [../docs_notfor_submission/gap_closure.md](../docs_notfor_submission/gap_closure.md), `checks.py` |
| 6 | Signature B: deep-research orchestration | Parallel fan-out, critic loop (≤2 revisions), token and tool budget enforced by hooks; same budget as C1 | `team.py` |
| 7 | E1 results | C0 / C1 / C2 table: success, verified share, cost, latency; development now, held-out ×3 with spread when run | [evaluation_report.md](evaluation_report.md) §3 |
| 8 | Retrieval and memory | Recall@5 0.389 → 0.903; memory on vs off | report §2, §8 |
| 9 | Safety | Threat model in one line; defence layers; E2 attack success off vs on, and false blocks | [../docs_notfor_submission/threat_model.md](../docs_notfor_submission/policies/threat_model.md), report §4 |
| 10 | Learning and evaluation | Reflexion lessons (one accepted, one rejected with its reason), frozen playbook version, E3; judge kappa | report §5, §7 |
| 11 | Operations | Docker Compose with one command, Grafana dashboard, 98% alert, CI with the failed-run story | [ci_failure.md](ci_failure.md) |
| 12 | Limits and next steps | Honest limits (fixed corpus, typed names, judge scope); what a supervised pilot would need: sign-in, a per-call sandbox, a prompt-injection classifier, a correction workflow | report §9 |

Tips:
- Put numbers on the slides with their context: development vs held-out, n, and the spread over three runs.
- Every teammate presents the slide for their own role. In the viva, everyone must be able to redraw slide 3 from memory.
