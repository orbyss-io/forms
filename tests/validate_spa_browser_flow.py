from __future__ import annotations

import functools
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "extensions/program-kit-dotnet/templates/dotnet"
sys.path.insert(0, str(ROOT / "extensions/program-kit-dotnet/scripts"))

import identity_fixture  # noqa: E402
import spa_profile  # noqa: E402


def run(command: list[str], cwd: Path, environment: dict[str, str] | None = None, timeout: int = 300) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def image_reference() -> str:
    compose = (TEMPLATE / "web-profiles/common/deploy/compose.identity.yml").read_text(encoding="utf-8")
    for line in compose.splitlines():
        candidate = line.strip()
        if candidate.startswith("image:"):
            reference = candidate.removeprefix("image:").strip()
            if "@sha256:" in reference:
                return reference
    raise AssertionError("The SPA acceptance test requires one digest-pinned Keycloak image")


def render_realm(path: Path, spa_origin: str, api_origin: str, identity_origin: str) -> None:
    source = (TEMPLATE / "web-profiles/common/deploy/keycloak/program-kit-realm.json").read_bytes()
    configuration = json.loads(
        (TEMPLATE / "web-profiles/spa-pkce/.program-kit/spa-pkce.json").read_text(encoding="utf-8")
    )
    configuration.update(
        {
            "applicationOrigin": spa_origin,
            "apiOrigin": api_origin,
            "identityOrigin": identity_origin,
            "identityAuthority": f"{identity_origin}/realms/program-kit",
            "redirectUris": [f"{spa_origin}/auth/callback"],
            "postLogoutRedirectUris": [f"{spa_origin}/signed-out"],
            "scopes": ["openid", "profile", "program-kit-api"],
        }
    )
    validated = spa_profile.validate_configuration(configuration)
    realm = json.loads(identity_fixture.render_realm(source, TEMPLATE, "spa-pkce", validated))
    realm["revokeRefreshToken"] = True
    realm["refreshTokenMaxReuse"] = 0
    for user in realm["users"]:
        user["attributes"] = {"programKitTenant": ["human-fixture"]}
    realm["clientScopes"].append(
        {
            "name": "program-kit-context",
            "description": "Acceptance-only custom user attribute mapping",
            "protocol": "openid-connect",
            "attributes": {"include.in.token.scope": "true"},
            "protocolMappers": [
                {
                    "name": "program-kit-tenant",
                    "protocol": "openid-connect",
                    "protocolMapper": "oidc-usermodel-attribute-mapper",
                    "consentRequired": False,
                    "config": {
                        "user.attribute": "programKitTenant",
                        "claim.name": "tenant_id",
                        "jsonType.label": "String",
                        "id.token.claim": "true",
                        "access.token.claim": "true",
                        "userinfo.token.claim": "true",
                        "introspection.token.claim": "true",
                    },
                }
            ],
        }
    )
    client = next(item for item in realm["clients"] if item.get("clientId") == "program-kit-spa")
    client.setdefault("optionalClientScopes", []).append("program-kit-context")
    path.write_text(json.dumps(realm, indent=2) + "\n", encoding="utf-8")


def wait_keycloak(name: str, health_port: int, timeout: int = 180) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{health_port}/health/ready", timeout=3) as response:
                if response.status == 200 and b'"status": "UP"' in response.read():
                    return
        except (OSError, urllib.error.URLError):
            pass
        state = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", name],
            capture_output=True,
            text=True,
        )
        if state.returncode != 0 or state.stdout.strip() != "true":
            logs = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
            raise AssertionError(f"Keycloak exited before readiness:\n{logs.stdout}{logs.stderr}")
        time.sleep(2)
    logs = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
    raise AssertionError(f"Keycloak did not become ready:\n{logs.stdout}{logs.stderr}")


def create_consumer(repository: Path, authority: str, spa_origin: str) -> Path:
    project = repository / "src/ProgramKit.IdentityAcceptance/ProgramKit.IdentityAcceptance.csproj"
    project.parent.mkdir(parents=True)
    project.write_text(
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>true</IsPackable>
    <PackageId>ProgramKit.IdentityAcceptance</PackageId>
    <AssemblyName>ProgramKit.IdentityAcceptance</AssemblyName>
    <Version>1.0.0</Version>
    <ProgramKitFeatureIdentity>ProgramKit.IdentityAcceptance</ProgramKitFeatureIdentity>
    <ProgramKitFeatureRoutes>/;/api/identity-test</ProgramKitFeatureRoutes>
  </PropertyGroup>
  <ItemGroup>
    <FrameworkReference Include="Microsoft.AspNetCore.App" />
    <PackageReference Include="CShells.AspNetCore.Abstractions" Version="0.0.29-preview.147" PrivateAssets="all" />
  </ItemGroup>
</Project>
""",
        encoding="utf-8",
        newline="\n",
    )
    (project.parent / "IdentityAcceptanceFeature.cs").write_text(
        """using CShells.AspNetCore.Features;
using CShells.Features;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace ProgramKit.IdentityAcceptance;

[ShellFeature(name: "ProgramKit.IdentityAcceptance", DisplayName = "Program Kit Identity Acceptance")]
public sealed class IdentityAcceptanceFeature : IWebShellFeature
{
    public void ConfigureServices(IServiceCollection services) { }

    public void MapEndpoints(IEndpointRouteBuilder endpoints, IHostEnvironment? environment)
    {
        endpoints.MapGet("/", () => Results.NoContent()).AllowAnonymous();
        endpoints.MapGet("/api/identity-test/user", Results.NoContent)
            .RequireAuthorization("permission:app-user");
        endpoints.MapGet("/api/identity-test/admin", Results.NoContent)
            .RequireAuthorization("permission:app-admin");
    }
}
""",
        encoding="utf-8",
        newline="\n",
    )
    (repository / "Directory.Build.targets").write_text(
        f'<Project><Import Project="{(TEMPLATE / "files/eng/program-kit/ProgramKit.Build.targets").as_posix()}" /></Project>\n',
        encoding="utf-8",
    )
    shutil.copyfile(ROOT / "NuGet.config", repository / "NuGet.config")
    (repository / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    managed = repository / "eng/program-kit"
    managed.mkdir(parents=True)
    shutil.copyfile(
        TEMPLATE / "files/eng/program-kit/ProgramKit.Packages.props",
        managed / "ProgramKit.Packages.props",
    )
    shutil.copyfile(TEMPLATE / "files/hostsettings.json", repository / "hostsettings.json")
    profile = json.loads(
        (TEMPLATE / "web-profiles/spa-pkce/.program-kit/web-profile.shells.json").read_text(encoding="utf-8")
    )
    web = profile["CShells"]["Shells"]["default"]["Configuration"]["ProgramKit"]["Web"]
    web.update(
        {
            "Authority": f"{authority}/realms/program-kit",
            "BackchannelAuthority": f"{authority}/realms/program-kit",
            "AllowedOrigins": [spa_origin],
            "RolePermissions": {"user": ["app-user"], "admin": ["app-user", "app-admin"]},
        }
    )
    profile_path = repository / ".program-kit/web-profile.shells.json"
    profile_path.parent.mkdir()
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    (repository / "shells.json").write_text(
        json.dumps(
            {
                "CShells": {
                    "Shells": {
                        "default": {
                            "Name": "default",
                            "Features": {"ProgramKit.IdentityAcceptance": {}},
                            "Configuration": {"WebRouting": {"Path": ""}},
                        }
                    }
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return project


def stage_host(repository: Path, project: Path, packages: Path, staged: Path) -> None:
    built_in_packages = ROOT / "artifacts/nuget"
    runtime_version = (ROOT / "RUNTIME_VERSION").read_text(encoding="utf-8").strip()
    for package_id in (
        "ProgramKit.Authentication",
        "ProgramKit.Authentication.SpaPkce",
        "ProgramKit.WebDefaults",
        "ProgramKit.Web.OpenApi",
        "ProgramKit.Web.ProblemDetails",
    ):
        package = built_in_packages / f"{package_id}.{runtime_version}.nupkg"
        if not package.is_file():
            raise AssertionError(f"Pack the current runtime before the SPA browser test; missing {package}")
        shutil.copyfile(package, packages / package.name)
    run(
        [
            "dotnet",
            "pack",
            str(project),
            "--configuration",
            "Release",
            "--output",
            str(packages),
            "--configfile",
            str(repository / "NuGet.config"),
        ],
        repository,
    )
    environment = os.environ.copy()
    environment["GITHUB_SHA"] = "0" * 40
    run(
        [
            sys.executable,
            str(TEMPLATE / "files/eng/program-kit/runnable_host.py"),
            "stage",
            "--repository",
            str(repository),
            "--packages",
            str(packages),
            "--output",
            str(staged),
        ],
        repository,
        environment,
    )
    shutil.copyfile(ROOT / "src/dotnet/ProgramKit.Host/appsettings.json", staged / "appsettings.json")


def wait_application(process: subprocess.Popen[str], api_origin: str, timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError("ProgramKit.Host exited before SPA acceptance readiness")
        try:
            with urllib.request.urlopen(f"{api_origin}/", timeout=2) as response:
                if response.status == 204:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.5)
    raise AssertionError("ProgramKit.Host did not expose the SPA acceptance fixture")


def raw_response(request: urllib.request.Request) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.headers


def validate_cors(api_origin: str, spa_origin: str) -> None:
    status, headers = raw_response(
        urllib.request.Request(
            f"{api_origin}/api/identity-test/user",
            headers={"Origin": spa_origin},
        )
    )
    if status != 401 or headers.get("Access-Control-Allow-Origin") != spa_origin:
        raise AssertionError("The configured SPA origin did not receive CORS on an authentication error")
    status, headers = raw_response(
        urllib.request.Request(
            f"{api_origin}/api/identity-test/user",
            headers={"Origin": "https://attacker.example"},
        )
    )
    if status != 401 or headers.get("Access-Control-Allow-Origin") is not None:
        raise AssertionError("An unconfigured origin received a CORS grant")
    status, headers = raw_response(
        urllib.request.Request(
            f"{api_origin}/api/identity-test/user",
            method="OPTIONS",
            headers={
                "Origin": spa_origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
    )
    if (
        status not in {200, 204}
        or headers.get("Access-Control-Allow-Origin") != spa_origin
        or "GET" not in headers.get("Access-Control-Allow-Methods", "")
        or "authorization" not in headers.get("Access-Control-Allow-Headers", "").casefold()
    ):
        raise AssertionError("The configured SPA preflight contract was not exact")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def start_spa(root: Path, port: int) -> tuple[http.server.ThreadingHTTPServer, threading.Thread]:
    page = "<!doctype html><meta charset=utf-8><title>Program Kit SPA identity acceptance</title>"
    (root / "auth/callback").mkdir(parents=True)
    (root / "signed-out").mkdir(parents=True)
    for relative in ("index.html", "auth/callback/index.html", "signed-out/index.html"):
        (root / relative).write_text(page, encoding="utf-8")
    handler = functools.partial(QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def install_browser(browser_root: Path, npm: str) -> None:
    shutil.copyfile(TEMPLATE / "web-profiles/common/eng/program-kit/web/package.json", browser_root / "package.json")
    shutil.copyfile(
        TEMPLATE / "web-profiles/common/eng/program-kit/web/package-lock.json",
        browser_root / "package-lock.json",
    )
    run([npm, "ci", "--ignore-scripts", "--no-audit", "--fund=false"], browser_root, timeout=300)
    command = [npm, "exec", "--", "playwright", "install"]
    if os.environ.get("CI") == "true" and os.name != "nt":
        command.append("--with-deps")
    command.append("chromium")
    run(command, browser_root, timeout=600)


def write_browser_flow(path: Path) -> None:
    path.write_text(
        textwrap.dedent(
            """
            import { createHash, randomBytes } from 'node:crypto';
            import { chromium } from 'playwright';

            const spaOrigin = process.env.PROGRAM_KIT_SPA_ORIGIN;
            const apiOrigin = process.env.PROGRAM_KIT_API_ORIGIN;
            const identityOrigin = process.env.PROGRAM_KIT_IDENTITY_ORIGIN;
            const personaPasswords = JSON.parse(process.env.PROGRAM_KIT_PERSONA_PASSWORDS);
            if (!spaOrigin || !apiOrigin || !identityOrigin) throw new Error('SPA acceptance origins are required.');

            const base64url = value => Buffer.from(value).toString('base64url');
            const decode = token => JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString('utf8'));

            async function expectTheme(page) {
              const marker = await page.evaluate(() => getComputedStyle(document.documentElement)
                .getPropertyValue('--program-kit-theme-contract').trim());
              if (marker !== 'program-kit-theme-v1') throw new Error(`SPA login theme marker missing: ${marker}`);
            }

            async function browserPost(page, url, body) {
              return page.evaluate(async ({ url, body }) => {
                const response = await fetch(url, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                  body: new URLSearchParams(body),
                });
                return { status: response.status, body: await response.json() };
              }, { url, body });
            }

            async function apiGet(page, path, token) {
              return page.evaluate(async ({ url, token }) => {
                const response = await fetch(url, {
                  headers: token ? { Authorization: `Bearer ${token}` } : {},
                });
                const text = await response.text();
                return {
                  status: response.status,
                  body: text ? JSON.parse(text) : null,
                };
              }, { url: apiOrigin + path, token });
            }

            async function login(browser, persona) {
              const context = await browser.newContext({ baseURL: spaOrigin });
              const page = await context.newPage();
              await page.goto('/');
              const verifier = base64url(randomBytes(48));
              const challenge = base64url(createHash('sha256').update(verifier).digest());
              const state = base64url(randomBytes(24));
              const nonce = base64url(randomBytes(24));
              const authorize = new URL(identityOrigin + '/realms/program-kit/protocol/openid-connect/auth');
              authorize.search = new URLSearchParams({
                client_id: 'program-kit-spa',
                redirect_uri: spaOrigin + '/auth/callback',
                response_type: 'code',
                response_mode: 'query',
                scope: 'openid profile program-kit-api program-kit-context',
                code_challenge: challenge,
                code_challenge_method: 'S256',
                state,
                nonce,
              });
              await page.goto(authorize.toString());
              await expectTheme(page);
              await page.locator('#username').fill(persona.username);
              await page.locator('#password').fill(persona.password);
              await page.locator('#kc-login').click();
              await page.waitForURL(spaOrigin + '/auth/callback**');
              const callback = new URL(page.url());
              if (callback.searchParams.get('state') !== state || !callback.searchParams.get('code')) {
                throw new Error(`SPA callback state/code mismatch: ${page.url()}`);
              }
              const tokens = await browserPost(
                page,
                identityOrigin + '/realms/program-kit/protocol/openid-connect/token',
                {
                  grant_type: 'authorization_code',
                  client_id: 'program-kit-spa',
                  redirect_uri: spaOrigin + '/auth/callback',
                  code: callback.searchParams.get('code'),
                  code_verifier: verifier,
                },
              );
              if (tokens.status !== 200 || !tokens.body.access_token || !tokens.body.refresh_token) {
                throw new Error(`SPA token exchange failed: ${JSON.stringify(tokens)}`);
              }
              const claims = decode(tokens.body.access_token);
              const audiences = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
              if (!audiences.includes('program-kit-api')
                  || claims.tenant_id !== 'human-fixture'
                  || claims.preferred_username !== persona.username) {
                throw new Error(`SPA token claims mismatch: ${JSON.stringify(claims)}`);
              }
              const storage = await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }));
              if (storage.local !== 0 || storage.session !== 0) {
                throw new Error(`SPA acceptance persisted tokens/state in browser storage: ${JSON.stringify(storage)}`);
              }
              return { context, page, tokens: tokens.body, claims };
            }

            const browser = await chromium.launch({ headless: true });
            try {
              const anonymousContext = await browser.newContext({ baseURL: spaOrigin });
              const anonymousPage = await anonymousContext.newPage();
              await anonymousPage.goto('/');
              const anonymous = await apiGet(anonymousPage, '/api/identity-test/user');
              if (anonymous.status !== 401 || anonymous.body?.code !== 'authentication_required') {
                throw new Error(`SPA anonymous/CORS contract failed: ${JSON.stringify(anonymous)}`);
              }
              await anonymousContext.close();

              const matrix = [
                { username: 'local-wrong-role', password: personaPasswords['local-wrong-role'], permissions: [], user: 403, admin: 403 },
                { username: 'local-user', password: personaPasswords['local-user'], permissions: ['app-user'], user: 204, admin: 403 },
                { username: 'local-admin', password: personaPasswords['local-admin'], permissions: ['app-admin', 'app-user'], user: 204, admin: 204 },
              ];
              for (const persona of matrix) {
                const flow = await login(browser, persona);
                try {
                  const roles = flow.claims.roles ?? [];
                  if ((persona.username === 'local-wrong-role' && (roles.includes('user') || roles.includes('admin')))
                      || (persona.username === 'local-user' && (!roles.includes('user') || roles.includes('admin')))
                      || (persona.username === 'local-admin' && (!roles.includes('user') || !roles.includes('admin')))) {
                    throw new Error(`Provider role matrix mismatch for ${persona.username}: ${JSON.stringify(roles)}`);
                  }
                  const user = await apiGet(flow.page, '/api/identity-test/user', flow.tokens.access_token);
                  const admin = await apiGet(flow.page, '/api/identity-test/admin', flow.tokens.access_token);
                  if (user.status !== persona.user || admin.status !== persona.admin) {
                    throw new Error(`SPA permission/CORS matrix mismatch for ${persona.username}: ${JSON.stringify({ user, admin })}`);
                  }
                  if (user.status === 403 && user.body?.code !== 'authorization_denied') {
                    throw new Error(`SPA user denial was not stable Problem Details: ${JSON.stringify(user.body)}`);
                  }
                  if (admin.status === 403 && admin.body?.code !== 'authorization_denied') {
                    throw new Error(`SPA admin denial was not stable Problem Details: ${JSON.stringify(admin.body)}`);
                  }

                  const logout = new URL(identityOrigin + '/realms/program-kit/protocol/openid-connect/logout');
                  const logoutParameters = {
                    client_id: 'program-kit-spa',
                    post_logout_redirect_uri: spaOrigin + '/signed-out',
                  };
                  if (persona.username !== 'local-wrong-role') {
                    logoutParameters.id_token_hint = flow.tokens.id_token;
                  }
                  logout.search = new URLSearchParams(logoutParameters);
                  await flow.page.goto(logout.toString());
                  if (persona.username === 'local-wrong-role') {
                    await expectTheme(flow.page);
                    const confirmation = flow.page.locator(
                      '#kc-logout, button[name="confirmLogout"], input[name="confirmLogout"]',
                    ).first();
                    if (await confirmation.count() !== 1) {
                      throw new Error(`The governed logout confirmation screen was not rendered: ${flow.page.url()}`);
                    }
                    await confirmation.click();
                  }
                  await flow.page.waitForURL(spaOrigin + '/signed-out**');
                } finally {
                  await flow.context.close();
                }
              }

              // Keycloak revokes the user session when reuse detection catches the old
              // rotated refresh token. Keep that destructive security assertion separate
              // from the normal RP-initiated logout journeys above.
              const refreshFlow = await login(browser, {
                username: 'local-user',
                password: personaPasswords['local-user'],
              });
              try {
                const refreshed = await browserPost(
                  refreshFlow.page,
                  identityOrigin + '/realms/program-kit/protocol/openid-connect/token',
                  {
                    grant_type: 'refresh_token',
                    client_id: 'program-kit-spa',
                    refresh_token: refreshFlow.tokens.refresh_token,
                  },
                );
                if (refreshed.status !== 200 || !refreshed.body.refresh_token
                    || refreshed.body.refresh_token === refreshFlow.tokens.refresh_token) {
                  throw new Error(`SPA refresh rotation failed: ${JSON.stringify(refreshed)}`);
                }
                const refreshedAccess = await apiGet(
                  refreshFlow.page,
                  '/api/identity-test/user',
                  refreshed.body.access_token,
                );
                if (refreshedAccess.status !== 204) {
                  throw new Error(`Rotated SPA access token was not accepted: ${JSON.stringify(refreshedAccess)}`);
                }
                const replay = await browserPost(
                  refreshFlow.page,
                  identityOrigin + '/realms/program-kit/protocol/openid-connect/token',
                  {
                    grant_type: 'refresh_token',
                    client_id: 'program-kit-spa',
                    refresh_token: refreshFlow.tokens.refresh_token,
                  },
                );
                if (replay.status < 400 || replay.body.error !== 'invalid_grant') {
                  throw new Error(`Rotated SPA refresh token was reusable: ${JSON.stringify(replay)}`);
                }
              } finally {
                await refreshFlow.context.close();
              }
            } finally {
              await browser.close();
            }
            console.log('Chromium completed public SPA PKCE, custom claims, personas, CORS, refresh rotation, and logout.');
            """
        ).lstrip(),
        encoding="utf-8",
    )


def main() -> int:
    commands = {command: shutil.which(command) for command in ("docker", "dotnet", "node", "npm")}
    for command, resolved in commands.items():
        if resolved is None:
            raise AssertionError(f"{command} is required for the browser-complete SPA acceptance test")
    built_host = ROOT / "src/dotnet/ProgramKit.Host/bin/Release/net10.0/ProgramKit.Host.dll"
    if not built_host.is_file():
        raise AssertionError("Build ProgramKit.Host in Release configuration before the SPA browser test")

    spa_port = free_port()
    api_port = free_port()
    identity_port = free_port()
    health_port = free_port()
    spa_origin = f"http://localhost:{spa_port}"
    api_origin = f"http://localhost:{api_port}"
    identity_origin = f"http://localhost:{identity_port}"
    container = f"program-kit-spa-browser-{uuid.uuid4().hex[:8]}"
    process: subprocess.Popen[str] | None = None
    host_log = None
    host_output = ""
    server: http.server.ThreadingHTTPServer | None = None
    with tempfile.TemporaryDirectory(prefix="program-kit-spa-browser-", ignore_cleanup_errors=True) as value:
        fixture = Path(value)
        host_runtime = fixture / "host-runtime"
        shutil.copytree(built_host.parent, host_runtime, ignore=shutil.ignore_patterns(".nuplane"))
        host = host_runtime / built_host.name
        realm = fixture / "program-kit-realm.json"
        render_realm(realm, spa_origin, api_origin, identity_origin)
        realm_configuration = json.loads(realm.read_text(encoding="utf-8"))
        persona_passwords = {
            user["username"]: next(
                credential["value"]
                for credential in user.get("credentials", [])
                if credential.get("type") == "password"
            )
            for user in realm_configuration["users"]
            if user.get("username") in {"local-user", "local-admin", "local-wrong-role"}
        }
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
                "KC_BOOTSTRAP_ADMIN_PASSWORD=ephemeral-browser-only",
                "--env",
                f"KC_HOSTNAME={identity_origin}",
                "--volume",
                f"{realm.resolve()}:/opt/keycloak/data/import/program-kit-realm.json:ro",
                "--volume",
                f"{(TEMPLATE / 'web-profiles/common/deploy/keycloak/themes').resolve()}:/opt/keycloak/themes:ro",
                image_reference(),
                "start-dev",
                "--import-realm",
                "--health-enabled=true",
            ],
            capture_output=True,
            text=True,
        )
        if started.returncode != 0:
            raise AssertionError(f"Could not start pinned Keycloak: {started.stderr}")
        try:
            wait_keycloak(container, health_port)
            spa_root = fixture / "spa"
            spa_root.mkdir()
            server, _ = start_spa(spa_root, spa_port)
            repository = fixture / "consumer"
            repository.mkdir()
            project = create_consumer(repository, identity_origin, spa_origin)
            packages = repository / "artifacts/packages"
            packages.mkdir(parents=True)
            staged = repository / "artifacts/runnable-host"
            stage_host(repository, project, packages, staged)
            environment = os.environ.copy()
            environment["ASPNETCORE_URLS"] = f"http://127.0.0.1:{api_port}"
            environment["DOTNET_ENVIRONMENT"] = "Development"
            host_log_path = fixture / "program-kit-host.log"
            host_log = host_log_path.open("w", encoding="utf-8")
            process = subprocess.Popen(
                ["dotnet", str(host)],
                cwd=staged,
                env=environment,
                stdout=host_log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            wait_application(process, api_origin)
            validate_cors(api_origin, spa_origin)
            browser_root = fixture / "browser"
            browser_root.mkdir()
            install_browser(browser_root, commands["npm"] or "npm")
            flow = browser_root / "spa-flow.mjs"
            write_browser_flow(flow)
            browser_environment = os.environ.copy()
            browser_environment["PROGRAM_KIT_SPA_ORIGIN"] = spa_origin
            browser_environment["PROGRAM_KIT_API_ORIGIN"] = api_origin
            browser_environment["PROGRAM_KIT_IDENTITY_ORIGIN"] = identity_origin
            browser_environment["PROGRAM_KIT_PERSONA_PASSWORDS"] = json.dumps(persona_passwords)
            run(["node", str(flow)], browser_root, browser_environment, timeout=240)
        except Exception as error:
            if host_log is not None:
                host_log.flush()
            if (fixture / "program-kit-host.log").is_file():
                host_output = (fixture / "program-kit-host.log").read_text(encoding="utf-8", errors="replace")
            raise AssertionError(f"{error}\nProgramKit.Host output:\n{host_output}") from error
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            if host_log is not None:
                host_log.close()
            if server is not None:
                server.shutdown()
                server.server_close()
            subprocess.run(["docker", "rm", "--force", container], capture_output=True)
    print("Real Chromium completed the packaged SPA-PKCE identity acceptance matrix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
