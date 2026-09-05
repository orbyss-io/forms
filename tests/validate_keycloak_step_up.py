from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.parse
import uuid
from pathlib import Path

import validate_keycloak_advanced_browser as advanced
import validate_spa_browser_flow as spa


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "extensions/program-kit-dotnet/templates/dotnet"
FLOW = "program-kit-step-up"
AUTH_FLOW = "program-kit-step-up-auth"
LOW_FLOW = "program-kit-step-up-loa-1"
HIGH_FLOW = "program-kit-step-up-loa-2"


def render_realm(path: Path, spa_origin: str, identity_origin: str) -> None:
    advanced.render_realm(path, spa_origin, identity_origin)
    realm = json.loads(path.read_text(encoding="utf-8"))
    realm.setdefault("attributes", {})["acr.loa.map"] = json.dumps(
        {"urn:program-kit:loa:1": 1, "urn:program-kit:loa:2": 2}, separators=(",", ":")
    )
    path.write_text(json.dumps(realm, indent=2) + "\n", encoding="utf-8")


def flow_executions(identity_origin: str, token: str, flow: str) -> list[dict]:
    result = advanced.admin_request(
        identity_origin,
        token,
        "GET",
        f"authentication/flows/{urllib.parse.quote(flow, safe='')}/executions",
    )
    if not isinstance(result, list):
        raise AssertionError(f"Keycloak did not return executions for {flow}")
    return result


def set_requirement(
    identity_origin: str,
    token: str,
    flow: str,
    requirement: str,
    *,
    provider: str | None = None,
    display_name: str | None = None,
) -> dict:
    matches = [
        item
        for item in flow_executions(identity_origin, token, flow)
        if (provider is None or item.get("providerId") == provider)
        and (display_name is None or item.get("displayName") == display_name)
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"Could not select {provider or display_name!r} in {flow}: "
            f"{[(item.get('displayName'), item.get('providerId')) for item in flow_executions(identity_origin, token, flow)]}"
        )
    execution = matches[0]
    execution["requirement"] = requirement
    advanced.admin_request(
        identity_origin,
        token,
        "PUT",
        f"authentication/flows/{urllib.parse.quote(flow, safe='')}/executions",
        execution,
    )
    return execution


def add_subflow(identity_origin: str, token: str, parent: str, alias: str) -> None:
    advanced.admin_request(
        identity_origin,
        token,
        "POST",
        f"authentication/flows/{urllib.parse.quote(parent, safe='')}/executions/flow",
        {
            "alias": alias,
            "description": "Program Kit advanced step-up acceptance",
            "provider": "basic-flow",
            "type": "basic-flow",
        },
    )


def add_execution(identity_origin: str, token: str, flow: str, provider: str) -> None:
    advanced.admin_request(
        identity_origin,
        token,
        "POST",
        f"authentication/flows/{urllib.parse.quote(flow, safe='')}/executions/execution",
        {"provider": provider},
    )


def configure_level(
    identity_origin: str,
    token: str,
    parent: str,
    flow: str,
    level: int,
    max_age: int,
    authenticator: str,
) -> None:
    add_subflow(identity_origin, token, parent, flow)
    set_requirement(identity_origin, token, parent, "CONDITIONAL", display_name=flow)
    add_execution(identity_origin, token, flow, "conditional-level-of-authentication")
    condition = set_requirement(
        identity_origin,
        token,
        flow,
        "REQUIRED",
        provider="conditional-level-of-authentication",
    )
    advanced.admin_request(
        identity_origin,
        token,
        "POST",
        f"authentication/executions/{condition['id']}/config",
        {
            "alias": f"Program Kit LoA {level}",
            "config": {
                "loa-condition-level": str(level),
                "loa-max-age": str(max_age),
            },
        },
    )
    add_execution(identity_origin, token, flow, authenticator)
    set_requirement(identity_origin, token, flow, "REQUIRED", provider=authenticator)


def configure_step_up(identity_origin: str) -> None:
    token = advanced.admin_token(identity_origin)
    advanced.admin_request(
        identity_origin,
        token,
        "POST",
        "authentication/flows",
        {
            "alias": FLOW,
            "description": "Program Kit advanced step-up acceptance",
            "providerId": "basic-flow",
            "topLevel": True,
            "builtIn": False,
        },
    )
    add_execution(identity_origin, token, FLOW, "auth-cookie")
    set_requirement(identity_origin, token, FLOW, "ALTERNATIVE", provider="auth-cookie")
    add_subflow(identity_origin, token, FLOW, AUTH_FLOW)
    set_requirement(identity_origin, token, FLOW, "ALTERNATIVE", display_name=AUTH_FLOW)
    configure_level(
        identity_origin, token, AUTH_FLOW, LOW_FLOW, 1, 36000, "auth-username-password-form"
    )
    configure_level(identity_origin, token, AUTH_FLOW, HIGH_FLOW, 2, 0, "auth-otp-form")

    token = advanced.admin_token(identity_origin)
    flows = advanced.admin_request(identity_origin, token, "GET", "authentication/flows")
    matches = [item for item in flows if item.get("alias") == FLOW] if isinstance(flows, list) else []
    if len(matches) != 1:
        raise AssertionError(f"Could not resolve the created step-up flow: {flows}")
    clients = advanced.admin_request(
        identity_origin,
        token,
        "GET",
        "clients?" + urllib.parse.urlencode({"clientId": "program-kit-spa"}),
    )
    if not isinstance(clients, list) or len(clients) != 1:
        raise AssertionError(f"Could not resolve program-kit-spa: {clients}")
    client = clients[0]
    client["authenticationFlowBindingOverrides"] = {"browser": matches[0]["id"]}
    advanced.admin_request(
        identity_origin, token, "PUT", f"clients/{client['id']}", client
    )

    actions = advanced.admin_request(
        identity_origin, token, "GET", "authentication/required-actions"
    )
    if not isinstance(actions, list):
        raise AssertionError("Keycloak did not return required actions")
    otp = advanced.enable_required_action(actions, identity_origin, token, "configure_totp")
    advanced.assign_required_actions(identity_origin, token, "local-mfa", [otp])


def write_browser_flow(path: Path) -> None:
    path.write_text(
        r"""
import { createHash, createHmac, randomBytes } from 'node:crypto';
import { chromium } from 'playwright';

const spaOrigin = process.env.PROGRAM_KIT_SPA_ORIGIN;
const identityOrigin = process.env.PROGRAM_KIT_IDENTITY_ORIGIN;
const encode = value => Buffer.from(value).toString('base64url');
const decode = token => JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString('utf8'));

function base32(value) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const character of value.replace(/\s+/g, '').replace(/=+$/, '').toUpperCase()) {
    const index = alphabet.indexOf(character);
    if (index < 0) throw new Error(`Invalid TOTP base32 character: ${character}`);
    bits += index.toString(2).padStart(5, '0');
  }
  const bytes = [];
  for (let index = 0; index + 8 <= bits.length; index += 8) bytes.push(parseInt(bits.slice(index, index + 8), 2));
  return Buffer.from(bytes);
}

function totp(secret, timestamp = Date.now()) {
  const counter = Math.floor(timestamp / 30000);
  const message = Buffer.alloc(8);
  message.writeBigUInt64BE(BigInt(counter));
  const digest = createHmac('sha1', base32(secret)).update(message).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  return ((digest.readUInt32BE(offset) & 0x7fffffff) % 1000000).toString().padStart(6, '0');
}

async function expectTheme(page, screen) {
  await page.waitForFunction(() => getComputedStyle(document.documentElement)
    .getPropertyValue('--program-kit-theme-contract').trim() === 'program-kit-theme-v1', null, { timeout: 10000 }).catch(() => {});
  const marker = await page.evaluate(() => getComputedStyle(document.documentElement)
    .getPropertyValue('--program-kit-theme-contract').trim());
  if (marker !== 'program-kit-theme-v1') throw new Error(`Theme missing on ${screen}: ${page.url()}`);
}

async function begin(page, acr) {
  const verifier = encode(randomBytes(48));
  const challenge = encode(createHash('sha256').update(verifier).digest());
  const state = encode(randomBytes(24));
  const authorize = new URL(identityOrigin + '/realms/program-kit/protocol/openid-connect/auth');
  const parameters = {
    client_id: 'program-kit-spa', redirect_uri: spaOrigin + '/auth/callback', response_type: 'code',
    response_mode: 'query', scope: 'openid profile program-kit-api', code_challenge: challenge,
    code_challenge_method: 'S256', state, nonce: encode(randomBytes(24)),
  };
  if (acr) parameters.claims = JSON.stringify({ id_token: { acr: { essential: true, values: [acr] } } });
  authorize.search = new URLSearchParams(parameters);
  await page.goto(authorize.toString());
  if (!page.url().startsWith(spaOrigin + '/auth/callback')) await expectTheme(page, `step-up ${acr || 'baseline'}`);
  return { verifier, state };
}

async function exchange(page, started) {
  await page.waitForURL(spaOrigin + '/auth/callback**');
  const callback = new URL(page.url());
  if (callback.searchParams.get('state') !== started.state) throw new Error('Step-up callback state mismatch.');
  const response = await page.evaluate(async ({ endpoint, body }) => {
    const result = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(body) });
    return { status: result.status, body: await result.json() };
  }, { endpoint: identityOrigin + '/realms/program-kit/protocol/openid-connect/token', body: {
    grant_type: 'authorization_code', client_id: 'program-kit-spa', redirect_uri: spaOrigin + '/auth/callback',
    code: callback.searchParams.get('code'), code_verifier: started.verifier,
  }});
  if (response.status !== 200 || !response.body.id_token) throw new Error(`Step-up exchange failed: ${JSON.stringify(response)}`);
  return response.body;
}

const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext();
  try {
    const page = await context.newPage();
    const low = await begin(page, 'urn:program-kit:loa:1');
    await page.locator('#username').fill('local-mfa');
    await page.locator('#password').fill('local-mfa-only');
    await page.locator('#kc-login').click();
    await page.locator('#mode-manual').click();
    await page.locator('#kc-totp-secret-key').waitFor();
    const secret = (await page.locator('#kc-totp-secret-key').innerText()).replace(/\s+/g, '');
    const label = page.locator('#userLabel');
    if (await label.count()) await label.fill('Program Kit step-up authenticator');
    await page.locator('#totp').fill(totp(secret));
    await page.locator('#saveTOTPBtn').click();
    const lowTokens = await exchange(page, low);
    if (decode(lowTokens.id_token).acr !== 'urn:program-kit:loa:1') throw new Error(`Expected low ACR, got ${decode(lowTokens.id_token).acr}`);

    const firstWait = 31000 - (Date.now() % 30000);
    await new Promise(resolve => setTimeout(resolve, firstWait));
    const high = await begin(page, 'urn:program-kit:loa:2');
    await page.locator('#otp').waitFor();
    if (await page.locator('#username').count()) throw new Error('Step-up unnecessarily requested the first factor again.');
    await page.locator('#otp').fill('000000');
    await page.locator('#kc-login').click();
    await page.locator('#otp').waitFor();
    await page.locator('#otp').fill(totp(secret));
    await page.locator('#kc-login').click();
    const highTokens = await exchange(page, high);
    if (decode(highTokens.id_token).acr !== 'urn:program-kit:loa:2') throw new Error(`Expected high ACR, got ${decode(highTokens.id_token).acr}`);

    const wait = 31000 - (Date.now() % 30000);
    await new Promise(resolve => setTimeout(resolve, wait));
    const repeat = await begin(page, 'urn:program-kit:loa:2');
    await page.locator('#otp').waitFor();
    await page.locator('#otp').fill(totp(secret));
    await page.locator('#kc-login').click();
    const repeatedTokens = await exchange(page, repeat);
    if (decode(repeatedTokens.id_token).acr !== 'urn:program-kit:loa:2') throw new Error('Repeated max-age-zero step-up lost its high ACR.');

    const unknown = await begin(page, 'urn:program-kit:loa:99');
    if (page.url().startsWith(spaOrigin + '/auth/callback')) {
      const rejected = new URL(page.url());
      if (!rejected.searchParams.get('error') || rejected.searchParams.get('code')) throw new Error(`Unknown essential ACR was not rejected: ${page.url()}`);
      if (rejected.searchParams.get('state') !== unknown.state) throw new Error('Rejected ACR callback state mismatch.');
    } else {
      const text = (await page.locator('body').innerText()).toLowerCase();
      if (!text.includes('invalid') && !text.includes('acr') && !text.includes('request')) {
        throw new Error(`Unknown essential ACR did not produce a protocol error: ${page.url()} ${text.slice(0, 1000)}`);
      }
    }
  } finally {
    await context.close();
  }
} finally {
  await browser.close();
}
console.log('Chromium completed low-to-high ACR step-up, forced repeat, and unknown-ACR rejection.');
""".lstrip(),
        encoding="utf-8",
    )


def main() -> int:
    missing = [command for command in ("docker", "node", "npm") if shutil.which(command) is None]
    if missing:
        raise AssertionError("Step-up acceptance requires: " + ", ".join(missing))
    spa_port = spa.free_port()
    identity_port = spa.free_port()
    health_port = spa.free_port()
    spa_origin = f"http://localhost:{spa_port}"
    identity_origin = f"http://localhost:{identity_port}"
    container = f"program-kit-step-up-{uuid.uuid4().hex[:8]}"
    server = None
    with tempfile.TemporaryDirectory(prefix="program-kit-step-up-") as value:
        fixture = Path(value)
        realm = fixture / "program-kit-realm.json"
        render_realm(realm, spa_origin, identity_origin)
        started = subprocess.run(
            [
                "docker", "run", "--detach", "--name", container,
                "--publish", f"127.0.0.1:{identity_port}:8080",
                "--publish", f"127.0.0.1:{health_port}:9000",
                "--env", "KC_BOOTSTRAP_ADMIN_USERNAME=fixture-admin",
                "--env", "KC_BOOTSTRAP_ADMIN_PASSWORD=ephemeral-advanced-only",
                "--env", f"KC_HOSTNAME={identity_origin}",
                "--volume", f"{realm.resolve()}:/opt/keycloak/data/import/program-kit-realm.json:ro",
                "--volume", f"{(TEMPLATE / 'web-profiles/common/deploy/keycloak/themes').resolve()}:/opt/keycloak/themes:ro",
                spa.image_reference(), "start-dev", "--import-realm", "--health-enabled=true",
            ],
            capture_output=True,
            text=True,
        )
        if started.returncode != 0:
            raise AssertionError(f"Could not start step-up Keycloak fixture: {started.stderr}")
        try:
            spa.wait_keycloak(container, health_port)
            configure_step_up(identity_origin)
            spa_root = fixture / "spa"
            spa_root.mkdir()
            server, _ = spa.start_spa(spa_root, spa_port)
            browser_root = fixture / "browser"
            browser_root.mkdir()
            spa.install_browser(browser_root, shutil.which("npm") or "npm")
            flow = browser_root / "step-up-flow.mjs"
            write_browser_flow(flow)
            environment = os.environ.copy()
            environment["PROGRAM_KIT_SPA_ORIGIN"] = spa_origin
            environment["PROGRAM_KIT_IDENTITY_ORIGIN"] = identity_origin
            spa.run(["node", str(flow)], browser_root, environment, timeout=240)
        except Exception as error:
            logs = subprocess.run(
                ["docker", "logs", container], capture_output=True, text=True, check=False
            )
            raise AssertionError(f"{error}\nKeycloak output:\n{logs.stdout[-16000:]}{logs.stderr[-16000:]}") from error
        finally:
            if server is not None:
                server.shutdown()
                server.server_close()
            subprocess.run(["docker", "rm", "--force", container], capture_output=True, check=False)
    print("Real Chromium completed Keycloak step-up authentication acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
