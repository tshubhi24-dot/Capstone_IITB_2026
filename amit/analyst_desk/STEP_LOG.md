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
