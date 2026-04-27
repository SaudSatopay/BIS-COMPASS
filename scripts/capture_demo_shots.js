// Capture two demo screenshots for slide 5:
//   docs/demo_hero.png      — hero + search panel + sample queries
//   docs/demo_results.png   — ranked top-5 results card with confidence badges
//
// Uses playwright-core driving the user's installed Chrome (no separate
// Chromium download). Disables prefers-reduced-motion so Framer Motion
// animations actually paint. Runs against the local backend (:8000) and
// frontend (:3000) which must already be up.

const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright-core");

const CHROME =
  "C:/Program Files/Google/Chrome/Application/chrome.exe";
const FRONTEND = "http://127.0.0.1:3000";
const QUERY =
  "Our company is shifting to manufacturing hollow and solid lightweight concrete masonry blocks. What standard outlines the dimensions and physical requirements?";

(async () => {
  const browser = await chromium.launch({
    executablePath: CHROME,
    headless: true,
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    reducedMotion: "no-preference",
    colorScheme: "dark",
  });
  const page = await context.newPage();

  // 1) Hero + search panel
  await page.goto(FRONTEND, { waitUntil: "networkidle" });
  await page.waitForSelector("textarea");
  // give Framer Motion's first paint a moment
  await page.waitForTimeout(1500);

  const heroOut = path.join(__dirname, "..", "docs", "demo_hero.png");
  await page.screenshot({
    path: heroOut,
    clip: { x: 0, y: 0, width: 1440, height: 900 },
  });
  console.log("wrote", heroOut);

  // 2) Type the query (production build hydrates correctly so React state works).
  await page.locator("textarea").click();
  await page.keyboard.type(QUERY, { delay: 5 });
  await page.locator('button[type="submit"]:not([disabled])').waitFor({ timeout: 10000 });
  await page.click('button[type="submit"]:not([disabled])');
  // Results render once the /search promise resolves; rerank uses GPU so allow up to 20 s.
  await page.waitForSelector("ol li", { timeout: 25000 });
  await page.waitForTimeout(900); // let stagger animations settle

  // Scroll the results list into the top of the viewport for a clean shot.
  await page.evaluate(() => {
    const ol = document.querySelector("ol");
    if (ol) ol.scrollIntoView({ block: "start", behavior: "instant" });
    window.scrollBy(0, -120);
  });
  await page.waitForTimeout(400);

  const resOut = path.join(__dirname, "..", "docs", "demo_results.png");
  await page.screenshot({
    path: resOut,
    clip: { x: 0, y: 0, width: 1440, height: 900 },
  });
  console.log("wrote", resOut);

  await browser.close();
})().catch((err) => {
  console.error("FAILED:", err);
  process.exit(1);
});
