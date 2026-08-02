"""Resolution of sibling line packages. The only module that reaches for them.

Every other module in ``line_set`` is pure structure over this package's own
declaration. This one is the single seam where the wrapper touches another
package, and it is deliberately narrow. It resolves a package by name, reads a
version string, counts a registry, asks the package for its own digest, and
collects the member names of the enums the package exports. It never calls a
sibling's evaluator, never passes it data, and never forms an opinion about
what a sibling concluded.

Absence is an ordinary outcome, not an error. A line that is not installed
yields :attr:`~line_set.models.ReadCode.NOT_INSTALLED` and no version, no
size, and no digest. A line that raises on import yields ``IMPORT_FAILED``
and the exception text. Nothing here raises out of a resolution and nothing
here invents a value for a package it could not read.

Resolution goes through the normal import system by default. Sibling source
directories are added to ``sys.path`` only when a caller explicitly asks for
it, by constructing an :class:`ImportResolver` with ``search_paths`` or by
calling :func:`sibling_path_resolver`. Importing this module changes nothing.
"""

from __future__ import annotations

import dataclasses
import enum
import importlib
import importlib.util
import os
import pkgutil
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Protocol

from .models import ReadCode

#: Attributes consulted, in order, for a package's version string.
VERSION_ATTRS: tuple[str, ...] = ("__version__", "PROJECT_VERSION")

#: Package-root callables consulted, in order, for a registry digest.
DIGEST_ATTRS: tuple[str, ...] = ("registry_digest", "registry_hash")

#: The naming convention used to discover line packages.
#:
#: Discovery is convention-based and therefore best-effort: it finds an
#: installed package whose name ends this way and cannot find one that does
#: not. A reading's ``undeclared_lines`` is a report of what this convention
#: turned up, never a proof that nothing else exists.
LINE_PACKAGE_SUFFIX: str = "_line"

#: Where this project's source tree lives, used to locate sibling checkouts.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

#: The environment variable that names where the sibling checkouts are.
SIBLING_BASE_ENV: str = "LINE_SET_SIBLINGS"


def sibling_base() -> Path:
    """The directory the sibling checkouts are looked for in.

    The default is this project's parent directory, because that is where they
    sit in the tree this project is developed in. That default is *positional*,
    and this project is its own repository: a clone of it will usually have
    something else entirely in its parent directory, or nothing at all. Finding
    nothing there is an ordinary outcome and is reported as ``NOT_INSTALLED``,
    never guessed at and never raised.

    A copy whose set lives somewhere else says so with ``LINE_SET_SIBLINGS``
    rather than being moved into a particular layout. The variable is read at
    call time, so setting it in a shell changes what the next command reads
    without touching a file. An empty value means "unset" — an empty string
    would otherwise resolve to the working directory and read whatever happens
    to be beside it.
    """
    declared = os.environ.get(SIBLING_BASE_ENV, "").strip()
    return PROJECT_ROOT.parent if not declared else Path(declared).expanduser()


@dataclass(frozen=True)
class Resolution:
    """The outcome of asking the import system for one package."""

    package_name: str
    code: ReadCode
    module: ModuleType | None
    detail: str


@dataclass(frozen=True)
class Vocabulary:
    """What was legible in a resolved package.

    Every field is independently optional. A package can expose enums and no
    registry, or a registry and no digest function; each missing piece stays
    ``None`` and is explained in ``detail``.
    """

    version: str | None
    registry_size: int | None
    registry_digest: str | None
    tokens: tuple[str, ...]
    detail: str


class PackageResolver(Protocol):
    """A callable that resolves one package by name into a :class:`Resolution`.

    Both :class:`ImportResolver` and the plain callables the tests inject
    satisfy it. A resolver is not required to enumerate candidate packages;
    that capability is probed separately via :func:`candidate_packages`, so a
    caller that only resolves is still a resolver.
    """

    def __call__(self, package_name: str) -> Resolution: ...


def exported_enums(module: ModuleType) -> tuple[type[enum.Enum], ...]:
    """The enum classes a package publishes at its root, in definition order.

    Only the package root is read. A class defined in a submodule but not
    re-exported is invisible here, which is intentional: the set's non-overlap
    contract is about the vocabulary a line publishes, not about every name
    that exists somewhere inside it.

    Classes belonging to the standard library's ``enum`` module are excluded.
    A package that writes ``from enum import Enum`` at its root has re-exported
    the machinery, not declared a vocabulary, and counting ``Enum`` as one of
    its classes would inflate the census of a package that did nothing but
    import normally. They carry no members, so this changes no token count —
    which is exactly why it had to be fixed here rather than noticed later in
    a number that looked plausible.

    This is the one place the exported set is decided, so
    :func:`enum_tokens` and :func:`vocabulary_census` cannot come to describe
    different classes.
    """
    return tuple(
        value
        for value in vars(module).values()
        if isinstance(value, type)
        and issubclass(value, enum.Enum)
        and value.__module__ != enum.__name__
    )


def enum_tokens(module: ModuleType) -> tuple[str, ...]:
    """Collect the member names of every enum exported at the package root.

    The result is sorted and de-duplicated so that neither ``dict`` nor
    ``set`` iteration order can reach a reading.
    """
    names: set[str] = set()
    for exported in exported_enums(module):
        names.update(member.name for member in exported)
    return tuple(sorted(names))


@dataclass(frozen=True)
class VocabularyCensus:
    """How a package arrived at the vocabulary :func:`enum_tokens` returns.

    ``enum_tokens`` deduplicates, because a line that spells one word in two of
    its own enums has still said one word and a within-line repeat is not a
    cross-line event. That is the right input to the collision scan and the
    wrong thing to quote as "how many names this package declares", so the two
    counts are kept apart here rather than conflated in prose.

    ``declared_members`` counts every member of every exported enum, repeats
    included. ``distinct_names`` is what survives deduplication and is exactly
    ``len(enum_tokens(module))``.
    """

    enum_classes: int
    declared_members: int
    distinct_names: int

    @property
    def within_line_repeats(self) -> int:
        """Members whose name another enum in the same package already used."""
        return self.declared_members - self.distinct_names


def vocabulary_census(module: ModuleType) -> VocabularyCensus:
    """Count the enums a package exports and the members they declare.

    Read from the package root only, on exactly the terms
    :func:`enum_tokens` reads it, so the two cannot describe different sets of
    classes.
    """
    exported = exported_enums(module)
    declared = [member.name for item in exported for member in item]
    return VocabularyCensus(
        enum_classes=len(exported),
        declared_members=len(declared),
        distinct_names=len(set(declared)),
    )


def _version_of(module: ModuleType) -> str | None:
    """Return the first non-blank version string the package publishes."""
    for attr in VERSION_ATTRS:
        value = getattr(module, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _registry_tuple(module: ModuleType) -> tuple[object, ...] | None:
    """Find the package's primary registry tuple, or ``None``.

    A candidate is a public, non-empty tuple declared in the package's
    ``registry`` submodule whose members are all instances of one dataclass
    type. When one candidate exists it is the registry. When several exist the
    strictly largest wins, and a tie yields ``None`` rather than a guess.

    This is a convention read, not a contract. A package that keeps its
    registry somewhere else, or under a private name, simply reports no size.
    """
    submodule = getattr(module, "registry", None)
    if not isinstance(submodule, ModuleType):
        return None
    candidates: list[tuple[object, ...]] = []
    for name, value in vars(submodule).items():
        if name.startswith("_") or not isinstance(value, tuple) or not value:
            continue
        member_types = {type(item) for item in value}
        if len(member_types) != 1:
            continue
        (member_type,) = member_types
        if not dataclasses.is_dataclass(member_type):
            continue
        candidates.append(value)
    if not candidates:
        return None
    largest = max(len(candidate) for candidate in candidates)
    winners = [candidate for candidate in candidates if len(candidate) == largest]
    if len(winners) != 1:
        return None
    return winners[0]


def _registry_digest(
    module: ModuleType, registry: tuple[object, ...] | None
) -> tuple[str | None, str]:
    """Ask the package for its own registry digest.

    The digest is the package's, computed by the package's own function over
    the package's own registry. This module never computes a digest for a
    sibling: a value the wrapper derived would say nothing about whether the
    sibling agrees with it.
    """
    if registry is None:
        return None, "no registry tuple was found, so no digest was requested"
    for attr in DIGEST_ATTRS:
        function = getattr(module, attr, None)
        if not callable(function):
            continue
        try:
            value = function(registry)
        except Exception as exc:  # noqa: BLE001 - a sibling must not crash us
            return None, f"{attr}() raised {type(exc).__name__}: {exc}"
        if isinstance(value, str) and value.strip():
            return value, f"digest read from {attr}()"
        return None, f"{attr}() returned no digest string"
    return None, "the package exposes no registry digest function"


def read_vocabulary(module: ModuleType) -> Vocabulary:
    """Read everything this module is willing to read from one package."""
    tokens = enum_tokens(module)
    registry = _registry_tuple(module)
    digest, digest_detail = _registry_digest(module, registry)
    details = [digest_detail]
    if not tokens:
        details.append("the package root exports no enum")
    if registry is None:
        details.append("the package exposes no unambiguous registry tuple")
    return Vocabulary(
        version=_version_of(module),
        registry_size=None if registry is None else len(registry),
        registry_digest=digest,
        tokens=tokens,
        detail="; ".join(details),
    )


class ImportResolver:
    """Resolve line packages through the normal import system.

    With no arguments this resolver adds nothing to ``sys.path`` and finds
    exactly what an ordinary ``import`` would find. Passing ``search_paths``
    is the caller explicitly asking for those directories to be prepended to
    ``sys.path`` on first use; the paths actually inserted are recorded in
    :attr:`added_paths` so the caller can see and undo what it asked for.
    """

    def __init__(self, search_paths: Sequence[str | Path] = ()) -> None:
        self.search_paths: tuple[str, ...] = tuple(str(path) for path in search_paths)
        self.added_paths: tuple[str, ...] = ()
        self._paths_ready = not self.search_paths

    def _ensure_paths(self) -> None:
        """Prepend the requested search paths to ``sys.path``, once."""
        if self._paths_ready:
            return
        added: list[str] = []
        for path in reversed(self.search_paths):
            if path not in sys.path:
                sys.path.insert(0, path)
                added.append(path)
        self.added_paths = tuple(sorted(added))
        self._paths_ready = True

    def __call__(self, package_name: str) -> Resolution:
        """Resolve one package by name, never raising."""
        self._ensure_paths()
        if not isinstance(package_name, str) or not package_name.strip():
            return Resolution(
                package_name=str(package_name),
                code=ReadCode.NOT_INSTALLED,
                module=None,
                detail="a package name must be non-blank text",
            )
        try:
            spec = importlib.util.find_spec(package_name)
        except (ImportError, ValueError, TypeError) as exc:
            return Resolution(
                package_name=package_name,
                code=ReadCode.IMPORT_FAILED,
                module=None,
                detail=f"find_spec raised {type(exc).__name__}: {exc}",
            )
        if spec is None:
            return Resolution(
                package_name=package_name,
                code=ReadCode.NOT_INSTALLED,
                module=None,
                detail="the import system found no such package",
            )
        try:
            module = importlib.import_module(package_name)
        except Exception as exc:  # noqa: BLE001 - a sibling must not crash us
            return Resolution(
                package_name=package_name,
                code=ReadCode.IMPORT_FAILED,
                module=None,
                detail=f"import raised {type(exc).__name__}: {exc}",
            )
        return Resolution(
            package_name=package_name,
            code=ReadCode.RESOLVED,
            module=module,
            detail="resolved through the import system",
        )

    def candidates(self) -> tuple[str, ...]:
        """Names of importable top-level packages that look like lines.

        Convention-based and best-effort, as documented on
        :data:`LINE_PACKAGE_SUFFIX`. Already-imported packages are included so
        that a package registered in-process is not missed.
        """
        self._ensure_paths()
        names = {
            info.name
            for info in pkgutil.iter_modules()
            if info.ispkg and info.name.endswith(LINE_PACKAGE_SUFFIX)
        }
        names.update(
            name
            for name in sys.modules
            if "." not in name and name.endswith(LINE_PACKAGE_SUFFIX)
        )
        return tuple(sorted(names))


#: The resolver used when a caller passes none. It touches ``sys.path`` never.
default_resolver: ImportResolver = ImportResolver()


def candidate_packages(resolver: object) -> tuple[str, ...] | None:
    """Ask a resolver to enumerate line packages, if it can.

    Returns ``None`` when the resolver offers no enumeration. That is a
    reported inability, not an empty answer: a reader that got ``None`` must
    say it did not scan rather than say it found nothing.
    """
    lister = getattr(resolver, "candidates", None)
    if not callable(lister):
        return None
    try:
        found = lister()
    except Exception:  # noqa: BLE001 - an unwilling resolver is not a crash
        return None
    if isinstance(found, (str, bytes)) or found is None:
        return None
    try:
        names = tuple(str(name) for name in found)
    except TypeError:
        return None
    return tuple(sorted(set(names)))


def sibling_source_roots(
    package_names: Iterable[str], base: Path | None = None
) -> tuple[str, ...]:
    """Locate ``<base>/<package>/src`` for each name, keeping those that exist.

    ``base`` defaults to :func:`sibling_base`, which is this project's parent
    directory unless ``LINE_SET_SIBLINGS`` names another. A name with no
    checkout is simply absent from the result; the caller then reads it as not
    installed.
    """
    root = sibling_base() if base is None else Path(base)
    found = [
        str(root / name / "src")
        for name in package_names
        if (root / name / "src").is_dir()
    ]
    return tuple(sorted(set(found)))


def sibling_path_resolver(
    package_names: Iterable[str] | None = None, base: Path | None = None
) -> ImportResolver:
    """Build a resolver that looks in the sibling checkouts' source trees.

    This is the explicit opt-in: calling it is a caller saying "also look
    over there". The returned resolver prepends those directories to
    ``sys.path`` the first time it is used, and records what it added.
    """
    if package_names is None:
        from .registry import LINE_SET

        package_names = [entry.package_name for entry in LINE_SET]
    return ImportResolver(sibling_source_roots(package_names, base))
