# Analyst Desk Supported Research Scope

**Status:** Final project specification v1.0.

## Purpose and intended user

Analyst Desk will assist an equity research analyst at an asset manager in preparing evidence-backed company-comparison notes from annual filings.

It will retrieve reported financial facts and relevant disclosures, calculate and check numerical results in code, compare fiscal years and suitable peers, and prepare a cited draft for human review.

The analyst can edit the research plan and must approve the exact final note before publication.

## Supported research questions

| Research task | Supported scope |
|---|---|
| Reported financial figures | Retrieve annual revenue and operating income for covered companies and years, with metric definitions, units, actual reporting periods and filing sources. |
| Ratios and trends | Calculate operating margins, annual growth and signed percentage-point changes in code using compatible inputs. |
| Peer comparisons | Compare selected companies using clearly defined metrics and explain material differences in fiscal periods, accounting bases and business models. |
| Risk-disclosure changes | Compare earlier and later Item 1A evidence to identify supported additions, removals or material changes in disclosed risks. |
| Management commentary | Summarise relevant Item 7 MD&A explanations and disclosure changes, attributing management's views and preserving uncertainty. |
| Previous-note follow-ups | Explain what changed since a relevant approved past note, using its recorded version and current evidence. |

Changed disclosure wording must be distinguished from evidence that an economic risk is new, more severe or causally responsible for a financial result.

### Example research requests

- "Compare Microsoft and Alphabet operating margins for FY2022-2024, explain fiscal-period differences, and cite the reported inputs and calculations."
- "Compare a covered company's FY2023 and FY2024 risk disclosures. Show evidence from both years and identify any limitations."
- "What changed since our last approved note on this company?"

The final example requires an actual relevant saved note.

## Data and evidence requirements

The project coverage is **15 companies in two project sectors over three fiscal years each**, within the required 10-15-company range.

The source for this version is cached SEC annual 10-K filings and XBRL financial facts. Required evidence includes:

- Item 1A Risk Factors.
- Item 7 Management's Discussion and Analysis.
- Relevant financial statements, preserved tables and explanatory notes.

Each reported financial figure must be traceable to an XBRL fact or cited table cell. Derived values must retain their input sources and be calculated and checked in code.

Evidence records will preserve company identifiers, fiscal years, filing sections, source URLs, filing identifiers, actual reporting dates, units and financial concepts.

Section boundaries, table extraction and source completeness must be reviewed before the dataset is accepted.

## Company coverage and research period

The following existing implementation list is retained for the project:

| Project group | Companies |
|---|---|
| Technology | Microsoft (MSFT), Alphabet (GOOGL), Apple (AAPL), Amazon (AMZN), Meta (META), NVIDIA (NVDA), AMD (AMD), Oracle (ORCL) |
| Finance | JPMorgan Chase (JPM), Goldman Sachs (GS), Bank of America (BAC), Visa (V), Morgan Stanley (MS), Mastercard (MA), Wells Fargo (WFC) |

**Confirmed period:** FY2022, FY2023 and FY2024.

For the retained 15 companies, this confirmed period provides **45 company-years**. This count does not establish operating-margin availability for every company. It is a historical research window and must be described accordingly.

Consecutive periods support repeatable year-to-year comparisons. Differences in business models and fiscal calendars provide opportunities to assess financial comparability and evidence limitations.

Technology and Finance are the project coverage groups. Apply the peer definitions and task-specific comparability checks in the Bank Metrics and Comparison Rules. Companies within the same broad group are not automatically suitable peers.

### Bank metric treatment

Operating margin and pre-tax margin are different metrics.

For operating-margin questions, the system must use supported operating-income and revenue inputs. Where these inputs are unavailable, it must explain the limitation rather than substitute a different margin.

A separately labelled bank pre-tax-margin task uses the definitions, compatible inputs and revised-plan controls in the Bank Metrics and Comparison Rules.

For JPM, GS, BAC, MS and WFC, support the separate pre-tax-margin task only when its required reported inputs are eligible. An operating-margin request with an unavailable operating-income input must retain the limitation; company coverage never permits a silent metric substitution.

## Request boundaries

| Condition | Required response |
|---|---|
| Unsupported company or year | Explain the coverage limit and invite a supported selection. |
| "Latest" or "last three years" request | Clarify the requested periods against the available evidence window. Do not silently interpret these terms as FY2022-2024. |
| Missing financial facts | Identify the missing evidence. Do not invent or estimate an absent reported figure. |
| Incomplete disclosure evidence | Return only supported findings with explicit limitations, or stop when the requested comparison cannot be supported. |
| Incompatible periods or metrics | Explain the differences. Apply only a documented, valid normalization method; otherwise request a revised comparison. |
| Uncertain risk novelty | Show both-period evidence and the extent reviewed. A missing retrieved passage does not establish that a risk was absent. |
| No relevant approved past note | Explain that the previous-note comparison is unavailable. A filing-period comparison may be offered through a revised plan. |
| Investment recommendation request | Decline buy/sell calls, price targets, promises of returns and forecasts of adverse events. Provide supported filing analysis within scope. |

New companies, years or research tasks must not be silently substituted into the agreed research plan.

**Data coverage: FY2022–FY2024 (historical). Requests for other fiscal years are outside current coverage.**

**Implementation responsibilities:** R6 displays the notice near company/year selection. R3 enforces supported years, with R4 guardrail support. R5 verifies both supported and unsupported requests.

## Required research output

A research note will contain:

1. The research question, selected companies and fiscal periods.
2. Financial figures and calculations with supporting source links.
3. Relevant year-to-year or peer comparisons.
4. Supported risk and management-commentary findings.
5. Both-period evidence for disclosure-change claims where applicable.
6. Missing evidence, comparability limitations and uncertainty.
7. Verification results and human-review status.

The analyst must approve the exact final note before publication. An edit requires fresh checking and approval.

Unresolved material numerical errors or incomplete required evidence review are not acceptable as a completed research result.

Apply the final bank-metric, fiscal-period/unit, filing-version, evidence/risk and acceptance/publication policies to every result and export.

## Outcomes to evaluate

The project will assess:

- Whether the note answers the agreed research question.
- Whether financial figures, calculations and explanatory claims are supported.
- The number and significance of corrections required.
- Total research and review time.
- Model usage and cost.

Equivalent tasks and evidence conditions will be used for comparisons. The existing spreadsheet or data-vendor workflow is a relevant user-workflow baseline.

Project evaluation will also compare fixed-workflow, single-agent and multi-agent designs.

No improvement in quality, time or cost is established by this scope document.

## Optional extensions

The following require separate scope and priority decisions:

- Onboarding arbitrary new companies.
- Quarterly research and charts.
- Excel or Capital IQ integration.
- Real-time news monitoring.
- Valuation and forecasting.
- Filing-length statistics.
- Systematic detection of omitted recurring wording and boilerplate changes.

Disclosure comparison remains part of the core research scope. Dedicated text-length and wording metrics are potential methods for improving that comparison.

Any such implementation must use comparable sections, reproducible calculations and source-linked differences. Increased filing length or omitted wording must not automatically be interpreted as adverse economic news.

## Scope execution requirements

| Area | Required behaviour |
|---|---|
| Research tasks | Support the six task categories and their response boundaries. |
| Company coverage | Retain the existing 15-company list. Company selection is confirmed; source completeness and metric availability still require review. |
| Sector and peer definitions | Use the defined coverage groups and metric-specific peers; check each comparison's reporting basis and business mix. |
| Historical window | FY2022-FY2024 confirmed. Display the limitation and validate unsupported-year handling. |
| Bank metrics | Apply metric-dependent support and the separately labelled bank task; preserve the requested metric and obtain revised-plan approval for a changed task. |
| Optional features | Keep extensions outside the assessed core until a separate scope change defines their evidence and acceptance requirements. |
| Useful outcome | Measure representative tasks using relevance, corrections, total research/review time, source-checking effort and model usage/cost. |

Record implementation verification and measured outcomes in the product checklist. Changes to this scope require a new identifiable specification version; a changed live research task also requires the applicable plan approval.
