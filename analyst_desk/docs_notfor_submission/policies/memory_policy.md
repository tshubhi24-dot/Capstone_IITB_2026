# Memory policy

Analyst Desk remembers four things across runs, so that an analyst can ask *"What changed since our last note?"* and does not have to repeat standing instructions. Everything else is forgotten when a run ends.

Code: [analystdesk/memory.py](../../analystdesk/memory/store.py). Store: a LangGraph SQLite store at `.runtime/memory/memory.sqlite`, separate from the run checkpointer. Not in git.

## What is saved, and when

| Memory | Contents | Saved when | Never saved |
|---|---|---|---|
| **Preferences** | Standing instructions, e.g. "Always include a peer comparison table" | Only when the analyst adds one in the app (🧠 Memory panel) | Anything the model infers about the analyst |
| **Coverage list** | Tickers the analyst has published on, note ids, last publish date | After a note is **published** | Drafts, rejected notes, plans |
| **Private watchlist** | Tickers the analyst follows privately (covered companies only) | Only when the analyst saves it in the 🧠 Memory panel | Anything the model proposes; uncovered tickers |
| **Past-note memory** | Per ticker: note id, title, date, approver, and the note's key figures | After a note is **published** (i.e. after the analyst approved the exact note) | Unverified numbers: figures are parsed from the note's own `[fact]`/`[calc]` tags, which code already checked against XBRL |

Not remembered at all: the research conversation, tool results, rejected or unapproved drafts, and the API key. Within a run, the research conversation is **trimmed** to a size budget (system prompt, request and the most recent tool rounds), so long runs stay within the model's context.

## Who reads it

| Reader | Reads | Purpose |
|---|---|---|
| Planner | Preferences; which tickers have a previous note | Plans around standing instructions and a "what changed" comparison |
| Writer | Preferences; the "what changed" lines | Follows instructions; comments on the comparison |
| Code (not the model) | Previous note's figures | Computes the "what changed" lines: previous → current value, margin moves in pp |
| Analyst | Everything | 🧠 Memory panel in the Research tab (C1/C2 modes) |

Memory is read-only to the agent: no tool lets the model write, edit or delete memory. Only three code paths write it: the analyst's own "Add preference" and "Save watchlist", and the publish step after an approved publication.

The stored watchlist is not added to the planner prompt. A pre-tool hook refuses a tool call that names a watchlist company the approved plan does not cover, and note checks reject such names ([guards.py](../../analystdesk/agent/guards.py)). This is not a general data-loss-prevention guarantee: the analyst's request, preferences, prior context and approved plan may themselves contain those names and are sent to the model provider.

## How it is corrected or deleted

- **Delete:** in the 🧠 Memory panel, click a preference or a past-note memory, then **Delete selected memory**. The next run no longer sees it. To change or clear the watchlist, edit it and click **Save watchlist**.
- **Correct:** delete the wrong item and add the right one (preferences), or re-run `python scripts/ops.py backfill-memory`, which rebuilds past-note memory from the published notes in the portal. It skips notes the analyst deleted from memory.
- **Run without memory:** memory is on by default for each analyst. **↻ Re-run this request without memory** (C1/C2 panel) repeats a request with memory off; that run neither reads nor writes memory, and the `get_past_notes` tool is removed from it, so the agent has no route to earlier notes. This is also how memory-on vs memory-off is compared. Through the API, send `"memory_on": false`. Evaluation runs (`AGENT_EVAL=1`) always run without memory.
- **Forget everything:** delete `.runtime/memory/memory.sqlite`. Published notes stay in the portal, because publishing is a separate, approved record.
- **Withdraw or supersede a published note:** use the Published notes controls or `POST /api/notes/{note_id}/lifecycle`. A correction is a separately published, newly reviewed replacement with the same tickers; then supersede the original. Enter an actor and reason and confirm the action. The original, approval context and lifecycle event remain in the portal audit history; normal past-note retrieval, memory views and backfill exclude inactive notes. Withdrawing a replacement does not reactivate its predecessor.
- If an approver public key is registered, preview the exact action digest in the UI and sign it using `python -m analystdesk.servers.signing sign --key <private-key> --digest <digest>`. The signature binds the note ID, action, replacement ID, reason and actor; changing any field requires a new signature. Keep the private key outside this project. With no registered key, the typed actor is not authenticated.
- A lifecycle change invalidates in-progress memory-on runs: start a fresh run and review it again. Publication also rechecks the lifecycle version in the portal transaction. Older checkpoints and other historical records are retained, not rewritten.
- Live C1/C2 runs also require a cited-evidence and policy snapshot. If it is missing or changes before approval or publication, start a fresh run. Old checkpoints without a snapshot cannot be approved under the new live policy; they remain available as history.

## Privacy and access

Each kind of record has its own purpose and store. Being stored does not make a record approved or safe to reuse.

| Record | Store | Purpose and boundary |
|---|---|---|
| Preferences, coverage, past-note memory | Memory store (above) | Follow-up research. Written only by the analyst or after an approved publication |
| Run checkpoints | `.runtime/runs/`, separate from memory | Resume a run and review what happened. Hold the request, plan, tool results and drafts, including failed or rejected drafts; never treated as approved history |
| Published notes | Research portal, `.runtime/portal/` | The approved record. Each note is stored with the approver and a hash of the exact approved text. New graph approvals also store the signed request, plan and check context; legacy approvals may not have it. That context is not returned by the past-notes tool |
| Playbook lessons | Memory store, in their own `("lessons", <status>)` namespace | Procedures learned from development failures. Pending until the analyst approves each one; frozen before held-out evaluation |
| Filing passages and index | `data/passages/`, `.runtime/index/` | Public SEC text only. No analyst questions, preferences or notes are added to the index |

- **Memory off** stops the run from reading preferences, the watchlist and previous notes (including through the `get_past_notes` tool) and from writing memory. It does not delete existing records, and the run's checkpoint is still saved. Publishing to the portal and using playbook lessons are separate settings (`AGENT_LESSONS=0` turns lessons off).
- **A previous note is context, not a source.** Its figures are compared with freshly fetched XBRL facts; a same-year difference is reported as a later presentation of that year (cause not established), not as a business change.
- **What leaves the machine:** the request, plan, preferences, previous-note context and retrieved passages and facts are sent to the model provider (OpenRouter) during a run. The stored watchlist is not automatically sent, but names entered in other context can be. The API key, the memory files and published notes stay local unless they are part of that context.
- **Secrets stay out of memory**, lessons, logs and git: the key is read from `.env` at run time.
- **Deletion has a stated scope, and the app says it.** Deleting a past-note memory removes it from the memory store and from every coverage list, and records the note as deleted, so neither a backfill nor a later memory sync brings it back. It does not withdraw the published note, edit old checkpoints or change the portal. The confirmation message states exactly this.

## Limits

- Preferences are free text and are not checked; a contradictory preference is followed as written. The analyst sees which preferences were used in each run's activity log.
- The analyst and approver are typed names, not verified identities. Preferences and coverage are kept per analyst name, but nothing stops one analyst from typing another's name, and past-note memory and published notes are shared by everyone using the app.
- A preference cannot widen a run's scope. For example, "always include a peer table" does not add peers to the approved plan. Figures for companies outside the plan are not available to the writer, and any placeholder for them is rejected by the checker.
- There is no automatic expiry or deletion: records remain until an operator deliberately removes them according to their own retention and backup procedures. This is a trusted single-analyst, public-data demo, not cross-account isolation or a shared private-data deployment.
