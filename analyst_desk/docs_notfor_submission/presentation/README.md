# Rebuilding `docs_notfor_submission/presentation.pptx`

`build.js` is the source for the deck. The `.pptx` is a build artifact — change
the script, not the binary, or the next rebuild silently discards your edit.

```bash
cd docs_notfor_submission/presentation
npm install pptxgenjs      # the only dependency; node_modules/ is gitignored
node build.js              # writes ../presentation.pptx
```

The **Threat model** section's icons are committed PNGs in `icons/`, read with
`fs.readFileSync` at build time, so pptxgenjs stays the only thing a rebuild
needs. They were rendered once by `make_icons.js` (feather icons via
`react-icons`, rasterised with `sharp`); run that again only to change an icon,
and install its four dependencies first.

`applyTheme()` is inlined at the top of the script, so nothing outside npm is
needed. It runs after `writeFile()` because pptxgenjs sets the theme's fonts but
hard-codes Office's palette: until the deck's own colors are written into
`ppt/theme/theme1.xml`, every scheme color resolves to Office blue.

## Slides

1. **Securing secrets** — the `_SECRET_ENV` fix
2. **Forced approval injection** — the `tests/security/` chain
3. **Injected recommendation** — the four guards, and where each one lives
4. **Injected recommendation — the test run** — the verdict matrix the module
   prints, and **Fix 1**: the `wrap_tool_call` middleware that refuses the
   paraphrase at the write
5. **Poisoned tool arguments** — injected text shapes the code the quant sends
   to a tool it legitimately holds. Neither payload carries a forbidden import,
   so the hook and the sandbox pass both: `check_note` recomputes the wrong
   *number*, and the wrong *wording* reaches the note gate untouched
6. **Fix 1 — a guardrail on the write** — the `wrap_tool_call` middleware that
   refuses an uncited recommendation at `publish_note`, the analyst's own text
   included. First slide of the **Additional guardrails** section
7. **Fix 2 — the approver's signature** — Ed25519 in place of a shared-secret
   HMAC, so the deployment can check a sign-off and cannot manufacture one
8. **Fix 3 — only fields cross the hand-off** — the specialist's prose stops
   being a channel: verified spans and `fact_id`s, nothing else
9. **Threat model — where untrusted text enters** — the trust-boundary map:
   five arrows in, one out. First slide of the **Threat model** section
10. **Threat model — the Rule of Two** — which of the three properties each
    session holds, and the one session that holds all three
11. **Threat model — the most dangerous tool** — the five plain-code checks a
    `publish_note` call passes, and what each returns when it fires
12. **Threat model — the score, and how to game it** — `verified_share` returns
    100.0 on `0/0`, and the Prometheus rule meant to catch that is NaN-blind
13. **Threat model — what limits the damage at 3 am** — four rings of
    containment, and the honest answer about who is actually told
14. **Threat model — two agents, one capability** — the researcher and the
    writer are each safe alone; the hand-off between them was not
15. **Appendix — verification by configuration** — what C0, C1 and C2 each verify
16. **Appendix — the eight tools, and what each reads** — the whole `AGENT_TOOLS`
    surface, which is what makes guard 1 on slide 3 true
17. **Appendix — container, thread, process** — what actually runs in parallel in
    one C2 run, traced from *"Compare Microsoft and Alphabet's FY2024 operating
    margins"*
18. **Appendix — two "threads", and two databases** — LangGraph's `thread_id`
    against an OS thread, and the run checkpointer against the long-term store
19. **Appendix — the hooks around every tool call** — the three pre checks and
    the one post record, and which of them can actually refuse
20. **Appendix — guardrails at each stage** — every guardrail the MSFT-vs-GOOGL
    run passes through, in pipeline order, with the mechanism behind each one.
    Mirrors `docs_notfor_submission/security_summary.md` section 10

### Use-case numbers and fix numbers

They are two different sequences and the deck now says which is which. A **use
case** is an attack the deck walks through; `useCase(slide, n)` stamps the
number top right, and the `// ════ use case N` banners in `build.js` match it.
A **fix** is a change made to the code, numbered in the order the fixes were
made and carried as a `# Fix N - use case M` comment at each place in
`analystdesk/` that implements it. Fix 1 implements use case 3, Fix 2 use
case 2, and Fix 3 use cases 3 *and* 4 — which is why the fix slides are not in
the same order as the use cases they answer, and why one fix chip names two.

The two sequences also get their own deck sections. A **use case** slide sits in
the section named after the attack; a **fix** slide sits in **Additional
guardrails**, which comes after the use cases and before the appendix. A fix
slide's chip carries both numbers — `FIX 1  ·  USE CASE 3`,
`FIX 2  ·  USE CASE 2`, `FIX 3  ·  USE CASES 3+4` — so the mapping is readable
without this file.

`stamp(slide, text, x, w)` draws the chip; `useCase(slide, n)` is the thin
wrapper for the plain `USE CASE n` form. The appendix carries no chip — it is
reference, not a use case or a fix. The chip is measured against the title
beside it, and the budget shrinks as the chips grow: `USE CASE n` needs 1.20"
at x 10.95, the Fix 1 and Fix 2 chips 1.88" and 2.00" at x 10.45, and Fix 3's
2.36" at **x 10.15** — which leaves a title only 9.60" wide. The widest in the
deck is slide 4's at 9.54", so there is 0.06" in hand. A longer title, or a
longer fix chip, runs under it with no warning: measure both together.

Slides 3 and 4 are one fix over two slides, in one section: the guards, then the
run that exercises them. Slide 4 and all six appendix slides reuse the `FIX`
layout as a title-only frame — `leftCards()` is simply not called, so the full
12.2" width is free. Reference slides go last, in their own `Appendix` section,
which is now slides 9-14.

Slide 5 went through three drafts, and the reason matters more than the layout.

Draft 1 was about naming a forbidden tool. That needs the model to emit a call
for a function it was never offered, which the provider's constrained decoding
normally prevents — a barrier that is not ours and not uniform across models,
so a slide should not rest on it.

Draft 2 used poisoned *arguments*, but every payload was `import os` /
`socket` / `subprocess`. The sandbox blocks all of them, which made the slide
argue that the sandbox answers argument poisoning. **It does not**, and the
slide was accidentally reassuring.

Draft 3 — the current one — uses two payloads that reach for nothing. One is a
`* 1.1` multiplier; the other is a bare string, because `run_python` returns
whatever the code assigns to `result`. No import, no syscall, so the import
allowlist and the audit hooks pass both and `run_python` returns `ok=True` with
`blocked=[]`. A sandbox is an isolation boundary and has no idea what the right
answer is. **If this slide is ever edited, keep both payloads importless** — a
payload the sandbox blocks proves nothing, because the sandbox was always going
to win that one.

The two columns are the point of the table: the wrong *number* is caught by
`check_note` recomputing the `[calc:]` tag from XBRL, and the wrong *wording*
is caught by nothing in code — four of the five rules need a number or a
citation to inspect and the fifth is eleven literal advice terms, so numberless
prose passes with `0/0` reported as 100% verified. That is why the last row is
the note gate: it is the only control left for wording, and wording is what a
person reviews best.

The FIX MADE card says "Nothing new — already covered", because this attack was
defended before the scenario was written. That is the honest answer and it is
worth keeping; the deck should not invent a fix for a hole that was not open.

*Container, thread, process* and *two "threads", and two databases* answer the
two questions the earlier slides provoke: *are the parallel agents separate
containers?* (no — coroutines) and *is LangGraph's "thread" an OS thread?*
(no — a run id). Both tables are traced from the code and from probes, not from
the architecture diagram: the counts on the first come from running the real
`fan_out` shape with the LLM work stubbed, which prints
all five specialists on one pid, one thread and one event loop. Re-run that
probe rather than editing the numbers if `fan_out` or `AGENT_TOOLS` changes.

*The hooks around every tool call* is C2 only, and its claim that the permission
check is *load-bearing* was proved rather than argued: drive the real `run_specialist` with a stub LLM that
emits a `run_python` call as the `researcher`, once with the real `AGENT_TOOLS`
and once with `run_python` added to that set. The tool executes in the second
case and not the first, from the same dispatch table — because `team.py:124`
indexes the unfiltered `tools_by_name`, so the bind-time filter only controls
what the model is *told* about. Re-run that if `run_specialist` changes.

Slide 6's two right-hand columns are generated from the real table, and the
agent lists were checked against it rather than typed: invert `AGENT_TOOLS` in
Python and compare, after any change to the permission table.

Slide 11 is the densest table in the deck — 12 rows, every cell a single line at
11pt with 0.01" of slack. It fits because each cell was measured against its
column before being written, not trimmed afterwards. Its "Mechanism" column is
the one to keep accurate: there is **no middleware** in this project (grep for
`middleware`, `before_model`, `after_model` returns nothing), so if a row ever
starts claiming a framework hook, check it against the code first.

## One slide per fix

Slides sit on a single `FIX` layout (title placeholder, footer, slide number),
with one `pres.addSection()` per fix. Two helpers do the shared frame:

```js
pres.addSection({ title: "Your fix" });
const s3 = pres.addSlide({ masterName: "FIX", sectionTitle: "Your fix" });
s3.addText("Your fix", { placeholder: "title" });

leftCards(s3, [ /* Issue runs */ ], [ /* Fix Made runs */ ]);
rightHead(s3, "a one-line caption");
// then compose the right column: table, mono block, or both
```

`leftCards()` draws the Issue and Fix Made cards at fixed geometry;
`rightHead()` draws the "HOW IT WORKS" heading plus its caption. Only the right
column differs per slide — slide 1 is a table over a monospace block, slide 2 a
monospace payload over a table, slide 3 a payload over a three-column table
whose third column names the file each guard lives in.

A **fix** slide carries the cards too, but reads differently inside them: the
Issue card restates the gap in the use-case slide's own terms, and the Fix Made
card ends on what the fix does *not* claim. Slide 6's right column is the shape
to copy — the middleware itself in Courier New, the rule it applies in one
italic line, then a verdict table showing what each kind of sentence meets, and
a closing line naming the deliberate holes. Put the limit on the slide, not only
in the notes: a fix slide that reads as a clean win invites the question it
should have answered.

A results slide carries no cards: give it the title placeholder, then compose
the full width directly. Slide 4 reads top to bottom as intro line → the two
wordings being compared, side by side in 6.00" strips → the matrix → what it
means → the command transcript, last and thin. The gap column's header and
cells are filled `FBEEEC`, the same red as the paraphrase strip above them, so
the one column that gets through is tied to the text that does it.

Put the compared inputs *above* the matrix. The first draft of this slide led
with the command and showed neither sentence, and the "paraphrased" column was
unreadable as a result — a column of blanks with no visible cause.

**Slide 8 relearned the same lesson, so take it as a rule: a table whose
verdicts depend on a source has to show that source.** Its first draft listed
`"Azure growth drove …" — verbatim` against `"Azure drove cloud growth" —
reworded`, with the passage nowhere on the slide. Two elided near-identical
stubs, and the reader was asked to take "verbatim" on trust. The fix was to put
the real passage in a strip above the table and quote the rows in full against
it; the labels *verbatim* and *reworded* then became unnecessary, because the
reader can see it. Trimming the code block from eight lines to five paid for
the space.

Keep the reasoning in `slide.addNotes()` rather than on the slide: the slide
carries the claim, the notes carry the argument.

**A fix changes what earlier slides may claim.** Slide 4's red "nothing catches
this" caption became the blue Fix 1 line when the middleware landed, slide 3's
`Limit:` run now points forward to it, and *guardrails at each stage* lost its
"No middleware anywhere" caption — which had been true when it was written. The
test counts in slide 4's command transcript moved with it, as did the
teeth-check numbers in its notes. Fix 2 did the same to slide 2: its Fix Made
card said "14 tests, stdlib only, so the suite runs on any checkout", and the
Fix 2 classes are neither 14 nor stdlib. Grep the deck for the claim before
leaving a fix half-landed — counts and the words *only*, *never* and *nothing*
are where a deck goes stale first.

## Gotchas that cost time

- **Hex colors never take `#`, and never eight digits.** `"065A82"`. Both
  `"#065A82"` and baked-in alpha corrupt the file.
- **`pres.layout` must be set before any slide is added.** `LAYOUT_WIDE` is
  13.3" × 7.5"; coordinates past the edge are written, not clamped, so the shape
  just isn't on the slide.
- **Never share one options object across two `add*` calls** — pptxgenjs mutates
  them in place, converting values to EMU on first use.
- **Every `addText` without a `placeholder` needs `isTextBox: true`**, or screen
  readers announce the text as a graphic.
- **Text boxes have internal padding** — `margin: 0` whenever text must line up
  with a shape at the same x.
- **Bold small caps measure far wider than a plain-Arial proxy suggests.** Slide
  5's `THE ENFORCEMENT — PERMISSION_DENIED` came out 3.74" in a 3.46" cell and
  wrapped, which would have grown the row 0.19" into the caption below. The fit
  pass measures in regular Arial and under-reported it as fitting. Measure any
  bold or all-caps cell with **Arial Bold** before trusting the pass.
- **A multi-run table cell is `{ text: [runs] }`.** A bare array of run objects
  in a cell position renders as *nothing* — no error, no warning, just an empty
  column. *The hooks around every tool call* had invisible names on its first
  build for exactly this. Put
  `breakLine: true` on every run but the last; never a literal `\n`.
- **Nothing warns when two shapes land on top of each other.** A text-fit check
  compares text against its own box and cannot see this. The *hooks* table ran
  to 5.96" under a caption at 5.26", and *two "threads", and two databases*
  shipped one build with a 0.32" overlap. After any change to a `rowH` array, add up the rows and compare the
  table bottom with the next shape's `y` — the overlap pass at the end of the
  fit script does this for the whole deck.
- **A caption can be a claim with a shelf life.** *Guardrails at each stage*
  said "No middleware anywhere" in bold, which was accurate and is now wrong by one
  middleware. Captions that count things, or say *never* / *nothing* / *no*,
  are the first casualty of the next fix.
- **The title placeholder holds one line.** It is 12.2" x 0.75", and a 36pt line
  is 0.61" tall, so a title that wraps spills into the content below instead of
  shrinking. Measured in Cambria bold the budget is about 11.6" — the widest
  title already in the deck — and four titles have now been drafted past it and
  cut: *container, thread, process* (12.60"), *two "threads", and two databases*
  (13.98"), *the most dangerous tool, and its guard* (13.11") and *what two
  agents do that one does not* (12.80"). **The fit pass does not catch these**:
  it measures a title in regular Arial, which is narrow enough that the last
  one came back clean. Measure every new title in Arial Bold before rebuilding.

## Checking a rebuild

Text overflow is the defect that actually ships, and it is invisible in the
generator. The figures this deck was built against:

| Slide | Block | Text | Box | Slack |
|---|---|---|---|---|
| 1 | monospace levels (Courier New 10pt) | 5.92" × 2.35" | 6.30" × 2.94" | +0.38" / +0.59" |
| 1 | Issue prose (Calibri 14pt) | 1.63" | 1.80" | +0.17" |
| 1 | Fix Made prose (Calibri 14pt) | 1.99" | 2.20" | +0.21" |
| 2 | injected payload (Courier New 10pt) | 4.50" × 0.47" | 6.30" × 0.62" | +1.80" / +0.15" |
| 2 | Issue prose (Calibri 14pt) | 1.38" | 1.80" | +0.42" |
| 2 | Fix Made prose, with the Fix 2 pointer (Calibri 14pt) | 1.71" | 2.20" | +0.49" |
| 2 | five-links table (Calibri 11pt) | 2 lines/row, 0.37" | rowH 0.46" | +0.09" |
| 3 | Issue prose (Calibri 14pt) | 1.61" | 1.80" | +0.19" |
| 3 | Fix Made prose, with the Fix 1 pointer (Calibri 14pt) | 1.95" | 2.20" | +0.25" |
| 3 | injected article (Courier New 10pt) | 4.75" × 0.47" | 6.30" × 0.56" | +1.55" / +0.09" |
| 3 | caption (Calibri 12pt italic) | 0.22" | 0.26" | +0.04" |
| 3 | guards table, 3-line row | 0.67" incl. margins | rowH 0.78" | +0.11" |
| 3 | guards table, 2-line row | 0.49" incl. margins | rowH 0.58" | +0.09" |
| 3 | table bottom | 6.26" | 6.66" (card bottom) | +0.40" |
| 4 | intro line (Calibri 12pt) | 0.22" | 0.28" | +0.06" |
| 4 | compare strip, said plainly (Courier New 10pt) | 5.33" × 0.16" | 5.72" × 0.38" | +0.39" / +0.22" |
| 4 | compare strip, paraphrased (Courier New 10pt) | 4.50" × 0.31" | 5.72" × 0.38" | +1.22" / +0.07" |
| 4 | verdict matrix (Calibri 11pt) | 2.42", widest cell 1.44" | 2.46" → 4.88", col 1.96" | +0.52" on width |
| 4 | "other two layers" line (Calibri 12pt) | 0.22" | 0.28" | +0.06" |
| 4 | Fix 1 line (Calibri 12pt, bold lead run) | 0.41" | 0.68" | +0.27" |
| 4 | command transcript (Courier New 10pt) | 8.58" × 0.31" | 11.92" × 0.36" | +3.34" / +0.05" |
| 4 | Fix 1 line box bottom to run box top | 6.10" → 6.12" | — | +0.02" gap |
| 4 | last shape bottom | 6.62" | footer at 6.95" | +0.33" |
| 1–5 | `USE CASE n` chip (Arial Bold 12pt proxy, charSpacing) | 1.20" | 1.80" at x 10.95 | +0.60" |
| 6 | `FIX 1 · USE CASE 3` chip (same proxy) | 1.88" | 2.30" at x 10.45 | +0.42" |
| 1–8 | widest title (Arial/Times Bold 36pt proxy) | 9.54" | 9.60" to the Fix 3 chip | +0.06" |
| 5 | title (Cambria bold 36pt) | 5.98" wide, 0.61" tall | 12.2" × 0.75" | +6.22" / +0.14" |
| 5 | Issue prose (Calibri 14pt) | 1.54" | 1.80" | +0.26" |
| 5 | Fix Made prose (Calibri 14pt) | 2.05" | 2.20" | +0.15" |
| 5 | two-payloads table (Calibri 11pt) | 0.31"/row | rowH 0.32" | +0.01" |
| 5 | bold verdict cell (Arial Bold 11pt proxy) | 1.17" | col 1.52" | +0.35" |
| 5 | table bottom to caption top | 4.04" → 4.14" | — | +0.10" gap |
| 5 | poisoned run block (Courier New 10pt) | 1.86" | 2.04" | +0.18" |
| 5 | block bottom | 6.66" | 6.66" (card bottom) | flush |
| 6 | title (Cambria bold 36pt) | 7.39" wide, 0.61" tall | 12.2" × 0.75" | +4.81" / +0.14" |
| 6 | Issue prose (Calibri 14pt) | 1.38" | 1.80" | +0.42" |
| 6 | Fix Made prose (Calibri 14pt) | 1.95" | 2.20" | +0.25" |
| 6 | guardrail code (Courier New 10pt) | 5.17" × 1.19" | 6.30" × 1.22" | +1.13" / +0.03" |
| 6 | verdict table, 6 rows (Calibri 11pt) | 0.31"/row | rowH 0.32" | +0.01" |
| 6 | widest sentence cell (Calibri 11pt) | 2.68" | col 2.74" | +0.06" |
| 6 | the analyst row's sentence cell | 2.47" | col 2.74" | +0.27" |
| 6 | table bottom to caption top | 5.90" → 5.98" | — | +0.08" gap |
| 6 | closing caption (Calibri 12pt italic) | 0.65" | 0.68" | +0.03" |
| 6 | last shape bottom | 6.66" | 6.95" (footer top) | +0.29" |
| 7 | title (Cambria bold 36pt) | 7.72" wide, 0.61" tall | 12.2" × 0.75" | +4.48" / +0.14" |
| 7 | `FIX 2 · USE CASE 2` chip (Arial Bold 12pt proxy) | 2.00" | 2.30" at x 10.45 | +0.30" |
| 7 | Issue prose (Calibri 14pt) | 1.38" | 1.80" | +0.42" |
| 7 | Fix Made prose (Calibri 14pt) | 1.95" | 2.20" | +0.25" |
| 7 | signing code (Courier New 10pt) | 5.50" × 1.36" | 6.30" × 1.36" | +0.80" / flush |
| 7 | who-can-sign table (Calibri 11pt) | 0.31"/row | rowH 0.34" | +0.03" |
| 7 | table bottom to caption top | 5.48" → 5.60" | — | +0.12" gap |
| 7 | closing caption (Calibri 12pt italic) | 0.65" | 0.68" | +0.03" |
| 7 | last shape bottom | 6.28" | 6.66" (card bottom) | +0.38" |
| 8 | title (Cambria bold 36pt) | 8.85" wide, 0.61" tall | 12.2" × 0.75" | +3.35" / +0.14" |
| 8 | `FIX 3 · USE CASES 3+4` chip (Arial Bold 12pt proxy) | 2.36" | 2.60" at x 10.15 | +0.24" |
| 8 | Issue prose (Calibri 14pt) | 1.38" | 1.80" | +0.42" |
| 8 | Fix Made prose (Calibri 14pt) | 1.95" | 2.20" | +0.25" |
| 8 | passage strip (Courier New 10pt) | 4.92" × 0.34" | 6.30" × 0.40" | +1.38" / +0.06" |
| 8 | hand-off code, 5 lines (Courier New 10pt) | 5.50" × 0.85" | 6.30" × 0.89" | +0.80" / +0.04" |
| 8 | verdict table (Calibri 11pt) | 0.31"/row | rowH 0.34" | +0.03" |
| 8 | widest quote cell (Calibri 11pt) | 3.15" | col 3.48" | +0.33" |
| 8 | widest verdict cell (Calibri 11pt) | 1.68" | col 1.76" | +0.08" |
| 8 | table bottom to caption top | 5.83" → 5.95" | — | +0.12" gap |
| 8 | closing caption (Calibri 12pt italic) | 0.65" | 0.68" | +0.03" |
| 8 | last shape bottom | 6.63" | 6.66" (card bottom) | +0.03" |
| 9 | title (Cambria bold 36pt) | 10.47" wide | 12.2" | +1.73" |
| 9 | question banner (Calibri 13pt bold) | 1L 0.22" | 0.34" | +0.12" |
| 9 | panel A inflows (Calibri 11pt) | 10L 2.07" | 2.74" | +0.67" |
| 9 | arrow label inside the 1.02" panel gap | 0.61" | 0.72" | +0.11" |
| 10 | title (Cambria bold 36pt) | 7.60" wide | 12.2" | +4.60" |
| 10 | Rule of Two table (Calibri 11pt) | 0.31"/row | rowH 0.32-0.38" | +0.01" |
| 11 | title (Cambria bold 36pt) | 9.72" wide | 12.2" | +2.48" |
| 11 | intro line, 14pt lead run (Calibri) | 2L 0.47" | 0.50" | +0.03" |
| 11 | five gate rows (Calibri 11pt) | 0.19"/row | 0.46" | +0.27" |
| 12 | title (Cambria bold 36pt) | 10.91" wide | 12.2" | +1.29" |
| 12 | score code line (Courier New 10pt) | 7.35" wide | 11.86" | +4.51" |
| 13 | title (Cambria bold 36pt) | 11.26" wide | 12.2" | +0.94" |
| 13 | ring labels in the 0.46" bands (Calibri 11pt) | 0.19" | 0.26" | +0.07" |
| 14 | title (Cambria bold 36pt) | 10.10" wide | 12.2" | +2.10" |
| 14 | TOGETHER body (Calibri 11pt) | 5L 1.06" | 1.08" | +0.02" |
| 9-14 | example strip (Calibri 12pt) | 2L 0.43" | 0.66" | +0.23" |
| 15 | C0/C1/C2 definitions (Calibri 12pt) | 0.65" | 0.75" | +0.10" |
| 15 | verification matrix (Calibri 11pt) | 2.52" → 5.90" | caption at 6.20" | +0.30" gap |
| 15 | single-line table cell | 0.31" incl. margins | rowH 0.34" | +0.03" |
| 16 | intro line (Calibri 12pt) | 0.22" | 0.28" | +0.06" |
| 16 | tool cell (Courier New 10pt) | 1.17" | col 1.98" | +0.81" |
| 16 | "what it reads" cell (Calibri 11pt) | 4.25" | col 4.88" | +0.63" |
| 16 | "which agents" cell (Calibri 10pt) | 2.82" | col 2.98" | +0.16" |
| 16 | table bottom | 5.06" | footer at 6.95" | +1.89" |
| 16 | takeaway (Calibri 12pt italic) | 0.43" | 0.60" | +0.17" |
| 17 | title (Cambria bold 36pt) | 9.29" wide, 0.61" tall | 12.2" × 0.75" | +2.91" / +0.14" |
| 17 | intro line (Calibri 12pt) | 0.43" | 0.52" | +0.09" |
| 17 | runtime layers, 2-line row | 0.49" incl. margins | rowH 0.64" | +0.15" |
| 17 | table bottom | 4.94" | footer at 6.95" | +2.01" |
| 17 | caption (Calibri 12pt italic) | 0.65" | 0.80" | +0.15" |
| 18 | title (Cambria bold 36pt) | 11.08" wide, 0.61" tall | 12.2" × 0.75" | +1.12" / +0.14" |
| 18 | intro line (Calibri 12pt) | 0.43" | 0.52" | +0.09" |
| 18 | path cell, hard-broken (Courier New 10pt) | 2 lines, 0.46" | rowH 0.62" | +0.16" |
| 18 | table bottom | 5.58" | footer at 6.95" | +1.37" |
| 18 | caption (Calibri 12pt italic) | 0.65" | 0.80" | +0.15" |
| 18 | table bottom to caption top | 5.58" → 5.76" | — | +0.18" gap |
| 19 | title (Cambria bold 36pt) | 10.69" wide, 0.61" tall | 12.2" × 0.75" | +1.51" / +0.14" |
| 19 | intro line (Calibri 12pt) | 0.43" | 0.52" | +0.09" |
| 19 | hook table, 3-line row | 0.68" incl. margins | rowH 0.86" | +0.18" |
| 19 | hook table, 2-line row | 0.49" incl. margins | rowH 0.66" | +0.17" |
| 19 | table bottom to caption top | 5.32" → 5.52" | — | +0.20" gap |
| 19 | caption (Calibri 12pt italic) | 0.43" | 0.60" | +0.17" |
| 20 | title (Cambria bold 36pt) | 8.77" wide, 0.61" tall | 12.2" × 0.75" | +3.43" / +0.14" |
| 20 | intro line (Calibri 12pt) | 0.20" | 0.28" | +0.08" |
| 20 | guardrail table, 14 rows with Fix 1 and Fix 2 (Calibri 11pt) | 0.31"/row | rowH 0.32" | +0.01" |
| 20 | widest bold stage cell (Arial Bold 11pt proxy) | 1.23" | col 1.43" | +0.20" |
| 20 | widest "in this run" cell, the Fix 1 and Fix 2 rows (Calibri 11pt) | 4.80" | col 4.98" | +0.18" |
| 20 | table bottom to caption top | 6.16" → 6.26" | — | +0.10" gap |
| 20 | caption, cut to two lines to clear the footer | 0.41" | 0.46" | +0.05" |

The Courier New figures come from the system TTF via PIL. Calibri is not
installed here: rows for slides 1-4, 6 and 7 use an average advance calibrated
at 53 characters per 4.86" line at 14pt, and rows for slides 5 and 8-10 the
better method — measure in **Arial**, which is wider than Calibri at every size,
so a fit in Arial is a fit in Calibri. Titles are Cambria bold, also absent, so they are
measured as the worse of Arial Bold and Times New Roman Bold. Two cautions when
re-running such a script: it sees `"".join(run.text)`, which drops a `<a:br/>`
inside a cell, so hard-broken cells (the two database paths) must be counted by
hand; and the Arial upper bound inflates by roughly 8%, which is why slides 1-3
report single-line rows a hundredth or two over their `rowH` — that is the
substitute font, not a real overflow, and a table row grows rather than clips.
All of it is computed, not rendered —
LibreOffice and Poppler have not been available on any machine this deck was
built on, so **it has never been visually checked**. The thinnest blocks are
the single-line 12pt captions, at +0.04" to +0.06"; look at those first if you
get a renderer. A table is more forgiving than a text box — PowerPoint grows a
row that does not fit — but on slide 3 that growth would run into the card
bottom, which is why those rows carry +0.09" rather than +0.03".
The real check is:

```bash
soffice --headless --convert-to pdf ../presentation.pptx
pdftoppm -jpeg -r 150 presentation.pdf slide     # then look at slide-1.jpg
```

Adding prose to a card without widening it is the likely way to break this, and
body text should not go below 14pt to make room — cut words or grow the card.
