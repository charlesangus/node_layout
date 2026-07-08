"""Widget-capture scenario: Node Layout "leader window" HUD overlay.

Run with nuke-screenshotter's widget mode (auto-detected from the .py
extension)::

    NUKE_PATH=$PWD nuke_dag_capture_auto \
        docs/screenshots/gui/leader_capture.py --output-dir docs/images

The nuke-screenshotter runner execs this file inside a live headless Nuke/Qt
session with ``capture(widget, name)`` and ``nuke`` already injected into
globals (do NOT import them). Each ``capture(widget, name)`` call renders one
widget to ``<name>.png`` in the output directory, so ``capture(overlay,
"leader-window")`` produces ``leader-window.png``.

Why widget mode (not playback ``.json``): the leader HUD is the
``LeaderKeyOverlay`` QDialog defined in ``node_layout_overlay.py``. It sets no
Qt ``objectName``, and the live overlay only appears transiently after
``node_layout_leader.arm()`` runs while the DAG panel holds keyboard focus and
a preference-driven timer fires — none of which a playback target resolver can
reliably grab. Constructing the overlay widget directly and handing it to
``capture()`` renders exactly the documented HUD (title, colour-coded QWERTY key
badges, and the sidebar key list) deterministically.

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
        # docs/screenshots/gui/leader_capture.py -> repository root is four up.
        repository_root = pathlib.Path(this_file).resolve().parent.parent.parent.parent
        yield str(repository_root)

    explicit_repo = os.environ.get("NODE_LAYOUT_REPO")
    if explicit_repo:
        yield explicit_repo

    for nuke_path_entry in os.environ.get("NUKE_PATH", "").split(os.pathsep):
        if nuke_path_entry:
            yield nuke_path_entry


def _ensure_node_layout_importable():
    """Add the first root that actually contains node_layout_overlay.py to sys.path."""
    for candidate_root in _candidate_package_roots():
        if os.path.isfile(os.path.join(candidate_root, "node_layout_overlay.py")):
            if candidate_root not in sys.path:
                sys.path.insert(0, candidate_root)
            return candidate_root
    return None


if _ensure_node_layout_importable() is None:
    raise RuntimeError(
        "Could not locate the node_layout repository root (looked for "
        "node_layout_overlay.py relative to __file__, then NODE_LAYOUT_REPO, "
        "then each NUKE_PATH entry). Set the NODE_LAYOUT_REPO environment "
        "variable (or NUKE_PATH) to the node_layout repository root."
    )

from node_layout_overlay import LeaderKeyOverlay  # noqa: E402

# Build the HUD overlay exactly as node_layout_leader.arm() would (parent=None is
# fine here — parenting only affects on-screen centering, not the rendered pixels).
leader_overlay = LeaderKeyOverlay(parent=None)

# Realize the widget so the grid/sidebar layouts and the translucent rounded-rect
# paintEvent are fully computed before capture. The injected capture() settles the
# Qt event loop before grabbing, so the async-painted badges render non-blank.
leader_overlay.show()

# Writes leader-window.png into the --output-dir (docs/images).
capture(leader_overlay, "leader-window")  # noqa: F821 — injected by the runner
