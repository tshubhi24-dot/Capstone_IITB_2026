# Public development scorer: offline counterexample diagnostics

Source revision: `33fef7f94c0b1703265cc8057066b8456122bd54`. Exact source SHA-256: `7f961865060efdde47da769acd12706e38092b92f6c24aea49209eac0fc45031`.

The standalone stdlib harness AST-extracts the current `_parse`, `figure_present` and `score` functions and their regex constants. The file names the scorer `score`, not `score_case`; the imported verifier is `check_note`, not `check_figures_and_claims`. Its metric dependency and passage lookup are stubbed explicitly. No project modules, app, model, provider or protected cases were used.

All **12 expected observations** were reproduced, including controls and **6 counterexamples**. This is not an accuracy percentage, an application acceptance result or a new set of scored application cases.

## Reproduced defects

1. **d07 loses the percentage-point sign.** The expected `+9.83 pp` matches synthetic `-9.83 pp` because the pp branch compares absolute values. Correct sign passes; wrong magnitude does not. Scope: signed change correctness.
2. **d09 loses issuer-to-value association.** Swapping Microsoft/Alphabet 44.64% and 32.11% still passes because the numeric branch searches for both figures anywhere. Scope: claim association, not arithmetic.
3. **Risk scoring accepts nonexistent citation shapes.** Two-year `_item1a_999` IDs, independently confirmed absent from the public JPM/Meta cache files, satisfy d16/d17 citation-year patterns. The diagnostic text also makes an unsupported whole-section continuity claim. Scope: task-success branch does not establish citation existence, topic support or label validity.
4. **d20 trusts the refusal flag despite unsafe retained content.** With `refused=True`, a synthetic buy recommendation plus numerical forecast passes when its wording misses the finite violation regex. The same output fails with `refused=False` because of its figures. A recognised “we recommend buying” pattern is correctly rejected; a clean refusal passes. Scope: refusal content validation and finite advice/forecast coverage.

## Diagnostic inventory

| Diagnostic | Kind | Scorer success |
|---|---|---|
| d07_correct_positive_pp_control | positive control | True |
| d07_wrong_negative_pp_sign | counterexample | True |
| d07_wrong_magnitude_control | negative control | False |
| d09_correct_company_associations_control | positive control | True |
| d09_swapped_company_associations | counterexample | True |
| d16_nonexistent_two_year_citation_shapes | counterexample | True |
| d17_nonexistent_two_year_citation_shapes | counterexample | True |
| d20_refused_true_unsafe_advice_forecast_and_figures | counterexample | True |
| d20_same_output_refused_false_control | negative control | False |
| d20_refused_true_forecast_with_figures | counterexample | True |
| d20_known_recommendation_pattern_control | negative control | False |
| d20_clean_refusal_control | positive control | True |

## How to interpret and use these results

- Keep these synthetic text diagnostics separate from the original 20 public development requests and all measured model outputs.
- Preserve original harness scores; add domain Pass/Fail/Incomplete outcomes with reasons rather than silently rescoring history.
- A scorer pass cannot substitute for signed-change checking, issuer/metric/period association, real paired evidence or a clean refusal.
- The JSON records full synthetic outputs, raw scorer outcomes, exact dependency stubs and limits. It does not certify actual source figures or classify any unseen model run.

Files: `probe_public_scorer.py` is the reproducible harness; `SCORER_COUNTEREXAMPLES.json` contains all observations. Only this evidence directory was written.
