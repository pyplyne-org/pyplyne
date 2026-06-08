from __future__ import annotations

import dataclasses
import inspect
import re
from pathlib import Path
from typing import Any

import pyplyne as pyplyne_api

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = PROJECT_ROOT / "docs" / "generated-python-api-reference.md"
SECTION_NAMES = {"Args", "Attributes", "Returns", "Raises"}
MAX_INLINE_SIGNATURE_LENGTH = 88


def markdown_text(value: str) -> str:
    return value.replace("|", "\\|").strip()


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_docstring(obj: Any) -> dict[str, Any]:
    raw = inspect.getdoc(obj) or "No docstring available."
    sections: dict[str, list[str]] = {}
    summary_lines: list[str] = []
    current_section: str | None = None

    for line in raw.splitlines():
        stripped = line.strip()
        heading = stripped[:-1] if stripped.endswith(":") else ""
        if heading in SECTION_NAMES:
            current_section = heading
            sections[current_section] = []
            continue
        if current_section:
            sections[current_section].append(line)
        else:
            summary_lines.append(line)

    return {
        "summary": "\n".join(summary_lines).strip(),
        "args": parse_named_entries(sections.get("Args", [])),
        "attributes": parse_named_entries(sections.get("Attributes", [])),
        "returns": parse_typed_entries(sections.get("Returns", [])),
        "raises": parse_typed_entries(sections.get("Raises", [])),
    }


def docstring_summary(obj: Any) -> str:
    raw = inspect.getdoc(obj)
    if not raw:
        raise ValueError(f"Public API object {obj!r} is missing a docstring")
    for line in raw.splitlines():
        if line.strip():
            return compact_text(line)
    raise ValueError(f"Public API object {obj!r} has an empty docstring")


def parse_named_entries(lines: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    current_name: str | None = None
    current_description: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", stripped)
        if match:
            if current_name is not None:
                entries.append((current_name, " ".join(current_description).strip()))
            current_name = match.group(1)
            current_description = [match.group(2)]
        elif current_name is not None:
            current_description.append(stripped)

    if current_name is not None:
        entries.append((current_name, " ".join(current_description).strip()))
    return entries


def parse_typed_entries(lines: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    current_type: str | None = None
    current_description: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^([^:]+):\s*(.*)$", stripped)
        if match:
            if current_type is not None:
                entries.append((current_type, " ".join(current_description).strip()))
            current_type = match.group(1)
            current_description = [match.group(2)]
        elif current_type is not None:
            current_description.append(stripped)
        else:
            entries.append(("", stripped))

    if current_type is not None:
        entries.append((current_type, " ".join(current_description).strip()))
    return entries


def wrapped_signature(name: str, signature: inspect.Signature) -> str:
    lines = [f"{name}("]
    parameters = list(signature.parameters.values())
    has_var_positional = any(
        parameter.kind is inspect.Parameter.VAR_POSITIONAL for parameter in parameters
    )
    inserted_keyword_only_marker = False

    for index, parameter in enumerate(parameters):
        if (
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            and not has_var_positional
            and not inserted_keyword_only_marker
        ):
            lines.append("    *,")
            inserted_keyword_only_marker = True

        lines.append(f"    {parameter},")

        next_parameter = parameters[index + 1] if index + 1 < len(parameters) else None
        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY and (
            next_parameter is None
            or next_parameter.kind is not inspect.Parameter.POSITIONAL_ONLY
        ):
            lines.append("    /,")

    signature_text = str(signature)
    return_suffix = signature_text[signature_text.rfind(")") + 1 :]
    return "\n".join([*lines, f"){return_suffix}"])


def formatted_signature(name: str, signature: inspect.Signature) -> str:
    inline_signature = f"{name}{signature}"
    if len(inline_signature) <= MAX_INLINE_SIGNATURE_LENGTH:
        return inline_signature
    return wrapped_signature(name, signature)


def fenced_signature(name: str, obj: Any) -> str:
    try:
        signature = inspect.signature(obj)
    except (TypeError, ValueError):
        rendered_signature = name
    else:
        rendered_signature = formatted_signature(name, signature)
    return f"```python\n{rendered_signature}\n```"


def parameters_table(entries: list[tuple[str, str]]) -> str:
    rows = [
        "| Name | Description |",
        "| --- | --- |",
    ]
    for name, description in entries:
        rows.append(f"| `{name}` | {markdown_text(description)} |")
    return "\n".join(rows)


def typed_table(type_header: str, entries: list[tuple[str, str]]) -> str:
    rows = [
        f"| {type_header} | Description |",
        "| --- | --- |",
    ]
    for entry_type, description in entries:
        label = f"`{entry_type}`" if entry_type else ""
        rows.append(f"| {label} | {markdown_text(description)} |")
    return "\n".join(rows)


def rendered_docstring(obj: Any, heading_level: int = 3) -> str:
    parsed = parse_docstring(obj)
    heading = "#" * heading_level
    parts = [parsed["summary"]]
    if parsed["args"]:
        parts.extend(
            ["", f"{heading} Parameters", "", parameters_table(parsed["args"])]
        )
    if parsed["returns"]:
        parts.extend(
            ["", f"{heading} Returns", "", typed_table("Type", parsed["returns"])]
        )
    if parsed["raises"]:
        parts.extend(
            ["", f"{heading} Raises", "", typed_table("Type", parsed["raises"])]
        )
    return "\n".join(parts).strip()


def function_section(name: str, obj: Any) -> str:
    return f"""## `{name}`

{fenced_signature(name, obj)}

{rendered_docstring(obj)}
"""


def dataclass_fields_section(cls: type[Any], descriptions: dict[str, str]) -> str:
    rows = [
        "| Field | Type | Default | Description |",
        "| --- | --- | --- | --- |",
    ]
    for field in dataclasses.fields(cls):
        default = ""
        if field.default is not dataclasses.MISSING:
            default = repr(field.default)
        elif field.default_factory is not dataclasses.MISSING:  # type: ignore[attr-defined]
            default = "<factory>"
        else:
            default = "required"
        description = markdown_text(descriptions.get(field.name, ""))
        rows.append(
            f"| `{field.name}` | `{field.type}` | `{default}` | {description} |"
        )
    return "\n".join(rows)


def property_section(cls: type[Any], property_names: list[str]) -> str:
    rows = [
        "| Property | Description |",
        "| --- | --- |",
    ]
    for property_name in property_names:
        prop = getattr(cls, property_name)
        rows.append(
            f"| `{property_name}` | {markdown_text(inspect.getdoc(prop) or '')} |"
        )
    return "\n".join(rows)


def public_exports() -> list[tuple[str, Any]]:
    return [(name, getattr(pyplyne_api, name)) for name in pyplyne_api.__all__]


def source_order(obj: Any) -> int:
    try:
        _, lineno = inspect.getsourcelines(obj)
    except (OSError, TypeError):
        return 10**9
    return lineno


def public_methods(cls: type[Any]) -> list[str]:
    methods = []
    for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        if member.__qualname__.split(".", 1)[0] != cls.__name__:
            continue
        methods.append((source_order(member), name))
    return [name for _, name in sorted(methods)]


def public_properties(cls: type[Any]) -> list[str]:
    properties = []
    for name, member in inspect.getmembers(cls):
        if name.startswith("_") or not isinstance(member, property):
            continue
        properties.append((source_order(member.fget), name))
    return [name for _, name in sorted(properties)]


def public_surface_table(exports: list[tuple[str, Any]]) -> str:
    rows = [
        "| API | Use it for |",
        "| --- | --- |",
    ]
    for name, obj in exports:
        rows.append(f"| `{name}` | {markdown_text(docstring_summary(obj))} |")
    return "\n".join(rows)


def class_section(
    cls: type[Any],
) -> str:
    parsed = parse_docstring(cls)
    attribute_descriptions = dict(parsed["attributes"])
    methods = public_methods(cls)
    properties = public_properties(cls)
    parts = [
        f"## `{cls.__name__}`",
        "",
        fenced_signature(cls.__name__, cls),
        "",
        parsed["summary"],
    ]
    init_args = parse_docstring(cls.__init__)["args"]
    if init_args and not dataclasses.is_dataclass(cls):
        parts.extend(["", "### Parameters", "", parameters_table(init_args)])
    if dataclasses.is_dataclass(cls):
        parts.extend(
            [
                "",
                "### Fields",
                "",
                dataclass_fields_section(cls, attribute_descriptions),
            ]
        )
    if properties:
        parts.extend(["", "### Properties", "", property_section(cls, properties)])
    for method_name in methods:
        method = getattr(cls, method_name)
        parts.extend(
            [
                "",
                f"### `{cls.__name__}.{method_name}`",
                "",
                fenced_signature(method_name, method),
                "",
                rendered_docstring(method, heading_level=4),
            ]
        )
    return "\n".join(parts) + "\n"


def rendered_export_section(name: str, obj: Any) -> str:
    if inspect.isclass(obj):
        return class_section(obj)
    return function_section(name, obj)


def rendered_reference() -> str:
    exports = public_exports()
    rendered_public_surface = public_surface_table(exports)
    rendered_export_sections = "\n".join(
        rendered_export_section(name, obj) for name, obj in exports
    )

    return f"""---
title: Generated Python API Reference
description: Public Python API signatures generated from the current PyPlyne package.
---

# Generated Python API Reference

This page is generated from the public Python API signatures and docstrings.
Update the package source first, then regenerate with `npm run docs:api` from
`site/`.

## Public Surface

{rendered_public_surface}

{rendered_export_sections}
"""


def main() -> None:
    OUTPUT_PATH.write_text(rendered_reference(), encoding="utf-8")
    print(f"Generated {OUTPUT_PATH.relative_to(PROJECT_ROOT)}.")


if __name__ == "__main__":
    main()
