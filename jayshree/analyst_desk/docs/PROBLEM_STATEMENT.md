# Analyst Desk Problem Statement

**Status:** Final project specification v1.0.

## Problem statement

Equity research analysts at asset managers need to prepare company-comparison notes from annual filings. This requires locating supporting disclosures, extracting reported financial figures, reconciling fiscal periods and units, calculating ratios, comparing companies and years, and assessing changes in disclosed risk factors. Incorrect figures, incompatible comparisons or unsupported conclusions can undermine trust in the research note.

Analysts need a research workflow that makes financial comparisons and their supporting evidence easy to inspect. Every financial figure and derived calculation must be traceable to filing evidence and checked in code. Differences in fiscal periods, units and metric definitions must be explicit. Conclusions about changes in risk disclosures must be supported by evidence from both periods, with uncertainty and missing evidence clearly stated.

Analyst Desk should assist this work by coordinating filing research, quantitative analysis and a separate critic review into a cited draft. The analyst must be able to review and edit the research plan and approve the exact final note before publication. The project's value must be evaluated through research quality, cost and time against comparable fixed-workflow and single-agent baselines.

## Intended outcome

A source-backed company-comparison note that an analyst can inspect, challenge, correct and decide whether to publish. Numerical verification supports human judgement; it does not establish that every interpretation is correct.

## Evaluation question

How does coordinated research with a critic compare with fixed-workflow and single-agent baselines in research quality, cost and time under matched conditions?

## Product acceptance requirements

- Use the supported company, period and source boundaries and the project's financial and research policies.
- Make each financial figure, derived calculation and explanatory claim inspectable against its evidence.
- Account for the requested scope and display missing evidence and material comparison limitations.
- Measure correction count and significance, total research/review time, source-checking effort and model usage/cost on comparable tasks.
- Compare fixed-workflow, single-agent and multi-agent results under matched conditions, reporting failures and limitations alongside successful results.

Record implementation evidence, current-product acceptance and measured outcomes through the product checklist and project work log.

## Project documents

- [Word version](PROBLEM_STATEMENT.docx).
- [Product and domain checklist](PRODUCT_CHECKLIST.md).
- [Project work and decision log](PROJECT_WORK_LOG.md).
