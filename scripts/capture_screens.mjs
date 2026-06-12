// Captures README screenshots from the local dev server (demo mode).
// Usage: node scripts/capture_screens.mjs [baseUrl]
import { chromium } from "playwright";

const BASE = process.argv[2] || "http://localhost:3000";
const OUT = "docs/assets";

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
});

// 1. Landing hero
await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
await page.waitForTimeout(900);
await page.screenshot({ path: `${OUT}/landing.png` });

// 2. Contradictions — document selection
await page.goto(`${BASE}/contradictions`, { waitUntil: "networkidle" });
await page.waitForTimeout(900);
await page.screenshot({ path: `${OUT}/select-documents.png` });

// 3. Run demo analysis, capture results
await page.getByText("Atorvastatin and Cardiovascular Mortality").click();
await page.getByText("Statin Therapy and Cardiovascular Outcomes").click();
await page.getByRole("button", { name: /Analyze/ }).click();
await page.waitForSelector("text=Analysis Complete", { timeout: 30000 });
await page.waitForTimeout(900);
await page.screenshot({ path: `${OUT}/analysis-results.png` });

// 4. Expanded contradiction card with explanation
await page.getByText("Analysis & Explanation").first().click();
await page.waitForTimeout(700);
const card = page.locator(".card-hover").first();
await card.scrollIntoViewIfNeeded();
await page.waitForTimeout(400);
await card.screenshot({ path: `${OUT}/contradiction-card.png` });

await browser.close();
console.log("Saved 4 screenshots to", OUT);
