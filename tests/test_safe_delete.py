"""Tests for Safe Delete (issue #17).

These tests verify the structure and pure-Python helpers of safe_delete.py
without booting Nuke. The Nuke-touching paths (`safe_delete()`,
`_collect_external_dependents`) are covered indirectly by AST checks plus a
dependency-summary test that exercises `_build_warning_html`.
"""

import ast
import importlib.util
import inspect
import os
import sys
import types
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
SAFE_DELETE_PATH = os.path.join(REPO_ROOT, "safe_delete.py")
MENU_PATH = os.path.join(REPO_ROOT, "menu.py")


def _load_safe_delete_with_stub_nuke():
    """Import safe_delete with stub `nuke`, `nukescripts`, and `node_layout_prefs`
    modules so the pure-Python helpers can be exercised without a real Nuke install.

    Returns ``(module, stubs, restore)`` where ``stubs`` is a dict of the stub
    modules keyed by name and ``restore()`` undoes the sys.modules edits so
    other test modules see a clean slate.
    """
    saved_modules = {
        name: sys.modules.get(name)
        for name in ("nuke", "nukescripts", "safe_delete", "node_layout_prefs")
    }

    nuke_stub = types.ModuleType("nuke")
    nuke_stub.HIDDEN_INPUTS = 1
    nuke_stub.EXPRESSIONS = 2
    nuke_stub.dependentNodes = lambda *args, **kwargs: []
    nuke_stub.nodeDelete = lambda: None
    nuke_stub.selectedNodes = lambda: []
    nuke_stub.Text_Knob = lambda *args, **kwargs: None

    nukescripts_stub = types.ModuleType("nukescripts")
    nukescripts_stub.PythonPanel = lambda: None
    nukescripts_stub.node_delete = lambda *args, **kwargs: None

    class _StubPrefs:
        def __init__(self):
            self._values = {"safe_delete_enabled": True}

        def get(self, key):
            return self._values.get(key)

        def set(self, key, value):
            self._values[key] = value

    prefs_stub = types.ModuleType("node_layout_prefs")
    prefs_stub.prefs_singleton = _StubPrefs()

    sys.modules["nuke"] = nuke_stub
    sys.modules["nukescripts"] = nukescripts_stub
    sys.modules["node_layout_prefs"] = prefs_stub

    spec = importlib.util.spec_from_file_location("safe_delete", SAFE_DELETE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["safe_delete"] = module
    spec.loader.exec_module(module)

    stubs = {
        "nuke": nuke_stub,
        "nukescripts": nukescripts_stub,
        "node_layout_prefs": prefs_stub,
    }

    def restore():
        for name, value in saved_modules.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value

    return module, stubs, restore


class TestSafeDeleteStructure(unittest.TestCase):
    """AST checks that don't need Nuke at all."""

    def test_file_parses(self):
        with open(SAFE_DELETE_PATH) as source_file:
            ast.parse(source_file.read())

    def test_install_function_present(self):
        with open(SAFE_DELETE_PATH) as source_file:
            tree = ast.parse(source_file.read())
        function_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertIn("install", function_names)
        self.assertIn("safe_delete", function_names)
        self.assertIn("node_delete", function_names)

    def test_viewer_dependents_are_filtered(self):
        """The collector must skip Viewer dependents -- regression guard."""
        with open(SAFE_DELETE_PATH) as source_file:
            source = source_file.read()
        self.assertIn('"Viewer"', source)


class TestSafeDeleteHelpers(unittest.TestCase):
    """Pure-Python helpers exercised against stub nuke/nukescripts."""

    @classmethod
    def setUpClass(cls):
        cls.module, cls.stubs, cls._restore_modules = _load_safe_delete_with_stub_nuke()
        cls.nukescripts_stub = cls.stubs["nukescripts"]
        cls.prefs_stub = cls.stubs["node_layout_prefs"]

    @classmethod
    def tearDownClass(cls):
        cls._restore_modules()

    def setUp(self):
        # Reset the captured original between tests so install()'s
        # idempotency check can be exercised in isolation.
        self.module._original_node_delete = None
        self.prefs_stub.prefs_singleton.set("safe_delete_enabled", True)

    def test_install_replaces_nukescripts_node_delete(self):
        original = self.nukescripts_stub.node_delete
        self.module.install()
        try:
            self.assertIs(self.nukescripts_stub.node_delete, self.module.node_delete)
            self.assertIsNot(self.nukescripts_stub.node_delete, original)
        finally:
            self.nukescripts_stub.node_delete = original

    def test_natural_sort_orders_numerics_correctly(self):
        sorted_names = sorted(["Read10", "Read1", "Read2"], key=self.module._natural_sort_key)
        self.assertEqual(sorted_names, ["Read1", "Read2", "Read10"])

    def test_warning_html_lists_each_external_dependent(self):
        external_dependents = {
            "Blur1": {"Expression": ["Grade2"]},
            "Read1": {"Hidden Input": ["Merge1", "Merge2"]},
        }
        html = self.module._build_warning_html(external_dependents)
        self.assertIn("Blur1", html)
        self.assertIn("Read1", html)
        self.assertIn("Grade2", html)
        self.assertIn("Merge1", html)
        self.assertIn("Merge2", html)
        # Three dependents -> three table rows for arrows.
        self.assertEqual(html.count("&#x2192;"), 3)

    def test_warning_html_sorts_nodes_naturally(self):
        external_dependents = {f"Read{n}": {"Expression": ["X"]} for n in (10, 1, 2)}
        html = self.module._build_warning_html(external_dependents)
        positions = [html.index(f"<b>Read{n}</b>") for n in (1, 2, 10)]
        self.assertEqual(positions, sorted(positions))


class TestSafeDeletePreferenceGate(unittest.TestCase):
    """The safe_delete_enabled preference must route node_delete() to either
    Safe Delete or the captured original `nukescripts.node_delete`."""

    @classmethod
    def setUpClass(cls):
        cls.module, cls.stubs, cls._restore_modules = _load_safe_delete_with_stub_nuke()
        cls.nukescripts_stub = cls.stubs["nukescripts"]
        cls.prefs_stub = cls.stubs["node_layout_prefs"]

    @classmethod
    def tearDownClass(cls):
        cls._restore_modules()

    def setUp(self):
        self.calls = []

        def stock_node_delete(popupOnError=False, evaluateAll=False):  # noqa: N803
            self.calls.append(("stock", popupOnError, evaluateAll))

        self.nukescripts_stub.node_delete = stock_node_delete

        def fake_safe_delete(evaluate_all=False):
            self.calls.append(("safe", evaluate_all))

        # Reset module state and patch the safe_delete() heavy path with a probe.
        self.module._original_node_delete = None
        self._real_safe_delete = self.module.safe_delete
        self.module.safe_delete = fake_safe_delete
        self.prefs_stub.prefs_singleton.set("safe_delete_enabled", True)

        self.module.install()

    def tearDown(self):
        self.module.safe_delete = self._real_safe_delete
        self.module._original_node_delete = None

    def test_install_captures_original_node_delete(self):
        """install() must remember the pre-patch nukescripts.node_delete."""
        self.assertIsNotNone(self.module._original_node_delete)

    def test_install_is_idempotent(self):
        """A second install() must NOT capture the already-patched callable."""
        first_captured = self.module._original_node_delete
        self.module.install()
        self.assertIs(self.module._original_node_delete, first_captured)

    def test_enabled_pref_routes_to_safe_delete(self):
        self.prefs_stub.prefs_singleton.set("safe_delete_enabled", True)
        self.module.node_delete(popupOnError=True, evaluateAll=False)
        self.assertEqual(self.calls, [("safe", False)])

    def test_disabled_pref_routes_to_original_node_delete(self):
        self.prefs_stub.prefs_singleton.set("safe_delete_enabled", False)
        self.module.node_delete(popupOnError=True, evaluateAll=True)
        self.assertEqual(self.calls, [("stock", True, True)])

    def test_disabled_pref_tolerates_legacy_signature(self):
        """Older Nuke builds' nukescripts.node_delete accepts only popupOnError.
        We must NOT pass evaluateAll to such a callable (regression: TypeError)."""
        legacy_calls = []

        def legacy_stock_node_delete(popupOnError=False):  # noqa: N803
            legacy_calls.append(popupOnError)

        # Re-install with a legacy-signature stock as the captured original.
        self.module._original_node_delete = None
        self.nukescripts_stub.node_delete = legacy_stock_node_delete
        self.module.install()

        self.prefs_stub.prefs_singleton.set("safe_delete_enabled", False)
        # Should not raise even though we pass evaluateAll=True.
        self.module.node_delete(popupOnError=True, evaluateAll=True)
        self.assertEqual(legacy_calls, [True])

    def test_disabled_pref_tolerates_unintrospectable_callable(self):
        """If inspect.signature() fails (e.g. C builtin), call with no args."""
        unintrospectable_calls = []

        class UnintrospectableCallable:
            def __call__(self_inner, *args, **kwargs):
                unintrospectable_calls.append((args, kwargs))

        unintrospectable = UnintrospectableCallable()
        # Patch so signature() raises and exercises the fallback branch.
        self.module._original_node_delete = unintrospectable
        original_signature = inspect.signature

        def raising_signature(target):
            if target is unintrospectable:
                raise ValueError("no signature available")
            return original_signature(target)

        self.module.inspect.signature = raising_signature
        try:
            self.prefs_stub.prefs_singleton.set("safe_delete_enabled", False)
            self.module.node_delete(popupOnError=True, evaluateAll=True)
        finally:
            self.module.inspect.signature = original_signature

        self.assertEqual(unintrospectable_calls, [((), {})])


class TestMenuInstallsSafeDelete(unittest.TestCase):
    """menu.py must install Safe Delete on import (issue #17)."""

    def test_menu_imports_safe_delete(self):
        with open(MENU_PATH) as menu_file:
            source = menu_file.read()
        self.assertIn("import safe_delete", source)

    def test_menu_calls_install(self):
        with open(MENU_PATH) as menu_file:
            source = menu_file.read()
        self.assertIn("safe_delete.install()", source)


if __name__ == "__main__":
    unittest.main()
