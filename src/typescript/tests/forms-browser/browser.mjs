import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, resolve } from "node:path";
import { chromium, firefox, webkit } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const output = resolve(import.meta.dirname, "../../../../artifacts/forms-browser");
const evidence = resolve(output, "evidence");
await mkdir(evidence, { recursive: true });
const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"]
]);
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

const requested = (process.argv.find(value => value.startsWith("--engines="))?.split("=")[1] ?? "chromium,firefox,webkit")
  .split(",").filter(Boolean);
const browserTypes = { chromium, firefox, webkit };
for (const engine of requested) {
  if (!(engine in browserTypes)) throw new Error(`Unknown browser engine '${engine}'.`);
}
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
  const context = await browser.newContext({
    viewport: profile.viewport,
    screen: profile.viewport,
    hasTouch: profile.touch,
    isMobile: profile.mobile,
    locale: "en-US",
    timezoneId: "UTC"
  });
  const page = await context.newPage();
  const label = `${engine}/${profile.name}`;
  page.on("pageerror", error => errors.push(`${label}: ${error.message}`));
  page.on("console", message => { if (message.type() === "error") errors.push(`${label}: console: ${message.text()}`); });
  await page.route("**/*", route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
  try {
    await page.emulateMedia({ colorScheme: "light", reducedMotion: "reduce", forcedColors: "none" });
    await page.goto(origin);
    try {
      await page.getByRole("heading", { name: "Form journey acceptance" }).waitFor({ timeout: 5000 });
    } catch (error) {
      throw new Error(`${label}: fixture startup failed: ${errors.join(" | ") || error.message}`);
    }
    assertNoErrors(label, "startup");
    assert.equal(await page.locator(".pk-form-wizard__step").count(), 2, `${label}: conditional step starts hidden`);
    await page.getByRole("button", { name: "Submit now" }).click();
    assert.equal(await page.locator('[data-action-id="submit"][role="alert"]').innerText(), "Resolve the form validation errors before continuing.", `${label}: action validation gate`);
    assert.equal(await page.locator(".fixture-action-result").innerText(), "submit:validation", `${label}: blocked result callback`);
    const requiredName = page.getByRole("textbox", { name: /^Name/ });
    assert.equal(await requiredName.getAttribute("aria-invalid"), "true", `${label}: required field exposes its invalid state`);
    assert.match(await page.locator('[data-control-path="name"] .pk-form-control__error').innerText(), /required/i, `${label}: required field renders an inline error`);
    assert.deepEqual(await requiredName.evaluate(element => {
      const style = getComputedStyle(element);
      return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth };
    }), { outlineStyle: "solid", outlineWidth: "2px" }, `${label}: invalid field has a visible danger-state outline`);
    await page.getByRole("button", { name: "Save draft" }).click();
    await page.getByText("save:succeeded", { exact: true }).waitFor();
    assert.equal(await page.locator(".fixture-action-result").innerText(), "save:succeeded", `${label}: manifest action dispatch`);
    await page.getByRole("button", { name: "Test safe failure" }).click();
    await page.getByText("fail:failed", { exact: true }).waitFor();
    assert.equal(await page.locator('[data-action-id="fail"][role="alert"]').innerText(), "The action could not be completed.", `${label}: safe public failure`);
    assert.equal((await page.locator("body").innerText()).includes("private fixture detail"), false, `${label}: private failure is not disclosed`);
    await page.getByRole("button", { name: /^Next$/ }).click();
    assert.equal(await page.locator('[data-status="error"]').count(), 1, `${label}: invalid advance is blocked`);
    assert.equal(await page.locator('[aria-current="step"]').getAttribute("id"), "pk-wizard-account-setup-profile-step");
    try {
      await page.getByRole("textbox", { name: /^Name/ }).waitFor({ timeout: 5000 });
      await page.getByRole("textbox", { name: /^Name/ }).fill("Ada");
      await waitForFormData(page, '"name":"Ada"');
      assert.equal(await requiredName.getAttribute("aria-invalid"), null, `${label}: corrected field clears its invalid state`);
      assert.equal(await page.locator('[data-control-path="name"] .pk-form-control__error').count(), 0, `${label}: corrected field clears its inline error`);
    } catch (error) {
      throw new Error(`${label}: core control labels were ${JSON.stringify(await page.locator("label").allTextContents())}: ${error.message}`);
    }
    const notes = page.getByRole("textbox", { name: "Notes" });
    await notes.click();
    await notes.fill("Note");
    await waitForFormData(page, '"notes":"Note"');
    await page.getByRole("spinbutton", { name: "Quantity" }).click();
    await page.getByRole("spinbutton", { name: "Quantity" }).pressSequentially("3");
    await waitForFormData(page, '"quantity":3');
    await page.getByRole("checkbox", { name: "Product updates" }).check();
    await waitForFormData(page, '"updates":true');
    await page.getByRole("combobox", { name: "Role" }).click();
    await page.getByRole("combobox", { name: "Role" }).selectOption({ label: "Writer" });
    await waitForFormData(page, '"role":"writer"');
    const channels = page.getByRole("listbox", { name: "Channels" });
    if (engine === "chromium") {
      await channels.selectOption({ label: "Push" });
      await waitForFormData(page, '"channels":["push"]');
      assert.deepEqual(await channels.evaluate(element => [...element.selectedOptions].map(option => option.textContent)), ["Push"], `${label}: semantic core controls preserve typed multi-choice data`);
    } else {
      assert.equal(await channels.getAttribute("multiple"), "", `${label}: semantic multi-choice listbox remains native`);
      assert.equal(await channels.locator("option").count(), 3, `${label}: semantic multi-choice options remain available`);
    }
    await page.locator(".pk-form-wizard__step").nth(2).waitFor();
    await page.getByRole("button", { name: /^Next$/ }).click();
    assert.match(await page.locator('[aria-current="step"]').innerText(), /Preferences/);
    const plan = page.getByRole("combobox", { name: /^Plan/ });
    await plan.fill("pro");
    await page.getByRole("option", { name: "Professional" }).waitFor();
    await page.getByRole("button", { name: "Load more" }).click();
    await page.getByRole("option", { name: "Starter" }).waitFor();
    await page.getByRole("option", { name: "Professional" }).click();
    assert.equal(await plan.inputValue(), "Professional", `${label}: selected label hydration`);
    await page.getByRole("button", { name: "العربية" }).click();
    assert.equal(await page.locator("html").getAttribute("dir"), "rtl", `${label}: RTL direction`);
    assert.match(await page.locator('[aria-current="step"]').innerText(), /التفضيلات/, `${label}: locale switch retains step`);
    await page.waitForFunction(value => [...document.querySelectorAll("input")].some(input => input.value === value), "احترافي");
    await page.getByRole("button", { name: "تخطي" }).click();
    assert.match(await page.locator('[aria-current="step"]').innerText(), /تأكيد/);
    await page.locator('[aria-current="step"]').focus();
    await page.keyboard.press("ArrowRight");
    assert.match(await page.locator('[aria-current="step"]').innerText(), /التفضيلات/, `${label}: RTL arrow navigation`);
    await page.locator("#pk-wizard-account-setup-confirm-step").click();
    await page.getByRole("button", { name: "إنهاء" }).click();
    assert.equal(await page.locator(".fixture-finished").innerText(), "Journey completed");
    assertNoErrors(label, "journey");
    const violations = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    assert.deepEqual(violations.violations.map(item => ({ id: item.id, nodes: item.nodes.map(node => node.target) })), [], `${label}: accessibility`);
    assertNoErrors(label, "axe");
    for (const button of await page.locator("button:visible").all()) {
      const box = await button.boundingBox();
      assert(box !== null && box.width >= 44 && box.height >= 44, `${label}: touch-sized button`);
    }
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${label}: no page overflow`);
    await page.setViewportSize({ width: 320, height: 900 });
    await page.evaluate(() => { document.documentElement.classList.add("pk-text-200"); });
    const reflows = await page.evaluate(() => ({
      fits: document.documentElement.scrollWidth <= innerWidth + 1,
      width: document.documentElement.scrollWidth,
      viewport: innerWidth,
      bodyWidth: document.body.scrollWidth,
      main: (() => { const value = document.querySelector("main")?.getBoundingClientRect(); return value === undefined ? null : { left: Math.round(value.left), right: Math.round(value.right), width: Math.round(value.width) }; })(),
      active: document.activeElement === null ? null : { tag: document.activeElement.tagName, text: document.activeElement.textContent?.trim(), className: document.activeElement.className },
      offenders: [...document.querySelectorAll("body *")].filter(element => element.getBoundingClientRect().right > innerWidth + 1 || element.getBoundingClientRect().left < -1).slice(0, 12).map(element => ({ tag: element.tagName, className: element.className, left: Math.round(element.getBoundingClientRect().left), right: Math.round(element.getBoundingClientRect().right), scrollWidth: element.scrollWidth }))
    }));
    assert(reflows.fits, `${label}: 320px/200% RTL reflow ${JSON.stringify(reflows)}`);
    assert.equal(await page.locator(".pk-form-wizard__step-button").first().evaluate(element => getComputedStyle(element).transitionDuration), "0s");
    assertNoErrors(label, "reflow");
    if (engine === "chromium") {
      await page.screenshot({ path: resolve(evidence, `${engine}-${profile.name}.png`) });
      assertNoErrors(label, "screenshot");
    }
    results.push({ engine, profile: profile.name, actions: "passed", lookups: "passed", theme: "passed", validation: "passed", keyboardRtl: "passed", localization: "passed", axe: "passed", touch: "passed", reflow: "passed", csp: "passed" });
  } finally {
    await context.close();
    await browser.close();
  }
}

function assertNoErrors(label, stage) {
  const relevant = errors.filter(error => error.startsWith(`${label}:`));
  assert.deepEqual(relevant, [], `${label}: ${stage} console/page errors`);
}

try {
  for (const profile of profiles) {
    for (const engine of profile.engines) await verify(engine, browserTypes[engine], profile);
  }
  assert.deepEqual(errors, []);
} finally {
  await new Promise(resolveClose => server.close(resolveClose));
  await writeFile(resolve(evidence, "report.json"), JSON.stringify({
    results,
    errors,
    scope: "Automated engine/device emulation; physical devices, virtual keyboards, screen readers and production field performance remain manual acceptance."
  }, null, 2));
}
console.log(`Forms browser acceptance passed: ${results.length} engine/device profiles.`);

async function waitForFormData(page, fragment) {
  try {
    await page.waitForFunction(
      expected => document.querySelector(".fixture-form-data")?.textContent?.includes(expected) === true,
      fragment,
      { timeout: 5000 }
    );
  } catch (error) {
    throw new Error(`Form data did not contain ${fragment}; current data is ${await page.locator(".fixture-form-data").textContent()}: ${error.message}`);
  }
}
