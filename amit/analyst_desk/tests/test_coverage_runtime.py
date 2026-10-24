"""Source upgrade and browser scope guards; all values are invented test data."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from ops.verify_runtime import prepared_source_scope, matches_prepared_source


ROOT = Path(__file__).resolve().parents[1]


def source_files(tmp_path, company_count):
    tickers = [f"T{number}" for number in range(company_count)]
    years = [2023, 2024, 2025]
    companies = [{"ticker": ticker, "company": f"Invented {ticker}",
                  "sector": "Technology" if index < 6 else "Healthcare"}
                 for index, ticker in enumerate(tickers)]
    facts = [{"id": f"{company['ticker']}:{year}:{concept}", **company,
              "fiscal_year": year, "concept": concept, "value": 100}
             for company in companies for year in years for concept in ("revenue", "operating_income")]
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(json.dumps({"companies": companies, "facts": facts, "passages": []}))
    fingerprint = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    manifest = {"source_kind": "sec_edgar", "tickers": tickers, "years": years,
                "snapshot_sha256": fingerprint, "fact_inventory": facts, "fact_count": len(facts)}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    config = {"companies": companies, "company_years": {ticker: years for ticker in tickers},
              "years": years, "source_fingerprint": fingerprint}
    return manifest_path, corpus_path, manifest, config


@pytest.mark.parametrize("company_count", [2, 12])
def test_runtime_scope_matches_prepared_manifest_for_old_and_expanded_snapshots(tmp_path, company_count):
    manifest, corpus, _, config = source_files(tmp_path, company_count)
    expected = prepared_source_scope(manifest, corpus)
    assert matches_prepared_source(config, expected)
    assert len(expected["company_years"]) == company_count
    assert len(set(expected["sectors"].values())) == (1 if company_count == 2 else 2)
    # Company display order is not source identity; its membership is.
    config["companies"].reverse()
    assert matches_prepared_source(config, expected)


@pytest.mark.parametrize("change", ["missing_company", "extra_company", "missing_year", "duplicate_company", "changed_sector", "changed_fingerprint", "changed_year_list"])
def test_runtime_scope_rejects_partial_stale_or_mislabelled_api_metadata(tmp_path, change):
    manifest, corpus, _, config = source_files(tmp_path, 12)
    expected = prepared_source_scope(manifest, corpus)
    if change == "missing_company":
        config["companies"].pop()
    elif change == "extra_company":
        config["companies"].append({"ticker": "EXTRA", "sector": "Technology"})
    elif change == "missing_year":
        config["company_years"]["T0"] = [2023, 2024]
    elif change == "duplicate_company":
        config["companies"].append(deepcopy(config["companies"][0]))
    elif change == "changed_sector":
        config["companies"][0]["sector"] = "Healthcare"
    elif change == "changed_fingerprint":
        config["source_fingerprint"] = "0" * 64
    else:
        config["years"] = [2024, 2025]
    assert not matches_prepared_source(config, expected)


@pytest.mark.parametrize("change", ["missing_fact", "duplicate_fact", "duplicate_ticker", "invalid_year", "stale_snapshot", "changed_bytes"])
def test_runtime_scope_refuses_invalid_or_unprepared_manifest(tmp_path, change):
    manifest_path, corpus_path, manifest, _ = source_files(tmp_path, 12)
    if change == "missing_fact":
        manifest["fact_inventory"].pop()
    elif change == "duplicate_fact":
        manifest["fact_inventory"][-1] = manifest["fact_inventory"][0]
    elif change == "duplicate_ticker":
        manifest["tickers"][-1] = manifest["tickers"][0]
    elif change == "invalid_year":
        manifest["years"] = [2023, True, 2025]
    elif change == "stale_snapshot":
        manifest["snapshot_sha256"] = "0" * 64
    else:
        corpus_path.write_text(corpus_path.read_text() + "\n")
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        prepared_source_scope(manifest_path, corpus_path)


def browser_scope(config, tickers, years, mode):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to execute the browser's actual scope validation")
    script = """const {researchScope}=require(process.argv[1]);
const input=JSON.parse(process.argv[2]);
try { console.log(JSON.stringify({ok:true,scope:researchScope(...input),input})); }
catch(error) { console.log(JSON.stringify({ok:false,error:error.message,input})); }
"""
    payload = [config, tickers, years, mode]
    result = subprocess.run([node, "-e", script, str(ROOT / "web/app.js"), json.dumps(payload)],
                            check=True, capture_output=True, text=True, timeout=10)
    output = json.loads(result.stdout)
    assert output["input"] == payload  # Guards must never silently shrink selection.
    return output


def test_browser_can_select_new_sector_companies_and_specific_years(tmp_path):
    _, _, _, config = source_files(tmp_path, 12)
    output = browser_scope(config, ["T6", "T11"], [2024, 2025], "offline")
    assert output == {"ok": True, "scope": {"tickers": ["T6", "T11"], "years": [2024, 2025]},
                      "input": [config, ["T6", "T11"], [2024, 2025], "offline"]}


@pytest.mark.parametrize("tickers,years,mode,valid", [
    (["T0", "T1", "T6", "T11"], [2023, 2024, 2025], "offline", True),
    (["T0", "T6"], [2023, 2024, 2025], "live", True),
    (["T0", "T1", "T6"], [2023, 2024, 2025], "live", False),
    (["T0", "T1", "T6", "T11"], [2024, 2025], "live", True),
    (["T0", "T1", "T6", "T10", "T11"], [2025], "offline", False),
    (["UNKNOWN"], [2025], "offline", False),
    (["T0", "T0"], [2025], "offline", False),
    (["T0"], [2025, 2024], "offline", False),
    (["T0"], [2025, 2025], "offline", False),
    (["T0"], [], "offline", False),
])
def test_browser_request_bounds_match_supported_workflow(tmp_path, tickers, years, mode, valid):
    _, _, _, config = source_files(tmp_path, 12)
    assert browser_scope(config, tickers, years, mode)["ok"] is valid


def test_browser_blocks_missing_company_year_coverage(tmp_path):
    _, _, _, config = source_files(tmp_path, 12)
    config["company_years"]["T11"] = [2024, 2025]
    assert not browser_scope(config, ["T0", "T11"], [2023, 2024, 2025], "offline")["ok"]
    assert browser_scope(config, ["T0", "T11"], [2024, 2025], "offline")["ok"]
    config["company_years"].pop("T11")
    assert not browser_scope(config, ["T0"], [2025], "offline")["ok"]
