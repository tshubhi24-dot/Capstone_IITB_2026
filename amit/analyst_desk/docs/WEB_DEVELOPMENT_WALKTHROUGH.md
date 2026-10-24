# Run a public development case in the web app

The research web app is the analyst's working interface. It submits requests to FastAPI, which runs the same checkpointed LangGraph workflow as the operator API. Development verification may inspect persisted records separately, but the request and human decisions in this walkthrough use the web controls.

## Selected case

Use **KDEV018**, the next registered risk-comparison case after KDEV017: Apple, fiscal 2024 and 2025.

> Compare AAPL Item 1A risk disclosures in fiscal 2024 and fiscal 2025. Identify supported additions, removals or material changes with citations to both versions. Separate wording changes from economic changes and state when the evidence is insufficient.

## Analyst actions

1. Open the local desk at `http://127.0.0.1:18080/` and connect using the locally generated analyst token. Keep credentials outside screenshots and Git.
2. Select **Live AI** and **Public development rehearsal**. Choose **KDEV018 · AAPL · 2024, 2025**. Check that the exact question and scope are loaded, private analyst memory is disabled, and no frozen playbook is selected. Do not change the registered question or plant a failure.
3. Click **Create a plan**. This requests live planning within the existing authorized budget. Wait for **Review the research plan**.
4. Read the outline, scope, source caveats and exact version. The analyst can edit the outline and save it for fresh review, approve the displayed plan, or reject it. Approval resumes research; creating a plan alone does not approve it.
5. Inspect the research trace, verified financial values, cited source passages and model critic outcome. The critic is a fallible model judgment, not an independently calibrated outcome label.
6. Review the resulting note in the app. Development notes cannot publish. Request an actual correction only when needed; saving changed claim wording invalidates the earlier review and runs checks again. A clean case can correctly produce no lesson.
7. If an actual critic rejection or analyst edit exists, select it in **Reflect on this development rehearsal** and prepare a proposal. Code reflection makes no model call; optional AI reflection uses the original run's remaining budget. Read the action, explanation, applicability, counterexamples and exact proposal version in **Reviewed research lessons**.
8. The analyst enters a reason and accepts or rejects the exact proposal in the app. Acceptance does not apply guidance automatically. Freeze explicitly selected accepted lessons before a later held-out comparison.

The interface intentionally blocks development publication; its production approval button is not a way to acknowledge a clean rehearsal. A clean development note may remain at the review pause without being falsely rejected or published.

## Observed web rehearsal

The first KDEV018 planner was started through **Create a plan** and paused for exact-plan review. A further web attempt received exact-plan approval, then stopped during the researcher call with `provider_connect_error`. That code identifies a gateway-to-provider connection failure; it does not establish its DNS, TCP or TLS cause, nor is it a critic rejection.

Sixteen admission, version and preservation checks pass. The two attempts have two completed planner responses and one failed call with retained reservation. Neither has produced a draft, critic rejection, analyst edit, lesson proposal or publication. All earlier runs, the approved library, preferences and lesson bank are preserved. The earlier awaiting plan still needs its own exact approval; approval of the failed attempt does not transfer to it.

Web inspection also exposed a polling race: an older in-flight refresh can replace the selected run, and a previous run's error can remain visible after switching. This display issue needs correction before continuing the analyst walkthrough. Preserve both attempts and their accounting rather than deleting the failure or automatically retrying it.

## What the brief requires

Printed p.15 starts the Analyst Desk walkthrough with a request in the research UI and an editable plan. Printed p.16 requires exact-note approval before publication and a demo of linked financial facts, critic correction/security and memory. The common deployment requirements on p.3 include FastAPI streaming, Docker Compose and monitoring.

For improvement, p.3 L12 and p.16 require lessons from actual development failures or analyst edits, human review of every lesson, relevant retrieval and a frozen playbook before held-out evaluation. A passing case, a fixture or a pending proposal does not demonstrate improvement. The deliberately planted wrong-number demo is separate from naturally observed development failures.

[The case receipt](../evidence/web_development_case_verification.json) records sanitized checks and the current boundary. Full run records, review screenshots and human decisions remain in ignored local storage. Read [the lesson workflow](REVIEWED_LESSONS.md) for versioning, limits and revocation, and [the evaluation plan](EVALUATION_PLAN.md) for the outstanding independent comparisons.
