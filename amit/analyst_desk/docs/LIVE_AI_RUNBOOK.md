# Run the live reasoning pilot

The optional live deployment adds model reasoning to the existing Microsoft/Apple journey. The offline mode and its approved note remain available. Use [ADR-002](ADR-002-LIVE_REASONING.md) for the design, scope and limits. Work remains on `Amit/analyst_desk`.

## Prepare privately, without spending

First prepare the reviewed SEC source snapshot as described in the [original journey runbook](TWO_COMPANY_JOURNEY.md). A current clone also needs the offline image built once before the live overlay, because unchanged MCP/worker services retain that image.

From this contribution folder, prepare a disabled proposal using a local private env file containing `OPENROUTER_API_KEY`:

```sh
python3 ops/prepare_live.py --prepare --provider-env /absolute/path/to/private.env
python3 ops/start_live.py --check
python3 ops/start_live.py --start
python3 ops/verify_live_runtime.py
```

The helper extracts only the requested key. It never evaluates an env file or copies the older application. The key file is inside ignored `.runtime/live/`, whose directory is private. Only the gateway receives its read-only bind mount; the key is not a browser token, model prompt, container environment value or Git artifact. The nonroot gateway reads this one file. Keep the private folder and its contents out of shared archives as well as Git.

Preparation and startup perform no model completions. The gateway starts disabled, and the API blocks live research creation before a model request. Read the printed proposal hash and model/spending limits. The prepared policy proposes $1 total, $0.50 per run, twelve model calls and 250,000 tokens per run. These application limits apply to this authorization, not every use of the provider key elsewhere.

## Authorize only the reviewed proposal

Actual spending requires an explicit analyst decision on the prepared proposal. The `--authorize` operation requires its exact `--expected-hash` and an operator-supplied `--human-confirmation`; see `python3 ops/prepare_live.py --help`. The helper records that decision privately and does not independently authenticate a human. A generic request to implement the feature is not recorded as a fabricated budget approval.

After a real authorization, run `python3 ops/start_live.py --start` again. It recreates the gateway to reload the exact configuration; starting it does not itself make a model call. `--disable` on the preparation helper revokes future requests after the same explicit gateway reload. It does not refund or erase earlier charges or pending reservations.

## Change a reviewed model profile without resetting spending

ADR-003 selects Mistral Medium 3.1 and Mistral Large 3 through the pinned `mistral/zdr` endpoint. Before switching an older installation, start the updated gateway once with its unchanged original policy. This safely initializes the cumulative ledger ceiling from that original policy; a new policy cannot perform the legacy migration.

Use `python3 ops/prepare_live.py --switch-profile mistral --expected-hash CURRENT_HASH`. The helper privately archives the old policy and authorization, retains credentials and all limits, and creates a disabled replacement with a fresh policy ID. It does not change the ledger or contact a provider. Review the resulting exact hash before recording activation and reloading the gateway. Record the actual basis of authorization truthfully: an explicit request delegating supported model selection within a previously approved, unchanged cap is distinct from a human review of the exact model IDs. Neither authorizes the generated research plan or note.

The dedicated ledger counts charges and holds across every policy ID within the original desk ceiling. Same-run limits survive a switch, and accounting-anomaly blocks carry forward. The API shows the actual allowlisted gateway pair and route; unknown or inconsistent metadata blocks live creation. The original refused route remains stopped, without provider fallback or location spoofing.

## Run one question through both reviews

Connect to <http://127.0.0.1:18080> with the existing private **analyst token**. Select **Live AI pilot** after the approved gateway becomes available. The analyst token authorizes the local UI/API; the provider key stays inside the gateway.

The manual client provides the same path:

```sh
python3 ops/journey_session.py --mode live prepare
python3 ops/journey_session.py --mode live status
```

Live sessions are stored separately in `.runtime/live/session.json`; their public receipts use `evidence/live_two_company_journey.json`. Offline session files and earlier receipts remain separate. Repeating preparation reuses the saved session; creating another run requires an explicit new-run choice and consumes the same authorized balance.

The model-generated plan pauses for a real approve/edit/reject decision. Only after that approval do company branches choose search queries, read actual MCP evidence, calculate verified margins, interpret selected disclosure excerpts and draft a cited note. The separately configured model critic checks the exact narrative and source package. A failed check blocks note approval.

The finished note pauses for a separate decision. Edit only the claim bullet text while retaining the financial table, source references, headings and mandatory limitations. An edit invalidates the old semantic verdict and approval. The exact changed claims need another model review, which consumes the same original call/token/spending limits. The sole publisher saves only the exact approved version.

## Inspect accounting and failures

The UI shows actual model requests, tokens, provider-reported costs and held reservations. The gateway's dedicated SQLite volume retains the ledger across restarts. A timeout or uncertain charge keeps its reservation; an unreachable accounting service is shown as unknown, not zero. No automatic paid HTTP retries or offline substitution occur.

Failure traces include fixed diagnostic codes for HTTP status categories, connection failures, malformed responses and missing or inconsistent accounting. For HTTP 403 only, the gateway may inspect a bounded JSON error in memory and retain a fixed provider-reported hint for privacy, region, account, model access or content policy. This hint is not a verified cause. Unknown, oversized, ambiguous or unreadable bodies retain the generic status code. Only allowlisted codes enter the ledger and run events; provider response text, headers and arbitrary upstream codes are excluded. An uncertain call keeps its complete reservation even when a diagnostic code is available. Preserve stopped-run receipts before deliberately creating a new learning run; a new run shares the original cumulative authorization and does not clear earlier holds.

Typical requests use seven model calls before repairs or edits: planner, company query selectors, disclosure interpreters, writer and critic. Two bounded automatic draft repairs remain subject to all original limits. Successful duplicate call IDs return their recorded response without another provider charge. A failed or ambiguous call cannot silently retry under the same ID.

Risk and writer generation select identifiers from a finite menu of code-selected verbatim quote windows. The gateway schema restricts these identifiers; code expands them into canonical source IDs and unchanged quotations. Unknown selections, duplicate sources, wrong periods and unsupported prose still fail. A relevant exact quote does not establish semantic support: the independent model critic and final human note review remain required. The menu narrows the evidence available to generation, which must be stated among the note's limits.

An explicitly requested continuation can resume a stopped content-validation failure with `python3 ops/journey_session.py --mode live continue RUN_ID --expected-plan-hash APPROVED_HASH`. It checks the failed checkpoint, exact original plan/request/source and prior human approval, then retains the same run, usage and cumulative ledger. It cannot approve a plan or note, reset budgets, restart a published/rejected run, or retry a provider/uncertain-accounting failure. A revised prompt has a distinct call hash and its new cost remains counted. Earlier successful identical responses can be reused from the ledger. This is deliberate continuation after an inspected implementation correction; no automatic recovery is enabled.

A separate explicit `--retry-transient` flag permits one critic-only HTTP 429 retry after cooldown. It requires the matching failed critic checkpoint/event, its retained uncertain reservation, the exact checked draft, unchanged plan/source/request and remaining original limits. The new stable critic call ID is counted; the old hold is never released by retry. Successful accounting continues to show that hold and distinguishes observed tokens from reserved allowances. HTTP 403, terms/region refusals, other failure stages and a second transient retry remain excluded. A failed critic reaches blocked note review if fewer than two calls remain for a complete rewrite-and-critique cycle.

If that single retry also returns HTTP 429, a separately selected reviewed critic policy can be considered under the original limits. Prepare `mistral-large2407` with the switch helper, record the actual authorization basis and reload the gateway. This reviewed profile tightens context bounds without raising any budget. Measure the unchanged full critic payload locally before spending. The new policy's `policy_hash` is exposed by the gateway budget; it excludes the `enabled` field entirely and differs from the preparation helper's activation `proposal_hash`.

Use `python3 ops/journey_session.py --mode live continue RUN_ID --expected-plan-hash APPROVED_HASH --replace-critic-policy DEPLOYED_LEDGER_POLICY_HASH` only for the same frozen critic checkpoint. This is a distinct one-time operation, mutually exclusive with `--retry-transient`. It must retain both failed-call reservations, require the same producer and exact reviewed replacement critic/provider, bind the deployed policy hash and draft, and fit the remaining original calls/tokens/spending. It cannot retry HTTP 403, change the plan or note, clear a hold or create a new run. A passing verdict still pauses for separate human note approval; another provider failure stops the run.

If the original twelve calls are exhausted, another model choice alone cannot authorize spending beyond that run limit. The current teaching implementation supports one separately approved exact critic extension. Prepare the `google-critic` profile, record the genuine delegated model-selection basis and reload it with the unchanged original policy limits. Producing roles remain on Mistral; the Google critic is pinned to `google-ai-studio`, with optional reasoning disabled and all completion tokens accounted.

Run `python3 ops/critic_extension.py --prepare --run-id RUN_ID`. This read-only operation saves the complete captured critic request privately and returns a reviewable proposal/hash. It binds the exact draft, plan, model policy, call ID, full request hash and complete existing ledger checkpoint. Its sole exception permits call thirteen and at most 300,000 total reserved/observed tokens for that critic, preserving the original twelve-call/250,000-token request and ledger rows. Original US$1 desk and US$0.50 run dollar caps and every old hold remain intact.

Only after actual explicit human approval of that proposal, use the helper's `--authorize --expected-hash PROPOSAL_HASH --human-confirmation TEXT` operation. It rechecks the proposal and uses trusted local Docker access to append the grant; the application exposes no grant-minting HTTP route. Then explicitly continue with `python3 ops/journey_session.py --mode live continue RUN_ID --expected-plan-hash APPROVED_HASH --critic-extension GRANT_ID`. The grant is consumed atomically with its exact reservation. A changed request, replay, call fourteen, provider refusal or failed/uncertain outcome cannot obtain another allowance. Final note approval remains a separate gate.

Run `python3 ops/check_secrets.py --history` before each commit/push. It checks the real local provider and analyst credentials, plus regular nonsymlink key files in private `.runtime/live/retired/` and `.runtime/live/key_vault/`, against staged content and reachable history without printing their values. Separately stored keys are checked even if they have never been active. Keep all credential archives private so key replacement does not remove them from later scans. Replacing the gateway credential must preserve the existing authorization, ledger and all reservations; reload the gateway to use the replacement file. Provider refusals require diagnosis; automatic credential fallback is disabled. The guard supplements `.gitignore`; it is not a general-purpose secret detector for unknown credentials.

The model gateway restricts the provider URL/models in code. Its egress network is not a domain firewall. Learned semantic retrieval, trained injection/safety classifiers, full original-section validation, independent semantic evaluation and crash recovery during active operations remain future work. Exact quotations establish provenance; internal model criticism and human approval do not establish an independent benchmark score.
