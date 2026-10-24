"""Read-only provenance checks against public SEC response bodies already cached.

No network, model calls, contact metadata, or previous application code is used.
Successful receipts contain only public source identities, hashes and coverage
counts. Matching cached facts is distinct from independent domain review of
financial comparability and original filing section boundaries.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desk.data import Corpus

YEARS = (2023, 2024, 2025)
CONCEPTS = ("revenue", "operating_income")
ITEMS = ("1A", "7")
TAGS = {
    "revenue": {"us-gaap:Revenues", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"},
    "operating_income": {"us-gaap:OperatingIncomeLoss"},
}


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _scope():
    document = json.loads((ROOT / "data/coverage_scope.json").read_bytes())
    companies = {row["ticker"]: row for row in document["companies"]}
    if (len(companies) != 12 or len(document["companies"]) != 12
            or document["fiscal_years"] != list(YEARS)
            or Counter(row["sector"] for row in companies.values()) != {"Technology": 6, "Healthcare": 6}):
        raise ValueError("Invalid twelve-company verification scope")
    return document["scope_id"], companies


def _cik(value):
    if isinstance(value, bool) or not re.fullmatch(r"\d{1,10}", str(value)):
        raise ValueError("Cached SEC issuer CIK is invalid")
    return int(value)


def _amount(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Financial amount is not decimal-compatible")
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("Financial amount is not a valid decimal") from error
    if not result.is_finite():
        raise ValueError("Financial amount is not finite")
    return result


def _read_cached_source(entry, expected_url, cache_dir):
    if entry.get("url") != expected_url:
        raise ValueError("SEC cache source URL does not match the required public source")
    filename = entry.get("cache_file")
    expected_filename = _digest(expected_url.encode("utf-8")) + ".json"
    if filename != expected_filename:
        raise ValueError("SEC cache filename must be the hash of its source URL")
    path = cache_dir / filename
    if path.is_symlink() or not path.is_file():
        raise ValueError("Required public SEC cache response is missing or is a symbolic link")
    wrapper = json.loads(path.read_bytes())
    if wrapper.get("url") != expected_url or not isinstance(wrapper.get("body"), str):
        raise ValueError("Cached SEC wrapper URL or response body is invalid")
    body = wrapper["body"]
    actual_hash = _digest(body.encode("utf-8"))
    if not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("body_sha256", ""))) or actual_hash != entry["body_sha256"]:
        raise ValueError("Cached SEC response body hash does not match the public source manifest")
    return body, actual_hash


def _submission_match(recent, fact, cik):
    fields = ("accessionNumber", "filingDate", "reportDate", "form", "primaryDocument")
    if any(not isinstance(recent.get(field), list) for field in fields):
        raise ValueError("Cached submissions lack filing arrays")
    if len({len(recent[field]) for field in fields}) != 1:
        raise ValueError("Cached submissions arrays have incompatible lengths")
    matches = [index for index, accession in enumerate(recent["accessionNumber"]) if accession == fact["accession"]]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("Canonical annual accession is not unique in cached submissions")
    index = matches[0]
    if (recent["form"][index] != "10-K" or recent["filingDate"][index] != fact["filed"]
            or recent["reportDate"][index] != fact["end"]):
        raise ValueError("Canonical annual filing fields do not match cached submissions")
    document = recent["primaryDocument"][index]
    if not isinstance(document, str) or not re.fullmatch(r"[^/]+\.(?:htm|html)", document, flags=re.IGNORECASE):
        raise ValueError("Cached annual filing primary document is invalid")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{fact['accession'].replace('-', '')}/{document}"


def _recent_submission(submissions, fact, cik, sources, cache_dir, historical):
    """Resolve a filing in recent data or its issuer-declared historical index."""
    recent_url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    match = _submission_match(submissions.get("filings", {}).get("recent", {}), fact, cik)
    if match is not None:
        return match, recent_url
    files = submissions.get("filings", {}).get("files", [])
    if not isinstance(files, list):
        raise ValueError("Cached historical submissions declarations are invalid")
    filing_date = date.fromisoformat(fact["filed"])
    names, candidates = set(), []
    for entry in files:
        if not isinstance(entry, dict):
            raise ValueError("Cached historical submissions declaration is invalid")
        name = entry.get("name", "")
        if not isinstance(name, str) or not re.fullmatch(rf"CIK{cik:010d}-submissions-\d{{3}}\.json", name):
            raise ValueError("Historical submissions index name does not match the issuer CIK")
        if name in names:
            raise ValueError("Duplicate historical submissions index declaration")
        names.add(name)
        try:
            first, last = date.fromisoformat(entry["filingFrom"]), date.fromisoformat(entry["filingTo"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Historical submissions declaration has invalid date bounds") from error
        if first > last:
            raise ValueError("Historical submissions declaration has reversed date bounds")
        if first <= filing_date <= last:
            candidates.append((entry, first, last))
    matches = []
    for entry, first, last in candidates:
        url = "https://data.sec.gov/submissions/" + entry["name"]
        if url not in sources:
            raise ValueError("Public source manifest is missing a required historical submissions index")
        if url not in historical:
            body, digest = _read_cached_source(sources[url], url, cache_dir)
            response = json.loads(body)
            if not isinstance(response, dict) or ("cik" in response and _cik(response["cik"]) != cik):
                raise ValueError("Historical submissions index belongs to the wrong issuer CIK")
            historical[url] = {"response": response, "body_sha256": digest}
        response = historical[url]["response"]
        match = _submission_match(response, fact, cik)
        filing_count = entry.get("filingCount")
        if type(filing_count) is not int or filing_count != len(response["accessionNumber"]):
            raise ValueError("Historical submissions index count differs from its declaration")
        try:
            in_bounds = all(first <= date.fromisoformat(value) <= last for value in response["filingDate"])
        except (TypeError, ValueError) as error:
            raise ValueError("Historical submissions index contains invalid filing dates") from error
        if not in_bounds:
            raise ValueError("Historical submissions index filing dates exceed its declared bounds")
        if match is not None:
            matches.append((match, url))
    if len(matches) != 1:
        raise ValueError("Canonical annual accession is not unique in cached submissions")
    return matches[0]


def _matches_companyfact(fact, companyfacts):
    tag = fact.get("xbrl_concept")
    if tag not in TAGS[fact["concept"]] or fact.get("unit") != "USD" or fact.get("form") != "10-K":
        raise ValueError("Canonical financial concept, annual form or currency is invalid")
    namespace, concept = tag.split(":", 1)
    candidates = companyfacts.get("facts", {}).get(namespace, {}).get(concept, {}).get("units", {}).get("USD", [])
    if not isinstance(candidates, list):
        raise ValueError("Cached companyfacts USD records are invalid")
    expected_amount = _amount(fact["value"])
    fields = {"start": fact["start"], "end": fact["end"], "accn": fact["accession"], "form": "10-K", "filed": fact["filed"]}
    for candidate in candidates:
        if all(candidate.get(field) == value for field, value in fields.items()):
            if _amount(candidate.get("val")) == expected_amount:
                return
    raise ValueError("Canonical financial value and annual filing fields are absent from cached SEC companyfacts")


def verify(corpus_path, source_manifest_path, cache_dir):
    """Return a path-free public receipt after all cached provenance checks pass."""
    corpus_path, source_manifest_path, cache_dir = Path(corpus_path), Path(source_manifest_path), Path(cache_dir)
    corpus_raw = corpus_path.read_bytes()
    document = json.loads(corpus_raw)
    corpus = Corpus(corpus_path)
    manifest_raw = source_manifest_path.read_bytes()
    source_manifest = json.loads(manifest_raw)
    scope_id, expected_companies = _scope()
    if document.get("metadata", {}).get("origin_corpus_sha256") != source_manifest.get("corpus_sha256"):
        raise ValueError("Normalized snapshot origin hash does not match the supplied public source manifest")
    if not re.fullmatch(r"[0-9a-f]{64}", str(source_manifest.get("corpus_sha256", ""))):
        raise ValueError("Public source manifest lacks its original corpus hash")
    source_rows = source_manifest.get("sources", [])
    if not isinstance(source_rows, list) or source_manifest.get("source_count") != len(source_rows):
        raise ValueError("Public source manifest count is inconsistent")
    sources = {row.get("url"): row for row in source_rows}
    if len(sources) != len(source_rows):
        raise ValueError("Public source manifest has duplicate source URLs")
    company_rows = document["companies"]
    actual_companies = {row["ticker"]: row for row in company_rows}
    if len(actual_companies) != len(company_rows) or set(actual_companies) != set(expected_companies):
        raise ValueError("Normalized snapshot must contain the twelve declared companies exactly once")
    for ticker, expected in expected_companies.items():
        if any(actual_companies[ticker].get(field) != expected[field] for field in ("company", "sector", "cik")):
            raise ValueError("Normalized company identity or sector differs from the declared coverage scope")
    fact_groups, passage_groups = defaultdict(list), defaultdict(list)
    for fact in document["facts"]:
        cell = (fact.get("ticker"), fact.get("fiscal_year"))
        if cell[0] not in expected_companies or type(cell[1]) is not int or cell[1] not in YEARS or fact.get("concept") not in CONCEPTS:
            raise ValueError("Normalized fact is outside the declared company/year/concept scope")
        fact_groups[cell].append(fact)
    for passage in document["passages"]:
        cell = (passage.get("ticker"), passage.get("year"))
        if (cell[0] not in expected_companies or type(cell[1]) is not int or cell[1] not in YEARS
                or passage.get("item") not in ITEMS or not isinstance(passage.get("text"), str) or not passage["text"].strip()):
            raise ValueError("Normalized section chunk is outside the declared scope or has no text")
        passage_groups[cell].append(passage)
    required_urls = set()
    validated_sources, cells, historical = [], [], {}
    for ticker, expected in sorted(expected_companies.items()):
        cik = _cik(expected["cik"])
        facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        bodies = {}
        for kind, url in (("companyfacts", facts_url), ("submissions", submissions_url)):
            if url not in sources:
                raise ValueError("Public source manifest is missing a required SEC API source")
            body, digest = _read_cached_source(sources[url], url, cache_dir)
            response = json.loads(body)
            if _cik(response.get("cik")) != cik:
                raise ValueError("Cached SEC API response belongs to the wrong issuer CIK")
            bodies[kind] = response
            required_urls.add(url)
            validated_sources.append({"kind": kind, "url": url, "body_sha256": digest})
        for year in YEARS:
            facts = fact_groups[(ticker, year)]
            if len(facts) != 2 or Counter(row["concept"] for row in facts) != {"revenue": 1, "operating_income": 1}:
                raise ValueError("Expected exactly two canonical annual facts for every company/year")
            by_concept = {row["concept"]: row for row in facts}
            revenue, income = corpus.canonical_pair(by_concept["revenue"]["id"], by_concept["operating_income"]["id"])
            if not revenue["end"].startswith(f"{year}-"):
                raise ValueError("Canonical annual period end differs from its fiscal year label")
            filing_url, submissions_index_url = _recent_submission(bodies["submissions"], revenue, cik, sources, cache_dir, historical)
            for fact in (revenue, income):
                if (fact.get("company") != expected["company"] or fact.get("sector") != expected["sector"]
                        or fact.get("source_kind") != "sec_edgar" or fact.get("source_url") != filing_url):
                    raise ValueError("Normalized financial source identity does not match its SEC annual filing")
                if fact.get("filed") != revenue["filed"]:
                    raise ValueError("Canonical financial pair uses different filing dates")
                _matches_companyfact(fact, bodies["companyfacts"])
            if filing_url not in sources:
                raise ValueError("Public source manifest is missing an original annual filing")
            _, filing_hash = _read_cached_source(sources[filing_url], filing_url, cache_dir)
            required_urls.add(filing_url)
            validated_sources.append({"kind": "annual_filing", "url": filing_url, "body_sha256": filing_hash})
            passages = passage_groups[(ticker, year)]
            item_counts = Counter(row["item"] for row in passages)
            if any(item_counts[item] == 0 for item in ITEMS):
                raise ValueError("Every company/year requires cached Item 1A and Item 7 section chunks")
            for passage in passages:
                if any(passage.get(field) != revenue[field] for field in ("company", "accession", "filed", "source_kind", "source_url")):
                    raise ValueError("Normalized passage source identity differs from its canonical annual filing")
                if "sector" in passage and passage["sector"] != expected["sector"]:
                    raise ValueError("Normalized passage sector differs from the declared company")
            cells.append({"ticker": ticker, "sector": expected["sector"], "fiscal_year": year,
                          "period_start": revenue["start"], "period_end": revenue["end"],
                          "accession": revenue["accession"], "source_url": filing_url, "filing_body_sha256": filing_hash,
                          "submissions_index_url": submissions_index_url,
                          "fact_count": 2, "companyfacts_memberships_checked": 2,
                          "item_1a_chunk_count": item_counts["1A"], "item_7_chunk_count": item_counts["7"]})
    for url, entry in historical.items():
        required_urls.add(url)
        validated_sources.append({"kind": "historical_submissions", "url": url, "body_sha256": entry["body_sha256"]})
    if set(sources) != required_urls:
        raise ValueError("Public source manifest does not exactly match the required SEC responses")
    return {
        "status": "passed", "verification_kind": "read_only_cached_sec_provenance",
        "coverage_scope_id": scope_id, "snapshot_sha256": _digest(corpus_raw),
        "origin_corpus_sha256": source_manifest["corpus_sha256"], "source_manifest_sha256": _digest(manifest_raw),
        "company_count": 12, "sector_counts": {"Healthcare": 6, "Technology": 6},
        "fiscal_years": list(YEARS), "company_year_count": len(cells), "fact_count": len(document["facts"]),
        "companyfacts_memberships_checked": 72, "submissions_accessions_checked": 36,
        "historical_submissions_source_count": len(historical),
        "historical_submissions_accessions_checked": sum("-submissions-" in cell["submissions_index_url"] for cell in cells),
        "section_group_count": 72, "passage_count": len(document["passages"]), "cached_source_count": len(required_urls),
        "network_requests": 0, "model_calls": 0,
        "review_limits": {
            "original_item_boundaries": "independent_domain_review_pending",
            "financial_comparability": "independent_domain_review_pending",
            "section_text_extraction": "cached_chunk_source_identity_checked; original_HTML_extraction_not_reconstructed",
            "freshness": "checks_supplied_cached_responses_only",
        },
        "sources": sorted(validated_sources, key=lambda row: row["url"]), "cells": cells,
    }


def _write_receipt(path, receipt):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".coverage-", dir=path.parent, delete=False) as handle:
            stage = Path(handle.name)
            handle.write((json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
            stage.chmod(0o644)
        os.replace(stage, path)
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--cache-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    if arguments.output.resolve() in {arguments.corpus.resolve(), arguments.source_manifest.resolve()}:
        parser.error("The receipt output must differ from both source documents")
    if arguments.output.resolve().is_relative_to(arguments.cache_dir.resolve()):
        parser.error("The receipt output must be outside the read-only SEC cache")
    receipt = verify(arguments.corpus, arguments.source_manifest, arguments.cache_dir)
    _write_receipt(arguments.output, receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "company_count", "company_year_count", "companyfacts_memberships_checked", "cached_source_count", "passage_count", "network_requests", "model_calls")}, indent=2))
