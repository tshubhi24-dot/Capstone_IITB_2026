"""Research-agent panel — run C1 or C2 with both human approval gates.

Flow in the UI:
  1. Analyst enters a request -> Start. The agent checks scope and drafts a plan.
  2. Plan gate: approve, edit the JSON and approve, or cancel before research.
  3. The agent researches with MCP tools; every tool call and result streams
     into the activity log.
  4. Note gate: the draft note, its code check (numbers verified) and buttons
     to approve, edit (re-checked, needs a fresh approval) or reject.
  5. On approval the note is signed and published; it appears under Past notes.
A run id identifies each run: paste it into "Load run" to resume later — even
after restarting the app — because every step is saved in the checkpointer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import uuid

import gradio as gr

EXAMPLES = [
    "Compare Microsoft's and Alphabet's operating margins over fiscal 2022-2024 and what drove the change",
    "Compare JPMorgan and Goldman Sachs pre-tax margins in 2023 and 2024 and their main risk factors",
    "How did NVIDIA's revenue and operating margin change from fiscal 2023 to 2024, and why?",
]

_FACT_TAG = re.compile(r"\[(fact|calc|growth|diff):\s*([^\]]+?)\s*\]")


def _can_start_agent_run(request: str | None, workflow: str | None, running: bool = False) -> bool:
    return not running and workflow in ("c1", "c2") and bool(request and request.strip())


def _has_run_id(run_id: str | None) -> bool:
    return bool(run_id and run_id.strip())


def _can_use_run_actions(run_id: str | None, running: bool = False) -> bool:
    return not running and _has_run_id(run_id)


def _can_add_preference(text: str | None) -> bool:
    return bool(text and text.strip())


async def _delete_memory_item(selection: list | None, confirmed: bool) -> str:
    """'' if nothing was deleted, else what was removed and what was kept."""
    if not confirmed or not selection:
        return ""

    from analystdesk import memory as ltm

    return await ltm.forget(tuple(selection[:2]), selection[2])


def _playbook_button_states(
    lesson_key: str | None, lesson_status: str | None, frozen: bool
) -> tuple[bool, bool, bool, bool]:
    selected = bool(lesson_key)
    pending = selected and lesson_status == "pending"
    return pending and not frozen, pending and not frozen, selected and not frozen, selected and frozen


def _lesson_source_label(lesson: dict) -> str:
    sources = lesson.get("source_cases") or [{
        "source_case": lesson.get("source_case", ""),
        "source_config": lesson.get("source_config", ""),
    }]
    return ", ".join(
        f"{source.get('source_case', '')}/{source.get('source_config', '')}".strip("/")
        for source in sources
        if source.get("source_case") or source.get("source_config")
    )


def _parse_edited_plan(plan_text: str | None, original_plan_text: str | None) -> tuple[dict | None, str]:
    if not original_plan_text:
        return None, "The original plan is unavailable. Reload the plan before editing."

    try:
        plan_data = json.loads(plan_text or "")
    except (json.JSONDecodeError, TypeError):
        return None, "Enter valid JSON before approving the edited plan."
    if not isinstance(plan_data, dict):
        return None, "The plan must be a JSON object."

    try:
        original_data = json.loads(original_plan_text)
        if not isinstance(original_data, dict):
            return None, "The original plan is invalid. Reload the plan before editing."

        from analystdesk.agent.graph import Plan, plan_scope_errors

        edited_plan = Plan(**plan_data).model_dump()
        original_plan = Plan(**original_data).model_dump()
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        return None, f"Plan validation failed: {error}"
    if errors := plan_scope_errors(edited_plan):
        return None, "Plan validation failed: " + " ".join(errors)

    if edited_plan == original_plan:
        return None, "No plan changes detected. Make a valid change before approving."
    return edited_plan, "Valid plan changes detected. You can approve the edited plan."


# ── formatting ────────────────────────────────────────────────────────────────

def _args_short(args: dict) -> str:
    parts = []
    for k, v in (args or {}).items():
        if k == "code":
            v = (v.strip().splitlines() or [""])[0][:60] + ("…" if len(v) > 60 else "")
        elif k == "data":
            v = "{…}"
        parts.append(f"{k}={v!r}" if isinstance(v, str) else f"{k}={v}")
    return ", ".join(parts)[:160]


def _event_line(ev: dict) -> str:
    n = ev.get("node")
    if n == "input_guard":
        return (f"✅ **Scope check** — companies {', '.join(ev['companies'])}" if ev["ok"]
                else f"⛔ **Out of scope** — {ev['reason']}")
    if n == "plan":
        mem = ev.get("memory_used") or {}
        used = []
        if mem.get("preferences"):
            used.append(f"{mem['preferences']} preference(s)")
        if mem.get("previous_notes"):
            used.append("previous notes on " + ", ".join(mem["previous_notes"]))
        suffix = f" · 🧠 memory used: {'; '.join(used)}" if used else ""
        if ev.get("lessons_used"):
            suffix += f" · 📘 {len(ev['lessons_used'])} playbook lesson(s) applied"
        return ("🔁 **Revised plan drafted**" if ev.get("replan")
                else "📝 **Plan drafted** by the research lead") + suffix
    if n == "review_plan":
        if ev["action"] == "cancel":
            return "🚫 **Plan cancelled** — research did not start"
        if ev["action"] == "confirm_years":
            years = ", ".join(f"FY{year}" for year in ev["year_confirmation"]["fiscal_years"])
            return f"👤 **Fiscal years confirmed** — {years} by the analyst"
        return f"👤 **Plan {'edited and approved' if ev['action'] == 'edit' else 'approved'}** by the analyst"
    if n == "research":
        calls = ev.get("tool_calls") or []
        if not calls:
            return "🧠 **Agent** has enough evidence — moving to writing"
        # older runs stored just tool names; newer ones name + args
        return "🧠 **Agent calls** " + "; ".join(
            f"`{c}`" if isinstance(c, str) else f"`{c['name']}`({_args_short(c.get('args', {}))})"
            for c in calls)
    if n == "tool_result":
        mark = "✔" if ev["ok"] else "✖"
        preview = ev["preview"].replace("\n", " ")[:140]
        return f"&nbsp;&nbsp;&nbsp;{mark} `{ev['tool']}` → {preview}"
    if n == "tool":   # hook event from a C2 specialist
        mark = "✔" if ev["ok"] else ("⛔" if ev.get("denied") else "✖")
        err = "" if ev["ok"] else f" **{ev.get('error')}**"
        return (f"&nbsp;&nbsp;&nbsp;{mark} 👥 `{ev['agent']}` → `{ev['tool']}`"
                f"({_args_short(ev.get('args', {}))}){err} · {ev.get('ms', 0)} ms")
    if n == "handoff":
        who = ev["agent"] + (f"[{ev['company']}]" if ev.get("company") else "")
        return (f"📨 **Hand-off from {who}**: {ev['passages']} passages, {ev['facts']} facts, "
                f"{ev['tool_calls']} tool calls, confidence **{ev['confidence']}**"
                + (f", errors {', '.join(ev['errors'])}" if ev.get("errors") else ""))
    if n == "gather":
        return f"🧩 **Research lead** gathered {ev['handoffs']} hand-offs"
    if n == "replan":
        return f"🔁 **Replanning** — a tool result contradicted the plan: {ev['reason'][:160]}"
    if n == "write":
        return f"✍️ **Writer** drafted the note" + (f" (revision {ev['revision']})" if ev["revision"] else "")
    if n in ("check", "critic"):
        line = (f"🔎 **{'Compliance critic' if n == 'critic' else 'Code check'}** — "
                f"{ev['verified']}/{ev['total']} numbers verified")
        claims = ev.get("claims") or {}
        if claims.get("checked"):
            line += (f"; judge ({claims.get('model', '').split('/')[-1]}) found "
                     f"{claims.get('supported')}/{claims['checked']} claims supported")
        return line + ("" if ev["ok"] else f", {len(ev['issues'])} issue(s) sent back")
    if n == "review_note":
        return f"👤 **Note {ev['action']}{'d' if ev['action'] != 'edit' else 'ed'}** by the analyst"
    if n == "publish":
        if ev["ok"]:
            return (f"📤 **Published** to the research portal"
                    + (f" as note #{ev['note_id']}" if ev.get("note_id") else "")
                    + (" · 🧠 remembered for next time" if ev.get("remembered") else ""))
        return "❌ **Publish refused** by the portal" + (f": {ev['error']}" if ev.get("error") else "")
    if n == "status_corrected":
        return f"🛠 **Status corrected** to published (note #{ev.get('note_id')}): {ev.get('reason', '')}"
    return f"· {n}"



def _note_display(body: str) -> str:
    """Note with long [fact: ...] / [calc: ...] tags turned into numbered sources."""
    sources: list[str] = []

    def repl(m):
        sources.append(f"**{m.group(1)}** `{m.group(2)}`")
        return f"<sup>[{len(sources)}]</sup>"

    text = _FACT_TAG.sub(repl, body)
    if sources:
        text += ("\n\n---\n**Sources** (XBRL facts; computed in code: `calc` = A / B, "
                 "`growth` = A / B − 1, `diff` = margin change in percentage points)\n\n")
        text += "\n".join(f"{i}. {s}" for i, s in enumerate(sources, 1))
    return text


def _check_display(c: dict) -> str:
    head = (f"### {'✅' if c['ok'] else '⚠️'} Code check: {c['verified']}/{c['total']} numbers "
            f"verified ({c['verified_share']}%)")
    claims = c.get("claims") or {}
    if claims.get("checked"):
        reviewed = claims.get("reviewed", claims["checked"])
        head += (f"\n**Judge** ({claims.get('model')}): {claims.get('supported')}/{claims['checked']} "
                 "cited claims supported by their passages")
        if reviewed < claims["checked"]:
            head += f" · **review incomplete**: {claims['checked'] - reviewed} claim(s) got no verdict"
    elif claims.get("error"):
        head += f"\n**Judge**: {claims['error']}"
    if claims.get("uncited"):
        head += (f"\n{claims['uncited']} substantive line(s) cite no passage, so the judge could not "
                 "check them: read them yourself before approving.")
    if c["issues"]:
        head += ("\n\n**Approval unavailable** until these are fixed: edit the note (it is re-checked) "
                 "or reject it.\n" + "\n".join(f"- {i}" for i in c["issues"]))
    else:
        head += "\n\nReady for your review: approving publishes exactly this note."
    return head


def _past_notes() -> list[list]:
    from analystdesk.servers.portal import _db_path
    path = _db_path()
    if not path.exists():
        return []
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT id, published_at, approver, tickers, title FROM notes "
                           "ORDER BY id DESC LIMIT 50").fetchall()
    finally:
        con.close()
    return [[r[0], r[1], r[2], ", ".join(json.loads(r[3])), r[4]] for r in rows]


# ── team board ────────────────────────────────────────────────────────────────

def _board(events: list[dict], mode: str = "c2") -> str:
    """One row per agent: status, tool calls, last action — built from the events."""
    plan = next((e["plan"] for e in reversed(events) if e.get("node") == "plan" and e.get("plan")), None)
    approved = any(e.get("node") == "review_plan" for e in events)
    rows: dict[str, dict] = {}

    def row(key, role, scope=""):
        return rows.setdefault(key, {"role": role, "scope": scope, "status": "· idle",
                                     "calls": 0, "last": "", "detail": ""})

    lead = row("lead", "🧭 Research lead", "plan · fan-out · gather")
    if plan:
        lead["status"] = "✅ planned" if approved else "⏸ plan waiting for you"
        lead["detail"] = f"{', '.join(plan['companies'])} · FY{min(plan['fiscal_years'])}–{max(plan['fiscal_years'])}"
    if mode == "c2":
        companies = plan["companies"] if plan else []
        for t in companies:
            row(f"researcher/{t}", "🔎 Researcher", t)
        row("quant", "🧮 Quant", ", ".join(companies) or "all")
        for t in companies:
            row(f"risk_diff/{t}", "⚖️ Risk-diff", t)
        if approved:
            for k in rows:
                if k != "lead":
                    rows[k]["status"] = "⏳ queued"
    else:
        single = row("single_agent", "🤖 Single agent (C1)", "all research tools")
        if approved:
            single["status"] = "⏳ queued"
    row("writer", "✍️ Writer", "drafts from evidence")
    row("critic", "🛡️ Compliance critic" if mode == "c2" else "🔎 Code check", "numbers + claims")
    row("gate", "👤 You (note gate)", "approve · edit · reject")
    row("publisher", "📤 Publisher", "publish_note only")

    for e in events:
        n = e.get("node")
        if n == "tool":   # live hook event
            r = rows.get(e["agent"]) or row(e["agent"], e["agent"])
            r["calls"] += 1
            r["status"] = "🔄 working"
            mark = "✔" if e["ok"] else ("⛔" if e.get("denied") else "✖")
            r["last"] = f"{mark} {e['tool']}" + ("" if e["ok"] else f" {e.get('error')}")
        elif n == "handoff":
            key = f"{e['agent']}/{e['company']}" if e.get("company") else e["agent"]
            r = rows.get(key) or row(key, e["agent"], e.get("company") or "")
            r["calls"] = e["tool_calls"]
            if e.get("tools") and not r["last"]:
                t = e["tools"][-1]
                r["last"] = ("✔ " if t["ok"] else "✖ ") + t["tool"]
            r["status"] = "✅ handed off" if not e.get("errors") else "⚠️ handed off"
            r["detail"] = (f"{e['passages']} passages · {e['facts']} facts · confidence {e['confidence']}"
                           + (f" · {', '.join(e['errors'])}" if e.get("errors") else ""))
        elif n == "research":
            r = row("single_agent", "🤖 Single agent (C1)")
            r["status"] = "🔄 working"
            calls = e.get("tool_calls") or []
            r["calls"] += len(calls)
            if calls:
                c = calls[-1]
                r["last"] = c if isinstance(c, str) else c["name"]
            else:
                r["status"] = "✅ done"
        elif n == "gather":
            lead["status"] = f"✅ gathered {e['handoffs']} hand-offs"
        elif n == "replan":
            lead["status"] = "🔁 replanning"
        elif n == "write":
            rows["writer"]["status"] = "✅ drafted" + (f" (revision {e['revision']})" if e.get("revision") else "")
            rows["critic"]["status"] = "🔄 checking"
        elif n in ("check", "critic"):
            c = rows["critic"]
            c["status"] = "✅ passed" if e["ok"] else f"⚠️ {len(e['issues'])} issue(s)"
            claims = e.get("claims") or {}
            c["detail"] = f"{e['verified']}/{e['total']} numbers verified" + (
                f" · judge {claims.get('supported')}/{claims['checked']} claims" if claims.get("checked") else "")
            rows["gate"]["status"] = "⏸ waiting for you"
        elif n == "review_note":
            rows["gate"]["status"] = {"approve": "✅ approved", "edit": "✏️ edited", "reject": "🛑 rejected"}.get(
                e["action"], e["action"])
        elif n == "publish":
            rows["publisher"]["status"] = (f"✅ published #{e.get('note_id')}" if e["ok"] else "❌ refused")

    lines = ["| Agent | Scope | Status | Tool calls | Last action | Details |", "|---|---|---|---|---|---|"]
    for r in rows.values():
        lines.append(f"| {r['role']} | {r['scope']} | {r['status']} | {r['calls'] or ''} | {r['last']} | {r['detail']} |")
    return "\n".join(lines)


# ── driving the agent ─────────────────────────────────────────────────────────

async def _drive(run_id: str, payload):
    """Yield ("event", raw event) while the agent runs, then ("done", result)."""
    from analystdesk.agent.runtime import run_until_gate
    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(ev):
        await queue.put(ev)

    task = asyncio.create_task(run_until_gate(run_id, payload, on_event, transport="auto"))
    try:
        while not (task.done() and queue.empty()):
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=0.5)
                yield "event", ev
            except asyncio.TimeoutError:
                continue
        yield "done", task.result()
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


def _view(run_id: str, result: dict, log: list[str], events: list[dict] | None = None):
    """All tab outputs for a run state."""
    v = result.get("values", {})
    board = _board(events if events is not None else v.get("trace", []), v.get("mode", "c1"))
    gate = result["interrupts"][0] if result.get("interrupts") else None
    usage = f"tool calls **{v.get('tool_calls', 0)}** · tokens **{v.get('tokens', 0):,}**"
    if v.get("memory_on") is False:
        usage += " · 🧠 saved memory **off**: no preferences, past notes or past-note tool in this run"

    plan_md, plan_json, note_md, check_md, note_body = "", "", "", "", ""
    plan_edit_feedback = ""
    original_plan_json = ""
    show_plan = show_note = False
    requires_year_confirmation = False
    if gate and gate["gate"] == "plan":
        requires_year_confirmation = gate.get("requires_year_confirmation")
        if requires_year_confirmation is None:
            from analystdesk.agent.graph import year_confirmation_required
            requires_year_confirmation = year_confirmation_required(v.get("request", ""))
        next_step = ("confirm the fiscal years, edit the plan, or cancel"
                     if requires_year_confirmation else "approve, edit, or cancel the plan")
        status = f"### ⏸ Waiting for you: {next_step}\nRun `{run_id}` · {usage}"
        p = gate["plan"]
        plan_md = (f"**Companies:** {', '.join(p['companies'])} · **Fiscal years:** "
                   f"{', '.join(map(str, p['fiscal_years']))}\n\n**Sub-questions**\n"
                   + "\n".join(f"1. {q}" for q in p["sub_questions"])
                   + "\n\n**Outline:** " + " → ".join(p["outline"])
                   + ("\n\n**How your request was read** (edit the plan to change it)\n"
                      + "\n".join(f"- {a}" for a in gate.get("assumptions", []))
                      if gate.get("assumptions") else ""))
        if requires_year_confirmation:
            plan_md += "\n\n**Confirm the fiscal-year range below before research starts.**"
        plan_json = json.dumps(p, indent=2)
        original_plan_json = plan_json
        plan_edit_feedback = "Make a valid change to the JSON plan to enable this button."
        show_plan = True
    elif gate and gate["gate"] == "note":
        if gate.get("check", {}).get("ok", False):
            status = f"### ⏸ Waiting for you: approve, edit or reject the note\nRun `{run_id}` · {usage}"
        else:
            status = (f"### ⛔ Note failed verification. Edit and re-check it, or reject it. "
                      f"Approval is blocked.\nRun `{run_id}` · {usage}")
        note_md = f"# {gate['note']['title']}\n\n" + _note_display(gate["note"]["body"])
        check_md = _check_display(gate["check"])
        note_body = gate["note"]["body"]
        show_note = True
    else:
        outcome = v.get("outcome")
        pub = v.get("published") or {}
        if outcome == "published":
            status = f"### ✅ Published as note #{pub.get('note_id')}\nRun `{run_id}` · {usage}"
            if pub.get("memory_error"):
                status += ("\n\n⚠️ The note is saved in the portal, but the memory update failed "
                           f"({pub['memory_error']}). Do not publish again; run scripts/backfill_memory.py.")
        elif outcome == "publish_unconfirmed":
            status = (f"### ❓ Save outcome unknown\nThe portal may or may not have saved this note "
                      f"({pub.get('error') or 'no note id returned'}). Check the portal's Recent notes "
                      f"before trying again.\nRun `{run_id}` · {usage}")
        elif outcome == "publish_failed":
            status = f"### ✖ Not published: the portal refused the note\nRun `{run_id}` · {usage}"
        elif outcome == "rejected":
            status = f"### 🛑 Rejected by the analyst\nRun `{run_id}` · {usage}"
        elif outcome == "cancelled":
            status = f"### 🚫 Plan cancelled — research did not start\nRun `{run_id}` · {usage}"
        elif v.get("guard") and not v["guard"].get("ok"):
            status = f"### ⛔ Out of scope\n{v['guard']['reason']}"
        elif not v:
            status = f"### No run found with id `{run_id}`"
        else:
            status = f"### Run `{run_id}`: {outcome or 'finished'} · {usage}"
        if v.get("draft"):
            note_md = f"# {v['draft']['title']}\n\n" + _note_display(v["draft"]["body"])
            if v.get("check"):
                check_md = _check_display(v["check"])

    return (run_id, status, "\n\n".join(log) or "_No activity yet._",
            gr.update(value=plan_md), gr.update(value=plan_json), gr.update(visible=show_plan),
            gr.update(value=note_md), gr.update(value=check_md), gr.update(value=note_body),
            gr.update(visible=show_note), _past_notes(), board,
            gr.update(value=plan_edit_feedback), original_plan_json,
            gr.update(interactive=False),
            gr.update(interactive=bool(gate and gate.get("gate") == "note"
                                       and gate.get("check", {}).get("ok", False))),
            gr.update(visible=requires_year_confirmation, value=False),
            requires_year_confirmation)


def _log_from_trace(values: dict) -> list[str]:
    lines = []
    for ev in values.get("trace", []):
        if ev.get("node") == "handoff":   # replay the agent's tool calls saved with its hand-off
            who = f"{ev['agent']}/{ev['company']}" if ev.get("company") else ev["agent"]
            lines += [_event_line({"node": "tool", "agent": who, **t}) for t in ev.get("tools", [])]
        lines.append(_event_line(ev))
    return lines


# ── the panel ─────────────────────────────────────────────────────────────────

def build_agent_panel(workflow_mode):
    with gr.Column():
        gr.Markdown(
            "The selected agent workflow plans, waits for your approval, researches with "
            "tools (every call is shown live), writes a note whose numbers are inserted and checked "
            "by code, and publishes **only after you approve the exact note**. **C1** is one agent "
            "with all tools; **C2** is a team of parallel researchers, a quant, risk-diff agents, "
            "and a compliance critic. Memory is used automatically for your own coverage."
        )
        with gr.Row():
            request = gr.Textbox(label="Research request", scale=5,
                                 placeholder="e.g. Compare Microsoft and Alphabet operating margins 2022-2024")
            start_btn = gr.Button("▶ Start", variant="primary", scale=1, interactive=False)
            start_busy = gr.State(False)
        gr.Examples([[e] for e in EXAMPLES], inputs=request)
        with gr.Row():
            run_id = gr.Textbox(label="Run id (paste one to resume)", scale=2)
            load_btn = gr.Button("⟳ Load run", scale=1, interactive=False)
            approver = gr.Textbox(label="Your name (approvals, preferences)", value="analyst", scale=2)
            rerun_btn = gr.Button("↻ Re-run this request without memory", scale=2, interactive=False)
        with gr.Accordion("📂 Your runs: click a row to load it", open=True):
            runs_table = gr.Dataframe(
                headers=["run id", "agents", "updated (UTC)", "status", "numbers verified", "tool calls",
                         "request"],
                interactive=False, wrap=True, max_height=260)
            refresh_runs_btn = gr.Button("↻ Refresh list", size="sm")
        status = gr.Markdown("### Enter a request and press Start, or pick a run above")

        with gr.Group(visible=False) as plan_box:
            gr.Markdown("## 📝 Plan — your approval is needed")
            plan_md = gr.Markdown()
            confirm_years_checkbox = gr.Checkbox(
                label="I confirm the fiscal years shown above and want research to proceed.",
                visible=False,
                value=False,
            )
            year_confirmation_required = gr.State(False)
            with gr.Accordion("✏️ Edit the plan (JSON)", open=False):
                plan_json = gr.Code(language="json", label="Plan")
                plan_edit_feedback = gr.Markdown()
                plan_json_baseline = gr.State("")
                edit_plan_btn = gr.Button("Approve the edited plan", interactive=False)
            with gr.Row():
                approve_plan_btn = gr.Button("✅ Approve plan and start research", variant="primary")
                cancel_plan_btn = gr.Button("🚫 Cancel plan", variant="stop")

        with gr.Group(visible=False) as note_box:
            gr.Markdown("## 🧾 Draft note — your approval is needed")
            check_md = gr.Markdown()
            note_md = gr.Markdown()
            with gr.Accordion("✏️ Edit the note (an edit is re-checked and needs a fresh approval)",
                              open=False):
                note_body = gr.Textbox(lines=18, label="Note body (keep the [fact: …] tags)")
                edit_note_btn = gr.Button("Save edit and re-check")
            with gr.Row():
                approve_note_btn = gr.Button("✅ Approve and publish", variant="primary")
                reject_reason = gr.Textbox(label="Reason for rejecting", scale=2)
                reject_btn = gr.Button("🛑 Reject", variant="stop")

        with gr.Accordion("👥 Team board: who is doing what (live)", open=True):
            board = gr.Markdown("_Start a run to see the agents._")

        with gr.Accordion("🔧 Agent activity: steps, tool calls and results (live)", open=True):
            activity = gr.Markdown("_No activity yet._")

        with gr.Accordion("🧠 Memory: what the desk remembers (view, add, delete)", open=False):
            gr.Markdown("Saved only from **your** actions: preferences you add here, and notes you "
                        "approved and published. Click a row, then delete it. Policy: "
                        "`docs/memory_policy.md`.")
            with gr.Row():
                new_pref = gr.Textbox(label="Add a standing preference", scale=4,
                                      placeholder="e.g. Always include a peer comparison table")
                add_pref_btn = gr.Button("Add", scale=1, interactive=False)
            with gr.Row():
                watchlist_box = gr.Textbox(
                    label="🔒 Private watchlist (tickers, comma-separated)", scale=4,
                    info="Only the planner sees it. It never goes into a tool call, a search or a note "
                         "unless you approve a plan that covers the company.")
                save_watchlist_btn = gr.Button("Save watchlist", scale=1)
            watchlist_status = gr.Markdown()
            prefs_table = gr.Dataframe(headers=["key", "preference", "added (UTC)"],
                                       interactive=False, wrap=True)
            coverage_table = gr.Dataframe(headers=["ticker", "notes", "last published"],
                                          interactive=False, label="Coverage list")
            notes_mem_table = gr.Dataframe(headers=["ticker", "key", "note", "published", "title", "figures"],
                                           interactive=False, wrap=True, label="Past-note memory")
            selected_mem = gr.State(None)
            with gr.Row():
                selected_label = gr.Markdown("_Nothing selected_")
                delete_mem_btn = gr.Button(
                    "🗑 Delete selected memory", variant="stop", size="sm", interactive=False
                )
            delete_status = gr.Markdown()
            with gr.Group(visible=False, elem_id="memory-delete-confirmation") as delete_confirmation:
                gr.Markdown("**Delete this memory?** This action cannot be undone.")
                with gr.Row():
                    confirm_delete_btn = gr.Button("Confirm deletion", variant="stop")
                    cancel_delete_btn = gr.Button("Cancel")

        with gr.Accordion("📘 Playbook: lessons learned from development runs (review here)", open=False):
            gr.Markdown(
                "The reflection step (`scripts/reflect.py`) turns failures on **development** cases into "
                "short lessons. **None is used until you approve it.** Approved lessons are given to the "
                "agents only when relevant to the request. **Freeze** the playbook before the held-out run.")
            playbook_status = gr.Markdown()
            pending_table = gr.Dataframe(headers=["key", "when", "do", "tags", "from case", "issue that triggered it"],
                                         interactive=False, wrap=True, label="Pending your review")
            selected_lesson = gr.State(None)
            selected_lesson_status = gr.State(None)
            playbook_frozen = gr.State(False)
            with gr.Row():
                selected_lesson_md = gr.Markdown("_Click a pending lesson to select it_")
                lesson_reason = gr.Textbox(label="Reason (required to reject)", scale=2)
            with gr.Row():
                approve_lesson_btn = gr.Button("✅ Approve lesson", variant="primary", interactive=False)
                reject_lesson_btn = gr.Button("🛑 Reject lesson", variant="stop", interactive=False)
                freeze_btn = gr.Button("🧊 Freeze playbook", interactive=False)
                unfreeze_btn = gr.Button("Unfreeze", interactive=False)
            approved_table = gr.Dataframe(headers=["key", "when", "do", "tags", "approved by"],
                                          interactive=False, wrap=True, label="Approved (used by agents)")
            rejected_table = gr.Dataframe(headers=["key", "when", "do", "rejected by", "reason"],
                                          interactive=False, wrap=True, label="Rejected (kept as evidence)")

        with gr.Accordion("📚 Published notes (research portal)", open=False):
            past = gr.Dataframe(headers=["id", "published", "approver", "tickers", "title"],
                                value=_past_notes, wrap=True)

        outputs = [run_id, status, activity, plan_md, plan_json, plan_box,
                   note_md, check_md, note_body, note_box, past, board,
                   plan_edit_feedback, plan_json_baseline, edit_plan_btn, approve_note_btn,
                   confirm_years_checkbox, year_confirmation_required]

        def start_control_updates(req, mode, running, current_run_id):
            return (
                gr.update(interactive=_can_start_agent_run(req, mode, running)),
                running,
                gr.update(interactive=not running),
                gr.update(interactive=not running),
                gr.update(interactive=_can_use_run_actions(current_run_id, running)),
                gr.update(interactive=_can_use_run_actions(current_run_id, running)),
            )

        async def run_step(rid, payload, prior_log, prior_events=None, mode="c1", request_text=""):
            log, events = list(prior_log), list(prior_events or [])
            yield (
                rid, "### ⏳ Agents working…", "\n\n".join(log) or "_Starting…_",
                gr.update(), gr.update(), gr.update(visible=False),
                gr.update(), gr.update(), gr.update(), gr.update(visible=False), gr.update(),
                _board(events, mode), gr.update(value=""), gr.update(),
                gr.update(interactive=False), gr.update(interactive=False),
                gr.update(visible=False, value=False), False,
                *start_control_updates(request_text, mode, True, rid),
            )
            try:
                async for kind, item in _drive(rid, payload):
                    if kind == "event":
                        events.append(item)
                        log.append(_event_line(item))
                        yield (
                            rid, "### ⏳ Agents working…", "\n\n".join(log),
                            gr.update(), gr.update(), gr.update(visible=False),
                            gr.update(), gr.update(), gr.update(), gr.update(visible=False), gr.update(),
                            _board(events, mode), gr.update(value=""), gr.update(),
                            gr.update(interactive=False), gr.update(interactive=False),
                            gr.update(visible=False, value=False), False,
                            *start_control_updates(request_text, mode, True, rid),
                        )
                    else:
                        yield (*_view(rid, item, log, events),
                               *start_control_updates(request_text, mode, False, rid))
            except Exception:
                logging.getLogger(__name__).exception("Agent run failed")
                failure_updates = [gr.update() for _ in outputs]
                failure_updates[1] = "### Run failed; check the server logs for details"
                failure_updates[5] = gr.update(visible=False)
                failure_updates[9] = gr.update(visible=False)
                failure_updates[12] = gr.update(value="")
                failure_updates[14] = gr.update(interactive=False)
                failure_updates[15] = gr.update(interactive=False)
                failure_updates[16] = gr.update(visible=False, value=False)
                failure_updates[17] = False
                yield (
                    *failure_updates,
                    *start_control_updates(request_text, mode, False, rid),
                )

        async def memory_tables(name):
            from analystdesk import memory as ltm
            analyst = (name or "analyst").strip()
            prefs = [[p["key"], p["text"], p["added_at"][:16].replace("T", " ")]
                     for p in await ltm.preferences(analyst)]
            cov = [[c["ticker"], ", ".join(f"#{n}" for n in c["notes"]), c["last_published"][:16].replace("T", " ")]
                   for c in await ltm.coverage(analyst)]
            notes = [[n["ticker"], n["key"], n["note_id"], n["published_at"][:10], n["title"],
                      ", ".join(f"{k} {v['value']:g}{'%' if v['unit'] == '%' else 'M'}"
                                for k, v in sorted(n["figures"].items()))]
                     for n in await ltm.all_note_memories()]
            return prefs, cov, notes

        async def on_add_pref(name, text):
            if not _can_add_preference(text):
                yield ("", *await memory_tables(name), gr.update(interactive=False))
                return

            yield (gr.update(), gr.update(), gr.update(), gr.update(),
                   gr.update(interactive=False))
            from analystdesk import memory as ltm
            await ltm.add_preference((name or "analyst").strip(), text)
            yield ("", *await memory_tables(name), gr.update(interactive=False))

        async def watchlist_text(name):
            from analystdesk import memory as ltm
            return ", ".join(await ltm.watchlist((name or "analyst").strip()))

        async def on_save_watchlist(name, text):
            from analystdesk import memory as ltm
            asked = [t for t in re.split(r"[,\s]+", text or "") if t]
            kept = await ltm.set_watchlist((name or "analyst").strip(), asked)
            dropped = sorted({t.upper() for t in asked} - set(kept))
            status = f"_Saved: {', '.join(kept)}._" if kept else "_Watchlist cleared._"
            if dropped:
                status += f" _Not covered, so not kept: {', '.join(dropped)}._"
            return ", ".join(kept), status

        def update_add_preference_button(text):
            return gr.update(interactive=_can_add_preference(text))

        def on_pick_pref(table, name, evt: gr.SelectData):
            row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
            key = table.iloc[row, 0]
            return (["preferences", (name or "analyst").strip(), key],
                    f"Selected preference: **{table.iloc[row, 1]}**",
                    gr.update(interactive=True))

        def on_pick_note_mem(table, evt: gr.SelectData):
            row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
            return (["notes", table.iloc[row, 0], table.iloc[row, 1]],
                    f"Selected memory of note #{table.iloc[row, 2]} for {table.iloc[row, 0]}",
                    gr.update(interactive=True))

        def request_memory_deletion(sel):
            if not sel:
                return gr.update(visible=False), gr.update(interactive=False), "_Select a memory row first._"
            return gr.update(visible=True), gr.update(interactive=False), ""

        async def on_delete_mem(sel, name):
            deleted = await _delete_memory_item(sel, confirmed=True)
            if not deleted:
                return (
                    sel, gr.update(visible=False), gr.update(interactive=bool(sel)),
                    "_Select a memory row first._", *await memory_tables(name),
                )
            return (
                None, gr.update(visible=False), gr.update(interactive=False),
                f"_Deleted. {deleted}_", *await memory_tables(name),
            )

        def cancel_memory_deletion(sel):
            return (
                gr.update(visible=False), gr.update(interactive=bool(sel)),
                "_Deletion canceled._",
            )

        async def on_start(req, name, agents, busy=False, current_run_id="", memory_on=True):
            def response(status_text, enabled, running, inputs_enabled):
                updates = [gr.update() for _ in outputs]
                updates[1] = status_text
                return (
                    *updates,
                    gr.update(interactive=enabled),
                    running,
                    gr.update(interactive=inputs_enabled),
                    gr.update(interactive=inputs_enabled),
                    gr.update(interactive=_has_run_id(current_run_id)),
                    gr.update(interactive=_has_run_id(current_run_id)),
                )

            if busy:
                yield response(
                    "### A research run is already in progress",
                    False,
                    True,
                    False,
                )
                return
            if not req or not req.strip():
                yield response(
                    "### Please enter a request",
                    _can_start_agent_run(req, agents),
                    False,
                    True,
                )
                return
            if agents not in ("c1", "c2"):
                yield response(
                    "### Choose C1 or C2 to start agent research",
                    False,
                    False,
                    True,
                )
                return
            payload = {"request": req, "analyst": (name or "analyst").strip(), "memory_on": memory_on,
                       "mode": agents}
            async for out in run_step(
                uuid.uuid4().hex[:8], payload, [], [], payload["mode"], req
            ):
                yield out

        async def resume_with(rid, decision):
            from langgraph.types import Command
            from analystdesk.agent.runtime import get_run
            values = (await get_run(rid))["values"]
            async for out in run_step(rid, Command(resume=decision), _log_from_trace(values),
                                      values.get("trace", []), values.get("mode", "c1"),
                                      values.get("request", "")):
                yield out

        async def on_rerun_without_memory(rid, name, req, agents, busy):
            """Same request and agents as the loaded run, as a new run with memory off."""
            if busy:
                yield run_action_response(
                    "### A research run is already in progress", req, agents, rid, True
                )
                return

            yield run_action_response(
                "### Loading run for a memory-off rerun…", req, agents, rid, True
            )
            from analystdesk.agent.runtime import get_run
            try:
                v = (await get_run((rid or "").strip()))["values"]
            except Exception:
                logging.getLogger(__name__).exception("Unable to load run for memory-off rerun")
                yield run_action_response(
                    "### Unable to load run; check the server logs for details",
                    req, agents, rid, False,
                )
                return
            if not v.get("request"):
                yield run_action_response(
                    "### Load a run first, then re-run it without memory",
                    req, agents, rid, False,
                )
                return
            async for out in on_start(
                v["request"], name, v.get("mode", "c1"), busy=False,
                current_run_id=rid, memory_on=False
            ):
                yield out

        async def on_approve_plan(rid, confirm_years, confirmation_required, req, agents, busy):
            if confirmation_required and not confirm_years:
                response = run_action_response(
                    "### Confirm the fiscal-year range, edit the plan, or cancel before research starts.",
                    req, agents, rid, busy,
                )
                response = list(response)
                response[12] = gr.update(value="Fiscal-year confirmation is required to continue.")
                yield tuple(response)
                return
            async for out in resume_with(rid, {"action": "approve", "confirm_years": bool(confirm_years)}):
                yield out

        async def on_cancel_plan(rid):
            async for out in resume_with(rid, {"action": "cancel"}):
                yield out

        def update_plan_edit_button(text, original_plan):
            edited_plan, feedback = _parse_edited_plan(text, original_plan)
            return gr.update(interactive=edited_plan is not None), feedback

        async def on_edit_plan(rid, text, req, agents, busy, original_plan,
                               confirm_years, confirmation_required):
            if confirmation_required and not confirm_years:
                response = run_action_response(
                    "### Confirm the fiscal-year range before approving the edited plan.",
                    req, agents, rid, busy,
                )
                response = list(response)
                response[12] = gr.update(value="Fiscal-year confirmation is required to continue.")
                yield tuple(response)
                return
            plan, feedback = _parse_edited_plan(text, original_plan)
            if plan is None:
                updates = [gr.update() for _ in outputs]
                updates[1] = "### Edited plan was not submitted"
                updates[-3] = gr.update(value=feedback)
                updates[-1] = gr.update(interactive=False)
                yield (*updates, *start_control_updates(req, agents, busy, rid))
                return
            async for out in resume_with(
                rid, {"action": "edit", "plan": plan, "confirm_years": bool(confirm_years)}
            ):
                yield out

        async def on_approve_note(rid, name):
            async for out in resume_with(rid, {"action": "approve", "approver": name or "analyst"}):
                yield out

        async def on_edit_note(rid, body):
            async for out in resume_with(rid, {"action": "edit", "note": {"body": body}}):
                yield out

        async def on_reject(rid, reason):
            async for out in resume_with(rid, {"action": "reject", "reason": reason or "no reason given"}):
                yield out

        def run_action_response(status_text, req, agents, rid, running):
            updates = [gr.update() for _ in outputs]
            updates[1] = status_text
            if running:
                updates[-2] = gr.update(interactive=False)
                updates[-1] = gr.update(interactive=False)
            return (*updates, *start_control_updates(req, agents, running, rid))

        async def on_load(rid, req, agents, busy):
            from analystdesk.agent.runtime import get_run
            rid = (rid or "").strip()
            if busy:
                yield run_action_response(
                    "### A research run is already in progress", req, agents, rid, True
                )
                return

            yield run_action_response("### Loading run…", req, agents, rid, True)
            try:
                result = await get_run(rid)
            except Exception:
                logging.getLogger(__name__).exception("Unable to load run")
                yield run_action_response(
                    "### Unable to load run; check the server logs for details",
                    req, agents, rid, False,
                )
                return
            yield (*_view(rid, result, _log_from_trace(result["values"])),
                   *start_control_updates(req, agents, False, rid))

        async def refresh_runs():
            from analystdesk.agent.runtime import list_runs
            return [[r["run_id"], r["mode"], r["updated"], r["status"], r["check"], r["tool_calls"], r["request"]]
                    for r in await list_runs()]

        async def on_pick_run(table, evt: gr.SelectData, req, agents, busy):
            row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
            rid = table.iloc[row, 0] if hasattr(table, "iloc") else table[row][0]
            async for out in on_load(str(rid), req, agents, busy):
                yield out

        start_outputs = [*outputs, start_btn, start_busy, request, workflow_mode, load_btn, rerun_btn]
        start_inputs = [request, approver, workflow_mode, start_busy, run_id]

        def refresh_after(event):
            (event.then(refresh_runs, None, runs_table)
             .then(memory_tables, [approver], [prefs_table, coverage_table, notes_mem_table]))

        for trigger in (start_btn.click, request.submit):
            refresh_after(trigger(
                on_start,
                start_inputs,
                start_outputs,
                concurrency_id="agent-start",
                concurrency_limit=1,
                trigger_mode="once",
            ))
        refresh_after(rerun_btn.click(
            on_rerun_without_memory,
            [run_id, approver, request, workflow_mode, start_busy],
            start_outputs,
            concurrency_id="agent-start",
            concurrency_limit=1,
            trigger_mode="once",
        ))

        def update_start_button(req, agents, busy):
            return gr.update(interactive=_can_start_agent_run(req, agents, busy))

        def update_run_actions(rid, busy):
            enabled = _can_use_run_actions(rid, busy)
            return gr.update(interactive=enabled), gr.update(interactive=enabled)

        run_id.input(update_run_actions, [run_id, start_busy], [load_btn, rerun_btn])
        run_id.change(update_run_actions, [run_id, start_busy], [load_btn, rerun_btn])
        plan_json.input(
            update_plan_edit_button,
            [plan_json, plan_json_baseline],
            [edit_plan_btn, plan_edit_feedback],
        )
        plan_json.change(
            update_plan_edit_button,
            [plan_json, plan_json_baseline],
            [edit_plan_btn, plan_edit_feedback],
        )
        request.input(
            update_start_button,
            [request, workflow_mode, start_busy],
            start_btn,
        )
        workflow_mode.change(
            update_start_button,
            [request, workflow_mode, start_busy],
            start_btn,
        )

        # every action refreshes the runs list afterwards
        for trigger, fn, inputs in (
                (approve_plan_btn.click, on_approve_plan,
                 [run_id, confirm_years_checkbox, year_confirmation_required,
                  request, workflow_mode, start_busy]),
                (cancel_plan_btn.click, on_cancel_plan, [run_id]),
                (edit_plan_btn.click, on_edit_plan,
                 [run_id, plan_json, request, workflow_mode, start_busy, plan_json_baseline,
                  confirm_years_checkbox, year_confirmation_required]),
                (approve_note_btn.click, on_approve_note, [run_id, approver]),
                (edit_note_btn.click, on_edit_note, [run_id, note_body]),
                (reject_btn.click, on_reject, [run_id, reject_reason])):
            event = trigger(fn, inputs, start_outputs)
            refresh_after(event)
        load_btn.click(
            on_load,
            [run_id, request, workflow_mode, start_busy],
            start_outputs,
            concurrency_id="agent-start",
            concurrency_limit=1,
            trigger_mode="once",
        )
        runs_table.select(
            on_pick_run,
            [runs_table, request, workflow_mode, start_busy],
            start_outputs,
            concurrency_id="agent-start",
            concurrency_limit=1,
            trigger_mode="once",
        )
        refresh_runs_btn.click(refresh_runs, None, runs_table)
        mem_outputs = [prefs_table, coverage_table, notes_mem_table]
        new_pref.input(update_add_preference_button, [new_pref], add_pref_btn)
        new_pref.change(update_add_preference_button, [new_pref], add_pref_btn)
        add_pref_btn.click(on_add_pref, [approver, new_pref], [new_pref, *mem_outputs, add_pref_btn])
        save_watchlist_btn.click(on_save_watchlist, [approver, watchlist_box], [watchlist_box, watchlist_status])
        approver.blur(watchlist_text, [approver], watchlist_box)
        prefs_table.select(
            on_pick_pref, [prefs_table, approver], [selected_mem, selected_label, delete_mem_btn]
        )
        notes_mem_table.select(
            on_pick_note_mem, [notes_mem_table], [selected_mem, selected_label, delete_mem_btn]
        )
        delete_mem_btn.click(
            request_memory_deletion,
            [selected_mem],
            [delete_confirmation, delete_mem_btn, delete_status],
            show_progress="hidden",
        )
        confirm_delete_btn.click(
            on_delete_mem,
            [selected_mem, approver],
            [selected_mem, delete_confirmation, delete_mem_btn, delete_status, *mem_outputs],
        )
        cancel_delete_btn.click(
            cancel_memory_deletion,
            [selected_mem],
            [delete_confirmation, delete_mem_btn, delete_status],
            show_progress="hidden",
        )
        approver.blur(memory_tables, [approver], mem_outputs)

        async def playbook_tables():
            from analystdesk import lessons as pb
            frozen = await pb.is_frozen()
            pend = [[x["key"], x["when"], x["do"], ", ".join(x.get("applies_to", [])),
                     _lesson_source_label(x), x.get("source_issue", "")[:160]]
                    for x in await pb.list_lessons("pending")]
            appr = [[x["key"], x["when"], x["do"], ", ".join(x.get("applies_to", [])), x.get("reviewed_by", "")]
                    for x in await pb.list_lessons("approved")]
            rej = [[x["key"], x["when"], x["do"], x.get("reviewed_by", ""), x.get("review_reason", "")]
                   for x in await pb.list_lessons("rejected")]
            snapshot = await pb.frozen_playbook() if frozen else None
            version = (f" version `{snapshot['version']}` ({len(snapshot['lessons'])} lessons; runs use only "
                       "this snapshot)") if snapshot and snapshot.get("version") else ""
            status_md = (f"**Playbook {'🧊 FROZEN' if frozen else 'open'}**{version} · {len(pend)} pending · "
                         f"{len(appr)} approved · {len(rej)} rejected")
            return (status_md, pend, appr, rej, frozen,
                    *[gr.update(interactive=False) for _ in range(4)])

        def playbook_controls(key, status, frozen):
            return tuple(
                gr.update(interactive=enabled)
                for enabled in _playbook_button_states(key, status, frozen)
            )

        pb_outputs = [
            playbook_status, pending_table, approved_table, rejected_table, playbook_frozen,
            approve_lesson_btn, reject_lesson_btn, freeze_btn, unfreeze_btn,
        ]

        def lesson_picker(status):
            def on_pick_lesson(table, frozen, evt: gr.SelectData):
                row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
                key = table.iloc[row, 0]
                return (
                    key, status, f"Selected: **When {table.iloc[row, 1]}** → {table.iloc[row, 2]}",
                    *playbook_controls(key, status, frozen),
                )
            return on_pick_lesson

        async def on_review_lesson(key, status, name, reason, approve):
            from analystdesk import lessons as pb
            if not key or status != "pending":
                return (None, None, "_Select a pending lesson first_", reason, *await playbook_tables())
            if not approve and not (reason or "").strip():
                return (key, status, "_Give a reason to reject it_", reason, *await playbook_tables())
            ok = await pb.review(key, approve, (name or "analyst").strip(), reason or "")
            msg = (("✅ Approved" if approve else "🛑 Rejected") if ok
                   else "_Not changed: the playbook is frozen_")
            return (None, None, msg, "", *await playbook_tables())

        async def on_freeze(name, frozen, key):
            if not key:
                return (None, None, "_Select a lesson row first_", "", *await playbook_tables())
            from analystdesk import lessons as pb
            await pb.set_frozen(frozen, (name or "analyst").strip())
            return (None, None, f"_Playbook {'frozen' if frozen else 'unfrozen'}._",
                    "", *await playbook_tables())

        lesson_selection_outputs = [
            selected_lesson, selected_lesson_status, selected_lesson_md,
            approve_lesson_btn, reject_lesson_btn, freeze_btn, unfreeze_btn,
        ]
        for table, lesson_status in (
            (pending_table, "pending"),
            (approved_table, "approved"),
            (rejected_table, "rejected"),
        ):
            table.select(
                lesson_picker(lesson_status),
                [table, playbook_frozen],
                lesson_selection_outputs,
            )

        lesson_review_out = [
            selected_lesson, selected_lesson_status, selected_lesson_md, lesson_reason, *pb_outputs
        ]
        async def on_approve_lesson(k, status, n, r):
            return await on_review_lesson(k, status, n, r, True)

        async def on_reject_lesson(k, status, n, r):
            return await on_review_lesson(k, status, n, r, False)

        async def on_freeze_playbook(n, key):
            return await on_freeze(n, True, key)

        async def on_unfreeze_playbook(n, key):
            return await on_freeze(n, False, key)

        approve_lesson_btn.click(
            on_approve_lesson,
            [selected_lesson, selected_lesson_status, approver, lesson_reason],
            lesson_review_out,
        )
        reject_lesson_btn.click(
            on_reject_lesson,
            [selected_lesson, selected_lesson_status, approver, lesson_reason],
            lesson_review_out,
        )
        freeze_btn.click(
            on_freeze_playbook, [approver, selected_lesson], lesson_review_out
        )
        unfreeze_btn.click(
            on_unfreeze_playbook, [approver, selected_lesson], lesson_review_out
        )

        async def on_page_load(name):
            return (await refresh_runs(), *await memory_tables(name), *await playbook_tables(),
                    await watchlist_text(name))

        return on_page_load, [approver], [runs_table, *mem_outputs, *pb_outputs, watchlist_box]
