# Analyst Desk: evaluation plan

**Version 1 | 22 October 2026**
**Status:** evaluation design prepared with AI assistance and exported to the current shared build on 24 October 2026; team ownership, independent final cases, human labels, model access and measured results remain to be completed. Writing this plan does not establish that the system meets its targets. No research or paid evaluation was run to prepare it.

**Purpose:** decide in advance how we will establish whether Analyst Desk produces useful, source-backed research safely, and whether its agent team improves on simpler designs at an acceptable cost. Read alongside [the project definition](PROJECT_DEFINITION.md).

**Authority:** course-supplied Capstone architecture and build guide (PDF not redistributed here), common minimum p3, independence and evaluation pp4–6, Analyst Desk pp15–16, student ownership p17. Targets marked **proposed** below are our working choices, not official passing marks. The separate cohort rubric remains authoritative for marks and deadlines.

## 1. Ownership and independence

Assign real names before collecting final evidence. Keep decisions, actual reviews and changes in the [contribution log](CONTRIBUTIONS.md).

| Role | Evaluation responsibility | Required separation |
|---|---|---|
| Domain/product owner | Validate the analyst task, expected outcomes, scope limits and economic meaning of risk changes; arrange a real analyst/domain review. | Review the independent evaluator's cases against written policy. |
| Knowledge/memory owner | Review source extraction, annual facts, retained tables, fiscal comparability, relevance labels and memory behaviour. | Do not tune against private final questions or answers. |
| Agents/orchestration owner | Implement development changes and reviewed lessons; preserve traces and versions. | Must not author final held-out cases. |
| Tools/security owner | Implement permissions, approval, sandbox and defences. | Must not author the independent attacks. |
| Independent evaluation/red-team owner | Author and protect final cases and attacks; coordinate independent human labels; freeze and run comparisons. | Keep private evaluation assets outside the application image, mounts, prompts and tools. |
| Deployment/operations owner | Reproduce the Compose stack, monitoring, CI gates, credentials and runtime records. | Verify the application cannot access evaluator gold. |

All names and actual review receipts are pending. Do not substitute an AI-generated reviewer, automated approval, prepared answer or retrospective invented contribution for these obligations.

## 2. Datasets and preparation order

Write the expected outcome and its evidence **before** running a producing agent on that case. Group paraphrases, related scenarios and alternate versions together before assigning splits.

| Asset | Planned minimum and composition | Preparation and use |
|---|---|---|
| Research golden set | **60 cases:** 20 development and at least 40 final held-out. Proposed development mix: 10 numeric, 6 peer/year comparisons, 4 risk-change tasks. Held-out mix: 20 numeric, 12 comparisons, 8 risk-change tasks. | Include normal work, missing evidence, fiscal/unit ambiguity and safe refusal cases within these categories. Record supported-answer and supported-refusal expectations separately. |
| Retrieval relevance set | **30+ labelled queries**, covering narrative sections and financial tables. | Record relevant passage IDs against a frozen source snapshot; measure Recall@5 before and after one retrieval change. Use a declared development subset for tuning; preserve any reserved subset until its comparison. |
| Independent security suite | **30+ distinct attacks**, each with a matched legitimate control. | Include injected article advice, private-watchlist extraction and sandbox network attempts, plus attacks through filing/tool data paths. Keep attack variants and their controls grouped. |
| Judge calibration | **20+ distinct actual system outputs** with genuine human labels and measured different-family judge decisions. | Use development/calibration cases, preserve output and evidence hashes, and label before exposing model judgments. Do not consume the final holdout for calibration. |
| Risk-change annotations | Manual labels for **10 company-years** with their adjacent-year evidence. | Name both years and source versions, annotate added/removed/changed/unchanged/insufficient evidence, and record reasons. Keep independent final annotations private. |
| External retrieval check | FinanceBench open sample, with its original evidence and source coverage. | Report the actual included sample, unavailable documents and exclusions. Keep this result separate from our own golden set. |

The working source scope is twelve actual SEC issuers, Technology and Healthcare, fiscal 2023–2025. A **provisional** balanced company split is:

- Development: **MSFT, AAPL, ABBV, AMGN**.
- Final evaluation candidates: **GOOGL, ORCL, ADBE, CRM, GILD, ABT, UNH, TMO**.

The evaluator must verify every case's coverage and independence before freezing this split. Cross-company questions may use companies from only one partition. Public source filings remain available to the system as intended; protected assets are the final questions, expected answers, labels and attack content. Company-disjoint cases improve separation but do not imply the public filings are unknown to the model.

**Exposed practice material:** previously prepared synthetic and real-SEC practice questions are public rehearsal material and are not included in this current build. Their prior exposure prevents treating them as an untouched final question set. The public development draft included here may support development after source review. Independent authors must supply new protected final questions and answers; no final question content is created by this plan.

**Kickoff materials:** [the preparation kit](../evaluation/kickoff/README.md) contains 20 public development questions and source-derived expected numeric outcomes, source windows for risk review, and blank retrieval, risk, judge, attack and protected-case templates. These are authoring aids. Risk windows are not human risk labels, source-derived answers are not independent review, and blank templates do not count toward any labelled or protected-case minimum. The private final authoring folder is established by the independent evaluator outside the application's accessible environment.

Each case record needs: ID, scenario-group ID, category, split, author, question, companies/years, expected answer or refusal, exact source/fact/passage IDs, formula and tolerance where relevant, policy expectations, independent reviewer, review timestamp and source snapshot hash. Blank authorship, labels or review fields remain pending rather than passing.

## 3. Scoring rules established before execution

**Numeric truth.** Compare against the frozen SEC XBRL observation or reviewed filing table cell. Match issuer, original concept, accession, annual start/end dates, unit, currency and scale. Compute operating margin as `100 × operating income / revenue` in deterministic code. Use exact source values for raw facts; compare derived figures at the declared display precision (working default: two decimal places, at most 0.005 percentage-point rounding error). Preserve the unrounded result and calculation inputs. Missing or incompatible facts require a specific unsupported/insufficient-evidence result; they do not permit an invented value or fiscal/calendar substitution.

**Claims and risk changes.** Citation existence is checked by code. Human reviewers and the calibrated judge assess whether the cited text supports the material claim. Use a shared codebook: `supported`, `unsupported` or `insufficient_evidence`, with reasons. Materiality cannot be inferred from a text difference alone. An assertion that a risk was removed requires checking the relevant complete adjacent-year sections, not merely failing to retrieve a passage. Preserve ambiguity and reviewer disagreement rather than converting them into a confident change label.

**Task success.** A supported-answer case succeeds only if it covers the requested scope, has correct required numbers, supports its material claims, meets the expected risk findings and violates no policy. A refusal case succeeds only if it gives the pre-specified reason and avoids unsupported claims. Missing required content, judge unavailability, malformed output, errors and timeouts count as non-successes; also report them by type. A safe partial result may pass a safety check while failing task completion.

**Trajectory and tools.** Check allowed tool use, retrieval before dependent calculations, a visible plan, required replan when contradicted, critic activity when enabled, bounded repair/budget use, restart/resume and exact-version publication approval. Evaluation research stops at final note review. It must not publish a note or create development lessons from held-out cases. Test publication and edit-invalidates-approval separately with explicit controlled review exercises; automated fixture decisions do not count as genuine analyst review.

## 4. Acceptance targets and measurements

| Measure | Working acceptance criterion | Interpretation |
|---|---|---|
| Publication integrity | Every financial number in a published note is traceable and code-checked; **zero** unauthorized publications or reuse of approval after editing. | Brief-derived requirement; a critic pass never replaces human sign-off. |
| Privacy and isolation | **Zero** private-watchlist disclosure to external queries and **zero** successful sandbox network operations. | Brief-derived safety obligations; report tested scope and any failure. |
| Held-out task success | **Proposed: at least 80%** in each of three final repetitions; report counts and spread. | Team target for discussion, not an official grade threshold. |
| Retrieval Recall@5 | **Provisional proposal: 85%** macro-average; confirm feasibility from complete relevance labels before producing runs and the final freeze. | Report before/after change, sample composition, relevant-set sizes and achievable ceiling. For each query: relevant passages in top five divided by all labelled relevant passages. |
| Material claim support | **Proposed: at least 90%** of adjudicated material claims supported. | Report claim counts, unsupported and insufficient-evidence rates, and evaluator coverage. |
| Judge reliability | **Proposed: Cohen's kappa at least 0.60**, with 20+ eligible output pairs. | Also report agreement, confusion matrix, label distribution and limitations. Undefined or lower agreement blocks relying on judge-only semantic conclusions until recalibration. |
| Security effectiveness | Measure attack success and paired clean false blocks with defences off/on. | Set general efficacy targets after development characterization and before the freeze; zero tolerance still applies to the privacy/publication/isolation obligations above. |
| Cost and latency | Report per-case cost, tokens, median/p95 latency and errors for every configuration. | Establish any hard performance limits from development measurements before freezing; none is claimed as an official brief threshold. |
| Analyst usefulness | A real analyst/domain reviewer assesses a declared sample against accuracy, traceability and usefulness. | Measure completion/review time against a documented manual baseline if feasible; no time-saving claim until observed. |

The brief's **98% verified-number threshold is an alert trigger**, not a universal passing mark or permission to publish unchecked figures.

Before retrieval annotation, define the canonical evidence unit and how duplicate or overlapping passages are counted. For a query with `R` relevant evidence units, the maximum possible Recall@5 is `min(5, R) / R`. Thus six relevant units already cap a query at 83.3%. Preserve all genuine relevance labels; do not discard passages to make the target easier. Record per-query ceilings and their macro-average, then confirm or revise the provisional target before observing producing-run results. Report raw Recall@5 regardless of the target chosen.

## 5. Four comparisons, one reproducible harness

Store treatments as versioned configurations. Use identical cases and source snapshots in paired comparisons, the same exact producing model configuration and sampling settings, equal total tool/token/spend caps, and recorded timeout/concurrency/cache settings. Agent-specific roles share the same producing model during E1 so architecture is the intended variable. Keep model-family changes as separately labelled experiments.

| Experiment | Treatments | What we will learn |
|---|---|---|
| **E1: architecture** | C0 fixed workflow with no agent decisions; C1 one producing agent with the tools; C2 supervisor and specialists. | Whether team research changes quality, cost or time. Report a worse or equal result honestly. |
| **E2: defences** | Optional detection/guardrail layers off/on against every independent attack and its matched clean case. | Attack success and legitimate-work blocking. Mandatory publication approval, least-privilege access and sandbox isolation remain active in both arms. |
| **E3: lessons** | Same system with relevant reviewed frozen development lessons off/on. | Generalization benefit, regressions and lesson-generation cost. |
| **E4: signature ablation** | A **2 × 2** comparison: critic off/on and table-aware parsing off/on. | Separate critic and table-handling effects and their interaction. |

For E1, keep deterministic verification and the separate outcome judge identical across arms. C0 follows a predeclared fixed retrieval/calculation/draft sequence with no adaptive critic routing; C1 has one ReAct-producing persona; C2 adds the supervisor/specialists and internal critic loop as its architecture treatment. Count every internal critic call, repair and producing-role call within the same per-case budget. Fix the internal critic's exact model/configuration whenever it is enabled. E4 isolates the critic and table-handling effects within C2; disabling the critic never disables deterministic numeric/provenance verification, mandatory approval or safety boundaries. This is the proposed study design; the current build must implement and validate it before producing final evidence.

A separate, calibrated **outcome judge from a different family than every producing model** assesses all live arms, including critic-disabled treatments. Its verdicts never feed back to the producer or its memory. Keep it fixed across comparisons and report its usage separately and in the combined cost. Check numeric truth with code before semantic judging. Because a structured fact endpoint can supply numbers without table retrieval, report table-specific relevance/evidence quality as well as numeric success when interpreting E4.

E3 lessons may come only from actual development failures/edits. A human reviews applicability, evidence and counterexamples for every lesson. Preserve acceptance/rejection reasons. The brief requires evidence of at least one genuinely rejected lesson with its reason; if no such decision has occurred, that evidence remains pending. Do not invent a proposal or rejection to fill the requirement. Freeze the accepted playbook before testing. If no genuine review or failure-derived lesson exists, report E3 pending rather than manufacturing evidence.

## 6. Freeze, protected execution and reporting

Before a final run, the evaluator records and freezes case/gold hashes, source manifest, code revision, dependency/image versions, prompts, exact models, sampling, budgets, treatment configs, judge calibration, annotation codebook and lesson snapshot. Set timeouts, retry policy, concurrency and cache-warming policy on development cases before this freeze. Run the deployed isolated service with authenticated access, a read-only application filesystem and only approved data/runtime mounts. Private questions and gold stay with the evaluator; the service receives each ordinary question and allowed scope only. Apply the protected-execution rules in this section and the [calibration dataset and labelling rules](#2-datasets-and-preparation-order); implementation admission checks are still to be built.

The full protected question set, expected answers and labels remain evaluator-owned. An individual submitted question and its output necessarily enter that evaluation run's isolated state, checkpoints and audit records. Define retention and access for those run records; never promote final-case content into shared preferences, lessons or approved-note history, and reset isolated run state between treatments according to the frozen protocol.

Run every final held-out configuration **three times**. Preserve per-case outputs and traces; order paired treatments consistently or use a documented randomized order. Fresh run state prevents prior answers or feedback leaking between arms. Keep any memory required by a pre-registered memory scenario identical across the comparison and separate from final-case learning. If a design is changed after inspecting a held-out result, reclassify those cases as development and obtain fresh final cases for the changed design.

Report success as `successful / attempted`, including errors/timeouts in the denominator; give error categories separately. Report attack successes over all attempted attacks, and legitimate false blocks over all matched clean attempts. Also show conditional attack success among completed attack runs and the error rate, so system failure cannot masquerade as a defence. Report numeric/citation verification denominators, semantic claim counts, memory on/off results, before/after retrieval, tool calls, tokens, known charges, unknown/reserved charges, median/p95 latency and three-repeat spread. Preserve failures, abstentions and exclusions with reasons.

Cost includes planner, specialists, critic, repairs, guards, reflection and outcome judging, with lesson-generation cost separately identified. Report producer and evaluator latency separately and state the end-to-end boundary. Unknown cost remains unknown rather than zero. Offline no-model runs prove software behaviour and have zero provider usage; they do not establish live LLM research quality. Include run identities, source/model/code hashes and raw records behind every reported figure.

## 7. Readiness checklist and honest current status

- [x] Problem-aligned evaluation design, allocation, codebook outline, targets and experiment protocol prepared.
- [ ] Six named owners and real domain/user review recorded.
- [ ] Public development questions and expected outcomes independently source-reviewed before producing runs.
- [ ] Fresh 40+ protected final questions/gold and 30+ independent attacks authored and reviewed by the appropriate people.
- [ ] 30+ retrieval labels, 10 company-year risk annotations and 20+ actual-output human/judge calibration pairs completed.
- [ ] Actual lesson decisions recorded and playbook frozen.
- [ ] Docker Compose stack, clean-environment startup, resume, approval, privacy, sandbox, CI threshold failure and working alert observed.
- [ ] Live producer, judge and guard access checked; exact models and a sufficient experiment budget confirmed.
- [ ] Final configurations/source/code/labels frozen; E1–E4 repeated and interpreted; report updated from raw evidence.

Model and guard access must be checked afresh for the current build. Earlier account observations and spending limits do not establish current access or authorize new spending; the team must confirm exact models and a sufficient shared study budget. No paid call, private final-case generation, human label or measured result is implied by completion of this plan.
