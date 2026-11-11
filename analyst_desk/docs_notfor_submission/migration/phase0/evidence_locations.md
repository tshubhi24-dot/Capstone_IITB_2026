# Baseline Evidence Locations

Paths are relative to `jayshree/analyst_desk/`, except where explicitly marked repository-relative. Presence is not independent validation of quality or completeness. Protected case/label contents were not opened for this inventory.

| Location | Function and handling |
|---|---|
| `CURRENT_IMPLEMENTATION_GAP_ANALYSIS.docx` | Original historical audit; untracked input, preserved and included in eligible local working-document backup. |
| `docs/gap_closure.md` | Current implementation-status claims; verify against code/tests in Phase 1. |
| `docs/evidence/product_domain/`, `docs/PRODUCT_DOMAIN_INDEX.md` | Domain policies and associated review evidence; preserve original versions and references. |
| `docs/DEMO_EVIDENCE_INDEX.md`, `docs/assets/` | Demonstration index/assets; retain provenance. |
| `docs/evaluation.md`, `docs/heldout_report.md`, `docs/heldout_report.json` | Existing summary reports; do not regenerate for cleanup. |
| `docs/role6_development_evidence.md`, `docs/retrieval_eval.md` | Development audit and retrieval reports; retain their source/result links. |
| `data/passages/`, `data/passages_plain/`, `data/edgar_cache/` | Corpus and comparison inputs; preserve both passage variants and accepted raw sources. |
| `data/evaluation/` | Cases, results, labels, and manifests; metadata-only inventory. Preserve failed runs as evidence. Role 5 controls protected assets. |
| `evaluation/domain_reference/` | Reference examples; not a source for prompt tuning or mock fixture extraction during cleanup. |
| `experiments/` | Experiment switches and reproducibility configurations; preserve semantics and budgets. |
| `submission/` and `submission/demo/` | Final deliverables, work/experiment logs, demo material; keep traceable source links. |
| `tests/`, `tests/security/` | Offline regressions, mocks/scripted models, local fixture use, and security checks; IDs recorded separately. |
| `.github/workflows/` (repository-relative) | Offline CI, image publication, live evaluation gate. Live evaluation is excluded from migration validation. |

## Local and runtime boundaries

| Location | Phase 0 action |
|---|---|
| `jayshree/analyst_desk/.env`, `shubhi/analyst_desk/.env` (repository-relative) | Existence only; no contents read, hashed, exported, or copied. Keep both unchanged. |
| `.venv/`, `__pycache__/` | Existing ignored environment/cache; package versions recorded through metadata. No environment recreation or cache removal. |
| `data/approval/`, `data/index/`, `data/memory/`, `data/portal/`, `data/runs/` | Existing local runtime directories; retain untouched. Do not inventory database contents or approval keys. |
| Docker named volumes | Not inspected or changed. Later root migration must preserve volume identity; no `down -v` or equivalent cleanup. |
| `.review_dependencies/` (repository-relative) | Ignored local review tooling; permission-limited subdirectories left untouched. |
| `docs/~$presentation.pptx` | Temporary Office lock-file candidate if still present; no removal in Phase 0. Close the owning application before later review. |
| `.migration-local/phase0/` (repository-relative) | Ignored local recovery archive; no credentials or protected cases/results included. |

All source and evidence reclassification/removal remains a later, reviewed action. This index intentionally does not summarize protected expected answers or human labels.
