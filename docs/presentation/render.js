// Renders slides.html to presentation.pdf at the repository root.
// Requires Node.js and Playwright with Chromium: npm i playwright && npx playwright install chromium
// Usage (from this folder): node render.js
const path = require("path");
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("file://" + path.resolve(__dirname, "slides.html"), { waitUntil: "load" });
  await page.pdf({
    path: path.resolve(__dirname, "..", "..", "presentation.pdf"),
    width: "1280px",
    height: "720px",
    printBackground: true,
    preferCSSPageSize: true,
  });
  await browser.close();
  console.log("presentation.pdf written");
})();
