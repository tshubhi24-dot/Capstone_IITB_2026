# Program Flow

This diagram distinguishes the C0 response path from gated C1/C2 publication. It describes the principal workflow and required acceptance behavior to preserve during cleanup; it is not proof of live correctness.

```mermaid
flowchart TD
    User[Analyst opens Gradio UI / FastAPI] --> Mode{Research mode}
    Mode -->|C0| Baseline[Fixed retrieval and verified financial preparation]
    Baseline --> C0Draft[Model response, citations, optional chart]
    C0Draft --> Display[Display baseline result and limitations]
    Mode -->|C1 or C2| Guard[Validate scope, advice and input boundaries]
    Guard -->|Unsupported| Decline[Decline or request clarification]
    Guard -->|Supported| Plan[Create editable research plan]
    Plan --> PlanGate{Human plan review}
    PlanGate -->|Cancel| End[Stop]
    PlanGate -->|Approve or apply valid edit and confirm years| Route{Orchestration}
    Route -->|C1| Single[One agent with bounded research tools]
    Route -->|C2| Lead[Lead dispatches parallel specialists]
    Lead --> Researcher[Researcher per company: MD&A]
    Lead --> Quant[Quant: financial facts and calculations]
    Lead --> Risk[Risk specialist per company: requested years]
    Researcher --> Handoff[Typed evidence handoffs and limitations]
    Quant --> Handoff
    Risk --> Handoff
    Single --> Evidence[Gather evidence / replan when needed]
    Handoff --> Evidence
    Evidence -->|Scope contradiction| Plan
    Evidence --> Writer[Draft note; insert figures from code]
    Writer --> Checks[Financial, citation and required claim review]
    Checks --> Eligible{Checks complete and passing?}
    Eligible -->|No, repair enabled and revisions remain| Writer
    Eligible -->|No, no automated repair remains| Blocked[Approval blocked: human edit or reject]
    Blocked -->|Edit| Checks
    Blocked -->|Reject| End
    Eligible -->|Yes| NoteGate{Review exact note}
    NoteGate -->|Edit| Checks
    NoteGate -->|Reject| End
    NoteGate -->|Approve| Sign[Bind exact content and review context]
    Sign --> Portal[Portal validates approval and eligibility]
    Portal --> Receipt{Confirmed matching receipt?}
    Receipt -->|Yes| Saved[Published]
    Saved --> Memory[Sync derived note memory; report failure separately]
    Receipt -->|Uncertain| Unknown[Outcome unconfirmed; reconcile before retry]
    Receipt -->|Explicit failure| Failed[Publication failed]
```

MCP hooks enforce tool permissions and budgets. Filing retrieval and EDGAR provide evidence; the Python sandbox computes; the portal alone holds the publication write tool. Checkpoints support resume. Optional memory and reviewed lessons remain separate from protected evaluation answers. Traces/metrics observe execution and do not grant publication permission.

See the [system architecture](architecture.md), [Phase 1 contracts](../migration/phase1/REPORT.md), and [three-story demonstration](../THREE_STORY_DEMO_SCRIPT.md). Live demo actions are outside the offline migration test gate.
