"""Write the development golden cases (data/evaluation/development/dev_cases.jsonl).

Expected figures are computed here from XBRL by code and frozen into the
file BEFORE any agent runs on them (evaluation protocol: "write each
expected outcome before running the agent on that case").

Only development cases are written here. Held-out cases go in
data/evaluation/heldout/ and must be written by someone who does not tune
the agent (role 5); the agent has no tool that can read that folder.

    python not_for_submission/scripts/data/make_dev_cases.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from analystdesk.finance.figures import build_figures   # noqa: E402

OUT = ROOT / "data" / "evaluation" / "development" / "dev_cases.jsonl"

# id, type, request, expected figure keys | risk (ticker, year) | refusal
CASES = [
    ("d01", "numeric", "What was Microsoft's operating margin in fiscal 2024?", ["MSFT_2024_margin"]),
    ("d02", "numeric", "Report Apple's fiscal 2024 revenue and operating margin.", ["AAPL_2024_revenue", "AAPL_2024_margin"]),
    ("d03", "numeric", "How fast did NVIDIA's revenue grow in fiscal 2024 compared with fiscal 2023?", ["NVDA_2024_revenue_growth"]),
    ("d04", "numeric", "What was JPMorgan's pre-tax margin in 2024?", ["JPM_2024_margin"]),
    ("d05", "numeric", "What was Visa's operating margin in fiscal 2023?", ["V_2023_margin"]),
    ("d06", "numeric", "What was Wells Fargo's pre-tax margin in 2023?", ["WFC_2023_margin"]),
    ("d07", "numeric", "How much did Meta's operating margin change from 2022 to 2023?", ["META_2023_margin_change"]),
    ("d08", "numeric", "By how much did Goldman Sachs' net revenue grow in 2024 versus 2023?", ["GS_2024_revenue_growth"]),
    ("d09", "comparison", "Compare Microsoft's and Alphabet's operating margins in fiscal 2024.", ["MSFT_2024_margin", "GOOGL_2024_margin"]),
    ("d10", "comparison", "Visa vs Mastercard operating margin in 2024.", ["V_2024_margin", "MA_2024_margin"]),
    ("d11", "comparison", "Compare JPMorgan's and Bank of America's pre-tax margins in 2023.", ["JPM_2023_margin", "BAC_2023_margin"]),
    ("d12", "comparison", "Compare NVIDIA's and AMD's revenue in fiscal 2024.", ["NVDA_2024_revenue", "AMD_2024_revenue"]),
    ("d13", "comparison", "Compare Amazon's and Oracle's operating margins in fiscal 2023.", ["AMZN_2023_margin", "ORCL_2023_margin"]),
    ("d14", "risk_change", "What changed in Microsoft's risk factors between fiscal 2023 and 2024?", ("MSFT", 2024)),
    ("d15", "risk_change", "How did NVIDIA's risk factors change from fiscal 2023 to fiscal 2024?", ("NVDA", 2024)),
    ("d16", "risk_change", "What changed in JPMorgan's risk factors from 2022 to 2023?", ("JPM", 2023)),
    ("d17", "risk_change", "What new risks did Meta add in its 2024 risk factors compared with 2023?", ("META", 2024)),
    ("d18", "refusal", "What were Tesla's operating margins in 2024?", "not covered"),
    ("d19", "refusal", "What was Microsoft's operating margin in fiscal 2019?", "year not covered"),
    ("d20", "refusal", "Should investors buy NVIDIA now? Give me a price target.", "investment advice"),
]


def main() -> None:
    keys = [k for c in CASES if c[1] in ("numeric", "comparison") for k in c[3]]
    tickers = sorted({k.split("_")[0] for k in keys})
    years = sorted({int(k.split("_")[1]) for k in keys} | {2022, 2023})
    figures = build_figures(tickers, years)
    lines = []
    for cid, ctype, request, spec in CASES:
        case = {"id": cid, "split": "dev", "type": ctype, "request": request}
        if ctype in ("numeric", "comparison"):
            case["expect"] = {"figures": [{"key": k, "text": figures[k]["text"].split(" [")[0]} for k in spec]}
        elif ctype == "risk_change":
            t, y = spec
            case["expect"] = {"risk_change": {"ticker": t, "years": [y - 1, y]}}
        else:
            case["expect"] = {"refusal": spec}
        lines.append(json.dumps(case))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} dev cases to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
