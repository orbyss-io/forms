# Viewing the Program Kit C4 projection

Program Kit uses `docs/architecture/architecture-map.json` as the semantic source of truth and
generates `docs/architecture/workspace.dsl` only as a review projection. Viewing must not import DSL
edits or change either canonical file.

## Runtime policy

The managed viewer profile is `c4-viewer-tool.json`. Prefer its exact Docker image when Docker is
running and that image is already present. Otherwise use its exact-version WAR only when Java meets
the profile minimum and the WAR is already available through `--war`,
`PROGRAM_KIT_STRUCTURIZR_WAR`, or the displayed user-cache path.

Do not run `docker pull`, download the WAR, install Docker or Java, upload the workspace, or contact
the Structurizr playground without explicit user authorization immediately before that action.
Docker `run` can pull implicitly, so never run it until image inspection proves the exact pin is
local. Structurizr Lite is obsolete and is not a fallback.

The launcher stages `workspace.dsl` and locally referenced documentation/ADR inputs under the OS
temporary directory. Structurizr may create `workspace.json` there for manual layout; that file is
disposable and never supersedes the canonical map or generated DSL. The server binds to
`127.0.0.1`, starts at port 8081, and selects the next safe port when occupied.

The generated projection applies Program Kit's review theme: people are teal, software systems are
blue, bounded contexts are violet, and proposed items/relationships use orange dashed cues. These
styles are generated review metadata, not accepted architecture semantics. The launcher links
straight to the first diagram. Use the left thumbnail rail to switch views and the key control in
the diagram toolbar to decode the styling. A magnifier on an element opens a linked detail view;
when it is absent, the canonical architecture map defines no deeper C4 view. The `+` and `-`
controls zoom the canvas rather than navigating the model hierarchy.

## Commands and recovery

Run inspection first:

```text
python .specify/extensions/program-kit-governance/scripts/c4_view.py inspect --project-root . --json
```

Start a detached local viewer and open the browser:

```text
python .specify/extensions/program-kit-governance/scripts/c4_view.py start --project-root . --open --detach
```

The successful start output includes the exact diagram URL, navigation hint, and stop command. A foreground start
(omit `--detach`) cleans up on Ctrl+C. Stop either mode explicitly with:

```text
python .specify/extensions/program-kit-governance/scripts/c4_view.py stop --project-root .
```

If inspection reports a missing image or WAR, present the exact pin and local cache location, ask
whether the user authorizes that specific retrieval, and stop. If neither Docker nor Java 21 is
available, explain both requirements without claiming a visual review. Static SVG/PNG review
packets remain an optional future mode because the upstream exporter needs the separate Playwright
binary variant; they are not an intake-validation dependency.
