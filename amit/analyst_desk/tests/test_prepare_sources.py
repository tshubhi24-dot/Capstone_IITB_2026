"""Coverage-import boundaries using invented source records, without network I/O."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from desk.data import Corpus
from ops import prepare_sources


@pytest.fixture
def source_document():
    scope = json.loads(prepare_sources.SCOPE_PATH.read_text())
    document = {"metadata": {"unrelated_cache_metadata": "must not be copied"},
                "companies": deepcopy(scope["companies"]), "facts": [], "passages": []}
    for company in scope["companies"]:
        for year in scope["fiscal_years"]:
            accession = f"{company['cik']}-{str(year + 1)[-2:]}-000001"
            url = f"https://www.sec.gov/Archives/edgar/data/{int(company['cik'])}/{accession.replace('-', '')}/test-only.htm"
            common = {"ticker": company["ticker"], "company": company["company"], "accession": accession,
                      "filed": f"{year + 1}-02-15", "source_url": url, "source_kind": "sec_edgar"}
            for concept, value in (("revenue", 1000), ("operating_income", 100)):
                document["facts"].append({**common, "id": f"{company['ticker']}:{year}:{concept}",
                                          "sector": company["sector"], "fiscal_year": year, "concept": concept,
                                          "xbrl_concept": "us-gaap:Revenues" if concept == "revenue" else "us-gaap:OperatingIncomeLoss",
                                          "start": f"{year}-01-01", "end": f"{year}-12-31", "unit": "USD",
                                          "value": value, "form": "10-K"})
            for item in ("1A", "7"):
                for index in range(2):
                    document["passages"].append({**common, "id": f"{company['ticker']}:{year}:{item}:{index}",
                                                 "year": year, "item": item, "text": f"Invented test-only section chunk {index}.",
                                                 "table": [{"column": "Invented test-only retained table"}]})
    return document


@pytest.fixture
def importer(tmp_path, source_document):
    source = tmp_path / "raw.json"
    output = tmp_path / "sources"
    manifest = tmp_path / "public/source_manifest.json"

    def run(document=None, **kwargs):
        source.write_text(json.dumps(document if document is not None else source_document))
        return prepare_sources.prepare(source, output, manifest_path=manifest, **kwargs)

    return run, source, output / "corpus.json", manifest


def test_default_scope_is_twelve_companies_in_two_sectors(importer, source_document):
    run, source, snapshot, manifest_path = importer
    receipt = run()
    assert receipt["company_count"] == 12
    assert receipt["company_year_count"] == 36
    assert receipt["sectors"] == {"Healthcare": 6, "Technology": 6}
    assert receipt["fact_count"] == 72
    assert receipt["section_count"] == 72
    assert receipt["passage_count"] == 144
    assert receipt["years"] == [2023, 2024, 2025]
    manifest = json.loads(manifest_path.read_text())
    assert manifest["origin_corpus_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest["snapshot_sha256"] == hashlib.sha256(snapshot.read_bytes()).hexdigest()
    assert manifest["independent_source_review"] == "pending"
    assert manifest["raw_cache_committed"] is False
    assert all(row["chunk_count"] == 2 and row["snapshot_complete"]
               and not row["original_item_boundaries_reviewed"] for row in manifest["section_inventory"])
    stored = json.loads(snapshot.read_text())
    assert stored["passages"] == source_document["passages"]
    assert stored["facts"] == source_document["facts"]
    assert "unrelated_cache_metadata" not in stored["metadata"]
    assert "prepared_date" not in manifest
    assert run() == receipt
    assert json.loads(manifest_path.read_text()) == manifest
    assert list(snapshot.parent.glob(".prepare-*")) == []


def test_explicit_original_two_company_subset_preserves_all_chunks(importer, source_document):
    run, _, snapshot, manifest_path = importer
    receipt = run(tickers=["MSFT", "AAPL"])
    assert receipt["tickers"] == ["AAPL", "MSFT"]
    assert receipt["company_count"] == 2 and receipt["company_year_count"] == 6
    assert receipt["fact_count"] == 12 and receipt["passage_count"] == 24 and receipt["section_count"] == 12
    corpus = Corpus(snapshot)
    for ticker in receipt["tickers"]:
        for year in receipt["years"]:
            for item in ("1A", "7"):
                expected = [row for row in source_document["passages"] if row["ticker"] == ticker and row["year"] == year and row["item"] == item]
                assert corpus.section(ticker, year, item)["chunks"] == expected
    assert json.loads(manifest_path.read_text())["sectors"] == {"Technology": 2}


@pytest.mark.parametrize("tickers", [[], ["AAPL", "AAPL"], ["UNKNOWN"], ["aapl"]])
def test_rejects_invalid_subset_without_mutation(importer, tickers):
    run, _, snapshot, manifest = importer
    run()
    before = snapshot.read_bytes(), manifest.read_bytes()
    with pytest.raises(ValueError, match="subset"):
        run(tickers=tickers)
    assert (snapshot.read_bytes(), manifest.read_bytes()) == before


def mutate_missing_fact(document):
    document["facts"].pop()


def mutate_duplicate_concept(document):
    document["facts"].append({**document["facts"][0], "id": "duplicate-concept-with-distinct-id"})


def mutate_missing_section(document):
    document["passages"] = [row for row in document["passages"] if not (row["ticker"] == "MSFT" and row["year"] == 2023 and row["item"] == "7")]


def mutate_duplicate_company(document):
    document["companies"].append(deepcopy(document["companies"][0]))


def mutate_duplicate_identifier(document):
    document["passages"][0]["id"] = document["facts"][0]["id"]


def mutate_quarter_pair(document):
    for row in document["facts"][:2]:
        row["start"] = "2023-10-01"


def mutate_nonfinite(document):
    document["facts"][0]["value"] = "NaN"


def mutate_incompatible_pair(document):
    document["facts"][1]["start"] = "2023-01-02"


def mutate_wrong_sector(document):
    document["facts"][0]["sector"] = "Healthcare"


def mutate_wrong_company(document):
    document["companies"][0]["company"] = "Wrong invented identity"


def mutate_wrong_passage_company(document):
    document["passages"][0]["company"] = "Wrong invented identity"


def mutate_wrong_filing_section(document):
    row = document["passages"][0]
    row["accession"] = "0000789019-24-000002"
    row["source_url"] = row["source_url"].replace("000078901924000001", "000078901924000002")


def mutate_empty_chunk(document):
    document["passages"][0]["text"] = "   "


def mutate_string_year(document):
    document["facts"][0]["fiscal_year"] = "2023"


def mutate_bad_form(document):
    document["facts"][0]["form"] = "10-Q"


def mutate_wrong_xbrl_mapping(document):
    document["facts"][0]["xbrl_concept"] = "us-gaap:OperatingIncomeLoss"


def mutate_wrong_fiscal_label(document):
    for row in document["facts"][:2]:
        row["start"], row["end"] = "2022-01-01", "2022-12-31"


def mutate_invalid_decimal(document):
    document["facts"][0]["value"] = "not a decimal"


def mutate_zero_revenue(document):
    document["facts"][0]["value"] = 0


@pytest.mark.parametrize("mutation", [mutate_missing_fact, mutate_duplicate_concept, mutate_missing_section,
                                     mutate_duplicate_company, mutate_duplicate_identifier, mutate_quarter_pair,
                                     mutate_nonfinite, mutate_incompatible_pair, mutate_wrong_sector,
                                     mutate_wrong_company, mutate_wrong_passage_company, mutate_wrong_filing_section,
                                     mutate_empty_chunk, mutate_string_year, mutate_bad_form, mutate_wrong_xbrl_mapping,
                                     mutate_wrong_fiscal_label, mutate_invalid_decimal, mutate_zero_revenue])
def test_invalid_source_never_replaces_existing_snapshot_or_manifest(importer, source_document, mutation):
    run, _, snapshot, manifest = importer
    run()
    before = snapshot.read_bytes(), manifest.read_bytes()
    invalid = deepcopy(source_document)
    mutation(invalid)
    with pytest.raises(ValueError):
        run(invalid)
    assert (snapshot.read_bytes(), manifest.read_bytes()) == before
    assert list(snapshot.parent.glob(".prepare-*")) == []
    assert list(manifest.parent.glob(".prepare-*")) == []


@pytest.mark.parametrize("collection", ["facts", "passages"])
@pytest.mark.parametrize("url", [
    "http://www.sec.gov/Archives/edgar/data/789019/000078901924000001/test-only.htm",
    "https://www.sec.gov.evil.example/Archives/edgar/data/789019/000078901924000001/test-only.htm",
    "https://username:password@www.sec.gov/Archives/edgar/data/789019/000078901924000001/test-only.htm",
    "https://www.sec.gov/Archives/edgar/data/320193/000078901924000001/test-only.htm",
    "https://www.sec.gov/Archives/edgar/data/789019/000078901924000002/test-only.htm",
    "https://www.sec.gov/Archives/edgar/data/789019/000078901924000001/test-only.htm?tracking=unrelated",
])
def test_facts_and_passages_require_original_company_and_accession_sec_urls(importer, source_document, collection, url):
    run, _, snapshot, manifest = importer
    invalid = deepcopy(source_document)
    invalid[collection][0]["source_url"] = url
    with pytest.raises(ValueError, match="SEC filing URLs"):
        run(invalid)
    assert not snapshot.exists() and not manifest.exists()


def test_public_manifest_replace_failure_restores_existing_snapshot(importer, source_document, monkeypatch):
    run, _, snapshot, manifest = importer
    run()
    before = snapshot.read_bytes(), manifest.read_bytes()
    modified = deepcopy(source_document)
    modified["facts"][1]["value"] = 200
    real_replace = prepare_sources.os.replace

    def refuse_manifest(source, destination):
        if Path(destination) == manifest:
            raise OSError("Invented manifest filesystem failure")
        return real_replace(source, destination)

    monkeypatch.setattr(prepare_sources.os, "replace", refuse_manifest)
    with pytest.raises(OSError, match="manifest filesystem failure"):
        run(modified)
    assert (snapshot.read_bytes(), manifest.read_bytes()) == before
    assert list(snapshot.parent.glob(".prepare-*")) == []
    assert list(manifest.parent.glob(".prepare-*")) == []


def test_first_import_manifest_failure_removes_unpublished_snapshot(importer, monkeypatch):
    run, _, snapshot, manifest = importer
    real_replace = prepare_sources.os.replace

    def refuse_manifest(source, destination):
        if Path(destination) == manifest:
            raise OSError("Invented manifest filesystem failure")
        return real_replace(source, destination)

    monkeypatch.setattr(prepare_sources.os, "replace", refuse_manifest)
    with pytest.raises(OSError):
        run()
    assert not snapshot.exists() and not manifest.exists()


def test_public_metadata_and_company_records_are_scope_owned(importer, source_document):
    run, _, snapshot, manifest = importer
    document = deepcopy(source_document)
    document["companies"][0]["unrelated_personal_detail"] = "must not enter artifacts"
    document["facts"][0]["unrelated_personal_detail"] = "must not enter artifacts"
    document["passages"][0]["unrelated_personal_detail"] = "must not enter artifacts"
    run(document)
    assert "unrelated_personal_detail" not in snapshot.read_text()
    assert "unrelated_personal_detail" not in manifest.read_text()


@pytest.mark.parametrize("metadata", [{"synthetic": True}, {"source_kind": "synthetic_demo"}])
def test_rejects_explicit_synthetic_source_without_mutation(importer, source_document, metadata):
    run, _, snapshot, manifest = importer
    run()
    before = (snapshot.read_bytes(), manifest.read_bytes())
    source_document["metadata"] = metadata
    with pytest.raises(ValueError, match="Synthetic or non-SEC"):
        run(source_document)
    assert (snapshot.read_bytes(), manifest.read_bytes()) == before
