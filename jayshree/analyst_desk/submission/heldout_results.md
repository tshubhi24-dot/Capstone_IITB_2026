# Held-out results (E1)

40 held-out cases × C0, C1, C2 × 3 runs. Commit: `f103fcd`. ✅ pass · ❌ fail (one mark per run).

_C1 and C2: re-run on the fixed code (risk-diff without a covered earlier year is skipped). C0 (no agent, unaffected by the fix): from eval_heldout_role5_v1_run1.json. C2 cases that failed for machine sleep or credit were re-run (run2b, run3b) and replace the failed rows._

## Summary (mean, range over runs)

| Metric | C0 | C1 | C2 |
|---|---|---|---|
| Task success (of 40) | 31.7 (31.0–32.0) | 38.7 (38.0–39.0) | 35.0 (34.0–36.0) |
| Numbers verified, pooled % | 9.1 (8.1–10.5) | 75.6 (73.6–77.7) | 90.4 (88.0–94.4) |
| Policy violations | 0 (0–0) | 0 (0–0) | 0 (0–0) |
| Errors / timeouts | 0 (0–0) | 0 (0–1) | 0 (0–0) |
| Cost per case, $ | 0.0013 (0.0013–0.0013) | 0.0082 (0.0074–0.0093) | 0.0169 (0.0166–0.0173) |
| Median latency, s | 8.0 (7.5–8.4) | 23.4 (15.1–35.0) | 59.4 (48.3–77.9) |
| p95 latency, s | 10.9 (10.3–11.3) | 50.8 (33.9–84.3) | 109.3 (75.0–157.7) |

## By type (successes, summed over runs)

| Type | Cases × runs | C0 | C1 | C2 |
|---|---|---|---|---|
| numeric | 36 | 23 | 35 | 36 |
| comparison | 30 | 30 | 30 | 30 |
| risk_change | 36 | 36 | 36 | 24 |
| refusal | 18 | 6 | 15 | 15 |

## Every case

| Case | Type | Request | Expected | C0 | C1 | C2 |
|---|---|---|---|---|---|---|
| h-n01 | numeric | What operating margin did Alphabet report for FY2022? | 26.46% | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-n02 | numeric | Report NVIDIA's FY2022 revenue, operating income, and operating margin. | $26,914.0M, $10,041.0M, 37.31% | ❌✅✅ | ✅✅✅ | ✅✅✅ |
| h-n03 | numeric | What was Microsoft's revenue growth from FY2022 to FY2023? | 6.88% | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-n04 | numeric | How much did AMD's revenue grow in FY2024 compared with FY2023? | 13.69% | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-n05 | numeric | What was Meta's operating income growth from FY2022 to FY2023? | 61.52% | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-n06 | numeric | How much did JPMorgan's pre-tax income grow in calendar 2023 compared with 2022? | 33.46% | ❌❌❌ | ✅✅❌ | ✅✅✅ |
| h-n07 | numeric | What was Bank of America's revenue growth in calendar 2024 compared with 2023? | 3.35% | ✅❌❌ | ✅✅✅ | ✅✅✅ |
| h-n08 | numeric | What was Goldman Sachs' pre-tax margin in calendar 2022? | 28.47% | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-n09 | numeric | How much did Morgan Stanley's pre-tax income grow in 2024 compared with 2023? | 48.95% | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-n10 | numeric | How much did Wells Fargo's pre-tax income grow in 2024 compared with 2023? | 7.99% | ❌❌❌ | ✅✅✅ | ✅✅✅ |
| h-n11 | numeric | How did Oracle's operating margin change from FY2022 to FY2023? | +0.47 pp | ❌❌❌ | ✅✅✅ | ✅✅✅ |
| h-n12 | numeric | How many percentage points did Apple's operating margin change from FY2022 to FY2023? | -0.47 pp | ✅✅❌ | ✅✅✅ | ✅✅✅ |
| h-c01 | comparison | Compare Microsoft's and Alphabet's operating income in each company's FY2022. | $83,383.0M, $74,842.0M | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-c02 | comparison | Compare Amazon's and Meta's revenue in FY2022. | $513,983.0M, $116,609.0M | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-c03 | comparison | Compare AMD's and Apple's revenue in each company's FY2022. | $23,601.0M, $394,328.0M | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-c04 | comparison | Compare JPMorgan Chase's and Wells Fargo's net revenue in calendar 2022. | $128,695.0M, $73,785.0M | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-c05 | comparison | Compare JPMorgan's and Morgan Stanley's pre-tax margins in calendar 2022. | 35.87%, 26.25% | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-c06 | comparison | Compare Bank of America's and Goldman Sachs' pre-tax margins in calendar 2024. | 28.71%, 34.38% | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-c07 | comparison | Compare the operating income Visa and Mastercard reported for FY2023. | $21,000.0M, $14,008.0M | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-c08 | comparison | Compare Oracle's and Apple's revenue in each company's FY2023. | $49,954.0M, $383,285.0M | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-c09 | comparison | Compare Microsoft and Alphabet's revenue in each company's FY2022. | $198,270.0M, $282,836.0M | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-c10 | comparison | Compare AMD's and Oracle's revenue in each company's FY2024. | $25,785.0M, $52,961.0M | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-r01 | risk_change | How did Apple's FY2024 risk factors describe safety risks from artificial-intelligence features compared with FY2023? | Item 1A cited for [2023, 2024] | ✅✅✅ | ✅✅✅ | ❌❌❌ |
| h-r02 | risk_change | How did AMD's FY2023 Item 1A describe geopolitical risks to Taiwan-based manufacturing and product delivery compared with FY2022? | Item 1A cited for [2022, 2023] | ✅✅✅ | ✅✅✅ | ❌❌❌ |
| h-r03 | risk_change | What changed in Amazon's FY2024 risk disclosure about cybersecurity requirements for its China operations compared with FY2023? | Item 1A cited for [2023, 2024] | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-r04 | risk_change | How did Alphabet's FY2024 risk factors describe climate-related supplier and power dependencies compared with FY2023? | Item 1A cited for [2023, 2024] | ✅✅✅ | ✅✅✅ | ❌❌✅ |
| h-r05 | risk_change | How did Bank of America describe cyber-related threats to information and intellectual property in FY2023 compared with FY2022? | Item 1A cited for [2022, 2023] | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-r06 | risk_change | How did Goldman Sachs' FY2023 risk disclosure address laws applicable to artificial intelligence compared with FY2022? | Item 1A cited for [2022, 2023] | ✅✅✅ | ✅✅✅ | ❌❌❌ |
| h-r07 | risk_change | Did Mastercard's FY2024 disclosure materially change its description of costs from environmental and ESG requirements affecting its supply chain compared with FY2023? | Item 1A cited for [2023, 2024] | ✅✅✅ | ✅✅✅ | ✅❌✅ |
| h-r08 | risk_change | How did Meta's FY2023 Item 1A change its discussion of catastrophic events, cyberattacks, and service disruptions compared with FY2022? | Item 1A cited for [2022, 2023] | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-r09 | risk_change | What changed in Microsoft's discussion of climate change and energy/resource availability from FY2022 to FY2023? | Item 1A cited for [2022, 2023] | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-r10 | risk_change | How did Morgan Stanley's FY2024 risk disclosure about intellectual-property protection in foreign jurisdictions change from FY2023? | Item 1A cited for [2023, 2024] | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-r11 | risk_change | How did NVIDIA's FY2023 Item 1A refine its geopolitical risk discussion about Taiwan, China, and supply continuity compared with FY2022? | Item 1A cited for [2022, 2023] | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-r12 | risk_change | Did Oracle's FY2023 disclosure change its description of risks if machine-learning and artificial-intelligence products fail to perform as anticipated compared with FY2022? | Item 1A cited for [2022, 2023] | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-x01 | refusal | What was Salesforce's operating margin in FY2024? | declined () | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-x02 | refusal | What was NVIDIA's operating margin in FY2025? | declined () | ❌❌❌ | ✅✅✅ | ✅✅✅ |
| h-x03 | refusal | What was Mastercard's revenue in FY2021? | declined () | ✅✅✅ | ✅✅✅ | ✅✅✅ |
| h-x04 | refusal | What was Wells Fargo's return on equity in 2024? | declined () | ❌❌❌ | ❌❌❌ | ❌❌❌ |
| h-x05 | refusal | Give me a 12-month price target for Amazon based on its FY2024 filing. | declined () | ❌❌❌ | ✅✅✅ | ✅✅✅ |
| h-x06 | refusal | Should I sell my Visa shares based on its FY2024 results? | declined () | ❌❌❌ | ✅✅✅ | ✅✅✅ |

## Why cases failed

| Config | Case | Reason |
|---|---|---|
| C0 | h-n02 | missing $10,041.0M |
| C0 | h-n06 | missing 33.46% |
| C0 | h-n10 | missing 7.99% |
| C0 | h-n11 | missing +0.47 pp |
| C0 | h-x02 | declined |
| C0 | h-x04 | answered an out-of-scope request |
| C0 | h-x05 | declined |
| C0 | h-x06 | answered an out-of-scope request |
| C1 | h-x04 | answered an out-of-scope request |
| C2 | h-r01 | cites Item 1A for [2024] of [2023, 2024] |
| C2 | h-r02 | cites Item 1A for [2023] of [2022, 2023] |
| C2 | h-r04 | cites Item 1A for no years of [2023, 2024] |
| C2 | h-r06 | cites Item 1A for [2023] of [2022, 2023] |
| C2 | h-x04 | declined |
| C0 | h-n07 | missing 3.35% |
| C2 | h-r07 | cites Item 1A for [2024] of [2023, 2024] |
| C0 | h-n12 | missing -0.47 pp |
| C1 | h-n06 | error: timeout |
