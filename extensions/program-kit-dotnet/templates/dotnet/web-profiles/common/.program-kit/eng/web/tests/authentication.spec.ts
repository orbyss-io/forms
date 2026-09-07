import { expect, type Browser, type BrowserContext, type Page, test } from '@playwright/test';
import { personas } from '../persona-fixture.js';

async function authenticatedContext(
  browser: Browser,
  baseURL: string,
  persona: (typeof personas)[keyof typeof personas],
): Promise<BrowserContext> {
  const context = await browser.newContext({ baseURL });
  const page = await context.newPage();
  await page.goto('/bff/login?returnUrl=/');
  await page.locator('#username').fill(persona.username);
  await page.locator('#password').fill(persona.password);
  await page.locator('#kc-login').click();
  await page.waitForURL(`${baseURL}/`);
  const session = await context.request.get('/bff/user');
  expect(session.ok()).toBeTruthy();
  expect(await session.json()).toMatchObject({ authenticated: true });
  return context;
}

async function submitLogoutForm(page: Page): Promise<Page> {
  const token = await page.evaluate(async () => {
    const response = await fetch('/bff/antiforgery', { credentials: 'same-origin', cache: 'no-store' });
    if (!response.ok) throw new Error('Could not obtain the BFF antiforgery token.');
    return await response.json() as {
      headerName: string;
      formFieldName: string;
      requestToken: string;
    };
  });
  expect(token).toMatchObject({
    headerName: 'X-CSRF-TOKEN',
    formFieldName: '__RequestVerificationToken',
  });
  const popup = page.waitForEvent('popup');
  await page.evaluate(({ formFieldName, requestToken }) => {
    const target = 'program-kit-provider-logout';
    window.open('about:blank', target);
    const form = document.createElement('form');
    form.method = 'post';
    form.action = '/bff/logout';
    form.target = target;
    const field = document.createElement('input');
    field.type = 'hidden';
    field.name = formFieldName;
    field.value = requestToken;
    form.append(field);
    document.body.append(form);
    form.submit();
    form.remove();
  }, token);
  return await popup;
}

test('anonymous browser has no BFF session', async ({ request }) => {
  const response = await request.get('/bff/user');
  expect(response.ok()).toBeTruthy();
  expect(await response.json()).toEqual({ authenticated: false });
});

test('WEB-V3 same-origin BFF response has the governed browser headers', async ({ request }) => {
  const response = await request.get('/bff/user');
  expect(response.headers()['content-security-policy']).toContain("frame-ancestors 'none'");
  expect(response.headers()['x-frame-options']).toBe('DENY');
  expect(response.headers()['referrer-policy']).toBe('no-referrer');
  expect(response.headers()['permissions-policy']).toContain('camera=()');
  expect(response.headers()['x-content-type-options']).toBe('nosniff');
});

test('real browser form logout clears local state and completes provider navigation', async ({ browser, baseURL }) => {
  if (!baseURL) throw new Error('Playwright baseURL is required.');
  const context = await authenticatedContext(browser, baseURL, personas.user);
  const page = await context.newPage();
  await page.reload();
  expect(await (await context.request.get('/bff/user')).json()).toMatchObject({ authenticated: true });

  const providerWindow = await submitLogoutForm(page);
  await expect.poll(async () => await (await context.request.get('/bff/user')).json()).toEqual({ authenticated: false });
  await providerWindow.waitForURL(`${baseURL}/bff/signed-out`);
  await page.goto('/bff/signed-out?remote=pending');
  expect(await page.locator('body').innerText()).toContain('"signedOut":true');
  await providerWindow.close();
  await context.close();
});

test('missing or invalid browser antiforgery logout does not clear the session', async ({ browser, baseURL }) => {
  if (!baseURL) throw new Error('Playwright baseURL is required.');
  const context = await authenticatedContext(browser, baseURL, personas.user);
  const page = await context.newPage();
  const outcomes = await page.evaluate(async () => {
    const missing = await fetch('/bff/logout', { method: 'POST', redirect: 'error' });
    const invalid = await fetch('/bff/logout', {
      method: 'POST',
      headers: { 'X-CSRF-TOKEN': 'invalid' },
      redirect: 'error',
    });
    return [
      { status: missing.status, body: await missing.json() },
      { status: invalid.status, body: await invalid.json() },
    ];
  });
  for (const outcome of outcomes) {
    expect(outcome.status).toBe(400);
    expect(outcome.body).toMatchObject({ code: 'invalid_antiforgery_token' });
  }
  expect(await (await context.request.get('/bff/user')).json()).toMatchObject({ authenticated: true });
  await context.close();
});

test('cross-site top-level logout form fails before session mutation', async ({ browser, baseURL }) => {
  if (!baseURL) throw new Error('Playwright baseURL is required.');
  const context = await authenticatedContext(browser, baseURL, personas.user);
  const attacker = await context.newPage();
  await attacker.goto('http://localhost:8080/realms/program-kit/.well-known/openid-configuration');
  await attacker.evaluate(applicationOrigin => {
    const form = document.createElement('form');
    form.method = 'post';
    form.action = `${applicationOrigin}/bff/logout`;
    document.body.append(form);
    form.submit();
  }, baseURL);
  await attacker.waitForURL(`${baseURL}/bff/logout`);
  expect(await attacker.locator('body').innerText()).toContain('invalid_antiforgery_token');
  expect(await (await context.request.get('/bff/user')).json()).toMatchObject({ authenticated: true });
  await context.close();
});

test('provider navigation failure cannot restore local access or displace the signed-out page', async ({ browser, baseURL }) => {
  if (!baseURL) throw new Error('Playwright baseURL is required.');
  const context = await authenticatedContext(browser, baseURL, personas.user);
  await context.route('http://localhost:8080/**', route => route.abort());
  const page = await context.newPage();
  const providerWindow = await submitLogoutForm(page);
  await expect.poll(async () => await (await context.request.get('/bff/user')).json()).toEqual({ authenticated: false });
  await page.goto('/bff/signed-out?remote=unavailable');
  expect(await page.locator('body').innerText()).toContain('"signedOut":true');
  await providerWindow.close();
  await context.close();
});

test('configured permission endpoint distinguishes authorized and unauthorized users', async ({ browser, baseURL }) => {
  test.skip(!process.env.PROGRAMKIT_PERMISSION_PROBE_PATH, 'Set PROGRAMKIT_PERMISSION_PROBE_PATH when the first protected slice is mapped.');
  if (!baseURL) throw new Error('Playwright baseURL is required.');
  const path = process.env.PROGRAMKIT_PERMISSION_PROBE_PATH!;
  const authorized = await authenticatedContext(browser, baseURL, personas.admin);
  const authorizedResponse = await authorized.request.get(path);
  expect(authorizedResponse.ok()).toBeTruthy();
  await authorized.close();
  const denied = await authenticatedContext(browser, baseURL, personas.wrongRole);
  const deniedResponse = await denied.request.get(path);
  expect(deniedResponse.status()).toBe(403);
  await denied.close();
});
