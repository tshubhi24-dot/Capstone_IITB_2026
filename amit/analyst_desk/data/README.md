# Source data for the first journey

The current implementation accepts a reviewed public SEC snapshot as JSON with four keys: `metadata`, `companies`, `facts`, and `passages`.

- Companies contain `ticker`, company/name, sector and optional CIK.
- Facts contain `id`, `ticker`, `fiscal_year`, `concept` (`revenue` or `operating_income`), original `xbrl_concept`, unscaled `value`, `unit`, annual `start`/`end`, `accession`, filing date and original SEC `source_url`.
- Passages contain `id`, `ticker`, `year`, `item` (`1A` or `7`), `text`, source URL/accession and retained table records where available. Preserve every section chunk, not just retrieved excerpts.

Prepare the current two-company subset:

```sh
python ops/prepare_sources.py --source-corpus /absolute/path/to/reviewed-sec-corpus.json
```

This writes a new local snapshot under `.runtime/journey/sources/` and a public source-identity manifest. The local source snapshot, raw filings and databases are excluded from Git. The shared manifest records the twelve annual facts and provenance hashes so the team can check source selection; it is not an independent domain-review receipt.

For this Mac's first journey, data is extracted from the already available public SEC cache. No older application code, test results or provider credentials are imported. Integration with the team's ingestion output is a later adapter task; the startup script fails clearly if the reviewed snapshot is absent. A fresh clone therefore needs this source-preparation step before starting Docker.
