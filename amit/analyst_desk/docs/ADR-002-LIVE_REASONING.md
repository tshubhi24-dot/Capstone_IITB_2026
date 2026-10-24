# ADR-002: bounded live AI reasoning

**Date:** 24 October 2026 · **Status:** implemented and explicitly authorized; actual planner requests blocked by provider access refusal

## Context

The first Docker journey completed with real SEC data, deterministic reasoning and two explicit human decisions. The next increment adds actual model judgments while preserving verified calculations, source scope, persistent state and exact-version publication. This is a development pilot, not completion of the larger capstone architecture or its final evaluation.

## Decision

Add an optional model gateway to Docker Compose. Only that service receives the OpenRouter key and outbound network access. The application, four MCP services and calculation worker retain their existing network and credential boundaries. The gateway has a dedicated persistent SQLite spending ledger; it cannot read the portal database or sign publications. The base offline Compose file remains runnable.

Use `openai/gpt-4.1-mini` for planning, company search-query selection, disclosure interpretation and drafting. Use `openai/gpt-4.1` for a separately prompted internal semantic critic. Both were present in the public OpenRouter catalogue on 24 October 2026 with structured-output support. Their observed input/output prices were respectively $0.40/$1.60 and $2.00/$8.00 per million tokens. These are catalogue observations, not guarantees against future changes. Code binds requests to approved price ceilings and fails when the required route or output contract is unavailable.

The ordinary two-company path uses seven model calls: a planner, two company query selectors, two disclosure interpreters, one writer and one critic. Repairs and human note edits consume the same original limits. Brief structured decisions and evidence are saved; hidden chains of thought are neither requested nor stored.

Model output never selects a network endpoint, supplies shell code, changes tool permissions, changes the approved issuer/year scope or authorizes publication. The graph executes allowlisted evidence and calculation operations. Canonical financial tables are still produced by code and independently checked with Decimal arithmetic. This increment is bounded specialist reasoning; it does not claim an unrestricted ReAct agent or learned semantic retrieval.

## Source support and review

Risk interpretation uses bounded, explicitly selected excerpts from the cached source snapshot. Selected excerpts cannot establish that a risk is new, absent, removed or economically material. Preserve source IDs, exact supporting excerpts, issuer/year scope and the selection policy. Exact quote checks establish provenance; they do not prove entailment. The AI critic is an internal model judgment, not independent evaluation gold.

Narrative text in this increment is qualitative; financial quantities stay in the verified table. Model outputs use strict JSON schemas and local validation. Unknown citations, wrong issuer/year scope, invented quotes, unsupported quantitative prose or a failed critic block approval. A note edit invalidates the previous semantic verdict and approval, and must be criticized again against the exact edited body. Both existing human review gates remain required.

## Spending and activation

Prepare the gateway disabled. The proposed first authorization is **$1 total**, with **$0.50 per run**, at most **12 model calls** and **250,000 tokens per run**. Private configuration pins the two models, their price ceilings, prompt-size limits and output limits. These are ceilings, not an expected charge or a provider-account-wide limit.

Before a request, atomically reserve its worst-case allowed token cost. After a valid response, reconcile provider-reported usage. A timeout, malformed accounting or other ambiguous response keeps its reservation committed and does not cause an automatic paid retry. Distinguish reported spend from committed reservations. Persist call IDs and hashes so successful repeated requests reuse the recorded response. Approval and budget limits survive application/gateway restarts.

The analyst must explicitly authorize the concrete prepared configuration before the first paid call. The existing private key may be used only by the gateway; no key, authorization text or full private output enters Git. The preparation command does not activate spending. This follows the project's existing requirement that missing paid authorization blocks live requests; prior offline approvals are not spending authorization.

## Alternatives and consequences

| Option | Benefit | Cost or limit |
|---|---|---|
| Keep deterministic offline processing | Repeatable, no model spend | No actual model reasoning |
| Give the application a provider key and outbound access | Fewer components | Wider credential/network boundary and weaker separation of spend accounting |
| Dedicated optional gateway (chosen) | Narrow credential boundary, persistent budget and reusable adapter | Additional service, activation configuration and failure handling |

Provider endpoint restrictions are enforced by code; the egress network is not an operating-system domain firewall. Trained injection/safety classifiers, full-document risk coverage, vector retrieval/reranking, final held-out evaluation and automatic recovery during an active tool operation remain separate work. A live pilot must disclose these limits.

## Primary references

- [OpenRouter public model catalogue](https://openrouter.ai/api/v1/models)
- [Structured output contract](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Provider selection, parameter support and price ceilings](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting)

These sources informed the adapter. Runtime receipts, rather than documentation, will establish whether the selected route works with this account.
