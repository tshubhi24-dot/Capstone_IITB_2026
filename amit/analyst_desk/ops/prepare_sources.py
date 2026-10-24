"""Validate and prepare a fixed-scope public SEC source snapshot.

The default scope contains twelve companies in two sectors, FY2023–2025.
Only supplied public source data is read; the raw cache remains local. Every
selected section chunk is preserved. Original filing boundaries still require
independent domain review.
"""
import argparse
from collections import Counter
from datetime import date
from decimal import InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desk.data import Corpus

SCOPE_PATH = ROOT / "data/coverage_scope.json"
CONCEPTS = ("revenue", "operating_income")
SECTIONS = ("1A", "7")
XBRL_CONCEPTS = {
    "revenue": {"us-gaap:Revenues", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"},
    "operating_income": {"us-gaap:OperatingIncomeLoss"},
}
FACT_FIELDS = ("id", "ticker", "company", "sector", "fiscal_year", "concept", "xbrl_concept",
               "value", "unit", "start", "end", "accession", "filed", "form", "source_url", "source_kind")
PASSAGE_FIELDS = ("id", "ticker", "company", "year", "item", "text", "accession", "filed", "source_url", "source_kind", "table")


def _json_bytes(document, *, indent=None):
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=indent, allow_nan=False) + "\n").encode("utf-8")


def _integer(value, label):
    if type(value) is not int:
        raise ValueError(f"{label} must be an integer")
    return value


def _required(row, field):
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid source field: {field}")
    return value


def _load_scope(scope_path, tickers):
    raw = Path(scope_path).read_bytes()
    scope = json.loads(raw)
    if scope.get("canonical_concepts") != list(CONCEPTS) or scope.get("sections") != list(SECTIONS):
        raise ValueError("Scope must require the two canonical concepts and Items 1A and 7")
    years = scope.get("fiscal_years", [])
    if years != [2023, 2024, 2025] or any(type(year) is not int for year in years):
        raise ValueError("The coverage scope is fixed to FY2023–2025")
    rows = scope.get("companies", [])
    if not isinstance(rows, list) or len(rows) != 12:
        raise ValueError("Scope must contain twelve companies")
    by_ticker = {}
    for row in rows:
        ticker = _required(row, "ticker")
        if ticker in by_ticker or not re.fullmatch(r"[A-Z]{1,5}", ticker):
            raise ValueError("Scope has duplicate or invalid company tickers")
        for field in ("company", "sector"):
            _required(row, field)
        if not re.fullmatch(r"\d{10}", _required(row, "cik")):
            raise ValueError("Scope CIK must contain ten digits")
        by_ticker[ticker] = row
    if Counter(row["sector"] for row in rows) != {"Technology": 6, "Healthcare": 6}:
        raise ValueError("Scope must contain six Technology and six Healthcare companies")
    selected = list(by_ticker) if tickers is None else list(tickers)
    if not selected or len(set(selected)) != len(selected) or not set(selected) <= set(by_ticker):
        raise ValueError("Requested tickers must be a nonempty, unique subset of the declared scope")
    return scope, {ticker: by_ticker[ticker] for ticker in sorted(selected)}, hashlib.sha256(raw).hexdigest()


def _sec_source(row, company):
    accession = _required(row, "accession")
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
        raise ValueError("Invalid SEC accession")
    parsed = urlparse(_required(row, "source_url"))
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("Invalid SEC source URL") from error
    expected = f"/Archives/edgar/data/{int(company['cik'])}/{accession.replace('-', '')}/"
    if (parsed.scheme != "https" or parsed.hostname not in {"www.sec.gov", "sec.gov"}
            or parsed.username or parsed.password or port not in (None, 443)
            or parsed.query or parsed.fragment or not parsed.path.startswith(expected)
            or not re.fullmatch(r"[^/]+\.(?:htm|html)", parsed.path[len(expected):], flags=re.IGNORECASE)):
        raise ValueError("Only original SEC filing URLs matching company CIK and accession are accepted")
    if row.get("source_kind") != "sec_edgar" or row.get("company") != company["company"]:
        raise ValueError("Source company or source kind does not match the declared scope")
    if "sector" in row and row["sector"] != company["sector"]:
        raise ValueError("Source sector does not match the declared scope")
    date.fromisoformat(_required(row, "filed"))
    _required(row, "id")


def _select(original, companies, years):
    source_companies = original["companies"]
    facts, passages = [], []
    selected_companies = []
    for ticker, expected in companies.items():
        matches = [row for row in source_companies if row.get("ticker") == ticker]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one company record for {ticker}")
        row = matches[0]
        if any(row.get(field) != expected[field] for field in ("company", "sector", "cik")):
            raise ValueError(f"Company identity does not match the declared scope: {ticker}")
        # Scope-owned identities prevent unrelated cache metadata entering the snapshot.
        selected_companies.append({**expected, "name": expected["company"]})
    for row in original["facts"]:
        if row.get("ticker") not in companies:
            continue
        year = _integer(row.get("fiscal_year"), "Fact fiscal_year")
        if year not in years or row.get("concept") not in CONCEPTS:
            continue
        _sec_source(row, companies[row["ticker"]])
        if row.get("form") != "10-K" or _required(row, "xbrl_concept") not in XBRL_CONCEPTS[row["concept"]]:
            raise ValueError("Expected canonical annual 10-K US-GAAP facts")
        for field in FACT_FIELDS:
            if field not in row:
                raise ValueError(f"Missing fact field: {field}")
        if isinstance(row["value"], bool) or not isinstance(row["value"], (str, int, float)):
            raise ValueError("Financial input value must be a decimal-compatible number")
        period_end = date.fromisoformat(_required(row, "end"))
        date.fromisoformat(_required(row, "start"))
        if period_end.year != year:
            raise ValueError("Annual period end must fall in its labelled fiscal year")
        if date.fromisoformat(row["filed"]) < period_end:
            raise ValueError("A filing date cannot precede the annual period end")
        facts.append({field: row[field] for field in FACT_FIELDS})
    counts = Counter((row["ticker"], row["fiscal_year"], row["concept"]) for row in facts)
    expected_cells = {(ticker, year, concept) for ticker in companies for year in years for concept in CONCEPTS}
    if set(counts) != expected_cells or any(count != 1 for count in counts.values()):
        raise ValueError("Expected exactly one revenue and one operating-income fact per company and fiscal year")
    canonical = {(row["ticker"], row["fiscal_year"]): row for row in facts if row["concept"] == "revenue"}
    for row in original["passages"]:
        if row.get("ticker") not in companies:
            continue
        year = _integer(row.get("year"), "Passage year")
        item = row.get("item", "").upper()
        if year not in years or item not in SECTIONS:
            continue
        _sec_source(row, companies[row["ticker"]])
        _required(row, "text")
        if any(row.get(field) != canonical[(row["ticker"], year)][field]
               for field in ("accession", "filed", "source_url", "company", "source_kind")):
            raise ValueError("Section chunk does not match its canonical annual filing")
        passages.append({**{field: row[field] for field in PASSAGE_FIELDS if field in row}, "item": item})
    ids = [row["id"] for row in facts + passages]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source identifiers")
    return selected_companies, facts, passages


def _stage(path, raw, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".prepare-", dir=path.parent, delete=False) as handle:
        stage = Path(handle.name)
        try:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
            stage.chmod(mode)
        except BaseException:
            stage.unlink(missing_ok=True)
            raise
    return stage


def _replace_pair(snapshot_stage, destination, manifest_stage, public):
    """Publish data first and the manifest last; restore data on publish failure."""
    previous = destination.read_bytes() if destination.exists() else None
    previous_mode = destination.stat().st_mode & 0o777 if previous is not None else 0o644
    os.replace(snapshot_stage, destination)
    try:
        os.replace(manifest_stage, public)
    except BaseException:
        if previous is None:
            destination.unlink(missing_ok=True)
        else:
            restoration = _stage(destination, previous, previous_mode)
            try:
                os.replace(restoration, destination)
            finally:
                restoration.unlink(missing_ok=True)
        raise


def prepare(source_path, output=None, *, tickers=None, scope_path=None, manifest_path=None):
    """Import the full declared scope, or an explicit subset, without model calls.

    Both artifacts are fully staged and validated before replacement. Validation
    failures leave the existing snapshot and manifest byte-for-byte unchanged.
    The public manifest is replaced only after the validated data is installed.
    """
    source = Path(source_path).resolve()
    scope, companies, scope_hash = _load_scope(scope_path or SCOPE_PATH, tickers)
    raw = source.read_bytes()
    original = json.loads(raw)
    metadata = original.get("metadata", {})
    if metadata.get("synthetic") is True or metadata.get("source_kind") not in (None, "sec_edgar"):
        raise ValueError("Synthetic or non-SEC source snapshots cannot supply research coverage")
    origin = hashlib.sha256(raw).hexdigest()
    years = scope["fiscal_years"]
    selected_companies, facts, passages = _select(original, companies, years)
    destination = Path(output or ROOT / ".runtime/journey/sources").resolve() / "corpus.json"
    public = Path(manifest_path or ROOT / "data/source_manifest.json").resolve()
    if len({source, destination, public, Path(scope_path or SCOPE_PATH).resolve()}) != 4:
        raise ValueError("Source, snapshot, scope and manifest paths must be distinct")
    document = {
        "metadata": {"source_kind": "sec_edgar", "coverage_scope_id": scope["scope_id"], "coverage_scope_sha256": scope_hash,
                     "origin_corpus_sha256": origin,
                     "selection": "Declared company subset, fixed fiscal years, two canonical annual concepts and all cached Item 1A/7 chunks.",
                     "limitations": "Original filing Item boundaries and fact selection require independent domain review."},
        "companies": selected_companies, "facts": facts, "passages": passages,
    }
    snapshot_stage = manifest_stage = None
    try:
        snapshot_stage = _stage(destination, _json_bytes(document), 0o644)
        corpus = Corpus(snapshot_stage)
        section_inventory = []
        for ticker in companies:
            for year in years:
                by_concept = {row["concept"]: row for row in corpus.facts(ticker, [year])}
                try:
                    revenue, income = corpus.canonical_pair(by_concept["revenue"]["id"], by_concept["operating_income"]["id"])
                except InvalidOperation as error:
                    raise ValueError("Financial inputs must contain valid decimal amounts") from error
                if any(revenue[field] != income[field] for field in ("filed", "form", "source_url", "company", "sector", "source_kind")):
                    raise ValueError("Canonical financial pair must describe the same annual filing")
                for item in SECTIONS:
                    section = corpus.section(ticker, year, item)
                    section_inventory.append({"ticker": ticker, "year": year, "item": item,
                                              "chunk_count": len(section["chunks"]), "accession": revenue["accession"],
                                              "source_url": revenue["source_url"],
                                              "source_ids_sha256": hashlib.sha256(_json_bytes(section["source_ids"])).hexdigest(),
                                              "snapshot_complete": True, "original_item_boundaries_reviewed": False})
        manifest = {
            "source_kind": "sec_edgar", "coverage_scope_id": scope["scope_id"], "coverage_scope_sha256": scope_hash,
            "companies": selected_companies, "tickers": sorted(companies), "years": years,
            "sectors": dict(sorted(Counter(row["sector"] for row in selected_companies).items())),
            "snapshot_sha256": corpus.fingerprint, "origin_corpus_sha256": origin,
            "company_count": len(companies), "company_year_count": len(companies) * len(years),
            "fact_count": len(facts), "passage_count": len(passages), "section_count": len(section_inventory),
            "fact_inventory": facts, "section_inventory": section_inventory,
            "raw_cache_committed": False, "independent_source_review": "pending",
            "section_completeness": "All selected section chunks from the supplied cached snapshot; original Item boundaries remain unverified.",
            "reproduction": "Run ops/prepare_sources.py --source-corpus PATH_TO_SEC_CORPUS_JSON; default data/coverage_scope.json, optional --tickers for an explicit subset.",
        }
        manifest_stage = _stage(public, _json_bytes(manifest, indent=2), 0o644)
        _replace_pair(snapshot_stage, destination, manifest_stage, public)
        return {key: manifest[key] for key in ("source_kind", "coverage_scope_id", "tickers", "years", "sectors", "snapshot_sha256", "company_count", "company_year_count", "fact_count", "passage_count", "section_count")}
    finally:
        for stage in (snapshot_stage, manifest_stage):
            if stage is not None:
                stage.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-corpus", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--scope", type=Path, default=SCOPE_PATH)
    parser.add_argument("--tickers", nargs="+", help="Explicit subset of the declared twelve-company scope")
    parser.add_argument("--manifest", type=Path, help="Public manifest output path")
    args = parser.parse_args()
    print(json.dumps(prepare(args.source_corpus, args.output, tickers=args.tickers, scope_path=args.scope, manifest_path=args.manifest), indent=2))
