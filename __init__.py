"""Hermes plugin entry point for home-3d-workshop.

Everything lives in the ``home3d`` package; imports are lazy so plugin load stays fast and the
package also works outside Hermes (the zero-token watcher script and the test-suite import it).
"""

from __future__ import annotations


def register(ctx) -> None:
    from .home3d.plugin import register_all

    register_all(ctx)
