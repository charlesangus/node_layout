"""Compatibility shim for the bbox layout implementation.

The engine bake-off is over in this worktree: all layout entry points use the
``node_layout_bbox`` implementation.  This module remains only because the
bbox engine class registers through it and a few test utilities inspect the
registered engine list.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod


class LayoutEngine(ABC):
    """Abstract layout engine. Subclasses implement the five layout entry
    points; everything else (scaling, freeze, arrange) reuses the shared
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
_SUPPORTED_ENGINE_NAMES = ("bbox",)


def register(name: str):
    """Decorator: register an engine class under a string name."""
    def _wrap(cls):
        cls.name = name
        _ENGINES[name] = cls
        return cls
    return _wrap


def get_engine_name() -> str:
    """Return the requested engine name, defaulting to the bbox engine."""
    return (
        os.environ.get("NODE_LAYOUT_ENGINE")
        or os.environ.get("NL_ENGINE")
        or "bbox"
    )


def _try_autoload(name: str) -> None:
    """Auto-import the engine module that owns the given name.

    Each engine module registers itself via ``@register(name)`` at import.
    Importing here is a no-op if the module has already been imported, and
    silently skipped if the module does not exist on this branch.
    """
    if name in _ENGINES:
        return
    __import__(f"node_layout_{name}")


def get_engine() -> LayoutEngine:
    """Return an instance of the bbox engine."""
    name = get_engine_name()
    try:
        _try_autoload(name)
    except ModuleNotFoundError as exc:
        if exc.name != f"node_layout_{name}":
            raise
    engine_cls = _ENGINES.get(name)
    if engine_cls is None:
        raise ValueError(
            f"Unknown layout engine {name!r}. "
            f"Registered engines: {sorted(_ENGINES)}; "
            f"expected the bbox engine to be registered."
        )
    return engine_cls()


def maybe_dispatch(method_name: str, *args, **kwargs) -> bool:
    """Dispatch to the bbox engine. Always returns ``True``."""
    engine = get_engine()
    method = getattr(engine, method_name, None)
    if method is None:
        raise AttributeError(
            f"Engine {engine.name!r} does not implement {method_name!r}"
        )
    method(*args, **kwargs)
    return True


def list_registered_engines() -> list[str]:
    """Return a sorted list of registered engine names."""
    return sorted(set(_SUPPORTED_ENGINE_NAMES) | set(_ENGINES))
