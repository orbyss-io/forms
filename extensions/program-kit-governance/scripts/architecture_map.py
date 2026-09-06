from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


SCHEMA_VERSION = "1.0"
IMPORTER_VERSION = "1.0"
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ELEMENT_TYPES = {
    "person",
    "software-system",
    "external-system",
    "container",
    "component",
    "domain-capability",
    "bounded-context",
    "data-store",
    "deployment-node",
    "infrastructure-node",
    "software-system-instance",
    "container-instance",
}
STATUSES = {"explicit", "derived", "proposed", "unresolved", "accepted"}
DECISION_STATUSES = {"Proposed", "Accepted", "Rejected", "Deprecated", "Superseded"}
VIEW_TYPES = {
    "system-context",
    "system-landscape",
    "container",
    "component",
    "domain-context",
    "dynamic",
    "deployment",
    "filtered",
    "custom",
    "image",
}
SUPPORTED_DSL_ELEMENT_TYPES = {
    "person",
    "software-system",
    "external-system",
    "container",
    "component",
    "domain-capability",
    "bounded-context",
    "data-store",
}


class ArchitectureMapError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImportResult:
    model: dict
    importer_id: str
    importer_version: str
    diagnostics: tuple[str, ...] = ()


class ArchitectureMapImporter(ABC):
    id: str
    version: str = IMPORTER_VERSION

    @abstractmethod
    def can_import(self, path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def import_path(self, path: Path, base: dict | None = None) -> ImportResult:
        raise NotImplementedError


class ArchitectureMapExporter(ABC):
    id: str
    version: str = IMPORTER_VERSION

    @abstractmethod
    def export(self, model: dict) -> str:
        raise NotImplementedError


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArchitectureMapError(f"Cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArchitectureMapError(f"Expected a JSON object in {path}")
    return value


def _text(value: object, label: str, maximum: int = 500, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not allow_empty and not value.strip()):
        qualifier = "a string" if allow_empty else "a non-empty string"
        raise ArchitectureMapError(f"{label} must be {qualifier} of at most {maximum} characters")
    return value


def _id(value: object, label: str) -> str:
    text = _text(value, label, 64)
    if not ID.fullmatch(text):
        raise ArchitectureMapError(f"{label} is not a stable Program Kit ID: {text!r}")
    return text


def _unique_strings(value: object, label: str, maximum: int = 120) -> list[str]:
    if not isinstance(value, list):
        raise ArchitectureMapError(f"{label} must be a list")
    result: list[str] = []
    for index, item in enumerate(value, 1):
        result.append(_text(item, f"{label}[{index}]", maximum))
    if len(set(result)) != len(result):
        raise ArchitectureMapError(f"{label} contains duplicates")
    return result


def _properties(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ArchitectureMapError(f"{label} must be an object")
    for key, item in value.items():
        _text(key, f"{label} key", 120)
        _text(item, f"{label}.{key}", 2000, allow_empty=True)
    return value


def _perspectives(value: object, label: str) -> list[dict]:
    if not isinstance(value, list):
        raise ArchitectureMapError(f"{label} must be a list")
    for index, item in enumerate(value, 1):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict) or set(item) != {"name", "description", "value"}:
            raise ArchitectureMapError(f"{item_label} has an invalid shape")
        _text(item.get("name"), f"{item_label}.name")
        _text(item.get("description"), f"{item_label}.description", allow_empty=True)
        _text(item.get("value"), f"{item_label}.value")
    return value


def _relative_file(project_root: Path, value: object, label: str) -> Path:
    text = _text(value, label, 260)
    candidate = Path(text)
    if candidate.is_absolute():
        raise ArchitectureMapError(f"{label} must be repository-relative")
    resolved = (project_root / candidate).resolve()
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ArchitectureMapError(f"{label} escapes the repository") from exc
    return resolved


def validate_model(model: dict, project_root: Path | None = None) -> dict:
    required = {
        "schema_version",
        "model_id",
        "title",
        "sources",
        "decisions",
        "documentation",
        "constraints",
        "elements",
        "relationships",
        "views",
        "configuration",
        "extensions",
    }
    if set(model) != required or model.get("schema_version") != SCHEMA_VERSION:
        raise ArchitectureMapError("Architecture map has an invalid top-level shape or schema version")
    _id(model.get("model_id"), "model_id")
    _text(model.get("title"), "title")

    sources = model.get("sources")
    if not isinstance(sources, list):
        raise ArchitectureMapError("sources must be a list")
    source_ids: set[str] = set()
    for index, source in enumerate(sources, 1):
        label = f"sources[{index}]"
        if not isinstance(source, dict) or set(source) != {"id", "path", "sha256", "format", "importer"}:
            raise ArchitectureMapError(f"{label} has an invalid shape")
        source_id = _id(source.get("id"), f"{label}.id")
        if source_id in source_ids:
            raise ArchitectureMapError(f"Duplicate source ID: {source_id}")
        source_ids.add(source_id)
        _text(source.get("path"), f"{label}.path", 260)
        digest = _text(source.get("sha256"), f"{label}.sha256", 64)
        if not SHA256.fullmatch(digest):
            raise ArchitectureMapError(f"{label}.sha256 is invalid")
        _text(source.get("format"), f"{label}.format", 120)
        importer = source.get("importer")
        if not isinstance(importer, dict) or set(importer) != {"id", "version"}:
            raise ArchitectureMapError(f"{label}.importer has an invalid shape")
        _id(importer.get("id"), f"{label}.importer.id")
        _text(importer.get("version"), f"{label}.importer.version", 40)
        if project_root is not None:
            source_path = _relative_file(project_root, source["path"], f"{label}.path")
            if not source_path.is_file():
                raise ArchitectureMapError(f"Architecture source is missing: {source['path']}")
            if sha256_file(source_path) != digest:
                raise ArchitectureMapError(f"Architecture source changed: {source['path']}")

    decisions = model.get("decisions")
    if not isinstance(decisions, list):
        raise ArchitectureMapError("decisions must be a list")
    decision_ids: set[str] = set()
    decision_statuses: dict[str, str] = {}
    supersedes: dict[str, list[str]] = {}
    for index, decision in enumerate(decisions, 1):
        label = f"decisions[{index}]"
        expected = {"id", "path", "sha256", "title", "date", "status", "scope", "owner", "supersedes"}
        if not isinstance(decision, dict) or set(decision) != expected:
            raise ArchitectureMapError(f"{label} has an invalid shape")
        decision_id = _id(decision.get("id"), f"{label}.id")
        if decision_id in decision_ids:
            raise ArchitectureMapError(f"Duplicate decision ID: {decision_id}")
        decision_ids.add(decision_id)
        _text(decision.get("path"), f"{label}.path", 260)
        digest = _text(decision.get("sha256"), f"{label}.sha256", 64)
        if not SHA256.fullmatch(digest):
            raise ArchitectureMapError(f"{label}.sha256 is invalid")
        _text(decision.get("title"), f"{label}.title")
        if not isinstance(decision.get("date"), str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", decision["date"]):
            raise ArchitectureMapError(f"{label}.date must use YYYY-MM-DD")
        status = decision.get("status")
        if status not in DECISION_STATUSES:
            raise ArchitectureMapError(f"{label}.status is invalid")
        decision_statuses[decision_id] = status
        _text(decision.get("scope"), f"{label}.scope")
        _text(decision.get("owner"), f"{label}.owner")
        supersedes[decision_id] = _unique_strings(decision.get("supersedes"), f"{label}.supersedes", 64)
        if project_root is not None:
            decision_path = _relative_file(project_root, decision["path"], f"{label}.path")
            if not decision_path.is_file() or sha256_file(decision_path) != digest:
                raise ArchitectureMapError(f"Architecture decision is missing or stale: {decision['path']}")
    for decision_id, previous_ids in supersedes.items():
        if decision_id in previous_ids or any(previous not in decision_ids for previous in previous_ids):
            raise ArchitectureMapError(f"Decision {decision_id} has invalid supersession links")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(decision_id: str) -> None:
        if decision_id in visiting:
            raise ArchitectureMapError(f"Decision supersession cycle contains {decision_id}")
        if decision_id in visited:
            return
        visiting.add(decision_id)
        for previous in supersedes[decision_id]:
            visit(previous)
        visiting.remove(decision_id)
        visited.add(decision_id)

    for decision_id in decision_ids:
        visit(decision_id)

    documentation = model.get("documentation")
    if not isinstance(documentation, list):
        raise ArchitectureMapError("documentation must be a list")
    documentation_ids: set[str] = set()
    for index, document in enumerate(documentation, 1):
        label = f"documentation[{index}]"
        if not isinstance(document, dict) or set(document) != {"id", "path", "sha256", "scope"}:
            raise ArchitectureMapError(f"{label} has an invalid shape")
        document_id = _id(document.get("id"), f"{label}.id")
        if document_id in documentation_ids:
            raise ArchitectureMapError(f"Duplicate documentation ID: {document_id}")
        documentation_ids.add(document_id)
        _text(document.get("path"), f"{label}.path", 260)
        digest = _text(document.get("sha256"), f"{label}.sha256", 64)
        if not SHA256.fullmatch(digest):
            raise ArchitectureMapError(f"{label}.sha256 is invalid")
        _text(document.get("scope"), f"{label}.scope")
        if project_root is not None:
            document_path = _relative_file(project_root, document["path"], f"{label}.path")
            if not document_path.is_file() or sha256_file(document_path) != digest:
                raise ArchitectureMapError(f"Architecture documentation is missing or stale: {document['path']}")

    def decision_references(value: object, label: str, status: str) -> list[str]:
        references = _unique_strings(value, label, 64)
        if any(reference not in decision_ids for reference in references):
            raise ArchitectureMapError(f"{label} contains an unknown decision ID")
        if status == "accepted" and (
            not references or not any(decision_statuses[reference] == "Accepted" for reference in references)
        ):
            raise ArchitectureMapError(f"{label} must cite an Accepted decision for accepted architecture")
        return references

    elements = model.get("elements")
    if not isinstance(elements, list) or not elements:
        raise ArchitectureMapError("elements must be a non-empty list")
    element_ids: set[str] = set()
    parents: dict[str, str] = {}
    for index, element in enumerate(elements, 1):
        label = f"elements[{index}]"
        expected = {
            "id", "type", "name", "description", "status", "ownership", "technology",
            "evidence", "decision_refs", "tags", "properties", "perspectives", "url", "group", "archetype"
        }
        if isinstance(element, dict) and "parent" in element:
            expected.add("parent")
        if not isinstance(element, dict) or set(element) != expected:
            raise ArchitectureMapError(f"{label} has an invalid shape")
        element_id = _id(element.get("id"), f"{label}.id")
        if element_id in element_ids:
            raise ArchitectureMapError(f"Duplicate element ID: {element_id}")
        element_ids.add(element_id)
        if element.get("type") not in ELEMENT_TYPES:
            raise ArchitectureMapError(f"{label}.type is invalid")
        _text(element.get("name"), f"{label}.name", 240)
        _text(element.get("description"), f"{label}.description")
        if element.get("status") not in STATUSES:
            raise ArchitectureMapError(f"{label}.status is invalid")
        _text(element.get("ownership"), f"{label}.ownership", 240, allow_empty=True)
        _text(element.get("technology"), f"{label}.technology", 240, allow_empty=True)
        _unique_strings(element.get("evidence"), f"{label}.evidence", 64)
        decision_references(element.get("decision_refs"), f"{label}.decision_refs", element["status"])
        _unique_strings(element.get("tags"), f"{label}.tags")
        _properties(element.get("properties"), f"{label}.properties")
        _perspectives(element.get("perspectives"), f"{label}.perspectives")
        _text(element.get("url"), f"{label}.url", 1000, allow_empty=True)
        _text(element.get("group"), f"{label}.group", 240, allow_empty=True)
        _text(element.get("archetype"), f"{label}.archetype", 240, allow_empty=True)
        if "parent" in element:
            parents[element_id] = _id(element.get("parent"), f"{label}.parent")
    for element_id, parent in parents.items():
        if parent not in element_ids or parent == element_id:
            raise ArchitectureMapError(f"Element {element_id} has invalid parent {parent}")

    constraints = model.get("constraints")
    if not isinstance(constraints, list):
        raise ArchitectureMapError("constraints must be a list")
    constraint_ids: set[str] = set()
    for index, constraint in enumerate(constraints, 1):
        label = f"constraints[{index}]"
        expected = {"id", "statement", "status", "applies_to", "evidence", "decision_refs"}
        if not isinstance(constraint, dict) or set(constraint) != expected:
            raise ArchitectureMapError(f"{label} has an invalid shape")
        constraint_id = _id(constraint.get("id"), f"{label}.id")
        if constraint_id in constraint_ids:
            raise ArchitectureMapError(f"Duplicate constraint ID: {constraint_id}")
        constraint_ids.add(constraint_id)
        _text(constraint.get("statement"), f"{label}.statement")
        status = constraint.get("status")
        if status not in STATUSES:
            raise ArchitectureMapError(f"{label}.status is invalid")
        for element_id in _unique_strings(constraint.get("applies_to"), f"{label}.applies_to", 64):
            if element_id not in element_ids:
                raise ArchitectureMapError(f"{label} references missing element {element_id}")
        _unique_strings(constraint.get("evidence"), f"{label}.evidence", 64)
        decision_references(constraint.get("decision_refs"), f"{label}.decision_refs", status)

    relationships = model.get("relationships")
    if not isinstance(relationships, list):
        raise ArchitectureMapError("relationships must be a list")
    relationship_ids: set[str] = set()
    for index, relationship in enumerate(relationships, 1):
        label = f"relationships[{index}]"
        expected = {
            "id", "source", "target", "description", "technology", "status", "evidence",
            "decision_refs", "tags", "properties", "perspectives", "url"
        }
        if not isinstance(relationship, dict) or set(relationship) != expected:
            raise ArchitectureMapError(f"{label} has an invalid shape")
        relationship_id = _id(relationship.get("id"), f"{label}.id")
        if relationship_id in relationship_ids:
            raise ArchitectureMapError(f"Duplicate relationship ID: {relationship_id}")
        relationship_ids.add(relationship_id)
        source = _id(relationship.get("source"), f"{label}.source")
        target = _id(relationship.get("target"), f"{label}.target")
        if source not in element_ids or target not in element_ids or source == target:
            raise ArchitectureMapError(f"Relationship {relationship_id} has invalid endpoints")
        _text(relationship.get("description"), f"{label}.description")
        _text(relationship.get("technology"), f"{label}.technology", 240, allow_empty=True)
        if relationship.get("status") not in STATUSES:
            raise ArchitectureMapError(f"{label}.status is invalid")
        _unique_strings(relationship.get("evidence"), f"{label}.evidence", 64)
        decision_references(relationship.get("decision_refs"), f"{label}.decision_refs", relationship["status"])
        _unique_strings(relationship.get("tags"), f"{label}.tags")
        _properties(relationship.get("properties"), f"{label}.properties")
        _perspectives(relationship.get("perspectives"), f"{label}.perspectives")
        _text(relationship.get("url"), f"{label}.url", 1000, allow_empty=True)

    views = model.get("views")
    if not isinstance(views, list) or len(views) < 2:
        raise ArchitectureMapError("views must contain at least System Context and Domain Context views")
    view_keys: set[str] = set()
    view_types: set[str] = set()
    for index, view in enumerate(views, 1):
        label = f"views[{index}]"
        expected = {
            "key", "type", "title", "description", "scope", "elements", "relationships",
            "decision_refs", "filters", "order", "layout", "animations", "properties"
        }
        if not isinstance(view, dict) or set(view) != expected:
            raise ArchitectureMapError(f"{label} has an invalid shape")
        key = _id(view.get("key"), f"{label}.key")
        if key in view_keys:
            raise ArchitectureMapError(f"Duplicate view key: {key}")
        view_keys.add(key)
        view_type = view.get("type")
        if view_type not in VIEW_TYPES:
            raise ArchitectureMapError(f"{label}.type is invalid")
        view_types.add(view_type)
        _text(view.get("title"), f"{label}.title")
        _text(view.get("description"), f"{label}.description", allow_empty=True)
        scope = _text(view.get("scope"), f"{label}.scope", 240, allow_empty=True)
        if view_type == "system-context" and scope not in element_ids:
            raise ArchitectureMapError(f"System Context view {key} must name an element scope")
        for element_id in _unique_strings(view.get("elements"), f"{label}.elements", 64):
            if element_id not in element_ids:
                raise ArchitectureMapError(f"View {key} references missing element {element_id}")
        for relationship_id in _unique_strings(view.get("relationships"), f"{label}.relationships", 64):
            if relationship_id not in relationship_ids:
                raise ArchitectureMapError(f"View {key} references missing relationship {relationship_id}")
        decision_references(view.get("decision_refs"), f"{label}.decision_refs", "proposed")
        _unique_strings(view.get("filters"), f"{label}.filters")
        for ordered_id in _unique_strings(view.get("order"), f"{label}.order", 64):
            if ordered_id not in element_ids and ordered_id not in relationship_ids:
                raise ArchitectureMapError(f"View {key} order references missing identity {ordered_id}")
        _properties(view.get("layout"), f"{label}.layout")
        animations = view.get("animations")
        if not isinstance(animations, list):
            raise ArchitectureMapError(f"{label}.animations must be a list")
        for animation_index, animation in enumerate(animations, 1):
            for animated_id in _unique_strings(animation, f"{label}.animations[{animation_index}]", 64):
                if animated_id not in element_ids and animated_id not in relationship_ids:
                    raise ArchitectureMapError(f"View {key} animation references missing identity {animated_id}")
        _properties(view.get("properties"), f"{label}.properties")
    if not {"system-context", "domain-context"}.issubset(view_types):
        raise ArchitectureMapError("Architecture map requires system-context and domain-context views")

    configuration = model.get("configuration")
    if not isinstance(configuration, dict) or set(configuration) != {
        "styles", "themes", "terminology", "branding", "properties"
    }:
        raise ArchitectureMapError("configuration has an invalid shape")
    if not isinstance(configuration["styles"], list) or any(not isinstance(item, dict) for item in configuration["styles"]):
        raise ArchitectureMapError("configuration.styles must be a list of objects")
    _unique_strings(configuration["themes"], "configuration.themes", 1000)
    _properties(configuration["terminology"], "configuration.terminology")
    _properties(configuration["branding"], "configuration.branding")
    _properties(configuration["properties"], "configuration.properties")

    extensions = model.get("extensions")
    if not isinstance(extensions, list):
        raise ArchitectureMapError("extensions must be a list")
    extension_ids: set[str] = set()
    for index, extension in enumerate(extensions, 1):
        label = f"extensions[{index}]"
        if not isinstance(extension, dict) or set(extension) != {"id", "kind", "content", "policy", "source"}:
            raise ArchitectureMapError(f"{label} has an invalid shape")
        extension_id = _id(extension.get("id"), f"{label}.id")
        if extension_id in extension_ids:
            raise ArchitectureMapError(f"Duplicate extension ID: {extension_id}")
        extension_ids.add(extension_id)
        _text(extension.get("kind"), f"{label}.kind")
        content = _text(extension.get("content"), f"{label}.content", 65536)
        if extension.get("policy") not in {"preserve", "blocked-executable", "approved-external"}:
            raise ArchitectureMapError(f"{label}.policy is invalid")
        if re.match(r"^!(?:script|plugin|include|extend|ref)\b", content.strip(), re.IGNORECASE) and extension.get("policy") == "preserve":
            raise ArchitectureMapError(
                f"{label} contains executable or externally resolved DSL and must be blocked or explicitly approved"
            )
        _text(extension.get("source"), f"{label}.source", 260, allow_empty=True)
    return model


class ProgramKitJsonImporter(ArchitectureMapImporter):
    id = "program-kit-json"

    def can_import(self, path: Path) -> bool:
        return path.suffix.lower() == ".json"

    def import_path(self, path: Path, base: dict | None = None) -> ImportResult:
        del base
        return ImportResult(validate_model(load_object(path)), self.id, self.version)


def _escape(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _dsl_identifier(value: str) -> str:
    """Project a Program Kit kebab-case ID into Structurizr's identifier alphabet."""
    return value.replace("-", "_")


def _canonical_identifier(value: str) -> str:
    candidate = value.replace("_", "-").lower()
    return _id(candidate, "Structurizr identifier")


def _tags(element: dict) -> str:
    values = list(element["tags"])
    values.extend(
        (
            f"ProgramKitId:{element['id']}",
            f"ProgramKitType:{element['type']}",
            f"ProgramKitStatus:{element['status']}",
        )
    )
    if element["ownership"]:
        values.append(f"ProgramKitOwner:{element['ownership']}")
    values.extend(f"ProgramKitDecision:{decision_id}" for decision_id in element["decision_refs"])
    return ",".join(dict.fromkeys(values))


def _element_declaration(element: dict) -> str:
    element_type = element["type"]
    if element_type == "person":
        keyword = "person"
        values = (element["name"], element["description"], _tags(element))
    elif element_type in {"software-system", "external-system", "domain-capability", "bounded-context"}:
        keyword = "softwareSystem"
        values = (element["name"], element["description"], _tags(element))
    elif element_type in {"container", "data-store"}:
        keyword = "container"
        values = (element["name"], element["description"], element["technology"], _tags(element))
    elif element_type == "component":
        keyword = "component"
        values = (element["name"], element["description"], element["technology"], _tags(element))
    else:
        raise ArchitectureMapError(f"No Structurizr DSL declaration for {element_type}")
    return f"{_dsl_identifier(element['id'])} = {keyword} " + " ".join(_escape(value) for value in values)


class StructurizrDslExporter(ArchitectureMapExporter):
    id = "structurizr-dsl"

    def export(self, model: dict) -> str:
        validate_model(model)
        unsupported = sorted(
            element["id"] for element in model["elements"] if element["type"] not in SUPPORTED_DSL_ELEMENT_TYPES
        )
        if unsupported:
            raise ArchitectureMapError(
                "Structurizr DSL intake projection cannot represent these detailed elements yet: "
                + ", ".join(unsupported)
            )
        by_id = {element["id"]: element for element in model["elements"]}
        children: dict[str, list[dict]] = {}
        roots: list[dict] = []
        for element in model["elements"]:
            parent = element.get("parent")
            if parent:
                children.setdefault(parent, []).append(element)
            else:
                roots.append(element)
        for element in model["elements"]:
            element_type = element["type"]
            parent = by_id.get(element.get("parent", ""))
            if element_type in {"container", "data-store"} and (
                parent is None
                or parent["type"] not in {"software-system", "external-system", "domain-capability", "bounded-context"}
            ):
                raise ArchitectureMapError(f"C4 container {element['id']} requires a software-system parent")
            if element_type == "component" and (
                parent is None or parent["type"] not in {"container", "data-store"}
            ):
                raise ArchitectureMapError(f"C4 component {element['id']} requires a container parent")

        def render_element(element: dict, depth: int) -> list[str]:
            nested = children.get(element["id"], [])
            prefix = "    " * depth
            declaration = prefix + _element_declaration(element)
            if not nested:
                return [declaration]
            rendered = [declaration + " {"]
            for child in nested:
                rendered.extend(render_element(child, depth + 1))
            rendered.append(prefix + "}")
            return rendered
        lines = [
            f"workspace {_escape(model['title'])} {_escape('Program Kit C4-aligned intake model')} {{",
        ]
        for directory in sorted({Path(item["path"]).parent.as_posix() for item in model["documentation"]}):
            lines.append(f"    !docs {_escape(directory)}")
        for directory in sorted({Path(item["path"]).parent.as_posix() for item in model["decisions"]}):
            lines.append(f"    !adrs {_escape(directory)}")
        for extension in model["extensions"]:
            if extension["policy"] == "blocked-executable":
                lines.append(f"    // BLOCKED {extension['kind']}: {extension['content']}")
            else:
                lines.append("    " + extension["content"])
        lines.append("    model {")
        for element in roots:
            lines.extend(render_element(element, 2))
        for relationship in model["relationships"]:
            tags = ",".join(
                dict.fromkeys(
                    [
                        *relationship["tags"],
                        f"ProgramKitId:{relationship['id']}",
                        f"ProgramKitStatus:{relationship['status']}",
                        *(f"ProgramKitDecision:{decision_id}" for decision_id in relationship["decision_refs"]),
                    ]
                )
            )
            lines.append(
                f"        {_dsl_identifier(relationship['id'])} = "
                f"{_dsl_identifier(relationship['source'])} -> {_dsl_identifier(relationship['target'])} "
                f"{_escape(relationship['description'])} {_escape(relationship['technology'])} {_escape(tags)}"
            )
        lines.extend(("    }", "", "    views {"))
        for view in model["views"]:
            if view["type"] == "system-context":
                lines.append(
                    f"        systemContext {_dsl_identifier(view['scope'])} {_escape(view['key'])} {{"
                )
            elif view["type"] in {"system-landscape", "domain-context"}:
                lines.append(f"        systemLandscape {_escape(view['key'])} {{")
            elif view["type"] in {"container", "component"}:
                lines.append(
                    f"        {view['type']} {_dsl_identifier(view['scope'])} {_escape(view['key'])} {{"
                )
            else:
                raise ArchitectureMapError(
                    f"Structurizr DSL exporter does not yet render {view['type']} view {view['key']}; "
                    "the canonical model remains intact"
                )
            if view["elements"]:
                lines.append(
                    "            include "
                    + " ".join(_dsl_identifier(element_id) for element_id in view["elements"])
                )
            lines.extend(("            autolayout lr", "        }"))
        lines.extend(("    }", "}", ""))
        return "\n".join(lines)


DSL_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
ELEMENT_LINE = re.compile(
    rf'^({DSL_IDENTIFIER})\s*=\s*(person|softwareSystem)\s+("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")\s*(\{{)?\s*$'
)
DETAIL_ELEMENT_LINE = re.compile(
    rf'^({DSL_IDENTIFIER})\s*=\s*(container|component)\s+("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")\s*(\{{)?\s*$'
)
RELATIONSHIP_LINE = re.compile(
    rf'^({DSL_IDENTIFIER})\s*=\s*({DSL_IDENTIFIER})\s*->\s*({DSL_IDENTIFIER})\s+("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")\s+("(?:[^"\\]|\\.)*")\s*$'
)
SYSTEM_CONTEXT_LINE = re.compile(
    rf'^systemContext\s+({DSL_IDENTIFIER})\s+("(?:[^"\\]|\\.)*")\s*\{{$'
)
SYSTEM_LANDSCAPE_LINE = re.compile(r'^systemLandscape\s+("(?:[^"\\]|\\.)*")\s*\{$')
SCOPED_STATIC_VIEW_LINE = re.compile(
    rf'^(container|component)\s+({DSL_IDENTIFIER})\s+("(?:[^"\\]|\\.)*")\s*\{{$'
)
WORKSPACE_LINE = re.compile(
    r'^workspace\s+("(?:[^"\\]|\\.)*")(?:\s+("(?:[^"\\]|\\.)*"))?\s*\{$'
)
BLOCKED_EXTENSION_LINE = re.compile(r"^//\s*BLOCKED\s+([a-z0-9-]+):\s*(.+)$", re.IGNORECASE)


def _quoted(token: str) -> str:
    try:
        value = json.loads(token)
    except json.JSONDecodeError as exc:
        raise ArchitectureMapError(f"Invalid quoted Structurizr DSL value: {token}") from exc
    return _text(value, "Structurizr DSL value", 500, allow_empty=True)


def _tag_metadata(tags: str, fallback_type: str) -> tuple[str, str, str, list[str], list[str], str]:
    element_type = fallback_type
    status = "proposed"
    ownership = ""
    canonical_id = ""
    retained: list[str] = []
    decision_refs: list[str] = []
    for raw in filter(None, (item.strip() for item in tags.split(","))):
        if raw.startswith("ProgramKitId:"):
            canonical_id = _id(raw.split(":", 1)[1], "ProgramKitId tag")
        elif raw.startswith("ProgramKitType:"):
            element_type = raw.split(":", 1)[1]
        elif raw.startswith("ProgramKitStatus:"):
            status = raw.split(":", 1)[1]
        elif raw.startswith("ProgramKitOwner:"):
            ownership = raw.split(":", 1)[1]
        elif raw.startswith("ProgramKitDecision:"):
            decision_refs.append(raw.split(":", 1)[1])
        else:
            retained.append(raw)
    if element_type not in SUPPORTED_DSL_ELEMENT_TYPES or status not in STATUSES:
        raise ArchitectureMapError("Structurizr DSL contains unsupported Program Kit type or status metadata")
    return element_type, status, ownership, retained, decision_refs, canonical_id


def _extension(content: str, policy: str, source: str, kind: str = "structurizr-dsl") -> dict:
    digest = hashlib.sha256(f"{kind}\0{content}".encode("utf-8")).hexdigest()[:12]
    return {
        "id": f"dsl-extension-{digest}",
        "kind": kind,
        "content": content,
        "policy": policy,
        "source": source,
    }


class StructurizrDslImporter(ArchitectureMapImporter):
    id = "structurizr-dsl"

    def can_import(self, path: Path) -> bool:
        return path.suffix.lower() in {".dsl", ".structurizr"}

    def import_path(self, path: Path, base: dict | None = None) -> ImportResult:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            raise ArchitectureMapError(f"Cannot read Structurizr DSL {path}: {exc}") from exc
        elements: list[dict] = []
        relationships: list[dict] = []
        views: list[dict] = []
        imported_extensions: list[dict] = []
        diagnostics: list[str] = []
        title_from_dsl = ""
        base_elements = {item["id"]: item for item in (base or {}).get("elements", [])}
        base_relationships = {item["id"]: item for item in (base or {}).get("relationships", [])}
        identifiers: dict[str, str] = {}
        current_view: dict | None = None
        element_stack: list[str] = []
        in_model = False
        in_views = False
        for line_number, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            blocked = BLOCKED_EXTENSION_LINE.fullmatch(line)
            if blocked:
                imported_extensions.append(
                    _extension(
                        blocked.group(2),
                        "blocked-executable",
                        f"{path.as_posix()}:{line_number}",
                        blocked.group(1).lower(),
                    )
                )
                continue
            if line.startswith("//"):
                continue
            if line == "model {":
                in_model = True
                continue
            if line == "views {":
                in_views = True
                continue
            workspace = WORKSPACE_LINE.fullmatch(line)
            if workspace:
                title_from_dsl = _quoted(workspace.group(1))
                continue
            if line == "}":
                if line == "}" and current_view is not None:
                    views.append(current_view)
                    current_view = None
                elif line == "}" and in_model and element_stack:
                    element_stack.pop()
                elif line == "}" and in_model:
                    in_model = False
                elif line == "}" and in_views:
                    in_views = False
                continue
            if in_model:
                match = ELEMENT_LINE.fullmatch(line)
                if match:
                    dsl_element_id, keyword, name, description, tags, opens = match.groups()
                    element_type, status, ownership, retained, decision_refs, tagged_id = _tag_metadata(
                        _quoted(tags), "person" if keyword == "person" else "software-system"
                    )
                    element_id = tagged_id or _canonical_identifier(dsl_element_id)
                    identifiers[dsl_element_id] = element_id
                    previous = base_elements.get(element_id, {})
                    element = {
                            "id": element_id,
                            "type": element_type,
                            "name": _quoted(name),
                            "description": _quoted(description),
                            "status": status,
                            "ownership": ownership,
                            "technology": previous.get("technology", ""),
                            "evidence": previous.get("evidence", []),
                            "decision_refs": decision_refs or previous.get("decision_refs", []),
                            "tags": retained,
                            "properties": previous.get("properties", {}),
                            "perspectives": previous.get("perspectives", []),
                            "url": previous.get("url", ""),
                            "group": previous.get("group", ""),
                            "archetype": previous.get("archetype", ""),
                        }
                    if element_stack:
                        raise ArchitectureMapError(
                            f"Top-level C4 element {element_id} cannot be nested at line {line_number}"
                        )
                    elements.append(element)
                    if opens:
                        element_stack.append(element_id)
                    continue
                match = DETAIL_ELEMENT_LINE.fullmatch(line)
                if match:
                    dsl_element_id, keyword, name, description, technology, tags, opens = match.groups()
                    if not element_stack:
                        raise ArchitectureMapError(
                            f"Detailed C4 element at line {line_number} has no parent"
                        )
                    fallback_type = "container" if keyword == "container" else "component"
                    element_type, status, ownership, retained, decision_refs, tagged_id = _tag_metadata(
                        _quoted(tags), fallback_type
                    )
                    if element_type not in {"container", "component", "data-store"}:
                        raise ArchitectureMapError(
                            f"Detailed C4 element at line {line_number} has incompatible Program Kit type"
                        )
                    element_id = tagged_id or _canonical_identifier(dsl_element_id)
                    identifiers[dsl_element_id] = element_id
                    previous = base_elements.get(element_id, {})
                    elements.append(
                        {
                            "id": element_id,
                            "type": element_type,
                            "name": _quoted(name),
                            "description": _quoted(description),
                            "status": status,
                            "ownership": ownership,
                            "technology": _quoted(technology),
                            "parent": element_stack[-1],
                            "evidence": previous.get("evidence", []),
                            "decision_refs": decision_refs or previous.get("decision_refs", []),
                            "tags": retained,
                            "properties": previous.get("properties", {}),
                            "perspectives": previous.get("perspectives", []),
                            "url": previous.get("url", ""),
                            "group": previous.get("group", ""),
                            "archetype": previous.get("archetype", ""),
                        }
                    )
                    if opens:
                        element_stack.append(element_id)
                    continue
                match = RELATIONSHIP_LINE.fullmatch(line)
                if match:
                    dsl_rel_id, dsl_source, dsl_target, description, technology, tags = match.groups()
                    raw_tags = _quoted(tags)
                    status = "proposed"
                    tagged_id = ""
                    retained: list[str] = []
                    decision_refs: list[str] = []
                    for tag in filter(None, (item.strip() for item in raw_tags.split(","))):
                        if tag.startswith("ProgramKitId:"):
                            tagged_id = _id(tag.split(":", 1)[1], "ProgramKitId tag")
                        elif tag.startswith("ProgramKitStatus:"):
                            status = tag.split(":", 1)[1]
                        elif tag.startswith("ProgramKitDecision:"):
                            decision_refs.append(tag.split(":", 1)[1])
                        else:
                            retained.append(tag)
                    if status not in STATUSES:
                        raise ArchitectureMapError(f"Invalid relationship status at line {line_number}")
                    rel_id = tagged_id or _canonical_identifier(dsl_rel_id)
                    source = identifiers.get(dsl_source, _canonical_identifier(dsl_source))
                    target = identifiers.get(dsl_target, _canonical_identifier(dsl_target))
                    previous = base_relationships.get(rel_id, {})
                    relationships.append(
                        {
                            "id": rel_id,
                            "source": source,
                            "target": target,
                            "description": _quoted(description),
                            "technology": _quoted(technology),
                            "status": status,
                            "evidence": previous.get("evidence", []),
                            "decision_refs": decision_refs or previous.get("decision_refs", []),
                            "tags": retained,
                            "properties": previous.get("properties", {}),
                            "perspectives": previous.get("perspectives", []),
                            "url": previous.get("url", ""),
                        }
                    )
                    continue
                raise ArchitectureMapError(
                    f"Unsupported Structurizr DSL model statement at line {line_number}: {line}"
                )
            if in_views:
                match = SYSTEM_CONTEXT_LINE.fullmatch(line)
                if match:
                    current_view = {
                        "key": _quoted(match.group(2)),
                        "type": "system-context",
                        "title": "System Context",
                        "description": "",
                        "scope": identifiers.get(match.group(1), _canonical_identifier(match.group(1))),
                        "elements": [],
                        "relationships": [],
                        "decision_refs": [],
                        "filters": [],
                        "order": [],
                        "layout": {"rankDirection": "lr"},
                        "animations": [],
                        "properties": {},
                    }
                    continue
                match = SYSTEM_LANDSCAPE_LINE.fullmatch(line)
                if match:
                    key = _quoted(match.group(1))
                    current_view = {
                        "key": key,
                        "type": "domain-context" if key == "domain-context" else "system-landscape",
                        "title": "Domain Context Map" if key == "domain-context" else key,
                        "description": "",
                        "scope": "",
                        "elements": [],
                        "relationships": [],
                        "decision_refs": [],
                        "filters": [],
                        "order": [],
                        "layout": {"rankDirection": "lr"},
                        "animations": [],
                        "properties": {},
                    }
                    continue
                match = SCOPED_STATIC_VIEW_LINE.fullmatch(line)
                if match:
                    view_type, dsl_scope, key_token = match.groups()
                    key = _quoted(key_token)
                    current_view = {
                        "key": key,
                        "type": view_type,
                        "title": key,
                        "description": "",
                        "scope": identifiers.get(dsl_scope, _canonical_identifier(dsl_scope)),
                        "elements": [],
                        "relationships": [],
                        "decision_refs": [],
                        "filters": [],
                        "order": [],
                        "layout": {"rankDirection": "lr"},
                        "animations": [],
                        "properties": {},
                    }
                    continue
                if current_view is not None and line.startswith("include "):
                    current_view["elements"] = [
                        identifiers.get(token, _canonical_identifier(token))
                        for token in line.split()[1:]
                    ]
                    continue
                if current_view is not None and line.startswith("autolayout "):
                    continue
                raise ArchitectureMapError(
                    f"Unsupported Structurizr DSL view statement at line {line_number}: {line}"
                )
            if line.startswith("!docs ") or line.startswith("!adrs "):
                diagnostics.append(
                    f"Observed {line.split(maxsplit=1)[0]} at line {line_number}; file hashes require canonical catalog entries"
                )
                continue
            if line.startswith("!"):
                directive = line.split(maxsplit=1)[0].lstrip("!").lower()
                policy = (
                    "blocked-executable"
                    if directive in {"script", "plugin", "include", "extend", "ref"}
                    else "preserve"
                )
                imported_extensions.append(
                    _extension(line, policy, f"{path.as_posix()}:{line_number}", f"structurizr-{directive}")
                )
                diagnostics.append(f"Preserved Structurizr directive from line {line_number} as {policy}")
                continue
            raise ArchitectureMapError(
                f"Unsupported Structurizr DSL statement at line {line_number}: {line}"
            )
        if current_view is not None:
            raise ArchitectureMapError("Structurizr DSL ended inside a view")
        if not elements:
            raise ArchitectureMapError("Structurizr DSL did not contain any supported C4 elements")
        if base:
            parsed_element_ids = {item["id"] for item in elements}
            elements.extend(item for item in base.get("elements", []) if item["id"] not in parsed_element_ids)
            parsed_relationship_ids = {item["id"] for item in relationships}
            relationships.extend(
                item for item in base.get("relationships", []) if item["id"] not in parsed_relationship_ids
            )
            base_views = {item["key"]: item for item in base.get("views", [])}
            for view in views:
                previous = base_views.get(view["key"], {})
                for key in ("title", "description", "decision_refs", "filters", "order", "layout", "animations", "properties"):
                    if key in previous and (key not in view or view[key] in ("", [], {})):
                        view[key] = previous[key]
            parsed_view_keys = {item["key"] for item in views}
            views.extend(item for item in base.get("views", []) if item["key"] not in parsed_view_keys)
        rel_ids = {item["id"] for item in relationships}
        element_ids = {item["id"] for item in elements}
        for view in views:
            view["relationships"] = [
                item["id"]
                for item in relationships
                if item["source"] in view["elements"] and item["target"] in view["elements"]
            ]
        title = (base or {}).get("title") or title_from_dsl or path.stem
        extensions_by_signature: dict[tuple[str, str, str], dict] = {}
        for extension in [*(base or {}).get("extensions", []), *imported_extensions]:
            signature = (extension["kind"], extension["content"], extension["policy"])
            extensions_by_signature.setdefault(signature, extension)
        model = {
            "schema_version": SCHEMA_VERSION,
            "model_id": (base or {}).get("model_id", "imported-architecture"),
            "title": title,
            "sources": list((base or {}).get("sources", [])),
            "decisions": list((base or {}).get("decisions", [])),
            "documentation": list((base or {}).get("documentation", [])),
            "constraints": list((base or {}).get("constraints", [])),
            "elements": elements,
            "relationships": relationships,
            "views": views,
            "configuration": dict(
                (base or {}).get(
                    "configuration",
                    {"styles": [], "themes": [], "terminology": {}, "branding": {}, "properties": {}},
                )
            ),
            "extensions": list(extensions_by_signature.values()),
        }
        validate_model(model)
        diagnostics.insert(
            0,
            f"Imported {len(element_ids)} element(s), {len(rel_ids)} relationship(s), and {len(views)} view(s)",
        )
        return ImportResult(model, self.id, self.version, tuple(diagnostics))


IMPORTERS: tuple[ArchitectureMapImporter, ...] = (ProgramKitJsonImporter(), StructurizrDslImporter())
EXPORTERS: dict[str, ArchitectureMapExporter] = {"structurizr-dsl": StructurizrDslExporter()}


def choose_importer(path: Path, format_name: str) -> ArchitectureMapImporter:
    if format_name != "auto":
        matches = [item for item in IMPORTERS if item.id == format_name]
    else:
        matches = [item for item in IMPORTERS if item.can_import(path)]
    if len(matches) != 1:
        raise ArchitectureMapError(f"No unambiguous architecture-map importer for {path}")
    return matches[0]


def write_text(path: Path, value: str, force: bool) -> None:
    if path.exists() and not force:
        raise ArchitectureMapError(f"Refusing to overwrite existing output without --force: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Validate and translate Program Kit architecture maps.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--map", required=True)
    validate_parser.add_argument("--project-root", default=".")
    validate_parser.add_argument("--verify-sources", action="store_true")
    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--source", required=True)
    import_parser.add_argument("--format", default="auto")
    import_parser.add_argument("--base")
    import_parser.add_argument("--output", required=True)
    import_parser.add_argument("--force", action="store_true")
    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--map", required=True)
    export_parser.add_argument("--format", default="structurizr-dsl")
    export_parser.add_argument("--output", required=True)
    export_parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            model = load_object(Path(args.map))
            project_root = Path(args.project_root).resolve() if args.verify_sources else None
            validate_model(model, project_root)
            print(
                f"Program Kit architecture map is valid: {len(model['elements'])} element(s), "
                f"{len(model['relationships'])} relationship(s), {len(model['views'])} view(s)"
            )
        elif args.command == "import":
            source = Path(args.source)
            base = load_object(Path(args.base)) if args.base else None
            result = choose_importer(source, args.format).import_path(source, base)
            write_text(
                Path(args.output),
                json.dumps(result.model, indent=2, ensure_ascii=False) + "\n",
                args.force,
            )
            print("; ".join(result.diagnostics) or f"Imported with {result.importer_id}")
        else:
            model = validate_model(load_object(Path(args.map)))
            exporter = EXPORTERS.get(args.format)
            if exporter is None:
                raise ArchitectureMapError(f"Unknown architecture-map exporter: {args.format}")
            write_text(Path(args.output), exporter.export(model), args.force)
            print(f"Exported architecture map with {exporter.id} {exporter.version}: {args.output}")
    except (ArchitectureMapError, OSError, UnicodeError) as exc:
        print(f"Program Kit architecture map failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
