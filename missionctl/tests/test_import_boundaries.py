"""Belt-and-suspenders for the core architectural invariant.

import-linter enforces this statically in `make contracts`; this test enforces it
at runtime by importing the whole core subtree and asserting no Qt module got
pulled in. Two independent guards make the invariant hard to break silently.
"""

import importlib
import pkgutil
import sys


def test_core_does_not_import_qt() -> None:
    import missionctl.core as core

    for mod in pkgutil.walk_packages(core.__path__, prefix="missionctl.core."):
        importlib.import_module(mod.name)

    assert "PySide6" not in sys.modules, "core must not import PySide6"
    assert "qasync" not in sys.modules, "core must not import qasync"
    assert "missionctl.qt" not in sys.modules, "core must not import the Qt layer"
