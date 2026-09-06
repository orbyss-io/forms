import assert from 'node:assert/strict';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium, firefox, webkit } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const manifest = JSON.parse(await readFile(resolve(root, 'publication.json'), 'utf8'));
const resources = new Map(manifest.resources.map(r => [r.route, r]));
resources.set('/__tailwind.css', { file: 'acceptance/tailwind-compiled.css', contentType: 'text/css; charset=utf-8' });
const archetypes = ['journey', 'product-shell', 'workspace', 'content-hub', 'showcase'];
for (const name of archetypes) resources.set(`/__gallery/${name}`, { file: `acceptance/archetypes/${name}.html`, contentType: 'text/html; charset=utf-8' });
const server = createServer(async (request, response) => {
  const route = new URL(request.url, 'http://127.0.0.1').pathname;
  const resource = resources.get(route);
  if (!resource) { response.writeHead(404); response.end(); return; }
  try { response.setHeader('Content-Type', resource.contentType); response.end(await readFile(resolve(root, resource.file))); }
  catch { response.writeHead(500); response.end('Fixture read failed'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const results = [], errors = [];
const evidence = resolve(root, 'acceptance/browser-evidence');
await mkdir(evidence, { recursive: true });

const engines = [
  { name: 'chromium', browserType: chromium },
  { name: 'webkit', browserType: webkit },
  { name: 'firefox', browserType: firefox },
];
const deviceProfiles = [
  { name: 'phone-portrait', engine: 'chromium', viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true },
  { name: 'phone-landscape', engine: 'chromium', viewport: { width: 844, height: 390 }, deviceScaleFactor: 3, isMobile: true },
  { name: 'tablet-portrait', engine: 'webkit', viewport: { width: 768, height: 1024 }, deviceScaleFactor: 2, isMobile: true },
  { name: 'tablet-landscape', engine: 'webkit', viewport: { width: 1024, height: 768 }, deviceScaleFactor: 2, isMobile: true },
];

async function securePage(page, label) {
  page.on('pageerror', error => errors.push(`${label}: ${error.message}`));
  await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
}

async function assertNoPageOverflow(page, label) {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${label} page overflow`);
}

async function verifyDesktop(engine, browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'en-US', timezoneId: 'UTC' });
  const page = await context.newPage();
  await securePage(page, engine);
  try {
    if (engine === 'chromium') {
      // Verify consumer public documents really expose their content before JavaScript executes.
      for (const resource of manifest.resources.filter(r => r.contentType.startsWith('text/html'))) {
        const response = await context.request.get(origin + resource.route);
        assert.equal(response.status(), 200);
        const raw = await response.text();
        assert(raw.includes('<h1') && raw.includes('rel="canonical"') && raw.includes('application/ld+json'));
      }
    }
    for (const archetype of archetypes) {
      for (const scheme of ['light', 'dark']) {
        const label = `${engine}/${archetype}/${scheme}`;
        await page.emulateMedia({ colorScheme: scheme, reducedMotion: 'reduce', forcedColors: 'none' });
        await page.setViewportSize({ width: 1440, height: 1000 });
        await page.goto(`${origin}/__gallery/${archetype}`);
        await page.getByRole('heading', { level: 1 }).waitFor();
        await assertNoPageOverflow(page, label);
        const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
        assert.deepEqual(axe.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) })), [], `${label} accessibility`);
        await page.keyboard.press('Tab');
        await assert.doesNotReject(() => page.getByRole('link', { name: 'Skip to content' }).waitFor());
        assert.equal(await page.evaluate(() => document.activeElement.textContent), 'Skip to content');
        const opener = page.getByRole('button', { name: 'Open confirmation' });
        await opener.focus(); await page.keyboard.press('Enter');
        assert.equal(await page.locator('dialog').evaluate(d => d.open), true);
        assert.equal(await page.evaluate(() => document.activeElement.textContent), 'Cancel');
        await page.keyboard.press('Tab');
        assert.equal(await page.evaluate(() => document.activeElement.closest('dialog') !== null), true);
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('dialog').evaluate(d => d.open), false);
        assert.equal(await page.evaluate(() => document.activeElement.textContent), 'Open confirmation');
        await page.screenshot({ path: resolve(evidence, `${engine}-${archetype}-${scheme}.png`), fullPage: true, animations: 'disabled' });
        // Narrow viewport plus doubled root text is a reflow approximation, not actual browser zoom certification.
        await page.setViewportSize({ width: 320, height: 900 });
        await page.evaluate(() => { document.documentElement.dir = 'rtl'; document.documentElement.style.fontSize = '200%'; });
        await assertNoPageOverflow(page, `${label}/rtl-200-percent`);
        const target = await opener.boundingBox();
        assert(target.height >= 44 && target.width >= 44, `${label} touch target`);
        if (engine === 'chromium') {
          await page.emulateMedia({ forcedColors: 'active' });
          await opener.focus();
          assert.equal(await opener.evaluate(el => getComputedStyle(el).transitionDuration), '0s');
          assert.notEqual(await opener.evaluate(el => getComputedStyle(el).outlineStyle), 'none');
        }
        results.push({ engine, archetype, scheme, axe: 'passed', keyboard: 'passed', reflowRtl: 'passed', reducedMotion: 'passed', forcedColors: engine === 'chromium' ? 'passed' : 'not-emulated' });
      }
    }
    if (engine === 'chromium') {
      await page.goto(`${origin}/__gallery/product-shell`);
      await page.emulateMedia({ colorScheme: 'light', forcedColors: 'none' });
      await page.addStyleTag({ url: origin + '/__tailwind.css' });
      await page.evaluate(() => {
        const sample = document.createElement('div'); sample.id = 'tailwind-bridge';
        sample.className = 'bg-primary text-on-primary rounded-brand font-sans'; sample.textContent = 'Tailwind bridge';
        document.querySelector('main').append(sample);
      });
      for (const colorScheme of ['light', 'dark']) {
        await page.emulateMedia({ colorScheme });
        const colors = await page.evaluate(() => {
          const native = getComputedStyle(document.querySelector('[data-pk-dialog]'));
          const utility = getComputedStyle(document.getElementById('tailwind-bridge'));
          return { native: [native.color, native.backgroundColor, native.borderRadius], utility: [utility.color, utility.backgroundColor, utility.borderRadius] };
        });
        assert.deepEqual(colors.utility, colors.native, `Tailwind/native ${colorScheme} semantic parity`);
      }
    }
  } finally {
    await context.close();
  }
}

async function verifyTouchDevice(profile, browser) {
  const context = await browser.newContext({
    viewport: profile.viewport,
    screen: profile.viewport,
    deviceScaleFactor: profile.deviceScaleFactor,
    hasTouch: true,
    isMobile: profile.isMobile,
    locale: 'en-US',
    timezoneId: 'UTC',
  });
  const page = await context.newPage();
  await securePage(page, profile.name);
  try {
    for (const archetype of archetypes) {
      const label = `${profile.engine}/${profile.name}/${archetype}`;
      await page.emulateMedia({ colorScheme: 'light', reducedMotion: 'reduce' });
      await page.goto(`${origin}/__gallery/${archetype}`);
      await page.getByRole('heading', { level: 1 }).waitFor();
      await assertNoPageOverflow(page, label);
      const opener = page.getByRole('button', { name: 'Open confirmation' });
      const target = await opener.boundingBox();
      assert(target.height >= 44 && target.width >= 44, `${label} touch target`);
      await opener.tap();
      assert.equal(await page.locator('dialog').evaluate(d => d.open), true);
      await page.getByRole('button', { name: 'Cancel' }).tap();
      assert.equal(await page.locator('dialog').evaluate(d => d.open), false);
      await page.screenshot({ path: resolve(evidence, `${profile.engine}-${profile.name}-${archetype}.png`), fullPage: true, animations: 'disabled' });
      results.push({ engine: profile.engine, device: profile.name, archetype, touch: 'passed', sizing: 'passed', orientation: profile.name.endsWith('landscape') ? 'landscape' : 'portrait' });
    }
  } finally {
    await context.close();
  }
}

try {
  for (const { name, browserType } of engines) {
    const browser = await browserType.launch();
    try {
      await verifyDesktop(name, browser);
      for (const profile of deviceProfiles.filter(candidate => candidate.engine === name)) {
        await verifyTouchDevice(profile, browser);
      }
    } finally {
      await browser.close();
    }
  }
  assert.deepEqual(errors, []);
} finally {
  await new Promise(resolve => server.close(resolve));
  await writeFile(resolve(evidence, 'report.json'), JSON.stringify({ results, errors,
    scope: 'Chromium/Firefox/WebKit desktop plus emulated touch phone/tablet fixture checks; not full WCAG certification, physical-device/virtual-keyboard proof, actual browser zoom, assistive-technology task acceptance, or production field performance.' }, null, 2));
}
console.log(`UI browser acceptance passed: ${results.length} engine/archetype/device combinations.`);
