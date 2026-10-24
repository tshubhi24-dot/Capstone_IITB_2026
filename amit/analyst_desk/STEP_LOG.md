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

## Step 10b — Prepare private switching and actual model metadata

Added an explicit stale-hash-checked profile switch. It archives the prior policy and operator authorization privately, preserves keys and every limit, creates a fresh disabled model policy, and leaves ledger/history files untouched. Preparation remains compatible with either reviewed pair. Startup still makes no research requests. The API now obtains model IDs, profile and provider from validated gateway metadata; unknown or inconsistent metadata blocks live creation. Runtime checks derive their expected models from the prepared policy.

All 261 local tests passed in 9.06 seconds using mocked provider responses where applicable. This includes 49 deployment/API tests for switching, private archives, unchanged limits/keys, metadata failures and offline regression. Documentation records the required original-policy ledger migration and distinguishes delegated model selection from human review of generated research. No replacement-model paid request occurred in this implementation step.

## Step 10c — Activate the replacement and inspect the actual first plan

Reloaded the gateway under the original authorization before staging the replacement. Cumulative-ledger migration preserved all six uncertain reservations and both notes. Activated Mistral policy `a6602461f47ee912cdd7c7bbfc57cdbedd1549a6a69277267b74736580ba006e` without a new spending allowance. Policy activation did not approve a research plan or note.

All nineteen deployed runtime checks passed with the actual Mistral metadata before research creation. The first ordinary Mistral planner request, run `67904e6d14b34fc5a8397fa344bf897b`, returned a schema-valid plan: 528 observed tokens and US$0.0006448 reported cost. Its plan incorrectly described FY2025 as potentially partial/forward-looking and mixed quarterly filings into the fixed annual scope. Operator review caught this before human approval. The exact original plan remains unchanged and unapproved; its receipt is preserved. A focused planner-context correction is needed before another deliberate plan request, rather than approving this version.

The old US$0.1688064 remains held; cumulative reported spend is US$0.0006448 and US$0.8305488 remains within the original US$1 cap. Actual past charges for uncertain calls remain unknown. Both prior notes are unchanged; no live note was published. Public activation/runtime/first-plan receipts contain no key or private research history.

## Step 10d — Ground the planner in verified annual source coverage

The live planner now receives code-owned coverage for each requested issuer/year, built from compatible canonical annual revenue and operating-income pairs. It includes exact fiscal periods, fact IDs and the source fingerprint, while expressly marking original risk sections as unverified. Missing or mismatched financial coverage stops before a paid call. Instructions prohibit quarterly substitution or estimating already-reported annual inputs. A mandatory scope notice accompanies the returned plan; model output cannot replace trusted coverage. These measures guide and constrain the context, but do not guarantee every freeform sentence is correct.

Human scope edits recompute coverage and create a new review hash without another planner call. All 267 local tests passed in 9.00 seconds, including six regressions covering source grounding, missing inputs, model attempts to replace coverage and scope-edit freshness. The first actual plan remains unchanged and unapproved; a deliberate new plan will use this corrected context within the same original cumulative cap. No human decision or publication is implied by this fix.

## Step 10e — Approve the grounded plan and enforce exact citations

After deploying the grounding correction without changing ledger totals or prior notes, run `2b3a7913d508441ab0e7ce0c7d5120fa` returned annual-scoped plan `80d3749f49399aef7d155696cbd52ce2745f78c4695419ef99292dd8344528bd`, costing US$0.000904. The human plan gate accepted that exact version. This approval did not cover the final note.

Research reached the first issuer's disclosure analysis and stopped on an exact-quote/source-membership failure. Four successful billed model responses in this run totalled 6,892 tokens and US$0.0040784; thirteen MCP calls occurred before the stop. The already-billed cached response was inspected and revalidated locally without a paid retry. Its cited prose did not satisfy the supplied-source/quotation check, so it was not accepted as research evidence. No note was approved or published.

The run, approved plan and all costs remain preserved. A bounded citation-selection improvement and deliberate continuation under this same approved plan/run are next; the original financial, quote, scope, prose and semantic checks must remain. The US$1 cumulative ceiling and every old uncertain hold remain in force. Both prior notes are unchanged.

## Step 10f — Constrain citations and preserve approved-run continuation

Risk and writer model outputs now select stable quote identifiers from a finite code-owned menu. At most two exact windows per source are offered, each bounded to 240 characters; long-sentence fragments are marked. The gateway schema enumerates allowed identifiers. Code resolves them into original source IDs and unchanged quotations, then applies the existing duplicate-source, period, prose and provenance checks. This prevents accepting rewritten quotations; it does not prove a selected quote supports the model's interpretation. Generation has narrower evidence and the displayed note limits state this.

The independent critic still sees the full note and every claim. Provenance is checked against the full retained evidence first; the critic receives complete selected text for every cited source and every canonical fact used by the table. Uncited passages are omitted and counted, without truncating cited context or raising limits. Actual cached-corpus preflight found 24 quote options per issuer and 72 writer options; no provider call was used for this sizing check.

Added an authenticated, explicit content-failure continuation with the existing approved plan hash. It verifies the failed LangGraph checkpoint, unchanged request/plan/source, durable human approval and remaining original counters; it resumes the failed node without another plan vote. Legacy runs use their retained accepted decision and checkpoint evidence. Provider/uncertain-accounting failures, altered scope, exhausted budgets and publication stages cannot qualify. No automatic retry or new spending allowance is introduced; final note review remains mandatory.

All 307 local tests passed in 10.91 seconds. Tests cover enum/quote provenance, wrong-year and repeated selections, retained full critic modality, continuation without repeating earlier model stages, immutable counters, legacy approval evidence, stale checkpoints, authentication and blocked provider failures. Actual continuation and a separately approved final note remain pending this implementation commit.

## Step 10g — Diagnose a temporal-phrase false positive without replacing output

Deployed the citation/continuation revision and passed all nineteen runtime checks. The exact old plan approval and four billed calls remained. Explicitly continued the same run once. Finite citation choices passed, but prose validation stopped on "between the two years" as though it were an unchecked financial quantity. The run then retained five billed calls, 11,113 observed tokens, sixteen MCP calls and US$0.0061524 reported cost.

Corrected this narrow false positive: the exact temporal-pair idiom is allowed only when two distinct integer comparison periods are supplied by code. The existing claim verifier still requires citations for that issuer and both years. Financial amounts, doubled revenue, other number words and duration claims remain blocked. Human edits use the same scoped rule and still invalidate the semantic verdict. No model wording, evidence, approved plan or financial assertion was changed.

Locally revalidated the unchanged cached response successfully with zero provider calls; its content hash is recorded in `evidence/model_switch_continuation_review.json`. A subsequent deliberate continuation can reuse that successful cached call rather than charge for it again. All 311 local tests passed in 10.51 seconds, including scoped/unsourced temporal language, wrong-period citations, financial amounts and duration regressions. Lifetime reported spend is US$0.0067972, old uncertain holds remain US$0.1688064 and US$0.8243964 remains under the original US$1. Both prior notes are unchanged; no live note is approved or published yet.

## Step 10h — Expand known-secret scanning

The secret guard now includes every regular nonsymlink key in the private vault alongside active, retired and analyst credentials. Twelve fictional-key tests passed in 1.62 seconds, including a never-active vault key detected in staged files and removed historical blobs without disclosing its value. No key, private index or confirmation text is a Git artifact. The guard scans known real credentials locally before each push without printing them.

## Step 10i — Preserve the current pilot checkpoint before the next increment

After the temporal-reference deployment, explicitly continued the same approved run. It reused the successful Microsoft risk response from cache without another charge, obtained the Apple risk response, and reached writer validation. Both issuer risk outputs passed the finite-quote/provenance checks. The writer included calendar dates in qualitative prose, which this live slice disallows; the exact response was rejected. Its dates were not silently removed or accepted. The critic has not yet generated a verdict, no live note approval occurred, and no live note was published.

Current run totals are seven billed model calls, 29,862 observed tokens, twenty-two MCP calls and US$0.014604 provider-reported cost. There was one actual human plan approval and two explicit continuations. Lifetime reported spend is US$0.0152488; old uncertain holds remain US$0.1688064; US$0.8159448 remains under the original US$1 cap. Both prior notes are unchanged and all nineteen current runtime checks pass. `evidence/live_pilot_status.json` records the current checkpoint; earlier failures remain historical evidence.

The checkpoint remained stopped before writer correction. The remaining live-journey work was writer validation, model criticism, exact-note approval, publication and restart verification. Learned retrieval/memory, robustness, independent E1–E4 evaluation and final team deliverables remain later capstone work.

## Step 10j — Enforce the writer's prose rules at generation

The writer now receives a schema pattern excluding ASCII date digits, newlines and markup in claim text, plus clear instructions to keep periods/figures in citation metadata and the code-owned table. Full local Unicode/quantity/provenance validation remains authoritative. Risk schemas, prompts and cached responses are unchanged. The earlier billed writer response is preserved; no dates are silently removed from it.

Fifty-eight reasoning tests and twenty-three live graph tests passed, including eight new writer cases. No paid call or human note approval occurred in this implementation step. A separate read-only source review identified overbroad scope wording in a provisional risk observation; the writer must refine provisional interpretations against the supplied evidence before the configured critic assesses the exact final draft.

## Step 10k — Refine provisional risk claims before exact-note criticism

The writer now returns a source-grounded revision for every supplied provisional risk claim, alongside its summary claims. The schema fixes the expected count and allowlisted claim IDs; code requires each exactly once, retains issuer/period/category metadata, resolves finite quote choices and verifies evidence from both comparison periods. Writer prose rules apply to the revisions too. The prompt explicitly forbids inferring entire risk-profile or scope/framing consistency from selected windows. Empty input requires an empty revision list. Original billed observations are retained unchanged in the draft audit fields.

The final note uses the writer's newly generated revisions. The independent critic receives that exact body and all revised claims with their full cited selected-source text; its verdict remains a fallible model judgment. The writer output ceiling is 3,200 tokens, within the original 4,096-token configuration. Existing risk prompts/schemas and approved plan are unchanged. Sixty-six reasoning tests and twenty-four live workflow tests passed, including missing/invented/duplicate IDs, wrong periods, protected metadata, retained originals and the critic's exact revised input. Actual continuation follows this implementation commit; no human note approval is implied.

## Step 10l — Bind revision citations to their exact comparison periods

The first corrected writer response passed date/prose schema checks but selected a fiscal 2023 source for a fiscal 2024–2025 revision. Local period validation stopped it before criticism. The already-billed response was inspected without another request and preserved. Run totals then reached eight calls, 44,953 observed tokens and US$0.0217348 reported cost; the old holds and prior notes were unchanged. The stop is recorded in `evidence/writer_revision_scope_stop.json`.

Replaced the revision array with fixed code-owned claim keys. Each revision now has a separate earlier and later quote slot, with finite enums restricted to its original cited source IDs, issuer and respective year. Financial facts and unrelated same-year passages cannot enter these risk slots. Local keyset, slot membership and provenance checks remain authoritative. Empty input requires an empty object. Instructions also prohibit scope/framing/profile similarity assertions from selected windows. Original observations and invalid billed outputs remain unchanged.

Seventy reasoning tests and twenty-four live workflow tests passed. Four calls remain within this run's original twelve-call limit; the next deliberate continuation will resume only the writer, followed by the configured critic. No cap reset, provider switch, note approval or publication occurred in this implementation step.

## Step 10m — Preserve a checked draft and permit one explicit critic rate-limit retry

The period-specific writer generated a valid revised draft. Independent code verification passed all eighteen financial values plus source, period, prose and body consistency. Provisional risk observations remain in its audit fields, while the displayed note uses source-grounded refinements. The first Mistral Large critic request then returned HTTP 429 before a verdict. Its full US$0.035768 reservation remains uncertain and counted; no automatic HTTP retry occurred. The frozen draft was read from the failed checkpoint and checked locally without a paid request. Evidence is in `evidence/critic_rate_limit_stop.json`.

Added one explicit critic-only rate-limit retry. It binds the original human plan approval, source/request, failed checkpoint/event, exact checked draft and retained reservation. It uses a stable new counted call ID, excludes HTTP 403/other failures, cannot be repeated and keeps the original limits. Success reconciles actual calls/charges/holds with the ledger while observed tokens remain separate from held allowances. Unavailable reconciliation is unknown, never a refund. Automatic rewrite is blocked unless a full writer/critic pair fits the remaining call limit.

All 362 local tests passed in 13.59 seconds, including twenty-four new workflow/API/client cases for frozen legacy drafts, exact reservations, new IDs, unchanged counters, refusal cases and separate note approval. A read-only peer code review found no blocking issue. This commit does not claim an AI verdict, human note approval or publication; one deliberate critic retry follows.

## Step 10n — Prepare a supported critic within the last original call allowance

The one explicit Large 3 retry returned HTTP 429 again. It produced no verdict; both uncertain holds remain. The run has eleven calls, 60,185 observed tokens and 195,257 tokens including gateway reservations. Reported run spend is US$0.0290148 and its holds are US$0.071536. Lifetime reported spend is US$0.0296596, holds are US$0.2403424 and US$0.7299980 remains under the original US$1. Both prior notes are unchanged; no live note approval or publication occurred.

Added a reviewed Large 2407 critic profile with the same producer and exact provider route. It tightens the prompt ceiling to 49,152 tokens and message/schema bytes to 45,056 without raising any original cap. The exact frozen critic payload is 23,285 bytes with seven claims and nineteen full cited evidence records. Authenticated catalogue and public endpoint checks found the candidate listed with structured output support at US$2/US$6 per million input/output tokens; no generation request was made. The final 51,152-token reservation would reach 246,409 tokens at twelve calls, preserving both older holds. Policy metadata exposes the immutable ledger hash and relevant limits so a separate controller operation can freeze and verify them.

All 143 targeted provider/deployment tests passed, with one Docker integration check excluded from this local test run. Tests preserve the two uncertain holds, accept only the final bounded reservation and block call thirteen. Runtime policy activation and a distinct, explicitly controlled critic replacement follow separately. Final note approval remains pending.

## Step 10o — Bind one final critic continuation to its reviewed policy

Added the distinct authenticated `--replace-critic-policy` continuation, mutually exclusive with the consumed transient retry. It requires the exact deployed Large 2407 policy hash and reviewed pair/route, a different immutable policy ID, the same producer, original human approval, unchanged source/request/checkpoint and exact checked draft. Both earlier critic HTTP 429 call IDs must remain uncertain; no hold, charge, token allowance or original cap can be refunded or increased. The gateway's authoritative reserved-token total determines whether the last call fits. The queued operation rechecks its frozen policy and draft; its stable new call purpose includes the policy hash. No automatic fallback or new run is created, and HTTP 403 remains excluded.

All 400 local tests passed in 17.87 seconds. The replacement regressions cover exact policy, retained accounting, changed inputs/caps, refusals, distinct call IDs, queued rechecks and mandatory note approval. A separate read-only review found no blocking issue. Deployment and the actual final critic call follow this implementation commit; no successful AI verdict or note approval is claimed here.

## Step 10p — Prepare a different-provider critic and an exact extra-call grant

Deployed the tested replacement and passed all nineteen runtime checks. The ledger and two prior notes were unchanged. The explicit Large 2407 critic request returned HTTP 429 as well, without a verdict. It retained US$0.110304, bringing this run to twelve calls and 246,409 accounted tokens. Lifetime reported spend remains US$0.0296596; uncertain holds are US$0.3506464 and US$0.6196940 remains under the original US$1. No further request was made after the original call limit was reached. The failure is recorded in `evidence/critic_replacement_rate_limit_stop.json`.

Prepared Google Gemini 2.5 Flash as the critic, with exact per-role provider routing and the producing model unchanged. Authenticated/public catalogue checks advertise structured outputs at US$0.30/US$2.50 per million input/output tokens. Optional reasoning is disabled; every reported completion token still counts. Catalogue checks performed no generation and do not guarantee access or correctness.

Added an append-only, operator-authorized grant for one exact critic request. Its proposal binds the original plan/draft, new immutable policy, exact call ID and full gateway request hash, plus all existing ledger rows and retained accounting. Original request and `run_limits` stay twelve calls and 250,000 tokens. Only this exact approved critic may reach thirteen calls and 300,000 tokens; atomic consumption prevents another spend. All old holds and the original US$1/US$0.50 dollar caps remain. The proposed reservation totals 297,561 tokens and at most US$0.0197456. The private preparation helper has no paid-call operation and the application has no grant-creation HTTP route. Actual grant approval remains pending.

The provider/deployment/helper checks passed 158 targeted tests with seven Compose checks excluded. Tests cover exact request matching, concurrent consumption, unchanged original limits/holds, restart/cache behavior, uncertainty, duplicate grants and blocked call fourteen. A separate read-only review found no blocker. The configuration is prepared under the existing model-selection delegation; no extra-call grant or final note approval has been recorded.

## Step 10q — Admit only the separately approved frozen critic request

Added strict, mutually exclusive `--critic-extension GRANT_ID` continuation support in the authenticated API and manual client. Admission requires the gateway's approved, unconsumed grant, the exact Google profile/routes and immutable policy, the same original approved plan/source/request/checkpoint and checked draft, all three failed critic reservations, unchanged dollar accounting and the exact reconstructed call/request hashes. The queued operation rechecks this proof. Original request counters remain twelve calls and 250,000 tokens; only the bound critic identifier receives the approved thirteen-call/300,000-token exception. Traces distinguish this separate approval from the original spending authorization. No automatic provider retry or note approval is introduced.

All 462 local tests passed in 23.07 seconds, including the provider/helper and 175 workflow/API/client checks. Cases cover missing/unapproved/consumed grants, altered policy/input/ledger/scope/caps, HTTP 403, frozen-checkpoint changes, successful accounting with retained holds, exact request binding and mandatory final note approval. A separate read-only review found no blocker. Deployment and read-only proposal preparation follow this implementation commit; applying the grant and making the extra critic call still require explicit user approval.

## Step 10r — Record the approved Google response and validation stop

Deployed the Google configuration and passed all nineteen runtime checks. Exact proposal `158eb058` received human approval for one additional critic call. Its append-only grant continued the same frozen draft. Google AI Studio returned HTTP 200 with a normal finish, 6,934 prompt tokens, 903 completion tokens, no reasoning tokens and US$0.0043377 cost. The grant was consumed once; original request/ledger limits and all old reservations remain.

The gateway rejected the output with `model_output_invalid` and retained the charge, but the earlier implementation had discarded its body. Read-only provider metadata independently confirmed model, finish, token counts and cost. Stored content was unavailable because logging was disabled for that request. The exact formatting failure remains unknown; explanation length is an unproven hypothesis. No response was fabricated or marked passed.

This run has thirteen calls and 254,246 accounted tokens, including three uncertain critic holds. Known provider tokens total 68,022; the app's earlier failure display omitted the 7,837 billed invalid-output tokens, which the next increment corrects from authoritative accounting. Lifetime reported spend is US$0.0339973, retained holds are US$0.3506464 and US$0.6153563 remains under the original US$1. Both old notes are unchanged; no live note approval or publication occurred. `evidence/google_critic_attempt.json` records the safe facts without account/key identifiers.

Separate authorization covered one further exact critic request, with absolute bounds of fourteen calls and 350,000 tokens and at most US$0.0197456 additional cost. Both original dollar caps remained. Implementation of the bound amendment and private rejected-output diagnostics followed before execution.

## Step 10s — Preserve rejected output, reconcile known usage and bind the authorized retry

The gateway now settles known billing together with private validation diagnostics. It records bounded generation/finish metadata, a content hash and exact failure phase/schema path. Only bounded, credential-scanned failed message text can enter private quarantine; headers, hidden reasoning, raw provider errors and credentials are excluded. The audit is operator-only and absent from HTTP/API/public receipts. Invalid output remains rejected and charged, with a consumed grant. Malformed Unicode in diagnostic content cannot prevent known usage from settling.

Failure reconciliation now records an authoritative billed invalid call's observed tokens and cost, removes only its own temporary client reservation and retains all three earlier uncertain holds. It validates the full known usage and accounting totals before changing derived run metadata. The critic prompt explicitly requests brief reasons within eight to two hundred characters, exact supplied identifiers and JSON without fences or extra fields; local schema and source checks remain unchanged. This is a prevention measure, not a retrospective diagnosis of the lost response.

Implemented one separately authorized exact call-fourteen amendment, preserving the original consumed grant and approval in append-only history. It binds the same frozen draft/plan/source/policy, the known billed invalid thirteenth call and full current ledger checkpoint. It allows fourteen calls and 350,000 tokens only for the new exact request; the worst reservation total is 305,398 tokens and US$0.0197456 additional. Original request/ledger limits and both dollar caps remain unchanged; call fifteen is blocked. The amendment required separate human authorization. The private helper archives the previous proposal and receipt rather than replacing their history.

All 500 tests passed in 26.24 seconds with Compose v5.5.1 available. Tests cover private diagnostics/credential exclusion, malformed Unicode, retained rejected billing, parent/grant immutability, exact call fourteen, stale/mismatched requests and blocked call fifteen. A separate read-only review found no blocker. Deployment, derived-accounting reconciliation and the authorized attempt followed this implementation commit.

## Step 10t — Pass the actual critic and present the complete exact note

Deployed the tested fixes with Docker engine 29.8.1 and passed all nineteen runtime checks. Reconciled the settled thirteenth call to 68,022 known run tokens without changing the draft, request, plan or earlier holds. Prepared the separately authorized fourteenth-call amendment, preserved the consumed first grant and executed the one bound Google request.

Google Gemini 2.5 Flash returned a valid verdict supporting all seven narrative claims with no reported issues. The exact displayed body remained unchanged from the verified writer draft; code independently passed all eighteen financial values. The graph paused for review of note `2a248617fe85e8c107a6a761baac475ef51debe9181a1676ee00a8c00f6273ac`. Exported its full exact body, original SEC filing links, exact quotations and all actual model explanations privately for human review. Original section boundaries, partial evidence, fiscal comparability and economic-materiality limits remain explicit. Internal criticism is not independent gold evaluation.

At that review snapshot the same run retained fourteen calls, 75,452 known provider tokens, twenty-three MCP calls and US$0.0365539 reported cost; all three earlier holds remained. Both prior notes were unchanged. `evidence/live_critic_review.json` records this actual result without publishing the note body. The human note gate then approved that exact version; the publication and persistence receipt follows as a separate step. No approval is inferred from a model verdict.
