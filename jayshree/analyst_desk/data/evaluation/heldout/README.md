# Held-out evaluation cases

This directory contains Role 5's frozen, evaluator-side held-out set. The
current release is `role5-heldout-v1`: 40 cases in
[`role5_heldout_v1.jsonl`](role5_heldout_v1.jsonl), bringing the project to 60
core evaluation cases when combined with the 20 development cases.

| Type | Count |
|---|---:|
| Numeric | 12 |
| Comparison | 10 |
| Risk change | 12 |
| Refusal / scope | 6 |
| **Total** | **40** |

Expected values and source tags are in the evaluator-side `expect` fields.
`analystdesk.evaluation.run_c0` and `run_agent` pass only `case["request"]` to
the application; expected answers, labels, and evidence anchors must not be
copied into prompts, tools, indexes, or memory. Preserve this separation when
changing the runner or adding an application tool. The current risk-change
scorer verifies citations from both years; it does not judge whether the
answer's interpretation is supported. See the accompanying
[Role 5 review record](../../../evaluation/domain_reference/HELDOUT_ROLE5_REVIEW.md)
for source-validation scope and this limitation.

The case file's SHA-256, source revision, and release status are recorded in
[`HELDOUT_ROLE5_V1_MANIFEST.json`](../../../evaluation/domain_reference/HELDOUT_ROLE5_V1_MANIFEST.json).
Any edits after the freeze require a new release version and a new hash,
recorded before that release is scored. Keep runs and reports tied to the
matching case-file hash.

## Independence and access

The person tuning the agent must not write or inspect these cases or expected
answers. This release has been shown to the project owner in this review, so
the owner must not tune the evaluated agent. If the owner has already tuned
against these questions, treat the affected cases as development data and
replace them with a set prepared by an independent evaluator before making a
blind held-out claim. Keep the release and its answer key away from agent
tools and tuning workflows.

## Execution status

The `role5-heldout-v1` set was scored in three recorded runs. C2 run 3 contains
10 HTTP 402 insufficient-credit errors, so that configuration's third repeat
is incomplete. See the [three-run report](../../../docs/heldout_report.md)
and [review record](../../../evaluation/domain_reference/HELDOUT_ROLE5_REVIEW.md)
for the results, scorer limitations, and record sanitization note.
