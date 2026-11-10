# Analyst Desk Consolidated Specification Review

**Status: Final review complete.** The findings below are known implementation limitations, not an outstanding product-review decision.

**Current result: six findings remain Open and five are Partially resolved. None of the eleven findings is fully closed.** Working safeguards have been verified and retained separately as review history; they are not presented as missing features. Remaining issues concern incomplete enforcement, documentation guarantees and unresolved project-policy choices.

GitHub Main was fetched again and remains `33fef7f94c0b1703265cc8057066b8456122bd54`. No newer Main change is established since the initial review. The policy baseline is `R1_role` at `c64091276fea80140dd664c637c863b871c0b0e1`.

## 1 Current finding register

| Finding | Status | Current evidence and remaining issue |
|---|---|---|
| F01 Incomplete critic review | Open | Known failures block approval; missing or invalid review can still produce an approvable aggregate |
| F02 Every number verified guarantee | Open | Fact and arithmetic checks work; quantity coverage and source meaning are incomplete |
| F03 Bank metric selection | Partial | Pre-tax treatment is disclosed; requested-metric eligibility and explicit revised-task agreement need reconciliation |
| F04 Periods inputs and formula domains | Partial | Ordinary annual checks and comparability notes work; incompatible inputs and policy exceptions remain |
| F05 Filing versions | Partial | Original retention works; cutoff basis reliability and automatic restatement interpretation remain unresolved |
| F06 Risk pairs and coverage | Partial | Adjacent instructions work; nonadjacent plans receive conflicting instructions and coverage is not enforced |
| F07 Scope and mixed comparisons | Open | Unsupported-only requests and selected mixed comparisons fail; partial omissions and other comparison forms pass |
| F08 Private watchlist boundary | Open | Out-of-plan names are blocked; provider processing and policy descriptions conflict |
| F09 Retention and publication outcomes | Open | Exact signatures receipts and duplicate refusal work; deletion and unconfirmed outcomes need truthful handling |
| F10 Injection guarantee | Open | Known patterns are blocked; unconditional protection exceeds component coverage |
| F11 Completion evidence | Partial | Development records exist; consolidated release closure and independent acceptance are not established |

**Status rules.** Open means the stated issue remains. Partial means useful parts of that finding's requirements are implemented and verified, with a stated remainder. Implemented but unverified requires an identifiable change awaiting a relevant check. Closed and verified requires the complete agreed closure criteria and evidence. No finding is assigned either of the latter two statuses here.

<!-- PAGE -->

## 2 Verification evidence and boundaries

The review combines source inspection, selected tests and offline reproductions. Project document, config and script paths are relative to `jayshree/analyst_desk/`. Code shorthand such as `agent/`, `servers/`, `scope.py`, `edgar.py` and `memory.py` is relative to its `analystdesk/` package. Bare baseline policy filenames refer to the earlier `docs/` directory.

**Repository tests: 121 considered, 117 passed, 4 skipped.** Eleven selected modules ran against a read-only copy of current source and tracked public SEC cache files, in a temporary container with no network, private volumes or credentials. Runtime stores were isolated. The four skips were Docker-mode sandbox tests: the isolated container had no Docker socket or nested sandbox image. Local-mode sandbox tests ran. This is not a full repository or release-image result.

**Targeted probes: 83 assertions reproduced their expected observations.** These include positive controls and counterexamples; they are not 83 product acceptance passes. Exact source functions or prompt expressions were extracted and executed with synthetic amounts, fake model replies, synthetic approval material and temporary stores. Source hashes, observations and limitations are retained beside this report.

| Evidence reference | Local evidence under reverification | Coverage |
|---|---|---|
| U121 | offline_unit_tests.log and offline_test_manifest.json | Selected checks graph memory tools financial and scope tests |
| P37 | evidence_critic_numeric_scope/probe_results.json | 37 assertions for F01 F02 F07 |
| P28 | evidence_financial_risk/results.json | 28 assertions for F03 F04 F05 F06 |
| P18 | evidence_memory_security_readiness/probe_results.json | 18 assertions for F08 F09 F10 plus F11 inventory |
| Revision record | revision_record.json | Pinned revision and archived initial-report checksum |

Tests used dependencies from the existing `analystdesk-role6:42e2298` image, with current Main source mounted separately. A new Main image was not built. The running browser app still uses older `sha-8754386`, so its appearance is not evidence for the latest source.

No live model, paid API call, real-note publication, private runtime mutation or protected evaluation-case inspection was performed. Component reproductions do not establish that every live model run fails, that a real watchlist leaked, or that an actual published financial figure is wrong. Passing ordinary unit tests also does not close counterexamples they do not cover.

**Brief versus project policy.** Source-backed figures, compatible comparisons, meaningful critic review, exact approval and the private-data boundary support the capstone minimum. Bank alternatives, cutoff hierarchy, decimal rounding, lifecycle procedures and exact messages are adopted project details. Relaxing them requires an explicit decision; consolidation does not itself change policy.

<!-- PAGE -->

## 3 Verified controls retained as review history

These narrower controls are verified present at the reviewed revision. They are excluded from unresolved work below. They were not newly implemented during this review, and no unsupported author or introduction date is attributed to them. Each row closes only its stated control, not the broader related finding.

| Record | Verified control and evidence | Related finding |
|---|---|---|
| H01 | Correct fact tags and ratios pass; wrong tagged amounts and margins and uncited dollar amounts fail. U121 checks tests and P37 positive fixtures. | F02 |
| H02 | A known unsupported verdict creates an issue; failed aggregates block signing; automated writer corrections stop after two revisions. U121 graph tests and P37 gate probes. | F01 |
| H03 | An edited body fails its old approval token; fresh approval for that exact body succeeds. U121 portal tests and P18 signature fixtures. | F09 |
| H04 | Duplicate publication is refused; synthetic portal records retain hash approver and timestamps. U121 portal tests and P18 receipt fixtures. | F09 |
| H05 | Bank pre-tax treatment is named before plan approval; the plan can be approved or cancelled. U121 assumptions tests and P28 gate fixtures. | F03 |
| H06 | Ordinary annual facts are accepted and short-quarter facts rejected. Different fiscal ends and 53-week years receive notes. U121 edgar and figures tests plus P28 controls. | F04 |
| H07 | Original value is retained when a later presentation differs; later-value metadata is exposed. U121 edgar tests and P28 version fixtures. | F05 |
| H08 | Memory-off removes the past-note tool; evaluation mode also removes it. U121 memory-off tests. This does not certify every access or deletion boundary. | F08 F09 |
| H09 | A watchlist name outside the approved plan is blocked; an approved public-ticker query is allowed. U121 guard tests and P18 synthetic fixtures. | F08 |
| H10 | A known injected instruction is withheld and literal advice wording rejected; one clean fixture remains intact. U121 guard tests and P18 positive fixtures. | F10 |

The evidence supports saying that the review confirmed controls, reproduced residual gaps and defined closure checks. It does not support saying all eleven findings were fixed, that the running app is current or that final capstone evaluation is complete.

<!-- PAGE -->

## 4 Unresolved critic and numerical findings

### F01 Incomplete claim review can still be approved

**Status: Open.** Preserve H02 as verified history. P37 reproduced selection of at most ten cited lines and exclusion of uncited narrative. For two selected claims, empty, partial or duplicated positive verdicts could report both supported. Timeout, malformed JSON and missing verdicts returned no issues; the extracted aggregate and note gate then accepted approval. A fake signer was used, so no real token or publication was created.

**Example.** Ten checked claims can be correct while claim eleven wrongly attributes lower sales to a new regulation. Correct figures do not resolve that unreviewed explanation.

**Change and closure.** Inventory every retained substantive assertion. Require one valid verdict per required claim and distinguish Complete from Supported. Missing, duplicate, invalid or unavailable verdicts must leave review incomplete and block approval. Retain the two-revision bound. Test these response forms and prove full coverage. Ordinary approval cannot replace missing review; a separately permitted human review must preserve the automatic critic's original status.

**Brief and owners.** Each claim checked against evidence by a judge is core. A special human-completion route cannot replace required automatic evaluation evidence. R1 defines completeness; R3 implements; R4 gates; R5 tests; R6 displays coverage.

**Evidence.** P37; U121. `agent/team.py:140–165`; `agent/graph.py:371–417`; `docs/product_spec.md:175`; baseline acceptance policy `:50–57,77–81`.

### F02 Every number verified remains an unsupported guarantee

**Status: Open.** H01 confirms useful code checks. P37 reproduced omitted numerical forms, including USD amounts without a dollar symbol and unit counts, yielding zero detected figures and a 100% share. Tags or passage matches could retain wrong issuer, period, metric or segment labels. Title numbers were outside the checked body. Thousands-unit and signed-dollar fixtures also exposed matcher limits.

**Example.** A passage contains total revenue $500 million and segment revenue $100 million. Calling the latter total revenue can pass the quoted-occurrence check. A proper total-revenue fact tag is a different route and should reject the wrong value.

**Change and closure.** Inventory quantities across title, tables and narrative. Bind company, concept, period, perimeter, sign, currency, scale and version; enforce supported output forms or reject uncovered ones. Validate inputs before arithmetic. Distinguish no detected quantities from complete verification. Qualify the guarantee until coverage and association tests pass. No actual published issuer figure was proved wrong by these synthetic probes.

**Brief and owners.** Figures must be source-linked and code-checked with compatible inputs. R1 R2 R3 R4 R5 own definitions, metadata, enforcement and tests; R6 shows the real denominator.

**Evidence.** P37; U121. `agent/checks.py:39–108,125–202`; `agent/graph.py:371–379`; `docs/product_spec.md:182`.

<!-- PAGE -->

## 5 Bank tasks and compatible financial inputs

### F03 Bank metric selection needs policy reconciliation

**Status: Partially resolved.** H05 verifies disclosure and the existing plan gate. The earlier description of wholly silent substitution is corrected. P28 supplied a synthetic bank with operating and pre-tax inputs: fixed company metadata still selected pre-tax, independent of the requested metric. This does not establish eligible operating inputs for any real bank.

**Example.** Technology revenue 100 and operating income 30 give 30%. Bank net revenue 100 and pre-tax income 35 give 35% pre-tax margin. Its operating margin is unavailable in this example; there is no valid five-point operating-margin gap.

**Change and closure.** Preserve the requested metric and check eligible inputs per company-year. If operating income is unavailable, retain that row with a reason and offer a supported alternative. The existing gate can authorise a clearly explained revised task; a third gate is unnecessary. Reconcile the fixed convention with DG006's unavailable operating-margin expectation. Close after implementing the adopted rule or explicitly agreeing a coherent bounded task policy, then testing request and consent paths.

**Brief and owners.** Compatible comparison is core; the bank alternative is adopted policy. R1 decides; R2 validates; R3 R4 enforce scope; R5 tests; R6 explains the choice.

**Evidence.** P28; U121. `scope.py:22–25,42–48`; `agent/graph.py:169–181,292–307`; `agent/figures.py:43–61`; `docs/evaluation_guide.md:199`; baseline bank rules `:7,92,107`.

### F04 Annual eligibility and calculation domains remain partial

**Status: Partially resolved.** H06 confirms annual selection, quarter rejection and comparability notes. P28 reproduced acceptance of an approximately 18-month entry and division of revenue and income with different annual windows. It also reproduced negative-revenue margins, percentage growth from a negative baseline, meaningful amounts shown as $0.0M and an exact decimal rounding difference.

**Example.** Revenue 100 USD millions and income 20,000 USD thousands need normalisation to yield 20%. Income moving from −10 to +5 should show amounts and signed change under the adopted rule, instead of conventional −150% growth.

**Change and closure.** Validate issuer annual status, start/end dates, operations, currency, scale and compatible basis before pairing inputs. Plausible duration and end-year alone are insufficient. Implement or explicitly revise positive-revenue, positive-growth-baseline, smaller-unit and decimal-rounding rules. Zero or negative income with positive revenue remains valid. Close with compatible/incompatible pair tests and policy-boundary tests.

**Brief and owners.** Compatible source association is core. Exact denominator, growth and display conventions are adopted policy. R1 R2 R3 R4 R5 R6 share definition, implementation and display.

**Evidence.** P28; U121. `edgar.py:179–216,331–338`; `agent/figures.py:44–77,98–114`; baseline fiscal rules `:13–15,61–73` and bank rules `:129–131`.

<!-- PAGE -->

## 6 Filing versions and risk coverage

### F05 Version selection and difference interpretation remain partial

**Status: Partially resolved.** H07 verifies original retention and later-value metadata. P28 found no approved-basis or cutoff parameter in the financial interface. A later-only synthetic cache supplied its available record without enforcing a hypothetical earlier cutoff. Memory labelled an unexplained same-year difference “Restated since the last note”. No real non-reliance notice or amendment was tested.

**Example.** Original revenue 100 and income 20 give 20%. A later compatible pair 95 and 18 gives 18.95%. Mixing 20 with 95 gives an invalid 21.05%. A changed value alone does not establish a restatement.

**Change and closure.** Preserve versions, selected basis and approved cutoffs. Exclude evidence unavailable at a historical cutoff. Review amendments and reliability: affected originals cannot support a current conclusion after known non-reliance or confirmed correction without resolution. Labelled historical reproduction remains possible. Explain differences before calling them restatements. Explicitly declining unsupported cutoff tasks resolves only that scope item; reliability and classification still require agreed resolution and tests.

**Brief and owners.** Correct source use is core; the detailed hierarchy and cutoff procedure are adopted policy. R1 R2 R4 lead; R3 R5 R6 support.

**Evidence.** P28; U121. `edgar.py:148,190–207`; `servers/edgar_server.py:133–166`; `memory.py:166–193`; `docs/product_spec.md:111–113,176`; `docs/memory_policy.md:51`; baseline filing policy `:9–13,29–34`.

### F06 Requested risk pairs and coverage are not enforced

**Status: Partially resolved.** P28 verified the ordinary adjacent-year prompt and inclusion of the full plan. For an explicit 2022/2024 plan, however, the latest/prior instruction names 2023/2024. A three-year plan similarly emphasises only the last transition. The prompt requests Added/Removed/Changed without an enforced coverage or insufficient-evidence record.

**Example.** A moved paragraph is not necessarily Removed. A failed earlier search cannot establish Added. Comparing 2023/2024 does not answer an explicit 2022/2024 request.

**Change and closure.** Carry every requested company/year pair through research and validation. Record coverage, exclusions, versions and relocated text. Support scoped Unchanged and Insufficient evidence alongside justified change labels. Separate disclosure difference from economic significance. Close with nonadjacent/multiple-transition tests and independent paired-source review. A live model may follow the full plan despite the conflict; no inevitable wrong model outcome is claimed.

**Brief and owners.** Supported risk comparison is core; the exact five-state rubric is adopted policy. R1 defines; R2 supplies coverage; R3 routes; R5 independently labels; R6 displays limits.

**Evidence.** P28. `agent/team.py:192–218,233–238`; `config/llm.toml:83–88`; `docs/product_spec.md:63,124–126,174`; baseline evidence policy `:49–65`.

<!-- PAGE -->

## 7 Complete requests and private context

### F07 Request and comparison enforcement remains incomplete

**Status: Open.** P37 and U121 verified rejection of unsupported-only requests, unsupported years and same-line tagged mixed margins. Probes accepted “Compare Microsoft and Tesla FY2024” at the guard with only MSFT recognised. Cross-line common-metric ranking and a mixed-basis difference tag also escaped the targeted checker.

**Example.** Correct 20% operating and 35% pre-tax figures on separate lines do not support “the bank has the stronger operating margin”. An arithmetically correct +15 pp does not make the gap compatible.

**Change and closure.** Preserve all requested entities, years, metrics and pairs as covered, unsupported or unresolved. Obtain revised scope before dropping a requested part. Check basis at the comparison level, including difference tags, rankings, aggregates and prose across lines. Close with mixed-coverage requests and alternative comparison forms. The guard probe does not establish every live planner will omit the company; clarification could occur later.

**Brief and owners.** Answering the approved task correctly is core. R1 defines scope; R2 confirms coverage; R3 R4 enforce; R5 tests; R6 shows unresolved items.

**Evidence.** P37; U121. `query.py:44–64`; `agent/graph.py:217–236,280–283`; `agent/checks.py:208–213`; `docs/product_spec.md:71,90`.

### F08 Private watchlist processing needs an agreed boundary

**Status: Open policy conflict.** H08 and H09 verify narrower memory-off and out-of-plan controls. P18 recorded synthetic watchlist context in the extracted planner prompt using a fake model. Current memory policy discloses provider processing; earlier policy excludes it and current viva wording still says it must never reach a prompt.

**Example.** Researching public ticker MSFT differs from disclosing that MSFT belongs to an analyst's private list. The sensitive fact is membership and context. An approved public-ticker query does not automatically disclose membership.

**Change and closure.** Define whether the configured provider is inside the authorised processing boundary and reconcile policy descriptions. Retain membership controls for unrelated queries, outputs and traces. Use synthetic lists until validation. Close after a recorded decision, aligned implementation and relevant exfiltration tests. No real watchlist or provider call was used, so this is not an actual-leak finding.

**Brief and owners.** Keeping the list within the system and testing query exfiltration are core. The earlier no-model-disclosure rule is stronger adopted policy. R1 R4 decide; R2 R3 implement; R5 tests; R6 explains.

**Evidence.** P18; U121. `agent/graph.py:249–259,273–279`; `agent/guards.py:91–111`; `docs/memory_policy.md:22,29,52`; `docs/viva_notes.md:606`; baseline detailed memory rules `:34,50–54`.

<!-- PAGE -->

## 8 Record lifecycle and security assurances

### F09 Retention and publication states remain unresolved

**Status: Open.** H03 and H04 verify signatures, receipts and duplicate refusal. P18 reproduced an exception after a synthetic portal commit and a memory-sync exception after a confirmed save. The extracted publisher did not reconcile these states. Deletion and backfill fixtures also reproduced the distinction between active-memory deletion and retaining or reconstructing separate records.

**Example.** The portal can save note N and lose the response. “Publication refused” is not established. Deleting N from memory does not withdraw its portal copy, and backfill can recreate memory from it.

**Change and closure.** Correct “everything else is forgotten” and “Forget everything”. Explain checkpoints, memory, portal and lessons separately. Honour deletion/suppression before rebuilding. Treat lost responses as Unconfirmed until reconciled; confirmed saves remain Published when history sync fails. Close with fault-injection and lifecycle tests plus truthful UI. A documented manual reconciliation route may suffice; enterprise expiry automation is not a separate brief minimum.

**Brief and owners.** Truthful history and publication outcomes support human control; detailed suppression and withdrawal mechanisms are adopted lifecycle choices. R1 defines outcomes; R2 R3 R4 R6 implement; R5 validates.

**Evidence.** P18; U121. `agent/graph.py:427–443`; `servers/portal.py:147–165`; `memory.py:161–164`; `scripts/backfill_memory.py:35–40`; `docs/memory_policy.md:3,16,36,45,50,54,61`.

### F10 Injection protection remains overstated

**Status: Open assurance issue.** H10 verifies known instruction and literal advice controls. P18 reproduced an allocation paraphrase missed by both component patterns, and an instruction in a non-text JSON field left unscreened. These are component limits, not a successful attack demonstrated on the full application.

**Example.** Blocking “buy this stock” does not establish every indirect allocation recommendation will be detected. An exact-note signature binds text; it does not establish semantic safety.

**Change and closure.** Replace immunity language with the actual boundary. Treat retrieved material as untrusted evidence, preserve tool permissions and test required attacks independently across supported adapters and output forms. Close the wording issue when product and threat-model descriptions agree. Claim only attack outcomes supported by relevant tests; one planted example cannot certify every paraphrase.

**Brief and owners.** Guardrails and named security tests are core; universal immunity is not required. R4 builds; R5 independently tests; R3 R6 integrate; R1 approves accurate claims.

**Evidence.** P18; U121. `agent/guards.py:30–38,53–88`; `agent/checks.py:51–53,215–220`; `docs/product_spec.md:130`; `docs/threat_model.md:34`.

<!-- PAGE -->

## 9 Completion records and product acceptance

### F11 Existing development evidence does not establish full release completion

**Status: Partially resolved on reviewed Main.** This final submission supplies the product/domain completion record; it does not add shared execution evidence to Main. Credit existing development reports, a role-six offline audit, retrieval and memory-result records, evaluation procedures and reference answers. It would be incorrect to say all validation evidence is absent. The consolidated specification nevertheless lacks a clear replacement for the earlier register distinguishing definitions, implementation, independent acceptance and release execution.

Tracked inventory shows README-only held-out and red-team directories. No protected question or answer content was opened. Filename inventory cannot establish whether private, untracked or other-workspace final records exist. Live-check claims in viva notes were not replay-authenticated here.

**Example.** An application calculation agreeing with a reference margin is useful corroboration, not independent R5 verification or a frozen release. Practitioner workflow feedback supports expert engagement, not inspection or approval of an exact note.

**Change and closure.** Keep a concise release register with Defined, Implemented, Validated or Open, owner, revision and evidence location. Reconcile existing records before assigning missing work. R2 verifies sources and R5 independently verifies expectations and scoring before a frozen scored release. R1 may review protected policy fit through R5's controlled process without exposing cases to the agent or tuner. Close when a current register supports its claims; do not manufacture expert approval, lessons or results.

**Brief and owners.** R1 owns product definitions, expert engagement, golden content and demo. R5 owns independent evaluation; others supply evidence. Prototype inspection is an adopted checklist follow-up beyond the direct expert-engagement wording. The register format is optional; underlying deliverables and accurate claims are not.

**Evidence.** P18 inventory; `docs/evaluation.md:1–18,45–59`; `docs/role6_development_evidence.md:3–9,29–34`; `docs/evaluation_guide.md:97–165,169–203`; baseline checklist `:109–245` and golden rules `:170–174,193–199`.

### Execution records to reconcile with owners

- Independent source and scoring acceptance for development references.
- Human risk-change labels for ten company-years and judge calibration evidence under R5's controlled process.
- Genuine reviewed lessons and a frozen playbook.
- Matched quality cost and time experiments, independent security evidence and held-out repetitions.
- Current-version representative-note acceptance, three-story demo rehearsal and measured usefulness claims.
- Submission and contribution records with version-specific demo and viva claims.

These are requests to reconcile evidence, not assertions that every item is unfinished.

<!-- PAGE -->

## 10 Frontend changes still requiring evidence

This is the unresolved display handoff, separate from H01–H10. Wording is proposed, not claimed already implemented. R6 owns presentation; supporting roles provide the underlying state. The baseline frontend policy retains the full message inventory.

| Condition | Required product response | Support |
|---|---|---|
| Required critic coverage is incomplete | “Review incomplete. Final approval is unavailable.” Show reviewed and required claims and unresolved items. | R3 R4 R5 |
| Quantity coverage or association is unresolved | Show verified failed and unverified assertions; do not call a partial denominator universal verification. | R2 R3 R4 |
| Requested bank metric is unavailable | Retain the row and reason; offer the labelled alternative for explicit plan agreement. | R1 R2 R3 |
| Financial inputs are incompatible | Show the calculation as Unavailable with the incompatible period unit or version fields. | R2 R4 |
| Filing basis or reliability is unresolved | Show selected basis and the conclusion requiring review; preserve historical-task context. | R1 R2 |
| A requested entity or comparison is unsupported | Name each affected item and obtain revised scope; do not silently narrow the request. | R1 R3 |
| Comparable risk coverage is insufficient | Show Insufficient evidence and the missing year section or reviewed scope. | R2 R3 |
| Private context crosses the agreed boundary | Block or explain without exposing private membership in a message or trace. | R2 R4 |
| Publication response is lost | Show Unconfirmed until reconciled; a confirmed save with failed history sync remains Published. | R4 R6 |
| Memory is deleted disabled or reconstructed | State setting and deletion scope; do not imply checkpoint or portal erasure. | R2 R3 |
| Protection is described to the analyst | Explain known guardrails and relevant limits without an unconditional guarantee. | R1 R4 |

Existing pre-tax disclosure, ordinary failed-check block, exact-note approval and duplicate refusal remain verified history. Do not reintroduce them as wholly missing features.

<!-- PAGE -->

## 11 Engineering correction sequence and evidence access

First close F01's incomplete-review path and F02's association and coverage gaps, or clearly constrain unsupported output forms. Correct universal assurances immediately. Resolve F08's boundary decision before using a real private watchlist.

Then reconcile F03's task policy, enforce F04's compatible inputs and F07's complete scope. Resolve F05's version handling and F06's risk-pair coverage. Explicitly bound unsupported tasks where necessary.

For F09 use truthful lifecycle states and a tested reconciliation route; a narrow manual procedure may suffice. F10 needs accurate claims plus independent attack evidence. F11 needs a reconciled register rather than an unsupported statement that all work is complete or absent.

**Closure evidence:** agreed requirement or policy decision; implementation/document revision; relevant positive and counterexample checks; current result; remaining limitation; responsible review. After closure retain the ID in history and remove it from the open list. A commit alone is not verification.

Fixed historical scope, USD-only data and no news, Excel or calendar reconstruction can remain explicit limits. They do not authorise wrong values, silently dropped requests, incomplete mandatory review shown as complete or disclosure beyond the agreed boundary.

### Evidence locations

The repository [review evidence](evidence/product_domain/README.md) contains revision metadata, selected-test log/manifest, three sets of captured diagnostic results and detailed evidence notes. Original duplicate review drafts, raw runtime histories and reproducer scripts are not included. Working controls and earlier findings remain identifiable in this review’s history section.

### Pinned references

- [Reviewed Main source and documents](https://github.com/tshubhi24-dot/Capstone_IITB_2026/tree/33fef7f94c0b1703265cc8057066b8456122bd54/jayshree/analyst_desk)
- [Current product specification](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/33fef7f94c0b1703265cc8057066b8456122bd54/jayshree/analyst_desk/docs/product_spec.md)
- [Current memory policy](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/33fef7f94c0b1703265cc8057066b8456122bd54/jayshree/analyst_desk/docs/memory_policy.md)
- [Current evaluation guide](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/33fef7f94c0b1703265cc8057066b8456122bd54/jayshree/analyst_desk/docs/evaluation_guide.md)
- [Approved baseline and checklist](https://github.com/tshubhi24-dot/Capstone_IITB_2026/blob/c64091276fea80140dd664c637c863b871c0b0e1/jayshree/analyst_desk/docs/PRODUCT_CHECKLIST.md)

**Capstone basis.** Physical page 4 assigns the domain/product role. Pages 7–8 require source-linked code checks, compatible periods and units, judge-based claim checks, at most two revisions, exact-note approval, memory, private-watchlist protection, security tests and three demo stories. Shared evaluation requirements add independence and repeated held-out measurement.

**Minor documentation correction:** the reference-answer link uses section 9; its current heading is section 10. Update the fragment to `#10-reference-answers` when the source document is changed.
