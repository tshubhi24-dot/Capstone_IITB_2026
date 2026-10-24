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

## Prepare the pending lesson for human review

After the saved correction and fresh checks, the actual `note_edit` event was selected in **Reflect on this development rehearsal**. **Code reflection** created an unreviewed `verify_current_facts` proposal without calling a language model. This rule receives a controlled edit category and public scope; it does not inspect the before/after note prose. Its generic numeric guidance did not describe this wording-precision correction.

An operator inspected and refined the pending proposal in the web interface. **Proposed guidance** changed to `cite_exact_evidence`, with an explanation of the retail-stores wording distinction, applicability limited to Apple fiscal 2024–2025 against the same cached source, and limits covering partial excerpts, economic materiality and the absence of a demonstrated financial error. Saving created a new immutable exact proposal version. The generic initial version is **superseded**, not rejected.

All **27 actual proposal-preparation checks pass**, including exact proposal/origin hashes, immutable parent preservation, valid supersession links and source-scoped applicability. At this checkpoint there are **two immutable proposal versions: one pending and one superseded**. All run, approved-library, memory and budget records remain unchanged. There is no acceptance/rejection decision, frozen playbook or publication, and preparing/refining the proposal made no additional model call or charge. The note remains at its development review pause. This is a proposal derived from a genuine authorized edit and refined by an operator; it is not autonomous AI learning or evidence of improved research quality.

For a pending proposal, inspect its exact version, origin, reusable guidance, explanation, applicability and counterexamples in **Reviewed research lessons**. The user supplies a reason and separately chooses **Accept this exact proposal** or **Reject this exact proposal**. Any further edit must first be saved as a fresh version before a decision. Acceptance alone does not change research: accepted guidance must be explicitly frozen into a playbook and selected for later research. Only the fixed allowlisted action hint can reach producing models; the detailed explanation and review reason remain local. Protected evaluation and measured improvement remain separate work.

## Verify the recorded lesson acceptance

All **24 actual acceptance-verification checks pass**, including immutable proposal/decision hashes, exact-version and actor binding, preserved registered edit/source/scope, and unchanged research, library, memory and budget records. Initial inspection found that the refined exact proposal already had a persisted acceptance before this verification began. That decision is retained without resubmission or replacement. The recorded review reason stays in private local storage. The bank now has **one accepted version, one superseded version and no pending proposal**; no additional lesson decision was submitted during verification.

Acceptance is reasonable for a bounded citation-checking reminder. The originating edit identifies a wording omission visible in both retained quotations, applies to Apple fiscal 2024–2025 against the same cached source, and preserves explicit partial-evidence and economic-materiality limits. It does not reinterpret the original cautious claim as a financial error. Its fixed `cite_exact_evidence` hint asks producers to check that cited evidence supports claim wording; the detailed retail-stores explanation remains local.

The proposal covers all four producing stages, while the observed correction concerns note wording. That generic hint is consistent with those stages, but its usefulness beyond the observed risk/writer context has not been measured. This accepted checklist does not demonstrate autonomous learning, an independently authored human quality label or improved model performance. At the acceptance-verification checkpoint, no playbook had been frozen or reused and no development note had published. That verification made no model call; subsequent freezing and use are recorded separately below.

## Verify the frozen playbook before reuse

Initial inspection of the next checkpoint found **one frozen playbook containing the exact accepted lesson**. Its existing record was preserved; no duplicate freeze request was submitted. All **22 actual freeze checks pass**: the immutable playbook identity/hash, accepted proposal and decision, current source and unrevoked lesson agree. The bank has advanced once since the acceptance checkpoint, without adding another lesson. Runs, the approved library, memory, note policy and budget records are unchanged; live research and retrieval are ready and no operation is active.

This checkpoint establishes a valid frozen playbook, not model use. No fresh plan, model call, lesson reuse or development publication has occurred, and no independent improvement is claimed. The [frozen-playbook receipt](../evidence/frozen_playbook_use_verification.json) records these checks separately from the historical originating-case receipt.

To demonstrate reuse, explicitly select the frozen playbook and enable **Use a frozen reviewed playbook**, then choose a new **KDEV018 · AAPL · 2024, 2025** public development run with private memory off. The request must retain the exact registered question and current source. Creating its plan can use the original authorized model budget; execution still requires review of that new exact plan. To demonstrate actual use, verify a nonempty relevant lesson reference in the reviewed context and that the fixed hint reached a completed producer request. Repeating the originating development case is a scoped use demonstration, not held-out improvement evidence.

## Verify actual planner use and retain the stopped research

A new KDEV018 run was created through the web app with the exact Apple fiscal 2024–2025 request, private memory off and the frozen playbook explicitly selected. The live planner completed. A local capture-only reconstruction passed **21 checks without a provider call**: the validated context selects the accepted lesson, its fixed hint appears in the planner system message, and the reconstructed request identity matches the completed planner response and event. Removing the guidance changes that identity. This verifies actual planner guidance use, beyond an enabled setting.

The human approved the new exact plan in the web app. The researcher then retrieved canonical facts, but its query-selection model request stopped at an **upstream HTTP 429**. The new run is in error with **two recorded model attempts, one completed planner response and the failed request's reservation retained**. No automatic retry, offline substitution or model-configuration change occurred. A further **25 read-only runtime checks pass**, preserving earlier runs, lessons, library, memory and original spending controls while verifying the exact approval, two attempts and retained failed reservation.

**The research journey is incomplete.** This run produced no risk analysis, writer draft or critic result, and it created no new lesson proposal or publication. Guidance use in the later producing stages and exclusion from an actual new critic request have not been verified in this run. The original learning case and its accepted frozen lesson remain preserved. A provider rate limit is an operational failure, not a critic rejection or new research lesson.

The observed result establishes scoped guidance delivery to a completed live planner. It does not prove semantic adherence, completion of the remaining workflow or independent improvement on held-out questions. The [playbook-use receipt](../evidence/frozen_playbook_use_verification.json) records the request-level checks and retained failure; earlier freeze readiness and originating-case results remain distinct historical checkpoints.

## Verify the new primary route before continuing Apple research

After the bounded fallback profile is activated, a fresh KDEV018 plan is created in the web app with the same registered Apple fiscal 2024–2025 question, private memory off and the frozen playbook explicitly selected. GPT-4.1 Mini completes the planner request directly: **one call, 938 reported tokens and US$0.0006152**. This verifies live primary access; Mistral is available as a configured backup but is not used in this call.

All **25 activation checks**, **20 live-plan preservation checks** and **21 completed-planner guidance checks** pass. Earlier research, the accepted frozen lesson, approved library, memory and all prior uncertain holds remain intact. Actual fixed guidance delivery is verified through the completed request identity; semantic adherence and independent improvement are not established.

Before execution, an operator narrows the outline from extracting all risk disclosures to comparing available quoted excerpts. The edit retains the exact question, company/years, source and model usage, adds no paid call, and pauses for review of the new exact plan. The plan must be approved in the web app before research proceeds. This checkpoint produces no draft, critic verdict, lesson proposal or publication. The [fallback verification receipt](../evidence/model_fallback_verification.json) records this new attempt separately from the earlier stopped-run receipt.

## Files and responsibilities

| Files | Purpose |
|---|---|
| [web/app.js](../web/app.js), [web/index.html](../web/index.html) | Bind exact review/continuation actions to the selected run, preserve open unchanged evidence and refresh its saved-run status. |
| [tests/test_run_selection_ui.py](../tests/test_run_selection_ui.py) | Execute actual browser handlers with controlled delayed responses; check stale actions, exact hashes, supported continuation and stable note display. |
| [desk/reasoning.py](../desk/reasoning.py), [tests/test_temporal_provenance.py](../tests/test_temporal_provenance.py) | Infer narrow temporal wording only after canonical source/citation validation, while preserving quantity and comparison-scope checks. |
| [desk/workflow.py](../desk/workflow.py), [web/app.js](../web/app.js) | Save only an exact-version claim edit, retain code-owned note content, persist its origin and request fresh criticism before further review. |
| [desk/reflection.py](../desk/reflection.py), [desk/lessons.py](../desk/lessons.py), [web/lessons.js](../web/lessons.js) | Create an edit-derived proposal, preserve immutable supersession and recorded exact-version decisions, and keep acceptance, freezing and reuse separate. |
| [web case receipt](../evidence/web_development_case_verification.json) | Record observed completion, cached replay, retained failures, preservation checks and the pending human-review boundary. |
| [frozen-playbook receipt](../evidence/frozen_playbook_use_verification.json) | Separate frozen readiness, request-bound proof of actual planner guidance, the retained upstream failure and the limits of improvement evidence. |

## What the brief requires

Printed p.15 starts the Analyst Desk walkthrough with a request in the research UI and an editable plan. Printed p.16 requires exact-note approval before publication and a demo of linked financial facts, critic correction/security and memory. The common deployment requirements on p.3 include FastAPI streaming, Docker Compose and monitoring.

For improvement, p.3 L12 and p.16 require lessons from actual development failures or analyst edits, human review of every lesson, relevant retrieval and a frozen playbook before held-out evaluation. A passing case, a fixture or a pending proposal does not demonstrate improvement. The deliberately planted wrong-number demo is separate from naturally observed development failures.

[The case receipt](../evidence/web_development_case_verification.json) records sanitized checks and the current boundary. Full run records, review screenshots and human decisions remain in ignored local storage. Read [the lesson workflow](REVIEWED_LESSONS.md) for versioning, limits and revocation, and [the evaluation plan](EVALUATION_PLAN.md) for the outstanding independent comparisons.
