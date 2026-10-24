# SEC source coverage

The declared scope is [coverage_scope.json](coverage_scope.json): FY2023–2025 for twelve companies, split equally across two sectors.

| Sector | Companies |
|---|---|
| Technology | Microsoft (MSFT), Apple (AAPL), Alphabet (GOOGL), Oracle (ORCL), Adobe (ADBE), Salesforce (CRM) |
| Healthcare | AbbVie (ABBV), Amgen (AMGN), Gilead Sciences (GILD), Abbott (ABT), UnitedHealth (UNH), Thermo Fisher (TMO) |

The complete scope requires **36 company-years, 72 canonical financial facts and 72 section groups**: revenue, operating income, Item 1A and Item 7 for each company/year. Passage counts depend on the supplied cache; the importer retains every selected section chunk.

The current snapshot contains **72 financial inputs and 4,073 filing passages**. Its cached-source checks are recorded in [source_coverage_verification.json](../evidence/source_coverage_verification.json).

## Retrieval artifacts for this snapshot

[retrieval_config.json](retrieval_config.json) pins the public MiniLM embedding model, cross-encoder reranker, exact revisions and file checksums. It also fixes table handling, token-window policies, query decomposition and fusion limits. The [retrieval setup guide](../docs/HYBRID_RETRIEVAL.md) explains public model acquisition and offline preparation.

After importing the source snapshot and obtaining those public cached models, prepare the index:

```sh
python ops/prepare_retrieval.py \
  --corpus .runtime/journey/sources/corpus.json \
  --model-cache "$HOME/.cache/huggingface/hub" \
  --output .runtime/journey/retrieval
```

The generated bundle binds 4,073 passage IDs and their retrieval-text hashes to the source/configuration fingerprints and 384-dimensional normalized vectors. It includes only the allowlisted public model files, not the whole user cache. Source text and retained table cells form the same searchable representation in BM25, hybrid and reranked arms; original citation records remain unchanged.

The bundle remains outside Git and is mounted read-only into the filing service. Compose startup explicitly populates the internal Chroma collection from the frozen vectors before research search starts. Runtime search verifies source, collection and model/index identity and fails when the selected learned mode is unavailable. Stored float32 vectors are compared with an absolute `1e-7` tolerance and zero relative tolerance for numerical roundoff. Source or retrieval configuration changes require a matching newly prepared bundle and collection. The host-only exact NumPy backend supports reproducible development comparisons; it is identified separately from Chroma in retrieval metadata.

The [36-query development comparison](../evaluation/retrieval/README.md) uses four declared development companies and partial source-derived labels. It does not replace independent human relevance review or the protected final evaluation.

The [deployed Chroma/MCP verification](../evidence/retrieval_deployed_verification.json) completed all 36 frozen development queries without errors through 37 authenticated tool calls. It reproduced 98.61% sampled-label Recall@5 and 100.00% Hit@5 using local model inference, with no generative-model calls, new research runs or notes. All 36 top-five passage orders matched the host comparison.

The [final runtime check](../evidence/retrieval_deployment_runtime.json) passed all twelve company tool paths, 36 margin calculations with 108 verified values and 72 section groups. Chroma and filing-service restart reused 4,073 vectors and preserved representative search results, existing runs, spending records and all three saved notes. The complete verification records 780 local tests and 19 runtime checks passing. Independent human relevance review remains pending.

## Prepare the source snapshot

Supply a public SEC corpus with `metadata`, `companies`, `facts` and `passages`:

```sh
python ops/prepare_sources.py --source-corpus /path/to/public-sec-corpus.json
```

The default imports all twelve companies. To reproduce a two-company scope explicitly:

```sh
python ops/prepare_sources.py --source-corpus /path/to/public-sec-corpus.json --tickers MSFT AAPL
```

The snapshot is installed at `.runtime/journey/sources/corpus.json`; the shareable inventory is [source_manifest.json](source_manifest.json). `--output` and `--manifest` select alternative destinations. Stop source-reading services before replacing their snapshot, then restart them together so they load the same fingerprint. Preserve old snapshot bytes when retaining earlier run checkpoints.

## Input fields and validation

| Record | Required content |
|---|---|
| Company | Declared ticker, company name, sector and ten-digit SEC CIK. |
| Fact | Unique ID, ticker, fiscal year, canonical concept, original XBRL concept, unscaled USD value, annual start/end, accession, filing date, form `10-K`, original SEC filing URL and source kind. |
| Passage | Unique ID, ticker, company, fiscal year, Item `1A` or `7`, text, accession, filing date, original SEC filing URL and source kind. Existing table records are preserved. |

The importer rejects missing or duplicate financial cells, incompatible annual periods, nonfinite values, wrong company/sector identities, synthetic datasets and URLs that disagree with the issuer CIK or accession. Every company/year must have both cached section groups. All data is validated and staged before replacement; installation failure restores the prior snapshot.

The manifest records scope/source hashes, canonical fact identities and section chunk counts. Raw filings, source-cache bodies and runtime databases remain outside Git. Automated structural checks do not establish correct original Item boundaries, complete table extraction or the economic interpretation of risks; those need source/domain review. A fresh clone needs a supplied source cache before Docker startup.

SEC provides submissions and XBRL JSON through its [official data APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). Source collection should follow the [SEC access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) and reuse cached responses.

## Check the original cached SEC responses

[sec_cache_manifest.json](sec_cache_manifest.json) pins the public URL and response-body hash of each required SEC response. It includes the historical submissions index needed for the older Salesforce accession. Supply the matching cached response wrappers locally:

```sh
python ops/verify_source_coverage.py \
  --corpus .runtime/journey/sources/corpus.json \
  --source-manifest data/sec_cache_manifest.json \
  --cache-dir /path/to/sec-cache \
  --output evidence/source_coverage_verification.json
```

This read-only check matches every financial input to its original cached XBRL concept, amount, currency, period, accession, form and filing date. It verifies annual filing identities through recent or issuer-declared historical submissions and hashes all 61 required response bodies. It makes no network or model requests. Passage checks establish source identity; they do not independently reconstruct the original HTML sections or validate economic risk interpretations.

## Verify the deployed tools

After starting the live Compose stack, run the operator check inside its app container:

```sh
docker --context desktop-linux compose --project-name analyst-desk-journey \
  --env-file .runtime/journey/credentials.env -f compose.yaml -f compose.live.yaml \
  exec -T app python ops/verify_catalogue_tools.py
```

It checks all twelve search scopes, 36 isolated margin calculations and 72 cached section groups against the loaded snapshot. It creates no research run or note and makes no model requests. In the research UI, choose companies and fiscal years explicitly. The catalogue contains twelve companies; individual requests remain bounded to four, or two for live three-year risk comparisons. A source change requires a new plan before approval; earlier saved notes remain available.
