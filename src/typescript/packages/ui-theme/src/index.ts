export const programKitThemeAttribute = "data-pk-theme";
export const programKitSlotAttribute = "data-pk-slot";

export const programKitThemeTokenNames = Object.freeze([
  "--pk-color-canvas",
  "--pk-color-surface",
  "--pk-color-surface-muted",
  "--pk-color-text",
  "--pk-color-text-muted",
  "--pk-color-border",
  "--pk-color-primary",
  "--pk-color-primary-contrast",
  "--pk-color-danger",
  "--pk-color-focus",
  "--pk-color-backdrop",
  "--pk-font-family",
  "--pk-font-family-mono",
  "--pk-font-size-body",
  "--pk-line-height-body",
  "--pk-font-weight-strong",
  "--pk-space-xs",
  "--pk-space-sm",
  "--pk-space-md",
  "--pk-space-lg",
  "--pk-space-xl",
  "--pk-control-min-size",
  "--pk-control-radius",
  "--pk-panel-radius",
  "--pk-border-width",
  "--pk-focus-width",
  "--pk-shadow-panel",
  "--pk-shadow-dialog",
  "--pk-motion-duration",
  "--pk-motion-easing"
] as const);

export type OrbyssThemeTokenName = typeof programKitThemeTokenNames[number];
export type OrbyssThemeTokens = Partial<Record<OrbyssThemeTokenName, string>>;
export type OrbyssClassNames<TSlot extends string> = Partial<Readonly<Record<TSlot, string>>>;

export function joinOrbyssClassNames(
  ...values: readonly (string | undefined | null | false)[]
): string | undefined {
  const result = values
    .flatMap(value => typeof value === "string" ? value.trim().split(/\s+/u) : [])
    .filter((value, index, all) => value.length > 0 && all.indexOf(value) === index)
    .join(" ");
  return result.length === 0 ? undefined : result;
}

export function programKitClassName(
  defaultClassName: string,
  customClassName: string | undefined,
  unstyled = false
): string | undefined {
  return joinOrbyssClassNames(unstyled ? undefined : defaultClassName, customClassName);
}
