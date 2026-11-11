# Historical Results Archive and Fresh-run Reminder

Archived all 28 existing files from data/evaluation/results/ into data/evaluation/archive/pre_cleanup_20261111/, preserving bytes and filenames. The archive manifest records hashes/sizes and the original-to-archive path map. Failed/incomplete diagnostics and the older retrieval-query input snapshot are retained. No stored answers/attack details were inspected. A .gitkeep preserves the empty active results directory for clean checkouts and Docker bind mounts.

Updated the offline regression fixture and CI input to the archived 20-case baseline. CI audits it read-only without rewriting archived records or implying fresh submission evidence. Existing immutable report/manifests retain their historical internal paths; the relocation manifest resolves those paths. Current documentation links/examples were rebased and summaries marked historical.

The existing documentation README now holds the pending pre-submission checklist and tagged commands for development (44 cases, C0/C1/C2), red-team on/off with clean cases, and retrieval table/plain. Root/submission navigation links to that single checklist. No scheduled task was created, and no model evaluation, API-credit run, retrieval/index build, service startup, commit or push was performed.

validation.json records archive integrity and the offline regression gate. To restore, consult the archive manifest and move only the desired files back after checking for newer outputs; never overwrite fresh results or mix historical records into a new benchmark.
