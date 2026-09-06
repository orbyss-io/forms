"""Validate the owned UI schemas and cross-document invariants without third-party runtime code."""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

REFERENCES = Path(__file__).resolve().parents[1] / "references"


def validate_schema(value: object, rule: dict, root: dict | None = None, path: str = "$") -> None:
    """Implement only the vocabulary used by these two owned schemas, never remote schemas."""
    supported = {"$schema", "$id", "$defs", "$ref", "title", "description", "type", "const", "enum", "properties",
                 "additionalProperties", "required", "items", "minItems", "maxItems", "uniqueItems", "minLength", "maxLength", "pattern", "minimum", "maximum"}
    if set(rule) - supported:
        raise ValueError(f"Owned UI schema uses unsupported vocabulary: {set(rule) - supported}")
    root = rule if root is None else root
    if "$ref" in rule:
        validate_schema(value, root["$defs"][rule["$ref"].removeprefix("#/$defs/")], root, path)
        return
    kinds = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool}
    if "type" in rule and (type(value) is not kinds[rule["type"]]):
        raise ValueError(f"{path}: expected {rule['type']}")
    if "const" in rule and value != rule["const"]:
        raise ValueError(f"{path}: expected {rule['const']}")
    if "enum" in rule and value not in rule["enum"]:
        raise ValueError(f"{path}: unknown choice {value!r}")
    if isinstance(value, dict):
        properties = rule.get("properties", {})
        if set(rule.get("required", [])) - value.keys():
            raise ValueError(f"{path}: missing required fields")
        if rule.get("additionalProperties") is False and value.keys() - properties.keys():
            raise ValueError(f"{path}: unknown fields {value.keys() - properties.keys()}")
        for key, item in value.items():
            if key in properties:
                validate_schema(item, properties[key], root, f"{path}.{key}")
            elif isinstance(rule.get("additionalProperties"), dict):
                validate_schema(item, rule["additionalProperties"], root, f"{path}.{key}")
    if isinstance(value, list):
        if not rule.get("minItems", 0) <= len(value) <= rule.get("maxItems", 100000):
            raise ValueError(f"{path}: invalid item count")
        if rule.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            raise ValueError(f"{path}: duplicates")
        for index, item in enumerate(value):
            validate_schema(item, rule["items"], root, f"{path}[{index}]")
    if isinstance(value, str):
        if not rule.get("minLength", 0) <= len(value) <= rule.get("maxLength", 100000):
            raise ValueError(f"{path}: invalid text length")
        if rule.get("minLength", 0) and not value.strip():
            raise ValueError(f"{path}: nonblank text is required")
        if "pattern" in rule and re.fullmatch(rule["pattern"].removeprefix("^").removesuffix("$"), value) is None:
            raise ValueError(f"{path}: invalid format")
        if any(ord(c) < 32 and c not in "\n\t" for c in value):
            raise ValueError(f"{path}: control characters are forbidden")
    if type(value) is int and not rule.get("minimum", value) <= value <= rule.get("maximum", value):
        raise ValueError(f"{path}: outside supported range")


def safe_url(value: str) -> str:
    """Allow stable root-relative or HTTPS links without credentials or control characters."""
    if any(c.isspace() for c in value) or any(c in value for c in "\\<>'\""):
        raise ValueError("Unsafe URL")
    parsed = urlsplit(value)
    if parsed.username or parsed.password or value.startswith("//"):
        raise ValueError("URL credentials and protocol-relative URLs are forbidden")
    if parsed.scheme == "https" and parsed.hostname:
        return value
    if not parsed.scheme and not parsed.netloc and value.startswith("/"):
        return value
    raise ValueError("Expected root-relative or HTTPS URL")


def public(page: dict) -> bool:
    return page["intent"] != "private-app"


def discoverable(page: dict) -> bool:
    return public(page) and page["index"]


def validate(profile: dict, content: dict) -> None:
    for value, name in ((profile, "ui-profile"), (content, "ui-content")):
        validate_schema(value, json.loads((REFERENCES / f"{name}.schema.json").read_text(encoding="utf-8")))
    origin = urlsplit(safe_url(content["origin"]))
    if origin.scheme != "https" or origin.path or origin.query or origin.fragment or origin.port not in (None, 443):
        raise ValueError("origin must be an exact HTTPS origin without path/query/fragment")
    if profile["discovery"]["llms"] and not profile["discovery"]["markdown"]:
        raise ValueError("llms requires the same-source Markdown export")
    analytics = profile.get("analytics", {"provider": "none"})
    if (analytics["provider"] == "ga4") != ("measurementId" in analytics):
        raise ValueError("Only GA4 requires an explicit measurementId")
    if analytics["provider"] == "none" and analytics.get("events"):
        raise ValueError("Disabled analytics cannot declare active event mappings")
    brand = profile["brand"]
    if "favicon" in brand:
        safe_url(brand["favicon"])
    if "logo" in brand:
        if ("url" in brand["logo"]) == ("svg" in brand["logo"]):
            raise ValueError("A logo requires exactly one URL or SVG content plus meaningful alt text")
        if "url" in brand["logo"]:
            safe_url(brand["logo"]["url"])
    icons = brand.get("icons", {"bundle": "lucide"})
    if icons["bundle"] == "custom":
        if not icons.get("assets") or not icons.get("license") or not icons.get("source"):
            raise ValueError("Custom icons require SVG assets, license and source provenance")
        if len(icons["assets"]) > 200:
            raise ValueError("Import a used-icon subset, not an entire icon library")
        for name in icons["assets"]:
            if not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", name):
                raise ValueError("Invalid icon identifier")
    elif set(icons) != {"bundle"}:
        raise ValueError("Only custom icons accept explicit assets/license/source fields")
    pages = content["pages"]
    by_id = {p["id"]: p for p in pages}
    paths = {p["path"].lower() for p in pages}
    if len(by_id) != len(pages) or len(paths) != len(pages):
        raise ValueError("Page IDs and case-insensitive canonical paths must be unique")
    for page in pages:
        path = page["path"]
        if path != "/" and not re.fullmatch(r"/(?:[a-z0-9][a-z0-9-]*/)*[a-z0-9][a-z0-9-]*", path):
            raise ValueError("Canonical paths use lowercase slug segments, no extensions, query, or traversal")
        if path.split("/")[1] in {"assets", "discovery", "llms", "robots", "sitemap", "_program-kit"}:
            raise ValueError("Page path conflicts with generated resource namespace")
        modified = dt.date.fromisoformat(page["lastModified"])
        if not public(page) and page["index"]:
            raise ValueError("Private pages cannot be indexed")
        if "image" in page:
            safe_url(page["image"]["url"])
        if "article" in page:
            if dt.date.fromisoformat(page["article"]["datePublished"]) > modified:
                raise ValueError("Article modification date precedes publication")
        if "article" in page and "product" in page:
            raise ValueError("Choose one primary structured entity for this renderer")
        heading_ids = set()
        for block in page["blocks"]:
            required = {"heading": {"type", "text", "id"}, "paragraph": {"type", "text"},
                        "list": {"type", "items"}, "table": {"type", "text", "headers", "rows"},
                        "link": {"type", "text", "url"}}[block["type"]]
            if set(block) != required:
                raise ValueError(f"{page['id']}: invalid {block['type']} block fields")
            if block["type"] == "heading":
                if block["id"] in heading_ids or block["id"] in {"main", "page-title"}:
                    raise ValueError("Heading anchors must be unique and nonreserved")
                heading_ids.add(block["id"])
            if block["type"] == "table" and any(len(row) != len(block["headers"]) for row in block["rows"]):
                raise ValueError("Table rows must match the column headers")
            if block["type"] == "link":
                safe_url(block["url"])
        alternatives = page.get("alternates", [])
        languages = {page["language"]}
        for other_id in alternatives:
            other = by_id.get(other_id)
            if (other is None or not discoverable(page) or not discoverable(other)
                    or page["id"] not in other.get("alternates", []) or other["language"] in languages):
                raise ValueError("Language alternates must be public/indexed, reciprocal and language-unique")
            languages.add(other["language"])
