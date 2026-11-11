"""Entry point for the AnalystDesk CLI.

Usage:
    # Validate scope only (Phase 0)
    python3 -m analystdesk --years 2022 2023 2024

    # Run C0 baseline pipeline (Phase 1) — fetches real EDGAR data
    python3 -m analystdesk --years 2022 2023 2024 --mode baseline

    # Use tickers instead of company names
    python3 -m analystdesk --companies MSFT GOOGL --years 2022 2023 2024 --mode baseline
"""

import argparse
import json

from analystdesk.research.scope import ScopeError
from analystdesk.research.scope import create_request


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AnalystDesk: research notes with verified numbers."
    )
    parser.add_argument(
        "--companies", nargs="+", default=["Microsoft", "Alphabet"],
        help="Company names or tickers (default: Microsoft Alphabet)"
    )
    parser.add_argument(
        "--years", nargs="+", required=True, type=int,
        help="Exactly three fiscal-year labels, e.g. 2022 2023 2024"
    )
    parser.add_argument(
        "--mode", choices=["scope", "baseline"], default="scope",
        help=(
            "scope    — validate the request and exit (default)\n"
            "baseline — run C0 fixed pipeline, fetch real EDGAR data"
        )
    )
    args = parser.parse_args()

    try:
        request = create_request(args.companies, args.years)
    except ScopeError as error:
        parser.error(str(error))
        return

    if args.mode == "scope":
        print(json.dumps({
            "status": "scope_validated",
            "request": request.to_dict(),
            "message": "Scope accepted. Filing availability and actual period dates have not been checked.",
        }, indent=2))
        return

    if args.mode == "baseline":
        from analystdesk.research.baseline import run_baseline
        print("Fetching EDGAR data (first run hits the network, subsequent runs use cache)...",
              flush=True)
        note = run_baseline(request)
        print(note.to_json())
        if note.warnings:
            import sys
            print("\nWarnings:", file=sys.stderr)
            for w in note.warnings:
                print(f"  ! {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
