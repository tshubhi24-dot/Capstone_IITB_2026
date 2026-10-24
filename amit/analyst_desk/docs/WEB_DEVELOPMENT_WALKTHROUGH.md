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

### Resume a supported validation failure

When an approved live run stops on a content-validation error, the server may expose a verified continuation. After correcting the cause, select that stopped run and use **Resume approved research**. The control binds the exact original plan hash and retains the original call, token and spending limits, including prior charges and holds. The final note still needs its own review.

The control appears only when the server reports a supported content-validation continuation. It does not expose provider connection retries, rate-limit extensions or policy replacement. Nothing resumes automatically. Loading, an in-flight decision or switching to another run prevents stale or duplicate submissions.

The interface intentionally blocks development publication; its production approval button is not a way to acknowledge a clean rehearsal. A clean development note may remain at the review pause without being falsely rejected or published.

## Observed web rehearsal

The first KDEV018 planner was started through **Create a plan** and paused for exact-plan review. A further web attempt received exact-plan approval, then stopped during the researcher call with `provider_connect_error`. That code identifies a gateway-to-provider connection failure; it does not establish its DNS, TCP or TLS cause, nor is it a critic rejection.

Sixteen admission, version and preservation checks pass. The two attempts have two completed planner responses and one failed call with retained reservation. Neither has produced a draft, critic rejection, analyst edit, lesson proposal or publication. All earlier runs, the approved library, preferences and lesson bank are preserved. The earlier awaiting plan still needs its own exact approval; approval of the failed attempt does not transfer to it.

Web inspection also exposed a polling race: an older in-flight refresh could replace the selected run, and a previous run's error could remain visible after switching. The fix binds responses and timers to the selected run and refresh version, clears previous errors, and locks review controls while loading or submitting a decision. Same-version unsaved edits remain intact. An in-flight creation guard prevents overlapping submissions; it does not establish why the two observed attempts were created.

Thirty-nine targeted tests pass, including nine synthetic response-order and review-control cases. The app and local entry point were refreshed without changing runs, notes, preferences, note policy, lessons or the complete budget response. Browser verification selected the failed attempt, switched back to the awaiting plan and confirmed the old error cleared while the correct exact plan and development controls remained visible. No approval, retry, model call or research lesson was created by this fix.

A credential-free connection probe first failed DNS resolution and then retrieved the public OpenRouter catalogue successfully. This is consistent with a transient network problem, but does not prove the original failure's precise cause. Preserve both attempts and their accounting rather than deleting the failure or automatically retrying it. The awaiting plan is available for its own human decision in the app.

The original plan subsequently received its own web approval. Research and risk selection completed, but the writer was stopped before criticism by a quantity-guard false positive on the temporal phrase “between the two periods.” Both citations identify the same issuer and the two requested fiscal years. The structured writer response is preserved in the existing paid cache; no critic rejection or analyst edit is claimed.

An explicit web continuation control is implemented and tested against the existing backend guard. Nineteen UI cases pass, and the combined UI/provider/catalogue/API/session checks pass 144 tests. Deployment waits for the narrow validator correction so the cached response can be checked without buying another writer response merely to change temporal wording.

The validator correction checks canonical citation IDs, exact quotations and uniqueness before inferring temporal scope for summary claims. Only one issuer and exactly two distinct cited fiscal years enable the existing narrow temporal phrase exception. Amounts, durations, arbitrary number words, invalid sources and explicit comparison-scope mismatches remain blocked. Prompts, schemas and model request construction are unchanged.

Two hundred fifty-seven targeted reasoning/workflow/lesson/memory tests pass, including twenty-nine new temporal-provenance cases. A synthetic checkpoint test proves that a stopped writer can replay the identical cached request and proceed to a critic without charging for another writer response. The actual web continuation remains a separate observation to verify after deployment.

## What the brief requires

Printed p.15 starts the Analyst Desk walkthrough with a request in the research UI and an editable plan. Printed p.16 requires exact-note approval before publication and a demo of linked financial facts, critic correction/security and memory. The common deployment requirements on p.3 include FastAPI streaming, Docker Compose and monitoring.

For improvement, p.3 L12 and p.16 require lessons from actual development failures or analyst edits, human review of every lesson, relevant retrieval and a frozen playbook before held-out evaluation. A passing case, a fixture or a pending proposal does not demonstrate improvement. The deliberately planted wrong-number demo is separate from naturally observed development failures.

[The case receipt](../evidence/web_development_case_verification.json) records sanitized checks and the current boundary. Full run records, review screenshots and human decisions remain in ignored local storage. Read [the lesson workflow](REVIEWED_LESSONS.md) for versioning, limits and revocation, and [the evaluation plan](EVALUATION_PLAN.md) for the outstanding independent comparisons.
