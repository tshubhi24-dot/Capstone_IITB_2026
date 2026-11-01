// Regenerates docs/presentation.pptx — one slide per security fix.
//
//     cd docs/presentation && npm install pptxgenjs && node build.js
//
// See README.md beside this file. pptxgenjs is the only dependency.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const OUT = path.join(__dirname, "..", "presentation.pptx");

// pptxgenjs sets the theme's two fonts but hard-codes Office's palette, so every
// scheme color resolves to Office blue until the deck's own colors are written
// into ppt/theme/theme1.xml. This does that, after writeFile().
const THEME_SLOTS = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3",
                     "accent4", "accent5", "accent6", "hlink", "folHlink"];

async function applyTheme(deckPath, theme) {
  // jszip ships with pptxgenjs; resolve it from there rather than the cwd.
  const JSZip = require(require.resolve("jszip", { paths: [require.resolve("pptxgenjs")] }));
  const part = "ppt/theme/theme1.xml";
  const zip = await JSZip.loadAsync(fs.readFileSync(deckPath));
  if (!zip.file(part)) throw new Error(`${deckPath} has no ${part}. Nothing was changed.`);

  const colors = theme.colors;
  for (const k of THEME_SLOTS) {
    if (!/^[0-9A-Fa-f]{6}$/.test(String(colors[k]))) {
      throw new Error(`theme.colors.${k} must be six hex digits with no "#". Nothing was changed.`);
    }
  }
  const name = String(theme.name).replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const scheme = `<a:clrScheme name="${name}">`
    + THEME_SLOTS.map((k) => `<a:${k}><a:srgbClr val="${colors[k].toUpperCase()}"/></a:${k}>`).join("")
    + "</a:clrScheme>";

  const xml = (await zip.file(part).async("string"))
    .replace(/<a:clrScheme\b[\s\S]*?<\/a:clrScheme>/, () => scheme)
    .replace(/(<a:(?:theme|fontScheme)\b[^>]*?\bname=")[^"]*"/g, (_, head) => `${head}${name}"`);
  if (!xml.includes(scheme)) throw new Error("no <a:clrScheme> to replace. Nothing was changed.");
  zip.file(part, xml);

  // A scheme color handed to a hex-only option is written as <a:srgbClr val="bg2"/>,
  // which is not a color and which pptxgenjs does not warn about. Stop instead.
  for (const partName of Object.keys(zip.files)) {
    if (!partName.endsWith(".xml")) continue;
    const bad = (await zip.file(partName).async("string"))
      .match(/<a:srgbClr val="((?![0-9A-Fa-f]{6}")[^"]*)"/);
    if (bad) throw new Error(`${partName} has <a:srgbClr val="${bad[1]}">, not six hex digits — a `
      + "scheme color was passed to an option that takes hex only. Nothing was changed.");
  }
  fs.writeFileSync(deckPath, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

const THEME = {
  name: "AnalystDesk Security",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "21295C", lt1: "FFFFFF",
    dk2: "065A82", lt2: "EDF3F7",
    accent1: "065A82", accent2: "1C7293", accent3: "21295C",
    accent4: "4A7B8C", accent5: "8FB3C4", accent6: "B85042",
    hlink: "1C7293", folHlink: "8FB3C4",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.3 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Pranoti Deshmukh";
pres.title = "AnalystDesk — MCP tool security fixes";
const C = pres.SchemeColor;

// One reusable layout: a fix per slide, title top-left, footer on the layout.
pres.defineSlideMaster({
  title: "FIX",
  background: { color: THEME.colors.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title",
        x: 0.55, y: 0.38, w: 12.2, h: 0.75, margin: 0,
        fontSize: 36, bold: true, color: C.text1, align: "left" }, text: "" } },
    { text: { text: "AnalystDesk · MCP tool security · branch pranoti-security",
        options: { x: 0.55, y: 6.95, w: 9.0, h: 0.3, margin: 0,
                   fontSize: 10, color: THEME.colors.accent5, align: "left" } } },
    { placeholder: { options: { name: "slideNumber", type: "sldNum",
        x: 12.5, y: 6.95, w: 0.4, h: 0.3, fontSize: 10, color: THEME.colors.accent5 } }, text: "" },
  ],
});

pres.addSection({ title: "Securing secrets" });
const s = pres.addSlide({ masterName: "FIX", sectionTitle: "Securing secrets" });
s.addText("Securing secrets", { placeholder: "title" });

// ── left column: Issue, then Fix Made ────────────────────────────────────────
const LEFT_X = 0.55, LEFT_W = 5.30;

s.addShape(pres.ShapeType.roundRect, {
  x: LEFT_X, y: 1.32, w: LEFT_W, h: 2.38, rectRadius: 0.06,
  fill: { color: "FBEEEC" }, line: { color: "FBEEEC" }, objectName: "issue card",
});
s.addText("ISSUE", {
  x: LEFT_X + 0.22, y: 1.46, w: LEFT_W - 0.44, h: 0.3, margin: 0, isTextBox: true,
  fontSize: 14, bold: true, charSpacing: 1.4, color: THEME.colors.accent6,
});
s.addText(
  [
    { text: "One env dict reused for all four stdio servers, so ", options: { breakLine: false } },
    { text: "APPROVAL_SECRET reached every one", options: { bold: true, breakLine: false } },
    { text: " — only research-portal verifies tokens.", options: { breakLine: true } },
    { text: "python-sandbox runs model-authored code: a leaked HMAC key mints approval tokens and publishes with no human sign-off.",
      options: { breakLine: false } },
  ],
  { x: LEFT_X + 0.22, y: 1.82, w: LEFT_W - 0.44, h: 1.80, margin: 0, isTextBox: true,
    fontSize: 14, color: C.text1, align: "left", lineSpacingMultiple: 1.08, paraSpaceAfter: 7 },
);

s.addShape(pres.ShapeType.roundRect, {
  x: LEFT_X, y: 3.90, w: LEFT_W, h: 2.76, rectRadius: 0.06,
  fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.lt2 }, objectName: "fix card",
});
s.addText("FIX MADE", {
  x: LEFT_X + 0.22, y: 4.04, w: LEFT_W - 0.44, h: 0.3, margin: 0, isTextBox: true,
  fontSize: 14, bold: true, charSpacing: 1.4, color: THEME.colors.accent1,
});
s.addText(
  [
    { text: "_SECRET_ENV names which servers need each secret; _env_for() applied per server.",
      options: { breakLine: true } },
    { text: "Pinned by 3 tests in tests/test_secrets.py; compose.yaml already scoped HTTP.",
      options: { breakLine: true } },
    { text: "Limit: withholds the variable, not the file — .env still sits in each server's cwd.",
      options: { italic: true, color: THEME.colors.accent4, breakLine: false } },
  ],
  { x: LEFT_X + 0.22, y: 4.40, w: LEFT_W - 0.44, h: 2.20, margin: 0, isTextBox: true,
    fontSize: 14, color: C.text1, align: "left", lineSpacingMultiple: 1.08, paraSpaceAfter: 7 },
);

// ── right column: How it works ───────────────────────────────────────────────
const R_X = 6.17, R_W = 6.58;

s.addText("HOW IT WORKS", {
  x: R_X, y: 1.46, w: R_W, h: 0.3, margin: 0, isTextBox: true,
  fontSize: 14, bold: true, charSpacing: 1.4, color: THEME.colors.accent2,
});

s.addText("Two separate axes of least privilege", {
  x: R_X, y: 1.8, w: R_W, h: 0.26, margin: 0, isTextBox: true,
  fontSize: 12, italic: true, color: THEME.colors.accent4,
});

s.addTable(
  [
    [
      { text: "Axis", options: { bold: true, color: THEME.colors.lt1, fill: { color: THEME.colors.accent3 } } },
      { text: "Mechanism", options: { bold: true, color: THEME.colors.lt1, fill: { color: THEME.colors.accent3 } } },
      { text: "Granularity", options: { bold: true, color: THEME.colors.lt1, fill: { color: THEME.colors.accent3 } } },
    ],
    ["Which agent may call which tool", "AGENT_TOOLS + hooks.pre", "per tool"],
    ["Which secret each server holds", "_SECRET_ENV + _env_for", "per server process"],
  ],
  { x: R_X, y: 2.12, w: R_W, colW: [2.60, 2.30, 1.68], rowH: [0.3, 0.3, 0.3],
    fontSize: 12, color: C.text1, fontFace: "Calibri", valign: "middle",
    border: { type: "solid", color: "D6E2EA", pt: 1 }, margin: 0.06,
    objectName: "axes table" },
);

s.addText("What each process level actually receives", {
  x: R_X, y: 3.22, w: R_W, h: 0.26, margin: 0, isTextBox: true,
  fontSize: 12, italic: true, color: THEME.colors.accent4,
});

const BLOCK = [
  "LEVEL 1 - PARENT (app.py / agent CLI), after load_dotenv('.env')",
  "      OPENROUTER_API_KEY     sk-or-REAL",
  "      APPROVAL_SECRET        hmac-REAL",
  "      SANDBOX_MODE           local",
  "      PORTAL_DB              /tmp/p.db",
  "",
  "LEVEL 2 - each MCP server subprocess (client._env_for)   <-- our change",
  "      server           OPENROUTER   APPROVAL   SANDBOX_MODE   PORTAL_DB",
  "      filings-kb       -            -          YES            YES",
  "      edgar            -            -          YES            YES",
  "      python-sandbox   -            -          YES            YES",
  "      research-portal  -            YES        YES            YES",
  "",
  "LEVEL 3 - code inside run_python (sandbox._local_env)",
  "      total vars: 0    keys: (none)",
].join("\n");

s.addShape(pres.ShapeType.roundRect, {
  x: R_X, y: 3.52, w: R_W, h: 3.14, rectRadius: 0.05,
  fill: { color: "F4F7F9" }, line: { color: "D6E2EA" }, objectName: "env levels block",
});
s.addText(BLOCK, {
  x: R_X + 0.14, y: 3.62, w: R_W - 0.28, h: 2.94, margin: 0, isTextBox: true,
  fontFace: "Courier New", fontSize: 10, color: C.text1,
  align: "left", valign: "top", lineSpacingMultiple: 1.0,
});

s.addNotes(
  "Issue: connections() reused one env dict for all four stdio MCP servers, so APPROVAL_SECRET " +
  "reached servers that never verify tokens. The sharp edge is python-sandbox, which executes " +
  "model-authored code; a leaked HMAC key lets an attacker mint an approval token and publish " +
  "without a human, breaking rule 3.\n\n" +
  "Fix: _SECRET_ENV declares which servers need each secret and _env_for(name) builds a per-server " +
  "environment. HMAC is symmetric, so APPROVAL_SECRET must still reach research-portal - that is the " +
  "component whose job is to refuse unapproved writes. compose.yaml already did this for HTTP.\n\n" +
  "Level 3 is pre-existing: sandbox._local_env() keeps only four Windows vars, so on macOS/Linux " +
  "model-authored code sees zero environment variables.\n\n" +
  "Known limit: the scoping withholds the environment variable, not the file. Servers start with " +
  "cwd=PROJECT_DIR, so .env is readable to them; no server reads it today (verified by grep) but " +
  "nothing enforces that. In docker mode the sandbox image copies only sandbox_runner.py and " +
  ".dockerignore excludes .env, so there the file genuinely is not present."
);

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote " + OUT);
})();
