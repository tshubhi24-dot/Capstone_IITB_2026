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
monospace payload over a table.

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

Those were computed, not rendered — LibreOffice and Poppler were not available
when the deck was first built, so **it has never been visually checked**. If you
have them, the real check is:

```bash
soffice --headless --convert-to pdf ../presentation.pptx
pdftoppm -jpeg -r 150 presentation.pdf slide     # then look at slide-1.jpg
```

Adding prose to a card without widening it is the likely way to break this, and
body text should not go below 14pt to make room — cut words or grow the card.
