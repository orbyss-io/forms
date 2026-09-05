from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "extensions/program-kit-dotnet/templates/dotnet"
sys.path.insert(0, str(ROOT / "extensions/program-kit-dotnet/scripts"))

import identity_fixture  # noqa: E402


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
    raise AssertionError("The browser-complete BFF test requires one digest-pinned Keycloak image")


def render_realm(path: Path, application_origin: str) -> None:
    source = (TEMPLATE / "web-profiles/common/deploy/keycloak/program-kit-realm.json").read_bytes()
    realm = json.loads(identity_fixture.render_realm(source, TEMPLATE, "bff-cookie", None))
    client = next((item for item in realm["clients"] if item.get("clientId") == "program-kit-bff"), None)
    if client is None:
        raise AssertionError("The rendered BFF realm has no program-kit-bff client")
    client["redirectUris"] = [f"{application_origin}/signin-oidc"]
    client["webOrigins"] = [application_origin]
    client.setdefault("attributes", {})["post.logout.redirect.uris"] = (
        f"{application_origin}/signout-callback-oidc"
    )
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


def create_consumer(repository: Path, authority: str) -> Path:
    project = repository / "src/ProgramKit.BffBrowser.Probe/ProgramKit.BffBrowser.Probe.csproj"
    project.parent.mkdir(parents=True)
    project.write_text(
        """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>true</IsPackable>
    <PackageId>ProgramKit.BffBrowser.Probe</PackageId>
    <AssemblyName>ProgramKit.BffBrowser.Probe</AssemblyName>
    <Version>1.0.0</Version>
    <ProgramKitFeatureIdentity>ProgramKit.BffBrowser.Probe</ProgramKitFeatureIdentity>
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
    (project.parent / "BffBrowserProbeFeature.cs").write_text(
        """using CShells.AspNetCore.Features;
using CShells.Features;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

namespace ProgramKit.BffBrowser.Probe;

[ShellFeature(name: "ProgramKit.BffBrowser.Probe", DisplayName = "Program Kit BFF Browser Probe")]
public sealed class BffBrowserProbeFeature : IWebShellFeature
{
    public void ConfigureServices(IServiceCollection services) { }

    public void MapEndpoints(IEndpointRouteBuilder endpoints, IHostEnvironment? environment)
    {
        endpoints.MapGet("/", () => Results.Content("<!doctype html><title>Program Kit BFF probe</title>", "text/html"))
            .AllowAnonymous();
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
        (TEMPLATE / "web-profiles/bff-cookie/.program-kit/web-profile.shells.json").read_text(encoding="utf-8")
    )
    web = profile["CShells"]["Shells"]["default"]["Configuration"]["ProgramKit"]["Web"]
    web.update(
        {
            "Authority": f"{authority}/realms/program-kit",
            "BackchannelAuthority": f"{authority}/realms/program-kit",
            "ClientSecret": "local-program-kit-secret",
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
                            "Features": {"ProgramKit.BffBrowser.Probe": {}},
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
    expected = [
        "ProgramKit.Authentication",
        "ProgramKit.Authentication.BffCookie",
        "ProgramKit.WebDefaults",
        "ProgramKit.Web.OpenApi",
        "ProgramKit.Web.ProblemDetails",
    ]
    for package_id in expected:
        package = built_in_packages / f"{package_id}.{runtime_version}.nupkg"
        if not package.is_file():
            raise AssertionError(f"Pack the current runtime before the BFF browser test; missing {package}")
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


def wait_application(process: subprocess.Popen[str], application_origin: str, timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(f"ProgramKit.Host exited before readiness:\n{stdout}\n{stderr}")
        try:
            with urllib.request.urlopen(f"{application_origin}/bff/user", timeout=2) as response:
                if response.status == 200 and json.loads(response.read()) == {"authenticated": False}:
                    return
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            pass
        time.sleep(0.5)
    raise AssertionError("ProgramKit.Host did not expose the anonymous BFF session endpoint")


def write_browser_probe(path: Path) -> None:
    path.write_text(
        textwrap.dedent(
            """
            import { chromium } from 'playwright';

            const applicationOrigin = process.env.PROGRAM_KIT_APPLICATION_ORIGIN;
            const identityOrigin = process.env.PROGRAM_KIT_IDENTITY_ORIGIN;
            const personaPasswords = JSON.parse(process.env.PROGRAM_KIT_PERSONA_PASSWORDS);
            if (!applicationOrigin || !identityOrigin) throw new Error('Browser probe origins are required.');

            async function expectProblem(response, status, code) {
              if (response.status() !== status) {
                throw new Error(`Expected ${status}/${code}, got ${response.status()}: ${await response.text()}`);
              }
              const body = await response.json();
              if (body.code !== code || body.status !== status || !body.traceId) {
                throw new Error(`Problem Details mismatch: ${JSON.stringify(body)}`);
              }
            }

            async function expectProgramKitTheme(page, screen) {
              const marker = await page.evaluate(() => getComputedStyle(document.documentElement)
                .getPropertyValue('--program-kit-theme-contract').trim());
              if (marker !== 'program-kit-theme-v1') {
                throw new Error(`The governed theme was not active on the ${screen} screen: ${marker}`);
              }
              const logo = await page.locator('#kc-header-wrapper').evaluate(element =>
                getComputedStyle(element, '::before').backgroundImage,
              );
              if (!logo.includes('program-kit-mark.svg')) {
                throw new Error(`The governed brand asset was not active on the ${screen} screen: ${logo}`);
              }
            }

            async function login(context, username, password, returnUrl = '/') {
              const page = await context.newPage();
              await page.goto(`/bff/login?returnUrl=${encodeURIComponent(returnUrl)}`);
              if (!page.url().startsWith(identityOrigin + '/')) {
                throw new Error(`BFF login did not reach Keycloak: ${page.url()}`);
              }
              await expectProgramKitTheme(page, 'login');
              const transient = (await context.cookies(applicationOrigin + '/signin-oidc')).filter(
                cookie => cookie.name.startsWith('.AspNetCore.OpenIdConnect.Nonce.')
                  || cookie.name.startsWith('.AspNetCore.Correlation.'),
              );
              if (transient.length !== 2) {
                throw new Error(`Chromium retained ${transient.length} OIDC transient cookies instead of two.`);
              }
              for (const cookie of transient) {
                if (cookie.secure || cookie.sameSite !== 'Lax') {
                  throw new Error(`Local OIDC cookie is not HTTP/Lax compatible: ${JSON.stringify(cookie)}`);
                }
              }
              await page.locator('#username').fill(username);
              await page.locator('#password').fill(password);
              await page.locator('#kc-login').click();
              await page.waitForURL(applicationOrigin + '/');
              return page;
            }

            async function identity(context) {
              const response = await context.request.get('/bff/user');
              if (!response.ok()) {
                throw new Error(`Session returned ${response.status()}: ${await response.text()}`);
              }
              const body = await response.json();
              const keys = Object.keys(body).sort();
              const expected = ['authenticated', 'displayName', 'issuer', 'permissions', 'subject'];
              if (JSON.stringify(keys) !== JSON.stringify(expected)) {
                throw new Error(`Session leaked or omitted fields: ${JSON.stringify(body)}`);
              }
              return body;
            }

            async function logout(context, page) {
              await expectProblem(
                await context.request.post('/bff/logout'),
                400,
                'invalid_antiforgery_token',
              );
              if ((await identity(context)).authenticated !== true) {
                throw new Error('Rejected logout unexpectedly cleared the session.');
              }
              const antiforgery = await (await context.request.get('/bff/antiforgery')).json();
              await page.goto('/');
              await page.evaluate(token => {
                const form = document.createElement('form');
                form.method = 'post';
                form.action = '/bff/logout';
                const field = document.createElement('input');
                field.type = 'hidden';
                field.name = token.formFieldName;
                field.value = token.requestToken;
                form.append(field);
                document.body.append(form);
                form.submit();
              }, antiforgery);
              await page.waitForURL(applicationOrigin + '/bff/signed-out');
              const anonymous = await (await context.request.get('/bff/user')).json();
              if (JSON.stringify(anonymous) !== JSON.stringify({ authenticated: false })) {
                throw new Error(`Managed logout retained the local session: ${JSON.stringify(anonymous)}`);
              }
            }

            const browser = await chromium.launch({ headless: true });
            try {
              const anonymous = await browser.newContext({ baseURL: applicationOrigin });
              await expectProblem(
                await anonymous.request.get('/api/identity-test/user'),
                401,
                'authentication_required',
              );
              await anonymous.close();

              const matrix = [
                {
                  username: 'local-wrong-role', password: personaPasswords['local-wrong-role'],
                  permissions: [], userStatus: 403, adminStatus: 403,
                },
                {
                  username: 'local-user', password: personaPasswords['local-user'],
                  permissions: ['app-user'], userStatus: 204, adminStatus: 403,
                },
                {
                  username: 'local-admin', password: personaPasswords['local-admin'],
                  permissions: ['app-admin', 'app-user'], userStatus: 204, adminStatus: 204,
                },
              ];
              for (const persona of matrix) {
                const context = await browser.newContext({ baseURL: applicationOrigin });
                try {
                  const page = await login(context, persona.username, persona.password);
                  const session = await identity(context);
                  if (session.authenticated !== true
                      || JSON.stringify(session.permissions) !== JSON.stringify(persona.permissions)) {
                    throw new Error(`Session projection mismatch for ${persona.username}: ${JSON.stringify(session)}`);
                  }
                  const user = await context.request.get('/api/identity-test/user');
                  if (persona.userStatus === 204 && user.status() !== 204) {
                    throw new Error(`${persona.username} user endpoint returned ${user.status()}.`);
                  }
                  if (persona.userStatus === 403) await expectProblem(user, 403, 'authorization_denied');
                  const admin = await context.request.get('/api/identity-test/admin');
                  if (persona.adminStatus === 204 && admin.status() !== 204) {
                    throw new Error(`${persona.username} admin endpoint returned ${admin.status()}.`);
                  }
                  if (persona.adminStatus === 403) await expectProblem(admin, 403, 'authorization_denied');
                  await logout(context, page);
                } finally {
                  await context.close();
                }
              }

              const returnUrl = await browser.newContext({ baseURL: applicationOrigin });
              try {
                const page = await login(
                  returnUrl,
                  'local-user',
                  personaPasswords['local-user'],
                  'https://attacker.example/escape',
                );
                if (page.url() !== applicationOrigin + '/') {
                  throw new Error(`External return URL escaped the application: ${page.url()}`);
                }
                await logout(returnUrl, page);
              } finally {
                await returnUrl.close();
              }
            } finally {
              await browser.close();
            }
            console.log('Chromium completed the BFF anonymous, persona, permission, CSRF, return-URL, and logout matrix.');
            """
        ).lstrip(),
        encoding="utf-8",
    )


def install_browser(browser_root: Path, npm: str) -> None:
    shutil.copyfile(TEMPLATE / "web-profiles/common/eng/program-kit/web/package.json", browser_root / "package.json")
    shutil.copyfile(TEMPLATE / "web-profiles/common/eng/program-kit/web/package-lock.json", browser_root / "package-lock.json")
    run([npm, "ci", "--ignore-scripts", "--no-audit", "--fund=false"], browser_root, timeout=300)
    command = [npm, "exec", "--", "playwright", "install"]
    if os.environ.get("CI") == "true" and os.name != "nt":
        command.append("--with-deps")
    command.append("chromium")
    run(command, browser_root, timeout=600)


def main() -> int:
    commands = {command: shutil.which(command) for command in ("docker", "dotnet", "node", "npm")}
    for command, resolved in commands.items():
        if resolved is None:
            raise AssertionError(f"{command} is required for the browser-complete BFF release test")
    built_host = ROOT / "src/dotnet/ProgramKit.Host/bin/Release/net10.0/ProgramKit.Host.dll"
    if not built_host.is_file():
        raise AssertionError("Build ProgramKit.Host in Release configuration before the BFF browser test")

    application_port = free_port()
    identity_port = free_port()
    health_port = free_port()
    application_origin = f"http://localhost:{application_port}"
    identity_origin = f"http://localhost:{identity_port}"
    container = f"program-kit-bff-browser-{uuid.uuid4().hex[:8]}"
    process: subprocess.Popen[str] | None = None
    host_log = None
    host_log_path: Path | None = None
    host_output = ""
    browser_failure: Exception | None = None
    with tempfile.TemporaryDirectory(prefix="program-kit-bff-browser-", ignore_cleanup_errors=True) as value:
        fixture = Path(value)
        host_runtime = fixture / "host-runtime"
        shutil.copytree(
            built_host.parent,
            host_runtime,
            ignore=shutil.ignore_patterns(".nuplane"),
        )
        host = host_runtime / built_host.name
        realm = fixture / "program-kit-realm.json"
        render_realm(realm, application_origin)
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
            repository = fixture / "consumer"
            repository.mkdir()
            project = create_consumer(repository, identity_origin)
            packages = repository / "artifacts/packages"
            packages.mkdir(parents=True)
            staged = repository / "artifacts/runnable-host"
            stage_host(repository, project, packages, staged)
            environment = os.environ.copy()
            environment["ASPNETCORE_URLS"] = f"http://127.0.0.1:{application_port}"
            environment["DOTNET_ENVIRONMENT"] = "Development"
            environment["Logging__LogLevel__Default"] = "Information"
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
            wait_application(process, application_origin)
            browser_root = fixture / "browser"
            browser_root.mkdir()
            install_browser(browser_root, commands["npm"] or "npm")
            probe = browser_root / "browser-flow.mjs"
            write_browser_probe(probe)
            browser_environment = os.environ.copy()
            browser_environment["PROGRAM_KIT_APPLICATION_ORIGIN"] = application_origin
            browser_environment["PROGRAM_KIT_IDENTITY_ORIGIN"] = identity_origin
            browser_environment["PROGRAM_KIT_PERSONA_PASSWORDS"] = json.dumps(persona_passwords)
            try:
                run(["node", str(probe)], browser_root, browser_environment, timeout=180)
            except Exception as error:  # Preserve host diagnostics after orderly cleanup.
                browser_failure = error
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
            if host_log_path is not None and host_log_path.is_file():
                host_output = host_log_path.read_text(encoding="utf-8", errors="replace")
            subprocess.run(["docker", "rm", "--force", container], capture_output=True)
    if browser_failure is not None:
        raise AssertionError(f"{browser_failure}\nProgramKit.Host output:\n{host_output}") from browser_failure
    forbidden = ("cookie not found", "SameSite=None and must also set Secure")
    if any(value.casefold() in host_output.casefold() for value in forbidden):
        raise AssertionError(f"BFF browser flow emitted an invalid transient-cookie warning:\n{host_output}")
    print("Real Chromium completed packaged BFF login, permission access, and managed logout.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
