"""Headless Nuke layout runner for integration testing.

Run with:
    nuke -t /workspace/nuke_tests/run_layout.py

Configuration is read from environment variables to avoid argument-parsing
issues between Nuke and sys.argv:

    NL_INPUT          path to input .nk fixture
    NL_OUTPUT         path to write the post-layout .nk (optional)
    NL_POSITIONS_JSON path to write node positions as JSON
    NL_ROOT_NODE      name of the node to pass as layout root (layout_upstream)
    NL_COMMAND        layout command: layout_upstream | layout_selected
                      (default: layout_upstream)
    NL_SELECT         comma-separated node names to select before layout_selected
                      (default: all nodes)

Outputs a JSON file at NL_POSITIONS_JSON with structure:
    {
        "NodeName": {
            "xpos": int, "ypos": int, "class": str,
            "freeze_group": str|null
        },
        ...
    }
"""
import json
import os
import sys
import traceback

# ---------------------------------------------------------------------------
# sys.path: make the workspace root importable so node_layout et al. resolve.
# ---------------------------------------------------------------------------
_WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKSPACE not in sys.path:
    sys.path.insert(0, _WORKSPACE)

import nuke  # noqa: E402 (must come after sys.path setup; provided by Nuke runtime)
import node_layout  # noqa: E402
import node_layout_state  # noqa: E402

# ---------------------------------------------------------------------------
# Terminal-mode patches
# In headless (-t) mode several GUI-only Nuke APIs raise RuntimeError.
# Patch them here, before any layout code runs, to ensure the layout logic
# (which is what we're testing) executes normally.
# ---------------------------------------------------------------------------

# 1. nuke.menu() — raises "not in GUI mode"; the toolbar-folder map is only
#    used for spacing hints.  Replace _build_toolbar_folder_map with a stub
#    that returns an empty dict, so same_toolbar_folder() returns True (the
#    "same folder" fallback) for all node pairs.
node_layout._build_toolbar_folder_map = lambda: {}

# 2. nuke.lastHitGroup() — may return None in terminal mode.  The layout
#    functions must call this as their very first Nuke API call for undo
#    tracking; we redirect it to the root group so `with current_group:` works.
nuke.lastHitGroup = lambda: nuke.root()


def _read_env(key, default=None):
    value = os.environ.get(key, default)
    if value is None:
        raise EnvironmentError(f"Required environment variable {key} not set")
    return value


def _collect_positions():
    """Return a dict of node name -> position/class/freeze_group info."""
    result = {}
    for node in nuke.allNodes(recurseGroups=False):
        freeze_uuid = node_layout_state.read_freeze_group(node)
        result[node.name()] = {
            "xpos": node.xpos(),
            "ypos": node.ypos(),
            "class": node.Class(),
            "freeze_group": freeze_uuid,
        }
    return result


def main():
    input_nk = _read_env("NL_INPUT")
    positions_json = _read_env("NL_POSITIONS_JSON")
    output_nk = os.environ.get("NL_OUTPUT")
    command = os.environ.get("NL_COMMAND", "layout_upstream")
    root_node_name = os.environ.get("NL_ROOT_NODE")
    select_names = os.environ.get("NL_SELECT")

    print(f"[run_layout] Loading: {input_nk}")
    nuke.scriptOpen(input_nk)

    print(f"[run_layout] Nodes loaded: {[n.name() for n in nuke.allNodes()]}")

    if command == "layout_upstream":
        if root_node_name is None:
            raise EnvironmentError("NL_ROOT_NODE must be set for layout_upstream")

        root_node = nuke.toNode(root_node_name)
        if root_node is None:
            raise ValueError(f"Node not found: {root_node_name!r}")

        # Deselect all, then select only the root node.
        for n in nuke.allNodes():
            n.setSelected(False)
        root_node.setSelected(True)

        print(f"[run_layout] Running layout_upstream on {root_node_name!r}")
        node_layout.layout_upstream()

    elif command == "layout_selected":
        if select_names:
            names = [s.strip() for s in select_names.split(",")]
            for n in nuke.allNodes():
                n.setSelected(n.name() in names)
        else:
            nuke.selectAll()

        # For layout_selected we also need a "selected node" for internal use;
        # pick the first Write node or the first node in the selection.
        selected = nuke.selectedNodes()
        if not selected:
            raise ValueError("No nodes selected for layout_selected")

        write_nodes = [n for n in selected if n.Class() in ("Write", "Write2")]
        primary = write_nodes[0] if write_nodes else selected[0]

        # layout_selected uses nuke.selectedNodes() internally, so selection is set.
        print(f"[run_layout] Running layout_selected (primary: {primary.name()!r})")
        node_layout.layout_selected()

    elif command == "layout_selected_horizontal":
        if select_names:
            names = [s.strip() for s in select_names.split(",")]
            for n in nuke.allNodes():
                n.setSelected(n.name() in names)
        else:
            nuke.selectAll()

        selected = nuke.selectedNodes()
        if not selected:
            raise ValueError("No nodes selected for layout_selected_horizontal")

        print(f"[run_layout] Running layout_selected_horizontal (selected: {[n.name() for n in selected]})")
        node_layout.layout_selected_horizontal()

    else:
        raise ValueError(f"Unknown NL_COMMAND: {command!r}")

    # Save output script if requested.
    if output_nk:
        nuke.scriptSave(output_nk)
        print(f"[run_layout] Saved: {output_nk}")

    # Always write positions JSON.
    positions = _collect_positions()
    with open(positions_json, "w") as fh:
        json.dump(positions, fh, indent=2)
    print(f"[run_layout] Positions written: {positions_json}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
