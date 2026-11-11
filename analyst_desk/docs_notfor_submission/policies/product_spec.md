# Analyst Desk: product specification

What Analyst Desk is for, what it covers and the domain rules a research note follows. For each rule, this page says how the app applies it, and [section 9](#9-where-the-app-differs-from-the-specification) lists where the app does not yet meet the specification.

Product and domain specification by Role 1 (domain and product). How the parts are built is in [architecture.md](../architecture/architecture.md); the memory rules are in [memory_policy.md](memory_policy.md) and the reference answers in [evaluation_guide.md](../evaluation_guide.md#9-reference-answers).

---

## 1. Problem and intended outcome

Equity research analysts at asset managers prepare company-comparison notes from annual filings. That means finding the supporting disclosures, extracting reported figures, reconciling fiscal periods and units, calculating ratios, comparing companies and years, and judging how risk disclosures changed. A wrong figure, an incompatible comparison or an unsupported conclusion undermines trust in the note.

Analyst Desk prepares a **cited draft note** that the analyst can inspect, challenge, correct and decide whether to publish:

- every reported figure traces to an SEC XBRL fact or a cited filing passage, and every derived number is calculated and checked in code;
- differences in fiscal periods and margin definitions are stated;
- the analyst approves the research plan, and then the exact final note, before anything is published.

Numerical verification supports the analyst's judgement; it does not prove every interpretation is right. The output is informational: no buy or sell calls, price targets or forecasts.

**Evaluation question:** how does coordinated research with a critic (C2) compare with a fixed pipeline (C0) and a single agent (C1) in quality, cost and time under matched conditions? See [evaluation_guide.md](../evaluation_guide.md).

## 2. The user and their workflow

**Practitioner input.**
- Charles Cheng's written feedback describes reading news, filings and reports, updating an Excel earnings and valuation model, and forming or updating an investment thesis from it. Collecting, updating and communicating information are the slow steps that limit how many companies an analyst can cover. He puts more weight on expectations versus actual results than on filing differences alone, and requires every assertion to trace to an original document or figure.
- Informal input from Klemens Loeffler points to changes in commentary, section length and recurring wording that disappears as useful things to investigate. They are checkpoints, not proof that a change is economically important.

**Where Analyst Desk fits.** Forecasts, valuation and the investment thesis stay with the analyst. Analyst Desk assembles evidence for the existing process:

| Stage | Analyst activity | What Analyst Desk does |
|---|---|---|
| 1. Frame the question | Choose companies, years and the question | Turns the request into a plan the analyst approves or edits |
| 2. Read sources | News, filings, reports | Searches the 10-K risk factors (Item 1A) and MD&A (Item 7) |
| 3. Update the model | Excel earnings and valuation model | Not covered |
| 4. Inspect disclosures | Statements, commentary, risk factors | Compares risk factors across two years with passages from both |
| 5. Reconcile inputs | Fiscal dates, metrics, units, filing versions | Code renders figures with their period end; a different later value is flagged |
| 6. Prepare findings | Review figures, explanations, limitations | Drafts the note; code checks numbers and live C1/C2 runs use a claim judge before approval |
| 7. Retain and revisit | Save the reviewed note | Publishes the approved note and remembers it for "what changed since our last note" |

**Measures of usefulness:** relevance, important omissions, the number and significance of corrections, total research and review time, source-checking effort and model cost. No improvement is claimed before it is measured.

**Outside the product:** news ingestion, consensus or expectations data, Excel or Capital IQ integration, forecasting and valuation. An expectations comparison would need a dated, compatible expectation as a separate input; the app has none, so it reports actual trends only.

## 3. Supported scope

**Coverage: 15 companies × FY2022–FY2024 (45 company-years), from cached SEC 10-K filings and XBRL facts.**

| Group | Companies |
|---|---|
| Technology | Microsoft (MSFT), Alphabet (GOOGL), Apple (AAPL), Amazon (AMZN), Meta (META), NVIDIA (NVDA), AMD (AMD), Oracle (ORCL) |
| Finance | JPMorgan Chase (JPM), Goldman Sachs (GS), Bank of America (BAC), Visa (V), Morgan Stanley (MS), Mastercard (MA), Wells Fargo (WFC) |

The list is fixed in [scope.py](../../analystdesk/research/scope.py) and the years in `COVERED_YEARS` ([servers/common.py](../../analystdesk/servers/common.py)). Being in the same group does not make two companies suitable peers.

**Research tasks:**

| Task | What the note contains |
|---|---|
| Reported figures | Annual revenue and operating income (pre-tax income for banks), with the period end and the XBRL fact |
| Ratios and trends | Margins, annual growth and margin changes in percentage points, calculated in code |
| Peer comparisons | The same metric across selected companies, with their different fiscal year ends stated |
| Risk-disclosure changes | Compare requested years using cited Item 1A excerpts from both years; excerpts cannot establish whole-section absence, additions or removals |
| Management commentary | Item 7 MD&A explanations, attributed to management |
| Previous-note follow-ups | "What changed since our last note": previous → current figures, computed by code from the remembered note |

**Request boundaries:**

| Condition | What the app does |
|---|---|
| Company not covered | Stops before planning: "No covered company named", with the supported tickers |
| Year outside FY2022–2024 | Stops before planning: "Only fiscal years (2022, 2023, 2024) are covered" |
| Investment advice (buy/sell, price targets) | Stops before planning; any advice wording in a draft is also flagged by the checker |
| A tool reports data outside coverage during research | The agent replans, and the analyst sees and approves the revised plan |
| Missing financial fact | The figure is unavailable; the writer has no placeholder for it, and a number typed without a source is flagged by the checker |
| No previous note for a follow-up | The note says "There is no previous note in memory to compare against" |

## 4. Financial rules

### Metrics

| Metric | Definition | Companies |
|---|---|---|
| Operating margin | Operating income ÷ revenue × 100 | The 8 technology companies, Visa, Mastercard |
| Pre-tax margin | Income before income taxes ÷ total net revenue (after interest expense) × 100 | JPM, GS, BAC, MS, WFC |
| Margin change | Later margin − earlier margin, in signed percentage points | Same company, same basis |
| Growth | (later amount ÷ earlier amount − 1) × 100 | Same company, same metric |

- **Banks use pre-tax margin, fixed per company** (`margin_basis` in [scope.py](../../analystdesk/research/scope.py)). Banks do not report an operating-income line in XBRL, so the basis cannot switch between years and an operating margin is never invented for a bank. The figure is labelled "pretax margin" and the bank's revenue "net revenue".
- **Operating and pre-tax margins are different metrics.** A gap, ranking or average across them is not valid even though the subtraction is correct: a company at 20.00% operating margin and a bank at 30.00% pre-tax margin are not "10 points apart". The checker rejects any line that sets one against the other, and the plan gate says which companies are banks.
- **Inputs come from consolidated U.S. GAAP reported figures**; segment, managed or adjusted figures are not used. Other bank ratios (net interest margin, return on equity, capital ratios) are out of scope.
- **Percentage points are not percent growth.** A margin rising from 30.00% to 32.00% is +2.00 pp, not 6.67% growth.

### Fiscal periods

- **"FY2024" means each company's own reported fiscal year 2024.** Microsoft's runs July 2023 to June 2024; Alphabet's is the calendar year. Different year ends are not a reason to stop. Code adds a **Comparability** section to the note whenever it applies: the fiscal year-end of each company when they differ, any 53-week fiscal year (Apple FY2023, AMD FY2022), and a statement that bank pre-tax margins are not comparable with operating margins ([figures.py](../../analystdesk/finance/figures.py)).
- **Only full-year facts are used** (about 365 days), so quarter-only or year-to-date values cannot enter an annual margin ([edgar.py](../../analystdesk/finance/edgar.py)).
- **A fiscal year is the year the period ends,** checked against the filing rather than assumed from the filing date.
- A fiscal year is not relabelled as a calendar year, and missing months are not estimated.
- **Relative periods require explicit confirmation.** "Last three years" proposes the latest three covered years (currently FY2022–FY2024). The analyst must confirm that range or edit and confirm it at the plan gate before research runs. Unspecified years also require confirmation of the proposed default.

### Units and precision

- XBRL values are in base USD; the note shows amounts in **$ millions to one decimal** and margins and changes to **two decimals**.
- Ratios and changes are calculated from the unrounded facts; rounded display values are never reused in a calculation.
- A figure quoted from a filing must appear in the cited passage **with the same unit**: "$2.2 billion" must appear as 2.2 billion, and a bare 2.2 or 2.2 thousand does not count ([checks.py](../../analystdesk/governance/checks.py)).
- No currency conversion: all covered companies report in USD.

### Filing versions

- **Default mode selects the earliest matching cached presentation.** Cached annual 10-K and 10-K/A versions are exposed, but the app has not independently established which is authoritative, whether an earlier filing is subject to non-reliance, or whether the cited commentary uses the same presentation. Do not equate earliest with verified original.
- **Later differing values are flagged, not automatically selected.** A difference alone does not establish a restatement or its cause. A follow-up note describes it as a later presentation, not a business change.
- A same-year difference between filings is a version change, not growth, and is not assumed to be an error correction.

#### Optional reviewed annual-source register

For a reviewed corpus, set `SOURCE_REVIEW_FILE` to an independently maintained JSON file. When configured, only annual XBRL facts with matching **eligible** records are returned; excluded and unreviewed facts are unavailable, including through exact fact lookup and the versions list. If multiple versions are eligible, the earliest is selected; to use a corrected version instead, the reviewer must mark the earlier affected presentation excluded. Revenue and income each need their own matching eligible record. The selected record and its review metadata are returned by the financial tool and included in the live C1/C2 approval snapshot. Changing the register invalidates an in-progress review.

The register is strict JSON with `{"version": 1, "decisions": [...]}`. Each decision has the following fields (this example is synthetic and **is not issuer evidence**):

```json
{
  "ticker": "MSFT", "fiscal_year": 2023,
  "concept": "OperatingIncomeLoss", "accession": "0000789019-23-000001",
  "period_start": "2022-07-01", "period_end": "2023-06-30",
  "filed": "2023-07-27", "form": "10-K", "value_usd": 123,
  "decision": "excluded", "reviewer": "example reviewer",
  "reviewed_at": "2024-01-15", "evidence": "reference to independently reviewed issuer evidence",
  "rationale": "example only"
}
```

Decisions must match the ticker, concept, year, accession, annual period, filing date, form and exact USD value in the cache. Dates use `YYYY-MM-DD`; duplicate or malformed records, a missing configured file or a mismatched reviewed record stop the operation. For Compose, place the reviewed file in the existing read-only `data/edgar_cache` mount and set `SOURCE_REVIEW_FILE=/app/data/edgar_cache/source_reviews.json` in the Compose environment. The app and EDGAR service receive the same setting. An unset or empty variable leaves the historical demo mode active: facts are **unverified**, not approved by default. Quarterly charts are unavailable when the annual-only register is enforced.

Annual margins and margin changes are withheld unless each income/revenue pair has the same complete period and filing accession. This conservative rule also applies without a register; eligible facts from different filings are not automatically treated as one presentation.

This mechanism enforces the supplied decisions; it does not authenticate the reviewer, inspect the referenced issuer evidence, validate excerpts quoted by the model, or establish that a statement is reliable. Protect and independently review the register and its source documents. It is not a historical as-of selector: as-of requests remain unsupported. No real review decisions are supplied by this project.

## 5. Evidence and risk-change rules

| Claim | Support required | How the app checks it |
|---|---|---|
| Reported figure | XBRL fact or cited table cell | Code renders the figure from a placeholder and checks it against the fact |
| Derived figure | Its source facts and an executed formula | Code recomputes every `[calc]`, `[growth]` and `[diff]` tag |
| Quoted number | The passage cited on the same line contains it, with its unit | Code |
| Narrative claim | A passage supporting the exact company, period and degree of certainty | Live C1 and C2: a judge checks cited claims; missing review blocks approval |
| Business explanation | Evidence for the explanation itself; management's view attributed to management | Writer prompt; the analyst at the note gate |
| Risk change | Adequate evidence for both years | C2 records requested year pairs as missing evidence or excerpt-only; passage-level claims require review and whole-section conclusions are not established by excerpts |

**Risk-change labels.** *Added*: in the later year and absent from the comparable earlier coverage. *Removed*: the reverse; it means removed from the disclosure, not that the risk ceased. *Changed*: in both years with a meaningful difference. Changed wording is evidence of a disclosure difference, not that an economic risk is new or worse. A failed search for the earlier year does not show the risk was absent; with no comparable earlier evidence, the change cannot be classified.

**Causes.** Correct arithmetic establishes a movement, not its cause. "Revenue grew 12.50%" can be verified; "because prices rose" needs its own source, or must be presented as management's explanation or left out.

**Retrieved text is data.** Filing passages and tool results are passed to the model as evidence, never as instructions. A passage that contains instructions aimed at the model is withheld from it, and advice wording in a note fails the checks, so an injected "buy this stock" cannot reach a signable note ([threat_model.md](threat_model.md)).

## 6. Acceptance and publication

1. **Plan gate.** The analyst approves, edits or cancels the plan. Approving the plan authorises the research, not the result.
2. **Checks.** Code checks the title and body. Live C1 and C2 also review cited lines, including titles, headings and table rows; the judge receives cited XBRL fact identities and periods as well as passage text. Uncited text outside exact structural headings and code-generated suffixes blocks approval. Missing evidence, invalid verdicts and unavailable review also block approval. The conservative rule may reject harmless labels or numeric-only claims; it is not proof of semantic correctness. Issues go back to the writer for **at most two automated revisions**.
3. **Note gate.** The analyst sees the full note and the check result. A note with remaining issues **cannot be approved** (the button is disabled, the API returns 409 and the graph refuses it): the analyst edits it, which re-runs the checks, or rejects it. An edited note must be approved again.
4. **Exact-note approval.** Live C1/C2 reviews capture cited fact records, passage text hashes, available source-file hashes, checking-policy file hashes and effective judge settings. The graph rechecks the snapshot before signing and before invoking publication; changes or missing snapshots require a fresh run. The signed context contains the snapshot, request, plan and check result, and the portal validates its shape and note hash ([approval.py](../../analystdesk/governance/approval.py)). Legacy tokens remain accepted for compatibility and do not provide this protection. This controlled-demo mechanism is not an atomic cross-service evidence lock: caches can predate capture, sources can change after the final check, and the portal does not independently reload the application's evidence. It does not establish source eligibility or identity.
5. **Publication.** The portal verifies the signature itself before writing and refuses a second copy of the same note (`ALREADY_EXISTS`). Only a confirmed publication is written to memory.

A 98% verified-number share is a monitoring alert threshold (`VerifiedShareBelow98`), not permission to publish known errors.

## 7. Memory and privacy

The rules for what is remembered, who reads it, memory off, and correction and deletion are in [memory_policy.md](memory_policy.md#privacy-and-access).

## 8. Analyst-facing messages

The specification defines short status messages for each situation. These are the ones the app shows today:

| Situation | Message in the app |
|---|---|
| Company or year outside coverage | ⛔ Out of scope, with the reason and the covered tickers or years |
| Investment-advice request or wording | "Requests for investment advice (buy/sell/price targets) are out of scope" / "Investment-advice wording … is not allowed in a research note" |
| Number without a source, or wrong | The check panel lists each issue, e.g. "Number '$46.2 billion' has no source" or "44.10% is wrong: … = 44.64%" |
| Judge unavailable (C1/C2) | Incomplete review is shown with the check result and approval is blocked |
| Waiting for a decision | "⏸ Waiting for you: approve, edit or reject the note" |
| Note failed its checks | "⛔ Note failed verification. Edit and re-check it, or reject it. Approval is blocked." |
| Request carries instructions to the system | "The request contains instructions aimed at the system rather than a research question." |
| How the request was read | Plan gate: "How your request was read", e.g. "“last three years” is read as FY2022–FY2024…" or "JPM is a bank: margins are pre-tax margin" |
| Private watchlist | A tool call naming a watchlist company outside the plan is refused (`WATCHLIST_PRIVATE`); a note naming one fails its checks |
| Published / rejected / cancelled | "✅ Published", with the note id; "🛑 Rejected by the analyst"; "🚫 Plan cancelled" |
| Publication refused | The team board shows "❌ refused" (invalid signature, or the note is already published), and the run ends as `publish_failed` |
| Memory used | The plan step shows "🧠 memory used: 1 preference(s); previous notes on MSFT"; with memory off it shows nothing, because nothing was read |
| No previous note | "There is no previous note in memory to compare against." |
| Lesson proposed | Lessons wait under "Pending your review"; none is used until the analyst approves it |
| Monitoring | 🚨 Monitoring alerts panel: active Prometheus alerts, or "Monitoring is unavailable" when Prometheus cannot be reached |

## 9. Where the app differs from the specification

The specification sets a higher bar than the app meets in some places. These are the known differences, kept visible rather than hidden:

| Specification | The app today |
|---|---|
| A typed coverage record for each risk comparison | The risk specialist labels each point Added / Removed / Changed / Unchanged / Insufficient evidence with passages from both years, and code adds a Limitations line when one year's Item 1A evidence is missing; there is no per-section coverage record |
| Every substantive claim is reviewed | Live C1/C2 use a conservative line inventory with fail-closed missing citations and verdicts. Exact structural headings and the unchanged code-generated suffix are exempt; automated semantic quality and financial claim associations still need independent validation |
| Calendar-period requests and filing as-of cutoffs handled explicitly | Detected explicit calendar and as-of requests are declined instead of silently treated as fiscal years; the annual note workflow also declines explicit quarterly requests. Detection is pattern-based and does not implement calendar conversion or as-of filing selection |
| Filing versions, amendments and non-reliance | Cached annual XBRL presentations, including amendments and their accessions, are exposed by the financials tool. Selection still uses the earliest matching cached filing, not an independently reviewed authoritative version. Eligibility and non-reliance are unverified and disclosed at the note gate |
| Verified reviewer identity, per-analyst access and audiences | The approver and analyst are typed names, not verified identities. Preferences, coverage and the watchlist are kept per analyst name; past-note memory and published notes are shared by everyone using the app |
| Corrections, supersession and withdrawal of published notes | Original records are retained; withdrawal hides a note and supersession links it to a newly reviewed replacement. See [memory policy](memory_policy.md). An unconfirmed save remains unknown and is reconciled by hand |
| Retention periods per record type | No automatic expiry; memory stays until it is deleted |

None of these affects the guarantee that every number in a published note was checked against its source before the analyst saw it.
