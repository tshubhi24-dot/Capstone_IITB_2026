# Analyst Desk: R1 problem statement

**Status:** Draft for R1 review. Real-user and domain-expert validation remain pending.

## Problem statement

Equity research analysts at asset managers need to prepare company-comparison notes from annual filings. This requires locating supporting disclosures, extracting reported financial figures, reconciling fiscal periods and units, calculating ratios, comparing companies and years, and assessing changes in disclosed risk factors. Incorrect figures, incompatible comparisons or unsupported conclusions can undermine trust in the research note.

Analysts need a research workflow that makes financial comparisons and their supporting evidence easy to inspect. Every financial figure and derived calculation must be traceable to filing evidence and checked in code. Differences in fiscal periods, units and metric definitions must be explicit. Conclusions about changes in risk disclosures must be supported by evidence from both periods, with uncertainty and missing evidence clearly stated.

Analyst Desk should assist this work by coordinating filing research, quantitative analysis and a separate critic review into a cited draft. The analyst must be able to review and edit the research plan and approve the exact final note before publication. The project's value must be evaluated through research quality, cost and time against comparable fixed-workflow and single-agent baselines.

## Intended outcome

A source-backed company-comparison note that an analyst can inspect, challenge, correct and decide whether to publish. Numerical verification supports human judgement; it does not establish that every interpretation is correct.

## Alignment with the capstone brief

| Brief requirement | How it informs the problem statement | Printed page |
|---|---|---|
| R1 defines the problem and users. | State the intended analyst, research task and trust problem before choosing implementation details. | 4 |
| Identify a real user, measure an outcome and state limits accurately. | Treat the intended user and expected benefit as requiring actual validation and measurement. | 6 |
| Support an equity research analyst preparing company comparisons from filings. | Cover financial figures, ratios, prior years, peers and disclosed risk factors. | 15 |
| Signature A: numbers linked to XBRL facts or cited table cells and checked in code. | Require numerical traceability and explicit fiscal/unit comparability. | 16 |
| Signature B: parallel research and a critic compared against a single agent. | Assess quality, cost and time under matched models, tools and budgets; do not assume a benefit. | 6, 16 |
| The analyst can edit the plan and signs the exact note before publication. | Keep research direction and the final publication decision under human control. | 15-16 |

## Decisions and validation still required

- R1 review and adoption of this framing.
- Identification of a real user and confirmation of their workflow, pain points and useful outcomes.
- Human domain-expert feedback and resulting revisions.
- A justified company/sector/year selection and detailed financial/research policies.
- Agreed outcome measures and subsequent evidence of quality, cost, time and limitations.

These follow-up decisions will be recorded separately. No user interview, measured improvement or implementation compliance is established by this draft. The current main implementation is assessed against the requirements after they are defined.

## Source and tracking

- [Word document](R1_PROBLEM_STATEMENT.docx).
- [Capstone architecture and build guide](../capstone_projects_Analyst_Desk.pdf), printed pp.4, 6 and 15-16.
- [R1 completion checklist](R1_CHECKLIST.md), phase 1 and the R1-first execution order.
- [R1 work and decision log](R1_WORK_LOG.md).
