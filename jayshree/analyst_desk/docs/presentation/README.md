# Rebuilding `docs/presentation.pptx`

`build.js` is the source for the deck. The `.pptx` is a build artifact — change
the script, not the binary, or the next rebuild silently discards your edit.

```bash
cd docs/presentation
npm install pptxgenjs      # the only dependency; node_modules/ is gitignored
node build.js              # writes ../presentation.pptx
```

`applyTheme()` is inlined at the top of the script, so nothing outside npm is
needed. It runs after `writeFile()` because pptxgenjs sets the theme's fonts but
hard-codes Office's palette: until the deck's own colors are written into
`ppt/theme/theme1.xml`, every scheme color resolves to Office blue.

## Slides

1. **Securing secrets** — the `_SECRET_ENV` fix
2. **Forced approval injection** — the `tests/security/` chain
3. **Injected recommendation** — the four guards, and where each one lives
4. **Injected recommendation — the test run** — the verdict matrix the module prints
5. **Poisoned tool arguments** — injected text shapes the code the quant sends
   to a tool it legitimately holds. Neither payload carries a forbidden import,
   so the hook and the sandbox pass both: `check_note` recomputes the wrong
   *number*, and the wrong *wording* reaches the note gate untouched
6. **Appendix — verification by configuration** — what C0, C1 and C2 each verify
7. **Appendix — the eight tools, and what each reads** — the whole `AGENT_TOOLS`
   surface, which is what makes guard 1 on slide 3 true
8. **Appendix — container, thread, process** — what actually runs in parallel in
   one C2 run, traced from *"Compare Microsoft and Alphabet's FY2024 operating
   margins"*
9. **Appendix — two "threads", and two databases** — LangGraph's `thread_id`
   against an OS thread, and the run checkpointer against the long-term store
10. **Appendix — the hooks around every tool call** — the three pre checks and
    the one post record, and which of them can actually refuse
11. **Appendix — guardrails at each stage** — every guardrail the MSFT-vs-GOOGL
    run passes through, in pipeline order, with the mechanism behind each one.
    Mirrors `docs/security_summary.md` section 10

Slides 3 and 4 are one fix over two slides, in one section: the guards, then the
run that exercises them. Slide 4 and all four appendix slides reuse the `FIX`
layout as a title-only frame — `leftCards()` is simply not called, so the full
12.2" width is free. Reference slides go after the fixes, in their own `Appendix`
section, which is now slides 6-11.

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

Slides 7 and 8 answer the two questions the earlier slides provoke: *are the
parallel agents separate containers?* (no — coroutines) and *is LangGraph's
"thread" an OS thread?* (no — a run id). Both tables are traced from the code
and from probes, not from the architecture diagram: the counts on slide 7 come
from running the real `fan_out` shape with the LLM work stubbed, which prints
all five specialists on one pid, one thread and one event loop. Re-run that
probe rather than editing the numbers if `fan_out` or `AGENT_TOOLS` changes.

Slide 9 is C2 only, and its claim that the permission check is *load-bearing* was
proved rather than argued: drive the real `run_specialist` with a stub LLM that
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

A results slide carries no cards: give it the title placeholder, then compose
the full width directly. Slide 4 reads top to bottom as intro line → the two
wordings being compared, side by side in 6.00" strips → the matrix → what it
means → the command transcript, last and thin. The gap column's header and
cells are filled `FBEEEC`, the same red as the paraphrase strip above them, so
the one column that gets through is tied to the text that does it.

Put the compared inputs *above* the matrix. The first draft of this slide led
with the command and showed neither sentence, and the "paraphrased" column was
unreadable as a result — a column of blanks with no visible cause.

Keep the reasoning in `slide.addNotes()` rather than on the slide: the slide
carries the claim, the notes carry the argument.

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
  column. Slide 9's hook names were invisible on the first build for this. Put
  `breakLine: true` on every run but the last; never a literal `\n`.
- **Nothing warns when two shapes land on top of each other.** A text-fit check
  compares text against its own box and cannot see this. Slide 9's table ran to
  5.96" under a caption at 5.26", and slide 8 shipped one build with a 0.32"
  overlap. After any change to a `rowH` array, add up the rows and compare the
  table bottom with the next shape's `y` — the overlap pass at the end of the
  fit script does this for the whole deck.
- **The title placeholder holds one line.** It is 12.2" x 0.75", and a 36pt line
  is 0.61" tall, so a title that wraps spills into the content below instead of
  shrinking. Measured in Cambria bold the budget is about 11.6" — the widest
  title already in the deck — and both slide 7 and slide 8 were drafted past it
  (12.60" and 13.98") and had to be cut. Measure a new title before rebuilding.

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
| 2 | Fix Made prose (Calibri 14pt) | 1.99" | 2.20" | +0.21" |
| 2 | five-links table (Calibri 11pt) | 2 lines/row, 0.37" | rowH 0.46" | +0.09" |
| 3 | Issue prose (Calibri 14pt) | 1.61" | 1.80" | +0.19" |
| 3 | Fix Made prose (Calibri 14pt) | 1.96" | 2.20" | +0.24" |
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
| 4 | takeaway (Calibri 12pt italic) | 0.43" | 0.56" | +0.13" |
| 4 | command transcript (Courier New 10pt) | 8.58" × 0.31" | 11.92" × 0.36" | +3.34" / +0.05" |
| 4 | last shape bottom | 6.62" | footer at 6.95" | +0.33" |
| 5 | title (Cambria bold 36pt) | 5.98" wide, 0.61" tall | 12.2" × 0.75" | +6.22" / +0.14" |
| 5 | Issue prose (Calibri 14pt) | 1.54" | 1.80" | +0.26" |
| 5 | Fix Made prose (Calibri 14pt) | 2.05" | 2.20" | +0.15" |
| 5 | two-payloads table (Calibri 11pt) | 0.31"/row | rowH 0.32" | +0.01" |
| 5 | bold verdict cell (Arial Bold 11pt proxy) | 1.17" | col 1.52" | +0.35" |
| 5 | table bottom to caption top | 4.04" → 4.14" | — | +0.10" gap |
| 5 | poisoned run block (Courier New 10pt) | 1.86" | 2.04" | +0.18" |
| 5 | block bottom | 6.66" | 6.66" (card bottom) | flush |
| 6 | C0/C1/C2 definitions (Calibri 12pt) | 0.65" | 0.75" | +0.10" |
| 6 | verification matrix (Calibri 11pt) | 2.52" → 5.90" | caption at 6.20" | +0.30" gap |
| 6 | single-line table cell | 0.31" incl. margins | rowH 0.34" | +0.03" |
| 7 | intro line (Calibri 12pt) | 0.22" | 0.28" | +0.06" |
| 7 | tool cell (Courier New 10pt) | 1.17" | col 1.98" | +0.81" |
| 7 | "what it reads" cell (Calibri 11pt) | 4.25" | col 4.88" | +0.63" |
| 7 | "which agents" cell (Calibri 10pt) | 2.82" | col 2.98" | +0.16" |
| 7 | table bottom | 5.06" | footer at 6.95" | +1.89" |
| 7 | takeaway (Calibri 12pt italic) | 0.43" | 0.60" | +0.17" |
| 8 | title (Cambria bold 36pt) | 9.29" wide, 0.61" tall | 12.2" × 0.75" | +2.91" / +0.14" |
| 8 | intro line (Calibri 12pt) | 0.43" | 0.52" | +0.09" |
| 8 | runtime layers, 2-line row | 0.49" incl. margins | rowH 0.64" | +0.15" |
| 8 | table bottom | 4.94" | footer at 6.95" | +2.01" |
| 8 | caption (Calibri 12pt italic) | 0.65" | 0.80" | +0.15" |
| 9 | title (Cambria bold 36pt) | 11.08" wide, 0.61" tall | 12.2" × 0.75" | +1.12" / +0.14" |
| 9 | intro line (Calibri 12pt) | 0.43" | 0.52" | +0.09" |
| 9 | path cell, hard-broken (Courier New 10pt) | 2 lines, 0.46" | rowH 0.62" | +0.16" |
| 9 | table bottom | 5.58" | footer at 6.95" | +1.37" |
| 9 | caption (Calibri 12pt italic) | 0.65" | 0.80" | +0.15" |
| 9 | table bottom to caption top | 5.58" → 5.76" | — | +0.18" gap |
| 10 | title (Cambria bold 36pt) | 10.69" wide, 0.61" tall | 12.2" × 0.75" | +1.51" / +0.14" |
| 10 | intro line (Calibri 12pt) | 0.43" | 0.52" | +0.09" |
| 10 | hook table, 3-line row | 0.68" incl. margins | rowH 0.86" | +0.18" |
| 10 | hook table, 2-line row | 0.49" incl. margins | rowH 0.66" | +0.17" |
| 10 | table bottom to caption top | 5.32" → 5.52" | — | +0.20" gap |
| 10 | caption (Calibri 12pt italic) | 0.43" | 0.60" | +0.17" |
| 11 | title (Cambria bold 36pt) | 8.77" wide, 0.61" tall | 12.2" × 0.75" | +3.43" / +0.14" |
| 11 | intro line (Calibri 12pt) | 0.20" | 0.28" | +0.08" |
| 11 | guardrail table, 12 rows (Calibri 11pt) | 0.31"/row | rowH 0.32" | +0.01" |
| 11 | widest bold stage cell (Arial Bold 11pt proxy) | 1.23" | col 1.43" | +0.20" |
| 11 | widest "in this run" cell (Calibri 11pt) | 4.30" | col 4.98" | +0.68" |
| 11 | table bottom to caption top | 5.52" → 5.62" | — | +0.10" gap |
| 11 | caption (Calibri 12pt italic) | 0.65" | 0.76" | +0.11" |

The Courier New figures come from the system TTF via PIL. Calibri is not
installed here: rows for slides 1-4, 6 and 7 use an average advance calibrated
at 53 characters per 4.86" line at 14pt, and rows for slides 5 and 8-10 the
better method — measure in **Arial**, which is wider than Calibri at every size,
so a fit in Arial is a fit in Calibri. Titles are Cambria bold, also absent, so they are
measured as the worse of Arial Bold and Times New Roman Bold. Two cautions when
re-running such a script: it sees `"".join(run.text)`, which drops a `<a:br/>`
inside a cell, so hard-broken cells (slide 8's two paths) must be counted by
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
