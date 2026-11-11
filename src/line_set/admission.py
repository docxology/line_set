"""Minimal reader admission, independent of historical ordering conventions.

This validates identities and serializable line fields before any import, and
shares nested record field admission between resolution and replay. It does not
decide whether a proposed instrument or exemption is substantively sound.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from functools import cache
from types import UnionType
from typing import get_args, get_origin, get_type_hints

from .models import LineEntry


class DeclarationError(ValueError):
    pass


def declaration_problems(lines: tuple[LineEntry, ...]) -> tuple[str, ...]:
    problems: list[str] = []
    if not lines:
        return ("declaration is empty; there is nothing to check",)
    identities: dict[str, set[str]] = {"id": set(), "package_name": set()}
    for index, entry in enumerate(lines):
        if not isinstance(entry, LineEntry):
            problems.append(f"declaration entry {index} is not a LineEntry")
            continue
        for field in fields(LineEntry):
            value = getattr(entry, field.name)
            if field.name == "opus_stage":
                valid = value is None or isinstance(value, str)
            elif field.name == "working_position":
                valid = isinstance(value, int) and not isinstance(value, bool)
            else:
                valid = isinstance(value, str) and bool(value.strip())
            if not valid:
                problems.append(f"declaration entry {index}: invalid {field.name}")
            elif field.name in identities:
                if value in identities[field.name]:
                    problems.append(f"declaration has duplicate {field.name}: {value}")
                identities[field.name].add(value)
    return tuple(problems)


def admit_declaration(lines: tuple[LineEntry, ...]) -> None:
    problems = declaration_problems(lines)
    if problems:
        raise DeclarationError("; ".join(problems))


@cache
def _record_field_types(model: type) -> dict[str, object]:
    return get_type_hints(model)


def admit_record_field(value: object, kind: object, path: str) -> None:
    """Admit declared nested model types without authenticating their values."""
    origin = get_origin(kind)
    arguments = get_args(kind)
    if origin is UnionType:
        for option in arguments:
            try:
                admit_record_field(value, option, path)
            except ValueError:
                continue
            return
    elif origin is tuple and isinstance(value, tuple):
        if len(arguments) == 2 and arguments[1] is Ellipsis:
            for index, item in enumerate(value):
                admit_record_field(item, arguments[0], f"{path}[{index}]")
            return
        if len(value) == len(arguments):
            for index, (item, expected) in enumerate(zip(value, arguments)):
                admit_record_field(item, expected, f"{path}[{index}]")
            return
    elif isinstance(kind, type):
        if is_dataclass(kind) and isinstance(value, kind):
            expected_fields = _record_field_types(kind)
            for field in fields(kind):
                admit_record_field(
                    getattr(value, field.name),
                    expected_fields[field.name],
                    f"{path}.{field.name}",
                )
            return
        if kind in (bool, int):
            if type(value) is kind:
                return
        elif isinstance(value, kind):
            return
    requirement = "booleans" if kind is bool else str(kind)
    raise ValueError(f"reading metadata field {path} requires {requirement}")
