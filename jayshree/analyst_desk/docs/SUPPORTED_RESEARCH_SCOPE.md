# Analyst Desk Supported Research Scope

**Status:** Scope document for team review. The existing 15-company list is retained. The fiscal-year window, bank-metric policy and remaining scope decisions are open.

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

The assessed dataset will cover **10-15 companies in two sectors over three fiscal years each**.

The proposed source for this version is cached SEC annual 10-K filings and XBRL financial facts. Evidence will include:

- Item 1A Risk Factors.
- Item 7 Management's Discussion and Analysis.
- Relevant financial statements, preserved tables and explanatory notes.

Each reported financial figure must be traceable to an XBRL fact or cited table cell. Derived values must retain their input sources and be calculated and checked in code.

Evidence records will preserve company identifiers, fiscal years, filing sections, source URLs, filing identifiers, actual reporting dates, units and financial concepts.

Section boundaries, table extraction and source completeness must be reviewed before the dataset is accepted.

## Company coverage and proposed years

The following existing implementation list is retained for the project:

| Project group | Companies |
|---|---|
| Technology | Microsoft (MSFT), Alphabet (GOOGL), Apple (AAPL), Amazon (AMZN), Meta (META), NVIDIA (NVDA), AMD (AMD), Oracle (ORCL) |
| Finance | JPMorgan Chase (JPM), Goldman Sachs (GS), Bank of America (BAC), Visa (V), Morgan Stanley (MS), Mastercard (MA), Wells Fargo (WFC) |

**Proposed period:** FY2022, FY2023 and FY2024. The period remains to be finalized.

For the retained 15 companies, this proposed period provides **45 company-years**. This count does not establish operating-margin availability for every company. It is a historical research window and must be described accordingly.

Consecutive periods support repeatable year-to-year comparisons. Differences in business models and fiscal calendars provide opportunities to assess financial comparability and evidence limitations.

The company names are retained; the sector classification and suitable peer groups still require agreement. Companies within the same broad group are not automatically suitable peers.

### Bank metric treatment

Operating margin and pre-tax margin are different metrics.

For operating-margin questions, the system must use supported operating-income and revenue inputs. Where these inputs are unavailable, it must explain the limitation rather than substitute a different margin.

A separately labelled bank pre-tax-margin task may be supported after the financial policy is agreed.

The metric treatment of JPM, GS, BAC, MS and WFC remains open. Retaining their company names does not approve the current pre-tax-margin substitution for operating-margin requests.

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

Detailed rules for rounding, restatements, financial comparability and publication eligibility will be documented in the financial and research policies.

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

## Decisions required before scope adoption

| Decision | Review required |
|---|---|
| Research tasks | Agree the six supported task categories and response boundaries. |
| Company coverage | Retain the existing 15-company list. Company selection is confirmed; source completeness and metric availability still require review. |
| Sector and peer definitions | Agree defensible groupings and appropriate comparison sets. |
| Historical window | Confirm FY2022-2024 or select another explicit three-year period. |
| Bank metrics | Agree metric-dependent support or a separately labelled bank task without substituting it for operating margin. |
| Optional features | Prioritise extensions separately from the assessed core. |
| Useful outcome | Agree representative tasks and measures of usefulness, quality, time and cost. |

Practitioner feedback and subsequent product testing may lead to revisions. Scope adoption, implementation verification and outcome validation will be recorded as separate decisions.
