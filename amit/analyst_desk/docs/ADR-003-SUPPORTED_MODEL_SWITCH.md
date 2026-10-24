# ADR-003: supported replacement models within the original spending cap

**Status:** writer verified; three critic rate-limit stops retained; different-provider critic and exact extra-call approval being prepared

**Date:** 24 October 2026
**Decision basis:** Bounded replacement model profiles preserve the existing spending authorization, source validation and separate human review gates.

## Context

The previous route returned a provider-reported Terms of Service refusal. The specific rule remains unverified. Five application planner attempts and one direct operator diagnostic retained US$0.1688064 in uncertain reservations under the original US$1 authorization. The replacement must preserve those reservations and all existing notes.

The source question remains Microsoft and Apple, fiscal 2023–2025. Only the research question and selected public SEC evidence are sent for reasoning. Existing private research notes are not model context. Both human review gates and deterministic financial verification remain required.

## Decision

Use this reviewed pair through OpenRouter's exact `mistral/zdr` endpoint:

| Role | Model ID | Input/output ceiling per million tokens | Advertised context |
|---|---|---|---|
| Producing specialists | `mistralai/mistral-medium-3.1` | US$0.40 / US$2.00 | 131,072 tokens |
| Internal critic | `mistralai/mistral-large-2512` | US$0.50 / US$1.50 | 262,144 tokens |

The authenticated user catalogue listed both models. Public endpoint metadata advertised JSON-schema structured outputs for both at the observed ceilings. Pin the full endpoint suffix, disallow fallback, require parameter support and preserve the no-data-collection setting. Keep strict local JSON Schema/Pydantic validation, quote/source/scope checks and the existing qualitative narrative constraints. Catalogue availability does not establish successful generation or semantic correctness.

Model selection uses advertised endpoint capabilities and remains subject to provider enforcement. Catalogue entries do not guarantee successful generation. Routes are pinned, fallback is disabled and local validation remains authoritative.

## Spending continuity

Keep the original **US$1 total**, **US$0.50 per run**, **12 calls per run** and **250,000 tokens per run**. The six old reservations remain committed, leaving US$0.8311936 at preparation time. This is not a fresh US$1 grant.

A model-policy change creates a fresh policy/authorization ID because existing policy hashes are immutable. The dedicated desk ledger must count charges and holds across all its policy IDs, freeze the desk spending ceiling, retain per-run limits across policy changes and carry accounting-anomaly blocks forward. SQLite transactions must enforce this under concurrent requests. Do not remove old ledger rows or release uncertain holds.

The explicit switch helper archives the old configuration and operator receipt privately, preserves the key and all original limits, and stages the new policy disabled. Activation records the authorized model profile and preserves separate plan and note review gates. Current and retired credential scans run before each commit/push.

## Options considered

| Option | Assessment |
|---|---|
| Wait for clarification of the refused route | Preserves the existing pair but cannot currently advance live research. The earlier diagnosis remains available. |
| Mistral Medium 3.1 and Large 3 through the pinned endpoint | Both advertise structured outputs and fit existing context/output ceilings at modest price ceilings. Selected for an ordinary supported-route attempt. |
| Arbitrary provider/model fallback | Would make actual models, prices and data handling uncertain. Excluded from this pilot. |

## Consequences and verification

The API must show actual gateway model metadata rather than hardcoded former model names. Unknown model/profile metadata blocks live creation. The base offline journey remains available. Model output quality may differ, so an internal passing critic still does not establish independent gold quality.

Implement and commit in separate steps: cumulative ledger/profile support; private deployment and truthful API metadata; actual replacement-model journey. Before paid work, verify local tests, the prepared configuration, the unchanged ledger/note library and deployed boundaries. The real planner must pause for human plan review, and a checked exact note must receive a separate publication decision. Stop and report any new provider refusal rather than treating it as a successful run.

## Primary references

- [Medium 3.1 endpoint metadata](https://openrouter.ai/api/v1/models/mistralai/mistral-medium-3.1/endpoints)
- [Large 3 endpoint metadata](https://openrouter.ai/api/v1/models/mistralai/mistral-large-2512/endpoints)
- [Endpoint routing and price ceilings](https://openrouter.ai/docs/guides/routing/provider-selection)
- [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Mistral custom JSON-schema outputs](https://docs.mistral.ai/studio/conversations/structured-output/custom)
- [Mistral commercial terms](https://legal.mistral.ai/terms/commercial-terms-of-service/)
- [Mistral partner-served deployment terms](https://legal.mistral.ai/terms/partner-served-deployment-terms/)

Observed endpoint metadata is recorded in `evidence/model_switch_preparation.json`. Runtime receipts will establish what actually worked.

## Step 10n: a bounded replacement after critic capacity failures

The corrected writer passed local checks, including all eighteen financial values. Large 3 then returned HTTP 429 twice: the original critic request and one explicit retry. Neither produced an AI verdict. Both uncertain reservations remain, and the same-model retry path is exhausted. These capacity failures are distinct from the earlier refused route; that route remains stopped.

Prepare a separate reviewed profile with the same Medium 3.1 producer and `mistralai/mistral-large-2407` critic, pinned to `mistral/zdr`. The authenticated account catalogue lists this critic; its [public endpoint metadata](https://openrouter.ai/api/v1/models/mistralai/mistral-large-2407/endpoints) advertises structured outputs, a 131,072-token context and input/output ceilings of US$2/US$6 per million tokens. Selection remains within the existing model-selection and spending authorization. No new spending grant or exact-model human review is claimed.

Tighten the prompt reservation ceiling to 49,152 tokens and the combined message/schema limit to 45,056 bytes. The exact unchanged critic payload measures 23,285 bytes, contains seven claims and nineteen full cited evidence records, and requires no truncation. With 2,000 output tokens, the final reservation is 51,152 tokens and at most US$0.110304. The run already accounts for 195,257 tokens including both failed-call holds; the worst total is 246,409 tokens and twelve calls, within its original limits. Earlier reservations cannot be released or replaced to make room.

The profile switch archives the old private policy and stages a fresh disabled policy ID. Activation and the subsequent critic-only continuation are separate operations. The controller must bind that continuation to the deployed ledger policy hash, unchanged approved plan, frozen draft and failed checkpoint, allow it only once, and retain all prior accounting. A passing internal critic still requires separate human note approval. Catalogue and payload checks are recorded in `evidence/critic_replacement_catalogue.json` and `evidence/critic_replacement_preflight.json`; these checks made no generation request.

## Different provider after the final original call

Large 2407 also returned HTTP 429 on the reviewed route. No AI verdict was obtained. The run now has twelve calls and 246,409 accounted tokens, including three uncertain critic reservations; its original call limit is exhausted. The old request and immutable ledger limits must remain twelve calls and 250,000 tokens. The rate-limit causes remain unverified because only the safe HTTP diagnostic was retained. This is not evidence of a credit or application-dollar-budget failure.

The next critic attempt requires a separate run-limit extension. Prepare `google/gemini-2.5-flash` as critic, pinned to `google-ai-studio`, with Medium 3.1 retained for producing roles through `mistral/zdr`. Routing must be explicit per role, with no fallback. The authenticated account catalogue lists the Google model; its [endpoint metadata](https://openrouter.ai/api/v1/models/google/gemini-2.5-flash/endpoints) advertises structured outputs and input/output rates of US$0.30/US$2.50 per million tokens. Disable optional reasoning for this bounded output; all reported completion tokens remain counted. Endpoint/account listing is a candidate check, not a guarantee of access or successful generation. Any new refusal stops the attempt.

Prepare one append-only human-approved grant for the exact frozen critic request. It binds the existing run, original plan and draft, new policy, exact call ID and gateway request hash, and complete pre-call ledger checkpoint. It permits absolute bounds of thirteen calls and 300,000 tokens for that one critic call only, consumes atomically with its reservation and never raises or rewrites the original limits. A fourteenth call remains blocked. The new 51,152-token reservation would total 297,561 tokens and at most US$0.0197456, within the unchanged US$1 desk and US$0.50 run dollar caps. All previous charges and holds remain. The grant must not be applied before explicit approval of its exact proposal; generated note approval remains separate.
