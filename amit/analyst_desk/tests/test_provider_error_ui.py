"""Execute the actual browser error formatter without a browser or model call."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("error,rate_limited", [
    ("ReviewError: provider_http_429: The model gateway blocked or failed the operation.", True),
    ("provider_http_403", False),
    ("A source citation is invalid.", False),
])
def test_error_formatter_explains_rate_limit_without_changing_other_errors(error, rate_limited):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required to execute browser helper")
    script = "const {runErrorMessage}=require(process.argv[1]);console.log(JSON.stringify(runErrorMessage(process.argv[2])));"
    result = subprocess.run([node, "-e", script, str(ROOT / "web/app.js"), error],
                            check=True, capture_output=True, text=True, timeout=10)
    message = json.loads(result.stdout)
    if rate_limited:
        assert "HTTP 429" in message and "will not retry automatically" in message
        assert "reserved model budget" in message and error in message
        assert "quota exhausted" not in message and "refunded" not in message
    else:
        assert message == error


def test_duplicate_citation_diagnostic_is_actionable_without_echoing_raw_fields():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required to execute browser helper")
    script = """
const {runErrorMessage}=require(process.argv[1]);
console.log(JSON.stringify(runErrorMessage('ReasoningError: research stopped; inspect service diagnostics',
 {code:'duplicate_source_citation',stage:'risk',message:'private-value-not-for-display'})));
"""
    result = subprocess.run([node, "-e", script, str(ROOT / "web/app.js")],
                            check=True, capture_output=True, text=True, timeout=10)
    message = json.loads(result.stdout)
    assert "same source record" in message and "each compared year" in message
    assert "Resuming is explicit" in message and "duplicate_source_citation" in message
    assert "private-value" not in message and "inspect service diagnostics" not in message


def test_risk_number_diagnostic_preserves_year_metadata_and_manual_resume():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js required to execute browser helper")
    script = """
const {runErrorMessage}=require(process.argv[1]);
console.log(JSON.stringify(runErrorMessage('ReasoningError: private raw failure',
 {code:'narrative_number',stage:'risk',message:'private untrusted diagnostic'})));
"""
    result = subprocess.run([node, "-e", script, str(ROOT / "web/app.js")],
                            check=True, capture_output=True, text=True, timeout=10)
    message = json.loads(result.stdout)
    assert "Exact years remain" in message and "comparison details and citations" in message
    assert "one bounded correction" in message and "Resume this same approved research" in message
    assert "charges remain counted" in message and "private" not in message
