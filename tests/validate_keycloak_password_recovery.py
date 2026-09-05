from __future__ import annotations

import email
import html
import json
import os
import re
import shutil
import socketserver
import subprocess
import tempfile
import threading
import time
import urllib.parse
import uuid
from pathlib import Path

import validate_keycloak_advanced_browser as advanced
import validate_spa_browser_flow as spa


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "extensions/program-kit-dotnet/templates/dotnet"


def extract_action_link(message: bytes) -> str:
    parsed = email.message_from_bytes(message)
    bodies: list[str] = []
    for part in parsed.walk():
        if part.get_content_maintype() == "multipart":
            continue
        payload = part.get_payload(decode=True)
        if payload is not None:
            bodies.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    for candidate in re.findall(r'https?://[^\s<>"\']+', html.unescape("\n".join(bodies))):
        if "/login-actions/action-token" in candidate:
            return candidate.rstrip(".,)")
    raise AssertionError("The password-reset email did not contain a Keycloak action link")


class SmtpCaptureHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.wfile.write(b"220 program-kit.test ESMTP\r\n")
        in_data = False
        content: list[bytes] = []
        while True:
            line = self.rfile.readline()
            if not line:
                return
            if in_data:
                if line in (b".\r\n", b".\n"):
                    message = b"".join(content)
                    link = extract_action_link(message)
                    capture_path = self.server.capture_path  # type: ignore[attr-defined]
                    self.server.messages.append(message)  # type: ignore[attr-defined]
                    capture_path.write_text(link, encoding="utf-8")
                    self.server.message_received.set()  # type: ignore[attr-defined]
                    self.wfile.write(b"250 2.0.0 queued\r\n")
                    in_data = False
                    content.clear()
                else:
                    content.append(line[1:] if line.startswith(b"..") else line)
                continue

            command = line.decode("ascii", errors="replace").strip().upper()
            if command.startswith("EHLO"):
                self.wfile.write(b"250-program-kit.test\r\n250-8BITMIME\r\n250 SIZE 10485760\r\n")
            elif command.startswith("HELO"):
                self.wfile.write(b"250 program-kit.test\r\n")
            elif command.startswith("MAIL FROM") or command.startswith("RCPT TO"):
                self.wfile.write(b"250 2.1.0 accepted\r\n")
            elif command == "DATA":
                self.wfile.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                in_data = True
            elif command == "RSET" or command == "NOOP":
                self.wfile.write(b"250 2.0.0 ok\r\n")
            elif command == "QUIT":
                self.wfile.write(b"221 2.0.0 bye\r\n")
                return
            else:
                self.wfile.write(b"250 2.0.0 ok\r\n")


class SmtpCaptureServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], capture_path: Path):
        super().__init__(address, SmtpCaptureHandler)
        self.capture_path = capture_path
        self.messages: list[bytes] = []
        self.message_received = threading.Event()


def assert_branded_email(
    message: bytes, expected_subject: str, html_marker: str, text_marker: str
) -> None:
    parsed = email.message_from_bytes(message)
    if parsed.get("Subject") != expected_subject:
        raise AssertionError(f"The custom password-reset subject was not rendered: {parsed.get('Subject')}")
    bodies: dict[str, str] = {}
    for part in parsed.walk():
        if part.get_content_maintype() == "multipart":
            continue
        payload = part.get_payload(decode=True)
        if payload is not None:
            bodies[part.get_content_type()] = payload.decode(
                part.get_content_charset() or "utf-8", errors="replace"
            )
    html_body = bodies.get("text/html", "")
    text_body = bodies.get("text/plain", "")
    if f'data-program-kit-email="{html_marker}"' not in html_body:
        raise AssertionError(f"The branded HTML {html_marker} template was not rendered")
    if text_marker not in text_body:
        raise AssertionError(f"The branded text {text_marker} template was not rendered")
    if "/login-actions/action-token" not in html.unescape(html_body) or "/login-actions/action-token" not in text_body:
        raise AssertionError("A safe action link was not rendered in both email alternatives")
    if "${" in html_body or "${" in text_body:
        raise AssertionError("An unresolved template expression escaped into the email")


def wait_for_messages(server: SmtpCaptureServer, count: int, timeout: int = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if len(server.messages) >= count:
            return
        time.sleep(0.1)
    raise AssertionError(f"Expected {count} email messages, received {len(server.messages)}")


def render_realm(path: Path, spa_origin: str, identity_origin: str, smtp_port: int) -> None:
    advanced.render_realm(path, spa_origin, identity_origin)
    realm = json.loads(path.read_text(encoding="utf-8"))
    realm["resetPasswordAllowed"] = True
    realm["smtpServer"] = {
        "host": "host.docker.internal",
        "port": str(smtp_port),
        "from": "no-reply@program-kit.test",
        "fromDisplayName": "Program Kit Acceptance",
        "auth": "false",
        "ssl": "false",
        "starttls": "false",
    }
    path.write_text(json.dumps(realm, indent=2) + "\n", encoding="utf-8")


def write_browser_flow(path: Path) -> None:
    path.write_text(
        r"""
import { createHash, randomBytes } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const spaOrigin = process.env.PROGRAM_KIT_SPA_ORIGIN;
const identityOrigin = process.env.PROGRAM_KIT_IDENTITY_ORIGIN;
const resetLinkPath = process.env.PROGRAM_KIT_RESET_LINK_PATH;
const oldPassword = process.env.PROGRAM_KIT_OLD_PASSWORD;
const encode = value => Buffer.from(value).toString('base64url');
const decode = token => JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString('utf8'));

async function expectTheme(page, screen) {
  await page.waitForFunction(() => getComputedStyle(document.documentElement)
    .getPropertyValue('--program-kit-theme-contract').trim() === 'program-kit-theme-v1', null, { timeout: 10000 }).catch(() => {});
  const marker = await page.evaluate(() => getComputedStyle(document.documentElement)
    .getPropertyValue('--program-kit-theme-contract').trim());
  if (marker !== 'program-kit-theme-v1') throw new Error(`Theme missing on ${screen}: ${page.url()}`);
}

async function begin(page) {
  const verifier = encode(randomBytes(48));
  const challenge = encode(createHash('sha256').update(verifier).digest());
  const state = encode(randomBytes(24));
  const authorize = new URL(identityOrigin + '/realms/program-kit/protocol/openid-connect/auth');
  authorize.search = new URLSearchParams({
    client_id: 'program-kit-spa', redirect_uri: spaOrigin + '/auth/callback', response_type: 'code',
    response_mode: 'query', scope: 'openid profile program-kit-api', code_challenge: challenge,
    code_challenge_method: 'S256', state, nonce: encode(randomBytes(24)),
  });
  await page.goto(authorize.toString());
  await expectTheme(page, 'password-recovery login');
  return { verifier, state };
}

async function exchange(page, started) {
  await page.waitForURL(spaOrigin + '/auth/callback**');
  const callback = new URL(page.url());
  if (callback.searchParams.get('state') !== started.state) throw new Error('Password-recovery callback state mismatch.');
  const response = await page.evaluate(async ({ endpoint, body }) => {
    const result = await fetch(endpoint, {
      method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(body),
    });
    return { status: result.status, body: await result.json() };
  }, {
    endpoint: identityOrigin + '/realms/program-kit/protocol/openid-connect/token',
    body: { grant_type: 'authorization_code', client_id: 'program-kit-spa',
      redirect_uri: spaOrigin + '/auth/callback', code: callback.searchParams.get('code'),
      code_verifier: started.verifier },
  });
  if (response.status !== 200 || !response.body.access_token) throw new Error(`Password-recovery exchange failed: ${JSON.stringify(response)}`);
  return response.body;
}

async function waitForResetLink() {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    try {
      const value = (await readFile(resetLinkPath, 'utf8')).trim();
      if (value) return value;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error('No password-reset email arrived within 30 seconds.');
}

const browser = await chromium.launch({ headless: true });
try {
  const recovery = await browser.newContext();
  try {
    const page = await recovery.newPage();
    await begin(page);
    await page.getByRole('link', { name: /forgot password/i }).click();
    await page.locator('#kc-reset-password-form').waitFor();
    await expectTheme(page, 'forgot-password request');
    await page.locator('#username').fill('local-user@example.test');
    await page.locator('#kc-reset-password-form button[type="submit"], #kc-reset-password-form input[type="submit"]').first().click();
    const resetLink = await waitForResetLink();
    await page.goto(resetLink);
    await page.locator('#password-new').waitFor();
    await expectTheme(page, 'password update');
    await page.locator('#password-new').fill('local-user-recovered');
    await page.locator('#password-confirm').fill('local-user-recovered');
    await page.locator('#kc-passwd-update-form button[type="submit"], #kc-passwd-update-form input[type="submit"]').first().click();
    await page.waitForLoadState('networkidle');
  } finally {
    await recovery.close();
  }

  const stalePassword = await browser.newContext();
  try {
    const page = await stalePassword.newPage();
    await begin(page);
    await page.locator('#username').fill('local-user');
    await page.locator('#password').fill(oldPassword);
    await page.locator('#kc-login').click();
    await page.locator('#username').waitFor();
    if (page.url().startsWith(spaOrigin + '/auth/callback')) throw new Error('The old password remained valid after recovery.');
  } finally {
    await stalePassword.close();
  }

  const changedPassword = await browser.newContext();
  try {
    const page = await changedPassword.newPage();
    const started = await begin(page);
    await page.locator('#username').fill('local-user');
    await page.locator('#password').fill('local-user-recovered');
    await page.locator('#kc-login').click();
    const tokens = await exchange(page, started);
    if (decode(tokens.access_token).preferred_username !== 'local-user') throw new Error('Recovered password returned the wrong subject.');
  } finally {
    await changedPassword.close();
  }
} finally {
  await browser.close();
}
console.log('Chromium completed email-driven password recovery and credential replacement.');
""".lstrip(),
        encoding="utf-8",
    )


def main() -> int:
    missing = [command for command in ("docker", "node", "npm") if shutil.which(command) is None]
    if missing:
        raise AssertionError("Password-recovery acceptance requires: " + ", ".join(missing))
    spa_port = spa.free_port()
    identity_port = spa.free_port()
    health_port = spa.free_port()
    smtp_port = spa.free_port()
    spa_origin = f"http://localhost:{spa_port}"
    identity_origin = f"http://localhost:{identity_port}"
    container = f"program-kit-password-recovery-{uuid.uuid4().hex[:8]}"
    server = None
    smtp_server = None
    with tempfile.TemporaryDirectory(prefix="program-kit-password-recovery-") as value:
        fixture = Path(value)
        reset_link = fixture / "reset-link.txt"
        realm = fixture / "program-kit-realm.json"
        render_realm(realm, spa_origin, identity_origin, smtp_port)
        realm_configuration = json.loads(realm.read_text(encoding="utf-8"))
        local_user = next(
            user for user in realm_configuration["users"] if user.get("username") == "local-user"
        )
        local_password = next(
            credential["value"]
            for credential in local_user["credentials"]
            if credential.get("type") == "password"
        )
        smtp_server = SmtpCaptureServer(("0.0.0.0", smtp_port), reset_link)
        smtp_thread = threading.Thread(target=smtp_server.serve_forever, daemon=True)
        smtp_thread.start()
        started = subprocess.run(
            [
                "docker", "run", "--detach", "--name", container,
                "--add-host", "host.docker.internal:host-gateway",
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
            raise AssertionError(f"Could not start password-recovery Keycloak fixture: {started.stderr}")
        try:
            spa.wait_keycloak(container, health_port)
            spa_root = fixture / "spa"
            spa_root.mkdir()
            server, _ = spa.start_spa(spa_root, spa_port)
            browser_root = fixture / "browser"
            browser_root.mkdir()
            spa.install_browser(browser_root, shutil.which("npm") or "npm")
            flow = browser_root / "password-recovery-flow.mjs"
            write_browser_flow(flow)
            environment = os.environ.copy()
            environment["PROGRAM_KIT_SPA_ORIGIN"] = spa_origin
            environment["PROGRAM_KIT_IDENTITY_ORIGIN"] = identity_origin
            environment["PROGRAM_KIT_RESET_LINK_PATH"] = str(reset_link)
            environment["PROGRAM_KIT_OLD_PASSWORD"] = local_password
            spa.run(["node", str(flow)], browser_root, environment, timeout=180)
            if not smtp_server.message_received.is_set():
                raise AssertionError("The SMTP fixture did not observe a password-reset message")
            wait_for_messages(smtp_server, 1)
            assert_branded_email(
                smtp_server.messages[0],
                "Reset your Program Kit password",
                "password-reset-v1",
                "PROGRAM KIT | PASSWORD RESET",
            )

            token = advanced.admin_token(identity_origin)
            users = advanced.admin_request(
                identity_origin,
                token,
                "GET",
                "users?" + urllib.parse.urlencode({"username": "local-user", "exact": "true"}),
            )
            if not isinstance(users, list) or len(users) != 1:
                raise AssertionError(f"Could not resolve the email-template persona: {users}")
            user_id = users[0]["id"]
            advanced.admin_request(
                identity_origin, token, "PUT", f"users/{user_id}/send-verify-email"
            )
            wait_for_messages(smtp_server, 2)
            assert_branded_email(
                smtp_server.messages[1],
                "Verify your Program Kit email address",
                "email-verification-v1",
                "PROGRAM KIT | VERIFY EMAIL",
            )
            advanced.admin_request(
                identity_origin,
                token,
                "PUT",
                f"users/{user_id}/execute-actions-email",
                ["UPDATE_PASSWORD"],
            )
            wait_for_messages(smtp_server, 3)
            assert_branded_email(
                smtp_server.messages[2],
                "Complete your Program Kit account setup",
                "execute-actions-v1",
                "PROGRAM KIT | ACCOUNT ACTION REQUIRED",
            )
        except Exception as error:
            logs = subprocess.run(
                ["docker", "logs", container], capture_output=True, text=True, check=False
            )
            raise AssertionError(f"{error}\nKeycloak output:\n{logs.stdout[-12000:]}{logs.stderr[-12000:]}") from error
        finally:
            if server is not None:
                server.shutdown()
                server.server_close()
            if smtp_server is not None:
                smtp_server.shutdown()
                smtp_server.server_close()
            subprocess.run(["docker", "rm", "--force", container], capture_output=True, check=False)
    print("Real Chromium completed email-driven Keycloak password-recovery acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
