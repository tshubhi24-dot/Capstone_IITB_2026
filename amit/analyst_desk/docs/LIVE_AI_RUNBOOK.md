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

Failure traces include fixed diagnostic codes for HTTP status categories, connection failures, malformed responses and missing or inconsistent accounting. Only allowlisted codes enter the ledger and run events; provider response text, headers and arbitrary upstream codes are excluded. An uncertain call keeps its complete reservation even when a diagnostic code is available. Preserve stopped-run receipts before deliberately creating a new learning run; a new run shares the original cumulative authorization and does not clear earlier holds.

Typical requests use seven model calls before repairs or edits: planner, company query selectors, disclosure interpreters, writer and critic. Two bounded automatic draft repairs remain subject to all original limits. Successful duplicate call IDs return their recorded response without another provider charge. A failed or ambiguous call cannot silently retry under the same ID.

Run `python3 ops/check_secrets.py --history` before each commit/push. It checks the real local provider and analyst credentials against staged content and reachable history without printing their values. It supplements `.gitignore`; it is not a general-purpose secret detector for unknown credentials.

The model gateway restricts the provider URL/models in code. Its egress network is not a domain firewall. Learned semantic retrieval, trained injection/safety classifiers, full original-section validation, independent semantic evaluation and crash recovery during active operations remain future work. Exact quotations establish provenance; internal model criticism and human approval do not establish an independent benchmark score.
