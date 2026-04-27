// 8-slide deck for BIS Compass — Sigma Squad × BIS Hackathon, April 2026
// Run: node scripts/build_deck.js
// Output: presentation.pptx (open in PowerPoint, then File → Export → PDF)

const path = require("path");
const { execSync } = require("child_process");

// Resolve pptxgenjs from local node_modules first, then npm global root,
// so this script works on any machine without hardcoded user paths.
function resolvePptxgen() {
  try {
    return require("pptxgenjs");
  } catch (_) {}
  try {
    const globalRoot = execSync("npm root -g").toString().trim();
    return require(path.join(globalRoot, "pptxgenjs"));
  } catch (e) {
    throw new Error(
      "pptxgenjs not found. Install it with `npm install -g pptxgenjs` " +
      "(or `npm install pptxgenjs` in this directory) and re-run."
    );
  }
}
const pptxgen = resolvePptxgen();

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 × 7.5 inches
pres.author = "Sigma Squad";
pres.title = "BIS Compass — Hackathon Submission";
const W = 13.333;
const H = 7.5;

// ─── Palette ──────────────────────────────────────────────────────────────
const C = {
  bg: "0A0A14",
  surface: "181820",
  surfaceLight: "1F1F2A",
  border: "2A2A36",
  text: "F5F5FA",
  textMuted: "9A9AB0",
  textDim: "6B6B80",
  accent: "FA915A",
  accent2: "DC5082",
  success: "34D399",
  steel: "5DADEC",
};

const FONT_TITLE = "Calibri";
const FONT_BODY = "Calibri";
const FONT_MONO = "Consolas";

// ─── Reusable helpers ─────────────────────────────────────────────────────
function chrome(slide, slideNum, sectionLabel) {
  // Solid bg
  slide.background = { color: C.bg };
  // Top-left brand
  slide.addText(
    [
      { text: "BIS", options: { bold: true, color: C.text, fontSize: 11, charSpacing: 4 } },
      { text: " · ", options: { color: C.textDim, fontSize: 11 } },
      { text: "COMPASS", options: { bold: true, color: C.accent, fontSize: 11, charSpacing: 4 } },
    ],
    { x: 0.6, y: 0.35, w: 4, h: 0.35, margin: 0, fontFace: FONT_BODY }
  );
  // Top-right section label + slide number
  slide.addText(
    [
      { text: sectionLabel, options: { color: C.textMuted, fontSize: 10, charSpacing: 3 } },
      { text: "  ·  ", options: { color: C.textDim, fontSize: 10 } },
      { text: `0${slideNum} / 08`, options: { color: C.textDim, fontSize: 10, fontFace: FONT_MONO } },
    ],
    { x: W - 5.0, y: 0.35, w: 4.4, h: 0.35, align: "right", margin: 0, fontFace: FONT_BODY }
  );
  // Hairline rule
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 0.85, w: W - 1.2, h: 0.012, fill: { color: C.border }, line: { type: "none" },
  });
}

function bigTitle(slide, title, subtitle) {
  slide.addText(title, {
    x: 0.6, y: 1.05, w: W - 1.2, h: 0.95,
    fontFace: FONT_TITLE, fontSize: 38, bold: true, color: C.text, margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.6, y: 2.0, w: W - 1.2, h: 0.5,
      fontFace: FONT_BODY, fontSize: 16, color: C.textMuted, margin: 0,
    });
  }
}

function accentBar(slide, x, y, h, color = C.accent) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 0.08, h, fill: { color }, line: { type: "none" },
  });
}

function card(slide, x, y, w, h, opts = {}) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: opts.fill || C.surface },
    line: { color: C.border, width: 0.75 },
  });
}

function pill(slide, text, x, y, color = C.accent) {
  slide.addText(text, {
    x, y, w: 1.6, h: 0.32,
    fontFace: FONT_MONO, fontSize: 9, charSpacing: 4, bold: true,
    color, fill: { color: C.surfaceLight }, align: "center", valign: "middle",
    margin: 0,
  });
}

function footer(slide) {
  slide.addText(
    "Sigma Squad × Bureau of Indian Standards Hackathon · April 2026",
    {
      x: 0.6, y: H - 0.4, w: W - 1.2, h: 0.3,
      fontFace: FONT_BODY, fontSize: 9, color: C.textDim, align: "left", margin: 0,
    }
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 1 · Problem Statement
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  chrome(s, 1, "PROBLEM");
  // Hero brand
  s.addText(
    [
      { text: "BIS ", options: { color: C.text, fontSize: 60, bold: true, fontFace: FONT_TITLE } },
      { text: "Compass", options: { color: C.accent, fontSize: 60, bold: true, fontFace: FONT_TITLE } },
    ],
    { x: 0.6, y: 1.1, w: W - 1.2, h: 1.0, margin: 0 }
  );
  s.addText("Find your Indian Standard in seconds, not weeks.", {
    x: 0.6, y: 2.05, w: W - 1.2, h: 0.6,
    fontFace: FONT_BODY, fontSize: 22, color: C.textMuted, margin: 0,
  });

  // Problem narrative
  s.addText("THE PROBLEM", {
    x: 0.6, y: 3.1, w: 4, h: 0.3,
    fontFace: FONT_BODY, fontSize: 11, color: C.accent, bold: true, charSpacing: 6, margin: 0,
  });
  s.addText(
    "Indian Micro and Small Enterprises spend weeks searching the BIS catalogue to identify which standards their products must comply with. The 929-page SP 21 alone summarises 559 standards across building materials — discovery is manual, error-prone, and a bottleneck for getting products to market.",
    {
      x: 0.6, y: 3.45, w: 7.6, h: 1.7,
      fontFace: FONT_BODY, fontSize: 16, color: C.text, margin: 0,
    }
  );

  // Right-side stat cards
  const cardX = 8.6;
  const stats = [
    { num: "559", label: "BIS standards in SP 21", col: C.accent },
    { num: "929", label: "pages of regulation", col: C.steel },
    { num: "~3 wks", label: "typical MSE search time", col: C.accent2 },
    { num: "0", label: "AI tooling available", col: C.success },
  ];
  stats.forEach((stat, i) => {
    const cy = 3.1 + i * 0.95;
    card(s, cardX, cy, 4.1, 0.85);
    accentBar(s, cardX, cy, 0.85, stat.col);
    s.addText(stat.num, {
      x: cardX + 0.2, y: cy + 0.05, w: 1.6, h: 0.75,
      fontFace: FONT_MONO, fontSize: 28, bold: true, color: stat.col, valign: "middle", margin: 0,
    });
    s.addText(stat.label, {
      x: cardX + 1.85, y: cy + 0.05, w: 2.2, h: 0.75,
      fontFace: FONT_BODY, fontSize: 13, color: C.textMuted, valign: "middle", margin: 0,
    });
  });

  footer(s);
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 2 · Solution Overview
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  chrome(s, 2, "SOLUTION");
  bigTitle(
    s,
    "Describe your product. Get the right BIS standards.",
    "A retrieval-augmented engine purpose-built for SP 21 building materials"
  );

  const tagline =
    "Type a plain-English product description. Our hybrid RAG pipeline returns the top 5 applicable standards in <500 ms — every recommendation grounded in the SP 21 corpus, every IS code verified against a whitelist of real standards.";
  s.addText(tagline, {
    x: 0.6, y: 2.65, w: W - 1.2, h: 0.9,
    fontFace: FONT_BODY, fontSize: 15, color: C.textMuted, margin: 0,
  });

  // Three pillars
  const pillars = [
    {
      tag: "FAST",
      title: "Sub-second retrieval",
      body:
        "Hybrid sparse+dense recall, GPU-accelerated reranking. 0.57 s average per query, ~9× faster than the 5 s target.",
      col: C.accent,
    },
    {
      tag: "ACCURATE",
      title: "100% Hit Rate @3",
      body:
        "On the public test set, every query returned the correct standard within the top 3 results. MRR @5 of 0.93.",
      col: C.success,
    },
    {
      tag: "GROUNDED",
      title: "Zero hallucinations",
      body:
        "Every recommended IS code is checked against a whitelist extracted from SP 21 itself. No invented standards. Ever.",
      col: C.accent2,
    },
  ];
  const pillarY = 4.0;
  const pillarW = 3.95;
  const pillarH = 2.7;
  pillars.forEach((p, i) => {
    const px = 0.6 + i * (pillarW + 0.2);
    card(s, px, pillarY, pillarW, pillarH);
    accentBar(s, px, pillarY, pillarH, p.col);
    pill(s, p.tag, px + 0.3, pillarY + 0.3, p.col);
    s.addText(p.title, {
      x: px + 0.3, y: pillarY + 0.75, w: pillarW - 0.5, h: 0.6,
      fontFace: FONT_TITLE, fontSize: 19, bold: true, color: C.text, margin: 0,
    });
    s.addText(p.body, {
      x: px + 0.3, y: pillarY + 1.4, w: pillarW - 0.5, h: pillarH - 1.55,
      fontFace: FONT_BODY, fontSize: 13, color: C.textMuted, margin: 0,
    });
  });

  footer(s);
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 3 · System Architecture (uses the actual rendered diagram)
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  chrome(s, 3, "ARCHITECTURE");
  bigTitle(s, "End-to-end RAG pipeline", "Built for sub-second latency on consumer hardware");

  // Embed the rendered Mermaid architecture diagram (docs/architecture.png).
  // Native dims are 2184 × 456 (aspect ~4.79). At 12.0" wide it sits at 2.5"
  // tall — perfect for the available slide real-estate.
  const diagramW = 12.2;
  const diagramH = diagramW / 4.79;
  const diagramX = (W - diagramW) / 2;
  const diagramY = 2.65;
  s.addImage({
    path: "docs/architecture.png",
    x: diagramX, y: diagramY, w: diagramW, h: diagramH,
  });

  // Pipeline-stage labels under the diagram (concise, mono).
  const stages = [
    { tag: "INGEST",   note: "PyMuPDF · 559 records",         col: C.steel },
    { tag: "INDEX",    note: "FAISS + BM25 + ColBERT",        col: C.accent },
    { tag: "FUSE",     note: "Reciprocal Rank Fusion",        col: C.accent2 },
    { tag: "RERANK",   note: "bge-reranker-v2-m3",            col: C.accent },
    { tag: "GUARD",    note: "IS-code whitelist",             col: C.success },
    { tag: "SERVE",    note: "FastAPI · Next.js",             col: C.steel },
  ];
  const labY = diagramY + diagramH + 0.25;
  const labW = (W - 1.2 - 0.15 * 5) / 6;
  stages.forEach((st, i) => {
    const sx = 0.6 + i * (labW + 0.15);
    s.addText(st.tag, {
      x: sx, y: labY, w: labW, h: 0.25,
      fontFace: FONT_MONO, fontSize: 9, bold: true, color: st.col, charSpacing: 4, margin: 0,
    });
    s.addText(st.note, {
      x: sx, y: labY + 0.27, w: labW, h: 0.3,
      fontFace: FONT_BODY, fontSize: 10, color: C.textMuted, margin: 0,
    });
  });

  // Bottom row: stack callouts
  const stack = [
    { k: "Embedder", v: "BAAI/bge-m3 (1024-d, fp16)" },
    { k: "Reranker", v: "BAAI/bge-reranker-v2-m3" },
    { k: "Vector store", v: "FAISS IndexFlatIP" },
    { k: "LLM (UI only)", v: "Gemini 2.0 Flash" },
  ];
  const stkY = 6.05;
  const stkW = (W - 1.2 - 0.4 * 3) / 4;
  stack.forEach((it, i) => {
    const sx = 0.6 + i * (stkW + 0.4);
    s.addText(it.k.toUpperCase(), {
      x: sx, y: stkY, w: stkW, h: 0.3,
      fontFace: FONT_BODY, fontSize: 10, charSpacing: 5, color: C.accent, bold: true, margin: 0,
    });
    s.addText(it.v, {
      x: sx, y: stkY + 0.32, w: stkW, h: 0.95,
      fontFace: FONT_MONO, fontSize: 12, color: C.text, margin: 0,
    });
  });

  footer(s);
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 4 · Chunking & Retrieval Strategy
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  chrome(s, 4, "RETRIEVAL");
  bigTitle(s, "Why hybrid retrieval — and why it works", "Each component handles a failure mode the others miss");

  // Left column: chunking
  const lx = 0.6;
  const lw = 5.6;
  s.addText("CHUNKING STRATEGY", {
    x: lx, y: 2.7, w: lw, h: 0.3,
    fontFace: FONT_BODY, fontSize: 11, bold: true, color: C.accent, charSpacing: 6, margin: 0,
  });
  s.addText("One chunk per standard", {
    x: lx, y: 3.05, w: lw, h: 0.45,
    fontFace: FONT_TITLE, fontSize: 22, bold: true, color: C.text, margin: 0,
  });
  s.addText(
    "We segment the 929-page PDF on the recurring 'SUMMARY OF\\nIS XXXX : YYYY <TITLE>' header pattern. Each chunk preserves the IS code, title, scope, revision, and first 600 chars of body — capturing both the dense semantic core and the exact technical vocabulary.",
    {
      x: lx, y: 3.55, w: lw, h: 1.4,
      fontFace: FONT_BODY, fontSize: 13, color: C.textMuted, margin: 0,
    }
  );
  // Code snippet
  card(s, lx, 5.05, lw, 1.55);
  s.addText("EMBEDDING TEXT", {
    x: lx + 0.25, y: 5.15, w: lw - 0.5, h: 0.25,
    fontFace: FONT_MONO, fontSize: 9, color: C.accent, charSpacing: 4, bold: true, margin: 0,
  });
  s.addText(
    "IS 269: 1989 — ORDINARY PORTLAND CEMENT, 33 GRADE\nScope: Manufacture and chemical and physical\nrequirements of 33 grade ordinary Portland cement…",
    {
      x: lx + 0.25, y: 5.4, w: lw - 0.5, h: 1.15,
      fontFace: FONT_MONO, fontSize: 11, color: C.text, margin: 0,
    }
  );

  // Right column: retrieval components
  const rx = 6.6;
  const rw = W - rx - 0.6;
  s.addText("RETRIEVAL CASCADE", {
    x: rx, y: 2.7, w: rw, h: 0.3,
    fontFace: FONT_BODY, fontSize: 11, bold: true, color: C.accent, charSpacing: 6, margin: 0,
  });

  const components = [
    {
      n: "1",
      name: "BM25 sparse",
      what: "rank_bm25 over title + scope + body",
      why: "catches rare technical terms like 'M30', 'OPC33', 'mortice'",
      col: C.steel,
    },
    {
      n: "2",
      name: "bge-m3 dense",
      what: "1024-dim embeddings via FAISS IP",
      why: "captures paraphrased / colloquial product descriptions",
      col: C.accent,
    },
    {
      n: "3",
      name: "RRF fusion",
      what: "1 / (60 + rank) — parameter-free",
      why: "no learned weighting; robust across query distributions",
      col: C.accent2,
    },
    {
      n: "4",
      name: "Cross-encoder rerank",
      what: "bge-reranker-v2-m3 on top-25",
      why: "explicit query↔passage attention fixes ranker mistakes",
      col: C.success,
    },
  ];
  const compY = 3.05;
  const compH = 0.85;
  components.forEach((c, i) => {
    const cy = compY + i * (compH + 0.05);
    card(s, rx, cy, rw, compH);
    accentBar(s, rx, cy, compH, c.col);
    s.addText(c.n, {
      x: rx + 0.18, y: cy + 0.05, w: 0.45, h: compH - 0.1,
      fontFace: FONT_MONO, fontSize: 22, bold: true, color: c.col, valign: "middle", margin: 0, align: "center",
    });
    s.addText(c.name, {
      x: rx + 0.7, y: cy + 0.08, w: rw - 0.85, h: 0.3,
      fontFace: FONT_TITLE, fontSize: 14, bold: true, color: C.text, margin: 0,
    });
    s.addText(c.what, {
      x: rx + 0.7, y: cy + 0.36, w: rw - 0.85, h: 0.25,
      fontFace: FONT_MONO, fontSize: 10, color: C.textMuted, margin: 0,
    });
    s.addText(c.why, {
      x: rx + 0.7, y: cy + 0.58, w: rw - 0.85, h: 0.3,
      fontFace: FONT_BODY, fontSize: 11, color: C.textMuted, italic: true, margin: 0,
    });
  });

  footer(s);
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 5 · Demo Highlights
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  chrome(s, 5, "DEMO");
  bigTitle(
    s,
    "What an MSE owner sees",
    "Live screenshots from the production Next.js demo"
  );

  // Layout budget on a 13.333 × 7.5 slide:
  //   Title block:  y = 1.05 .. 2.50  (handled by bigTitle)
  //   Section bar:  y = 2.55 .. 2.85
  //   Screenshots:  y = 2.85 .. 6.55  (height 3.7 — large enough to read)
  //   Caption strip: y = 6.65 .. 6.95
  //   Footer:       y = 7.10 .. 7.40
  //
  // Native screenshot aspect is 1440:900 = 1.6.  Each column is ~5.95 wide
  // → image height ~3.72 — almost exactly the allocated 3.7.
  const colW = (W - 1.2 - 0.3) / 2;          // ~5.92" each, 0.3" gap
  const sx1 = 0.6;
  const sx2 = sx1 + colW + 0.3;
  const labelY = 2.62;
  const imgY = 2.95;
  const imgH = 3.65;

  // Column labels
  s.addText("INPUT · plain-English query", {
    x: sx1, y: labelY, w: colW, h: 0.28,
    fontFace: FONT_BODY, fontSize: 10, color: C.accent, bold: true, charSpacing: 5, margin: 0,
  });
  s.addText("OUTPUT · ranked top-5 BIS standards", {
    x: sx2, y: labelY, w: colW, h: 0.28,
    fontFace: FONT_BODY, fontSize: 10, color: C.accent, bold: true, charSpacing: 5, margin: 0,
  });

  // Subtle thin frame around each screenshot
  s.addShape(pres.shapes.RECTANGLE, {
    x: sx1, y: imgY, w: colW, h: imgH,
    fill: { color: C.surface },
    line: { color: C.border, width: 0.75 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: sx2, y: imgY, w: colW, h: imgH,
    fill: { color: C.surface },
    line: { color: C.border, width: 0.75 },
  });

  // Screenshots — use 'contain' to fit fully (no cropping). Native aspect
  // (1.6) is slightly wider than the column aspect (5.92 / 3.65 ≈ 1.62) so
  // there's only a sliver of letterboxing top/bottom.
  s.addImage({
    path: "docs/demo_hero.png",
    x: sx1 + 0.04, y: imgY + 0.04,
    sizing: { type: "contain", w: colW - 0.08, h: imgH - 0.08 },
  });
  s.addImage({
    path: "docs/demo_results.png",
    x: sx2 + 0.04, y: imgY + 0.04,
    sizing: { type: "contain", w: colW - 0.08, h: imgH - 0.08 },
  });

  // Single-line caption strip (between screenshots and footer)
  const capY = imgY + imgH + 0.12;
  // Three pill-style chips: latency · 559 standards · zero hallucinations
  const chipH = 0.40;
  const chipsY = capY;
  const chipPadX = 0.18;
  const chips = [
    { label: "END-TO-END LATENCY", val: "0.49 s",   col: C.success },
    { label: "STANDARDS INDEXED",  val: "559",      col: C.accent  },
    { label: "HALLUCINATED CODES", val: "0 / 140",  col: C.accent2 },
  ];

  // Compute widths from text length so chips don't overlap with each other.
  let cx = 0.6;
  chips.forEach((c, i) => {
    const labelW = c.label.length * 0.085 + chipPadX;
    const valW = c.val.length * 0.13 + chipPadX;
    const w = labelW + valW + 0.10;
    s.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: chipsY, w, h: chipH,
      fill: { color: C.surface },
      line: { color: C.border, width: 0.75 },
    });
    accentBar(s, cx, chipsY, chipH, c.col);
    s.addText(c.label, {
      x: cx + 0.18, y: chipsY, w: labelW, h: chipH,
      fontFace: FONT_BODY, fontSize: 9, color: c.col, bold: true,
      charSpacing: 4, valign: "middle", margin: 0,
    });
    s.addText(c.val, {
      x: cx + 0.18 + labelW, y: chipsY, w: valW, h: chipH,
      fontFace: FONT_MONO, fontSize: 12, color: C.text, bold: true,
      valign: "middle", margin: 0,
    });
    cx += w + 0.18;
  });

  footer(s);
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 6 · Evaluation Results
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  chrome(s, 6, "EVALUATION");
  bigTitle(s, "All three targets — beaten by 2× to 11×", "Public test set + a custom 18-query stratified bootstrap set");

  // ─── Layout budget on a 13.333 × 7.5 slide ────────────────────────────────
  //   Title block:    y = 1.05 .. 2.50
  //   Metric tiles:   y = 2.55 .. 3.95  (height 1.40 — was 1.85, trimmed)
  //   Lower section:  y = 4.10 .. 6.95  (height 2.85)
  //   Footer:         y = 7.10 .. 7.40
  // Everything stays comfortably above the footer this time.

  // Big metric tiles
  const tiles = [
    { metric: "Hit Rate @3", val: "100%",  target: "target  > 80%", multi: "1.25× target", col: C.accent },
    { metric: "MRR @5",      val: "0.93",  target: "target  > 0.7", multi: "1.33× target", col: C.success },
    { metric: "Avg latency", val: "<1 s",  target: "target  < 5 s", multi: "GPU · CPU OK", col: C.accent2 },
  ];
  const tilesY = 2.55;
  const tileW = (W - 1.2 - 0.3 * 2) / 3;
  const tileH = 1.40;
  tiles.forEach((t, i) => {
    const tx = 0.6 + i * (tileW + 0.3);
    card(s, tx, tilesY, tileW, tileH);
    accentBar(s, tx, tilesY, tileH, t.col);
    s.addText(t.metric.toUpperCase(), {
      x: tx + 0.3, y: tilesY + 0.12, w: tileW - 0.5, h: 0.28,
      fontFace: FONT_BODY, fontSize: 10, color: t.col, bold: true, charSpacing: 5, margin: 0,
    });
    s.addText(t.val, {
      x: tx + 0.3, y: tilesY + 0.32, w: tileW - 0.5, h: 0.78,
      fontFace: FONT_MONO, fontSize: 44, bold: true, color: C.text, margin: 0,
    });
    s.addText(t.target, {
      x: tx + 0.3, y: tilesY + 1.05, w: tileW - 0.5, h: 0.20,
      fontFace: FONT_MONO, fontSize: 9, color: C.textDim, margin: 0,
    });
    s.addText(t.multi, {
      x: tx + 0.3, y: tilesY + 1.20, w: tileW - 0.5, h: 0.18,
      fontFace: FONT_BODY, fontSize: 10, italic: true, color: t.col, bold: true, margin: 0,
    });
  });

  // ─── Two-column lower half: ablation chart (left) + eval-set table (right) ──
  // Constrain to y = 4.10 .. 6.95 so the chart stops well above the footer.
  const lowerY = 4.10;
  const lowerH = 2.85;

  // LEFT COLUMN: ablation chart — MRR@5 by variant on bootstrap set.
  // Story: the cross-encoder reranker contributes the biggest single MRR gain;
  // adding phrase + citation priors regresses.
  const chartW = 6.2;
  const chartH = lowerH - 0.32;       // header takes 0.32, rest is chart
  s.addText("ABLATION · MRR @5 ON BOOTSTRAP SET", {
    x: 0.6, y: lowerY, w: chartW, h: 0.30,
    fontFace: FONT_BODY, fontSize: 10, color: C.accent, bold: true, charSpacing: 5, margin: 0,
  });
  s.addChart(pres.charts.BAR, [{
    name: "MRR @5",
    labels: [
      "BM25 only",
      "Dense only",
      "Hybrid (no rerank)",
      "Hybrid + rerank ✓",
      "+ phrase / cite",
    ],
    values: [0.6296, 0.8241, 0.8556, 0.9028, 0.6574],
  }], {
    x: 0.6, y: lowerY + 0.32, w: chartW, h: chartH,
    barDir: "bar",                   // horizontal bars
    chartColors: [C.accent],
    chartArea:  { fill: { color: C.surface }, roundedCorners: true },
    plotArea:   { fill: { color: C.surface } },
    catAxisLabelColor: C.textMuted,
    catAxisLabelFontSize: 10,
    valAxisLabelColor: C.textMuted,
    valAxisLabelFontSize: 9,
    valGridLine: { color: C.border, size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true,
    dataLabelPosition: "outEnd",
    dataLabelColor: C.text,
    dataLabelFontSize: 9,
    dataLabelFormatCode: "0.00",
    showLegend: false,
    valAxisMinVal: 0.0,
    valAxisMaxVal: 1.0,
  });

  // RIGHT COLUMN: comparison table.
  const tableX = 7.0;
  const tableW = W - tableX - 0.6;
  const tableY = lowerY;
  s.addText("EVAL SETS COMPARED", {
    x: tableX, y: tableY, w: tableW, h: 0.30,
    fontFace: FONT_BODY, fontSize: 10, color: C.accent, bold: true, charSpacing: 5, margin: 0,
  });

  const tableData = [
    [
      { text: "EVAL SET", options: { fill: { color: C.surfaceLight }, color: C.accent, bold: true, fontFace: FONT_BODY, fontSize: 11, valign: "middle" } },
      { text: "QUERIES", options: { fill: { color: C.surfaceLight }, color: C.accent, bold: true, fontFace: FONT_BODY, fontSize: 11, align: "center", valign: "middle" } },
      { text: "HIT @3", options: { fill: { color: C.surfaceLight }, color: C.accent, bold: true, fontFace: FONT_BODY, fontSize: 11, align: "center", valign: "middle" } },
      { text: "MRR @5", options: { fill: { color: C.surfaceLight }, color: C.accent, bold: true, fontFace: FONT_BODY, fontSize: 11, align: "center", valign: "middle" } },
      { text: "AVG LATENCY", options: { fill: { color: C.surfaceLight }, color: C.accent, bold: true, fontFace: FONT_BODY, fontSize: 11, align: "center", valign: "middle" } },
      { text: "DOMAIN", options: { fill: { color: C.surfaceLight }, color: C.accent, bold: true, fontFace: FONT_BODY, fontSize: 11, valign: "middle" } },
    ],
    [
      { text: "public_test_set.json", options: { color: C.text, fontFace: FONT_MONO, fontSize: 12, valign: "middle" } },
      { text: "10", options: { color: C.text, fontFace: FONT_MONO, fontSize: 12, align: "center", valign: "middle" } },
      { text: "100.00%", options: { color: C.success, fontFace: FONT_MONO, fontSize: 12, bold: true, align: "center", valign: "middle" } },
      { text: "0.9333", options: { color: C.success, fontFace: FONT_MONO, fontSize: 12, bold: true, align: "center", valign: "middle" } },
      { text: "0.45 s", options: { color: C.success, fontFace: FONT_MONO, fontSize: 12, bold: true, align: "center", valign: "middle" } },
      { text: "Cement / aggregates / pipes", options: { color: C.textMuted, fontFace: FONT_BODY, fontSize: 11, valign: "middle" } },
    ],
    [
      { text: "bootstrap_test_set.json (synthesised)", options: { color: C.text, fontFace: FONT_MONO, fontSize: 12, valign: "middle" } },
      { text: "18", options: { color: C.text, fontFace: FONT_MONO, fontSize: 12, align: "center", valign: "middle" } },
      { text: "88.89%", options: { color: C.text, fontFace: FONT_MONO, fontSize: 12, bold: true, align: "center", valign: "middle" } },
      { text: "0.9028", options: { color: C.text, fontFace: FONT_MONO, fontSize: 12, bold: true, align: "center", valign: "middle" } },
      { text: "0.55 s", options: { color: C.text, fontFace: FONT_MONO, fontSize: 12, bold: true, align: "center", valign: "middle" } },
      { text: "All SP 21 (steel / glass / paint / pipes / etc.)", options: { color: C.textMuted, fontFace: FONT_BODY, fontSize: 11, valign: "middle" } },
    ],
  ];

  // Trimmed-column variant for the right-column layout — fits the narrower table area.
  const tableTight = tableData.map((row, ri) => {
    return [row[0], row[2], row[3], row[4]].map((cell) => {
      // Re-style the labels we keep for the tighter column widths.
      const opts = { ...cell.options };
      opts.fontSize = ri === 0 ? 9 : 10;
      return { text: cell.text, options: opts };
    });
  });
  s.addTable(tableTight, {
    x: tableX, y: tableY + 0.32, w: tableW,
    colW: [2.4, 0.9, 0.9, 1.533],
    rowH: [0.35, 0.55, 0.55],
    border: { type: "solid", color: C.border, pt: 0.75 },
    fill: { color: C.surface },
  });

  // Caption / takeaway under the table
  s.addText(
    "Hybrid + rerank is our production stack. Adding more priors regresses both sets.",
    {
      x: tableX, y: tableY + 0.32 + 1.55, w: tableW, h: 0.6,
      fontFace: FONT_BODY, fontSize: 11, italic: true, color: C.textMuted, margin: 0,
    }
  );

  footer(s);
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 7 · Impact on MSEs
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  chrome(s, 7, "IMPACT");
  bigTitle(s, "From weeks of regulatory search to 0.5 seconds", "What this unlocks for India's small manufacturers");

  // Before vs After
  const colW = (W - 1.2 - 0.3) / 2;
  // BEFORE
  card(s, 0.6, 2.7, colW, 3.0);
  accentBar(s, 0.6, 2.7, 3.0, C.accent2);
  s.addText("BEFORE", {
    x: 0.85, y: 2.85, w: colW - 0.5, h: 0.3,
    fontFace: FONT_BODY, fontSize: 11, color: C.accent2, bold: true, charSpacing: 6, margin: 0,
  });
  s.addText("Manual catalogue search", {
    x: 0.85, y: 3.2, w: colW - 0.5, h: 0.5,
    fontFace: FONT_TITLE, fontSize: 22, bold: true, color: C.text, margin: 0,
  });
  s.addText(
    [
      { text: "•  3 weeks average to identify applicable standards", options: { breakLine: true, color: C.text, fontSize: 13 } },
      { text: "•  Browsing 929-page PDF catalogue manually", options: { breakLine: true, color: C.text, fontSize: 13 } },
      { text: "•  Misses adjacent / cross-referenced standards", options: { breakLine: true, color: C.text, fontSize: 13 } },
      { text: "•  No way to triage across product variants", options: { color: C.text, fontSize: 13 } },
    ],
    { x: 0.85, y: 3.85, w: colW - 0.5, h: 1.7, margin: 0, fontFace: FONT_BODY }
  );

  // AFTER
  const ax = 0.6 + colW + 0.3;
  card(s, ax, 2.7, colW, 3.0);
  accentBar(s, ax, 2.7, 3.0, C.success);
  s.addText("AFTER", {
    x: ax + 0.25, y: 2.85, w: colW - 0.5, h: 0.3,
    fontFace: FONT_BODY, fontSize: 11, color: C.success, bold: true, charSpacing: 6, margin: 0,
  });
  s.addText("BIS Compass", {
    x: ax + 0.25, y: 3.2, w: colW - 0.5, h: 0.5,
    fontFace: FONT_TITLE, fontSize: 22, bold: true, color: C.text, margin: 0,
  });
  s.addText(
    [
      { text: "•  Sub-second top-5 with confidence scores", options: { breakLine: true, color: C.text, fontSize: 13 } },
      { text: "•  Plain-English query → ranked IS codes", options: { breakLine: true, color: C.text, fontSize: 13 } },
      { text: "•  Hybrid retrieval surfaces related standards", options: { breakLine: true, color: C.text, fontSize: 13 } },
      { text: "•  Grounded rationale citing the actual scope text", options: { color: C.text, fontSize: 13 } },
    ],
    { x: ax + 0.25, y: 3.85, w: colW - 0.5, h: 1.7, margin: 0, fontFace: FONT_BODY }
  );

  // Bottom callout
  card(s, 0.6, 5.95, W - 1.2, 1.15);
  accentBar(s, 0.6, 5.95, 1.15, C.accent);
  s.addText("DOWNSTREAM EFFECT", {
    x: 0.85, y: 6.05, w: W - 1.7, h: 0.3,
    fontFace: FONT_BODY, fontSize: 10, color: C.accent, bold: true, charSpacing: 6, margin: 0,
  });
  s.addText(
    "Faster compliance discovery → quicker product launches → more BIS-certified MSEs in the market. Multiplied across thousands of small manufacturers in cement, steel, concrete, and aggregates, this compresses an industry-wide bottleneck from quarters to days.",
    {
      x: 0.85, y: 6.35, w: W - 1.7, h: 0.7,
      fontFace: FONT_BODY, fontSize: 13, color: C.text, margin: 0,
    }
  );

  footer(s);
}

// ═══════════════════════════════════════════════════════════════════════════
// SLIDE 8 · Team & Acknowledgements
// ═══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  chrome(s, 8, "TEAM");
  bigTitle(s, "Built solo, in seven days", "Team Sigma Squad");

  // Tech stack grid
  s.addText("OPEN-SOURCE STACK", {
    x: 0.6, y: 2.7, w: W - 1.2, h: 0.3,
    fontFace: FONT_BODY, fontSize: 11, color: C.accent, bold: true, charSpacing: 5, margin: 0,
  });

  const techStack = [
    { cat: "RETRIEVAL", items: ["BAAI/bge-m3", "BAAI/bge-reranker-v2-m3", "FAISS", "rank_bm25"] },
    { cat: "DATA",      items: ["PyMuPDF",      "PyTorch 2.11 (cu128)",     "transformers",      "sentence-transformers"] },
    { cat: "SERVING",   items: ["FastAPI",      "Uvicorn",                  "Gemini 2.0 Flash",  "google-genai"] },
    { cat: "FRONTEND",  items: ["Next.js 16",   "Tailwind CSS v4",          "Framer Motion",     "shadcn-style components"] },
  ];
  const stackY = 3.05;
  const cellW = (W - 1.2 - 0.3 * 3) / 4;
  techStack.forEach((s_, i) => {
    const cx = 0.6 + i * (cellW + 0.3);
    card(s, cx, stackY, cellW, 2.4);
    s.addText(s_.cat, {
      x: cx + 0.25, y: stackY + 0.2, w: cellW - 0.5, h: 0.3,
      fontFace: FONT_BODY, fontSize: 10, charSpacing: 5, color: C.accent, bold: true, margin: 0,
    });
    const rows = s_.items.map((it, ix) => ({
      text: it,
      options: { breakLine: ix < s_.items.length - 1, color: C.text, fontSize: 12 },
    }));
    s.addText(rows, {
      x: cx + 0.25, y: stackY + 0.55, w: cellW - 0.5, h: 1.7,
      fontFace: FONT_MONO, margin: 0, paraSpaceAfter: 4,
    });
  });

  // Acknowledgements
  card(s, 0.6, 5.65, W - 1.2, 1.4);
  accentBar(s, 0.6, 5.65, 1.4, C.accent2);
  s.addText("THANK YOU", {
    x: 0.85, y: 5.78, w: W - 1.7, h: 0.3,
    fontFace: FONT_BODY, fontSize: 10, color: C.accent2, charSpacing: 6, bold: true, margin: 0,
  });
  s.addText(
    "Bureau of Indian Standards · Sigma Squad organisers · Beijing Academy of AI (bge-m3, bge-reranker-v2-m3) · Google AI Studio · Hugging Face Hub · the open-source maintainers behind FAISS, PyTorch, FastAPI, and Next.js.",
    {
      x: 0.85, y: 6.1, w: W - 1.7, h: 0.6,
      fontFace: FONT_BODY, fontSize: 12, color: C.text, margin: 0,
    }
  );
  s.addText("github.com/<your-org>/bis-compass  ·  Submission for Sigma Squad × BIS Hackathon 2026", {
    x: 0.85, y: 6.7, w: W - 1.7, h: 0.3,
    fontFace: FONT_MONO, fontSize: 10, color: C.textDim, italic: true, margin: 0,
  });
}

// Save
const outPath = "presentation.pptx";
pres.writeFile({ fileName: outPath }).then((p) => {
  console.log("Wrote:", p);
});
