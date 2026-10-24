# First Docker learning journey: observed evidence

Recorded on 24 October 2026 for Microsoft and Apple, FY2023–2025. This is the fresh implementation's ordinary learning run, not the protected final evaluation.

| Receipt | What it records |
|---|---|
| [implementation_checks.json](implementation_checks.json) | 53 local tests and 37 tests inside the networkless application image. Fixtures and mocks remain labelled in the test sources. |
| [runtime_checks.json](runtime_checks.json) | Eleven passing checks for actual API/source configuration, budget, worker restrictions, network/ports, Prometheus scrape and Grafana readiness. |
| [two_company_journey.json](two_company_journey.json) | Actual published run, separate plan and note approvals, 18 tool calls, 18 checked financial values, zero model calls and zero model spend. |
| [journey_verification.json](journey_verification.json) | The same approved note remained after restarting the app; each of the four running MCP services rejected requests without credentials. |

Receipts contain technical results, approval states and exact payload hashes. They exclude credentials, account details and conversational text. Public SEC source provenance is in the [source manifest](../data/source_manifest.json).

The optional live increment has separate records: [implementation tests](live_implementation_checks.json), [deployed boundaries and ledger](live_runtime_checks.json), [explicit activation and first stopped attempt](live_activation.json), [second-attempt restart proof](live_attempt_verification.json), [authorized retry](live_retry_result.json) and [provider access attempt](provider_access_probe_result.json). Individual stopped-run receipts remain in `live_attempts/`; `live_two_company_journey.json` follows the latest live run. Four planner attempts stopped before a reviewable plan, and the latest returned HTTP 403 during access diagnosis. Reservations are held, actual charges are unconfirmed, and no successful live journey or live human approvals are claimed.

These checks do not establish semantic risk interpretation, original Item-boundary validation, full capstone targets, an independent held-out score, active attack containment or an exercised alert. See the [runbook and limitations](../docs/TWO_COMPANY_JOURNEY.md).
