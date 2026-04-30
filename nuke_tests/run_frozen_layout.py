"""Run layout on frozen_nodes.nk and save result for inspection.

Run with:  nuke -t /workspace/nuke_tests/run_frozen_layout.py

Outputs positions to stdout and saves post-layout .nk file.
"""
import os
import sys

_WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKSPACE not in sys.path:
    sys.path.insert(0, _WORKSPACE)

import node_layout  # noqa: E402, I001
import node_layout_state  # noqa: E402
import nuke  # noqa: E402

node_layout._build_toolbar_folder_map = lambda: {}
nuke.lastHitGroup = lambda: nuke.root()


def main():
    fixture_path = os.path.join(os.path.dirname(__file__), "frozen_nodes.nk")
    nuke.scriptOpen(fixture_path)
    print(f"Loaded {len(nuke.allNodes())} nodes")

    # Find layout root (bottom-most Merge)
    merges = [n for n in nuke.allNodes() if n.Class() == "Merge2"]
    root_node = max(merges, key=lambda n: n.ypos())
    print(f"Root: {root_node.name()}")

    # Print all positions BEFORE layout
    print("\n=== BEFORE ===")
    for n in sorted(nuke.allNodes(), key=lambda n: n.name()):
        fg = node_layout_state.read_freeze_group(n)
        fg_str = f" [freeze:{fg[:8]}]" if fg else ""
        print(f"  {n.name():20s} x={n.xpos():6d} y={n.ypos():6d} w={n.screenWidth():3d}{fg_str}")

    # Run layout
    for n in nuke.allNodes():
        n.setSelected(False)
    root_node.setSelected(True)
    node_layout.layout_upstream()

    # Print all positions AFTER layout
    print("\n=== AFTER ===")
    for n in sorted(nuke.allNodes(), key=lambda n: n.name()):
        fg = node_layout_state.read_freeze_group(n)
        fg_str = f" [freeze:{fg[:8]}]" if fg else ""
        print(f"  {n.name():20s} x={n.xpos():6d} y={n.ypos():6d} w={n.screenWidth():3d}{fg_str}")

    # Save result
    output_path = os.path.join(os.path.dirname(__file__), "output", "frozen_nodes_after.nk")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    nuke.scriptSave(output_path)
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
