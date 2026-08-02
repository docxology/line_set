"""Real building blocks for the Line Set suite.

Nothing in this suite uses a patching or test-double library. When a test needs
a line package that is absent, that raises on import, that exports no
vocabulary, or that nobody declared, it gets a real one: real directories and
real Python source written to a real temporary path and imported by the real
import system. When a test needs to control what the reader sees, it passes a
plain callable as ``resolver``; an ordinary function is a real object, not a
stand-in for one.

:func:`import_sandbox` is what makes that repeatable. Importing a package
changes two pieces of process-wide state — ``sys.path`` and ``sys.modules`` —
and the reader's own package discovery reads both. The context manager restores
each on exit, so no test inherits a package another test wrote.

The generated packages here are deliberately crude. They are not imitations of
the sibling line projects and they carry none of their content; they exist only
to give the binding layer something real to read a version, a registry, a
digest, and a set of enum member names from.
"""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from line_set.binding import ImportResolver, Resolution
from line_set.models import ReadCode

#: Body of the digest function written into a generated package by default.
#:
#: The generated package computes its own digest over its own registry, which
#: is what the binding layer expects to find and refuses to compute itself.
DEFAULT_DIGEST_BODY = (
    'return hashlib.sha256(repr(registry).encode("utf-8")).hexdigest()'
)


@contextmanager
def import_sandbox() -> Iterator[None]:
    """Restore ``sys.path`` and ``sys.modules`` when the block exits.

    Only modules imported inside the block are removed; nothing that was
    already imported is touched. ``invalidate_caches`` is called on the way out
    so a later block writing a package of the same name at a different path is
    not answered from the import system's directory cache.
    """
    saved_path = list(sys.path)
    saved_modules = frozenset(sys.modules)
    try:
        yield
    finally:
        sys.path[:] = saved_path
        for name in [name for name in sys.modules if name not in saved_modules]:
            del sys.modules[name]
        importlib.invalidate_caches()


@contextmanager
def environment(name: str, value: str | None) -> Iterator[None]:
    """Set or clear one environment variable for the block, then restore it.

    Environment isolation, not dependency replacement: the code under test
    reads the real ``os.environ`` through its own accessor, and what changes is
    the environment the process is genuinely running in. Nothing is substituted
    for anything, which is why this belongs here rather than being a reason to
    reach for a patching library the project bans.
    """
    missing = object()
    previous: object = os.environ.get(name, missing)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        yield
    finally:
        if previous is missing:
            os.environ.pop(name, None)
        else:
            os.environ[name] = str(previous)


def _enum_source(class_name: str, members: Sequence[str]) -> str:
    """Source for one enum class; no members is a legal and useful case."""
    lines = [f"class {class_name}(Enum):"]
    if not members:
        lines.append("    pass")
    for member in members:
        lines.append(f'    {member} = "{member.lower()}"')
    return "\n".join(lines)


def _registry_source(sizes: Mapping[str, int]) -> str:
    """Source for a registry submodule holding one tuple per requested name."""
    lines = [
        '"""A registry submodule written by the line_set test suite."""',
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True)",
        "class Item:",
        "    name: str",
        "",
    ]
    for tuple_name, size in sizes.items():
        members = ", ".join(
            f'Item("{tuple_name.lower()}-{index}")' for index in range(size)
        )
        lines.append(
            f"{tuple_name} = ({members},)"
            if size == 1
            else f"{tuple_name} = ({members})"
        )
    return "\n".join(lines)


def write_line_package(
    root: Path,
    name: str,
    tokens: Sequence[str] = (),
    *,
    version: str | None = "0.0.1",
    version_attr: str = "__version__",
    enums: Mapping[str, Sequence[str]] | None = None,
    registry_sizes: Mapping[str, int] | None = None,
    registry_source: str | None = None,
    digest_attr: str | None = "registry_digest",
    digest_body: str = DEFAULT_DIGEST_BODY,
    raise_on_import: str | None = None,
    extra_source: str = "",
) -> Path:
    """Write a real importable package under ``root`` and return its directory.

    Every knob corresponds to something the binding layer has to cope with:
    a package with no version, a version under a second attribute name, several
    enums or none, several registry tuples or none, a digest function that
    raises or returns something that is not a digest, and a package that raises
    on import. ``extra_source`` is appended last, so it can shadow anything
    written above it.
    """
    package = Path(root) / name
    package.mkdir(parents=True, exist_ok=True)

    blocks: list[str] = [
        f'"""A line package written by the line_set test suite: {name}."""',
        "",
        "import hashlib",
        "from enum import Enum",
        "",
    ]
    if version is not None:
        blocks.extend([f'{version_attr} = "{version}"', ""])

    groups: Mapping[str, Sequence[str]]
    groups = {"Vocabulary": tuple(tokens)} if enums is None else enums
    for class_name, members in groups.items():
        blocks.extend([_enum_source(class_name, members), ""])

    if registry_sizes is not None or registry_source is not None:
        source = (
            registry_source
            if registry_source is not None
            else _registry_source(dict(registry_sizes or {}))
        )
        (package / "registry.py").write_text(source + "\n", encoding="utf-8")
        blocks.extend(["from . import registry", ""])

    if digest_attr is not None:
        blocks.append(f"def {digest_attr}(registry):")
        blocks.extend(f"    {line}" for line in digest_body.splitlines())
        blocks.append("")

    if extra_source:
        blocks.extend([extra_source, ""])
    if raise_on_import is not None:
        blocks.extend([f'raise RuntimeError("{raise_on_import}")', ""])

    (package / "__init__.py").write_text("\n".join(blocks), encoding="utf-8")
    importlib.invalidate_caches()
    return package


def load_line_package(root: Path, name: str) -> ModuleType:
    """Import a package written by :func:`write_line_package`.

    Call inside :func:`import_sandbox`: this reaches the real import system
    through :class:`line_set.binding.ImportResolver`, which prepends ``root`` to
    ``sys.path`` exactly as a caller asking for that directory would.
    """
    resolution = ImportResolver([str(root)])(name)
    assert resolution.code is ReadCode.RESOLVED, resolution.detail
    assert resolution.module is not None
    return resolution.module


def resolved(name: str, module: ModuleType) -> Resolution:
    """A resolution carrying a real module."""
    return Resolution(
        name, ReadCode.RESOLVED, module, "resolved by an injected callable"
    )


def absent(name: str) -> Resolution:
    """A resolution for a package the import system did not find."""
    return Resolution(
        name, ReadCode.NOT_INSTALLED, None, "no such package in this test"
    )


def broken(
    name: str, detail: str = "import raised RuntimeError: planted"
) -> Resolution:
    """A resolution for a package that was found but raised on import."""
    return Resolution(name, ReadCode.IMPORT_FAILED, None, detail)


def canned_resolver(
    answers: Mapping[str, Resolution],
    *,
    default: Resolution | None = None,
) -> object:
    """A plain function resolver, with no way to enumerate packages.

    A resolver that cannot enumerate makes the reader's declare stage say it did
    not scan, rather than say it found nothing — which is the distinction the
    stage exists to keep.
    """

    def resolve(package_name: str) -> Resolution:
        if package_name in answers:
            return answers[package_name]
        return absent(package_name) if default is None else default

    return resolve


class ListingResolver:
    """A resolver that also enumerates the packages it knows about.

    Offering ``candidates()`` is what lets the reader look for a resolved
    package nobody declared. The listing is whatever the test says it is.
    """

    def __init__(
        self,
        answers: Mapping[str, Resolution],
        listed: Sequence[str] = (),
    ) -> None:
        self._answers = dict(answers)
        self._listed = tuple(listed)

    def __call__(self, package_name: str) -> Resolution:
        answer = self._answers.get(package_name)
        return absent(package_name) if answer is None else answer

    def candidates(self) -> tuple[str, ...]:
        """Names this resolver is willing to admit exist."""
        return tuple(sorted(self._listed))
