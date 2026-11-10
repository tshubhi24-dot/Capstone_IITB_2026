# JPMorgan and Meta: public development-case domain review

Source revision: `33fef7f94c0b1703265cc8057066b8456122bd54`. Cases: Main development `d16` and `d17` only.

This delivers actual source-backed reference answers and review contracts. It is an assistant-assisted R1 development review, not independent R5 gold, a protected evaluation set, calibrated human annotation or the required ten-company-year human risk labels. No application/model run was performed.

## Scope and source treatment

The evidence is the local public Item 1A JSONL cache. Each selected passage is preserved in SOURCE_PASSAGES.json with issuer, fiscal year, accession, kind, exact full text, local file/line and SHA-256. Cached chunk overlap and page/footer noise are retained in the evidence; excerpts below isolate the relevant sentences. Original HTML completeness, section boundaries, cross-references and global absence were not verified. The review classifies specific paired topics, not all risk factors.

| Source | Accession | Cached Item 1A rows |
|---|---|---:|
| JPM_2022 | 0000019617-23-000231 | 149 |
| JPM_2023 | 0000019617-24-000225 | 151 |
| META_2023 | 0001326801-24-000012 | 200 |
| META_2024 | 0001326801-25-000017 | 208 |

Row counts are inventory counts, not the percentage of an original section reviewed.

## d16 — What changed in JPMorgan's risk factors from 2022 to 2023?

**Reference answer:**

In the reviewed cached Item 1A passages, JPMorgan made its cybersecurity risk-driver discussion more specific in FY2023. The FY2022 list discussed mobile/internet/cloud expansion, acquisitions and remote-work access; the FY2023 counterpart explicitly includes malicious use of machine learning/generative AI for social-engineering and targeted-phishing attacks and quantum-computing threats to information protections [JPM_2022_item1a_085; JPM_2023_item1a_085]. I classify that as Changed detail in an existing cyber-risk topic, not as proof that the risk category was wholly new.

The reviewed economic/market-risk paragraph retains substantially the same themes, including inflation/deflation/recession, capital/liquidity/credit and market volatility; its minor wording/pagination differences do not establish a substantive thematic change [JPM_2022_item1a_037; JPM_2023_item1a_037]. This is Unchanged within that reviewed paragraph only. These cached pairs are examples, not an exhaustive original-filing comparison, and do not establish global Added or Removed labels.

### Paired topic evidence

#### d16-R1 — Cybersecurity risk drivers — Changed

Within the matched security-breach driver list, FY2023 explicitly discusses malicious actors using machine learning/generative AI for more advanced social-engineering and targeted-phishing attacks, and quantum-computing advances that may defeat information protections. The FY2022 matched list instead explicitly identifies mobile/internet/cloud expansion, acquisitions/integration and remote-access/video-conferencing arrangements. This is changed detail in an existing cyber-risk disclosure, not proof that cybersecurity or AI risk was wholly new across the filing.

**Earlier:** JPM_2022_item1a_085
> The risk of a security breach due to a cyber attack could increase in the future due to factors such as:

> the increased use of remote access and third party video conferencing solutions to facilitate work-from-home arrangements for employees.

**Later:** JPM_2023_item1a_085
> advances in artificial intelligence, such as the use of machine learning and generative artificial intelligence by malicious actors to develop more advanced social engineering attacks, including targeted phishing attacks

**Limit:** The comparison is this matched list/topic. No Removed conclusion follows from omission of the remote-access bullet here; absence elsewhere was not established.

#### d16-R2 — Economic and market risk themes — ScopedUnchanged

The reviewed economic/market-risk paragraph retains the same substantive exposure categories: sentiment/confidence, inflation/deflation/recession, employment, capital/liquidity/credit, interest-rate and market-price volatility, extraordinary/geopolitical events and economic strength. There are minor wording and pagination differences. These themes are substantially unchanged within this paragraph; this is not a claim that all JPMorgan risk factors were unchanged.

**Earlier:** JPM_2022_item1a_037
> inflation, deflation or recession

**Later:** JPM_2023_item1a_037
> inflation, deflation or recession

**Limit:** Scoped thematic continuity, not verbatim identity, section equivalence or proof of unchanged economic risk severity.

### Domain contract

- Retain the exact issuer and chronological year pair named in the request.
- Give at least one substantive, source-supported paired comparison with real passage IDs and topic-appropriate before/after evidence.
- Classify changes conservatively: Changed for demonstrated wording/detail; Unchanged only within an explicit reviewed scope; Unverified when prior comparable evidence or completeness is missing.
- State cached-excerpt coverage limits; do not convert an absent keyword/search result into full-filing absence.
- Distinguish disclosure wording from realised business effects, increased economic risk or legal materiality; do not invent investment advice.
- Allow validated alternative topics/passage pairs; exact wording or these particular reference topics is not the only passing answer.

### Pass, Fail and Incomplete

- **Pass:** A completed answer meets the mandatory issuer/year/topic/evidence/uncertainty rules, with at least one demonstrated change or an adequately supported challenge to the requested newness premise. Optional continuity examples remain scoped. The approved reference answer is an example, not a string-match answer key.
- **Fail:** An identifiable wrong issuer/year/topic, invented/nonexistent or non-supporting citation, unsupported full-filing Added/Removed/Unchanged assertion, causal/materiality overclaim, or investment recommendation remains. A known wrong assertion stays Fail even if the run also times out.
- **Incomplete:** No definite false assertion is established, but retrieval, required paired evidence, run execution or substantive review is unfinished. An honest inability to classify is not a false Added claim, but does not by itself complete the requested comparison. Preserve incomplete attempts in the denominator.

## d17 — What new risks did Meta add in its 2024 risk factors compared with 2023?

**Reference answer:**

The question presupposes new risks, but these cached passages do not support calling AI risk wholly new in FY2024: Meta already described AI and generative-AI deployment risks in FY2023 [META_2023_item1a_026; META_2023_item1a_027]. The comparable FY2024 discussion retains that topic and makes the list more explicit about misinformation/deepfakes and consumer protection [META_2024_item1a_028; META_2024_item1a_029]. This is Changed detail within an existing risk, not proof that those themes were absent everywhere in the earlier filing.

A second supported change is strategy-risk framing: FY2023 refers to the metaverse strategy and investments; FY2024 refers to the Reality Labs strategy and explicitly includes metaverse and wearables, with AI/wearables/devices in its development direction [META_2023_item1a_035; META_2024_item1a_037]. I classify that as Changed wording/scope in the reviewed strategy paragraph. Full-filing additions/removals and economic materiality remain unverified; I would not force an Added label from this evidence.

### Paired topic evidence

#### d17-R1 — Generative-AI risk disclosure detail — Changed

The question's premise must be qualified: Meta already disclosed risks of AI initiatives, including generative AI, in FY2023. Both years discuss infrastructure/headcount investment and risks such as harmful content, accuracy, bias, IP, privacy and cybersecurity. In the matched FY2024 risk-list paragraph, misinformation wording explicitly includes deepfakes and the list explicitly includes consumer protection. Classify this as changed or more specific wording within an existing AI risk, not a wholly new AI risk added in FY2024.

**Earlier:** META_2023_item1a_026, META_2023_item1a_027
> our AI-related efforts, particularly those related to generative AI, subject us to risks related to harmful or illegal content, accuracy, misinformation (including related to elections), bias, discrimination, toxicity, intellectual property infringement or misappropriation

**Later:** META_2024_item1a_028, META_2024_item1a_029
> misinformation and deepfakes (including related to elections), bias, discrimination, toxicity, consumer protection, intellectual property infringement or misappropriation

**Limit:** Specific phrases are newly explicit in this matched paragraph. The review does not establish that deepfakes or consumer-protection topics were absent everywhere in the FY2023 filing.

#### d17-R2 — Metaverse versus Reality Labs strategy framing — Changed

The comparable strategy/investment-risk wording changes from possible failure of the metaverse strategy in FY2023 to possible failure of the Reality Labs strategy in FY2024. The FY2024 passage explicitly says Reality Labs includes metaverse and wearables and describes directing efforts toward AI, wearables and devices. This supports a change in framing/detail of the reviewed strategy risk, not a finding that wearables or Reality Labs economic exposure first arose in 2024.

**Earlier:** META_2023_item1a_035
> We may not be successful in our metaverse strategy and investments, which could adversely affect our business, reputation, or financial results.

**Later:** META_2024_item1a_037
> We may not be successful in our Reality Labs strategy and investments, which could adversely affect our business, reputation, or financial results. Our Reality Labs efforts include our metaverse and wearables initiatives.

**Limit:** The matched paragraphs support the wording/scope shift. Full-filing Added/Removed status and economic materiality remain unverified.

### Domain contract

- Retain the exact issuer and chronological year pair named in the request.
- Give at least one substantive, source-supported paired comparison with real passage IDs and topic-appropriate before/after evidence.
- Classify changes conservatively: Changed for demonstrated wording/detail; Unchanged only within an explicit reviewed scope; Unverified when prior comparable evidence or completeness is missing.
- State cached-excerpt coverage limits; do not convert an absent keyword/search result into full-filing absence.
- Distinguish disclosure wording from realised business effects, increased economic risk or legal materiality; do not invent investment advice.
- Allow validated alternative topics/passage pairs; exact wording or these particular reference topics is not the only passing answer.
- Explicitly permit a paired-evidence answer that challenges the request's blanket newness premise. Do not require any Added label.

### Pass, Fail and Incomplete

- **Pass:** A completed answer meets the mandatory issuer/year/topic/evidence/uncertainty rules, with at least one demonstrated change or an adequately supported challenge to the requested newness premise. Optional continuity examples remain scoped. The approved reference answer is an example, not a string-match answer key.
- **Fail:** An identifiable wrong issuer/year/topic, invented/nonexistent or non-supporting citation, unsupported full-filing Added/Removed/Unchanged assertion, causal/materiality overclaim, or investment recommendation remains. A known wrong assertion stays Fail even if the run also times out.
- **Incomplete:** No definite false assertion is established, but retrieval, required paired evidence, run execution or substantive review is unfinished. An honest inability to classify is not a false Added claim, but does not by itself complete the requested comparison. Preserve incomplete attempts in the denominator.

## Existing Main scoring rule and required interpretation

`data/evaluation/dev_cases.jsonl:16–17` stores issuer/year expectations only. `analystdesk/evaluation.py:98–109` treats an error as failure; otherwise its risk-change success branch checks only whether Item1A-shaped citation strings for both expected years occur. It does not adjudicate whether a passage exists or supports the topic, nor whether Added/Removed/Changed is warranted. The later numerical checker is a separate control. A harness pass is therefore citation-year coverage, not this domain acceptance decision.

Keep the original automated result and the R1 domain outcome separate. Do not retrospectively rename these visible development cases as unseen tests. If a run honestly lacks comparable evidence, record Incomplete unless a known wrong assertion makes it Fail; do not force a new-risk conclusion to satisfy d17.

## Reviewer checklist

1. Confirm issuer and direction of the exact year pair.
2. Resolve every retained reference to the stored full text and its accession; inspect the matched topic, not merely the section opening.
3. Check the actual wording difference and whether the label is narrower than the reviewed scope.
4. Accept a properly supported alternative topic or d17 premise challenge; reject fabricated novelty from missing retrieval.
5. Separate factual disclosure differences from economic impact, materiality, recommendation and full-filing absence claims.
6. Record Pass, Fail or Incomplete with reasons, preserving automated scorer results and failed/unfinished attempts.

Files: DOMAIN_CONTRACTS.json contains both contracts and actual answers; SOURCE_PASSAGES.json preserves ten selected cached chunks; REVIEW_METADATA.json records source hashes and scope.
