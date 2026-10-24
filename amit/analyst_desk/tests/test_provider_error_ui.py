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
