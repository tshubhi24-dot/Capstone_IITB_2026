# Phase 4C ? Governance and Memory Grouping

Complete: checks, approval and review snapshots moved to governance; memory store and playbook grouped under memory. Callers/mock targets updated directly; no legacy module copies remain. APP_ROOT preserves database/key paths; policy-file references now name their maintained implementations and include the shared paths dependency. Existing review snapshots require fresh verification after this source/policy change.

Full gate: 538 run, 533 passed, five unchanged skips, no failures/errors. Memory namespaces, suppression, frozen playbooks, exact-note signatures, lifecycle handling and acceptance checks preserve existing semantics. Redundancy review: five old implementation locations removed; no extra compatibility modules created.
