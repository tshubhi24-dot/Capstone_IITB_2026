# Analyst Desk: missing features and proposed extensions

This file records work for later consideration. Listing a feature here does not
implement it or change the research application's behaviour.

## MF-001 — Add a new SEC company and refresh cached coverage

**Status:** proposed; not implemented.

**Priority:** optional product expansion. Unrestricted company entry is not an
explicit capstone minimum.

### Current behaviour

The web app lists companies and fiscal years from its prepared SEC source
snapshot. Research requests can use only that catalogue. The current baseline
covers twelve companies, two sectors and FY2023–2025. Entering an issuer outside
the catalogue does not trigger a new SEC download. The existing source importer
accepts prepared inputs; it does not download filings from SEC.

### Relationship to the capstone brief

The Analyst Desk brief, printed page 16, requires coverage of 10–15 companies in
two sectors over three years each. Printed pages 15–16 describe SEC/EDGAR data
access and cached filing/section/XBRL tools. They do not explicitly require an
arbitrary-company input field or automatic ingestion during a research request.

The twelve-company catalogue meets the stated coverage range. This does not by
itself prove source completeness, correct original Item boundaries, preserved
tables or all EDGAR-tool capabilities; those need separate verification.

### Proposed behaviour

An analyst can request a ticker or SEC CIK that is outside the current catalogue.
The application resolves the issuer, shows the available annual filings and
fiscal years, and provides an explicit onboarding action. Preparation downloads
and caches public SEC evidence, validates source coverage and builds the search
index before the company becomes available for research.

### Proposed implementation sequence

1. Resolve the ticker/CIK and display issuer identity and annual-filing coverage.
2. Fetch/cache SEC filings and XBRL facts with an identifying contact User-Agent,
   controlled request rate and bounded retry/backoff.
3. Preserve original Item boundaries and tables; normalize fiscal periods,
   concepts and units; retain accession IDs, source URLs and provenance.
4. Report missing/incomplete sources explicitly and require successful source
   checks before activating coverage.
5. Build matching lexical/vector indexes and reranking inputs.
6. Activate a versioned source snapshot and refresh the web catalogue. Research
   then uses that prepared snapshot through the usual plan-review workflow.

### Completion evidence

- A previously unsupported company appears with its actual available years.
- Retrieved passages, tables and financial inputs resolve to the correct issuer,
  accession, fiscal period and original source.
- A repeated preparation uses the cache; SEC request identification and rate
  controls can be demonstrated.
- Incomplete evidence is visible and does not become an apparently complete
  research result.
- Existing approved plans remain tied to their original source snapshot.
- Frozen evaluation data is preserved; onboarding does not silently change a
  held-out benchmark or an already approved run.

### Relevant existing files

- `web/index.html` and `web/app.js`: company/year selection.
- `desk/api.py`: source catalogue and research-request entry point.
- `desk/workflow.py`: source-scope validation and checkpoint identity.
- `desk/data.py` and the source-import preparation tools: source loading.
- `README.md` and `data/README.md`: installation and source preparation.

No company-onboarding implementation accompanies this entry.
