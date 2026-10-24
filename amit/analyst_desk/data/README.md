# SEC source coverage

The declared scope is [coverage_scope.json](coverage_scope.json): FY2023–2025 for twelve companies, split equally across two sectors.

| Sector | Companies |
|---|---|
| Technology | Microsoft (MSFT), Apple (AAPL), Alphabet (GOOGL), Oracle (ORCL), Adobe (ADBE), Salesforce (CRM) |
| Healthcare | AbbVie (ABBV), Amgen (AMGN), Gilead Sciences (GILD), Abbott (ABT), UnitedHealth (UNH), Thermo Fisher (TMO) |

The complete scope requires **36 company-years, 72 canonical financial facts and 72 section groups**: revenue, operating income, Item 1A and Item 7 for each company/year. Passage counts depend on the supplied cache; the importer retains every selected section chunk.

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
