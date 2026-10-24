# Public SEC source seed

[public-sec-fy2023-2025.zip](public-sec-fy2023-2025.zip) is the compact normalized public dataset used by this build. It is included in branch `Amit/analyst_desk`, so teammates do not need a separately shared source package. Follow [the installation command](../../README.md#4-install-the-included-public-sec-snapshot) from the Analyst Desk folder.

| Archive member | Purpose |
|---|---|
| `corpus.json` | Exact normalized public SEC company records, canonical financial inputs and cached filing passages. |
| `source_manifest.json` | Byte-identical copy of the tracked [source manifest](../source_manifest.json), binding inventory, origin and normalized snapshot hashes. |

[manifest.json](manifest.json) records the ZIP checksum, each uncompressed file checksum and the fixed coverage counts. The snapshot SHA-256 is `14dd61761199082124b65c5600cd0a0629e636c6e36eec53b110a83ea4a80897`.

The seed covers twelve companies across Technology and Healthcare, FY2023–2025: **36 company-years, 72 canonical financial inputs, 72 Item 1A/7 section groups and 4,073 passages**. Original SEC filing URLs, accessions, fiscal periods and retained table cells remain in the normalized records. The archive is about 1.4 MB; its uncompressed corpus is about 6.4 MB.

This is the existing frozen snapshot, not a fresh SEC fetch. The public [cached-source verification](../../evidence/source_coverage_verification.json) checks its fact/source identities against the separately retained original SEC responses. Those 61 raw response wrappers are not included here. Original Item boundaries, complete table extraction and economic risk interpretation still require independent review. Normalization and structural checks do not establish those conclusions.

Installation verifies the archive and matching tracked manifest, then copies the exact corpus bytes into the ignored `.runtime/journey/sources` folder. It does not feed the normalized seed back through `--source-corpus`, alter origin metadata, create a research run or approve a note. An existing different runtime snapshot must be preserved and reviewed before any replacement.

Only the two public files above belong in the ZIP. Credentials, private runtime databases, analyst preferences, lessons, research notes, approval records, provider settings and model files are excluded. The Docker build excludes this archive; services consume the installed source through the existing read-only mount. Download or prepare the matching retrieval bundle separately as described in [README section 5](../../README.md#5-download-the-two-local-retrieval-models-and-prepare-the-index).

For a deliberate dataset update, use the [source import guide](../README.md#prepare-the-source-snapshot) with original consolidated public inputs. Review and update the normalized snapshot, tracked source manifest, this two-file archive and its checksum inventory together. A changed snapshot requires matching retrieval artifacts and new source-aware verification; preserve old source bytes for retained run checkpoints.
