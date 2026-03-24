"""
freeze_test_scenarios.py -- Build 5 freeze group test scenarios in live Nuke.

Run this script in Nuke's Script Editor (or via execfile / import) to create
5 spatially-separated DAG configurations that exercise freeze group layout.

Each scenario is offset 500px in X from the previous one.
Positive Y is DOWN in Nuke's DAG coordinate system.
"""

import json
import uuid

import nuke


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_freeze_uuid(node, group_uuid):
    """Write a freeze_group UUID into the node_layout_state JSON knob."""
    tab_knob_name = "node_layout_tab"
    state_knob_name = "node_layout_state"

    if not node.knob(tab_knob_name):
        tab = nuke.Tab_Knob(tab_knob_name, "")
        tab.setFlag(nuke.INVISIBLE)
        node.addKnob(tab)

    if not node.knob(state_knob_name):
        state_knob = nuke.String_Knob(state_knob_name, "")
        state_knob.setFlag(nuke.INVISIBLE)
        node.addKnob(state_knob)

    raw = node.knob(state_knob_name).value()
    default_state = {
        "scheme": "normal",
        "mode": "vertical",
        "h_scale": 1.0,
        "v_scale": 1.0,
        "freeze_group": None,
    }
    state = json.loads(raw) if raw else dict(default_state)
    state["freeze_group"] = group_uuid
    node.knob(state_knob_name).setValue(json.dumps(state))


def _create_node(node_class, name, x_pos, y_pos):
    """Create a Nuke node, set its name and position."""
    node = nuke.createNode(node_class, inpanel=False)
    node.setName(name)
    node.setXYpos(x_pos, y_pos)
    return node


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------

Y_SPACING = 60          # vertical spacing between connected nodes
BASE_Y = 0              # starting Y for topmost node in each scenario


def build_scenario_1(base_x):
    """Scenario 1 -- Basic Freeze Group (vertical chain).

    Read1 -> Grade1 -> Blur1 -> Write1
    Freeze: Grade1, Blur1 (same UUID)
    Purpose: layout_upstream on Write1 should preserve Grade1-Blur1 relative positions.
    """
    y = BASE_Y
    read1 = _create_node("Read", "Read1", base_x, y)

    y += Y_SPACING
    grade1 = _create_node("Grade", "Grade1", base_x, y)
    grade1.setInput(0, read1)

    y += Y_SPACING
    blur1 = _create_node("Blur", "Blur1", base_x, y)
    blur1.setInput(0, grade1)

    y += Y_SPACING
    write1 = _create_node("Write", "Write1", base_x, y)
    write1.setInput(0, blur1)

    # Freeze Grade1 and Blur1 together
    freeze_uuid = str(uuid.uuid4())
    _set_freeze_uuid(grade1, freeze_uuid)
    _set_freeze_uuid(blur1, freeze_uuid)

    print("Scenario 1: Read1 -> Grade1* -> Blur1* -> Write1")
    print("  Frozen: Grade1, Blur1 (UUID: {})".format(freeze_uuid[:8]))
    return {"freeze_uuid": freeze_uuid, "frozen_nodes": ["Grade1", "Blur1"]}


def build_scenario_2(base_x):
    """Scenario 2 -- Freeze group with side branch.

    Read2 -> Grade2 -> Merge2 (A/input0)
    Read3 -> ColorCorrect1 -> Merge2 (B/input1)
    Merge2 -> Write2
    Freeze: Grade2, Merge2
    Purpose: side branch (Read3->ColorCorrect1) laid out normally, frozen group stays rigid.
    """
    y = BASE_Y

    # Main branch (A side)
    read2 = _create_node("Read", "Read2", base_x, y)

    y += Y_SPACING
    grade2 = _create_node("Grade", "Grade2", base_x, y)
    grade2.setInput(0, read2)

    # Side branch (B side) -- offset to the right
    side_x = base_x + 150
    read3 = _create_node("Read", "Read3", side_x, BASE_Y)

    color_correct1 = _create_node("ColorCorrect", "ColorCorrect1", side_x, BASE_Y + Y_SPACING)
    color_correct1.setInput(0, read3)

    # Merge -- positioned below both branches
    merge_y = BASE_Y + Y_SPACING * 2
    merge2 = _create_node("Merge2", "Merge2", base_x, merge_y)
    merge2.setInput(0, grade2)
    merge2.setInput(1, color_correct1)

    write_y = merge_y + Y_SPACING
    write2 = _create_node("Write", "Write2", base_x, write_y)
    write2.setInput(0, merge2)

    # Freeze Grade2 and Merge2 together
    freeze_uuid = str(uuid.uuid4())
    _set_freeze_uuid(grade2, freeze_uuid)
    _set_freeze_uuid(merge2, freeze_uuid)

    print("Scenario 2: Read2 -> Grade2* -> Merge2* <- ColorCorrect1 <- Read3")
    print("            Merge2* -> Write2")
    print("  Frozen: Grade2, Merge2 (UUID: {})".format(freeze_uuid[:8]))
    return {"freeze_uuid": freeze_uuid, "frozen_nodes": ["Grade2", "Merge2"]}


def build_scenario_3(base_x):
    """Scenario 3 -- Multiple independent freeze groups.

    Read4 -> Grade3 -> Blur2 -> Merge3 (A/input0)
    Read5 -> Grade4 -> Blur3 -> Merge3 (B/input1)
    Merge3 -> Write3
    Freeze-A: Grade3, Blur2
    Freeze-B: Grade4, Blur3
    Purpose: two independent freeze groups in the same tree.
    """
    y = BASE_Y

    # Left branch (A)
    read4 = _create_node("Read", "Read4", base_x, y)

    grade3 = _create_node("Grade", "Grade3", base_x, y + Y_SPACING)
    grade3.setInput(0, read4)

    blur2 = _create_node("Blur", "Blur2", base_x, y + Y_SPACING * 2)
    blur2.setInput(0, grade3)

    # Right branch (B) -- offset
    right_x = base_x + 150
    read5 = _create_node("Read", "Read5", right_x, y)

    grade4 = _create_node("Grade", "Grade4", right_x, y + Y_SPACING)
    grade4.setInput(0, read5)

    blur3 = _create_node("Blur", "Blur3", right_x, y + Y_SPACING * 2)
    blur3.setInput(0, grade4)

    # Merge
    merge_y = y + Y_SPACING * 3
    merge3 = _create_node("Merge2", "Merge3", base_x, merge_y)
    merge3.setInput(0, blur2)
    merge3.setInput(1, blur3)

    write3 = _create_node("Write", "Write3", base_x, merge_y + Y_SPACING)
    write3.setInput(0, merge3)

    # Freeze group A: Grade3, Blur2
    freeze_uuid_a = str(uuid.uuid4())
    _set_freeze_uuid(grade3, freeze_uuid_a)
    _set_freeze_uuid(blur2, freeze_uuid_a)

    # Freeze group B: Grade4, Blur3
    freeze_uuid_b = str(uuid.uuid4())
    _set_freeze_uuid(grade4, freeze_uuid_b)
    _set_freeze_uuid(blur3, freeze_uuid_b)

    print("Scenario 3: Read4 -> Grade3* -> Blur2* -> Merge3 <- Blur3** <- Grade4** <- Read5")
    print("            Merge3 -> Write3")
    print("  Frozen-A: Grade3, Blur2 (UUID: {})".format(freeze_uuid_a[:8]))
    print("  Frozen-B: Grade4, Blur3 (UUID: {})".format(freeze_uuid_b[:8]))
    return {
        "freeze_uuid_a": freeze_uuid_a,
        "freeze_uuid_b": freeze_uuid_b,
        "frozen_nodes_a": ["Grade3", "Blur2"],
        "frozen_nodes_b": ["Grade4", "Blur3"],
    }


def build_scenario_4(base_x):
    """Scenario 4 -- Freeze group in the middle of a long chain.

    Read6 -> Crop1 -> Grade5 -> Blur4 -> Saturation1 -> Write4
    Freeze: Grade5, Blur4 (middle segment only)
    Purpose: nodes above and below frozen segment still get laid out.
    """
    y = BASE_Y

    read6 = _create_node("Read", "Read6", base_x, y)

    y += Y_SPACING
    crop1 = _create_node("Crop", "Crop1", base_x, y)
    crop1.setInput(0, read6)

    y += Y_SPACING
    grade5 = _create_node("Grade", "Grade5", base_x, y)
    grade5.setInput(0, crop1)

    y += Y_SPACING
    blur4 = _create_node("Blur", "Blur4", base_x, y)
    blur4.setInput(0, grade5)

    y += Y_SPACING
    saturation1 = _create_node("Saturation", "Saturation1", base_x, y)
    saturation1.setInput(0, blur4)

    y += Y_SPACING
    write4 = _create_node("Write", "Write4", base_x, y)
    write4.setInput(0, saturation1)

    # Freeze Grade5 and Blur4
    freeze_uuid = str(uuid.uuid4())
    _set_freeze_uuid(grade5, freeze_uuid)
    _set_freeze_uuid(blur4, freeze_uuid)

    print("Scenario 4: Read6 -> Crop1 -> Grade5* -> Blur4* -> Saturation1 -> Write4")
    print("  Frozen: Grade5, Blur4 (UUID: {})".format(freeze_uuid[:8]))
    return {"freeze_uuid": freeze_uuid, "frozen_nodes": ["Grade5", "Blur4"]}


def build_scenario_5(base_x):
    """Scenario 5 -- Auto-join bridging node.

    Read7 -> Grade6 -> Reformat1 -> Blur5 -> Write5
    Freeze: Grade6, Blur5 (NOT Reformat1 -- it should be auto-joined by _detect_freeze_groups)
    Purpose: test auto-join behavior for non-frozen node between two frozen nodes.
    """
    y = BASE_Y

    read7 = _create_node("Read", "Read7", base_x, y)

    y += Y_SPACING
    grade6 = _create_node("Grade", "Grade6", base_x, y)
    grade6.setInput(0, read7)

    y += Y_SPACING
    reformat1 = _create_node("Reformat", "Reformat1", base_x, y)
    reformat1.setInput(0, grade6)

    y += Y_SPACING
    blur5 = _create_node("Blur", "Blur5", base_x, y)
    blur5.setInput(0, reformat1)

    y += Y_SPACING
    write5 = _create_node("Write", "Write5", base_x, y)
    write5.setInput(0, blur5)

    # Freeze Grade6 and Blur5 (skip Reformat1 -- auto-join should catch it)
    freeze_uuid = str(uuid.uuid4())
    _set_freeze_uuid(grade6, freeze_uuid)
    _set_freeze_uuid(blur5, freeze_uuid)

    print("Scenario 5: Read7 -> Grade6* -> Reformat1 -> Blur5* -> Write5")
    print("  Frozen: Grade6, Blur5 (UUID: {}), Reformat1 should be auto-joined".format(
        freeze_uuid[:8]))
    return {"freeze_uuid": freeze_uuid, "frozen_nodes": ["Grade6", "Blur5"]}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_all_scenarios():
    """Build all 5 freeze test scenarios in the live Nuke DAG."""
    print("=" * 60)
    print("Building Freeze Test Scenarios")
    print("=" * 60)

    x_offset = 0
    x_step = 500

    results = {}

    results["scenario_1"] = build_scenario_1(x_offset)
    x_offset += x_step

    results["scenario_2"] = build_scenario_2(x_offset)
    x_offset += x_step

    results["scenario_3"] = build_scenario_3(x_offset)
    x_offset += x_step

    results["scenario_4"] = build_scenario_4(x_offset)
    x_offset += x_step

    results["scenario_5"] = build_scenario_5(x_offset)

    print("")
    print("=" * 60)
    print("ALL 5 SCENARIOS BUILT SUCCESSFULLY")
    print("=" * 60)
    print("")
    print("Summary:")
    print("  Scenario 1 (X=0):    Basic vertical chain, 2 frozen nodes")
    print("  Scenario 2 (X=500):  Freeze group + side branch, 2 frozen nodes")
    print("  Scenario 3 (X=1000): Two independent freeze groups, 4 frozen nodes")
    print("  Scenario 4 (X=1500): Freeze in middle of long chain, 2 frozen nodes")
    print("  Scenario 5 (X=2000): Auto-join bridging test, 2 frozen + 1 expected auto-join")
    print("")
    print("To test each scenario:")
    print("  1. Select the Write node at the bottom of each scenario")
    print("  2. Run Edit -> Node Layout -> Layout Upstream (Shift+E)")
    print("  3. Observe frozen groups maintain relative positions")
    print("")
    print("Write nodes: Write1, Write2, Write3, Write4, Write5")

    return results


# Run if executed directly
if __name__ == "__main__":
    build_all_scenarios()
