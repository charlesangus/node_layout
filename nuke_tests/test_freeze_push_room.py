"""Test: freeze block must not overlap B-spine or sibling subtrees after layout.

Run with:  nuke -t /workspace/nuke_tests/test_freeze_push_room.py

Loads the frozen_nodes.nk fixture which has:
  - A B-spine chain (CheckerBoard1 -> Merge4 -> Merge1 -> Merge2 -> Merge3)
  - Two freeze groups (15d7... with 3 members, 23b7... with 3 members)
  - Multiple side-input subtrees

Runs layout_upstream on the bottom-most node (Merge3) and checks that
freeze block bounding boxes don't overlap sibling subtrees or the B-spine.
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

NODE_WIDTH = 80  # standard Nuke node width for GUI mode


def collect_freeze_groups():
    """Return dict of uuid -> list of nodes."""
    groups = {}
    for node in nuke.allNodes():
        uuid = node_layout_state.read_freeze_group(node)
        if uuid:
            groups.setdefault(uuid, []).append(node)
    return groups


def node_bbox(node):
    """Return (left, top, right, bottom) using real or simulated width."""
    width = node.screenWidth() or NODE_WIDTH
    height = node.screenHeight() or 28
    return (node.xpos(), node.ypos(), node.xpos() + width, node.ypos() + height)


def group_bbox(nodes):
    """Return bounding box of a group of nodes."""
    bboxes = [node_bbox(n) for n in nodes]
    return (
        min(b[0] for b in bboxes),
        min(b[1] for b in bboxes),
        max(b[2] for b in bboxes),
        max(b[3] for b in bboxes),
    )


def bboxes_overlap(bbox_a, bbox_b):
    """Check if two bboxes overlap."""
    return (bbox_a[0] < bbox_b[2] and bbox_b[0] < bbox_a[2] and
            bbox_a[1] < bbox_b[3] and bbox_b[1] < bbox_a[3])


def print_bbox(label, bbox):
    print(f"  {label}: x=[{bbox[0]}, {bbox[2]}], y=[{bbox[1]}, {bbox[3]}]")


def main():
    # Load the fixture
    fixture_path = os.path.join(os.path.dirname(__file__), "frozen_nodes.nk")
    nuke.scriptOpen(fixture_path)

    all_nodes = nuke.allNodes()
    print(f"Loaded {len(all_nodes)} nodes from {fixture_path}")

    # Find the bottom-most Merge (layout root)
    merges = [n for n in all_nodes if n.Class() == "Merge2"]
    root_node = max(merges, key=lambda n: n.ypos())  # most downstream = highest ypos
    print(f"Layout root: {root_node.name()} at ({root_node.xpos()}, {root_node.ypos()})")

    # Print freeze block details before layout
    print("\n=== Freeze Block Construction ===")
    freeze_groups_before = collect_freeze_groups()
    for uuid, members in freeze_groups_before.items():
        from node_layout import FreezeBlock, _find_freeze_block_root
        block_root = _find_freeze_block_root(members)
        block = FreezeBlock(root=block_root, members=members, uuid=uuid)
        print(f"  Group {uuid[:8]}: root={block_root.name()}")
        print(f"    left_overhang={block.left_overhang}, right_extent={block.right_extent}")
        for m in members:
            input_names = ", ".join(
                m.input(s).name() for s in range(m.inputs()) if m.input(s)
            )
            print(f"    {m.name()}: xpos={m.xpos()}, ypos={m.ypos()}, "
                  f"inputs=[{input_names}]")

    # Print Merge1's inputs
    merge1 = nuke.toNode("Merge1")
    if merge1:
        print("\n  Merge1 inputs:")
        for slot in range(merge1.inputs()):
            inp = merge1.input(slot)
            if inp:
                print(f"    slot {slot}: {inp.name()} ({inp.Class()})")

    # Run layout
    for n in all_nodes:
        n.setSelected(False)
    root_node.setSelected(True)
    node_layout.layout_upstream()

    # Collect positions after layout
    print("\n=== AFTER layout ===")
    freeze_groups = collect_freeze_groups()
    for uuid, members in freeze_groups.items():
        print(f"\nFreeze group {uuid[:8]}:")
        for m in members:
            print(f"  {m.name()}: xpos={m.xpos()}, ypos={m.ypos()}")

    # Identify the B-spine (nodes on the primary input chain)
    spine_nodes = []
    cursor = root_node
    while cursor is not None:
        spine_nodes.append(cursor)
        cursor = cursor.input(0)
    spine_names = [n.name() for n in spine_nodes]
    print(f"\nB-spine: {spine_names}")

    # Get all side subtrees (non-spine, non-freeze nodes connected as side inputs)
    # For each Merge on the spine, input 1 is a side subtree root
    side_subtree_roots = []
    for spine_node in spine_nodes:
        if spine_node.Class() == "Merge2":
            for slot in range(1, spine_node.inputs()):
                side_input = spine_node.input(slot)
                if side_input is not None:
                    side_subtree_roots.append((spine_node.name(), slot, side_input))

    # Collect full subtrees for each side input
    side_subtrees = []
    for parent_name, slot, side_root in side_subtree_roots:
        subtree = node_layout.collect_subtree_nodes(side_root)
        # Include any freeze members that are part of this subtree
        subtree_ids = {id(n) for n in subtree}
        for _uuid, members in freeze_groups.items():
            for member in members:
                if id(member) in subtree_ids:
                    # Add all members of this freeze group
                    for m in members:
                        if id(m) not in subtree_ids:
                            subtree.append(m)
                            subtree_ids.add(id(m))
        side_subtrees.append((f"{parent_name}.input{slot}", subtree))

    # Compute bounding boxes
    spine_bbox = group_bbox(spine_nodes)
    print("\n=== Bounding Boxes ===")
    print_bbox("B-spine", spine_bbox)

    side_bboxes = []
    for label, subtree in side_subtrees:
        bbox = group_bbox(subtree)
        side_bboxes.append((label, bbox))
        print_bbox(label, bbox)

    # --- Overlap checks ---
    # Use actual screenWidth (0 in headless) for overlap checks, matching
    # what the layout engine sees. Simulated-width checks would detect
    # false positives since the engine places nodes for zero-width.
    failures = []

    def actual_bbox(nodes):
        """Bbox using actual screenWidth/screenHeight (0 in headless)."""
        left = min(n.xpos() for n in nodes)
        top = min(n.ypos() for n in nodes)
        right = max(n.xpos() + n.screenWidth() for n in nodes)
        bottom = max(n.ypos() + n.screenHeight() for n in nodes)
        return (left, top, right, bottom)

    def strict_overlap(bbox_a, bbox_b):
        """Strict overlap (interior intersection, not just touching)."""
        return (bbox_a[0] < bbox_b[2] and bbox_b[0] < bbox_a[2] and
                bbox_a[1] < bbox_b[3] and bbox_b[1] < bbox_a[3])

    actual_spine_bbox = actual_bbox(spine_nodes)
    actual_side_bboxes = []
    for label, subtree in side_subtrees:
        actual_side_bboxes.append((label, actual_bbox(subtree)))

    # Check each side subtree against the spine
    for label, bbox in actual_side_bboxes:
        if strict_overlap(bbox, actual_spine_bbox):
            failures.append(f"{label} bbox overlaps B-spine")

    # Check side subtrees against each other
    for i in range(len(actual_side_bboxes)):
        for j in range(i + 1, len(actual_side_bboxes)):
            label_i, bbox_i = actual_side_bboxes[i]
            label_j, bbox_j = actual_side_bboxes[j]
            if strict_overlap(bbox_i, bbox_j):
                failures.append(f"{label_i} overlaps {label_j}")

    print("\n=== Results ===")
    if failures:
        for msg in failures:
            print(f"  FAIL: {msg}")
        print(f"\n*** {len(failures)} OVERLAP(S) ***")
        sys.exit(1)
    else:
        print("  PASS: No overlaps detected.")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
