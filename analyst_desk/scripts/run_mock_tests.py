"""Run the migration regression gate without network or paid model calls.

Run from the application root: python scripts/run_mock_tests.py
Uses existing mocks, scripted models, local fixtures and temporary stores.
This is test tooling, not an application entry point.
"""

from pathlib import Path
import argparse
import json
import os
import socket
import sys
import threading
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
_local = threading.local()
_socketpair = socket.socketpair


def local_socketpair(*args, **kwargs):
    # Windows implements asyncio's internal wakeup pipe using loopback sockets.
    # Permit only socketpair construction, never ordinary client connections.
    _local.socketpair = True
    try:
        return _socketpair(*args, **kwargs)
    finally:
        _local.socketpair = False


def deny_network(event, args):
    # Audit hooks still block connection attempts if a test replaces socket helpers.
    if (event in {"socket.connect", "socket.sendto", "socket.getaddrinfo"}
            and not getattr(_local, "socketpair", False)):
        raise RuntimeError("Network disabled by the mock-only migration test gate")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, help="Write test IDs and result metadata here")
    args = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ.update({
        "PYTHON_DOTENV_DISABLED": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "LANGCHAIN_TRACING_V2": "false",
        "LANGSMITH_TRACING": "false",
        "OTEL_SDK_DISABLED": "true",
        "OPENROUTER_API_KEY": "mock-only-no-credit",
        "OPENAI_API_KEY": "mock-only-no-credit",
        "SANDBOX_MODE": "local",
    })
    sys.addaudithook(deny_network)
    socket.socketpair = local_socketpair
    # Exclude the real Docker integration variant; retain local sandbox tests.
    with patch("analystdesk.servers.sandbox.docker_available", return_value=False):
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        def test_ids(node):
            for test in node:
                if isinstance(test, unittest.TestSuite):
                    yield from test_ids(test)
                else:
                    yield test.id()

        ids = sorted(test_ids(suite))
        if args.report_dir:
            args.report_dir.mkdir(parents=True, exist_ok=True)
            (args.report_dir / "test_ids.json").write_text(json.dumps(ids, indent=2) + "\n", encoding="utf-8")
        print(f"Discovered {suite.countTestCases()} tests (network blocked).", flush=True)
        started = time.monotonic()
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if args.report_dir:
            report = {
                "python": sys.version.split()[0], "platform": sys.platform,
                "discovered": len(ids), "run": result.testsRun,
                "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
                "failures": [test.id() for test, _ in result.failures],
                "errors": [test.id() for test, _ in result.errors],
                "skipped": [{"id": test.id(), "reason": reason} for test, reason in result.skipped],
                "seconds": round(time.monotonic() - started, 3),
                "successful": result.wasSuccessful(), "network_blocked": True,
            }
            (args.report_dir / "test_results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
