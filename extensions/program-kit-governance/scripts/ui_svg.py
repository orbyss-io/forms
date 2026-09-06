"""A conservative SVG asset boundary: reject active/remote content rather than silently stripping it."""
from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path
from xml.etree import ElementTree as ET

TEMPLATES = Path(__file__).resolve().parents[1] / "templates/ui-experience"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ELEMENTS = {"svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "title", "desc",
            "defs", "linearGradient", "radialGradient", "stop", "clipPath"}
ATTRIBUTES = {"viewBox", "width", "height", "fill", "fill-rule", "fill-opacity", "stroke", "stroke-width",
              "stroke-linecap", "stroke-linejoin", "stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset",
              "stroke-opacity", "opacity", "d", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry",
              "points", "transform", "id", "clip-path", "clip-rule", "gradientUnits", "gradientTransform", "offset",
              "stop-color", "stop-opacity", "fx", "fy", "fr", "spreadMethod", "preserveAspectRatio", "vector-effect"}


def sanitize_svg(source: str, prefix: str = "pk") -> str:
    if len(source.encode("utf-8")) > 262144 or re.search(r"<!|<\?", source):
        raise ValueError("SVG declarations, entities and oversized content are forbidden")
    try:
        root = ET.fromstring(source)
    except ET.ParseError as error:
        raise ValueError("Malformed SVG") from error
    elements = list(root.iter())
    if len(elements) > 2000:
        raise ValueError("SVG is too complex")
    pending = [(root, 0)]
    while pending:
        node, depth = pending.pop()
        if depth > 64:
            raise ValueError("SVG nesting is too deep")
        pending.extend((child, depth + 1) for child in node)
    ids, references = {}, []
    for element in elements:
        if element.tag.startswith("{") and not element.tag.startswith("{" + SVG_NAMESPACE + "}"):
            raise ValueError("Foreign SVG namespace")
        element.tag = element.tag.removeprefix("{" + SVG_NAMESPACE + "}")
        if element.tag not in ELEMENTS:
            raise ValueError(f"Unsupported SVG element: {element.tag}")
        if element.tag not in {"title", "desc"} and element.text and element.text.strip():
            raise ValueError("SVG text must be outlined paths, title or desc")
        for name, value in element.attrib.items():
            if name not in ATTRIBUTES or any(c in value for c in "<>\\"):
                raise ValueError(f"Unsupported SVG attribute: {name}")
            if re.search(r"url\s*\(", value, flags=re.I):
                match = re.fullmatch(r"url\(#([A-Za-z][A-Za-z0-9_-]*)\)", value)
                if match is None or name not in {"fill", "stroke", "clip-path"}:
                    raise ValueError("Only local SVG paint/clip references are supported")
                references.append((element, name, match[1]))
            elif any(c in value for c in ":;@&") or re.search(r"(?:javascript|data|https?)\s*:", value, flags=re.I):
                raise ValueError("SVG remote/active values are forbidden")
            if name == "id":
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value) or value in ids:
                    raise ValueError("Invalid/duplicate SVG ID")
                ids[value] = f"{prefix}-{value}"
                element.set(name, ids[value])
    if root.tag != "svg" or not re.fullmatch(r"[-+0-9.eE ,]+", root.get("viewBox", "")):
        raise ValueError("SVG needs a numeric viewBox")
    coordinates = re.split(r"[ ,]+", root.get("viewBox", "").strip())
    if len(coordinates) != 4 or any(not math.isfinite(float(v)) for v in coordinates) or min(float(v) for v in coordinates[2:]) <= 0:
        raise ValueError("SVG viewBox needs four finite numbers and positive dimensions")
    for element, name, identifier in references:
        if identifier not in ids:
            raise ValueError("SVG reference target is missing")
        element.set(name, f"url(#{ids[identifier]})")
    root.set("xmlns", SVG_NAMESPACE)
    return ET.tostring(root, encoding="unicode")


def icons(profile: dict) -> dict[str, str]:
    selected = profile["brand"].get("icons", {"bundle": "lucide"})
    if selected["bundle"] == "none":
        return {}
    assets = selected["assets"] if selected["bundle"] == "custom" else json.loads((TEMPLATES / "icons/lucide.json").read_text(encoding="utf-8"))["assets"]
    return {name: sanitize_svg(svg, "pk-icon-" + name) for name, svg in assets.items()}


def icon_markup(profile: dict, name: str, label: str | None = None) -> str:
    source = icons(profile).get(name)
    if source is None:
        return ""
    accessibility = 'aria-hidden="true"' if label is None else f'role="img" aria-label="{html.escape(label, quote=True)}"'
    return source.replace('<svg ', f'<svg class="pk-icon" focusable="false" {accessibility} ', 1)
