import os
import sys

from tests._compare_stub_nuke import (
    SCENARIO_BUILDERS,
    Universe,
    _Node,
    find_overlapping_node_pairs,
    install_nuke_stub,
    set_node_state,
    set_universe,
)

_ISOLATED_MODULES = [
    "nuke",
    "node_layout",
    "node_layout_engine",
    "node_layout_prefs",
    "node_layout_state",
    "node_layout_bbox",
]


def test_bbox_side_routing_dot_is_consumer_centered_with_subtree_gap():
    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

        import node_layout
        import node_layout_bbox
        import node_layout_prefs

        universe = Universe()
        primary = universe.add(
            _Node(node_class="Read", name="Primary", xpos=0, ypos=0)
        )
        side = universe.add(_Node(node_class="Read", name="Side", xpos=200, ypos=0))
        merge = universe.add(
            _Node(node_class="Merge2", name="Merge", xpos=400, ypos=400, max_inputs=2)
        )
        merge.setInput(0, primary)
        merge.setInput(1, side)
        for node in (primary, side, merge):
            set_node_state(node)
        universe.select(merge)
        set_universe(universe)

        snap = node_layout.get_dag_snap_threshold()
        expected_gap = max(
            snap - 1,
            int(
                node_layout._subtree_margin(
                    merge,
                    1,
                    node_layout_prefs.prefs_singleton.get(
                        "scaling_reference_count"
                    ),
                    mode_multiplier=node_layout_prefs.prefs_singleton.get(
                        "normal_multiplier"
                    ),
                )
            ),
        )

        node_layout.layout_upstream()

        routing_dot = merge.input(1)
        assert routing_dot is not None
        assert routing_dot.Class() == "Dot"
        assert routing_dot.knob(node_layout_bbox._SIDE_DOT_KNOB_NAME) is not None
        assert routing_dot.input(0) is side

        expected_dot_y = merge.ypos() + (
            merge.screenHeight() - routing_dot.screenHeight()
        ) // 2
        assert routing_dot.ypos() == expected_dot_y

        center_offset = (merge.screenHeight() - routing_dot.screenHeight()) // 2
        actual_gap = routing_dot.ypos() - (side.ypos() + side.screenHeight())
        expected_gap += center_offset
        assert actual_gap == expected_gap
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine


def test_layout_upstream_uses_bbox_without_engine_env():
    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ.pop("NODE_LAYOUT_ENGINE", None)

        import node_layout
        import node_layout_bbox

        universe = Universe()
        primary = universe.add(
            _Node(node_class="Read", name="Primary", xpos=0, ypos=0)
        )
        side = universe.add(_Node(node_class="Read", name="Side", xpos=200, ypos=0))
        merge = universe.add(
            _Node(node_class="Merge2", name="Merge", xpos=400, ypos=400, max_inputs=2)
        )
        merge.setInput(0, primary)
        merge.setInput(1, side)
        for node in (primary, side, merge):
            set_node_state(node)
        universe.select(merge)
        set_universe(universe)

        node_layout.layout_upstream()

        routing_dot = merge.input(1)
        assert routing_dot is not None
        assert routing_dot.Class() == "Dot"
        assert routing_dot.knob(node_layout_bbox._SIDE_DOT_KNOB_NAME) is not None
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine


def test_bbox_existing_side_routing_dot_is_consumer_centered_with_subtree_gap():
    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

        import node_layout
        import node_layout_bbox
        import node_layout_prefs

        universe = Universe()
        primary = universe.add(
            _Node(node_class="Read", name="Primary", xpos=0, ypos=0)
        )
        side = universe.add(_Node(node_class="Read", name="Side", xpos=200, ypos=0))
        routing_dot = universe.add(
            _Node(
                node_class="Dot",
                name="ExistingDot",
                width=12,
                height=12,
                xpos=300,
                ypos=200,
                max_inputs=1,
            )
        )
        merge = universe.add(
            _Node(node_class="Merge2", name="Merge", xpos=400, ypos=400, max_inputs=2)
        )
        routing_dot.setInput(0, side)
        merge.setInput(0, primary)
        merge.setInput(1, routing_dot)
        for node in (primary, side, routing_dot, merge):
            set_node_state(node)
        universe.select(merge)
        set_universe(universe)

        snap = node_layout.get_dag_snap_threshold()
        expected_gap = max(
            snap - 1,
            int(
                node_layout._subtree_margin(
                    merge,
                    1,
                    node_layout_prefs.prefs_singleton.get(
                        "scaling_reference_count"
                    ),
                    mode_multiplier=node_layout_prefs.prefs_singleton.get(
                        "normal_multiplier"
                    ),
                )
            ),
        )

        node_layout.layout_upstream()

        assert merge.input(1) is routing_dot
        assert routing_dot.knob(node_layout_bbox._SIDE_DOT_KNOB_NAME) is not None
        expected_dot_y = merge.ypos() + (
            merge.screenHeight() - routing_dot.screenHeight()
        ) // 2
        assert routing_dot.ypos() == expected_dot_y

        center_offset = (merge.screenHeight() - routing_dot.screenHeight()) // 2
        actual_gap = routing_dot.ypos() - (side.ypos() + side.screenHeight())
        expected_gap += center_offset
        assert actual_gap == expected_gap
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine


def test_bbox_side_routing_dot_gap_uses_fixed_reference_count():
    def run_scenario(select_downstream_root):
        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

        import node_layout
        import node_layout_bbox
        import node_layout_prefs

        universe = Universe()
        primary = universe.add(
            _Node(node_class="Read", name="Primary", xpos=0, ypos=0)
        )
        side = universe.add(_Node(node_class="Read", name="Side", xpos=200, ypos=0))
        merge = universe.add(
            _Node(node_class="Merge2", name="Merge", xpos=400, ypos=400, max_inputs=2)
        )
        write = universe.add(
            _Node(node_class="Write", name="Write", xpos=400, ypos=500, max_inputs=1)
        )
        merge.setInput(0, primary)
        merge.setInput(1, side)
        write.setInput(0, merge)
        for node in (primary, side, merge, write):
            set_node_state(node)
        universe.select(write if select_downstream_root else merge)
        set_universe(universe)

        node_layout.layout_upstream()
        routing_dot = merge.input(1)
        assert routing_dot.Class() == "Dot"
        assert routing_dot.knob(node_layout_bbox._SIDE_DOT_KNOB_NAME) is not None
        fixed_reference_gap = int(
            node_layout._subtree_margin(
                merge,
                1,
                node_layout_prefs.prefs_singleton.get("scaling_reference_count"),
                mode_multiplier=node_layout_prefs.prefs_singleton.get(
                    "normal_multiplier"
                ),
            )
        )
        center_offset = (merge.screenHeight() - routing_dot.screenHeight()) // 2
        gap = routing_dot.ypos() - (side.ypos() + side.screenHeight())
        assert gap == fixed_reference_gap + center_offset
        return gap

    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        subtree_gap = run_scenario(select_downstream_root=False)
        larger_tree_gap = run_scenario(select_downstream_root=True)
        assert larger_tree_gap == subtree_gap
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine


def test_bbox_selected_horizontal_only_creates_leftmost_input0_dot():
    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

        import node_layout

        universe = Universe()
        left = universe.add(_Node(node_class="Read", name="Left", xpos=0, ypos=0))
        side = universe.add(_Node(node_class="Read", name="Side", xpos=100, ypos=0))
        spine_left = universe.add(
            _Node(node_class="Grade", name="SpineLeft", xpos=200, ypos=0, max_inputs=1)
        )
        spine_root = universe.add(
            _Node(node_class="Merge2", name="SpineRoot", xpos=300, ypos=0, max_inputs=2)
        )
        spine_left.setInput(0, left)
        spine_root.setInput(0, spine_left)
        spine_root.setInput(1, side)
        for node in (left, side, spine_left, spine_root):
            set_node_state(node)
        universe.select(spine_left, spine_root)
        set_universe(universe)

        node_layout.layout_selected_horizontal()

        leftmost_dot = spine_left.input(0)
        assert leftmost_dot is not left
        assert leftmost_dot.Class() == "Dot"
        assert leftmost_dot.knob(node_layout._LEFTMOST_DOT_KNOB_NAME) is not None
        assert leftmost_dot.input(0) is left
        assert spine_root.input(0) is spine_left
        assert spine_root.input(1) is side

        dots = [node for node in universe.nodes if node.Class() == "Dot"]
        assert dots == [leftmost_dot]
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine


def test_bbox_selected_horizontal_spaces_side_subtree_bboxes_on_first_run():
    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

        import node_layout

        universe = Universe()
        left = universe.add(
            _Node(node_class="Read", name="Left", width=80, xpos=0, ypos=0)
        )
        side_left = universe.add(
            _Node(node_class="Read", name="SideLeft", width=500, xpos=0, ypos=0)
        )
        side_root = universe.add(
            _Node(node_class="Read", name="SideRoot", width=500, xpos=0, ypos=0)
        )
        spine_left = universe.add(
            _Node(
                node_class="Merge2",
                name="SpineLeft",
                xpos=200,
                ypos=0,
                max_inputs=2,
            )
        )
        spine_root = universe.add(
            _Node(
                node_class="Merge2",
                name="SpineRoot",
                xpos=300,
                ypos=0,
                max_inputs=2,
            )
        )
        spine_left.setInput(0, left)
        spine_left.setInput(1, side_left)
        spine_root.setInput(0, spine_left)
        spine_root.setInput(1, side_root)
        for node in (left, side_left, side_root, spine_left, spine_root):
            set_node_state(node)
        universe.select(spine_left, spine_root)
        set_universe(universe)

        node_layout.layout_selected_horizontal()

        assert find_overlapping_node_pairs(universe) == []
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine


def test_bbox_layout_upstream_replay_does_not_add_horizontal_spine_side_dots():
    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

        import node_layout
        import node_layout_bbox

        universe = Universe()
        left = universe.add(_Node(node_class="Read", name="Left", xpos=0, ypos=0))
        side = universe.add(_Node(node_class="Read", name="Side", xpos=100, ypos=0))
        spine_left = universe.add(
            _Node(node_class="Grade", name="SpineLeft", xpos=200, ypos=0, max_inputs=1)
        )
        spine_root = universe.add(
            _Node(node_class="Merge2", name="SpineRoot", xpos=300, ypos=0, max_inputs=2)
        )
        spine_left.setInput(0, left)
        spine_root.setInput(0, spine_left)
        spine_root.setInput(1, side)
        for node in (left, side, spine_left, spine_root):
            set_node_state(node)
        universe.select(spine_left, spine_root)
        set_universe(universe)

        node_layout.layout_selected_horizontal()
        universe.select(spine_root)
        node_layout.layout_upstream()

        assert spine_root.input(0) is spine_left
        assert spine_root.input(1) is side
        leftmost_dot = spine_left.input(0)
        assert leftmost_dot.Class() == "Dot"
        assert leftmost_dot.knob(node_layout._LEFTMOST_DOT_KNOB_NAME) is not None
        assert leftmost_dot.input(0) is left
        assert leftmost_dot.knob(node_layout_bbox._SIDE_DOT_KNOB_NAME) is None

        dots = [node for node in universe.nodes if node.Class() == "Dot"]
        assert dots == [leftmost_dot]
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine


def test_bbox_layout_upstream_does_not_create_horizontal_output_dot():
    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

        import node_layout
        import node_layout_state

        universe = Universe()
        left = universe.add(_Node(node_class="Read", name="Left", xpos=0, ypos=0))
        horizontal = universe.add(
            _Node(node_class="Grade", name="Horizontal", xpos=200, ypos=0, max_inputs=1)
        )
        write = universe.add(
            _Node(node_class="Write", name="Write", xpos=400, ypos=100, max_inputs=1)
        )
        horizontal.setInput(0, left)
        write.setInput(0, horizontal)
        set_node_state(left)
        set_node_state(horizontal, mode="horizontal")
        set_node_state(write)
        universe.select(write)
        set_universe(universe)

        node_layout.layout_upstream()

        assert write.input(0) is horizontal
        leftmost_dot = horizontal.input(0)
        assert leftmost_dot.Class() == "Dot"
        assert leftmost_dot.knob(node_layout._LEFTMOST_DOT_KNOB_NAME) is not None
        assert leftmost_dot.input(0) is left
        assert node_layout_state.read_node_state(horizontal)["mode"] == "horizontal"
        assert [
            node for node in universe.nodes
            if node.knob(node_layout._OUTPUT_DOT_KNOB_NAME) is not None
        ] == []
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine


def test_bbox_leftmost_dot_clears_full_horizontal_segment_bbox():
    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

        import node_layout
        import node_layout_prefs

        universe = Universe()
        left = universe.add(
            _Node(node_class="Read", name="Left", width=80, xpos=0, ypos=0)
        )
        wide_side = universe.add(
            _Node(node_class="Read", name="WideSide", width=500, xpos=200, ypos=0)
        )
        spine_left = universe.add(
            _Node(
                node_class="Merge2",
                name="SpineLeft",
                width=80,
                xpos=300,
                ypos=0,
                max_inputs=2,
            )
        )
        spine_root = universe.add(
            _Node(
                node_class="Grade",
                name="SpineRoot",
                width=80,
                xpos=500,
                ypos=0,
                max_inputs=1,
            )
        )
        spine_left.setInput(0, left)
        spine_left.setInput(1, wide_side)
        spine_root.setInput(0, spine_left)
        for node in (left, wide_side, spine_left, spine_root):
            set_node_state(node)
        universe.select(spine_left, spine_root)
        set_universe(universe)

        node_layout.layout_selected_horizontal()

        leftmost_dot = spine_left.input(0)
        h_gap = int(
            node_layout_prefs.prefs_singleton.get("horizontal_subtree_gap")
            * node_layout_prefs.prefs_singleton.get("normal_multiplier")
        )
        wide_side_left_overhang = (
            spine_left.screenWidth() // 2 - wide_side.screenWidth() // 2
        )
        segment_left = spine_left.xpos() + min(0, wide_side_left_overhang)
        left_column_right = max(
            left.xpos() + left.screenWidth(),
            leftmost_dot.xpos() + leftmost_dot.screenWidth(),
        )

        assert leftmost_dot.knob(node_layout._LEFTMOST_DOT_KNOB_NAME) is not None
        assert left.ypos() + left.screenHeight() < leftmost_dot.ypos()
        assert left_column_right <= segment_left - h_gap
        assert find_overlapping_node_pairs(universe) == []
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine


def test_selected_horizontal_place_only_preserves_side_subtree_horizontal_mode():
    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

        import node_layout
        import node_layout_state

        universe = Universe()
        left = universe.add(_Node(node_class="Read", name="Left", xpos=0, ypos=0))
        spine_left = universe.add(
            _Node(node_class="Grade", name="SpineLeft", xpos=200, ypos=0, max_inputs=1)
        )
        spine_root = universe.add(
            _Node(node_class="Merge2", name="SpineRoot", xpos=300, ypos=0, max_inputs=2)
        )
        side_leaf = universe.add(
            _Node(node_class="Read", name="SideLeaf", xpos=500, ypos=-100)
        )
        side_root = universe.add(
            _Node(node_class="Grade", name="SideRoot", xpos=600, ypos=0, max_inputs=1)
        )
        spine_left.setInput(0, left)
        spine_root.setInput(0, spine_left)
        spine_root.setInput(1, side_root)
        side_root.setInput(0, side_leaf)
        for node in (left, spine_left, spine_root):
            set_node_state(node)
        for node in (side_leaf, side_root):
            set_node_state(node, mode="horizontal")
        universe.select(spine_left, spine_root)
        set_universe(universe)

        node_layout.layout_selected_horizontal_place_only()

        assert node_layout_state.read_node_state(side_root)["mode"] == "horizontal"
        assert node_layout_state.read_node_state(side_leaf)["mode"] == "horizontal"
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine


def test_selected_horizontal_place_only_shared_stub_scenarios_do_not_overlap():
    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    scenarios = [
        "vertical_chain",
        "vertical_3input_merge",
        "vertical_with_mask",
        "horizontal_chain",
        "diamond",
    ]
    try:
        for scenario_name in scenarios:
            for name in _ISOLATED_MODULES:
                sys.modules.pop(name, None)
            install_nuke_stub()
            os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

            import node_layout

            root, _roots, universe = SCENARIO_BUILDERS[scenario_name]()
            set_universe(universe)

            node_layout.layout_selected_horizontal_place_only()

            assert find_overlapping_node_pairs(universe) == []
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine


def test_bbox_prepared_side_dots_keep_fan_and_staircase_rows_distinct():
    saved_modules = {name: sys.modules.get(name) for name in _ISOLATED_MODULES}
    saved_engine = os.environ.get("NODE_LAYOUT_ENGINE")
    try:
        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

        import node_layout
        import node_layout_bbox

        fan_universe = Universe()
        fan_reads = [
            fan_universe.add(
                _Node(node_class="Read", name=f"FanRead{i}", xpos=i * 120, ypos=0)
            )
            for i in range(3)
        ]
        fan_merge = fan_universe.add(
            _Node(
                node_class="Merge2",
                name="FanMerge",
                xpos=240,
                ypos=300,
                max_inputs=4,
            )
        )
        fan_merge.setInput(0, fan_reads[0])
        fan_merge.setInput(1, fan_reads[1])
        fan_merge.setInput(3, fan_reads[2])
        for node in (*fan_reads, fan_merge):
            set_node_state(node)
        fan_universe.select(fan_merge)
        set_universe(fan_universe)

        node_layout.layout_upstream()

        fan_dots = [fan_merge.input(slot) for slot in (0, 1, 3)]
        assert all(dot.Class() == "Dot" for dot in fan_dots)
        assert all(
            dot.knob(node_layout_bbox._SIDE_DOT_KNOB_NAME) is not None
            for dot in fan_dots
        )
        snap = node_layout.get_dag_snap_threshold()
        fan_row_y = fan_merge.ypos() - (snap - 1) - fan_dots[0].screenHeight()
        assert {dot.ypos() for dot in fan_dots} == {fan_row_y}
        assert find_overlapping_node_pairs(fan_universe) == []

        for name in _ISOLATED_MODULES:
            sys.modules.pop(name, None)
        install_nuke_stub()
        os.environ["NODE_LAYOUT_ENGINE"] = "bbox"

        import node_layout
        import node_layout_bbox

        stair_universe = Universe()
        primary = stair_universe.add(
            _Node(node_class="Read", name="Primary", xpos=0, ypos=0)
        )
        side = stair_universe.add(
            _Node(node_class="Read", name="Side", xpos=120, ypos=0)
        )
        mask = stair_universe.add(
            _Node(node_class="Read", name="Mask", xpos=240, ypos=0)
        )
        stair_merge = stair_universe.add(
            _Node(
                node_class="Merge2",
                name="StairMerge",
                xpos=120,
                ypos=300,
                max_inputs=3,
            )
        )
        stair_merge.setInput(0, primary)
        stair_merge.setInput(1, side)
        stair_merge.setInput(2, mask)
        for node in (primary, side, mask, stair_merge):
            set_node_state(node)
        stair_universe.select(stair_merge)
        set_universe(stair_universe)

        node_layout.layout_upstream()

        stair_dots = [stair_merge.input(slot) for slot in (1, 2)]
        assert all(dot.Class() == "Dot" for dot in stair_dots)
        assert all(
            dot.knob(node_layout_bbox._SIDE_DOT_KNOB_NAME) is not None
            for dot in stair_dots
        )
        stair_row_y = stair_merge.ypos() + (
            stair_merge.screenHeight() - stair_dots[0].screenHeight()
        ) // 2
        assert {dot.ypos() for dot in stair_dots} == {stair_row_y}
        assert stair_row_y != fan_row_y
        assert find_overlapping_node_pairs(stair_universe) == []
    finally:
        for name in _ISOLATED_MODULES:
            if saved_modules[name] is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved_modules[name]
        if saved_engine is None:
            os.environ.pop("NODE_LAYOUT_ENGINE", None)
        else:
            os.environ["NODE_LAYOUT_ENGINE"] = saved_engine
