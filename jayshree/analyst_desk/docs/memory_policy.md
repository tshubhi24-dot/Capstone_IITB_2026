# Memory policy

Analyst Desk remembers three things across runs, so that an analyst can ask *"What changed since our last note?"* and does not have to repeat standing instructions. Everything else is forgotten when a run ends.

Code: [analystdesk/memory.py](../analystdesk/memory.py). Store: a LangGraph SQLite store at `data/memory/memory.sqlite`, separate from the run checkpointer. Not in git.

## What is saved, and when

| Memory | Contents | Saved when | Never saved |
|---|---|---|---|
| **Preferences** | Standing instructions, e.g. "Always include a peer comparison table" | Only when the analyst adds one in the app (🧠 Memory panel) | Anything the model infers about the analyst |
| **Coverage list** | Tickers the analyst has published on, note ids, last publish date | After a note is **published** | Drafts, rejected notes, plans |
| **Past-note memory** | Per ticker: note id, title, date, approver, and the note's key figures | After a note is **published** (i.e. after the analyst approved the exact note) | Unverified numbers: figures are parsed from the note's own `[fact]`/`[calc]` tags, which code already checked against XBRL |

Not remembered at all: the research conversation, tool results, rejected or unapproved drafts, and the API key. Within a run, the research conversation is **trimmed** to a size budget (system prompt, request and the most recent tool rounds), so long runs stay within the model's context.

## Who reads it

| Reader | Reads | Purpose |
|---|---|---|
| Planner | Preferences; which tickers have a previous note | Plans around standing instructions and a "what changed" comparison |
| Writer | Preferences; the "what changed" lines | Follows instructions; comments on the comparison |
| Code (not the model) | Previous note's figures | Computes the "what changed" lines: previous → current value, margin moves in pp |
| Analyst | Everything | 🧠 Memory panel in the Research tab (C1/C2 modes) |

Memory is read-only to the agent: no tool lets the model write, edit or delete memory. Only two code paths write it: the analyst's own "Add preference", and the publish step after an approved publication.

## How it is corrected or deleted

- **Delete:** in the 🧠 Memory panel, click a preference or a past-note memory, then **Delete selected memory**. The next run no longer sees it.
- **Correct:** delete the wrong item and add the right one (preferences), or re-run `python scripts/backfill_memory.py`, which rebuilds past-note memory from the published notes in the portal.
- **Switch off:** untick **Use memory** when starting a run. That run neither reads nor writes memory. This is also how memory-on vs memory-off is compared.
- **Forget everything:** delete `data/memory/memory.sqlite`. Published notes stay in the portal, because publishing is a separate, approved record.

## Limits and planned changes

- Preferences are free text and are not checked; a contradictory preference is followed as written. The analyst sees which preferences were used in each run's activity log.
- No automatic expiry yet: memory stays until deleted.
- The **private watchlist** (brief, L15) will live in its own namespace that is never sent to any search tool or model prompt. It is added with the security phase.
