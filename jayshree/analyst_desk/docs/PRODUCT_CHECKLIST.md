# Analyst Desk Product and Domain Checklist

Define the analyst's problem, supported research scope, evidence standards and acceptance policies independently of the current implementation. Assess existing behavior against those decisions and record a gap when it falls short.

This checklist covers product and domain work, including the shared evidence needed for product acceptance. It is not a complete technical implementation checklist. The responsibility key and handoffs identify the engineers who own the supporting systems and evaluation.

All tasks remain unchecked until the work and review occur. Existing drafts, controls and automated tests are inputs to review; they do not establish completed human decisions, adoption or validation. Maintain the project decision and contribution log throughout the work.

## Execution order: product definitions, then shared validation

Prepare the domain and product proposals first. Where a phase also needs team agreement, leave that shared review open until the relevant owners participate. Preparing a proposal does not complete its adoption, implementation or evaluation.

| Order | Work to start with | Roles | Product/domain output | Related phase |
|---|---|---|---|---|
| 1 | Define the analyst's problem and the intended product outcome. | R1 | Problem statement and proposed success measures. | 1 |
| 2 | Identify a real user and describe their research workflow and needs. | R1 | User/workflow description and research scenarios. | 1 |
| 3 | Define data, source and coverage requirements. | R1 | Requirements and justified coverage proposal, independent of existing code. | 1 |
| 4 | Talk to a human domain expert and assess the feedback. | R1 | Actual feedback and domain decisions. | 2 |
| 5 | Define written financial, research and acceptance policies. | R1 | Policy proposal with examples and unresolved questions. | 3 |
| 6 | Define golden-answer content and domain scoring expectations for development work. | R1 | Source-grounded expectations/rubric for R5 review; no protected-case authoring. | 4 |
| 7 | Prepare the demonstration narrative and script. | R1 | Three-story script and a list of evidence needed from the team. | 10 |
| Throughout | Record actual decisions/contributions and practise the architecture and own scope. | R1 | Maintained decision/contribution log and presentation preparation. | 11 |

After the product and domain proposals are prepared, coordinate shared validation with the other role owners. R1 policy review of held-out cases requires controlled access from R5.

| Shared work | Roles | Boundary |
|---|---|---|
| Validate source feasibility and adopted coverage. | R1, R2, R3 | R1 defines requirements; source/workflow owners confirm feasibility and gaps. |
| Adopt policies, implement controls and review a corrected note. | R1, R2, R3, R4, R5 | R1 decides domain acceptance; engineers implement and R5 checks agreed regressions. |
| Review golden answers, human risk labels and protected-case policy alignment. | R1, R2, R5 | R5 controls independent evaluation and protected assets. |
| Review memory behaviour and applicable development lessons. | R1, R2, R3, R4, R5 | R1 reviews meaning; owners implement controls and R5 measures benefit. |
| Review independent experiments, security evidence and reported outcomes. | R1, R2, R3, R4, R5, R6 | R1 interprets product impact; execution remains with the relevant owners. |
| Execute the full demo, collect operational evidence and finalize submission. | R1, R2, R3, R4, R5, R6 | R1 owns the narrative; each member supplies evidence for their component. |

## Review and recording rules

- Keep repository content, deliverables, code comments, commit messages and pull-request descriptions in English.
- Check an item only after the work occurs. Record the evidence, actual reviewer, date, source version and decision.
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

## 1. Define the problem, user and supported scope

**Classification:** R1 product definition with shared scope and impact review. **Owner:** R1. **Support:** R2, R3.

**Roles:** R1, R2, R3. Prepare the product scope proposal first; coordinate source/workflow agreement afterwards.

- [ ] Identify a real equity-research user and describe their current filing-comparison workflow and pain points.
- [ ] State the product outcome and supported research questions: financial figures, year/peer comparisons, disclosed risk changes and follow-up research.
- [ ] Independently define and justify data/source coverage for 10-15 companies, two sectors and three years. Require Item 1A Risk Factors, Item 7 MD&A, preserved tables, financial facts, company/year/Item metadata and cached evidence; evaluate any existing corpus against those requirements.
- [ ] Define handling for unsupported companies/years, missing evidence, incompatible comparisons and requests for investment recommendations. Treat additional features such as quarterly charts as separate scope decisions.
- [ ] Define measurable usefulness criteria and how they will be measured; agree the scope with the team.

**Completion evidence:** an adopted product-scope record with user, problem, outcomes, boundaries, acceptance questions and unresolved limitations.

Treat existing company, sector and year selections as candidates to assess. Retain, revise or reject them with a documented domain reason.

## 2. Obtain actual domain-expert feedback

**Classification:** Direct R1 duty. **Owner:** R1.

**Roles:** R1. Domain-user feedback complements the financial/domain-expert review; retain evidence of each.

- [ ] Have a suitable human domain expert inspect the problem, scope, example question and proposed note format.
- [ ] Discuss financial comparability, useful evidence, unacceptable errors and the limits of the product.
- [ ] Record actual feedback and the decisions to accept, change or reject it, with reasons.
- [ ] Incorporate the agreed changes and retain evidence of the review.

**Completion evidence:** a domain-review record identifying the reviewer, relevant experience, material/version reviewed, actual date, feedback and resulting decisions. A prepared review template is not evidence that this interaction occurred.

## 3. Adopt financial, research and publication policies

**Classification:** Direct R1 domain-policy duty with engineering dependencies. **Owner:** R1. **Support:** R2, R3, R4, R5.

**Roles:** R1, R2, R3, R4, R5. Prepare domain definitions first; keep team adoption and implementation review as shared work.

- [ ] Define fiscal periods, actual dates, annual/quarterly boundaries, currency, units, reporting perimeter and suitable peer comparisons.
- [ ] Define the supported operating-margin comparison, its operating-income/revenue inputs and clear labels. Independently assess any proposed alternative metric; do not assume that an existing bank pre-tax-margin convention satisfies an operating-margin requirement.
- [ ] Agree rounding, percentage versus percentage-point changes, signs, invalid denominators and missing-value handling.
- [ ] Define original-as-reported versus later-reported values, restatements and presentation changes; require traceable sources and code calculations.
- [ ] Define sufficient evidence for factual/causal claims and added, removed, changed or unchanged risks; state when evidence is insufficient. Prohibit investment recommendations and promises of returns, and treat retrieved text as evidence rather than instructions.
- [ ] Decide which errors block product acceptance and what happens when numerical checks fail or claim review is unavailable/incomplete. Distinguish draft review from exact-note publication approval.
- [ ] Agree domain expectations for memory privacy, correction, withdrawal and deletion with R2/R4; record the team's effective policy version.

**Completion evidence:** an adopted, versioned policy and concrete acceptance examples handed to the implementation and evaluation owners. Record the justification for precision conventions, original-as-reported defaults, any alternative bank metric and HOLD rules. Treat a 98% verified-share monitoring threshold as an alert, not permission to publish known errors.

## 4. Review financial golden answers and scoring rules

**Classification:** Direct R1 golden-content duty; R5 owns evaluation implementation and independent cases. **Owner:** R1 for domain correctness. **Support:** R2, R5.

**Roles:** R1, R2, R5. Prepare domain expectations first; coordinate source/evaluator agreement afterwards.

- [ ] Review development questions and their expected financial answers against original source evidence, independently of the tested answer generator.
- [ ] Associate each expected value with its company, metric, fiscal period, accounting basis, units and source/table location.
- [ ] Verify formulas, precision, signs and derived changes; prevent a matching number elsewhere in the output from passing a wrong association.
- [ ] Agree the meaning of pass, fail, incomplete review and defective/disputed case with R5, including comparison and refusal requirements.
- [ ] Resolve disagreements and freeze the accepted expected answers, policy and rubric before subsequent scored runs.

**Completion evidence:** source-reviewed development expectations, a scoring rubric, a disagreement/decision record and an acknowledged R5 handoff. Earlier development cases remain development cases.

## 5. Validate the required human risk-change labels for ten company-years

**Classification:** Shared domain annotation and evaluation work; R1 does not personally own every label. **Owners:** R1 for domain content/review; R5 for the annotation/evaluation process. **Support:** R2.

**Roles:** R1, R2, R5. Coordinate this shared annotation/review work after the domain policy and content proposal.

- [ ] Select ten target company-years and obtain the relevant earlier/later filing evidence for each comparison.
- [ ] Ensure human reviewers inspect both periods and assign findings using agreed risk-label definitions, with a rationale and source locations. Perform or coordinate R1 domain review without compromising evaluation independence.
- [ ] Review sufficient relevant-section coverage before claiming addition/removal; distinguish newly disclosed wording from a newly arising economic risk.
- [ ] Record the actual human reviewer/date and resolve material disagreements with R5. Keep rejected or uncertain findings visible.
- [ ] Freeze the accepted annotations and acceptable answer boundaries; verify that completion counts reflect actual human reviews.

**Completion evidence:** ten completed company-year review records, paired evidence, final finding labels, rationales and R5 adjudication. These are separate from human labels on judge-calibration outputs.

## 6. Review a current-version research note and close product findings

**Classification:** R1 product acceptance and domain interpretation of shared end-to-end requirements. **Owner:** R1. **Support:** R2, R3, R4, R5.

**Roles:** R1, R2, R3, R4, R5. Review the product against adopted requirements; do not assume existing behavior is correct.

- [ ] Select a representative development request and record the code/configuration, source snapshot, scope and adopted policy used for the review.
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
- [ ] Check R5's held-out cases against the adopted written policy through a controlled R1 review. Preserve the independence boundaries: agent tuners do not author held-out cases, and defence builders do not author independent attacks.
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

**Roles:** R1, R2, R3, R4, R5, R6. Draft the demo script first; execute and verify the full demo with the team afterwards.

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
| Not yet recorded | Pending | Pending | Pending | Pending |

Artifact names and document formats are organizational choices. Existing behavior does not limit what a correct requirement or expected answer can demand. Reuse drafts only after actual review; their existence does not complete a phase.

## Related project documents

- [Problem statement](PROBLEM_STATEMENT.md) and [Word version](PROBLEM_STATEMENT.docx).
- [Project work and decision log](PROJECT_WORK_LOG.md). Preparing an artifact does not complete its review or validation.
- [Project overview and current setup](../README.md).
- [Architecture](architecture.md), [memory policy](memory_policy.md), [development evaluation](evaluation.md) and [evaluation guide](evaluation_guide.md).
