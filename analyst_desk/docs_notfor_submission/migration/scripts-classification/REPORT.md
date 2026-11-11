# Submission script classification

Retained 12 runnable scripts under `scripts/`: nine evaluation/learning scripts, two operations scripts and the offline mock runner. Calibration is imported by the evaluation UI; reflection implements playbook learning; memory recovery is referenced by the research UI. FinanceBench and memory comparisons reproduce submission evidence. These are distinct responsibilities, not duplicate implementations.

Moved four team authoring utilities into `not_for_submission/scripts/{data,operations}/`. Updated their application-root calculations, current commands/document links, and Docker exclusion. Dataset generators were not run; frozen inputs and saved evidence were not regenerated. The candidate held-out generator still targets the candidate directory, not active held-out inputs.

Removed `eval_report.py` (obsolete 20-case narrative and current-config provenance) and `results_tables.py` (old run-name patterns, hardcoded 24-case held-out count and only the first red-team configuration). Their originals are in the ignored `.migration-local/scripts-classification/originals.zip`; current audits/repeated-run reports remain canonical. No replacement feature was added.

Updated stale UI helper command paths and documented the classification in the repository README. Historical checkpoint/evidence text retains original paths. See `changes.json` for the movement/removal manifest.

Offline validation: 538 tests, 533 passed, five unchanged skips, no failures/errors; test IDs unchanged. Moved scripts match their archived originals apart from application-root and command-path updates. Updated links and Docker exclusions checked. No live/provider tests or generation runs.
