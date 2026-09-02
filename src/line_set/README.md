# Line Set package

`src/line_set/` holds the executable part of this project: the declaration of
the set, the staged reader that reads whichever line packages are installed,
the structural checks over the declaration, and the canonical serialization
used for digests.

Start with `registry.py` — it is the whole declaration, and appending another
colour to the set is an edit to that one file. Then `reader.py` for how a
reading is derived in five stages, and `invariants.py` for what is checked
about the declaration itself.

`binding.py` is the only module that imports a sibling line package. It
resolves through the ordinary import system by default and puts sibling source
directories on `sys.path` only when a caller asks. A line that is not
installed is an ordinary outcome, not an error.

The reading is narrow on purpose. `SET_LEGIBLE` says the declared
vocabularies of the lines that could be read do not overlap. It says nothing
about whether those lines are correct, complete, or worth having.

Run `uv run pytest tests/ --cov=src --cov-branch --cov-report=term-missing`
for the full package check.

See [AGENTS.md](AGENTS.md) for the working contract.
