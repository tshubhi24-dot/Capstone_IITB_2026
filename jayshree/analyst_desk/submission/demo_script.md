# Demo script

**Owner:** Role 1 (domain and product lead). **Length:** about 10 minutes live. Record the same run as the backup video.

The brief's three demo steps (p.16) come first. Then come the minimum-bar demonstrations the brief asks to see live: resume, an edit invalidating approval, and a replan.

## Before the session

1. Start the stack with the demo article planted (it only affects this demo):
   `docker compose -f compose.yaml -f submission/demo/compose.demo.yaml up -d`
   Wait until `curl.exe --fail http://127.0.0.1:7861/readyz` returns `{"status":"ready"}`.
2. Open these tabs:
   - the app, <http://127.0.0.1:7861>;
   - Grafana, <http://127.0.0.1:3000>;
   - Jaeger, <http://127.0.0.1:16686>.
3. In 🧠 Memory, as analyst **demo**:
   - make sure one earlier note on MSFT/GOOGL is in past-note memory (publish one in rehearsal if not);
   - add the preference "Always include a peer comparison table";
   - set the private watchlist to `NVDA`.
4. Have one paused run ready for the resume step: start a request and leave it at the plan gate.

## 1. Margin comparison, every number linked to its fact (brief demo 1)

1. **Request, C2 team:** "Compare Microsoft's and Alphabet's operating margins over the last three fiscal years, and tell me what changed in their risk factors."
2. **At the plan gate,** show "How your request was read": the last three years are read as FY2022–FY2024, each company's own fiscal year.
3. **Approve the plan.**
4. **Show the activity board:** researchers, quant and risk-diff run in parallel, and every tool call goes through the hooks.
5. **At the note gate,** show:
   - every figure carries a superscript linking to its XBRL fact (concept / year / accession);
   - the margins were computed by code (`calc`);
   - the Comparability section: Microsoft's year ends 30 June and Alphabet's 31 December;
   - the code check reports N/N numbers verified.

**Say:** "The model chooses which figure to mention; code decides what it says."

## 2. The critic catches a wrong number; the injected "buy" stays out (brief demo 2)

1. **Same note.** Open Edit and change one margin's digits (e.g. 44.64% → 48.00%), keeping its `[calc: …]` tag. Submit the edit.
2. **The note goes back to the checks.** It now shows "48.00% is wrong: … = 44.64%", the approval is withdrawn, and the Approve button is disabled. **This is also the L14 evidence: an edit invalidates the earlier approval.**
3. **Show where the injected article went.** Open the activity log for a `search_filings` result that shows **withheld**: the injection screen removed the planted article's instruction before the model saw it. The note contains no "buy" and no price target.
4. If time allows, explain the defences behind the screen: the note checks reject advice wording, and the analyst signs the exact note.

## 3. "What changed since our last note?" (brief demo 3)

1. **Request, C1:** "What changed in Microsoft's and Alphabet's operating margins since our last note?"
2. **At the note gate,** show:
   - the "What changed since our last note" section, computed by code from the previous note's verified figures;
   - the peer table that the saved preference asked for.
3. **Click "↻ Re-run this request without memory".** The note has no comparison, and the run status says saved memory is off.

## 4. Resume after a stop (L8)

Load the paused run from "Before the session" with **⟳ Load run**: it continues from its checkpoint at the plan gate. You can also stop the app container mid-run, start it again, and load the same run.

## 5. A replan (L10)

Request: "Compare Microsoft with Tesla's operating margin in fiscal 2024." Tesla is not covered, so the tool returns NOT_IN_COVERAGE. The plan goes back to the research lead, and the analyst sees the revised plan. *(Rehearse: if the input guard refuses first, use a request where the company is only implied, or show the trace from `tests/test_graph.py`.)*

## 6. Approve and publish

Edit the note back to the correct figure. The checks pass, so approve it. Show it in the research portal (Recent notes). Then show Grafana:
- verified share;
- critic rejections;
- tokens and cost per note;
- EDGAR cache hits;
- latency;
- the alert panel with the below-98% verified-share rule.

## After the session

`docker compose up -d`, without the demo file, returns to normal and removes the planted article.

## Backup recording

Record steps 1–3 and 6 with OBS or the Windows Game Bar (Win+Alt+R) at 1080p, about 8 minutes. Save it as `analyst_desk_demo.mp4`. Upload it to the team drive and link it here; don't commit the video to the repository.

**Recording link:** _to add_
