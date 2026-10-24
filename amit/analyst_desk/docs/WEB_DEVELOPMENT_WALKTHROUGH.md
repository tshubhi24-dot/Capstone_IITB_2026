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

Two genuine KDEV018 web attempts are retained. One received its own exact-plan approval, then stopped during researcher query selection with `provider_connect_error`; its failed call and held reservation remain recorded. A credential-free probe later failed DNS resolution once and retrieved the public provider catalogue successfully. That observation does not establish the original failure's precise cause, and a connection failure is not a critic rejection or lesson origin.

The original attempt subsequently received its own exact-plan approval in the app. Research and risk selection completed, but a quantity guard stopped the writer before criticism on the temporal phrase “between the two periods.” The correction validates canonical citation IDs, exact quotations and uniqueness before inferring that narrow temporal scope: one issuer and exactly two distinct fiscal years are required. Financial quantities, durations, invalid quotes and explicit scope mismatches remain blocked. Prompts, schemas and model request construction are unchanged.

**Resume approved research** was invoked explicitly in the web app under the existing human-approved plan; it did not create another human approval. The actual continuation reused the identical cached writer request and response without a new writer charge. Only one new critic response was requested and charged. Thirty completion checks pass: the resulting note has **6/6 verified financial values and 4/4 model-supported claims**, with eight exact source quotations and both requested fiscal years cited for each claim. The model review remains labelled fallible; partial evidence and source limitations remain visible.

At the initial completion checkpoint, the attempt paused at **awaiting note review** with five unique completed model responses. Across both retained attempts there were **seven recorded call attempts, six unique completed responses and one connection failure with its reservation held**. Earlier spending and holds remained counted. There were **zero critic rejections, analyst note edits, eligible lesson origins, proposals or lesson decisions**. No development note published and no independent improvement was claimed; the subsequent authorized correction is recorded below.

The deployed interface binds responses, errors and polling to the selected run, locks actions during loading/submission and preserves same-version unsaved edits. It now also retains the existing evidence DOM on an unchanged poll, so open risk/citation details remain open. A changed run, status or note version still rerenders, and the selected saved-run label reflects the latest status. **Fifty-two targeted tests pass, including 22 UI cases and three new display cases.** Deployment preserves six runtime groups: runs, notes, preferences, note policy, lessons and the full budget response. This display update makes no model calls or human decisions.

At display verification, the selected label showed note review, the exact note version was unchanged, expanded citations remained open across more than twenty seconds of polling, and unsaved review text was preserved. Development publication stayed disabled and no eligible reflection origin existed at that checkpoint.

## Apply the authorized wording correction

Source inspection identified a useful omission in the natural-disaster observation: the earlier selected quotation lists operations and facilities, while the later quotation explicitly includes retail stores. The original claim's caution about materiality was not false. The agreed correction adds the observable wording difference while retaining uncertainty about economic exposure.

The user selected and authorized this correction; an operator applied it through the web note editor. Only the existing natural-disaster claim bullet changed. Its original citation identifiers, every other claim, the financial table, headings and mandatory limitations remain unchanged. Saving persisted an actual `note_edit` event and invalidated the previous semantic verdict. This is an authorized correction, not an independently authored human quality label.

All **31 actual correction checks pass**, including two canonical financial rows, **6/6 financial values**, eight unchanged exact quotations and **4/4 fresh model-supported claims** bound to the new exact note version. Exactly one new critic response was used, bringing the primary attempt to six recorded model calls; the writer and retrieval did not rerun. Earlier usage, the failed-call hold, other runs, the approved library, memory and lessons remain preserved; original spending limits are unchanged. The note remains at **awaiting note review**, and development publication remains blocked. At this correction checkpoint there is **one eligible edit origin, zero lesson proposals and no lesson acceptance, rejection or frozen playbook**. The next action is to prepare an accurately scoped pending proposal for separate human review, not to treat the edit or critic pass as accepted learning or independent improvement.

## Files and responsibilities

| Files | Purpose |
|---|---|
| [web/app.js](../web/app.js), [web/index.html](../web/index.html) | Bind exact review/continuation actions to the selected run, preserve open unchanged evidence and refresh its saved-run status. |
| [tests/test_run_selection_ui.py](../tests/test_run_selection_ui.py) | Execute actual browser handlers with controlled delayed responses; check stale actions, exact hashes, supported continuation and stable note display. |
| [desk/reasoning.py](../desk/reasoning.py), [tests/test_temporal_provenance.py](../tests/test_temporal_provenance.py) | Infer narrow temporal wording only after canonical source/citation validation, while preserving quantity and comparison-scope checks. |
| [desk/workflow.py](../desk/workflow.py), [web/app.js](../web/app.js) | Save only an exact-version claim edit, retain code-owned note content, persist its origin and request fresh criticism before further review. |
| [web case receipt](../evidence/web_development_case_verification.json) | Record observed completion, cached replay, retained failures, preservation checks and the pending human-review boundary. |

## What the brief requires

Printed p.15 starts the Analyst Desk walkthrough with a request in the research UI and an editable plan. Printed p.16 requires exact-note approval before publication and a demo of linked financial facts, critic correction/security and memory. The common deployment requirements on p.3 include FastAPI streaming, Docker Compose and monitoring.

For improvement, p.3 L12 and p.16 require lessons from actual development failures or analyst edits, human review of every lesson, relevant retrieval and a frozen playbook before held-out evaluation. A passing case, a fixture or a pending proposal does not demonstrate improvement. The deliberately planted wrong-number demo is separate from naturally observed development failures.

[The case receipt](../evidence/web_development_case_verification.json) records sanitized checks and the current boundary. Full run records, review screenshots and human decisions remain in ignored local storage. Read [the lesson workflow](REVIEWED_LESSONS.md) for versioning, limits and revocation, and [the evaluation plan](EVALUATION_PLAN.md) for the outstanding independent comparisons.
