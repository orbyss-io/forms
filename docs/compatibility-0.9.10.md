# Program Kit 0.9.10 compatibility report

0.9.10 is a governance-reviewability and managed-tooling-layout release over 0.9.9. Program Kit
components advance to `0.9.10`; runtime packages and the host image remain `0.9.9-preview.1`
because no runtime package or application-host contract changed.

Existing consumers can update through the normal full-bundle, sequential release updater. The new
`speckit-program-kit-governance-view-c4` skill is optional and activates only for explicit viewing,
opening, rendering, previewing, or inspection requests. It does not alter architecture-editing or
acceptance commands.

During that full-bundle update, authenticated Program Kit files under `eng/program-kit/` migrate to
`.program-kit/eng/`. Consumer-owned files elsewhere under `eng/**` are preserved, and the retired
directories are removed only when empty. Repository scripts and CI references must use the new
managed path after the update; the supported updater performs that rewrite and validates coherence.

`docs/architecture/architecture-map.json` remains the semantic source of truth. The viewer validates
the generated `workspace.dsl`, stages writable Structurizr state outside the repository, binds only
to localhost, and never pulls an image, downloads a WAR, installs software, uploads architecture, or
contacts an external service without explicit authorization.

The generated review projection now has deterministic visual styling. This affects review rendering
only; it does not change canonical architecture semantics or accepted decisions. Existing generated
projections should be regenerated from their canonical map after upgrade.
