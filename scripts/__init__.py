"""Line Set CLI wrappers.

This file keeps the local ``scripts`` directory a regular package, so an
explicit import of one of these thin wrappers resolves to this project rather
than to a same-named module in a sibling checkout on ``sys.path``.

Every script here is an orchestrator: it calls the package, prints what came
back, and chooses an exit code from a value the package computed. No decision
rule lives in this directory.
"""
