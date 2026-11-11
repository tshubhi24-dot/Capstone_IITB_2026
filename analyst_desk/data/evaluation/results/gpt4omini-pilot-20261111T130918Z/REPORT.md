# GPT-4o mini two-case pilot

**Status: blocked by provider billing; incomplete pilot evidence, not a submission benchmark.**

Requested C1 on development d01 (Microsoft FY2024 operating margin) and d14 (Microsoft FY2023?FY2024 risk comparison). OpenRouter's public catalogue listed `openai/gpt-4o-mini` with tools and structured-output support. The agent model was overridden only in this child process. The separate judge remained `meta-llama/llama-3.3-70b-instruct`; prompts and budgets were unchanged. The shared `config/llm.toml` was never edited and its original hash was verified afterward.

| Case | Outcome |
|---|---|
| d01 | Input guard completed; the first planner generation was rejected with HTTP 402. No completed model output, draft or verification result. Recorded case duration: 4.3 seconds. |
| d14 | Not attempted: execution stopped after the provider rejection. |

The checkpoint retained the provider explanation: **Insufficient credits; the account associated with this key has never purchased credits.** Verify that the key belongs to the intended OpenRouter account/organization and that billing is funded. No model substitution or automatic whole-case retry was performed. A future retry needs a new tag; preserve this failed attempt.

## Evidence and audit

- `effective_llm.toml`: exact effective prompts, roles and configured output limit.
- `manifest.json`: original/effective config hashes, source hashes, revision/dirty state, input hash, model roles, playbook version and checkpoint path.
- `eval_dev_gpt4omini-pilot-20261111T130918Z.json`: the original attempted-case score/error and provenance; do not interpret the billing error as model quality.
- `case_diagnostics.json`, `provider_errors.json`, `execution.log`: sanitized diagnostics and the checkpoint error explanation. No credentials are included.
- `audit.json`: requested two-case coverage audit **failed**, correctly identifying unattempted d14.
- `attempted_case_audit.json` / `.md`: accounting audit passed for the one attempted record. This verifies recorded coverage/accounting only; it does not establish successful inference.
- `provider_preflight.json`: non-generation catalogue metadata and listed pricing. No actual provider charge was independently verified; null/zero recorded tokens do not constitute a billing receipt.

Frozen playbook `806f51dd6960` (six lessons) remained unchanged. Checkpoints were isolated in a pilot-specific ignored database. The run never reached note approval or publication. No held-out/red-team cases, judge generations, model fallback or published notes were involved. Shared source/configuration files were not changed; no new product functionality was added.
