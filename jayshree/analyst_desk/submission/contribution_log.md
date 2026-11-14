# Contribution log

Who built what. Dated detail: [work_log.md](work_log.md) and [../docs/plan.md](../docs/plan.md#contribution-log). Pull requests and commits on GitHub are the record.

## Team and roles

| Member | Role | Responsibilities |
|---|---|---|
| **Amit** | Role 1, Domain and product | Problem statement, user workflow, supported scope; financial, evidence, acceptance and memory rules; answer key and demo script |
| **Jayshree Rajan** | Role 2, Knowledge and memory | Ingestion, retrieval and reranking, query decomposition, memory store and policy |
| **Sachin Narang** | Role 3, Agents | Agent tool budgets, specialist prompts, cost metering, end-to-end agent tests |
| **Pranoti Deshmukh** | Security | Tool-level guards, approver signatures, quarantine of agent hand-offs |
| **Shubhi Tiwari** | Deployment and operations | Service and CI, setup and start/stop scripts, versioned configuration, UI workflow, alerts, held-out evaluation cases |
| **Pushparaj** | Role 6, Deployment checks | Docker networking checks, approval enforcement, CI on locked dependencies, evaluation-results audit, smoke checks |

Shared by the team: architecture, evaluation runs and report, slides and demo rehearsal.

AI tools used: Claude Code and GitHub Copilot, as recorded in [../docs/plan.md](../docs/plan.md#contribution-log).

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
| #30, #31 | Jayshree | Contribution log; Role 6 credited to Pushparaj |
