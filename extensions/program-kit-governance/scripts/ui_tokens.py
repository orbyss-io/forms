"""Compile one consumer brand into semantic, contrast-checked DTCG and CSS outputs."""
from __future__ import annotations

import json

LAYERS = "@layer theme, base, pk, components, utilities, consumer;\n"


def rgb(color: str) -> tuple[float, ...]:
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def luminance(color: str) -> float:
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb(color)]
    return sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(a: str, b: str) -> float:
    lighter, darker = sorted((luminance(a), luminance(b)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def foreground(background: str) -> str:
    return max(("#000000", "#FFFFFF"), key=lambda value: contrast(value, background))


def accent(seed: str, surface: str) -> str:
    """Preserve the seed where possible; otherwise mix toward the contrasting pole."""
    pole = rgb(foreground(surface))
    source = rgb(seed)
    for step in range(101):
        mixed = "#" + "".join(f"{round((c + (p - c) * step / 100) * 255):02X}" for c, p in zip(source, pole))
        if contrast(mixed, surface) >= 3:
            return mixed
    raise ValueError("Unable to derive an accessible accent")


def palettes(profile: dict) -> dict:
    result = {}
    for mode in ("light", "dark"):
        light = mode == "light"
        surface = "#FFFFFF" if light else "#141821"
        values = {
            "surface": surface, "on-surface": "#1B2333" if light else "#F4F6FA",
            "muted": "#EDF0F5" if light else "#252C38", "on-muted": "#414B5D" if light else "#D1D7E3",
            "border": "#707B8C" if light else "#8B96A8",
            "primary": accent(profile["brand"]["primary"], surface),
            "secondary": accent(profile["brand"]["secondary"], surface),
            "danger": "#AD1632" if light else "#FF90A2",
            "focus": "#173F8A" if light else "#A6C7FF"
        }
        for name in ("primary", "secondary", "danger"):
            values[f"on-{name}"] = foreground(values[name])
        values.update(profile["brand"].get("overrides", {}).get(mode, {}))
        for name in ("surface", "muted", "primary", "secondary", "danger"):
            if contrast(values[name], values[f"on-{name}"]) < 4.5:
                raise ValueError(f"{mode}: {name}/on-{name} fails 4.5:1 text contrast")
        for name in ("border", "focus"):
            for background in ("surface", "muted"):
                if contrast(values[name], values[background]) < 3:
                    raise ValueError(f"{mode}: {name}/{background} fails 3:1 nontext contrast")
        for name in ("primary", "secondary", "danger"):
            required = 4.5 if name == "danger" else 3
            if contrast(values[name], values["surface"]) < required:
                raise ValueError(f"{mode}: {name}/surface fails {required}:1 contrast")
        result[mode] = values
    return result


def compile_tokens(profile: dict) -> dict[str, str]:
    colors = palettes(profile)
    primitive, semantic = {}, {}
    for mode, values in colors.items():
        primitive[mode] = {name: {"$type": "color", "$value": {
            "colorSpace": "srgb", "components": list(rgb(value)), "alpha": 1}}
            for name, value in values.items()}
        semantic[mode] = {name: {"$type": "color", "$value": f"{{primitive.{mode}.{name}}}"} for name in values}
    tokens = {"$description": "Program Kit ui-experience-v1; DTCG 2025.10",
              "primitive": primitive, "semantic": semantic,
              "component": {"button": {mode: {"background": {"$type": "color", "$value": f"{{semantic.{mode}.primary}}"},
                                               "foreground": {"$type": "color", "$value": f"{{semantic.{mode}.on-primary}}"}}
                                         for mode in colors}}}
    def declarations(mode: str) -> str:
        return "\n".join(f"  --pk-{key}: {value};" for key, value in colors[mode].items())
    radius = {"square": "0", "rounded": "0.65rem", "pill": "1.5rem"}[profile["brand"]["shape"]]
    space = "0.75rem" if profile["density"] == "compact" else "1rem"
    duration = "240ms" if profile["motion"] == "expressive" else "120ms"
    elevation = {"quiet": "none", "balanced": "0 0.25rem 1rem #00000014", "expressive": "0 0.5rem 2rem #00000024"}[profile["brand"]["character"]]
    dimension = lambda value: {"$type": "dimension", "$value": {"value": value, "unit": "rem"}}
    primitive["spacing"] = dimension(0.75 if profile["density"] == "compact" else 1)
    primitive["radius"] = dimension({"square": 0, "rounded": 0.65, "pill": 1.5}[profile["brand"]["shape"]])
    primitive["font-family"] = {"$type": "fontFamily", "$value": [name.strip().strip("'") for name in profile["brand"]["fontStack"].split(",")], "$description": profile["brand"]["fontLicense"]}
    primitive["motion"] = {"$type": "duration", "$value": {"value": 240 if profile["motion"] == "expressive" else 120, "unit": "ms"}}
    shadow = {"quiet": (0, 0, 0), "balanced": (0.25, 1, 20 / 255), "expressive": (0.5, 2, 36 / 255)}[profile["brand"]["character"]]
    primitive["elevation"] = {"$type": "shadow", "$value": {"color": {"colorSpace": "srgb", "components": [0, 0, 0], "alpha": shadow[2]},
        "offsetX": dimension(0)["$value"], "offsetY": dimension(shadow[0])["$value"], "blur": dimension(shadow[1])["$value"], "spread": dimension(0)["$value"]}}
    semantic["layout"] = {name: {"$type": primitive[name]["$type"], "$value": f"{{primitive.{name}}}"}
                          for name in ("spacing", "radius", "font-family", "motion", "elevation")}
    tokens["component"]["button"]["radius"] = {"$type": "dimension", "$value": "{semantic.layout.radius}"}
    tokens["component"]["button"]["transition"] = {"$type": "duration", "$value": "{semantic.layout.motion}"}
    root_mode = "dark" if profile["scheme"] == "dark" else "light"
    css = LAYERS + f"@layer pk.tokens {{\n:root {{\n{declarations(root_mode)}\n"
    css += f"  --pk-font: {profile['brand']['fontStack']};\n  --pk-radius: {radius};\n  --pk-space: {space};\n  --pk-duration: {duration};\n  --pk-shadow: {elevation};\n  color-scheme: {root_mode};\n}}\n"
    if profile["scheme"] == "system":
        css += f"@media (prefers-color-scheme: dark) {{ :root {{\n{declarations('dark')}\ncolor-scheme: dark;\n}} }}\n"
    css += "@media (prefers-reduced-motion: reduce) { :root { --pk-duration: 0ms; } }\n}\n"
    tailwind = "/* Import after tokens.css into your pinned Tailwind v4 entry. */\n@theme inline {\n"
    tailwind += "\n".join(f"  --color-{key}: var(--pk-{key});" for key in colors["light"])
    tailwind += "\n  --font-sans: var(--pk-font);\n  --radius-brand: var(--pk-radius);\n}\n"
    # Email templates use literal color values: many mail clients do not support custom properties.
    bridge = {"loginStylesheet": "keycloak-brand.css", "fontLicense": profile["brand"]["fontLicense"],
              "email": colors["light"], "integration": "Import CSS in the consumer theme; apply literal email values in existing templates. Rerun identity-theme acceptance."}
    keycloak = css + "\n.login-pf body { font-family: var(--pk-font); background: var(--pk-surface); color: var(--pk-on-surface); }\n#kc-login { background: var(--pk-primary); color: var(--pk-on-primary); border-radius: var(--pk-radius); }\n"
    result = {"tokens.json": json.dumps(tokens, ensure_ascii=False, indent=2) + "\n", "tokens.css": css,
              "keycloak-brand.css": keycloak, "identity-theme.json": json.dumps(bridge, indent=2) + "\n"}
    if profile["css"] == "tailwind":
        result["tailwind.css"] = tailwind
        result["tailwind-entry.css"] = LAYERS + '@import "tailwindcss" source(none);\n@import "../public/assets/tokens.css";\n@import "../public/assets/layout.css";\n@import "./tailwind.css";\n/* Add explicit @source paths for your application components. */\n'
    return result
