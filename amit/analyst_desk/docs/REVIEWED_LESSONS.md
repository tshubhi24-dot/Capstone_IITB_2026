# Step 14: reviewed development lessons

The lesson workflow turns an actual development critic rejection or analyst edit into a proposal. A person accepts or rejects the exact proposal with a reason. Accepted lessons affect new research only after the analyst freezes a playbook and explicitly selects it.

## Use the interface

1. Connect to the local desk. Open **Reviewed research lessons** to inspect proposals, decisions and frozen playbooks.
2. To prepare development research, select **Public development rehearsal** and a registered public question. Its exact question, companies and fiscal years define the request; private analyst memory is off. The desk contains twenty public question/scope records, nineteen covered by the current snapshot. The unsupported-year refusal case remains unavailable for research execution.
3. Review the proposed plan before execution. Development research pauses at final note review and cannot publish. Outline edits are permitted; company/year changes require a different registered case.
4. After an actual critic rejection or analyst note edit, choose its event in **Reflect on this development rehearsal**. **Code reflection** maps controlled failure categories to a cautious unreviewed proposal. Optional **AI reflection** uses the original approved live plan and its remaining call/token/spending limits. It receives controlled failure categories, public scope and the fixed action catalogue; previous note prose and review reasons stay local. A failed AI call is not retried automatically.
5. Inspect the proposed guidance, explanation, applicability, counterexamples and originating event. Enter a reason, then **Accept this exact proposal** or **Reject this exact proposal**. Editing first creates a new pending proposal; the superseded pending version cannot be accepted.
6. Select accepted lessons and click **Freeze selected accepted lessons**. Freezing creates a new immutable playbook; acceptance alone does not change research.
7. For a new request, enable **Use a frozen reviewed playbook** and choose its exact version. The plan shows the selected context. At most three relevant lessons are retrieved for the requested company/year scope and producer stage.
8. Revoke a lesson with a reason when its applicability is no longer justified. Pending research using a revoked selected lesson must start with a fresh plan. Previous decisions, playbooks and published notes retain their original history.

A development rehearsal is an implementation exercise. The public questions and source-derived preparation still need independent source/domain review. They are not untouched final evaluation cases or evidence of semantic research quality.

## What a lesson can change

The reusable catalogue contains four code-owned checklists:

| Action | Guidance |
|---|---|
| `align_fiscal_periods` | Check actual fiscal start/end dates and explain calendar differences. |
| `verify_current_facts` | Use canonical current SEC facts and independently verified arithmetic. |
| `preserve_risk_qualifiers` | Preserve uncertainty, conditions and negation; excerpts cannot establish absent or removed risks. |
| `cite_exact_evidence` | Attach exact approved-scope evidence and check that it supports the wording. |

Models receive only the relevant fixed checklist text. Proposal explanations, reviewer reasons, historical research bodies and credential values are not forwarded as lesson context. Guidance cannot select providers, change permissions or budgets, replace facts, approve a plan or publish a note. The independent critic receives neither lesson guidance nor lesson metadata.

The producer models can use accepted guidance in planning, query selection, risk interpretation and writing. Offline research retains deterministic arithmetic. Neither a passing fixture nor a stored lesson proves an improvement in research quality.

## Provenance, storage and corrections

The actual LangGraph SQLite store shares the existing portal database. Actor namespaces separate proposals, decisions, supersessions, revocations, playbooks and the bounded bank. Each proposal binds its originating registered development case, source identity, immutable event hash and failed/edited output hashes.

Review decisions and rejection reasons are append-only exact-version records. An edited pending proposal creates a new identifier and supersedes the previous version. Accepted/rejected decisions are not overwritten. To correct an accepted lesson, create a new proposal with its own review and explicitly revoke the earlier lesson when appropriate.

The bank holds at most 256 proposals and 64 playbooks; one playbook contains one through sixteen accepted versions. Selection returns at most three applicable actions, with duplicate actions removed. Frozen playbooks bind one source snapshot. Unrelated proposals, rejections or new acceptances do not alter existing frozen research. Selected revocations do invalidate pending research; the publisher rechecks this inside its SQLite transaction.

Revocation stops future reuse; it does not delete prior review records, frozen versions, approved publications or backups. Lesson records have no automatic expiry in this step. Credential-like strings are rejected, but the UI remains a local development tool: do not enter unrelated personal information. Runtime databases and genuine review records stay outside Git.

## API and files

All routes use existing analyst authentication and cross-origin write protection. Mutation requests include the current bank `expected_revision`; stale requests return HTTP 409.

| Route | Purpose |
|---|---|
| `GET /api/development/cases` | List public questions and covered scope without expected answers. |
| `GET /api/lessons` | Inspect the local bank, exact proposals, decisions and frozen playbooks. |
| `POST /api/lessons/reflect` | Prepare a pending proposal from an eligible persisted event; choose `rules` or explicit `live` reflection. |
| `POST /api/lessons` | Create a locally explained proposal or a revision of a pending proposal. |
| `POST /api/lessons/{id}/decision` | Accept/reject the exact proposal hash with a reason. |
| `POST /api/lessons/{id}/revoke` | Revoke an accepted exact version with a reason. |
| `POST /api/playbooks` | Freeze explicitly selected accepted lesson IDs. |

| Files | Purpose |
|---|---|
| [development.py](../desk/development.py), [public questions](../data/development_cases.json) | Server-owned public-case admission and source binding; no answers or labels bundled. |
| [lessons.py](../desk/lessons.py) | Actual LangGraph persistence, exact decisions, supersession, frozen selection and transaction-time validation. |
| [reflection.py](../desk/reflection.py), [reasoning.py](../desk/reasoning.py) | Code-category reflection and optional bounded model-assisted proposal generation. |
| [workflow.py](../desk/workflow.py), [store.py](../desk/store.py) | Reviewed plan/note context, producer-only guidance, continuation validation and development publication blocks. |
| [api.py](../desk/api.py), [lessons.js](../web/lessons.js), [index.html](../web/index.html) | Authenticated development, review, freeze and revocation controls. |

## Human evidence and evaluation still required

This implementation does not invent an accepted lesson or a rejected lesson to meet the capstone requirement. Automated tests and operator checks use explicitly synthetic fixtures. The analyst must review a genuine development-derived proposal before the project can claim actual acceptance/rejection evidence.

L9's ordinary analyst-memory on/off comparison is separate from **E3**, which compares held-out results with reviewed frozen lessons off/on. Keep ordinary profiles/history constant between E3 arms, freeze the playbook before testing, account for lesson-generation cost and report regressions. The independent evaluator still owns protected questions, expected answers, semantic labels and the different-family outcome judge. No held-out output, judge verdict or final-case failure may become a shared lesson.

See the [storage decision](ADR-005-REVIEWED-LESSONS.md), [memory policy](MEMORY_POLICY.md) and [evaluation plan](EVALUATION_PLAN.md).

## Observed verification

The [deployed receipt](../evidence/reviewed_lessons_verification.json) records 1,005 passing tests, 24 deployed API/preservation checks and 19 general runtime checks. Fourteen isolated preparation checks, thirteen checks after an actual app restart and ten cleanup/revocation checks pass. The operator uses a separate database and explicitly synthetic review fixtures; the real lesson bank stays empty.

Browser inspection confirmed the development selector, exact public question, locked company/year scope, disabled private memory and explicit empty proposal/playbook states. Existing research runs, preferences, note policy, three approved notes and spending records remained unchanged. No paid model request, genuine human decision, real development run or publication was performed for this verification.
