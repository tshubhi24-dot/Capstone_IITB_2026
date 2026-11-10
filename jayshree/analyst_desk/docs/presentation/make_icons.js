// One-off: renders the threat-model section's icons to icons/*.png.
//
//     cd docs/presentation
//     npm install react react-dom react-icons sharp      # not needed to build the deck
//     node make_icons.js
//
// The PNGs are committed, so build.js reads them with fs.readFileSync and keeps
// pptxgenjs as its only dependency. Re-run this only to change an icon.
const fs = require("fs");
const path = require("path");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const sharp = require("sharp");
const Fi = require("react-icons/fi");

const COLOR = "#21295C";                 // THEME.colors.accent3, on a white circle
const OUT = path.join(__dirname, "icons");

const ICONS = {
  q1: "FiMap",            // trust-boundary map
  q2: "FiLayers",         // the Rule of Two properties stacking up
  q3: "FiUploadCloud",    // publish_note, the only write
  q4: "FiTrendingUp",     // the score
  q5: "FiClock",          // 3 am
  q6: "FiUsers",          // two agents together
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  for (const [name, icon] of Object.entries(ICONS)) {
    if (!Fi[icon]) throw new Error(`react-icons/fi has no ${icon}`);
    const svg = renderToStaticMarkup(
      React.createElement(Fi[icon], { color: COLOR, size: 256, strokeWidth: 2 }));
    const png = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
    fs.writeFileSync(path.join(OUT, `${name}.png`), png);
    console.log(`icons/${name}.png  ${icon}  ${png.length} bytes`);
  }
})();
