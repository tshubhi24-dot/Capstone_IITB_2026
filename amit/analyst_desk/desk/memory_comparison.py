"""Code-owned comparison of approved numeric history with current cached facts."""
from decimal import Decimal, ROUND_HALF_UP

from .store import canonical_hash


def compare_approved_note(record, source):
    payload = record["payload"]
    if canonical_hash(payload) != record["payload_hash"]:
        raise ValueError("The approved historical note changed")
    metrics = payload.get("metrics", [])
    if not isinstance(metrics, list) or len(metrics) > 12:
        raise ValueError("Historical numeric scope exceeds the comparison bound")
    rows = []
    for prior in metrics:
        ticker, year = prior.get("ticker"), prior.get("year")
        row = {"ticker": ticker, "fiscal_year": year, "status": "unavailable",
               "prior_note_citation": "note:" + record["id"] + "@" + record["payload_hash"]}
        try:
            facts = source.facts(ticker, [year])
            pair = {concept: [fact for fact in facts if fact["concept"] == concept]
                    for concept in ("revenue", "operating_income")}
            if any(len(values) != 1 for values in pair.values()):
                raise ValueError("Current annual financial pair is unavailable")
            revenue, income = source.canonical_pair(pair["revenue"][0]["id"], pair["operating_income"][0]["id"])
            margin = (Decimal(str(income["value"])) / Decimal(str(revenue["value"])) * 100).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
            current = {"ticker": ticker, "year": year, "revenue": str(revenue["value"]),
                       "operating_income": str(income["value"]), "margin_pct": str(margin),
                       "period_start": revenue["start"], "period_end": revenue["end"],
                       "unit": revenue["unit"], "fact_ids": [revenue["id"], income["id"]]}
            if not source.verify_row(current):
                raise ValueError("Current facts failed independent verification")
            row["current"] = current
            comparable = all(prior.get(key) == current[key] for key in ("period_start", "period_end", "unit"))
            if not comparable:
                row.update(status="not_comparable", reason="Fiscal dates or units differ; no change is calculated.")
            else:
                old = {key: Decimal(str(prior[key])) for key in ("revenue", "operating_income", "margin_pct")}
                if not all(value.is_finite() for value in old.values()) or old["revenue"] <= 0:
                    raise ValueError("Historical numbers are invalid")
                expected_margin = (old["operating_income"] / old["revenue"] * 100).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
                if expected_margin != old["margin_pct"]:
                    raise ValueError("Historical arithmetic is inconsistent")
                delta = {key: str(Decimal(current[key]) - old[key]) for key in old}
                row.update(status="compared", prior={key: str(value) for key, value in old.items()},
                           change={"revenue_usd": delta["revenue"], "operating_income_usd": delta["operating_income"],
                                   "margin_percentage_points": delta["margin_pct"]},
                           current_source_verified=True)
        except (ValueError, KeyError, TypeError, ArithmeticError):
            row.update(status="unavailable", reason="This historical row cannot be compared with the current canonical inputs.")
        rows.append(row)
    return {"note_id": record["id"], "note_payload_hash": record["payload_hash"],
            "prior_source_fingerprint": payload.get("source_fingerprint"),
            "current_source_fingerprint": source.fingerprint,
            "archive_only": payload.get("source_fingerprint") != source.fingerprint,
            "comparisons": rows, "generative_model_calls": 0,
            "limitations": ["Prior values come from the exact approved historical note; its original snapshot may differ.",
                            "Current values are checked against the desk's cached SEC snapshot; this operation does not refresh sources.",
                            "Numeric differences do not establish causes, new risks or economic materiality."]}
