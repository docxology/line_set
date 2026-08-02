# Tests

This folder holds the executable checks for the Line Set package. The modules
are grouped by concern: the record types, the declaration, the structural
checks, the staged reader, the sibling-binding seam, the canonical
serialization, the figures, extensibility, self-disjointness, the manuscript
bindings, the compiled volume, the documentation links, and the lexical
guardrails.

```bash
uv run pytest tests/ --cov=src --cov-branch --cov-report=term-missing
```

The coverage floor is configured in `pyproject.toml`.

Two properties of this suite matter more than the coverage number.

**It uses no mocking framework.** `tests/support.py` supplies the real building
blocks instead: `import_sandbox()` restores `sys.path` and `sys.modules` around
a block, and the helpers there write real Python packages to real temporary
directories for the import system to find. When a test needs to control what the
reader sees, it passes a plain callable as `resolver` — an ordinary function is a
real object, not a stand-in for one.

**It must pass with the sibling line packages absent.** Run it once inside this
working tree and once from a directory where nothing importable is named for a
line, and where nothing beside it is one of the declared works. Both runs must
clear the floor with no failures; the sibling-free run reports a few more skips
and a slightly lower figure, because the skipped checks are the ones that read a
real sibling. A check that needs the set present skips and names what it could
not read — it never fails. A suite that only passes here cannot travel with a
separated copy, and a separated copy is the ordinary case: this project is its
own repository.

**Its links must resolve inside this repository.**
`test_documentation_links.py` resolves every inline markdown link in every
document and fails on one that climbs above the repository root. An out-of-tree
reference is addressed by URL or cited by name; a relative path that only works
in one working tree is a dead link everywhere else.

The folder contract, including the required module surface and the assertions
each module owns, is [AGENTS.md](AGENTS.md).
