---
description: View or preview Program Kit's generated C4/Structurizr workspace projection in a safe localhost viewer. Use when the user asks to view, open, render, preview, or inspect the C4 map, architecture map, Structurizr model, or workspace.dsl; do not use for architecture editing, bootstrap approval, or architecture acceptance.
---

## Purpose

Help the human visually inspect the generated C4 projection without changing its semantic source.
Read `references/c4-viewing.md` and the managed profile it names. Treat
`docs/architecture/architecture-map.json` as canonical and `docs/architecture/workspace.dsl` as a
generated, read-only review projection. Never import viewer or DSL changes into the map.

## View workflow

Run the deterministic inspection command from `references/c4-viewing.md`. Report missing files,
invalid JSON or DSL, source-hash failures, intake-binding drift, or a projection that no longer
matches a fresh export. Do not start a viewer until inspection says the projection is current.

If the pinned Docker image is already local, start the viewer with the documented detached command.
If a supported Java runtime and exact pinned WAR are already available, the launcher selects that
fallback. Open the returned localhost URL when an available browser tool can do so; otherwise give
the URL clearly. The launcher opens the first diagram directly; tell the human that the left
thumbnail rail switches between generated views and that the diagram key explains the color and
border cues. Explain that a magnifier on an element opens a linked detail view, no magnifier means
the map defines no deeper C4 view, and the `+`/`-` controls zoom the canvas. Include the exact stop
command in the response.

If the required local binary is absent, stop and ask for explicit authorization before any exact
image pull or WAR download. Do not install software, use an unpinned or `latest` artifact, contact an
external service, or upload architecture content. Never use the public Structurizr playground as an
implicit fallback.

Viewer-created `workspace.json` and manual layout are temporary review state only. Do not copy them
into the repository or present them as accepted architecture. If no viewer runtime is available,
give the actionable Docker and Java prerequisites and say that visual review has not occurred.
