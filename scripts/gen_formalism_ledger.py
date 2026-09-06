#!/usr/bin/env python3
"""Regenerate ``data/formalism_claim_ledger.json``.

Thin orchestrator: parsing and derivation live in
``line_set.formalism_ledger``; this file only parses the command line.
"""

from __future__ import annotations

import argparse

from line_set.formalism_ledger import build_ledger


def main() -> None:
    """The generator takes no options. It still parses its command line, because
    a command that ignores an argument it was given cannot be told apart from
    one that honoured it, and the failure mode is an operator who believes a
    flag was honoured over a run that never understood it.
    """
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(build_ledger())


if __name__ == "__main__":
    main()
