import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, resolve } from "node:path";
import { chromium, firefox, webkit } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

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
    await page.getByRole("heading", { name: "Consumer-rendered form acceptance" }).waitFor({ timeout: 5000 });
    const name = page.getByRole("textbox", { name: /^Name/ });
    assert.equal(await name.getAttribute("aria-invalid"), null, `${label}: validation starts hidden`);
    assert.equal(await page.locator(".consumer-error").count(), 0, `${label}: no initial error component`);
    await page.getByRole("button", { name: "Submit" }).click();
    assert.equal(await page.locator(".fixture-action-result").innerText(), "validation", `${label}: consumer validation action is blocked`);
    await page.locator(".consumer-error").waitFor();
    assert.equal(await name.getAttribute("aria-invalid"), "true", `${label}: consumer renderer receives visible errors`);
    assert.match(await page.locator(".consumer-error").innerText(), /required/i, `${label}: inline validation message`);
    await name.fill("Ada");
    await page.waitForFunction(() => document.querySelector(".fixture-form-data")?.textContent?.includes('"name":"Ada"') === true);
    assert.equal(await name.getAttribute("aria-invalid"), null, `${label}: corrected field clears invalid state`);
    assert.equal(await page.locator(".consumer-error").count(), 0, `${label}: corrected field clears message`);
    await page.getByRole("button", { name: "Submit" }).click();
    assert.equal(await page.locator(".fixture-action-result").innerText(), "submitted", `${label}: valid consumer submission`);
    await page.getByRole("button", { name: "العربية" }).click();
    assert.equal(await page.locator("html").getAttribute("dir"), "rtl", `${label}: application-owned RTL switch`);
    await page.getByRole("button", { name: "English" }).waitFor();
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
    results.push({ engine, profile: profile.name, consumerRenderers: "passed", validation: "passed", localization: "passed", accessibility: "passed", reflow: "passed", csp: "passed" });
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
