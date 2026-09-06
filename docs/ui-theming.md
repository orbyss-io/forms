# Program Kit form-runtime theming

The published UI surface is the form journey. The rejected form-modeler, schema-modeler and
localization-management prototypes are not part of the package family.

## Default theme

Import the theme once, followed by the framework adapter stylesheet used by the application:

```ts
import "@orbyss/program-kit-ui-theme/default.css";
import "@orbyss/program-kit-forms-react/styles.css";
// Vue consumers use: @orbyss/program-kit-forms-vue/styles.css
```

Scope the light, dark or operating-system-responsive theme to an application region:

```html
<main data-pk-theme="auto">
  <!-- Program Kit form journey -->
</main>
```

The default theme uses the `program-kit.theme` cascade layer. Unlayered consumer CSS can override
it without specificity escalation or `!important`.

## Brand tokens

Tokens are semantic rather than application-specific:

```css
.acme-app {
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
}
```

The form adapter exposes stable `pk-form-control`, `pk-form-wizard` and `pk-form-actions`
classes. Consumer styles may target those classes or wrap the journey in a branded scope. Invalid
controls expose `aria-invalid="true"`, an inline error relationship through `aria-describedby`,
and a visible danger-state outline.

Focus visibility, minimum target size, forced-colors behavior, reduced motion, logical directions
and responsive reflow remain required. Branding must not remove these behaviors. Consumers may
integrate Tailwind, Bootstrap, Material or a private design system while retaining the semantic
markup and accessibility states.
