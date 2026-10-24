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

Validation: 46 local automated checks passed in 4.16 seconds. The application image built successfully after correcting the Uvicorn pin to meet the installed MCP server dependency. The first Compose startup created the services but stalled after one service started; Docker logs reported a connection-session healthcheck failure. Engine recovery and live readiness verification remain in progress. No actual plan approval, note approval or publication has occurred. Automated tests use invented fixtures and mocked tool calls where indicated; they do not substitute for a real Docker journey or a human review.
