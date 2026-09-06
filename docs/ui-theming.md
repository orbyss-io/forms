# Program Kit UI theming

Program Kit management behavior is independent of its presentation. Consumers can use the default
theme, override semantic tokens inside their own branded scope, target stable slots, add classes to
specific regions, or render the accessible structure without any Program Kit baseline classes.

## Default theme

Import the theme once, followed by only the component styles that the application uses:

```ts
import "@orbyss/program-kit-ui-theme/default.css";
import "@orbyss/program-kit-forms-modeler-react/styles.css";
import "@orbyss/program-kit-forms-schema-modeler-react/styles.css";
import "@orbyss/program-kit-localization-management-react/styles.css";
```

Scope the built-in light, dark or operating-system-responsive theme to an application region:

```html
<main data-pk-theme="auto">
  <!-- Program Kit and application components -->
</main>
```

The default theme uses the `program-kit.theme` cascade layer and component baselines use
`program-kit.components`. Normal unlayered consumer CSS therefore overrides them without
specificity escalation or `!important`.

## Brand tokens

Tokens are semantic rather than component-specific. A consumer can replace some or all of them:

```css
.acme-admin {
  --pk-color-canvas: #f7f9fc;
  --pk-color-surface: #fff;
  --pk-color-surface-muted: #edf2f8;
  --pk-color-text: #172033;
  --pk-color-text-muted: #56647a;
  --pk-color-border: #aab6c8;
  --pk-color-primary: #6750a4;
  --pk-color-primary-contrast: #fff;
  --pk-color-danger: #b42318;
  --pk-color-focus: #245eea;
  --pk-font-family: Inter, system-ui, sans-serif;
  --pk-control-radius: .25rem;
  --pk-panel-radius: 1rem;
  --pk-shadow-panel: 0 .5rem 1.5rem rgb(23 32 51 / 12%);
}
```

Focus visibility, minimum target size, forced-colors behavior, reduced motion, logical directions
and responsive reflow remain accessibility requirements. Branding must not remove those behaviors.

## Slots and classes

Every significant management region exposes a stable namespaced `data-pk-slot`, for example
`form-modeler.toolbar`, `schema-modeler.canvas` or `localization-management.table`. These are the portable CSS contract used
by React, Vue and Angular bindings.

React bindings additionally accept typed `classNames` maps:

```tsx
<ProgramKitFormModeler
  className="acme-admin"
  classNames={{ toolbar: "acme-toolbar", canvas: "acme-builder-canvas" }}
  session={session}
/>
```

Use `unstyled` when the application owns every visual rule. This removes Program Kit baseline
classes for that instance while retaining semantic markup, ARIA behavior and `data-pk-slot`
selectors:

```tsx
<ProgramKitLocalizationManagement
  actor={actor}
  className="acme-localization"
  session={session}
  unstyled
/>
```

Consumers can therefore integrate Tailwind, Bootstrap, Material or a private design system without
forking Program Kit behavior. Token and slot additions are compatible changes; removing or changing
the meaning of a published token or slot requires a major contract change.
