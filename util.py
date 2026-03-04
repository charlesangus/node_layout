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

