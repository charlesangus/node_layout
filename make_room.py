import nuke
import nukescripts


def make_room(amount=1600, direction="up"):
    nodes_to_move = nuke.selectedNodes()

    if direction == "up":
        x_amount = 0
        y_amount = -amount
    elif direction == "down":
        y_amount = amount
        x_amount = 0

    if direction == "left":
        y_amount = 0
        x_amount = -amount
    elif direction == "right":
        y_amount = 0
        x_amount = amount

    # override nodes to move if no selection
    if len(nodes_to_move) == 0:
        nukescripts.clear_selection_recursive()

        n = nuke.createNode("Dot", inpanel=False)
        y = n.ypos()
        nuke.delete(n)

        if direction == "up":
            nodes_to_move = [node for node in nuke.allNodes() if node.ypos() < y]
        elif direction == "down":
            nodes_to_move = [node for node in nuke.allNodes() if node.ypos() > y]
        elif direction in ("left", "right"):
            nodes_to_move = []


    for node in nodes_to_move:
        node.setXpos(node.xpos() + x_amount)
        node.setYpos(node.ypos() + y_amount)

