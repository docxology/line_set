"""Minimal reader admission, independent of historical ordering conventions.

This validates identities and serializable line fields before any import. It
does not decide whether a proposed instrument or exemption is substantively sound.
"""

from __future__ import annotations

from dataclasses import fields

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
