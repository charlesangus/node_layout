import nuke
import nukescripts


def sort_by_filename():
    ns = nuke.selectedNodes()

    ns = [n for n in ns if "file" in n.knobs()]

    ns = sorted(ns, key=lambda n: n["file"].value())

    start_location = (min([n.xpos() for n in ns]), min([n.ypos() for n in ns]))

    interval = 300

    for i, n in enumerate(ns):
        n.setXYpos(start_location[0] + interval * i, start_location[1])


def upstream_ignoring_hidden(node, nodes_so_far=None):
    inputs = node.dependencies(what=nuke.INPUTS)
    if len(inputs) == 0:
        return nodes_so_far
    else:
        if nodes_so_far is None:
            nodes_so_far = set(inputs)
        else:
            nodes_so_far.update(set(inputs))
    for input in inputs:
        nodes_so_far.update(upstream_ignoring_hidden(input, nodes_so_far))
    return nodes_so_far


def select_upstream_ignoring_hidden():
    node = nuke.selectedNode()
    ns = upstream_ignoring_hidden(node)
    nukescripts.clear_selection_recursive()
    for n in ns:
        n["selected"].setValue(True)
    node["selected"].setValue(True)


def select_hidden_outputs():
    """Select all immediately downstream nodes connected to any selected node via a hidden input.

    A hidden input means the downstream node has its hide_input knob set to True.
    The original selected nodes remain selected; hidden output nodes are added to the selection.
    """
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return

    selected_ids = {id(n) for n in selected_nodes}

    for candidate in nuke.allNodes():
        hide_input_knob = candidate.knob('hide_input')
        if hide_input_knob is None or not hide_input_knob.getValue():
            continue
        for input_index in range(candidate.inputs()):
            connected_input = candidate.input(input_index)
            if connected_input is not None and id(connected_input) in selected_ids:
                candidate["selected"].setValue(True)
                break

