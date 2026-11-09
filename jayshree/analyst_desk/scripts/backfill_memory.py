"""Rebuild past-note memory from the research portal.

Every published note in the portal is (re)remembered: its figures are parsed
from its verified [fact]/[calc] tags. Safe to run again (same keys are
overwritten). Use it for notes published before memory existed. A note the
analyst deleted from memory is skipped: deletion is not undone by a backfill.

    python scripts/backfill_memory.py [--analyst NAME]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analystdesk.memory import remember_published_note, suppressed_notes   # noqa: E402
from analystdesk.servers.portal import _db_path          # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyst", default="analyst", help="whose coverage list to update")
    args = ap.parse_args()
    path = _db_path()
    if not path.exists():
        print("No portal database yet: nothing to backfill.")
        return
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = con.execute("SELECT id, title, body, tickers, approver, published_at FROM notes ORDER BY id").fetchall()
    con.close()
    deleted = asyncio.run(suppressed_notes())
    for note_id, title, body, tickers, approver, published_at in rows:
        if note_id in deleted:
            print(f"note #{note_id}: skipped, deleted from memory by the analyst")
            continue
        figures = asyncio.run(remember_published_note(
            note_id, title, body, json.loads(tickers), approver, args.analyst, published_at))
        print(f"note #{note_id}: remembered figures for {', '.join(sorted(figures)) or 'none'}")


if __name__ == "__main__":
    main()
