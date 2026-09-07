# Releasing Program Kit 0.4.0

Program Kit `0.4.0` is the Spec Kit bundle version. The .NET packages and host image produced by the same
release are intentionally preview artifacts at `0.4.0-preview.1`.

## One-time GitHub preparation

1. Merge the implementation into the repository's default branch only after all required checks pass.
2. In **Settings → Actions → General**, permit GitHub Actions to read and write repository contents and
   packages. Keep fork pull-request workflows read-only and approval-gated.
3. In **Settings → Environments**, create `frontend-packages-production`, `nuget-production`, and
   `host-production`:
   - add the maintainers who may approve registry publication as required reviewers;
   - restrict deployment tags to `v*.*.*`;
   - add `ORBYSS_PACKAGES_TOKEN` to `frontend-packages-production`. It must be a classic personal access
     token issued by the `Orbyss` GitHub account, which owns the `@orbyss` npm namespace, with
     `read:packages` and `write:packages` scopes;
   - add the environment variable `NUGET_USER` to `nuget-production`, set to the NuGet.org username that owns
     the trusted-publishing policy. This is a variable, not a secret or email address.
4. On NuGet.org, configure a trusted-publishing policy for the `orbyss-io/program-kit` repository, workflow
   file `publish-nuget.yml`, and environment `nuget-production`. Do not create or store a long-lived NuGet API
   key. The workflow exchanges its GitHub OIDC token for a short-lived key at release time.
5. Confirm the organization permits this repository to create packages in GitHub Container Registry. The
   host workflow uses the repository `GITHUB_TOKEN`; no personal access token is required.

The NuGet workflow fails at its authentication step when `NUGET_USER` or the matching trusted-publishing policy
is absent or incorrect. This prevents a tag workflow from appearing successful without publishing its packages.
The temporary `NUGET_API_KEY` output exists only for the workflow run and is never stored in GitHub.

## Pre-release verification

From a clean checkout of the release commit, run:

```powershell
uv --system-certs run --with specify-cli==1.0.1 python tests/validate_components.py
uv --system-certs run --with specify-cli==1.0.1 python tests/validate_governance_state.py
python tests/validate_dotnet_scaffold.py
python tests/validate_dotnet_runtime.py
uv --system-certs run --with specify-cli==1.0.1 specify bundle validate --offline
dotnet restore ProgramKit.slnx --locked-mode
dotnet build ProgramKit.slnx -c Release --no-restore
dotnet pack ProgramKit.slnx -c Release --no-build
```

Check that `VERSION` is `0.4.0`, `RUNTIME_VERSION` is `0.4.0-preview.1`, and the release commit is on the
default branch.

## Create the release

Create and push the tag only after GitHub preparation and pre-release verification:

```powershell
git tag -a v0.4.0 -m "Program Kit 0.4.0"
git push origin v0.4.0
```

That single tag starts one governed release workflow. After every deterministic and public-catalog gate passes,
its registry publishers run in this order so a failed package family blocks later publication:

- **Publish Program Kit Frontend Packages** publishes the exact `@orbyss` engine family through the protected
  `frontend-packages-production` environment.
- **Publish Program Kit NuGet Packages** publishes and attests the `0.4.0-preview.1` packages through
  the protected `nuget-production` environment.
- **Publish Program Kit Host Image** publishes a multi-architecture, SBOM- and provenance-bearing image as
  `ghcr.io/orbyss-io/program-kit-host:0.4.0-preview.1` and `:sha-<commit>`.

Approve the frontend, NuGet, and host-image environment deployments only after verifying the tag points at the reviewed release commit. Do not rerun a partially failed release blindly; inspect which
registries already accepted immutable artifacts. The NuGet push is duplicate-safe.

## Verify and enable consumers

1. Verify the GitHub release contains the three Spec Kit ZIPs and `SHA256SUMS`, and that its attestations verify.
2. Verify the exact `@orbyss` frontend package family is `0.4.0-preview.1` under the `preview` dist-tag.
3. Verify all NuGet packages are `0.4.0-preview.1` and expose their repository metadata.
4. Verify the GHCR host image has both `linux/amd64` and `linux/arm64` manifests, an SBOM, and provenance.
5. Make the host package public so unauthenticated Docker, Kubernetes, and Azure deployments can pull it. If it
   must remain private, grant each consumer repository explicit Actions access to the package instead.
6. Resolve the host image digest and set each consuming repository's Actions variable `PROGRAMKIT_HOST_IMAGE`
   to `ghcr.io/orbyss-io/program-kit-host@sha256:<digest>`. Never configure a mutable tag there.

Consumers then install/update the Program Kit Spec Kit bundle, explicitly select the .NET profile, and run
`speckit.program-kit-governance.dotnet-sync`. Their application tag workflow publishes
`application-bundle.zip`; when `PROGRAMKIT_HOST_IMAGE` is configured, it also publishes the thin layered
application image.
