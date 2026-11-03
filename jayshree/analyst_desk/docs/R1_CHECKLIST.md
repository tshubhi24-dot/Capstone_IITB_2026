# R1 completion checklist: Domain and Product Lead

Use this checklist in order to complete the product and domain work for Analyst Desk. All items start unchecked. Existing drafts, working controls and automated tests are inputs to review; they do not establish completed human decisions.

## Working rules

- Keep repository content, deliverables, code comments, commit messages and pull-request descriptions in English.
- Keep conversations and personal operational details out of project artifacts.
- Develop on `R1_role`, based on main commit `f2fb159623ddfb3547ce2f0ed2615902c6d3d1d6`. Record a new baseline if main changes before evaluation or demonstration.
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

**Owner:** R1. **Support:** R2, R3. **Brief:** pp.4-6 and 15-16.

- [ ] Identify the intended equity-research user and describe their current filing-comparison workflow and pain points.
- [ ] State the product outcome and supported research questions: financial figures, year/peer comparisons, disclosed risk changes and follow-up research.
- [ ] Confirm the adopted coverage and source boundaries. The brief requires 10-15 companies in two sectors over three years. The current project's choices are 15 Technology/Finance companies, FY2022-2024, and cached SEC evidence.
- [ ] Define handling for unsupported companies/years, missing evidence, incompatible comparisons and requests for investment recommendations. Decide whether quarterly charts are part of the supported product.
- [ ] Define measurable usefulness criteria and how they will be measured; agree the scope with the team.

**Completion evidence:** an adopted product-scope record with user, problem, outcomes, boundaries, acceptance questions and unresolved limitations.

## 2. Obtain actual domain-user or domain-expert feedback

**Owner:** R1. **Brief:** pp.4-6.

- [ ] Have a suitable human domain reviewer inspect the problem, scope, example question and proposed note format.
- [ ] Discuss financial comparability, useful evidence, unacceptable errors and the limits of the product.
- [ ] Record actual feedback and the decisions to accept, change or reject it, with reasons.
- [ ] Incorporate the agreed changes and retain evidence of the review.

**Completion evidence:** a domain-review record identifying the reviewer, relevant experience, material/version reviewed, actual date, feedback and resulting decisions. An AI-prepared review is not evidence of this interaction.

## 3. Adopt financial, research and publication policies

**Owner:** R1. **Support:** R2, R3, R4, R5. **Brief:** pp.3 and 15-16.

- [ ] Define fiscal periods, actual dates, annual/quarterly boundaries, currency, units, reporting perimeter and suitable peer comparisons.
- [ ] Adopt metric definitions and labels. Explicitly justify the project's bank pre-tax-margin convention and keep it distinct from operating margin.
- [ ] Agree rounding, percentage versus percentage-point changes, signs, invalid denominators and missing-value handling.
- [ ] Define original-as-reported versus later-reported values, restatements and presentation changes; require traceable sources and code calculations.
- [ ] Define sufficient evidence for factual/causal claims and added, removed, changed or unchanged risks; state when evidence is insufficient.
- [ ] Decide which errors block product acceptance and what happens when numerical checks fail or claim review is unavailable/incomplete. Distinguish draft review from exact-note publication approval.
- [ ] Agree domain expectations for memory privacy, correction, withdrawal and deletion with R2/R4; record the team's effective policy version.

**Completion evidence:** an adopted, versioned policy and concrete acceptance examples handed to the implementation and evaluation owners. Precision conventions, the bank metric and a stricter HOLD policy are project choices. The 98% threshold in the brief is a monitoring alert, not permission to publish known errors.

## 4. Review financial golden answers and scoring rules

**Owner:** R1 for domain correctness. **Support:** R2, R5. **Brief:** pp.4-6 and 16.

- [ ] Review development questions and their expected financial answers against original source evidence, independently of the tested answer generator.
- [ ] Associate each expected value with its company, metric, fiscal period, accounting basis, units and source/table location.
- [ ] Verify formulas, precision, signs and derived changes; prevent a matching number elsewhere in the output from passing a wrong association.
- [ ] Agree the meaning of pass, fail, incomplete review and defective/disputed case with R5, including comparison and refusal requirements.
- [ ] Resolve disagreements and freeze the accepted expected answers, policy and rubric before subsequent scored runs.

**Completion evidence:** source-reviewed development expectations, a scoring rubric, a disagreement/decision record and an acknowledged R5 handoff. Earlier development cases remain development cases.

## 5. Complete human risk-change labels for ten company-years

**Owner:** R1 domain review. **Support:** R2, R5. **Brief:** p.16.

- [ ] Select ten target company-years and obtain the relevant earlier/later filing evidence for each comparison.
- [ ] Personally inspect both periods and assign findings using the agreed risk-label definitions, with a rationale and source locations.
- [ ] Review sufficient relevant-section coverage before claiming addition/removal; distinguish newly disclosed wording from a newly arising economic risk.
- [ ] Record the actual human reviewer/date and resolve material disagreements with R5. Keep rejected or uncertain findings visible.
- [ ] Freeze the accepted annotations and acceptable answer boundaries; verify that completion counts reflect actual human reviews.

**Completion evidence:** ten completed company-year review records, paired evidence, final finding labels, rationales and R5 adjudication. These are separate from human labels on judge-calibration outputs.

## 6. Review a current-version research note and close product findings

**Owner:** R1. **Support:** R2, R3, R4, R5. **Brief:** pp.3 and 15-16.

- [ ] Select a representative development request and record the code/configuration, source snapshot, scope and adopted policy used for the review.
- [ ] Run through the application's research and human-review gates under the applicable authorization; retain the exact plan, note, checks and trace.
- [ ] Review every displayed financial figure and derived change, its source/calculation chain, requested coverage, fiscal disclosure and interpretation.
- [ ] Review risk novelty, causal claims, missing evidence and claim-review completeness; record an actual accept, edit, reject or HOLD decision with reasons.
- [ ] Turn defects into evidence-backed R3/R4 handoffs with expected behaviour and R5 regression checks. Re-review the corrected exact note before closing findings.

**Completion evidence:** a versioned product-review register linking each finding to its source, policy, owner, fix/test evidence and R1 disposition. Preserve original failed outputs; a new code version does not retroactively correct them.

## 7. Review memory behaviour and development lessons

**Owner:** R1 for domain judgement. **Support:** R2, R3, R4. **Brief:** p.3, L9/L12; pp.15-16.

- [ ] Check that saved preferences, previous-note comparisons and correction/deletion behaviour match the adopted user-facing policy; document what remains in checkpoints or published records.
- [ ] Review genuine development-derived lesson proposals for correctness, applicability, counterexamples and possible harm.
- [ ] Record actual human decisions, including a genuine rejected lesson with its reason; retain relevant accepted lessons and freeze the playbook before held-out evaluation.
- [ ] Coordinate memory-on/off and lesson-before/after evidence with the owners; distinguish available controls from demonstrated benefit.

**Completion evidence:** domain-review decisions, an auditable reviewed/frozen playbook and relevant memory/lesson demonstration references. R3 builds the improvement loop; R5 measures unseen-case benefit.

## 8. Confirm independent evaluation and security handoffs

**Owner:** R5 for independent evaluation; R1 reviews domain/policy alignment. **Support:** R2, R3, R4. **Brief:** pp.3-6 and 16.

- [ ] Confirm evidence of at least 60 distinct cases: about 20 development and at least 40 protected held-out cases, with expected outcomes fixed before testing and related variants kept together.
- [ ] Confirm the independence boundaries: agent tuners do not author held-out cases, and defence builders do not author independent attacks. Conduct R1 policy review through a controlled process.
- [ ] Coordinate at least 20 genuinely human-labelled outputs for judge calibration; require agreement, Cohen's kappa and disagreement evidence for the actual judge configuration.
- [ ] Obtain R5/R4 evidence for 30+ independent attacks, defences off/on and legitimate-work false blocks, including the project's retrieved-instruction, private-watchlist and sandbox-network scenarios.
- [ ] Obtain R2/R5 evidence for the required retrieval comparison and FinanceBench external retrieval check; identify remaining source/label limitations.

**Completion evidence:** acknowledged ownership, case/label counts, freeze references, independence records and result artifacts. R1 does not need protected answers copied into this checklist or exposed to the application.

## 9. Interpret experiments and validate product claims

**Owner:** R1 for product interpretation; R5 for execution/scoring. **Support:** R2, R3, R4, R6. **Brief:** pp.5-6 and 16.

- [ ] Review E1: C0/C1/C2 with matched research capability, models, tools, budgets and recorded memory/playbook settings; explain remaining differences.
- [ ] Review E2 defence effectiveness, E3 lesson benefit/harm and E4 critic on/off plus table-aware/plain-text ablations.
- [ ] Require three final held-out repetitions and report spread, failures/timeouts, success counts, policy violations, false blocks, cost, median latency and p95 latency.
- [ ] Check scoring meaning and comparable denominators. Twenty questions across three configurations are not 60 distinct cases; a coarse task pass is not complete note accuracy.
- [ ] Distinguish actual provider charges from estimates and current frozen configurations from historical results with incomplete provenance.
- [ ] Validate the usefulness outcome from phase 1 and agree evidence-backed presentation claims, including negative results and limitations.

**Completion evidence:** an R1 interpretation of R5's versioned results, measured user/product outcomes and an agreed claim-to-evidence register. Do not infer superiority from architecture or a development score alone.

## 10. Rehearse and record the required demonstration

**Owner:** R1 for script and narrative. **Support:** R2-R6. **Brief:** pp.6 and 15-16.

- [ ] Demonstrate a margin comparison with every financial figure linked to its supporting fact or calculation.
- [ ] Demonstrate the critic finding/correcting a planted wrong number while an injected retrieved article's investment recommendation stays out of the note.
- [ ] Demonstrate "What changed since our last note?" using a real, approved prior note and explain what memory contributed.
- [ ] Include exact-plan review, an edit invalidating prior note approval and the required resume/replan evidence with the engineering owners.
- [ ] Rehearse the full story on the actual demonstration version; label synthetic fixtures and explain real limitations and failures accurately.
- [ ] Coordinate a complete backup recording with R6 and verify that it opens and plays through. Keep the evidence tied to the demonstrated version.

**Completion evidence:** the actual demo script, rehearsal record, traces/source bookmarks and a verified backup recording. Screenshots and component tests alone do not complete the live demonstration.

## 11. Complete submission, contribution evidence and individual viva

**Owner:** R1 for product narrative and personal contribution. **Support:** R2-R6. **Brief:** pp.6 and 17.

- [ ] Redraw and explain the architecture and a numbered request walkthrough, including decisions made by models, code and people.
- [ ] Explain scope, financial/risk definitions, evidence limits, memory behaviour, experiment trade-offs, an actual design decision and remaining pilot-readiness work.
- [ ] Finalize slides and review the 4-6-page evaluation report for accurate scope, impact, denominators and limitations with R5.
- [ ] Check the submission evidence with its owners: R2 memory policy, R4 threat model and R6 reproducible installation, actual CI failure/explanation and working alert evidence.
- [ ] Record personal work, actual reviews, decisions and contributions with evidence; acknowledge outstanding dependencies rather than marking them completed.
- [ ] Perform a final R1 readiness review and prepare only reviewed, English-language project artifacts for the team's merge process.

**Completion evidence:** the final presentation package, reviewed report, actual contribution/decision log, viva practice and a documented R1 readiness decision.

## Completion record

Record this for each phase when it is completed:

| Phase | Evidence and version | Actual reviewer/date | Decision | Open dependency |
|---|---|---|---|---|
| Not yet recorded | Pending | Pending | Pending | Pending |

Suggested artifact names and document formats are organizational choices, not additional course requirements. Existing drafts may be reused after actual review; their existence does not check off a phase.

## Sources and related material

- [Capstone architecture and build guide](../capstone_projects_Analyst_Desk.pdf): printed pp.3-6, 15-17. Cohort guidelines separately control official deadlines and marks.
- [Project overview and current setup](../README.md).
- [Architecture](architecture.md), [memory policy](memory_policy.md), [development evaluation](evaluation.md) and [evaluation guide](evaluation_guide.md).
