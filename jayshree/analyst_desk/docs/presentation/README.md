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
with one `pres.addSection()` per fix. To add the next one:

```js
pres.addSection({ title: "Your fix" });
const s2 = pres.addSlide({ masterName: "FIX", sectionTitle: "Your fix" });
s2.addText("Your fix", { placeholder: "title" });
```

Then the same three regions: **Issue** and **Fix Made** cards on the left,
**How it works** on the right. Keep the reasoning in `slide.addNotes()` rather
than on the slide — the slide carries the claim, the notes carry the argument.

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

| Block | Text | Box | Slack |
|---|---|---|---|
| monospace levels (Courier New 10pt) | 5.92" × 2.35" | 6.30" × 2.94" | +0.38" / +0.59" |
| Issue prose (Calibri 14pt) | 1.63" | 1.80" | +0.17" |
| Fix Made prose (Calibri 14pt) | 1.99" | 2.20" | +0.21" |

Those were computed, not rendered — LibreOffice and Poppler were not available
when the deck was first built, so **it has never been visually checked**. If you
have them, the real check is:

```bash
soffice --headless --convert-to pdf ../presentation.pptx
pdftoppm -jpeg -r 150 presentation.pdf slide     # then look at slide-1.jpg
```

Adding prose to a card without widening it is the likely way to break this, and
body text should not go below 14pt to make room — cut words or grow the card.
