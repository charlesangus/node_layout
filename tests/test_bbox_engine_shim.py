import importlib
import os
import sys

import pytest


def _reload_engine_shim():
    sys.modules.pop("node_layout_engine", None)
    return importlib.import_module("node_layout_engine")


def test_list_registered_engines_exposes_bbox_on_fresh_import():
    engine_shim = _reload_engine_shim()

    assert engine_shim.list_registered_engines() == ["bbox"]


def test_unknown_engine_env_does_not_silently_dispatch_to_bbox():
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        os.environ["NODE_LAYOUT_ENGINE"] = "legacy"
        engine_shim = _reload_engine_shim()

        with pytest.raises(ValueError, match="Unknown layout engine 'legacy'"):
            engine_shim.get_engine()
    finally:
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine
        sys.modules.pop("node_layout_engine", None)
