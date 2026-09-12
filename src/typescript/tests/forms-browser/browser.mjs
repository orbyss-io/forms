import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, resolve } from "node:path";
import { chromium, firefox, webkit, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { dictionaries } from "./locales.mjs";

const output = resolve(import.meta.dirname, "../../../../artifacts/forms-browser");
const evidence = resolve(output, "evidence");
await mkdir(evidence, { recursive: true });
const contentTypes = new Map([[".html", "text/html; charset=utf-8"], [".js", "text/javascript; charset=utf-8"], [".css", "text/css; charset=utf-8"], [".json", "application/json; charset=utf-8"]]);
const server = createServer(async (request, response) => {
  const pathname = new URL(request.url ?? "/", "http://127.0.0.1").pathname;
  const relative = pathname === "/" ? "index.html" : pathname.slice(1);
  if (relative.includes("..") || !["index.html", "app.js", "styles.css", "build-evidence.json"].includes(relative)) {
    response.writeHead(404); response.end(); return;
  }
  try {
    response.setHeader("Content-Type", contentTypes.get(extname(relative)) ?? "application/octet-stream");
    response.setHeader("X-Content-Type-Options", "nosniff");
    response.end(await readFile(resolve(output, relative)));
  } catch {
    response.writeHead(500); response.end("Fixture read failed");
  }
});
await new Promise(resolveListen => server.listen(0, "127.0.0.1", resolveListen));
const address = server.address();
if (address === null || typeof address === "string") throw new Error("Fixture server did not bind a TCP port.");
const origin = `http://127.0.0.1:${address.port}`;

const requested = (process.argv.find(value => value.startsWith("--engines="))?.split("=")[1] ?? "chromium,firefox,webkit").split(",").filter(Boolean);
const browserTypes = { chromium, firefox, webkit };
for (const engine of requested) if (!(engine in browserTypes)) throw new Error(`Unknown browser engine '${engine}'.`);
const profiles = [
  { name: "desktop", engines: requested, viewport: { width: 1366, height: 900 }, touch: false, mobile: false },
  { name: "phone-portrait", engines: requested.filter(value => value === "chromium"), viewport: { width: 390, height: 844 }, touch: true, mobile: true },
  { name: "phone-landscape", engines: requested.filter(value => value === "chromium"), viewport: { width: 844, height: 390 }, touch: true, mobile: true },
  { name: "tablet-portrait", engines: requested.filter(value => value === "webkit"), viewport: { width: 768, height: 1024 }, touch: true, mobile: true },
  { name: "tablet-landscape", engines: requested.filter(value => value === "webkit"), viewport: { width: 1024, height: 768 }, touch: true, mobile: true }
];
const results = [];
const errors = [];

async function verify(engine, browserType, profile) {
  const browser = await browserType.launch();
  const context = await browser.newContext({ viewport: profile.viewport, screen: profile.viewport, hasTouch: profile.touch, isMobile: profile.mobile, locale: "en-US", timezoneId: "UTC" });
  const page = await context.newPage();
  const label = `${engine}/${profile.name}`;
  page.on("pageerror", error => errors.push(`${label}: ${error.message}`));
  page.on("console", message => { if (message.type() === "error") errors.push(`${label}: console: ${message.text()}`); });
  await page.route("**/*", route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
  try {
    await page.emulateMedia({ colorScheme: "light", reducedMotion: "reduce", forcedColors: "none" });
    await page.goto(origin);
    await page.getByRole("heading", { name: dictionaries.en["app.title"] }).waitFor({ timeout: 10000 });
    await expect(page.getByTestId("release")).toHaveText("synthetic-product-v1");
    const field = path => page.locator(`[data-control-path="${path}"]`).locator("input,select");
    const result = page.locator(".fixture-action-result");
    const calculate = page.locator(".consumer-submit");
    await expect(page.locator(".consumer-error")).toHaveCount(0);
    await expect(field("detail")).toHaveCount(0);
    await field("name").fill("Ada");
    await field("kind").selectOption("custom");
    await expect(field("detail")).toBeEnabled();
    await field("editable").click();
    await expect(field("editable")).not.toBeChecked();
    await expect(field("detail")).toBeDisabled();
    await page.getByTestId("review-lock").check();
    await expect(field("name")).toBeDisabled();
    await expect(field("detail")).toBeDisabled();
    await page.getByTestId("review-lock").uncheck();
    await expect(field("detail")).toBeDisabled();
    await field("editable").click();
    await expect(field("editable")).toBeChecked();
    await field("detail").fill("Custom specification");
    await page.getByTestId("next").click();
    await expect(field("reference")).toHaveAttribute("readonly", "");
    await calculate.click();
    await expect(result).toHaveAttribute("data-status", "succeeded");
    await page.getByTestId("back").click();
    await expect(field("detail")).toHaveValue("Custom specification");
    await field("kind").selectOption("standard");
    await expect(field("detail")).toHaveCount(0);
    await expect(page.locator(".fixture-form-data")).not.toContainText('"detail"');
    await field("kind").selectOption("custom");
    await expect(field("detail")).toHaveValue("");
    await page.getByTestId("next").click();
    await calculate.click();
    await expect(result).toHaveAttribute("data-status", "validation");
    await page.getByTestId("back").click();
    for (const [locale, dictionary] of Object.entries(dictionaries)) {
      await page.locator(".fixture-header select").selectOption(locale);
      await expect(page.locator("h1")).toHaveText(dictionary["app.title"]);
      await expect(page.locator('[data-control-path="detail"] label')).toContainText(dictionary["fields.detail"]);
      await expect(page.locator('[data-control-path="name"] .consumer-help')).toHaveText(dictionary["fields.name.help"]);
      await expect(page.locator('[data-control-path="detail"] .consumer-error')).toHaveText(dictionary["error.required"]);
      await expect(field("kind").locator('option[value="custom"]')).toHaveText(dictionary["choices.custom"]);
      await expect(page.getByTestId("next")).toHaveText(dictionary["app.next"]);
      await expect(page.locator("html")).toHaveAttribute("dir", locale === "ar" ? "rtl" : "ltr");
    }
    await field("kind").selectOption("standard");
    await page.getByTestId("next").click();
    await calculate.click();
    await page.getByTestId("cancel").click();
    await expect(calculate).toBeEnabled();
    await expect(result).toHaveAttribute("data-status", "cancelled");
    await calculate.click();
    await field("quantity").fill("2");
    await expect(calculate).toBeEnabled();
    await expect(result).toHaveAttribute("data-status", "");
    await calculate.click();
    await expect(result).toHaveAttribute("data-status", "succeeded");
    await expect(result).toContainText("20");
    await calculate.click();
    await page.getByTestId("reset").click();
    await expect(field("name")).toHaveValue("");
    await expect(page.getByTestId("cancel")).toBeDisabled();
    await expect(result).toHaveAttribute("data-status", "");
    const violations = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    assert.deepEqual(violations.violations.map(item => ({ id: item.id, nodes: item.nodes.map(node => node.target) })), [], `${label}: accessibility`);
    for (const button of await page.locator("button:visible").all()) {
      const box = await button.boundingBox();
      assert(box !== null && box.width >= 44 && box.height >= 44, `${label}: touch-sized application control`);
    }
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${label}: no page overflow`);
    await page.setViewportSize({ width: 320, height: 900 });
    await page.evaluate(() => document.documentElement.classList.add("pk-text-200"));
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${label}: 320px/200% reflow`);
    if (engine === "chromium") await page.screenshot({ path: resolve(evidence, `${engine}-${profile.name}.png`) });
    assert.deepEqual(errors.filter(error => error.startsWith(`${label}:`)), [], `${label}: console/page errors`);
    results.push({ engine, profile: profile.name, publishedRelease: "passed", admission: "passed", consumerRenderers: "passed", conditionalValidation: "passed", combinedRules: "passed", branchCleanup: "passed", cancellationRaces: "passed", localization: ["en", "nl", "de", "ar"], accessibility: "passed", reflow: "passed", csp: "passed" });
  } catch (error) {
    const state = { label, data: await page.locator(".fixture-form-data").textContent().catch(() => null), errors: await page.locator(".consumer-error").allTextContents(), pageErrors: errors };
    await writeFile(resolve(evidence, "failure.json"), JSON.stringify(state, null, 2));
    console.error(JSON.stringify(state));
    throw error;
  } finally {
    await context.close();
    await browser.close();
  }
}

try {
  for (const profile of profiles) for (const engine of profile.engines) await verify(engine, browserTypes[engine], profile);
  assert.deepEqual(errors, []);
} finally {
  await new Promise(resolveClose => server.close(resolveClose));
  await writeFile(resolve(evidence, "report.json"), JSON.stringify({ results, errors, scope: "Automated engine/device emulation of the forms engine through fixture-owned renderers; Orbyss Forms publishes no renderer components." }, null, 2));
}
console.log(`Forms engine browser acceptance passed: ${results.length} engine/device profiles.`);
