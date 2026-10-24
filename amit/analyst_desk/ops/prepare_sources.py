"""Prepare a new two-company source snapshot from a reviewed public SEC cache.

Only source data is read; no older application code or historical results are
imported. The raw cache stays local. Public source identities are reviewable.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desk.data import Corpus


def prepare(source_path, output=None):
    source = Path(source_path).resolve()
    raw = source.read_bytes()
    original = json.loads(raw)
    tickers, years = {"MSFT", "AAPL"}, {2023, 2024, 2025}
    facts = [v for v in original["facts"] if v["ticker"] in tickers and v["fiscal_year"] in years and v["concept"] in {"revenue", "operating_income"}]
    passages = [v for v in original["passages"] if v["ticker"] in tickers and int(v["year"]) in years and v["item"].upper() in {"1A", "7"}]
    for fact in facts:
        url = urlparse(fact["source_url"])
        if url.scheme != "https" or url.hostname not in {"www.sec.gov", "sec.gov"} or url.username or url.password:
            raise ValueError("Only public original SEC source URLs are accepted")
    if len(facts) != 12:
        raise ValueError("Expected twelve canonical annual revenue/operating-income facts")
    origin = hashlib.sha256(raw).hexdigest()
    document = {"metadata": {"source_kind": "sec_edgar", "prepared_date": "2026-10-24", "origin_corpus_sha256": origin,
                            "provenance": "New two-company extraction from a supplied cached public SEC source snapshot; no legacy application imported.",
                            "limitations": "Original filing Item boundaries and fact selection still require independent domain review."},
                "companies": [v for v in original["companies"] if v["ticker"] in tickers], "facts": facts, "passages": passages}
    out = Path(output or ROOT / ".runtime/journey/sources")
    out.mkdir(parents=True, exist_ok=True)
    out.chmod(0o755)
    destination = out / "corpus.json"
    destination.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True) + "\n")
    destination.chmod(0o644)
    corpus = Corpus(destination)
    for ticker in sorted(tickers):
        for year in sorted(years):
            selected = corpus.facts(ticker, [year])
            by_concept = {v["concept"]: v for v in selected}
            corpus.canonical_pair(by_concept["revenue"]["id"], by_concept["operating_income"]["id"])
            for item in ("1A", "7"):
                corpus.section(ticker, year, item)
    manifest = {"source_kind": "sec_edgar", "prepared_date": "2026-10-24", "tickers": sorted(tickers), "years": sorted(years),
                "snapshot_sha256": corpus.fingerprint, "origin_corpus_sha256": origin, "fact_count": len(facts), "passage_count": len(passages),
                "fact_inventory": facts, "raw_cache_committed": False, "independent_source_review": "pending",
                "reproduction": "Run ops/prepare_sources.py --source-corpus PATH_TO_REVIEWED_SEC_CORPUS_JSON; schema documented in data/README.md."}
    public = ROOT / "data/source_manifest.json"
    public.parent.mkdir(parents=True, exist_ok=True)
    public.write_text(json.dumps(manifest, indent=2) + "\n")
    return {key: manifest[key] for key in ("source_kind", "tickers", "years", "snapshot_sha256", "fact_count", "passage_count")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-corpus", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source_corpus, args.output), indent=2))
