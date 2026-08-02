"""The one seam that touches another package, exercised against real packages.

Every package in this module is written to disk and imported by the real
import system. That is deliberate: the binding layer's whole job is to survive
whatever an installed package happens to look like, and a package described
rather than written would only prove that the description was consistent.

The recurring theme is that absence is an outcome. A missing version, an
unfindable registry, a digest function that raises — each yields ``None`` and a
sentence saying why, and none of them raises out of the layer or invents a
value.
"""

from __future__ import annotations

import sys
from pathlib import Path

from line_set import (
    DIGEST_ATTRS,
    LINE_PACKAGE_SUFFIX,
    LINE_SET,
    SIBLING_BASE_ENV,
    VERSION_ATTRS,
    ImportResolver,
    ReadCode,
    candidate_packages,
    default_resolver,
    enum_tokens,
    exported_enums,
    read_vocabulary,
    sibling_base,
    sibling_path_resolver,
    sibling_source_roots,
    vocabulary_census,
)
from tests.support import (
    environment,
    import_sandbox,
    load_line_package,
    write_line_package,
)


def test_version_attrs_are_tried_in_the_declared_order(tmp_path: Path) -> None:
    assert VERSION_ATTRS[0] == "__version__"
    with import_sandbox():
        write_line_package(
            tmp_path,
            "first_attr_pkg",
            ("ALPHA",),
            version="1.0.0",
            extra_source=f'{VERSION_ATTRS[1]} = "9.9.9"',
        )
        module = load_line_package(tmp_path, "first_attr_pkg")
        assert read_vocabulary(module).version == "1.0.0"


def test_a_blank_first_version_falls_through_to_the_second_attribute(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            "second_attr_pkg",
            ("ALPHA",),
            version="   ",
            extra_source=f'{VERSION_ATTRS[1]} = "2.5.0"',
        )
        module = load_line_package(tmp_path, "second_attr_pkg")
        assert read_vocabulary(module).version == "2.5.0"


def test_a_non_string_version_is_read_as_no_version(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            "numeric_version_pkg",
            ("ALPHA",),
            version=None,
            extra_source=f"{VERSION_ATTRS[0]} = 3",
        )
        module = load_line_package(tmp_path, "numeric_version_pkg")
        assert read_vocabulary(module).version is None


def test_enum_tokens_are_sorted_deduplicated_and_root_only(tmp_path: Path) -> None:
    """Two enums sharing a member name publish that name once."""
    with import_sandbox():
        write_line_package(
            tmp_path,
            "two_enum_pkg",
            enums={"First": ("ZULU", "SHARED"), "Second": ("ALPHA", "SHARED")},
        )
        module = load_line_package(tmp_path, "two_enum_pkg")
        assert enum_tokens(module) == ("ALPHA", "SHARED", "ZULU")


def test_a_package_with_no_enum_publishes_no_tokens(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "no_enum_pkg", enums={})
        module = load_line_package(tmp_path, "no_enum_pkg")
        assert enum_tokens(module) == ()
        vocabulary = read_vocabulary(module)
        assert vocabulary.tokens == ()
        assert "exports no enum" in vocabulary.detail


def test_an_empty_enum_publishes_no_tokens(tmp_path: Path) -> None:
    """An enum class with no members is a class, not a vocabulary."""
    with import_sandbox():
        write_line_package(tmp_path, "empty_enum_pkg", ())
        module = load_line_package(tmp_path, "empty_enum_pkg")
        assert enum_tokens(module) == ()


def test_a_lone_registry_tuple_gives_its_size_and_the_package_digest(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path, "sized_pkg", ("ALPHA",), registry_sizes={"ENTRIES": 3}
        )
        module = load_line_package(tmp_path, "sized_pkg")
        vocabulary = read_vocabulary(module)
        assert vocabulary.registry_size == 3
        assert vocabulary.registry_digest == module.registry_digest(
            module.registry.ENTRIES
        )
        assert f"digest read from {DIGEST_ATTRS[0]}()" in vocabulary.detail


def test_the_strictly_largest_registry_tuple_wins(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            "largest_pkg",
            ("ALPHA",),
            registry_sizes={"SMALL": 2, "LARGE": 5},
        )
        module = load_line_package(tmp_path, "largest_pkg")
        assert read_vocabulary(module).registry_size == 5


def test_a_tie_between_registry_tuples_reports_no_size_rather_than_a_guess(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path, "tied_pkg", ("ALPHA",), registry_sizes={"ONE": 2, "TWO": 2}
        )
        module = load_line_package(tmp_path, "tied_pkg")
        vocabulary = read_vocabulary(module)
        assert vocabulary.registry_size is None
        assert "no unambiguous registry tuple" in vocabulary.detail


def test_private_empty_and_mixed_tuples_are_not_registries(tmp_path: Path) -> None:
    """Each skipped shape is a real thing a package might legitimately hold."""
    source = "\n".join(
        [
            "from dataclasses import dataclass",
            "",
            "",
            "@dataclass(frozen=True)",
            "class Item:",
            "    name: str",
            "",
            "",
            "@dataclass(frozen=True)",
            "class Other:",
            "    name: str",
            "",
            "",
            '_HIDDEN = (Item("a"), Item("b"), Item("c"), Item("d"))',
            "EMPTY = ()",
            'NOT_A_TUPLE = [Item("a"), Item("b"), Item("c")]',
            'MIXED = (Item("a"), Other("b"), Item("c"))',
            'PLAIN = ("a", "b", "c")',
        ]
    )
    with import_sandbox():
        write_line_package(tmp_path, "shapes_pkg", ("ALPHA",), registry_source=source)
        module = load_line_package(tmp_path, "shapes_pkg")
        vocabulary = read_vocabulary(module)
        assert vocabulary.registry_size is None
        assert "no unambiguous registry tuple" in vocabulary.detail


def test_a_package_without_a_registry_submodule_is_never_asked_for_a_digest(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "registryless_pkg", ("ALPHA",))
        module = load_line_package(tmp_path, "registryless_pkg")
        vocabulary = read_vocabulary(module)
        assert vocabulary.registry_size is None
        assert vocabulary.registry_digest is None
        assert "no digest was requested" in vocabulary.detail


def test_a_digest_function_that_raises_is_reported_not_propagated(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            "raising_digest_pkg",
            ("ALPHA",),
            registry_sizes={"ENTRIES": 2},
            digest_body='raise RuntimeError("this package cannot digest itself")',
        )
        module = load_line_package(tmp_path, "raising_digest_pkg")
        vocabulary = read_vocabulary(module)
        assert vocabulary.registry_digest is None
        assert "raised RuntimeError" in vocabulary.detail
        assert vocabulary.registry_size == 2


def test_a_digest_function_returning_something_else_yields_no_digest(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            "numeric_digest_pkg",
            ("ALPHA",),
            registry_sizes={"ENTRIES": 2},
            digest_body="return 7",
        )
        module = load_line_package(tmp_path, "numeric_digest_pkg")
        vocabulary = read_vocabulary(module)
        assert vocabulary.registry_digest is None
        assert "returned no digest string" in vocabulary.detail


def test_a_digest_function_returning_blank_text_yields_no_digest(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            "blank_digest_pkg",
            ("ALPHA",),
            registry_sizes={"ENTRIES": 2},
            digest_body='return "   "',
        )
        module = load_line_package(tmp_path, "blank_digest_pkg")
        assert read_vocabulary(module).registry_digest is None


def test_a_non_callable_digest_attribute_falls_through_to_the_second_name(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            "fallback_digest_pkg",
            ("ALPHA",),
            registry_sizes={"ENTRIES": 2},
            digest_attr=DIGEST_ATTRS[1],
            extra_source=f"{DIGEST_ATTRS[0]} = 5",
        )
        module = load_line_package(tmp_path, "fallback_digest_pkg")
        vocabulary = read_vocabulary(module)
        assert vocabulary.registry_digest is not None
        assert f"digest read from {DIGEST_ATTRS[1]}()" in vocabulary.detail


def test_a_package_with_no_digest_function_says_so(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            "digestless_pkg",
            ("ALPHA",),
            registry_sizes={"ENTRIES": 2},
            digest_attr=None,
        )
        module = load_line_package(tmp_path, "digestless_pkg")
        vocabulary = read_vocabulary(module)
        assert vocabulary.registry_digest is None
        assert "exposes no registry digest function" in vocabulary.detail


def test_the_default_resolver_adds_nothing_to_the_import_path() -> None:
    """Importing this package must not change where anything is imported from."""
    before = list(sys.path)
    assert default_resolver("no_such_package_anywhere").code is ReadCode.NOT_INSTALLED
    assert sys.path == before
    assert default_resolver.added_paths == ()
    assert default_resolver.search_paths == ()


def test_a_blank_package_name_is_not_installed() -> None:
    resolver = ImportResolver()
    for name in ("", "   "):
        resolution = resolver(name)
        assert resolution.code is ReadCode.NOT_INSTALLED
        assert "non-blank text" in resolution.detail


def test_a_non_string_package_name_is_not_installed() -> None:
    resolution = ImportResolver()(7)
    assert resolution.code is ReadCode.NOT_INSTALLED
    assert resolution.package_name == "7"


def test_a_name_whose_parent_is_missing_is_an_import_failure() -> None:
    """``find_spec`` raises for a submodule of a package that is not there."""
    resolution = ImportResolver()("no_such_parent_pkg.child")
    assert resolution.code is ReadCode.IMPORT_FAILED
    assert "find_spec raised" in resolution.detail


def test_a_package_that_raises_on_import_is_reported_not_propagated(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(
            tmp_path,
            "detonating_pkg",
            ("ALPHA",),
            raise_on_import="this line does not import",
        )
        resolution = ImportResolver([str(tmp_path)])("detonating_pkg")
        assert resolution.code is ReadCode.IMPORT_FAILED
        assert resolution.module is None
        assert "this line does not import" in resolution.detail


def test_search_paths_are_prepended_once_and_recorded(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "recorded_pkg", ("ALPHA",))
        resolver = ImportResolver([str(tmp_path)])
        assert resolver.added_paths == ()
        assert resolver("recorded_pkg").code is ReadCode.RESOLVED
        assert resolver.added_paths == (str(tmp_path),)
        assert sys.path.count(str(tmp_path)) == 1
        assert resolver("recorded_pkg").code is ReadCode.RESOLVED
        assert sys.path.count(str(tmp_path)) == 1


def test_a_search_path_already_present_is_not_added_again(tmp_path: Path) -> None:
    with import_sandbox():
        write_line_package(tmp_path, "already_there_pkg", ("ALPHA",))
        seeding = ImportResolver([str(tmp_path)])
        assert seeding("already_there_pkg").code is ReadCode.RESOLVED
        second = ImportResolver([str(tmp_path)])
        assert second("already_there_pkg").code is ReadCode.RESOLVED
        assert second.added_paths == ()


def test_candidates_finds_packages_by_the_declared_naming_convention(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(tmp_path, f"violet{LINE_PACKAGE_SUFFIX}", ("ALPHA",))
        write_line_package(tmp_path, "violet_instrument", ("ALPHA",))
        resolver = ImportResolver([str(tmp_path)])
        found = resolver.candidates()
        assert f"violet{LINE_PACKAGE_SUFFIX}" in found
        assert "violet_instrument" not in found, (
            "discovery is by the naming convention alone, and says so"
        )
        assert list(found) == sorted(set(found))


def test_candidates_includes_a_package_already_imported_in_process(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        write_line_package(tmp_path, f"indigo{LINE_PACKAGE_SUFFIX}", ("ALPHA",))
        loader = ImportResolver([str(tmp_path)])
        assert loader(f"indigo{LINE_PACKAGE_SUFFIX}").code is ReadCode.RESOLVED
        assert f"indigo{LINE_PACKAGE_SUFFIX}" in ImportResolver().candidates()


def test_candidate_packages_reports_inability_rather_than_emptiness() -> None:
    """``None`` means "did not scan"; ``()`` would mean "scanned, found none"."""

    def resolver_without_enumeration(package_name: str) -> None:  # pragma: no cover
        raise AssertionError("this resolver is never called")

    assert candidate_packages(resolver_without_enumeration) is None


def test_candidate_packages_refuses_every_unusable_answer() -> None:
    class NotCallable:
        candidates = "not a method"

    class Raises:
        def candidates(self) -> tuple[str, ...]:
            raise RuntimeError("this resolver will not enumerate")

    class ReturnsText:
        def candidates(self) -> str:
            return "one_line"

    class ReturnsNothing:
        def candidates(self) -> None:
            return None

    class ReturnsNonIterable:
        def candidates(self) -> int:
            return 7

    for unusable in (
        NotCallable(),
        Raises(),
        ReturnsText(),
        ReturnsNothing(),
        ReturnsNonIterable(),
    ):
        assert candidate_packages(unusable) is None, type(unusable).__name__


def test_candidate_packages_sorts_and_deduplicates_a_usable_answer() -> None:
    class Lists:
        def candidates(self) -> list[str]:
            return ["zulu_line", "alpha_line", "zulu_line"]

    assert candidate_packages(Lists()) == ("alpha_line", "zulu_line")


def test_sibling_source_roots_keeps_only_directories_that_exist(
    tmp_path: Path,
) -> None:
    (tmp_path / "present_line" / "src").mkdir(parents=True)
    (tmp_path / "flat_line").mkdir()
    found = sibling_source_roots(
        ("present_line", "flat_line", "missing_line"), base=tmp_path
    )
    assert found == (str(tmp_path / "present_line" / "src"),)


def test_sibling_source_roots_defaults_to_the_neighbouring_checkouts() -> None:
    """With no base, the search is whatever :func:`sibling_base` resolved to."""
    found = sibling_source_roots(entry.package_name for entry in LINE_SET)
    for path in found:
        assert Path(path).is_dir()
        assert Path(path).parent.parent == sibling_base()


# ------------------------------------------------- where the siblings are


def test_the_sibling_base_defaults_to_this_project_s_parent_directory() -> None:
    """The default is positional, and it is the one the working tree uses."""
    with environment(SIBLING_BASE_ENV, None):
        assert sibling_base() == Path(__file__).resolve().parents[2]


def test_the_sibling_base_can_be_named_instead_of_assumed(tmp_path: Path) -> None:
    """A clone whose set is elsewhere says where, rather than being relocated.

    This project is its own repository. Its parent directory is whatever the
    person who cloned it happened to clone into, so a layout is a bad address
    and an environment variable is a good one.
    """
    with environment(SIBLING_BASE_ENV, str(tmp_path)):
        assert sibling_base() == tmp_path
        (tmp_path / "teal_line" / "src").mkdir(parents=True)
        assert sibling_source_roots(("teal_line",)) == (
            str(tmp_path / "teal_line" / "src"),
        )


def test_a_blank_sibling_base_is_read_as_unset_rather_than_as_here(
    tmp_path: Path,
) -> None:
    """``Path("")`` is the working directory, which would read a stranger's tree.

    Exported-but-empty is a common shell state, and resolving it to ``.`` would
    make the reader's answer depend on where the command was run from.
    """
    default = Path(__file__).resolve().parents[2]
    for blank in ("", "   "):
        with environment(SIBLING_BASE_ENV, blank):
            assert sibling_base() == default
    with environment(SIBLING_BASE_ENV, str(tmp_path)):
        assert sibling_base() != default


def test_an_explicit_base_still_wins_over_the_environment(tmp_path: Path) -> None:
    """The argument is the innermost address and the environment cannot override it."""
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / "teal_line" / "src").mkdir(parents=True)
    named = tmp_path / "named"
    (named / "teal_line" / "src").mkdir(parents=True)
    with environment(SIBLING_BASE_ENV, str(elsewhere)):
        assert sibling_source_roots(("teal_line",), base=named) == (
            str(named / "teal_line" / "src"),
        )


def test_sibling_path_resolver_defaults_to_the_declared_package_names(
    tmp_path: Path,
) -> None:
    with import_sandbox():
        default_named = sibling_path_resolver(base=tmp_path)
        assert default_named.search_paths == ()
        (tmp_path / LINE_SET[0].package_name / "src").mkdir(parents=True)
        named = sibling_path_resolver(base=tmp_path)
        assert named.search_paths == (str(tmp_path / LINE_SET[0].package_name / "src"),)
        explicit = sibling_path_resolver(["chartreuse_line"], base=tmp_path)
        assert explicit.search_paths == ()


# ------------------------------------------------------ the vocabulary census


def test_the_census_separates_declared_members_from_distinct_names(
    tmp_path: Path,
) -> None:
    """The count the collision scan uses is not the count a package declares.

    A line that spells one word in two of its own enums has still said one
    word, so ``enum_tokens`` deduplicates. Quoting the pre-dedup total as "how
    many names this line declares" would inflate it, so the census keeps both
    numbers and the difference between them.
    """
    with import_sandbox():
        write_line_package(
            tmp_path,
            "census_line",
            enums={
                "First": ("ALPHA", "SHARED"),
                "Second": ("SHARED", "BRAVO"),
                "Third": ("CHARLIE",),
            },
        )
        module = load_line_package(tmp_path, "census_line")
        counted = vocabulary_census(module)

    assert counted.enum_classes == 3
    assert counted.declared_members == 5
    assert counted.distinct_names == 4
    assert counted.within_line_repeats == 1
    assert counted.distinct_names == len(enum_tokens(module))


def test_the_census_counts_nothing_in_a_package_that_exports_no_enum(
    tmp_path: Path,
) -> None:
    """An empty census is a real answer, and it must not be a fabricated one."""
    with import_sandbox():
        write_line_package(tmp_path, "silent_line", ())
        module = load_line_package(tmp_path, "silent_line")
        counted = vocabulary_census(module)
    assert counted.enum_classes == 1, "the package does export one empty enum"
    assert counted.declared_members == 0
    assert counted.distinct_names == 0
    assert counted.within_line_repeats == 0


def test_the_census_reads_the_package_root_only(tmp_path: Path) -> None:
    """The same scope ``enum_tokens`` reads, so the two cannot disagree."""
    with import_sandbox():
        package = write_line_package(tmp_path, "deep_line", ("VISIBLE",))
        (package / "hidden.py").write_text(
            "from enum import Enum\n\n\nclass Hidden(Enum):\n    INVISIBLE = 'x'\n",
            encoding="utf-8",
        )
        module = load_line_package(tmp_path, "deep_line")
        counted = vocabulary_census(module)
    assert counted.distinct_names == len(enum_tokens(module)) == 1
    assert "INVISIBLE" not in enum_tokens(module)


def test_the_export_scan_refuses_to_count_the_enum_machinery(tmp_path: Path) -> None:
    """``from enum import Enum`` at a root is an import, not a vocabulary.

    Every generated package here writes that line, as real packages do. Before
    this was fixed the census counted ``Enum`` as one of the package's own
    classes — a number that stayed plausible while being wrong, which is the
    kind that survives review.
    """
    with import_sandbox():
        write_line_package(tmp_path, "importing_line", ("ALPHA",))
        module = load_line_package(tmp_path, "importing_line")
        exported = exported_enums(module)

    import enum as enum_module

    assert enum_module.Enum in vars(module).values(), (
        "the plant must actually re-export the base class"
    )
    assert enum_module.Enum not in exported
    assert [item.__name__ for item in exported] == ["Vocabulary"]
    assert all(item.__module__ != enum_module.__name__ for item in exported)
    assert vocabulary_census(module).enum_classes == len(exported)
