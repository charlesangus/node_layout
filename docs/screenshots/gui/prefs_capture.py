"""Widget-capture scenario: Node Layout preferences dialog.

Run with nuke-screenshotter's widget mode (auto-detected from the .py
extension)::

    NUKE_PATH=$PWD nuke_dag_capture_auto \
        docs/screenshots/gui/prefs_capture.py --output-dir docs/images

The nuke-screenshotter runner exec's this file inside a live headless Nuke/Qt
session with ``capture(widget, name)`` and ``nuke`` already injected into
globals (do NOT import them). Each ``capture(widget, name)`` call renders one
widget to ``<name>.png`` in the output directory, so ``capture(prefs_dialog,
"preferences-dialog")`` produces ``preferences-dialog.png``.

Why widget mode (not playback ``.json``): the preferences dialog is the
``NodeLayoutPrefsDialog`` QDialog defined in ``node_layout_prefs_dialog.py``.
It only appears when a user explicitly opens it from the Node Layout menu, so
a playback target resolver has no reliable on-screen trigger to grab.
Constructing the dialog directly and handing it to ``capture()`` renders
exactly the documented dialog (all five preference sections populated from
the live ``node_layout_prefs.prefs_singleton`` defaults) deterministically.

No machine-local absolute paths: the Node Layout package directory is derived
from this file's own location (``__file__``, set by the runner) and, as a
fallback, from the ``NUKE_PATH`` / ``NODE_LAYOUT_REPO`` environment variables.
"""
import os
import pathlib
import sys


def _candidate_package_roots():
    """Yield directories that may contain the node_layout modules.

    Ordered by preference: this file's repository root (derived from __file__),
    then the NODE_LAYOUT_REPO override, then any entry on NUKE_PATH. All are
    environment-relative — no absolute path is baked into this file.
    """
    this_file = globals().get("__file__")
    if this_file:
        # docs/screenshots/gui/prefs_capture.py -> repository root is three up.
        repository_root = pathlib.Path(this_file).resolve().parent.parent.parent.parent
        yield str(repository_root)

    explicit_repo = os.environ.get("NODE_LAYOUT_REPO")
    if explicit_repo:
        yield explicit_repo

    for nuke_path_entry in os.environ.get("NUKE_PATH", "").split(os.pathsep):
        if nuke_path_entry:
            yield nuke_path_entry


def _ensure_node_layout_importable():
    """Add the first root that actually contains node_layout_prefs_dialog.py to sys.path."""
    for candidate_root in _candidate_package_roots():
        if os.path.isfile(os.path.join(candidate_root, "node_layout_prefs_dialog.py")):
            if candidate_root not in sys.path:
                sys.path.insert(0, candidate_root)
            return candidate_root
    return None


_ensure_node_layout_importable()

from node_layout_prefs_dialog import NodeLayoutPrefsDialog  # noqa: E402

# Build the dialog exactly as show_prefs_dialog() would (parent=None is fine
# here — parenting only affects on-screen centering, not the rendered pixels).
# __init__ both builds the form layout and populates every field from the live
# node_layout_prefs.prefs_singleton defaults, so no extra setup call is needed.
preferences_dialog = NodeLayoutPrefsDialog(parent=None)

# Realize the widget so the QFormLayout rows and section headers are fully
# computed before capture. The injected capture() settles the Qt event loop
# before grabbing, so all five sections render non-blank.
preferences_dialog.show()

# Writes preferences-dialog.png into the --output-dir (docs/images).
capture(preferences_dialog, "preferences-dialog")  # noqa: F821 — injected by the runner
