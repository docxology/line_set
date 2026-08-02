# Source

The `line_set` package — a wrapper and reader that declares the set, reads
whichever declared packages are installed, and checks that no two of them
share a status token.

```bash
uv run pytest tests/ --cov=src --cov-fail-under=90
```

See [AGENTS.md](AGENTS.md) for the working contract.
