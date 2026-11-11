# Threat model

Analyst Desk turns a research request into a note that a person signs before it is published. What must be protected is narrow: **only notes the analyst approved, word for word, reach the portal; every number in them is true; and the analyst's private data stays inside the system.** Defences are code, not prompts ([guards.py](../../analystdesk/agent/guards.py), [hooks.py](../../analystdesk/agent/hooks.py), [checks.py](../../analystdesk/governance/checks.py)). They are measured by experiment E2: attack success with defences on and off, and false blocks on clean cases ([run_redteam.py](../../analystdesk/evaluation/workflows/run_redteam.py)).

## Assets and trust

| Asset | Why it matters |
|---|---|
| Published notes (portal) | Clients act on them; a wrong or unapproved note is the worst outcome |
| The approval signing key | Whoever holds it can make the portal accept a note |
| Private watchlist, preferences | The analyst's confidential intentions |
| OpenRouter API key | Spending and access |
| The host | Model-written code runs in the sandbox |

**Untrusted:** filing text and anything retrieved (data, never instructions), every model output (a proposal that code checks), model-written code. **Trusted:** the analyst at the gates, and our code. **External:** OpenRouter receives prompts; SEC EDGAR is read through a cache.

## Threats and defences

| # | Threat | Path | Defences (layered) |
|---|---|---|---|
| 1 | **Injected "news article"** makes the note recommend a stock | Planted text in a filing passage | Tool results screened: a passage with instructions to the model is withheld (`screen`); prompts mark filing text as data; output rule rejects advice wording; the analyst signs the exact note |
| 2 | **Direct injection** in the request | "Ignore your instructions…" | Input guard refuses instructions aimed at the system, advice requests, and uncovered companies or years |
| 3 | **Watchlist exfiltration** into a search query or the note | Planner sees the watchlist; injected text asks for it | Pre-tool hook denies any call naming a watchlist company outside the approved plan (`WATCHLIST_PRIVATE`); output rule; text asking about a watchlist is screened out |
| 4 | **Sandbox escape**: code reaches the network or files | `run_python` | Import allow-list and audit hooks in the runner; the sandbox service is read-only, non-root, capability-free and on an internal network with no internet route |
| 5 | **Wrong or invented number** | Model types or mis-copies a figure | Figures come from XBRL placeholders; every number is checked against XBRL or its cited passage; critic loop; approval is refused while checks fail (graph and API) |
| 6 | **Unapproved or altered publication** | Agent calls `publish_note`; note edited after approval | Only the publisher holds the write tool; HMAC over title, body, tickers and approver; the portal verifies it and refuses duplicates; any edit invalidates the approval |
| 7 | **Tool misuse, runaway cost** | Agent calls tools outside its role | Per-agent allow-list checked again by the pre-tool hook; tool and token budgets; EDGAR rate limit; at most two revisions |
| 8 | **Memory poisoning** | Model writes false "facts" to memory | No tool writes memory; only the analyst's own actions and figures from published, verified notes are saved |
| 9 | **Secret leakage** | Key in git, image or prompts | Key only in `.env` (git-ignored, not in the image); the signing key lives in a volume the agent cannot read |

## What is not defended (residual risk)

- **Identities are typed, not verified.** Anyone who can open the app (bound to 127.0.0.1) can approve. A pilot needs sign-in in front of the app.
- **The injection screen is a pattern list.** Paraphrased instructions can pass it. A classifier such as Llama Prompt Guard 2 would add a second layer. The checks and the human gate still apply.
- **A planted passage with a wrong number but no instructions** passes the quote check if the note cites it, because the number does appear in the cited text. Key figures are safe because they come from XBRL; quoted figures are only as good as the passage.
- **In Docker Compose the sandbox guard is in-process.** Code that defeated the import guard and audit hooks could reach the other services on the internal network, including the app's API, though not the internet. The networkless per-call container (`SANDBOX_MODE=docker`) needs the Docker socket, which we deliberately do not mount (socket access is root on the host).
- **OpenRouter sees prompts**, including the request and preferences, but not the saved watchlist as a separate planner input. Names supplied in other prompt context can still be sent. The signing key and memory database are not sent as prompts.
