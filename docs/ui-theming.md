# Program Kit application theming

Program Kit publishes an optional framework-neutral semantic-token contract. It does not publish
form controls, modelers, action bars, steppers, lookup widgets or editor components. Applications
own their renderer package, CSS and design system.

## Optional default tokens

Import the token defaults once when they are useful to the wider application:

```ts
import "@orbyss/program-kit-ui-theme/default.css";
```

Scope the light, dark or operating-system-responsive values to an application region:

```html
<main data-pk-theme="auto">
  <!-- Application-owned UI -->
</main>
```

The defaults use the `program-kit.theme` cascade layer. Unlayered application CSS can override the
variables without specificity escalation.

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

Consumer-supplied renderers remain responsible for focus visibility, accessible error relations,
minimum target size, forced-colors behavior, reduced motion, logical directions and responsive
reflow. Program Kit's forms engine supplies validated state and translation data, not markup or
visual acceptance for the consumer's selected component library.
