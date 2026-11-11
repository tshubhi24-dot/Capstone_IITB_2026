"""Run evaluation, calibration, memory comparison or development reflection."""

from __future__ import annotations

import argparse
import asyncio
from importlib import import_module
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    workflows = parser.add_subparsers(dest="workflow", required=True)
    forwarded = {
        "eval": ("run_eval", "C0/C1/C2 benchmark and E1/E3/E4 presets"),
        "redteam": ("run_redteam", "E2 attacks and clean-case false blocks"),
        "retrieval": ("eval_retrieval", "Labelled retrieval comparisons"),
    }
    for command, (_, description) in forwarded.items():
        workflows.add_parser(command, help=description, add_help=False)
    workflows.add_parser("financebench", help="External FinanceBench retrieval check")
    memory = workflows.add_parser("memory", help="Compare memory on/off or rescore saved runs")
    memory.add_argument("request", nargs="?")
    memory.add_argument("--rescore", type=Path)
    calibration = workflows.add_parser("calibrate", help="Sample human-label items or score judge agreement")
    calibration.add_argument("action", choices=["sample", "score"])
    calibration.add_argument("--n", type=int, default=30)
    reflection = workflows.add_parser("reflect", help="Propose pending lessons from development results")
    reflection.add_argument("results", type=Path)
    args, rest = parser.parse_known_args(argv)
    if args.workflow not in forwarded and rest:
        parser.error("unrecognized arguments: " + " ".join(rest))
    if args.workflow == "memory" and args.rescore and args.request:
        parser.error("memory accepts either a request or --rescore, not both")

    module_name = forwarded[args.workflow][0] if args.workflow in forwarded else {
        "memory": "memory_compare", "calibrate": "calibrate_judge", "reflect": "reflect",
        "financebench": "eval_financebench",
    }[args.workflow]
    module = import_module("analystdesk.evaluation.workflows." + module_name)
    if args.workflow in forwarded:
        previous = sys.argv
        sys.argv = [previous[0] + " " + args.workflow, *rest]
        try:
            if args.workflow in ("eval", "redteam"):
                return asyncio.run(module.main()) or 0
            return module.main() or 0
        finally:
            sys.argv = previous
    if args.workflow == "financebench":
        return module.main() or 0
    if args.workflow == "memory":
        operation = module.rescore(args.rescore) if args.rescore else module.main(args.request or module.REQUEST)
    elif args.workflow == "calibrate":
        operation = module.sample(args.n) if args.action == "sample" else module.score()
    else:
        operation = module.main(args.results)
    return asyncio.run(operation) or 0


if __name__ == "__main__":
    raise SystemExit(main())
