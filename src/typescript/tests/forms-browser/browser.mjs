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
    } catch (error) {
      throw new Error(`${label}: core control labels were ${JSON.stringify(await page.locator("label").allTextContents())}: ${error.message}`);
    }
    await page.getByRole("textbox", { name: "Notes" }).fill("Needs a governed renderer suite.");
    await page.getByRole("spinbutton", { name: "Quantity" }).fill("3");
    await page.getByRole("checkbox", { name: "Product updates" }).check();
    await page.getByRole("combobox", { name: "Role" }).selectOption({ label: "Writer" });
    await page.getByRole("listbox", { name: "Channels" }).selectOption([{ label: "Email" }, { label: "Push" }]);
    assert.deepEqual(await page.getByRole("listbox", { name: "Channels" }).evaluate(element => [...element.selectedOptions].map(option => option.textContent)), ["Email", "Push"], `${label}: semantic core controls preserve typed multi-choice data`);
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
    const modeler = page.locator(".pk-form-modeler");
    await modeler.getByRole("button", { name: "Add text field" }).click();
    assert.equal(await modeler.getByRole("button", { name: "Field 1", exact: true }).count(), 1, `${label}: palette adds field to tree`);
    assert.equal(await modeler.locator('[data-element-id="field-1-control-1"] > .pk-form-modeler__canvas-heading > button:first-child').count(), 1, `${label}: palette atomically adds matching control to canvas`);
    assert.match(await modeler.getByText(/^Trusted preview:/).innerText(), /Field 1/, `${label}: application-owned preview receives the synchronized document`);
    await modeler.getByRole("button", { name: "Add group" }).click();
    const fieldControl = modeler.locator('[data-element-id="field-1-control-1"]');
    await fieldControl.locator(':scope > .pk-form-modeler__canvas-heading > button:first-child').click();
    const elementInspector = modeler.getByRole("complementary", { name: "Properties" });
    await elementInspector.getByRole("combobox", { name: "Parent" }).selectOption("group-1");
    await elementInspector.getByRole("button", { name: "Move element" }).click();
    assert.equal(await modeler.locator('[data-element-id="group-1"] [data-element-id="field-1-control-1"]').count(), 1, `${label}: touch and keyboard-safe move controls reparent canvas blocks`);
    assert.equal(await modeler.getByRole("button", { name: "Move earlier: Field 1" }).isDisabled(), true, `${label}: bounded reorder controls reflect the new sibling position`);
    await modeler.getByRole("button", { name: "Name", exact: true }).click();
    const inspector = modeler.getByRole("complementary", { name: "Properties" });
    await inspector.getByRole("combobox", { name: "Component" }).selectOption("ProgramKit.SearchableSelect");
    assert.match(await inspector.innerText(), /@orbyss\/program-kit-forms-lookups-react/, `${label}: installed renderer package is visible`);
    assert.equal(await modeler.getByRole("button", { name: "Commit changes" }).isDisabled(), true, `${label}: invalid component binding blocks commit`);
    await inspector.getByRole("textbox", { name: "Data source" }).fill("catalog.plans");
    assert.equal(await modeler.getByRole("button", { name: "Commit changes" }).isEnabled(), true, `${label}: valid component binding permits commit`);
    const fieldLabel = inspector.getByRole("textbox", { name: "Label" });
    await fieldLabel.fill("Customer name");
    await fieldLabel.press("Tab");
    assert.equal(await modeler.getByRole("button", { name: "Customer name", exact: true }).count(), 1, `${label}: tree reflects inspector edit`);
    assert.equal(await modeler.getByRole("button", { name: "Undo" }).isEnabled(), true, `${label}: modeler edit enters undo history`);
    await modeler.getByRole("tab", { name: "JSON" }).focus();
    await modeler.getByRole("tab", { name: "JSON" }).press("Enter");
    const sourceEditor = modeler.getByLabel("Form JSON");
    assert.match(await sourceEditor.inputValue(), /Customer name/, `${label}: JSON view reflects design edit`);
    await sourceEditor.fill('{"invalid":true}');
    await modeler.getByRole("button", { name: "Apply JSON" }).click();
    assert.match(await modeler.getByRole("alert").innerText(), /PKM000|does not match/, `${label}: invalid JSON contract is rejected`);
    await modeler.getByRole("tab", { name: "Design" }).focus();
    await modeler.getByRole("tab", { name: "Design" }).press("Enter");
    await modeler.getByRole("button", { name: "Undo" }).click();
    assert.equal(await modeler.getByRole("button", { name: "Name", exact: true }).count(), 1, `${label}: undo synchronizes the tree`);
    await modeler.getByRole("button", { name: "Submit", exact: true }).click();
    assert.match(await modeler.getByRole("complementary", { name: "Properties" }).innerText(), /@orbyss\/program-kit-registration-actions/, `${label}: action package contract is visible`);
    await modeler.getByRole("tab", { name: "Graph" }).focus();
    await modeler.getByRole("tab", { name: "Graph" }).press("Enter");
    assert.equal(await modeler.getByRole("heading", { name: "Form nodes" }).count(), 1, `${label}: graph nodes visible`);
    assert.equal(await modeler.getByRole("table").getByText("binds", { exact: true }).count(), 2, `${label}: graph relationships visible`);
    const localization = page.locator(".pk-localization");
    assert.match(await localization.getByRole("caption").innerText(), /4 rows/, `${label}: localization row projection`);
    await localization.getByRole("button", { name: "Add message" }).click();
    const addMessage = localization.getByRole("dialog", { name: "Add localization message" });
    await addMessage.getByRole("textbox", { name: "Key" }).fill("cart.count");
    await addMessage.getByRole("textbox", { name: "Source" }).fill("{count, plural, one {One item} other {# items}}");
    await addMessage.getByRole("button", { name: "Add argument" }).click();
    await addMessage.getByRole("textbox", { name: "Argument name" }).fill("count");
    await addMessage.getByRole("combobox", { name: "Argument type" }).selectOption("integer");
    await addMessage.getByRole("button", { name: "Create message" }).click();
    assert.equal(await addMessage.count(), 0, `${label}: add-message dialog closes after a valid optimistic command`);
    assert.match(await localization.getByRole("caption").innerText(), /6 rows/, `${label}: added ICU message enters the locale grid`);
    await localization.getByRole("button", { name: "Import", exact: true }).click();
    const importDialog = localization.getByRole("dialog", { name: "Preview localization import" });
    await importDialog.getByLabel("Import file").setInputFiles({ name: "registration.csv", mimeType: "text/csv", buffer: Buffer.from("key,source,nl\nfields.email,Email,E-mail") });
    await importDialog.getByRole("textbox", { name: "Target locale" }).fill("nl");
    await importDialog.getByRole("button", { name: "Preview import" }).click();
    await importDialog.waitFor({ state: "detached" });
    assert.equal(await importDialog.count(), 0, `${label}: import dialog closes only after trusted preview completion`);
    assert.equal(await page.locator(".fixture-localization-action").innerText(), "import-previewed:csv:nl", `${label}: bounded upload and mapping reached the trusted preview port`);
    assert.match(await localization.getByRole("region", { name: "Import preview" }).innerText(), /fields.email/, `${label}: returned import preview replaces the reviewed proposal`);
    await localization.getByRole("combobox", { name: "Form" }).selectOption("registration");
    await localization.getByRole("combobox", { name: "Locale" }).selectOption("ar");
    assert.match(await localization.getByRole("caption").innerText(), /1 rows/, `${label}: structured form and locale filters`);
    const translation = localization.getByRole("textbox", { name: "Translation: fields.name (ar)" });
    assert.equal(await translation.getAttribute("dir"), "rtl", `${label}: target-locale editing direction`);
    await translation.fill("الاسم");
    await translation.press("Tab");
    await localization.getByRole("combobox", { name: "Status: fields.name (ar)" }).selectOption("reviewed");
    assert.equal(await localization.getByRole("button", { name: "Undo" }).isEnabled(), true, `${label}: inline translation is undoable`);
    await localization.getByRole("checkbox", { name: "Missing only" }).check();
    assert.match(await localization.getByRole("caption").innerText(), /0 rows/, `${label}: completed translation leaves missing filter`);
    await localization.getByRole("button", { name: "Apply import" }).click();
    assert.equal(await page.locator(".fixture-localization-action").innerText(), "import-applied", `${label}: reviewed import preview callback`);
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
      offenders: [...document.querySelectorAll("body *")].filter(element => element.getBoundingClientRect().right > innerWidth + 1 || element.getBoundingClientRect().left < -1).slice(0, 12).map(element => ({ tag: element.tagName, className: element.className, left: Math.round(element.getBoundingClientRect().left), right: Math.round(element.getBoundingClientRect().right), scrollWidth: element.scrollWidth }))
    }));
    assert(reflows.fits, `${label}: 320px/200% RTL reflow ${JSON.stringify(reflows)}`);
    assert.equal(await page.locator(".pk-form-wizard__step-button").first().evaluate(element => getComputedStyle(element).transitionDuration), "0s");
    assertNoErrors(label, "reflow");
    if (engine === "chromium") {
      await page.screenshot({ path: resolve(evidence, `${engine}-${profile.name}.png`) });
      assertNoErrors(label, "screenshot");
    }
    results.push({ engine, profile: profile.name, actions: "passed", lookups: "passed", modeler: "passed", localizationManagement: "passed", validation: "passed", keyboardRtl: "passed", localization: "passed", axe: "passed", touch: "passed", reflow: "passed", csp: "passed" });
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
