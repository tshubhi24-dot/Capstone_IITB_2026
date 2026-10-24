"""Fixed pandas calculation worker; its only runtime mount is the job queue."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
import json
import os
from pathlib import Path
import re
import signal
import time


def calculate_row(facts):
    """Validate again inside the isolated worker; never execute supplied code."""
    if not isinstance(facts, list) or len(facts) != 2:
        raise ValueError("Exactly two canonical facts are required.")
    revenue, income = facts
    if revenue.get("concept") != "revenue" or income.get("concept") != "operating_income":
        raise ValueError("Operating margin requires revenue and operating income.")
    if not revenue.get("id") or revenue["id"] == income.get("id"):
        raise ValueError("Distinct source fact identifiers are required.")
    for field in ("ticker", "fiscal_year", "start", "end", "unit", "accession"):
        if revenue.get(field) is None or revenue.get(field) != income.get(field):
            raise ValueError("Incompatible financial periods, issuer, units or filing.")
    days = (date.fromisoformat(revenue["end"]) - date.fromisoformat(revenue["start"])).days + 1
    if not 330 <= days <= 380 or revenue["unit"] != "USD":
        raise ValueError("Compatible annual USD facts are required.")
    amount, profit = Decimal(str(revenue["value"])), Decimal(str(income["value"]))
    if not amount.is_finite() or not profit.is_finite() or amount <= 0:
        raise ValueError("Financial inputs must be finite and revenue must be positive.")
    if max(abs(amount), abs(profit)) > Decimal("1e16"):
        raise ValueError("Financial inputs exceed the bounded calculation range.")
    import pandas as pd
    frame = pd.DataFrame([{"revenue": float(amount), "operating_income": float(profit)}])
    frame["margin_pct"] = frame["operating_income"] / frame["revenue"] * 100
    with localcontext() as context:
        context.prec = 40
        exact = profit / amount * 100
        if abs(Decimal(str(frame.iloc[0]["margin_pct"])) - exact) > Decimal(".0000001"):
            raise ValueError("Pandas and precise arithmetic disagree.")
        displayed = str(exact.quantize(Decimal(".01"), rounding=ROUND_HALF_UP))
    return {"ticker": revenue["ticker"], "year": revenue["fiscal_year"],
            "revenue": str(amount), "operating_income": str(profit), "margin_pct": displayed,
            "fact_ids": [revenue["id"], income["id"]], "period_start": revenue["start"],
            "period_end": revenue["end"], "unit": revenue["unit"],
            "formula": "operating_income / revenue * 100", "executor": "isolated_pandas_queue"}


def process_job(path):
    match = re.fullmatch(r"([a-f0-9]{32})\.request\.json", path.name)
    if not match:
        raise ValueError("Invalid queue request identifier.")
    identifier = match.group(1)
    result = {"request_id": identifier, "ok": False, "data": None, "error": None}
    try:
        if path.stat().st_size > 65536 or path.is_symlink():
            raise ValueError("Calculation request is too large or invalid.")
        job = json.loads(path.read_text())
        if set(job) != {"request_id", "facts"} or job["request_id"] != identifier:
            raise ValueError("Calculation request schema or identity does not match.")
        signal.setitimer(signal.ITIMER_REAL, 10)
        result.update(ok=True, data=calculate_row(job["facts"]))
    except Exception as exc:
        result["error"] = {"code": type(exc).__name__, "message": "The isolated calculation rejected or failed this job."}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    temporary = path.parent / (identifier + ".result.new")
    temporary.write_text(json.dumps(result) + "\n")
    temporary.replace(path.parent / (identifier + ".result.json"))
    path.unlink(missing_ok=True)


def main():
    queue = Path(os.environ.get("CALCULATION_QUEUE", "/queue"))
    if not queue.is_dir():
        raise SystemExit("The isolated calculation queue is unavailable.")

    def timed_out(*_):
        raise TimeoutError("Calculation exceeded its ten-second limit.")

    signal.signal(signal.SIGALRM, timed_out)
    print("Networkless calculation worker ready.", flush=True)
    while True:
        for path in sorted(queue.glob("*.request.json"))[:64]:
            try:
                process_job(path)
            except (OSError, ValueError):
                continue
        for path in queue.glob("*.result.json"):
            try:
                if time.time() - path.stat().st_mtime > 60:
                    path.unlink()
            except FileNotFoundError:
                pass
        time.sleep(.05)


if __name__ == "__main__":
    main()
