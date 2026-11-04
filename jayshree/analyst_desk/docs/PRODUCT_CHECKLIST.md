# Analyst Desk Product and Domain Checklist

Define the analyst's problem, supported research scope, evidence standards and acceptance policies independently of the current implementation. Assess existing behavior against those decisions and record a gap when it falls short.

This checklist covers product and domain work, including the shared evidence needed for product acceptance. It is not a complete technical implementation checklist. The responsibility key and handoffs identify the engineers who own the supporting systems and evaluation.

**Status:** Final project specification v1.0.

Checked definition items are complete. Unchecked tasks identify implementation, source eligibility, independent evaluation, domain acceptance or submission evidence still to produce. Research-plan approval, claim review and exact-note approval remain required product controls.

## Final project documents

Use these specifications as the implementation and acceptance baseline. The linked Markdown and Word versions carry the same requirements and worked examples.

- [x] Final [problem statement](PROBLEM_STATEMENT.md) and [Word version](PROBLEM_STATEMENT.docx): analyst problem, intended output and quality/cost/time evaluation question.
- [x] Final [supported research scope](SUPPORTED_RESEARCH_SCOPE.md) and [Word version](SUPPORTED_RESEARCH_SCOPE.docx): six task categories, 15 companies, FY2022-FY2024, source requirements and response boundaries.
- [x] Final [user needs and workflow](USER_NEEDS_AND_WORKFLOW.md) and [Word version](USER_NEEDS_AND_WORKFLOW.docx): received practitioner input, research workflow and usefulness measures.
- [x] Final [bank metrics and comparison rules](BANK_METRICS_AND_COMPARISON_RULES.md) and [Word version](BANK_METRICS_AND_COMPARISON_RULES.docx): operating/pre-tax definitions, compatible inputs, peer checks and revised-plan choices.
- [x] Final [fiscal periods and units rules](FISCAL_PERIODS_AND_UNITS_RULES.md) and [Word version](FISCAL_PERIODS_AND_UNITS_RULES.docx): dates, calendar requests, currency/scale, rounding and limitations.
- [x] Final [filing version policy](FILING_VERSION_POLICY.md) and [Word version](FILING_VERSION_POLICY.docx): original-as-reported default, later-reviewed basis, cutoff and version-compatible calculations.
- [x] Final [evidence, risk-change and uncertainty policy](EVIDENCE_RISK_CHANGE_AND_UNCERTAINTY_POLICY.md) and [Word version](EVIDENCE_RISK_CHANGE_AND_UNCERTAINTY_POLICY.docx): claim support, comparable coverage, labels, uncertainty and review completeness.
- [x] Final [acceptance and publication policy](ACCEPTANCE_AND_PUBLICATION_POLICY.md) and [Word version](ACCEPTANCE_AND_PUBLICATION_POLICY.docx): eligibility blockers, exact approval, confirmed publication and recovery.
- [x] Final one-page [memory and privacy policy](MEMORY_AND_PRIVACY_POLICY.md) and [Word version](MEMORY_AND_PRIVACY_POLICY.docx): saved records, permitted access, correction and deletion.
- [x] Final [memory and privacy rules and examples](MEMORY_AND_PRIVACY_RULES_AND_EXAMPLES.md) and [Word version](MEMORY_AND_PRIVACY_RULES_AND_EXAMPLES.docx): history, checkpoints, private context, lifecycle and reviewed lessons.
- [x] Final [golden answers and scoring rules](GOLDEN_ANSWERS_AND_SCORING_RULES.md) and [Word version](GOLDEN_ANSWERS_AND_SCORING_RULES.docx): eight development reference cases, expected values, scoring meanings and scoring-release requirements.
- [x] Final [frontend messages and trigger conditions](FRONTEND_MESSAGES_AND_CONDITIONS.md): 28 messages, trigger conditions, permitted actions and implementation owners.
- [x] Update the [project work and decision log](PROJECT_WORK_LOG.md) with the completed specification milestones and execution responsibilities.

The specification work is complete. Record actual source eligibility checks, product tests, expert inspections and scored results under the execution tasks below. The Golden reference cases are not a frozen execution release or eight passed application tests.

## Implementation responsibilities

| Role | Specification use | Required execution evidence |
|---|---|---|
| R1 Domain and product | Apply the problem, workflow, scope, policy meaning, acceptable limitations and golden-answer conclusions. | Domain decisions on actual research output, expert feedback, usefulness results and the demonstration narrative. |
| R2 Knowledge and memory | Implement source contracts, coverage, provenance and memory lifecycle. | Validated periods, units, concepts, versions, source eligibility and authorised correction/deletion behaviour. |
| R3 Agents and orchestration | Carry scope, compatible inputs, claim coverage, memory settings and bounded correction through the workflow. | State/trace evidence and validated development-fixture adapters. |
| R4 Tools, control and security | Enforce acceptance and privacy at tool and write boundaries. | Compatibility, review completeness, authority, exact approval, privacy and recovery checks. |
| R5 Evaluation and red team | Independently verify expectations/scoring and isolate protected assets. | Case/release verification, freeze identity, independent results and disagreement records. |
| R6 Deployment and operations | Implement frontend messages, limitations, review states, memory controls and publication receipts. | UI/recovery evidence, reproducible setup, traces and operational demonstration evidence. |

## Remaining execution work

- [ ] Complete a version-specific domain-expert inspection and record its actual findings and resulting decisions.
- [ ] Verify source eligibility and execution adapters for the eight reference cases with R2/R5; identify the case/policy release and freeze it before scored use.
- [ ] Obtain the required human risk annotations and independent evaluation evidence; teaching examples do not replace actual human records.
- [ ] Review a representative corrected note on an identified application/source/policy version and record accept, edit, reject or HOLD with reasons.
- [ ] Verify memory behaviour and genuine lesson decisions, then interpret the experiment and security evidence.
- [ ] Measure representative tasks against their baseline process using correction effort, quality, total research/review time and model usage/cost.
- [ ] Prepare the three-story demo script, rehearse it and complete the report, contribution record, backup recording and viva preparation.

## Execution order: product definitions, then shared validation

The product definitions and written specifications are complete. The sequence below identifies their responsibilities and the execution evidence required for product acceptance.

| Order | Work to start with | Roles | Product/domain output | Related phase |
|---|---|---|---|---|
| 1 | Define the analyst's problem and the intended product outcome. | R1 | Problem statement and success measures. | 1 |
| 2 | Identify a real user and describe their research workflow and needs. | R1 | User/workflow description and research scenarios. | 1 |
| 3 | Define data, source and coverage requirements. | R1 | Final coverage and evidence requirements, independent of existing code. | 1 |
| 4 | Talk to a human domain expert and assess the feedback. | R1 | Actual feedback and domain decisions. | 2 |
| 5 | Define written financial, research and acceptance policies. | R1 | Final policy definitions with worked acceptance examples. | 3 |
| 6 | Define golden-answer content and domain scoring expectations for development work. | R1 | Source-grounded expectations and rubric for independent R5 verification; no protected-case authoring. | 4 |
| 7 | Prepare the demonstration narrative and script. | R1 | Three-story script and a list of evidence needed from the team. | 10 |
| Throughout | Record actual decisions/contributions and practise the architecture and own scope. | R1 | Maintained decision/contribution log and presentation preparation. | 11 |

Use the final definitions for implementation and independent verification. R1 policy inspection of held-out cases requires controlled access from R5.

| Shared work | Roles | Boundary |
|---|---|---|
| Validate source feasibility and adopted coverage. | R1, R2, R3 | R1 defines requirements; source/workflow owners confirm feasibility and gaps. |
| Implement the specified controls and review a corrected note. | R1, R2, R3, R4, R5 | R1 decides domain acceptance; engineers implement and R5 checks agreed regressions. |
| Review golden answers, human risk labels and protected-case policy alignment. | R1, R2, R5 | R5 controls independent evaluation and protected assets. |
| Review memory behaviour and applicable development lessons. | R1, R2, R3, R4, R5 | R1 reviews meaning; owners implement controls and R5 measures benefit. |
| Review independent experiments, security evidence and reported outcomes. | R1, R2, R3, R4, R5, R6 | R1 interprets product impact; execution remains with the relevant owners. |
| Execute the full demo, collect operational evidence and finalize submission. | R1, R2, R3, R4, R5, R6 | R1 owns the narrative; each member supplies evidence for their component. |

## Review and recording rules

- Keep repository content, deliverables, code comments, commit messages and pull-request descriptions in English.
- Keep completed definitions checked. Close an execution task only after its required work occurs; record the evidence, actual reviewer, date, source version and decision.
- Keep protected evaluation questions and answers outside the application, model context and ordinary project artifacts. R5 controls access.

## Responsibility key

| Role | Responsibility |
|---|---|
| R1 | Domain and product lead: problem, users, data requirements, policies, golden-answer meaning, domain feedback, results interpretation and demo narrative. |
| R2 | Knowledge and memory engineer: ingestion, retrieval, reranking, source mapping and memory. |
| R3 | Agents and orchestration engineer: planning, specialists, workflow and improvement loop. |
| R4 | Tools, control and security engineer: MCP tools, permissions, approval controls, sandbox and defences. |
| R5 | Evaluation and red-team engineer: independent cases, scoring, judge calibration, attacks and experiment results. |
| R6 | Deployment and operations engineer: serving, UI, Docker, persistence, CI, tracing, dashboards, alerts and recording support. |

R1 defines and reviews domain requirements. Shared or dependent evidence below does not transfer another role's implementation responsibility to R1.

## 1. Define the problem user and supported scope

**Owner:** R1. **Support:** R2 and R3 for source/workflow feasibility. **Definition status:** Complete.

- [x] Define the equity-research user and document the workflow and pain points using received practitioner feedback.
- [x] State the outcome and supported questions: financial figures, year/peer comparisons, risk disclosures and approved-note follow-ups.
- [x] Define the 15-company, two-group, FY2022-FY2024 coverage and required Item 1A, Item 7, preserved tables, facts and company/year/Item metadata.
- [x] Define unsupported selections, missing evidence, incompatible comparisons and investment-recommendation boundaries; separate optional extensions.
- [x] Define usefulness measures: relevance, corrections, source-checking effort, total research/review time and model usage/cost.

**Completed specification:** Problem Statement, Supported Research Scope and User Needs and Workflow. Source completeness and measured outcomes require execution evidence under phases 6, 8 and 9.

## 2. Obtain actual domain expert feedback

**Owner:** R1. **Execution status:** Workflow feedback received; version-specific expert inspection still requires evidence.

- [x] Record actual practitioner workflow feedback and incorporate its domain requirements into the workflow specification.
- [ ] Have a suitable human domain expert inspect the identified scope, example question and note format or current prototype.
- [ ] Record actual findings on comparability, evidence, unacceptable errors and usefulness, together with the inspected version and resulting decisions.
- [ ] Implement the applicable resulting changes and retain evidence of that expert inspection.

**Required evidence:** The actual expert, relevant experience, material/version inspected, date, findings and resulting decisions. Received workflow comments do not establish prototype testing or approval of a particular research note.

## 3. Define financial research and publication policies

**Owner:** R1. **Implementation support:** R2, R3, R4, R5 and R6. **Definition status:** Complete.

- [x] Define fiscal dates, annual/quarter boundaries, currency/units, reporting perimeter and peer-comparison rules.
- [x] Define operating margin and the separate bank pre-tax task without silent substitution.
- [x] Define ROUND_HALF_UP display rounding, signs, percentage/percentage-point changes, invalid denominators and missing results.
- [x] Define original-as-reported default, eligible later-reviewed presentations, version differences and historical cutoff rules.
- [x] Define factual/causal support, risk-change labels, uncertainty, prohibited recommendations and treatment of retrieved instructions.
- [x] Define acceptance blockers, incomplete-review handling, exact approval and confirmed publication.
- [x] Define memory access, saved records, correction, withdrawal, deletion and reviewed-playbook requirements.

**Completed specification:** Final v1.0 financial, filing, evidence, acceptance and memory policies with worked examples and role responsibilities. Implement and independently verify these requirements; the 98% monitoring alert never permits publication of known errors.

## 4. Define golden answers and scoring rules

**Owner:** R1 for domain meaning. **Support:** R2 for sources and R5 for independent execution verification. **Domain specification status:** Complete; scoring release not yet frozen.

- [x] Document source-linked development reference answers independently calculated from source inputs rather than the tested generator's output.
- [x] Associate expected values with company, metric, actual period, basis, currency/scale and source location.
- [x] Define formulas, rounding, signs and derived changes; a matching number elsewhere cannot satisfy a wrong association.
- [x] Define Pass, Fail, Incomplete and disputed/defective-case meaning, including limitations and refusals.
- [ ] Complete independent R2/R5 source-eligibility and expectation verification, record disagreements and validate the issuer/fixture execution adapters.
- [ ] Identify and freeze the accepted case, evidence, policy and rubric release before scored runs; record the R5 handoff.

**Required execution evidence:** Verified expectations, source snapshots, adapter checks, decisions and an identified frozen release. Development questions and related variants remain development questions.

## 5. Validate the required human risk-change labels for ten company-years

**Classification:** Shared domain annotation and evaluation work; R1 does not personally own every label. **Owners:** R1 for domain content/review; R5 for the annotation/evaluation process. **Support:** R2.

**Roles:** R1, R2, R5. Coordinate this shared annotation/review work after the domain policy and reference content are defined.

- [ ] Select ten target company-years and obtain the relevant earlier/later filing evidence for each comparison.
- [ ] Ensure human reviewers inspect both periods and assign findings using agreed risk-label definitions, with a rationale and source locations. Perform or coordinate R1 domain review without compromising evaluation independence.
- [ ] Review sufficient relevant-section coverage before claiming addition/removal; distinguish newly disclosed wording from a newly arising economic risk.
- [ ] Record the actual human reviewer/date and resolve material disagreements with R5. Keep rejected or uncertain findings visible.
- [ ] Freeze the accepted annotations and acceptable answer boundaries; verify that completion counts reflect actual human reviews.

**Completion evidence:** ten completed company-year review records, paired evidence, final finding labels, rationales and R5 adjudication. These are separate from human labels on judge-calibration outputs.

## 6. Review a current-version research note and close product findings

**Classification:** R1 product acceptance and domain interpretation of shared end-to-end requirements. **Owner:** R1. **Support:** R2, R3, R4, R5.

**Roles:** R1, R2, R3, R4, R5. Review the product against adopted requirements; do not assume existing behavior is correct.

- [ ] Select a representative development request and record the code/configuration, source snapshot, scope and effective policy used for the review.
- [ ] Run through the application's research and human-review gates under the applicable authorization; retain the exact plan, note, checks and trace.
- [ ] Review every displayed financial figure and derived change, its source/calculation chain, requested coverage, fiscal disclosure and interpretation.
- [ ] Review risk novelty, causal claims, missing evidence and claim-review completeness; record an actual accept, edit, reject or HOLD decision with reasons.
- [ ] Turn defects into evidence-backed R3/R4 handoffs with expected behaviour and R5 regression checks. Re-review the corrected exact note before closing findings.

**Completion evidence:** a versioned product-review register linking each finding to its source, policy, owner, fix/test evidence and R1 disposition. Preserve original failed outputs; a new code version does not retroactively correct them.

## 7. Review memory behaviour and development lessons

**Classification:** Shared memory/learning evidence; R2/R3 own implementation and R5 measures effects. **Owner:** R1 for domain judgement. **Support:** R2, R3, R4, R5.

**Roles:** R1, R2, R3, R4, R5.

- [ ] Check that saved preferences, previous-note comparisons and correction/deletion behaviour match the adopted user-facing policy; document what remains in checkpoints or published records.
- [ ] Review genuine development-derived lesson proposals for correctness, applicability, counterexamples and possible harm.
- [ ] Record actual human decisions, including a genuine rejected lesson with its reason; retain relevant accepted lessons and freeze the playbook before held-out evaluation.
- [ ] Coordinate memory-on/off and lesson-before/after evidence with the owners; distinguish available controls from demonstrated benefit.

**Completion evidence:** domain-review decisions, an auditable reviewed/frozen playbook and relevant memory/lesson demonstration references. R3 builds the improvement loop; R5 measures unseen-case benefit.

## 8. Confirm independent evaluation and security handoffs

**Classification:** R1 held-out policy review with independent evaluation owned by R5 and supporting engineering roles. **Owner:** R5 for independent evaluation; R1 reviews domain/policy alignment. **Support:** R2, R3, R4.

**Roles:** R1, R2, R3, R4, R5. R5 provides the controlled cases and evaluation evidence before R1 completes this review.

- [ ] Confirm evidence of at least 60 distinct cases: about 20 development and at least 40 protected held-out cases, with expected outcomes fixed before testing and related variants kept together.
- [ ] Check R5's held-out cases against the written policy through a controlled R1 review. Preserve the independence boundaries: agent tuners do not author held-out cases, and defence builders do not author independent attacks.
- [ ] Coordinate at least 20 genuinely human-labelled outputs for judge calibration; require agreement, Cohen's kappa and disagreement evidence for the actual judge configuration.
- [ ] Obtain R5/R4 evidence for 30+ independent attacks, defences off/on and legitimate-work false blocks, including the project's retrieved-instruction, private-watchlist and sandbox-network scenarios.
- [ ] Obtain R2/R5 evidence for the required retrieval comparison and FinanceBench external retrieval check; identify remaining source/label limitations.

**Completion evidence:** acknowledged ownership, case/label counts, freeze references, independence records and result artifacts. R1 does not need protected answers copied into this checklist or exposed to the application.

## 9. Interpret experiments and validate product claims

**Classification:** Shared experiment evidence and common outcome/interpretation obligations. **Owner:** R1 for product interpretation; R5 for execution/scoring. **Support:** R2, R3, R4, R6.

**Roles:** R1, R2, R3, R4, R5, R6.

- [ ] Review E1: C0/C1/C2 with matched research capability, models, tools, budgets and recorded memory/playbook settings; explain remaining differences.
- [ ] Review E2 defence effectiveness, E3 lesson benefit/harm and E4 critic on/off plus table-aware/plain-text ablations.
- [ ] Require three final held-out repetitions and report spread, failures/timeouts, success counts, policy violations, false blocks, cost, median latency and p95 latency.
- [ ] Check scoring meaning and comparable denominators. Twenty questions across three configurations are not 60 distinct cases; a coarse task pass is not complete note accuracy.
- [ ] Distinguish actual provider charges from estimates and current frozen configurations from historical results with incomplete provenance.
- [ ] Validate the usefulness outcome from phase 1 and agree evidence-backed presentation claims, including negative results and limitations.

**Completion evidence:** a product interpretation of R5's versioned results, measured user/product outcomes and an agreed claim-to-evidence register. Do not infer superiority from architecture or a development score alone.

## 10. Rehearse and record the required demonstration

**Classification:** Direct R1 demo-script duty; the required technical demonstrations are team work. **Owner:** R1 for script and narrative. **Support:** R2-R6.

**Roles:** R1, R2, R3, R4, R5, R6. Write the required demo script, then execute and verify the full demonstration with the technical owners.

- [ ] Demonstrate a margin comparison with every financial figure linked to its supporting fact or calculation.
- [ ] Demonstrate the critic finding/correcting a planted wrong number while an injected retrieved article's investment recommendation stays out of the note.
- [ ] Demonstrate "What changed since our last note?" using a prior note saved through the normal approval/publication path and explain what memory contributed.
- [ ] Include exact-plan review, an edit invalidating prior note approval and the required resume/replan evidence with the engineering owners.
- [ ] Rehearse the full story on the actual demonstration version; label synthetic fixtures and explain real limitations and failures accurately.
- [ ] Coordinate a complete backup recording with R6 and verify that it opens and plays through. Keep the evidence tied to the demonstrated version.

**Completion evidence:** the actual demo script, rehearsal record, traces/source bookmarks and a verified backup recording. Screenshots and component tests alone do not complete the live demonstration.

## 11. Complete submission, contribution evidence and individual viva

**Classification:** Shared delivery and contribution evidence, with role-specific presentation preparation. **Owner:** R1 for product narrative and personal contribution. **Support:** R2-R6.

**Roles:** R1, R2, R3, R4, R5, R6. Maintain the decision/contribution record throughout and complete shared submission checks with the team.

- [ ] Redraw and explain the architecture and a numbered request walkthrough, including decisions made by models, code and people.
- [ ] Explain scope, financial/risk definitions, evidence limits, memory behaviour, experiment trade-offs, an actual design decision and remaining pilot-readiness work.
- [ ] Finalize slides and review the 4-6-page evaluation report for accurate scope, impact, denominators and limitations with R5.
- [ ] Check the submission evidence with its owners: R2 memory policy, R4 threat model and R6 reproducible installation, actual CI failure/explanation and working alert evidence.
- [ ] Record personal work, actual reviews, decisions and contributions with evidence; acknowledge outstanding dependencies rather than marking them completed.
- [ ] Perform a final product-readiness review and prepare only reviewed, English-language project artifacts for the team's merge process.

**Completion evidence:** the final presentation package, reviewed report, actual contribution/decision log, presentation preparation and a documented product-readiness decision.

## Completion record

Record this for each phase when it is completed:

| Phase | Evidence and version | Actual reviewer/date | Decision | Open dependency |
|---|---|---|---|---|
| Product definition | Final problem, scope and workflow specifications v1.0 | R1 specification finalization | Definition complete | Source execution and measured outcomes |
| Financial and research policies | Final policy specifications v1.0 with examples | R1 specification finalization | Definition complete | Implementation and independent verification |
| Golden content and scoring | Final domain specification v1.0 and eight reference cases | R1 specification finalization | Domain specification complete | R2/R5 eligibility, adapters, verification and scoring freeze |
| Other execution phases | Record actual evidence when produced | Actual reviewer and date required | Open until evidence exists | See the unchecked tasks |

Use the final specifications as the acceptance baseline. Update execution records only when the corresponding work and evidence exist.

## Related project documents

- The final-document register above links every project specification, its available Word version and the work log.
- [Project overview and current setup](../README.md).
- Existing implementation references: [architecture](architecture.md), [memory design](memory_policy.md), [tools](tools.md), [development evaluation](evaluation.md), [retrieval evaluation](retrieval_eval.md) and [evaluation guide](evaluation_guide.md). Their presence does not establish conformance with the final product policies.
