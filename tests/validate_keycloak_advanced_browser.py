from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import validate_spa_browser_flow as spa


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "extensions/program-kit-dotnet/templates/dotnet"


def render_realm(path: Path, spa_origin: str, identity_origin: str) -> None:
    spa.render_realm(path, spa_origin, "http://localhost:5000", identity_origin)
    realm = json.loads(path.read_text(encoding="utf-8"))
    realm.update(
        {
            "webAuthnPolicyPasswordlessRpEntityName": "Program Kit Acceptance",
            "webAuthnPolicyPasswordlessRpId": "localhost",
            "webAuthnPolicyPasswordlessSignatureAlgorithms": ["ES256"],
            "webAuthnPolicyPasswordlessAttestationConveyancePreference": "none",
            "webAuthnPolicyPasswordlessAuthenticatorAttachment": "platform",
            "webAuthnPolicyPasswordlessResidentKey": "required",
            "webAuthnPolicyPasswordlessUserVerificationRequirement": "required",
            "webAuthnPolicyPasswordlessAvoidSameAuthenticatorRegister": True,
            "webAuthnPolicyPasswordlessPasskeysEnabled": True,
            "webAuthnPolicyPasswordlessMediation": "conditional",
        }
    )
    realm["users"].extend(
        [
            {
                "username": "local-mfa",
                "enabled": True,
                "emailVerified": True,
                "firstName": "Local",
                "lastName": "MFA",
                "email": "local-mfa@example.test",
                "credentials": [
                    {"type": "password", "value": "local-mfa-only", "temporary": False}
                ],
                "realmRoles": ["user"],
            },
            {
                "username": "local-passkey",
                "enabled": True,
                "emailVerified": True,
                "firstName": "Local",
                "lastName": "Passkey",
                "email": "local-passkey@example.test",
                "credentials": [
                    {"type": "password", "value": "local-passkey-only", "temporary": False}
                ],
                "realmRoles": ["user"],
            },
            {
                "username": "local-recovery",
                "enabled": True,
                "emailVerified": True,
                "firstName": "Local",
                "lastName": "Recovery",
                "email": "local-recovery@example.test",
                "credentials": [
                    {"type": "password", "value": "local-recovery-only", "temporary": False}
                ],
                "realmRoles": ["user"],
            },
        ]
    )
    path.write_text(json.dumps(realm, indent=2) + "\n", encoding="utf-8")


def admin_token(identity_origin: str) -> str:
    request = urllib.request.Request(
        f"{identity_origin}/realms/master/protocol/openid-connect/token",
        data=urllib.parse.urlencode(
            {
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": "fixture-admin",
                "password": "ephemeral-advanced-only",
            }
        ).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read())["access_token"]


def admin_request(
    identity_origin: str,
    token: str,
    method: str,
    path: str,
    body: object | None = None,
) -> object:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{identity_origin}/admin/realms/program-kit/{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        content = response.read()
        return json.loads(content) if content else {}


def enable_required_action(actions: list[dict], identity_origin: str, token: str, match: str) -> str:
    candidates = [
        action
        for action in actions
        if match in f"{action.get('alias', '')} {action.get('providerId', '')}".casefold()
    ]
    if len(candidates) != 1:
        available = [f"{item.get('alias')}:{item.get('providerId')}" for item in actions]
        raise AssertionError(f"Could not select required action {match!r}: {available}")
    action = candidates[0]
    action["enabled"] = True
    alias = str(action["alias"])
    admin_request(
        identity_origin,
        token,
        "PUT",
        f"authentication/required-actions/{urllib.parse.quote(alias, safe='')}",
        action,
    )
    return alias


def assign_required_actions(
    identity_origin: str, token: str, username: str, actions: list[str]
) -> None:
    query = urllib.parse.urlencode({"username": username, "exact": "true"})
    users = admin_request(identity_origin, token, "GET", f"users?{query}")
    if not isinstance(users, list) or len(users) != 1:
        raise AssertionError(f"Could not resolve imported advanced persona {username}: {users}")
    user = users[0]
    admin_request(
        identity_origin,
        token,
        "PUT",
        f"users/{user['id']}",
        {"requiredActions": actions},
    )
    updated = admin_request(identity_origin, token, "GET", f"users/{user['id']}")
    if not isinstance(updated, dict) or updated.get("requiredActions") != actions:
        raise AssertionError(
            f"Keycloak did not persist required actions {actions!r} for {username}: {updated}"
        )


def enable_browser_authenticator(
    identity_origin: str, token: str, authenticator: str
) -> None:
    executions = admin_request(
        identity_origin, token, "GET", "authentication/flows/browser/executions"
    )
    if not isinstance(executions, list):
        raise AssertionError("Keycloak did not return browser-flow executions")
    matches = [item for item in executions if item.get("providerId") == authenticator]
    if len(matches) != 1:
        available = [item.get("providerId") for item in executions]
        raise AssertionError(
            f"Could not resolve browser authenticator {authenticator!r}: {available}"
        )
    execution = matches[0]
    execution["requirement"] = "ALTERNATIVE"
    admin_request(
        identity_origin,
        token,
        "PUT",
        "authentication/flows/browser/executions",
        execution,
    )


def configure_required_actions(identity_origin: str) -> None:
    token = admin_token(identity_origin)
    actions = admin_request(identity_origin, token, "GET", "authentication/required-actions")
    if not isinstance(actions, list):
        raise AssertionError("Keycloak did not return its required-action catalog")
    otp = enable_required_action(actions, identity_origin, token, "configure_totp")
    recovery = enable_required_action(
        actions, identity_origin, token, "configure_recovery_authn_codes"
    )
    passkey = enable_required_action(actions, identity_origin, token, "webauthn-register-passwordless")
    enable_browser_authenticator(identity_origin, token, "auth-recovery-authn-code-form")
    assign_required_actions(identity_origin, token, "local-mfa", [otp])
    assign_required_actions(identity_origin, token, "local-passkey", [passkey])
    assign_required_actions(identity_origin, token, "local-recovery", [otp, recovery])


def write_browser_flow(path: Path) -> None:
    path.write_text(
        r"""
import { createHash, createHmac, randomBytes } from 'node:crypto';
import { chromium } from 'playwright';

const spaOrigin = process.env.PROGRAM_KIT_SPA_ORIGIN;
const identityOrigin = process.env.PROGRAM_KIT_IDENTITY_ORIGIN;
const encode = value => Buffer.from(value).toString('base64url');
const decode = token => JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString('utf8'));
const passkeyOnly = process.argv.includes('--passkey-only');
const recoveryOnly = process.argv.includes('--recovery-only');

async function expectTheme(page, screen) {
  await page.waitForFunction(() => getComputedStyle(document.documentElement)
    .getPropertyValue('--program-kit-theme-contract').trim() === 'program-kit-theme-v1', null, { timeout: 10000 }).catch(() => {});
  const marker = await page.evaluate(() => getComputedStyle(document.documentElement)
    .getPropertyValue('--program-kit-theme-contract').trim());
  if (marker !== 'program-kit-theme-v1' && page.url().startsWith(spaOrigin + '/auth/callback')) return;
  if (marker !== 'program-kit-theme-v1') {
    throw new Error(`Theme missing on ${screen}: marker=${marker} url=${page.url()} title=${await page.title()} text=${(await page.locator('body').innerText()).slice(0, 1500)}`);
  }
}

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
  const value = (digest.readUInt32BE(offset) & 0x7fffffff) % 1000000;
  return value.toString().padStart(6, '0');
}

async function begin(page) {
  const verifier = encode(randomBytes(48));
  const challenge = encode(createHash('sha256').update(verifier).digest());
  const state = encode(randomBytes(24));
  const nonce = encode(randomBytes(24));
  const authorize = new URL(identityOrigin + '/realms/program-kit/protocol/openid-connect/auth');
  authorize.search = new URLSearchParams({
    client_id: 'program-kit-spa',
    redirect_uri: spaOrigin + '/auth/callback',
    response_type: 'code',
    response_mode: 'query',
    scope: 'openid profile program-kit-api',
    code_challenge: challenge,
    code_challenge_method: 'S256',
    state,
    nonce,
  });
  await page.goto(authorize.toString());
  if (!page.url().startsWith(spaOrigin + '/auth/callback')) await expectTheme(page, 'advanced login');
  return { verifier, state };
}

async function exchange(page, started) {
  await page.waitForURL(spaOrigin + '/auth/callback**');
  const callback = new URL(page.url());
  if (callback.searchParams.get('state') !== started.state) throw new Error('Advanced callback state mismatch.');
  const response = await page.evaluate(async ({ endpoint, body }) => {
    const result = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(body),
    });
    return { status: result.status, body: await result.json() };
  }, {
    endpoint: identityOrigin + '/realms/program-kit/protocol/openid-connect/token',
    body: {
      grant_type: 'authorization_code',
      client_id: 'program-kit-spa',
      redirect_uri: spaOrigin + '/auth/callback',
      code: callback.searchParams.get('code'),
      code_verifier: started.verifier,
    },
  });
  if (response.status !== 200 || !response.body.id_token) throw new Error(`Advanced exchange failed: ${JSON.stringify(response)}`);
  return response.body;
}

async function logout(page, tokens) {
  const endpoint = new URL(identityOrigin + '/realms/program-kit/protocol/openid-connect/logout');
  endpoint.search = new URLSearchParams({
    client_id: 'program-kit-spa',
    id_token_hint: tokens.id_token,
    post_logout_redirect_uri: spaOrigin + '/signed-out',
  });
  await page.goto(endpoint.toString());
  await page.waitForURL(spaOrigin + '/signed-out**');
}

async function passwordLogin(page, username, password) {
  const started = await begin(page);
  await page.locator('#username').fill(username);
  await page.locator('#password').fill(password);
  await page.locator('#kc-login').click();
  return started;
}

async function chooseRecoveryCode(page) {
  await page.locator('#try-another-way').waitFor();
  await page.locator('#try-another-way').click();
  const recovery = page.getByRole('button', { name: /recovery/i }).first();
  await recovery.waitFor();
  await recovery.click();
  await page.locator('#recoveryCodeInput').waitFor();
  await expectTheme(page, 'recovery-code challenge');
}

const browser = await chromium.launch({ headless: true });
try {
  if (!passkeyOnly && !recoveryOnly) {
  const mfa = await browser.newContext();
  try {
    const page = await mfa.newPage();
    const started = await begin(page);
    await page.locator('#username').fill('local-mfa');
    await page.locator('#password').fill('local-mfa-only');
    await page.locator('#kc-login').click();
    await page.locator('#mode-manual').click();
    try {
      await page.locator('#kc-totp-secret-key').waitFor({ timeout: 10000 });
    } catch {
      throw new Error(`TOTP enrollment was not presented. url=${page.url()} title=${await page.title()} text=${(await page.locator('body').innerText()).slice(0, 2000)}`);
    }
    await expectTheme(page, 'TOTP enrollment');
    const secret = (await page.locator('#kc-totp-secret-key').innerText()).replace(/\s+/g, '');
    const label = page.locator('#userLabel');
    if (await label.count()) await label.fill('Program Kit acceptance authenticator');
    await page.locator('#totp').fill(totp(secret));
    await page.locator('#saveTOTPBtn').click();
    const enrolled = await exchange(page, started);
    if (decode(enrolled.access_token).preferred_username !== 'local-mfa') throw new Error('TOTP enrollment returned the wrong subject.');
    await logout(page, enrolled);

    const wait = 31000 - (Date.now() % 30000);
    await new Promise(resolve => setTimeout(resolve, wait));
    const second = await begin(page);
    await page.locator('#username').fill('local-mfa');
    await page.locator('#password').fill('local-mfa-only');
    await page.locator('#kc-login').click();
    await page.locator('#otp').waitFor();
    await expectTheme(page, 'TOTP challenge');
    await page.locator('#otp').fill('000000');
    await page.locator('#kc-login').click();
    await page.locator('#otp').waitFor();
    await page.locator('#otp').fill(totp(secret));
    await page.locator('#kc-login').click();
    const authenticated = await exchange(page, second);
    if (decode(authenticated.access_token).preferred_username !== 'local-mfa') throw new Error('TOTP challenge returned the wrong subject.');
    await logout(page, authenticated);
  } finally {
    await mfa.close();
  }
  }

  if (!recoveryOnly) {
  const passkeys = await browser.newContext();
  try {
    const page = await passkeys.newPage();
    const cdp = await passkeys.newCDPSession(page);
    await cdp.send('WebAuthn.enable');
    await cdp.send('WebAuthn.addVirtualAuthenticator', {
      options: {
        protocol: 'ctap2',
        transport: 'internal',
        hasResidentKey: true,
        hasUserVerification: true,
        isUserVerified: true,
        automaticPresenceSimulation: true,
      },
    });
    const started = await begin(page);
    await page.locator('#username').fill('local-passkey');
    await page.locator('#password').fill('local-passkey-only');
    await page.locator('#kc-login').click();
    if (!page.url().startsWith(spaOrigin + '/auth/callback')) {
      await expectTheme(page, 'passkey enrollment');
      const register = page.locator('#registerWebAuthn, button:has-text("Register"), input[type="submit"]').first();
      if (await register.count()) await register.click();
    }
    const label = page.locator('input[name="userLabel"], #userLabel').first();
    if (await label.count()) {
      await label.fill('Program Kit virtual passkey');
      await page.locator('button[type="submit"], input[type="submit"]').first().click();
    }
    const enrolled = await exchange(page, started);
    if (decode(enrolled.access_token).preferred_username !== 'local-passkey') throw new Error('Passkey enrollment returned the wrong subject.');
    await logout(page, enrolled);

    const passwordless = await begin(page);
    try {
      await page.waitForURL(spaOrigin + '/auth/callback**', { timeout: 10000 });
    } catch {
      const button = page.getByRole('button', { name: /passkey/i }).first();
      if (await button.count()) await button.click();
    }
    const authenticated = await exchange(page, passwordless);
    if (decode(authenticated.access_token).preferred_username !== 'local-passkey') throw new Error('Passwordless sign-in returned the wrong subject.');
    await logout(page, authenticated);
  } finally {
    await passkeys.close();
  }
  }

  if (!passkeyOnly) {
  const recovery = await browser.newContext();
  try {
    const page = await recovery.newPage();
    const started = await passwordLogin(page, 'local-recovery', 'local-recovery-only');
    await page.locator('#mode-manual').click();
    await page.locator('#kc-totp-secret-key').waitFor();
    await expectTheme(page, 'recovery TOTP enrollment');
    const secret = (await page.locator('#kc-totp-secret-key').innerText()).replace(/\s+/g, '');
    const label = page.locator('#userLabel');
    if (await label.count()) await label.fill('Program Kit recovery authenticator');
    await page.locator('#totp').fill(totp(secret));
    await page.locator('#saveTOTPBtn').click();

    await page.locator('#kc-recovery-codes-list').waitFor();
    await expectTheme(page, 'recovery-code enrollment');
    const codes = await page.locator('#kc-recovery-codes-list li').allInnerTexts();
    const normalized = codes.map(value => value.replace(/^\s*\d+:\s*/, '').trim());
    if (normalized.length < 2 || normalized.some(value => !/^[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}$/i.test(value))) {
      throw new Error(`Recovery enrollment did not expose the expected one-time codes: ${JSON.stringify(codes)}`);
    }
    await page.locator('#kcRecoveryCodesConfirmationCheck').check();
    await page.locator('#saveRecoveryAuthnCodesBtn').click();
    const enrolled = await exchange(page, started);
    if (decode(enrolled.access_token).preferred_username !== 'local-recovery') throw new Error('Recovery enrollment returned the wrong subject.');
    await logout(page, enrolled);

    const firstUse = await passwordLogin(page, 'local-recovery', 'local-recovery-only');
    await chooseRecoveryCode(page);
    await page.locator('#recoveryCodeInput').fill('0000-0000-0000');
    await page.locator('#kc-login').click();
    await page.locator('#recoveryCodeInput').waitFor();
    if (page.url().startsWith(spaOrigin + '/auth/callback')) throw new Error('An invalid recovery code was accepted.');
    await page.locator('#recoveryCodeInput').fill(normalized[0]);
    await page.locator('#kc-login').click();
    const recovered = await exchange(page, firstUse);
    if (decode(recovered.access_token).preferred_username !== 'local-recovery') throw new Error('Recovery-code sign-in returned the wrong subject.');
    await logout(page, recovered);

    const replay = await passwordLogin(page, 'local-recovery', 'local-recovery-only');
    await chooseRecoveryCode(page);
    await page.locator('#recoveryCodeInput').fill(normalized[0]);
    await page.locator('#kc-login').click();
    await page.locator('#recoveryCodeInput').waitFor();
    if (page.url().startsWith(spaOrigin + '/auth/callback')) throw new Error('A consumed recovery code was accepted again.');
    await page.locator('#recoveryCodeInput').fill(normalized[1]);
    await page.locator('#kc-login').click();
    const afterReplay = await exchange(page, replay);
    await logout(page, afterReplay);
  } finally {
    await recovery.close();
  }
  }
} finally {
  await browser.close();
}
console.log('Chromium completed governed TOTP, passkey, and one-time recovery-code acceptance.');
""".lstrip(),
        encoding="utf-8",
    )


def main() -> int:
    passkey_only = "--passkey-only" in sys.argv[1:]
    recovery_only = "--recovery-only" in sys.argv[1:]
    if passkey_only and recovery_only:
        raise AssertionError("Choose at most one advanced-browser focus mode")
    missing = [command for command in ("docker", "node", "npm") if shutil.which(command) is None]
    if missing:
        raise AssertionError("Advanced browser acceptance requires: " + ", ".join(missing))
    spa_port = spa.free_port()
    identity_port = spa.free_port()
    health_port = spa.free_port()
    spa_origin = f"http://localhost:{spa_port}"
    identity_origin = f"http://localhost:{identity_port}"
    container = f"program-kit-advanced-{uuid.uuid4().hex[:8]}"
    server = None
    with tempfile.TemporaryDirectory(prefix="program-kit-advanced-browser-") as value:
        fixture = Path(value)
        realm = fixture / "program-kit-realm.json"
        render_realm(realm, spa_origin, identity_origin)
        started = subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                container,
                "--publish",
                f"127.0.0.1:{identity_port}:8080",
                "--publish",
                f"127.0.0.1:{health_port}:9000",
                "--env",
                "KC_BOOTSTRAP_ADMIN_USERNAME=fixture-admin",
                "--env",
                "KC_BOOTSTRAP_ADMIN_PASSWORD=ephemeral-advanced-only",
                "--env",
                f"KC_HOSTNAME={identity_origin}",
                "--volume",
                f"{realm.resolve()}:/opt/keycloak/data/import/program-kit-realm.json:ro",
                "--volume",
                f"{(TEMPLATE / 'web-profiles/common/deploy/keycloak/themes').resolve()}:/opt/keycloak/themes:ro",
                spa.image_reference(),
                "start-dev",
                "--import-realm",
                "--health-enabled=true",
            ],
            capture_output=True,
            text=True,
        )
        if started.returncode != 0:
            raise AssertionError(f"Could not start advanced Keycloak fixture: {started.stderr}")
        try:
            spa.wait_keycloak(container, health_port)
            configure_required_actions(identity_origin)
            spa_root = fixture / "spa"
            spa_root.mkdir()
            server, _ = spa.start_spa(spa_root, spa_port)
            browser_root = fixture / "browser"
            browser_root.mkdir()
            spa.install_browser(browser_root, shutil.which("npm") or "npm")
            flow = browser_root / "advanced-flow.mjs"
            write_browser_flow(flow)
            environment = os.environ.copy()
            environment["PROGRAM_KIT_SPA_ORIGIN"] = spa_origin
            environment["PROGRAM_KIT_IDENTITY_ORIGIN"] = identity_origin
            command = ["node", str(flow)]
            if passkey_only:
                command.append("--passkey-only")
            if recovery_only:
                command.append("--recovery-only")
            spa.run(command, browser_root, environment, timeout=300)
        except Exception as error:
            logs = subprocess.run(
                ["docker", "logs", container], capture_output=True, text=True, check=False
            )
            raise AssertionError(f"{error}\nKeycloak output:\n{logs.stdout[-12000:]}{logs.stderr[-12000:]}") from error
        finally:
            if server is not None:
                server.shutdown()
                server.server_close()
            subprocess.run(["docker", "rm", "--force", container], capture_output=True, check=False)
    print("Real Chromium completed advanced Keycloak MFA, passkey, and recovery-code acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
