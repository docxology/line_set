# Script contract

Every file in `scripts/` is a thin CLI over `src/`. Business logic belongs in
`src/line_set/`, not here.

## Files

- `__init__.py` — package marker
- `build_figures.py` — calls `line_set.figures.build_figures()` and prints the output paths
- `build_omnibus.py` — assembles the declared works into one compiled volume under `output/manuscript/`
- `check_registry.py` — runs structural checks over `LINE_SET` and `SHARED_TOKENS`
- `check_set.py` — runs the reader over the installed siblings and reports status
- `record_reading.py` — records a dated reading of the installed sibling packages

## Canonical commands

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90 --cov-report=term-missing
uv run ruff check src tests scripts && uv run ruff format --check src tests scripts
uv run python scripts/check_registry.py
uv run python scripts/build_figures.py
uv run python scripts/build_omnibus.py --write
```
