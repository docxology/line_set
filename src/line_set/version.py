"""Version markers for the Line Set package and its declaration.

``__version__`` tracks the package. ``SET_VERSION`` marks the reviewed
revision of the set declaration in :mod:`line_set.registry`, so a digest can
be discussed against a named revision rather than against a floating tuple.

Neither marker says anything about the sibling line packages. Their versions
are read at runtime and reported per line; they are never mirrored here.
"""

__version__ = "0.1.0"

SET_VERSION = "2026.07.27"
