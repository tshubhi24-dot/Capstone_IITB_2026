# Step-by-step work log

## Step 1 — Project definition

Prepared on 22 October 2026 and adapted for the shared repository on 24 October 2026: analyst problem, intended users, supported tasks, fiscal/source boundaries, proposed quality targets and six ownership roles. AI assistance is disclosed; team names, domain-user review and adoption decisions remain pending.

This commit adds only the new project definition and the current contribution's working instructions. It contains no older application, historical benchmark results, credentials or runtime databases.

## Step 2 — Evaluation design and development preparation

Prepared the evaluation protocol before producing runs: development/final separation, source-based scoring, independent human reviews, E1–E4 comparisons, cost/latency reporting and freeze rules. The public preparation kit has twenty development questions with twenty-five source-derived numeric rows and blank review forms. Protected final questions, real human annotations and empirical results remain pending. Source-cache hashes preserve provenance; the older raw cache and application are not included.

## Step 3 — Architecture

Defined the proposed supervisor/specialist workflow, four MCP services, human decision gates, persistent state, isolated calculations, Docker boundaries and independent evaluation. Included editable workflow/deployment drawings and an overview image/vector. The memory policy distinguishes current-run checkpoints, analyst preferences, reviewed lessons and approved notes. The design is reviewable; it is not a receipt for an implemented or evaluated full capstone.

## Step 4 — Fresh Docker journey implementation

On 24 October 2026, prepared a new implementation under this contribution folder: a LangGraph workflow with two persistent human review gates, parallel company branches, four authenticated MCP services, an isolated pandas calculation worker, independent financial checks, an exact-version publication capability, local review UI and monitoring configuration. The implementation imports only its own `desk` modules. Prior reference application code and results are excluded.

Prepared a local, ignored snapshot of public SEC facts and passages for Microsoft and Apple, FY2023–2025. Its shareable source manifest contains twelve financial inputs and provenance hashes. This first slice uses deterministic offline processing and lexical BM25 retrieval with zero paid model calls. Original Item boundaries, semantic risk interpretation, full learned retrieval and the final evaluation remain pending.

Initial validation: 46 local automated checks passed in 4.16 seconds. The application image built successfully after correcting the Uvicorn pin to meet the installed MCP server dependency. The first Compose startup created the services but stalled after one service started; Docker logs reported a connection-session healthcheck failure. This initial implementation commit did not claim human approvals or successful publication. Recovery and actual execution are recorded below. Automated tests use invented fixtures and mocked tool calls where indicated; they do not substitute for a real Docker journey or a human review.

## Step 5 — Run and verify the human-reviewed journey

On 24 October 2026, startup was changed to start one service at a time with bounded waits and a short readiness retry for transient proxy responses. All 53 local automated tests passed in 3.70 seconds. A further 37 implementation tests passed inside the networkless, read-only application image in 2.14 seconds; host Compose/launcher tests stayed on the host without exposing a Docker socket to the test container.

Actual Docker run `b1fd4eab632548328f354ef2794f679a` used SEC sources for Microsoft and Apple, FY2023–2025. Both human review gates completed for the exact plan and note versions recorded in the journey receipt. The manual client relays decisions; it does not independently verify human identity or the depth of source review.

The publisher saved one note, `c54ab4c70fc64615a95dfc8c462ba0c3`. The run made 18 actual HTTP MCP tool calls, checked all 18 displayed financial values and made zero model calls at zero model cost. All eleven runtime-readiness checks passed. The note remained available after restarting the application, and all four deployed MCP services returned HTTP 401 without credentials. Shareable receipts are in `evidence/`; full note content, checkpoints, credentials and confirmation text remain private.

These results establish this offline learning journey. They do not establish full capstone completion, semantic financial/risk correctness, original Item-boundary validation, hidden final performance, active containment testing or alert firing. Those remain separate work.

## Step 6 — Live provider and spending foundation

On 24 October 2026, defined the bounded live increment in ADR-002 and prepared the provider adapter, internal model gateway and dedicated SQLite usage ledger. The public OpenRouter catalogue confirmed the selected producing/critic model IDs, structured-output support and their observed price ceilings. Requests use a fixed endpoint and approved models, strict local schema validation, restricted routing and no automatic paid retries. Unknown charges retain their full reservation. No paid model calls occurred in this step.

Twenty-two mocked provider/ledger/gateway tests passed. Two secret-guard tests proved detection in staged content and reachable Git history using fictional keys in temporary repositories. The guard reads real private keys locally for pre-push checks without printing them. Credentials and private authorization configuration stay under ignored `.runtime/`; provider credentials are never tracked artifacts. Live specialist reasoning, deployment and an actual authorized journey are subsequent steps.

## Step 7 — Cited model reasoning and graph integration

Added strict, bounded model outputs for the planner, company search-query selectors, disclosure interpreters, writer and internal semantic critic. The graph retains deterministic MCP operations, isolated margin calculations and both human review gates. Evidence IDs, exact excerpts, issuer/year scope and qualitative narrative constraints are checked before note approval. Risk interpretation explicitly covers selected excerpts only. A passing AI critic is a model judgment, not independent gold.

Note edits retain the verified table, source references and mandatory limits. Editing a claim removes its old semantic verdict, updates the structured claim and requires a source-support review of the exact new body. Stale semantic hashes and failed checks cannot authorize publication. A provider failure reports authoritative charges/holds when available; an unreachable accounting service produces an unknown amount, not a false zero.

Thirty reasoning tests, seven live-graph tests and twenty-seven provider tests passed with fictional model responses. The latter include returned-model and token-ceiling checks with correct accounting for billed invalid output. Existing offline behavior remains covered by the regression suite. These are implementation tests, not evidence of an actual paid run. The optional deployment and review-screen update follow in step 8.

## Step 8 — Optional live Docker deployment and review screen

Added the optional Compose overlay, private disabled-by-default proposal/authorization helpers, stable internal gateway credentials and serial launcher. Only the gateway receives the provider-key file and provider-egress network. Its ledger uses a separate named volume; the gateway cannot mount research history. The API and browser expose explicit offline/live modes, safe accounting metadata and semantic-review issues. Unfunded, disabled, missing-key or unreachable live connections block creation without an offline substitute. A separate live manual session preserves the earlier offline receipt.

The complete local suite passed 153 tests in 7.35 seconds. Inside the new networkless, read-only application image, 116 tests passed in 2.72 seconds with fictional provider responses; host deployment/Git tests stayed outside the container. Nineteen actual runtime checks passed against the running optional stack, including rejected unauthenticated access, a blocked disabled live request, zero model calls, preserved offline publication, gateway-only key mount, no provider key in any container environment, separate ledger, worker/network restrictions and monitoring readiness.

Provider credentials remain in ignored private storage. Known-secret scans check staged content and reachable Git history before the commit/push. No paid model request or spending authorization occurred in this step. Actual live execution and its two human review decisions remain step 9, contingent on approval of the prepared spending proposal.

## Step 9a — Authorize live spending and preserve a stopped attempt

On 24 October 2026, the human spending gate authorized prepared policy `eed8a14ef850032984ce4ea14d49c164d7c5926c8ede046e1fdf5a2c484ad3e0`: US$1 total, US$0.50 per run, twelve calls and 250,000 tokens per run. The exact private configuration was enabled and the gateway reloaded. Nineteen enabled-runtime checks passed without creating research. Budget authorization did not approve a research plan or note.

The first actual planner request, run `58d5439f6eb9467eababb5179a9c0375`, stopped before producing a plan. Its US$0.0281344 reservation remains held because usage could not be confirmed. The original adapter collapsed diagnostics, so the original cause cannot be recovered. Its receipt is retained under `evidence/live_attempts/`. Read-only probes checked provider connectivity without requesting a model completion.

Added fixed, allowlisted HTTP/network/JSON/accounting diagnostic codes to the provider ledger, gateway client and run events. Raw provider bodies, headers, arbitrary upstream codes and private exception details remain excluded. No retry, spending-limit reset or release of the first reservation was introduced. All 189 local tests passed in 7.78 seconds using mocked provider responses. Actual continuation, plan review, note review and live publication remain pending.

## Step 9b — Record provider access refusal and verify persistence

After deploying the tested diagnostic update, made one deliberate new planner attempt under the same cumulative authorization. Run `89740c2115fb4f56afd16f2eccc9b04d` returned `provider_http_403` before producing a plan. It was not a retry under the original failed call ID. Its separate full reservation remains held alongside the first attempt: US$0.0562688 committed, US$0.9437312 left within the US$1 authorization. Zero recorded provider spend does not establish zero actual cost for uncertain calls.

The repeated HTTP 403 did not establish the exact provider access restriction. Further completion attempts stopped pending diagnosis. No plan approval, note approval or live publication occurred.

Restarted only the idle application and model gateway. The complete safe ledger summary and existing private note library were identical before and after restart; both prior approved notes remained. Nineteen deployed runtime checks passed again. Sanitized receipts preserve both attempts, and `evidence/live_attempt_verification.json` records the access failure, holds and persistence results. Credentials remain private. Step 9 is unfinished pending access diagnosis and the actual human review journey.

## Step 9c — Record an authorized retry

One separately authorized planner retry, run `84a7d9a88ac046e39e3b61d7c7692803`, used the same US$1 policy and again returned `provider_http_403` before producing a plan. Models, endpoint, policy and earlier reservations were unchanged. No further completion occurred in this retry.

The ledger now contains three uncertain attempts with US$0.0844032 held and US$0.9155968 remaining. Actual charges remain unconfirmed; zero reported spend is not proof of zero cost. Both existing private notes remain available. Nineteen read-only runtime checks passed and refreshed the current ledger evidence without requesting a completion. Preserved the full attempt and operator confirmation privately, and committed only sanitized technical receipts. Earlier restart proof remains labelled as a check after attempt two; this retry does not claim another restart test, successful live research or human plan/note approvals. The access restriction still needs diagnosis before the journey can continue.

## Step 9d — Strengthen secret scanning and access diagnostics

Strengthened the secret scanner to check all locally configured known provider credentials and the analyst credential. Six fictional-key tests prove staged/history detection and safe archive handling. Credential values and private credential inventories remain outside Git.

Planner run `85610a1da9094a208354fa3d7c3f5e34` again returned generic HTTP 403 before producing a plan. The ledger then held US$0.1125376 for four uncertain calls. Diagnostic validation and catalogue checks did not establish generation permission or a diagnosed restriction.

Added a bounded HTTP-403 diagnostic reader for fixed provider-reported hints. It can inspect immediate error fields, documented allowlisted metadata codes and one nested provider JSON wrapper in memory; conflicting or unknown hints remain generic. Raw responses, credential values and arbitrary upstream codes do not enter stored traces. All 229 local tests passed in 8.58 seconds with mocked provider responses where applicable. The provider route, privacy restrictions and reservation policy are unchanged. The access-failure receipt remains generic; no cause or successful live output is backfilled.

## Step 9e — Inspect OpenRouter directly and identify the reported refusal

Read-only provider diagnostics and an additional application planner attempt preceded a direct operator probe. No account settings were changed.

After a diagnostic-reader reload preserved the ledger and note library, planner run `e71ebfd9308e4ade87b85609e814cb49` returned generic HTTP 403. Direct operator diagnostic `operator-diagnostic-e193ed3b68d249058a519bb020873a96` used the same approved models/prices, research scope and reservation ledger. Selected provider error fields reported a Terms of Service refusal. The specific rule remains unverified; raw responses and account information are excluded from public evidence.

Five application planner attempts and one direct operator probe now retain US$0.1688064 in uncertain reservations, leaving US$0.8311936 under the original US$1 authorization. Zero reported spend does not establish zero actual charges. Both private notes remain available. Further generation stopped pending provider clarification; no model/provider substitution, control bypass, reservation reset, live human approval or publication occurred. Sanitized evidence is in `evidence/openrouter_access_diagnosis.json`; earlier receipts remain historical. The step does not claim successful live research or independent semantic evaluation.

## Step 10a — Review a supported replacement and retain the original budget

Selected Mistral Medium 3.1 for producing specialists and Mistral Large 3 for the internal critic through the exact `mistral/zdr` endpoint. Catalogue and endpoint metadata advertised structured outputs at the recorded prices. The earlier refusal remains unresolved. ADR-003 records the selection and its limitations.

Added a shared allowlist of reviewed model pairs and fixed provider routes. The dedicated SQLite ledger now counts every policy's charges and uncertain holds, freezes the original cumulative ceiling, preserves same-run limits across policy changes and carries accounting-anomaly blocks forward. Existing policy hashes remain immutable. Migration requires the unchanged original authorization before a new policy can initialize. The US$0.1688064 remains committed within the original US$1; changing models grants no new allowance.

All 113 mocked provider tests passed, including concurrent cross-policy reservations, old-ledger migration, retained holds and immutable ceilings. No replacement-model generation or private configuration switch occurred in this implementation step. Actual deployment, planner output and the two separate human decisions remain pending.
