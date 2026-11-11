# Phase 4A ? UI and Research Grouping

Complete: seven modules moved to `analystdesk/ui/` and `analystdesk/research/`; callers and mock targets updated directly, without old-module copies. `app.py` remains a thin run-module launch entry. Docker copies that launcher and the existing application package. `analystdesk.paths.APP_ROOT` is the shared application locator for relocated modules; storage/config paths preserve their meaning.

Gate: 538 run, 533 passed, five unchanged skips, no failures/errors; exact Phase 0 IDs. Redundancy review: removed seven old implementation locations; kept one canonical copy of each module and the required app launcher. No prompts, calculations or workflow functionality changed. See `changes.json` and test artifacts.
