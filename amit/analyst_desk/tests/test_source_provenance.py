"""Cached SEC provenance checks with invented public-source-shaped fixtures."""
from copy import deepcopy
import hashlib
import json

import pytest

from ops import verify_source_coverage


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def provenance_sources(tmp_path):
    scope = json.loads((verify_source_coverage.ROOT / "data/coverage_scope.json").read_bytes())
    cache = tmp_path / "cache"
    cache.mkdir()
    origin = digest(b"invented original corpus for provenance tests")
    corpus = {"metadata": {"origin_corpus_sha256": origin}, "companies": deepcopy(scope["companies"]),
              "facts": [], "passages": []}
    manifest = {"corpus_sha256": origin, "sources": [], "source_count": 0,
                "unrelated_input_metadata": "must not appear in output"}

    def cache_body(url, body):
        body_string = json.dumps(body) if isinstance(body, dict) else body
        filename = digest(url.encode()) + ".json"
        (cache / filename).write_text(json.dumps({"url": url, "body": body_string,
                                                "unrelated_wrapper_metadata": "must not appear in output"}))
        manifest["sources"].append({"url": url, "body_sha256": digest(body_string.encode()), "cache_file": filename})

    for company in scope["companies"]:
        cik = int(company["cik"])
        companyfacts = {"cik": cik, "facts": {"us-gaap": {
            "Revenues": {"units": {"USD": []}}, "OperatingIncomeLoss": {"units": {"USD": []}}}}}
        submissions = {"cik": company["cik"], "filings": {"recent": {key: [] for key in
                       ("accessionNumber", "filingDate", "reportDate", "form", "primaryDocument")}}}
        for year in (2023, 2024, 2025):
            accession = f"{company['cik']}-{str(year + 1)[-2:]}-000001"
            filing_date, start, end = f"{year + 1}-02-15", f"{year}-01-01", f"{year}-12-31"
            filename = f"test-only-{year}.htm"
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{filename}"
            common = {"ticker": company["ticker"], "company": company["company"], "accession": accession,
                      "filed": filing_date, "source_url": filing_url, "source_kind": "sec_edgar"}
            for concept, xbrl, value in (("revenue", "Revenues", 1000), ("operating_income", "OperatingIncomeLoss", 100)):
                corpus["facts"].append({**common, "id": f"{company['ticker']}:{year}:{concept}",
                                        "sector": company["sector"], "fiscal_year": year, "concept": concept,
                                        "xbrl_concept": f"us-gaap:{xbrl}", "value": value,
                                        "unit": "USD", "start": start, "end": end, "form": "10-K"})
                companyfacts["facts"]["us-gaap"][xbrl]["units"]["USD"].append({"val": value, "start": start, "end": end,
                        "accn": accession, "form": "10-K", "filed": filing_date})
            for item in ("1A", "7"):
                for index in range(2):
                    corpus["passages"].append({**common, "id": f"{company['ticker']}:{year}:{item}:{index}",
                                                "year": year, "item": item, "text": "Invented section text for a test."})
            for key, value in (("accessionNumber", accession), ("filingDate", filing_date), ("reportDate", end),
                               ("form", "10-K"), ("primaryDocument", filename)):
                submissions["filings"]["recent"][key].append(value)
            cache_body(filing_url, f"<html>Invented annual filing for {company['ticker']}, {year}.</html>")
        cache_body(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", companyfacts)
        cache_body(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", submissions)
    manifest["source_count"] = len(manifest["sources"])
    corpus_path, manifest_path = tmp_path / "corpus.json", tmp_path / "source-manifest.json"

    def persist():
        corpus_path.write_text(json.dumps(corpus))
        manifest_path.write_text(json.dumps(manifest))

    persist()
    return {"corpus": corpus, "manifest": manifest, "cache": cache, "corpus_path": corpus_path,
            "manifest_path": manifest_path, "persist": persist}


def check(source):
    source["persist"]()
    return verify_source_coverage.verify(source["corpus_path"], source["manifest_path"], source["cache"])


def edit_cached_body(source, fragment, mutate, *, rehash=True):
    entry = next(row for row in source["manifest"]["sources"] if fragment in row["url"])
    path = source["cache"] / entry["cache_file"]
    wrapper = json.loads(path.read_text())
    body = json.loads(wrapper["body"])
    mutate(body)
    wrapper["body"] = json.dumps(body)
    path.write_text(json.dumps(wrapper))
    if rehash:
        entry["body_sha256"] = digest(wrapper["body"].encode())


def test_verifies_seventy_two_exact_cached_financial_memberships_without_mutating_sources(provenance_sources):
    source = provenance_sources
    before = {path: path.read_bytes() for path in source["cache"].iterdir()}
    receipt = check(source)
    assert receipt["status"] == "passed"
    assert receipt["company_count"] == 12 and receipt["company_year_count"] == 36
    assert receipt["companyfacts_memberships_checked"] == 72 and receipt["submissions_accessions_checked"] == 36
    assert receipt["cached_source_count"] == 60 and receipt["section_group_count"] == 72
    assert receipt["fact_count"] == 72 and receipt["passage_count"] == 144
    assert receipt["network_requests"] == receipt["model_calls"] == 0
    assert len(receipt["cells"]) == 36 and len(receipt["sources"]) == 60
    assert all(cell["fact_count"] == cell["companyfacts_memberships_checked"] == 2
               and cell["item_1a_chunk_count"] == cell["item_7_chunk_count"] == 2 for cell in receipt["cells"])
    assert receipt["review_limits"]["original_item_boundaries"] == "independent_domain_review_pending"
    assert receipt["snapshot_sha256"] == digest(source["corpus_path"].read_bytes())
    assert {path: path.read_bytes() for path in source["cache"].iterdir()} == before
    serialized = json.dumps(receipt)
    assert str(source["cache"]) not in serialized
    assert "cache_file" not in serialized and "unrelated_" not in serialized


def test_rejects_cached_body_tamper_even_if_wrapper_remains_valid(provenance_sources):
    edit_cached_body(provenance_sources, "companyfacts/", lambda body: body.update(cik=1), rehash=False)
    with pytest.raises(ValueError, match="body hash"):
        check(provenance_sources)


def test_rejects_tampered_normalized_financial_value(provenance_sources):
    provenance_sources["corpus"]["facts"][0]["value"] = 1001
    with pytest.raises(ValueError, match="absent from cached SEC companyfacts"):
        check(provenance_sources)


def test_rejects_missing_cached_response(provenance_sources):
    entry = provenance_sources["manifest"]["sources"][0]
    (provenance_sources["cache"] / entry["cache_file"]).unlink()
    with pytest.raises(ValueError, match="missing"):
        check(provenance_sources)


@pytest.mark.parametrize("fragment", ["companyfacts/", "submissions/"])
def test_rejects_wrong_issuer_even_with_recomputed_cache_hash(provenance_sources, fragment):
    edit_cached_body(provenance_sources, fragment, lambda body: body.update(cik=1))
    with pytest.raises(ValueError, match="wrong issuer CIK"):
        check(provenance_sources)


def test_rejects_accession_absent_from_cached_submissions(provenance_sources):
    def mutate(body):
        body["filings"]["recent"]["accessionNumber"][0] = "0000000001-24-000001"
    edit_cached_body(provenance_sources, "submissions/", mutate)
    with pytest.raises(ValueError, match="accession is not unique"):
        check(provenance_sources)


@pytest.mark.parametrize("field,value", [("accn", "0000000001-24-000001"), ("form", "10-Q"),
                                         ("start", "2023-02-01"), ("end", "2023-12-30"), ("filed", "2024-02-16")])
def test_exact_companyfact_membership_checks_all_annual_filing_fields(provenance_sources, field, value):
    def mutate(body):
        body["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0][field] = value
    edit_cached_body(provenance_sources, "companyfacts/", mutate)
    with pytest.raises(ValueError, match="absent from cached SEC companyfacts"):
        check(provenance_sources)


def test_rejects_issuer_url_on_normalized_passage(provenance_sources):
    row = provenance_sources["corpus"]["passages"][0]
    row["source_url"] = row["source_url"].replace("/789019/", "/320193/")
    with pytest.raises(ValueError, match="passage source identity"):
        check(provenance_sources)


def test_rejects_missing_section_even_when_financial_facts_are_valid(provenance_sources):
    rows = provenance_sources["corpus"]["passages"]
    provenance_sources["corpus"]["passages"] = [row for row in rows if not
              (row["ticker"] == "MSFT" and row["year"] == 2023 and row["item"] == "7")]
    with pytest.raises(ValueError, match="Item 1A and Item 7"):
        check(provenance_sources)


def test_rejects_extra_duplicate_concept_with_distinct_identifier(provenance_sources):
    row = {**provenance_sources["corpus"]["facts"][0], "id": "invented-duplicate-revenue"}
    provenance_sources["corpus"]["facts"].append(row)
    with pytest.raises(ValueError, match="exactly two canonical annual facts"):
        check(provenance_sources)


def test_rejects_wrong_origin_manifest(provenance_sources):
    provenance_sources["corpus"]["metadata"]["origin_corpus_sha256"] = digest(b"different original cache")
    with pytest.raises(ValueError, match="origin hash"):
        check(provenance_sources)


def test_rejects_cache_wrapper_url_substitution(provenance_sources):
    entry = provenance_sources["manifest"]["sources"][0]
    path = provenance_sources["cache"] / entry["cache_file"]
    wrapper = json.loads(path.read_text())
    wrapper["url"] = "https://example.invalid/test-only"
    path.write_text(json.dumps(wrapper))
    with pytest.raises(ValueError, match="wrapper URL"):
        check(provenance_sources)


def test_rejects_manifest_path_traversal(provenance_sources):
    provenance_sources["manifest"]["sources"][0]["cache_file"] = "../outside-test-only.json"
    with pytest.raises(ValueError, match="filename must be the hash"):
        check(provenance_sources)


def test_rejects_duplicate_public_source_entries(provenance_sources):
    manifest = provenance_sources["manifest"]
    manifest["sources"].append(deepcopy(manifest["sources"][0]))
    manifest["source_count"] += 1
    with pytest.raises(ValueError, match="duplicate source URLs"):
        check(provenance_sources)


def test_rejects_companyfacts_currency_substitution(provenance_sources):
    def mutate(body):
        units = body["facts"]["us-gaap"]["Revenues"]["units"]
        units["EUR"] = units.pop("USD")
    edit_cached_body(provenance_sources, "companyfacts/", mutate)
    with pytest.raises(ValueError, match="absent from cached SEC companyfacts"):
        check(provenance_sources)


def add_historical_crm_index(source):
    """Move CRM's oldest filing to SEC's top-level historical-array shape."""
    main_url = "https://data.sec.gov/submissions/CIK0001108524.json"
    name = "CIK0001108524-submissions-001.json"
    historical_url = "https://data.sec.gov/submissions/" + name
    historical_body = {}

    def move(body):
        recent = body["filings"]["recent"]
        for key, values in recent.items():
            historical_body[key] = [values.pop(0)]
        filed = historical_body["filingDate"][0]
        body["filings"]["files"] = [{"name": name, "filingCount": 1, "filingFrom": filed, "filingTo": filed}]

    edit_cached_body(source, main_url, move)
    body = json.dumps(historical_body)
    filename = digest(historical_url.encode()) + ".json"
    (source["cache"] / filename).write_text(json.dumps({"url": historical_url, "body": body}))
    entry = {"url": historical_url, "body_sha256": digest(body.encode()), "cache_file": filename}
    source["manifest"]["sources"].append(entry)
    source["manifest"]["source_count"] += 1
    return entry


def test_resolves_issuer_declared_historical_submission_arrays(provenance_sources):
    historical = add_historical_crm_index(provenance_sources)
    receipt = check(provenance_sources)
    assert receipt["status"] == "passed" and receipt["cached_source_count"] == 61
    assert receipt["historical_submissions_source_count"] == 1
    assert receipt["historical_submissions_accessions_checked"] == 1
    assert receipt["submissions_accessions_checked"] == 36
    cell = next(cell for cell in receipt["cells"] if cell["ticker"] == "CRM" and cell["fiscal_year"] == 2023)
    assert cell["submissions_index_url"] == historical["url"]
    history_sources = [row for row in receipt["sources"] if row["kind"] == "historical_submissions"]
    assert history_sources == [{"kind": "historical_submissions", "url": historical["url"], "body_sha256": historical["body_sha256"]}]


def test_historical_index_requires_parent_submissions_declaration(provenance_sources):
    add_historical_crm_index(provenance_sources)
    edit_cached_body(provenance_sources, "submissions/CIK0001108524.json",
                     lambda body: body["filings"].pop("files"))
    with pytest.raises(ValueError, match="accession is not unique"):
        check(provenance_sources)


def test_historical_index_name_must_match_issuer_cik(provenance_sources):
    add_historical_crm_index(provenance_sources)
    def mutate(body):
        body["filings"]["files"][0]["name"] = "CIK0000320193-submissions-001.json"
    edit_cached_body(provenance_sources, "submissions/CIK0001108524.json", mutate)
    with pytest.raises(ValueError, match="index name does not match the issuer CIK"):
        check(provenance_sources)


def test_historical_index_requires_pinned_public_manifest_entry(provenance_sources):
    historical = add_historical_crm_index(provenance_sources)
    provenance_sources["manifest"]["sources"].remove(historical)
    provenance_sources["manifest"]["source_count"] -= 1
    with pytest.raises(ValueError, match="missing a required historical submissions index"):
        check(provenance_sources)


def test_historical_index_requires_cached_body(provenance_sources):
    historical = add_historical_crm_index(provenance_sources)
    (provenance_sources["cache"] / historical["cache_file"]).unlink()
    with pytest.raises(ValueError, match="missing"):
        check(provenance_sources)


def test_historical_index_body_hash_is_verified(provenance_sources):
    add_historical_crm_index(provenance_sources)
    edit_cached_body(provenance_sources, "CIK0001108524-submissions-001.json", lambda body: body.update(cik=1), rehash=False)
    with pytest.raises(ValueError, match="body hash"):
        check(provenance_sources)


def test_historical_index_rejects_explicit_wrong_cik(provenance_sources):
    add_historical_crm_index(provenance_sources)
    edit_cached_body(provenance_sources, "CIK0001108524-submissions-001.json", lambda body: body.update(cik=1))
    with pytest.raises(ValueError, match="wrong issuer CIK"):
        check(provenance_sources)


def test_historical_index_date_range_must_include_canonical_filing_date(provenance_sources):
    add_historical_crm_index(provenance_sources)
    def mutate(body):
        entry = body["filings"]["files"][0]
        entry["filingFrom"], entry["filingTo"] = "2020-01-01", "2020-12-31"
    edit_cached_body(provenance_sources, "submissions/CIK0001108524.json", mutate)
    with pytest.raises(ValueError, match="accession is not unique"):
        check(provenance_sources)


def test_historical_index_count_must_match_declared_count(provenance_sources):
    add_historical_crm_index(provenance_sources)
    def mutate(body):
        body["filings"]["files"][0]["filingCount"] = 2
    edit_cached_body(provenance_sources, "submissions/CIK0001108524.json", mutate)
    with pytest.raises(ValueError, match="index count differs from its declaration"):
        check(provenance_sources)


def test_historical_index_requires_exact_accession(provenance_sources):
    add_historical_crm_index(provenance_sources)
    def mutate(body):
        body["accessionNumber"][0] = "0001108524-24-999999"
    edit_cached_body(provenance_sources, "CIK0001108524-submissions-001.json", mutate)
    with pytest.raises(ValueError, match="accession is not unique"):
        check(provenance_sources)


def test_historical_index_rejects_incompatible_array_lengths(provenance_sources):
    add_historical_crm_index(provenance_sources)
    edit_cached_body(provenance_sources, "CIK0001108524-submissions-001.json", lambda body: body["primaryDocument"].clear())
    with pytest.raises(ValueError, match="incompatible lengths"):
        check(provenance_sources)
