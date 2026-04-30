"""Layout engine dispatcher for the bake-off between competing implementations.

Three engines coexist during the rewrite:

* ``"legacy"`` — the long-standing implementation living directly in
  ``node_layout.py``. This is the default; set nothing and behaviour is
  unchanged.
* ``"bbox"`` — Algorithm A (leaf-first bbox composition), implemented in
  ``node_layout_v2_bbox.py`` on the ``feat/layout-rewrite-bbox`` branch.
* ``"shape"`` — Algorithm C-on-B (Shape protocol + contour packing),
  implemented in ``node_layout_v2_shape.py`` on the
  ``feat/layout-rewrite-shape`` branch.

Engine selection (highest precedence first):

1. Environment variable ``NODE_LAYOUT_ENGINE``
2. Pref key ``engine`` from ``node_layout_prefs``
3. Default ``"legacy"``

The five layout entry points in ``node_layout.py`` (``layout_upstream``,
``layout_selected``, ``layout_selected_horizontal``,
``layout_selected_horizontal_place_only``, plus their compact/loose
wrappers via the first two) call ``maybe_dispatch`` at the top of their
body. When the active engine is non-legacy ``maybe_dispatch`` runs the
engine and returns ``True``; the caller should then ``return``
immediately. When the engine is legacy ``maybe_dispatch`` returns
``False`` and the legacy code path runs unchanged.

State-only operations (scaling, freeze, arrange, clear-state) are not
dispatched: they do not depend on the layout algorithm and are always
executed by the legacy implementation regardless of engine selection.
"""
from __future__ import annotations

import contextlib
import os
from abc import ABC, abstractmethod


class LayoutEngine(ABC):
    """Abstract layout engine. Subclasses implement the five layout entry
    points; everything else (scaling, freeze, arrange) reuses the legacy
    helpers in ``node_layout.py``.
    """

    name: str = "abstract"

    @abstractmethod
    def layout_upstream(self, scheme_multiplier=None):
        ...

    @abstractmethod
    def layout_selected(self, scheme_multiplier=None):
        ...

    @abstractmethod
    def layout_selected_horizontal(self, scheme_multiplier=None):
        ...

    @abstractmethod
    def layout_selected_horizontal_place_only(self, scheme_multiplier=None):
        ...


_ENGINES: dict[str, type[LayoutEngine]] = {}


def register(name: str):
    """Decorator: register an engine class under a string name."""
    def _wrap(cls):
        cls.name = name
        _ENGINES[name] = cls
        return cls
    return _wrap


def get_engine_name() -> str:
    """Return the active engine name. Reads env var, then prefs, then defaults."""
    env = os.environ.get("NODE_LAYOUT_ENGINE")
    if env:
        return env
    try:
        import node_layout_prefs
        prefs = getattr(node_layout_prefs, "current_prefs", None)
        if prefs is not None:
            value = prefs.get("engine")
            if value:
                return value
    except Exception:
        pass
    return "legacy"


def _try_autoload(name: str) -> None:
    """Auto-import the engine module that owns the given name.

    Each engine module registers itself via ``@register(name)`` at import.
    Importing here is a no-op if the module has already been imported, and
    silently skipped if the module does not exist on this branch.
    """
    if name in _ENGINES:
        return
    module_name = f"node_layout_v2_{name}"
    with contextlib.suppress(ImportError):
        __import__(module_name)


def get_engine() -> LayoutEngine | None:
    """Return an instance of the active engine, or None if it's legacy."""
    name = get_engine_name()
    if name == "legacy":
        return None
    _try_autoload(name)
    engine_cls = _ENGINES.get(name)
    if engine_cls is None:
        raise ValueError(
            f"Unknown layout engine {name!r}. "
            f"Registered engines: {sorted(_ENGINES)}; "
            f"set NODE_LAYOUT_ENGINE to one of those or 'legacy'."
        )
    return engine_cls()


def maybe_dispatch(method_name: str, *args, **kwargs) -> bool:
    """Called from each legacy entry point to optionally hand off to a new
    engine.

    Returns ``True`` if dispatch ran (caller should return immediately).
    Returns ``False`` if the legacy code path should run.

    Usage at the top of each layout entry point::

        def layout_upstream(scheme_multiplier=None):
            if node_layout_engine.maybe_dispatch(
                "layout_upstream", scheme_multiplier=scheme_multiplier,
            ):
                return
            # ... legacy body ...
    """
    engine = get_engine()
    if engine is None:
        return False
    method = getattr(engine, method_name, None)
    if method is None:
        raise AttributeError(
            f"Engine {engine.name!r} does not implement {method_name!r}"
        )
    method(*args, **kwargs)
    return True


def list_registered_engines() -> list[str]:
    """Return a sorted list of registered engine names (excludes 'legacy')."""
    return sorted(_ENGINES)
