# Contribution log

Who built what. Dated detail: [work_log.md](work_log.md) and [../docs/plan.md](../docs/plan.md#contribution-log). Pull requests and commits on GitHub are the record.

## Team and roles

| Member | Role | Main contributions | AI help |
|---|---|---|---|
| **Jayshree Rajan** | Base system; Role 2, knowledge and memory | EDGAR/XBRL facts; 10-K ingestion (table-aware); hybrid retrieval, reranker, query decomposition; MCP servers; C0, C1, C2; code checks and judge; HMAC approval; memory and playbook; evaluation harness and held-out runs; observability; the app; analyst override; submission docs and slides | Claude Code |
| **Amit** | Role 1, domain and product | Problem statement; user workflow; supported scope; bank, fiscal-year, unit and filing-version rules; evidence, acceptance and memory policies; 20-case answer key; frontend messages; implementation and note reviews; demo script | — |
| **Sachin Narang** | Role 3, agents | One tool budget for C1 and C2; C2 budget split; per-specialist cost metering; specialist prompt fixes; offline end-to-end tests of C1 and C2 | — |
| **Pranoti Deshmukh** | Security (Module 4) | Advice guard on write tools; optional Ed25519 approver signatures; quarantine of C2 hand-offs | — |
| **Shubhi Tiwari** | Deployment and operations | FastAPI service; Docker persistence; CI and evaluation gate; Windows setup; start/stop scripts; versioned LLM config; unified Research tab; run cancel; in-app alerts; fiscal-year confirmation; 40 held-out cases; gap fixes and citation inventory | GitHub Copilot |
| **Pushparaj** | Role 6, deployment checks | App reaches MCP servers over HTTP in Docker; approval refused while checks fail; CI on the lock file with Prometheus rule checks; evaluation-results audit; `ops_smoke.py` | — |

## By deliverable

| Deliverable | Owner(s) |
|---|---|
| Data, retrieval, MCP tools | Jayshree |
| C0 / C1 / C2 agents | Jayshree; Sachin (budgets, prompts, tests) |
| Product spec, rules, answer key | Amit |
| Security and guardrails | Jayshree; Pranoti (Module 4) |
| Memory and reflexion | Jayshree |
| Deployment, CI, operations | Shubhi; Pushparaj (Role 6 checks); Jayshree (Compose, image) |
| Held-out evaluation set | Jayshree (24-case v1); Shubhi (40 cases) |
| Evaluation runs and report | Jayshree |
| Slides | Jayshree; team rehearsal |

## Pull requests

Team repository, tshubhi24-dot/Capstone_IITB_2026. "via" = merged by Jayshree after resolving conflicts. PR #10 was opened from the GitHub account `nidhi-00`.

| PR | Author | What |
|---|---|---|
| #1 | Sachin | Role 3: C2 budget and prompt changes |
| #2, #8 | Shubhi | Deployment features; in-app Prometheus alerts |
| #3–#6 | Jayshree | Placeholder safety; docs; pinned team Docker image; README |
| #7 | Amit | R1 role documents |
| #9 | Jayshree | R1 specifications merged into the app docs |
| #10 | Pushparaj | Role 6: deployment, CI, monitoring, evaluation integration |
| #11, #12, #14 | Jayshree | Capstone gaps; on-demand evaluation gate; gap fixes and submission folder |
| #13 (via #18) | Shubhi | Start/stop scripts, fiscal-year confirmation |
| #15 (via #20) | Amit | Development answer key, reviews, evidence |
| #17 (via #19) | Pranoti | Security module 4 |
| #21, #25 | Shubhi | Held-out cases; contribution log |
| #22, #23 | Jayshree | Evaluation results, report, viva prep; judge calibration sheet |
| #26–#29 | Jayshree | Note gate: highlighted lines and analyst override |
| this PR | Jayshree | Contribution log; Role 6 credited to Pushparaj |
