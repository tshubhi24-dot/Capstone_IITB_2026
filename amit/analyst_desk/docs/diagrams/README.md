# Analyst Desk architecture drawings

These are the editable Mermaid sources for the [proposed architecture v1](../ARCHITECTURE_V1.md), prepared on 22 October 2026. They describe the design to implement and validate; they are not receipts for a running full stack.

- [Overview drawing](architecture-v1-overview.png), [scalable vector version](architecture-v1-overview.svg) and [editable layout source](architecture-v1-overview.dot): research workflow, tool services and supporting state/operations.
- [Research workflow](architecture-v1-workflow.mmd): numbered path, parallel company research, bounded replan and repair, human approval and development-only lessons.
- [Docker deployment](architecture-v1-deployment.mmd): application and MCP services, persistent data, isolated calculation worker, source ingestion, model access, monitoring and evaluator boundary.

Both drawings are also embedded in the architecture document. Edit the `.mmd` source and its corresponding embedded block together.

## Reading the boundaries

- Solid arrows show a request, processing dependency or data access. Dotted arrows show supporting state or development-learning relationships; they do not authorize a tool call.
- Human decision nodes pause the workflow. Failed checks, rejected plans and rejected notes do not publish.
- Research, quant, risk, writer and critic are logical roles in the app container. A role is not a separate Docker container.
- The four MCP services expose domain capabilities. The calculation service uses a shared queue to reach the networkless worker; no Docker socket is passed into the stack.
- The proposed app-only external model route still needs deployment configuration. Its destination/model allowlist is enforced in application code; the drawing does not claim a network firewall restricts destinations.
- Source ingestion is separate from a research run. Source snapshots are frozen for evaluation. Model weights are preloaded before isolated runtime use.
- The full protected dataset, gold answers, labels and outcome judgments stay evaluator-owned. Each submitted ordinary question and its output may enter its isolated run state/checkpoint/audit under a defined access/retention policy; they never become shared preferences, lessons or approved-note history. Final-case outputs stop at review.
