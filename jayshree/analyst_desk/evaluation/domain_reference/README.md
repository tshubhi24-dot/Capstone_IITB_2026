# Analyst Desk Domain Reference Content

Final publication release `analyst-desk-domain-gold-2.1-20261109` contains twenty public development contracts aligned to Main d01–d20: eight numeric, five comparison, four risk-change and three refusal cases. Each includes the research question, expected answer, acceptable interpretations and limitations. R1 defines meaning; R2 supports source quality; R5 owns independent scoring and execution.

`DEVELOPMENT_GOLDEN_CASES.json` is the core answer key. `GOLDEN_CONTENT_VERIFICATION.json` records bounded source/arithmetic verification. `SUPPLEMENTARY_EXAMPLES.json` preserves eight worked policy examples outside the core count. `evidence/development_case_review/` contains exact public source contexts, risk pairs, refusal contracts and scorer diagnostics. Refer to [Golden Answers and Scoring](../../docs/GOLDEN_ANSWERS_AND_SCORING_RULES.md) and [Domain Review](../../docs/DEVELOPMENT_CASE_DOMAIN_REVIEW.md).

The answer key is evaluator-side. Supply only the question and eligible public evidence to the application; exclude answers, rubrics and evidence-review records from prompts, tools, indexes and memory. This folder is outside `data/evaluation`, and existing runners are unchanged. Its location alone does not prove isolation; verify the boundary before scored execution.

Nineteen stored financial values match bounded independent calculations; four risk cases have eight selected topic pairs. These are not ten company-year human annotations. No new app case, paid model request, held-out inspection or independent human/R5 sign-off is claimed. Twenty public cases do not complete the brief’s 60+ expectations, 40+ protected held-out cases, calibration or repeated experiments.

Original questions and legacy expectations are unchanged. Version2.1 updates portable packaging and retains source hashes; old run scores are not rewritten. The current supplementary examples are reference content, not old drafts. Public source locators are relative to the pinned application root. Reproducer scripts and private runtime histories are excluded; captured diagnostic results identify their source revision and limits.
