"""Tests for Safe Delete (issue #17).

These tests verify the structure and pure-Python helpers of safe_delete.py
without booting Nuke. The Nuke-touching paths (`safe_delete()`,
`_collect_external_dependents`) are covered indirectly by AST checks plus a
dependency-summary test that exercises `_build_warning_html`.
"""

import ast
import importlib.util
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

    If the import itself raises (e.g. SyntaxError in safe_delete.py), the
    sys.modules edits are reverted before the exception propagates so a single
    broken import cannot cascade into unrelated tests.
    """
    saved_modules = {
        name: sys.modules.get(name)
        for name in ("nuke", "nukescripts", "safe_delete", "node_layout_prefs")
    }

    def restore():
        for name, value in saved_modules.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value

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

    try:
        spec = importlib.util.spec_from_file_location("safe_delete", SAFE_DELETE_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules["safe_delete"] = module
        spec.loader.exec_module(module)
    except BaseException:
        restore()
        raise

    stubs = {
        "nuke": nuke_stub,
        "nukescripts": nukescripts_stub,
        "node_layout_prefs": prefs_stub,
    }
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


class TestSafeDeleteLoaderRestoresOnImportFailure(unittest.TestCase):
    """If safe_delete fails to import, _load_safe_delete_with_stub_nuke must
    revert sys.modules so adjacent tests do not see leaked stubs."""

    def test_import_failure_restores_sys_modules(self):
        import tempfile

        sentinel_nuke = types.ModuleType("nuke")
        sentinel_nukescripts = types.ModuleType("nukescripts")
        sentinel_prefs = types.ModuleType("node_layout_prefs")

        saved = {
            "nuke": sys.modules.get("nuke"),
            "nukescripts": sys.modules.get("nukescripts"),
            "node_layout_prefs": sys.modules.get("node_layout_prefs"),
            "safe_delete": sys.modules.get("safe_delete"),
        }
        sys.modules["nuke"] = sentinel_nuke
        sys.modules["nukescripts"] = sentinel_nukescripts
        sys.modules["node_layout_prefs"] = sentinel_prefs
        sys.modules.pop("safe_delete", None)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix="bad_safe_delete_"
        ) as bad_file:
            bad_file.write("def broken(:\n")  # SyntaxError on exec_module
            bad_path = bad_file.name

        original_path = SAFE_DELETE_PATH
        module_globals = sys.modules[__name__].__dict__
        try:
            module_globals["SAFE_DELETE_PATH"] = bad_path
            with self.assertRaises(SyntaxError):
                _load_safe_delete_with_stub_nuke()
            # The stubs the loader installed must have been rolled back to our
            # sentinels. The leaked stubs would replace them otherwise.
            self.assertIs(sys.modules.get("nuke"), sentinel_nuke)
            self.assertIs(sys.modules.get("nukescripts"), sentinel_nukescripts)
            self.assertIs(sys.modules.get("node_layout_prefs"), sentinel_prefs)
        finally:
            module_globals["SAFE_DELETE_PATH"] = original_path
            os.unlink(bad_path)
            for name, value in saved.items():
                if value is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = value


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
        rendered_html = self.module._build_warning_html(external_dependents)
        self.assertIn("Blur1", rendered_html)
        self.assertIn("Read1", rendered_html)
        self.assertIn("Grade2", rendered_html)
        self.assertIn("Merge1", rendered_html)
        self.assertIn("Merge2", rendered_html)
        # Three dependents -> three table rows for arrows.
        self.assertEqual(rendered_html.count("&#x2192;"), 3)

    def test_warning_html_sorts_nodes_naturally(self):
        external_dependents = {f"Read{n}": {"Expression": ["X"]} for n in (10, 1, 2)}
        rendered_html = self.module._build_warning_html(external_dependents)
        positions = [rendered_html.index(f"<b>Read{n}</b>") for n in (1, 2, 10)]
        self.assertEqual(positions, sorted(positions))

    def test_warning_html_escapes_html_special_chars(self):
        """Node names with HTML special chars must be escaped, not break markup."""
        external_dependents = {
            "Read<script>": {"Expression": ["Merge&Co"]},
        }
        rendered_html = self.module._build_warning_html(external_dependents)
        # Raw payloads must NOT appear; their escaped forms must.
        self.assertNotIn("<script>", rendered_html)
        self.assertNotIn("Merge&Co", rendered_html)
        self.assertIn("Read&lt;script&gt;", rendered_html)
        self.assertIn("Merge&amp;Co", rendered_html)


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

        def stock_node_delete(popupOnError=False):  # noqa: N803
            self.calls.append(("stock", popupOnError))

        self.nukescripts_stub.node_delete = stock_node_delete

        def fake_safe_delete():
            self.calls.append(("safe",))

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
        self.module.node_delete(popupOnError=True)
        self.assertEqual(self.calls, [("safe",)])

    def test_disabled_pref_forwards_only_popup_on_error(self):
        """nukescripts.nodes.node_delete only takes popupOnError; that is the
        sole kwarg the disabled branch must forward."""
        self.prefs_stub.prefs_singleton.set("safe_delete_enabled", False)
        self.module.node_delete(popupOnError=True)
        self.assertEqual(self.calls, [("stock", True)])


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
