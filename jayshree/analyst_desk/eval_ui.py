"""Evaluation tab — the golden set, live evaluation runs, results and judge labelling.

Sections:
  📋 Golden set        every development case with its expected outcome
                       (frozen from XBRL before any run); held-out cases are
                       counted but never shown here (role 5 keeps them blind)
  ▶ Run                pick configurations and cases, run, watch pass/fail live
  📊 Results           any saved results file: the E1 table and a per-case grid;
                       click a row to open that run's note and check
  ⚖️ Judge calibration  label claim/passage pairs Yes/No (blind to the judge),
                       then compute agreement and Cohen's kappa

Evaluation runs here use memory off (passed per run), the same as the CLI.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "data" / "evaluation" / "results"
LABELS = ROOT / "data" / "evaluation" / "judge_labels.csv"
NAMES = {"c0": "C0 fixed pipeline", "c1": "C1 single agent", "c2": "C2 team"}
METRICS = [("success", "Task success"), ("policy_violations", "Policy violations"),
           ("verified_share_mean", "Numbers verified (mean %)"), ("errors", "Errors"),
           ("timeouts", "Timeouts"), ("tokens_mean", "Tokens per case"),
           ("cost_per_case_usd", "Cost per case (USD, est.)"), ("latency_median_s", "Latency median (s)"),
           ("latency_p95_s", "Latency p95 (s)")]


def _expected(case: dict) -> str:
    e = case["expect"]
    if "figures" in e:
        return ", ".join(f"{f['key']} = {f['text']}" for f in e["figures"])
    if "risk_change" in e:
        r = e["risk_change"]
        return f"cites {r['ticker']} Item 1A for FY{r['years'][0]} and FY{r['years'][1]}"
    return f"decline ({e['refusal']})"


def _golden_rows() -> list[list]:
    from analystdesk.evaluation import load_cases
    return [[c["id"], c["type"], c["request"], _expected(c)] for c in load_cases("dev")]


def _heldout_count() -> int:
    from analystdesk.evaluation import load_cases
    try:
        return len(load_cases("heldout"))
    except Exception:   # noqa: BLE001
        return 0


def _results_files() -> list[str]:
    return sorted((p.name for p in RESULTS.glob("eval_*.json")), reverse=True)


def _tables(rows_by_config: dict) -> tuple[list[list], list[list], list[str]]:
    from analystdesk.evaluation import summarise
    configs = [c for c in ("c0", "c1", "c2") if rows_by_config.get(c)]
    summary = {c: summarise(rows_by_config[c]) for c in configs}
    e1 = [[label] + [summary[c][key] for c in configs] for key, label in METRICS]
    types = sorted({t for c in configs for t in summary[c]["by_type"]})
    e1 += [[f"  {t}"] + [summary[c]["by_type"].get(t, "–") for c in configs] for t in types]
    ids = sorted({r["id"] for c in configs for r in rows_by_config[c]})
    grid = []
    for cid in ids:
        row, ctype = [cid, ""], ""
        for c in configs:
            r = next((r for r in rows_by_config[c] if r["id"] == cid), None)
            if r:
                row[1] = r["type"]
                row.append(("✅ " if r["success"] else "❌ ") + r["reason"][:70]
                           + (f"  · run {r['run_id']}" if r.get("run_id") else ""))
            else:
                row.append("–")
        grid.append(row)
    return e1, grid, [NAMES[c] for c in configs]


def _load_results(name: str):
    if not name:
        return gr.update(), gr.update(), "_Pick a results file_"
    data = json.loads((RESULTS / name).read_text(encoding="utf-8"))
    e1, grid, cols = _tables(data["rows"])
    note = (f"**{name}** · split **{data.get('split')}** · lessons "
            f"{'on' if data.get('lessons', True) else 'off'} · cost at ${data.get('price_per_m', 0.52)}/M tokens")
    return (gr.update(value=e1, headers=["Metric"] + cols),
            gr.update(value=grid, headers=["Case", "Type"] + cols), note)


# ── judge labelling ───────────────────────────────────────────────────────────

def _read_labels() -> list[dict]:
    if not LABELS.exists():
        return []
    return list(csv.DictReader(LABELS.open(encoding="utf-8")))


def _write_labels(rows: list[dict]) -> None:
    with LABELS.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def _next_item():
    rows = _read_labels()
    done = sum(1 for r in rows if r["human"].strip().lower() in ("yes", "no"))
    progress = f"**{done} / {len(rows)} labelled** (need at least 20)" if rows else "_No sample yet_"
    for i, r in enumerate(rows):
        if r["human"].strip().lower() not in ("yes", "no"):
            return i, f"### Claim\n{r['claim']}", f"**Cited passage(s)** `{r['passage_ids']}`\n\n{r['passages']}", progress
    return None, "### All items labelled ✅", "", progress


def build_eval_tab():
    with gr.Tab("📏 Evaluation"):
        gr.Markdown(
            "**Purpose:** Compare **C0 (baseline)**, **C1 (single agent)**, and **C2 (agent team)** "
            "on the same development questions against predefined expected outcomes.\n\n"
            "**Evaluation criteria:** Expected figures, required citations, appropriate refusals, and "
            "investment-advice language.\n\n"
            "**Results:** Compare answer quality, number traceability, run time, and estimated cost.\n\n"
            "**Judge calibration:** Check how closely the citation-support judge agrees with human reviewers.")

        with gr.Accordion("📋 Golden set (development cases)", open=False):
            golden_md = gr.Markdown()
            golden = gr.Dataframe(headers=["id", "type", "request", "expected (fixed before running)"],
                                  value=_golden_rows, interactive=False, wrap=True)

        with gr.Accordion("▶ Run an evaluation", open=False):
            gr.Markdown("Each case runs as an analyst would use the system: plan auto-approved, stops at "
                        "the note gate, nothing published. C1/C2 take 15–60 s per case.")
            with gr.Row():
                configs = gr.CheckboxGroup([("C0 fixed pipeline", "c0"), ("C1 single agent", "c1"),
                                            ("C2 team", "c2")], value=["c0", "c1"], label="Configurations")
                case_pick = gr.Dropdown(choices=[r[0] for r in _golden_rows()], multiselect=True,
                                        label="Cases (empty = all 20)")
                run_btn = gr.Button("▶ Run", variant="primary")
            run_log = gr.Dataframe(headers=["config", "case", "result", "reason", "seconds", "tokens", "verified"],
                                   interactive=False, wrap=True)

        with gr.Accordion("📊 Results", open=True):
            with gr.Row():
                results_pick = gr.Dropdown(choices=_results_files(), label="Results file", scale=4)
                refresh_btn = gr.Button("↻", scale=0)
            results_note = gr.Markdown()
            e1_table = gr.Dataframe(label="E1 — does the agent justify its cost?", interactive=False)
            grid = gr.Dataframe(label="Per case — click a row to open its run", interactive=False, wrap=True)
            run_detail = gr.Markdown()

        with gr.Accordion("⚖️ Judge calibration (label 20+ items, then compute kappa)", open=False):
            gr.Markdown(
                "The compliance critic's judge (Llama 3.3 70B) decides if a cited passage supports a claim. "
                "Before trusting it, a **person** labels the same items **without seeing the judge's verdict**. "
                "**Cohen's kappa** then measures agreement beyond chance (> 0.6 is substantial). "
                "Ideally role 5 labels, not whoever built the critic.")
            with gr.Row():
                sample_btn = gr.Button("1 · Sample 30 claims from saved runs")
                kappa_btn = gr.Button("3 · Compute agreement and kappa", variant="primary")
            label_progress = gr.Markdown()
            claim_md = gr.Markdown()
            passage_md = gr.Markdown()
            item_idx = gr.State(None)
            with gr.Row():
                yes_btn = gr.Button("2 · ✅ Supported", variant="primary")
                no_btn = gr.Button("❌ Not supported", variant="stop")
                skip_btn = gr.Button("Skip")
            kappa_md = gr.Markdown()

        # ── handlers ──────────────────────────────────────────────────────────
        def golden_header():
            return (f"**{len(_golden_rows())} development cases.** Held-out cases: **{_heldout_count()}** "
                    "(written by role 5, never shown here, so nobody tuning the system sees them).")

        async def on_run(selected, cases):
            from analystdesk.evaluation import load_cases, run_one
            pool = [c for c in load_cases("dev") if not cases or c["id"] in cases]
            tag = "ui-" + time.strftime("%Y%m%d-%H%M%S")
            rows, by_config = [], {}
            for config in selected or []:
                for case in pool:
                    rows.append([config, case["id"], "⏳ running…", "", "", "", ""])
                    yield rows, gr.update()
                    r = await run_one(config, case, tag)
                    rows[-1] = [config, case["id"], "✅ pass" if r["success"] else "❌ fail", r["reason"],
                                r["seconds"], r.get("tokens") or 0, r.get("verified", "-")]
                    by_config.setdefault(config, []).append(r)
                    RESULTS.mkdir(parents=True, exist_ok=True)
                    (RESULTS / f"eval_dev_{tag}.json").write_text(json.dumps(
                        {"split": "dev", "tag": tag, "lessons": True, "rows": by_config}, indent=1), encoding="utf-8")
                    yield rows, gr.update(choices=_results_files())

        async def on_pick_case(table, evt: gr.SelectData):
            row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
            cells = [str(x) for x in table.iloc[row].tolist()]
            run_ids = [c.split("· run ")[1] for c in cells if "· run " in c]
            if not run_ids:
                return f"Case **{cells[0]}**: C0 has no saved run (one model call); see the grid for its result."
            from analystdesk.agent.runtime import get_run
            from agent_ui import _check_display, _note_display
            parts = []
            for rid in run_ids:
                v = (await get_run(rid))["values"]
                if v.get("guard") and not v["guard"].get("ok"):
                    parts.append(f"### Run `{rid}`\n⛔ declined: {v['guard']['reason']}")
                elif v.get("draft"):
                    parts.append(f"### Run `{rid}`\n" + (_check_display(v["check"]) if v.get("check") else "")
                                 + f"\n\n#### {v['draft']['title']}\n\n" + _note_display(v["draft"]["body"]))
            return "\n\n---\n\n".join(parts) or "_Run not found_"

        async def on_sample():
            sys.path.insert(0, str(ROOT / "scripts"))
            from calibrate_judge import sample
            await sample(30)
            return _next_item()

        def on_label(idx, verdict):
            rows = _read_labels()
            if idx is not None and verdict:
                rows[idx]["human"] = verdict
                _write_labels(rows)
            elif idx is not None:   # skip: move it to the end
                rows.append(rows.pop(idx))
                _write_labels(rows)
            return _next_item()

        def on_yes(idx):
            return on_label(idx, "yes")

        def on_no(idx):
            return on_label(idx, "no")

        def on_skip(idx):
            return on_label(idx, None)

        async def on_kappa():
            sys.path.insert(0, str(ROOT / "scripts"))
            from calibrate_judge import OUT, score
            rows = _read_labels()
            if sum(1 for r in rows if r["human"].strip().lower() in ("yes", "no")) < 20:
                return "_Label at least 20 items first._"
            await score()
            r = json.loads(OUT.read_text(encoding="utf-8"))
            c = r["confusion"]
            return (f"### Judge `{r['judge_model']}` vs human, n = {r['n']}\n"
                    f"**Agreement {r['agreement']:.0%} · Cohen's kappa {r['cohen_kappa']:.2f}**\n\n"
                    f"| | judge yes | judge no |\n|---|---|---|\n"
                    f"| **human yes** | {c['both_yes']} | {c['human_yes_judge_no']} |\n"
                    f"| **human no** | {c['human_no_judge_yes']} | {c['both_no']} |")

        label_out = [item_idx, claim_md, passage_md, label_progress]
        run_btn.click(on_run, [configs, case_pick], [run_log, results_pick])
        refresh_btn.click(lambda: gr.update(choices=_results_files()), None, results_pick)
        results_pick.change(_load_results, results_pick, [e1_table, grid, results_note])
        grid.select(on_pick_case, [grid], run_detail)
        sample_btn.click(on_sample, None, label_out)
        yes_btn.click(on_yes, item_idx, label_out)
        no_btn.click(on_no, item_idx, label_out)
        skip_btn.click(on_skip, item_idx, label_out)
        kappa_btn.click(on_kappa, None, kappa_md)

        def on_tab_load():
            return (golden_header(), *_next_item(), gr.update(choices=_results_files()))
        return on_tab_load, [golden_md, *label_out, results_pick]
