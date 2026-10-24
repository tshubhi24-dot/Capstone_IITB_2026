# Analyst Desk: project definition

**Group 22 | Version 1 | 22 October 2026**
**Status:** AI-assisted draft for team review, exported to the shared repository on 24 October 2026. The deployment uses Docker Compose. Named owners, real-user/domain review and measured results remain pending. This describes the current build target; the implementation is under construction.

## Problem, users and outcome

An equity research analyst at an asset manager must read annual filings, reconcile periods and units, calculate financial ratios, compare peers, and identify changed risks before writing a research note. Manual preparation takes time; an unsupported claim or wrong figure undermines trust.

**Analyst Desk prepares an inspectable, cited draft with figures calculated in code and publication controlled by the analyst.** We will measure accuracy, evidence support, review effort, cost and time. Faster preparation is a hypothesis, with no gain yet demonstrated.

The **primary user** requests research, edits the plan, inspects evidence, and approves, edits or rejects the note. A **reviewing analyst/domain reviewer** checks usefulness and financial interpretation. The capstone team builds and evaluates the system; a real-user/domain review is still required.

**Example:** “Compare Microsoft and Alphabet's operating margins for fiscal 2023–2025 and explain changes in their disclosed risk factors.”

## Scope and boundaries

| Decision | Version 1 scope |
|---|---|
| Sources | Cached original SEC 10-K filings and annual XBRL facts; retain Item 7, Item 1A, tables, URLs, accessions, periods and units. Synthetic data is labelled teaching material. |
| Coverage | FY2023–2025; Technology: MSFT, AAPL, GOOGL, ORCL, ADBE, CRM. Healthcare: ABBV, AMGN, GILD, ABT, UNH, TMO. Twelve companies satisfy the brief's 10–15-company, two-sector range. |
| Tasks | Revenue/operating-income retrieval; code-calculated margins and peer/year comparisons; evidence-backed risk changes; cited notes and comparisons with previous approved notes. |
| Comparability | Display actual fiscal periods and currency/scale. Equal fiscal labels do not imply identical calendar periods. Margin = operating income ÷ revenue × 100; preserve input references and rounding rules. |
| Limits | State missing evidence explicitly; invent no figures or material risk changes. No buy/sell recommendations, promised returns, trading, price forecasts, portfolio allocation or real-time news analysis. |
| Delivery | Local interface and research portal packaged with Docker Compose and persistent volumes. New-company imports are outside the frozen baseline; cloud hosting is outside initial scope. |

The working company selection comes from prior cached SEC source preparation. Its raw corpus and ingestion manifest are not included here. The new data import must verify coverage and record provenance again; no missing financial figure may be estimated to make a company eligible.

## Human control and memory

The brief requires an editable plan; we propose a review pause before research. The analyst must approve the **exact final note** before publication. Edits invalidate approval and require rechecking. People also review lessons, prepare independent labels and interpret results.

Save current progress and pending review in persistent LangGraph checkpoints; save scoped preferences, coverage and reviewed lessons in a SQLite-backed LangGraph store; retain approved notes in the portal database. Document access, retention, correction and deletion. Keep watchlists private and credentials outside memory. Detailed architecture follows this definition.

## Success criteria and ownership

These are **proposed team targets, not official grades or measured results**. The brief's required capabilities remain obligations. The [evaluation plan](EVALUATION_PLAN.md) defines denominators, labels, comparisons and freeze rules.

| Measure | Proposed acceptance target |
|---|---|
| Publication | Every published financial figure source-linked and independently code-checked; zero unauthorized publication. |
| Privacy/sandbox | Zero observed watchlist disclosures or successful sandbox network access in the defined suite. |
| Task completion | At least 80% held-out success in each final repetition, including failures/timeouts in the denominator. |
| Retrieval/claims | Provisionally mean Recall@5 ≥85%, subject to the complete relevance labels' achievable ceiling before runs; supported material narrative claims ≥90%. |
| Judge | Different-family judge calibrated on 20+ human-labelled outputs; Cohen's kappa ≥0.60. |
| Value/operations | Report comparative quality, cost, median/p95 latency and review effort; demonstrate Compose startup, resume, persistence, alert and CI gate. Set further budgets from development evidence before freezing. |

Assign actual names to six roles: **1** domain/product; **2** knowledge/memory; **3** agents/orchestration; **4** tools/control/security; **5** independent evaluation/red team; **6** deployment/operations. Agent tuners must not author final held-out cases; defence builders must not author attacks. Record real contributions as they occur.

**Authority:** course-supplied Capstone architecture and build guide, pp. 3–6 and 15–17; the course PDF is not redistributed in this repository. Separate cohort guidelines control official marks and deadlines. See [contributions and ownership](CONTRIBUTIONS.md) for provenance and pending role assignments.
