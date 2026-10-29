"""Run the C1 agent from the command line, one human gate at a time.

Each command runs the graph until the next human gate (or the end), saves
the state in the SQLite checkpointer and exits. The next command can come
from a new process — that is the stop-and-resume demo (L8). The app's
Research tab's C1/C2 modes do the same through runtime.py.

    python -m analystdesk.agent start "Compare Microsoft and Alphabet operating margins 2022-2024"
    python -m analystdesk.agent start "..." --team          # C2 team instead of C1
    python -m analystdesk.agent resume RUN_ID --approve                 # plan gate
    python -m analystdesk.agent resume RUN_ID --edit-plan plan.json
    python -m analystdesk.agent resume RUN_ID --approve --approver Jayshree   # note gate
    python -m analystdesk.agent resume RUN_ID --edit-note note.md
    python -m analystdesk.agent resume RUN_ID --reject "reason"
    python -m analystdesk.agent show RUN_ID                             # state + trace
    python -m analystdesk.agent graph                                   # Mermaid diagram
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from dotenv import load_dotenv

from .runtime import ROOT, _NoModel, get_run, run_until_gate

load_dotenv(ROOT / ".env")


async def _print(ev: dict) -> None:
    print(f"  · {ev['node']}: " + json.dumps({k: v for k, v in ev.items() if k != 'node'})[:220], flush=True)


def _report(run_id: str, result: dict) -> None:
    v = result["values"]
    print(f"\nrun {run_id}")
    if result["interrupts"]:
        gate = result["interrupts"][0]
        if gate["gate"] == "plan":
            print("WAITING FOR PLAN APPROVAL:\n" + json.dumps(gate["plan"], indent=2))
            print(f"\n  approve: python -m analystdesk.agent resume {run_id} --approve"
                  f"\n  edit:    python -m analystdesk.agent resume {run_id} --edit-plan plan.json")
        else:
            c = gate["check"]
            print(f"WAITING FOR NOTE APPROVAL — code check: {'PASS' if c['ok'] else 'ISSUES'}, "
                  f"{c['verified']}/{c['total']} numbers verified ({c['verified_share']}%)")
            for i in c["issues"]:
                print("  ! " + i)
            print(f"\n# {gate['note']['title']}\n\n{gate['note']['body']}")
            print(f"\n  approve: python -m analystdesk.agent resume {run_id} --approve --approver <name>"
                  f"\n  edit:    python -m analystdesk.agent resume {run_id} --edit-note note.md"
                  f"\n  reject:  python -m analystdesk.agent resume {run_id} --reject \"reason\"")
    else:
        print(f"FINISHED: {v.get('outcome') or ('out of scope: ' + str(v.get('guard', {}).get('reason')))}")
        if v.get("published"):
            print(v["published"].get("result", ""))
    print(f"tool calls {v.get('tool_calls', 0)}, tokens {v.get('tokens', 0)}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m analystdesk.agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("request"); s.add_argument("--run-id")
    s.add_argument("--team", action="store_true", help="C2 team instead of the C1 single agent")
    s.add_argument("--no-memory", action="store_true")
    r = sub.add_parser("resume"); r.add_argument("run_id")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--approve", action="store_true")
    g.add_argument("--edit-plan", type=Path)
    g.add_argument("--edit-note", type=Path)
    g.add_argument("--reject")
    r.add_argument("--approver", default="analyst")
    sh = sub.add_parser("show"); sh.add_argument("run_id")
    sub.add_parser("graph")
    args = ap.parse_args()

    from langgraph.types import Command
    if args.cmd == "graph":
        from .graph import build_graph
        print(build_graph(_NoModel(), [], None).compile().get_graph().draw_mermaid())
        return
    if args.cmd == "start":
        run_id = args.run_id or uuid.uuid4().hex[:8]
        payload = {"request": args.request, "mode": "c2" if args.team else "c1",
                   "memory_on": not args.no_memory}
        result = asyncio.run(run_until_gate(run_id, payload, _print))
    elif args.cmd == "resume":
        run_id = args.run_id
        if args.approve:
            decision = {"action": "approve", "approver": args.approver}
        elif args.edit_plan:
            decision = {"action": "edit", "plan": json.loads(args.edit_plan.read_text(encoding="utf-8"))}
        elif args.edit_note:
            decision = {"action": "edit", "note": {"body": args.edit_note.read_text(encoding="utf-8")}}
        else:
            decision = {"action": "reject", "reason": args.reject}
        result = asyncio.run(run_until_gate(run_id, Command(resume=decision), _print))
    else:
        run_id = args.run_id
        result = asyncio.run(get_run(run_id))
        for ev in result["values"].get("trace", []):
            print(f"  · {ev['node']}: " + json.dumps({k: v for k, v in ev.items() if k != 'node'})[:300])
    _report(run_id, result)


if __name__ == "__main__":
    main()
