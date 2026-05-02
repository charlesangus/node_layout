"""Regression tests for bbox-engine PR review fixes.

Covers three behaviours that were promoted from one-off live-Nuke fixes
into permanent regression coverage:

* Diamond resolution + ``push_nodes_to_make_room`` skip-set in
  ``layout_selected``.
* Diamond resolution + skip-set covering touched nodes in
  ``layout_selected_horizontal``.
* ``layout_selected_horizontal_place_only`` translates side-input
  subtrees as a rigid unit (offsets between side-input nodes are
  preserved across the call).
"""

from unittest.mock import patch

from tests import _compare_stub_nuke as stub

stub.install_nuke_stub()

import node_layout  # noqa: E402
import node_layout_bbox  # noqa: E402  # registers the bbox engine


def _diamond_marker_dots(universe):
    return [
        n for n in universe.nodes
        if n.Class() == "Dot" and n.knob("node_layout_diamond_dot") is not None
    ]


def _build_selected_diamond():
    universe = stub.Universe()
    a = universe.add(stub._Node(node_class="Read", name="A", xpos=0, ypos=0))
    b = universe.add(stub._Node(node_class="Grade", name="B", xpos=0, ypos=80))
    c = universe.add(stub._Node(node_class="Blur", name="C", xpos=180, ypos=80))
    d = universe.add(
        stub._Node(node_class="Merge2", name="D", xpos=80, ypos=180, max_inputs=2)
    )
    b.setInput(0, a)
    c.setInput(0, a)
    d.setInput(0, b)
    d.setInput(1, c)
    universe.select(a, b, c, d)
    stub.set_universe(universe)
    return universe


def _build_horizontal_with_side_diamond():
    universe = stub.Universe()
    spine_left = universe.add(
        stub._Node(node_class="Grade", name="SpineLeft", xpos=0, ypos=180)
    )
    spine_root = universe.add(
        stub._Node(node_class="Merge2", name="SpineRoot", xpos=220, ypos=180,
                   max_inputs=2)
    )
    a = universe.add(stub._Node(node_class="Read", name="A", xpos=40, ypos=-120))
    b = universe.add(stub._Node(node_class="Grade", name="B", xpos=0, ypos=-40))
    c = universe.add(stub._Node(node_class="Blur", name="C", xpos=180, ypos=-40))
    d = universe.add(
        stub._Node(node_class="Merge2", name="D", xpos=80, ypos=60, max_inputs=2)
    )
    spine_root.setInput(0, spine_left)
    spine_root.setInput(1, d)
    b.setInput(0, a)
    c.setInput(0, a)
    d.setInput(0, b)
    d.setInput(1, c)
    universe.select(spine_left, spine_root)
    stub.set_universe(universe)
    return universe, {n.name(): n for n in universe.nodes}


def _build_horizontal_place_only_side_chain():
    universe = stub.Universe()
    source = universe.add(stub._Node(node_class="Read", name="Source", xpos=-180, ypos=180))
    spine_left = universe.add(
        stub._Node(node_class="Grade", name="SpineLeft", xpos=0, ypos=180)
    )
    spine_root = universe.add(
        stub._Node(node_class="Merge2", name="SpineRoot", xpos=220, ypos=180,
                   max_inputs=2)
    )
    side_leaf = universe.add(
        stub._Node(node_class="Read", name="SideLeaf", xpos=560, ypos=-20)
    )
    side_root = universe.add(
        stub._Node(node_class="Grade", name="SideRoot", xpos=410, ypos=70)
    )
    spine_left.setInput(0, source)
    spine_root.setInput(0, spine_left)
    spine_root.setInput(1, side_root)
    side_root.setInput(0, side_leaf)
    universe.select(spine_left, spine_root)
    stub.set_universe(universe)
    return universe, side_root, side_leaf


def test_layout_selected_resolves_diamonds_and_skips_created_dot_in_push_room():
    universe = _build_selected_diamond()
    captured_skip_sets = []

    with patch.object(
        node_layout,
        "push_nodes_to_make_room",
        side_effect=lambda ids, *_args, **_kwargs: captured_skip_sets.append(set(ids)),
    ):
        node_layout_bbox.BboxEngine().layout_selected()

    dots = _diamond_marker_dots(universe)
    assert len(dots) == 1
    assert captured_skip_sets
    assert id(dots[0]) in captured_skip_sets[-1]


def test_selected_horizontal_resolves_widened_scope_diamonds_and_skips_touched_nodes():
    universe, nodes = _build_horizontal_with_side_diamond()
    captured_skip_sets = []

    with patch.object(
        node_layout,
        "push_nodes_to_make_room",
        side_effect=lambda ids, *_args, **_kwargs: captured_skip_sets.append(set(ids)),
    ):
        node_layout_bbox.BboxEngine().layout_selected_horizontal()

    dots = _diamond_marker_dots(universe)
    assert len(dots) == 1
    assert captured_skip_sets
    skip_ids = captured_skip_sets[-1]
    assert id(dots[0]) in skip_ids
    assert id(nodes["A"]) in skip_ids
    assert id(nodes["D"]) in skip_ids


def test_selected_horizontal_place_only_moves_side_subtree_as_rigid_unit():
    _universe, side_root, side_leaf = _build_horizontal_place_only_side_chain()
    original_offset = (
        side_leaf.xpos() - side_root.xpos(),
        side_leaf.ypos() - side_root.ypos(),
    )

    node_layout_bbox.BboxEngine().layout_selected_horizontal_place_only()

    assert (
        side_leaf.xpos() - side_root.xpos(),
        side_leaf.ypos() - side_root.ypos(),
    ) == original_offset
