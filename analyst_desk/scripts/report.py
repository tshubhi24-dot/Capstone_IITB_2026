"""Audit a saved evaluation run or report spread across repeated held-out runs."""

from __future__ import annotations

import argparse
from importlib import import_module
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    workflows = parser.add_subparsers(dest="workflow", required=True)
    workflows.add_parser("audit", help="Validate recorded scores, coverage and provenance", add_help=False)
    workflows.add_parser("repeats", help="Audit repeated held-out runs and report their spread", add_help=False)
    args, rest = parser.parse_known_args(argv)
    module = "audit_eval_results" if args.workflow == "audit" else "eval_three_runs"
    return import_module("analystdesk.evaluation.workflows." + module).main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
