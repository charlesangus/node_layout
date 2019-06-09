import cProfile

class BBox(object):
    def __init__(self, base_node):
        self.base_node = base_node
        self.lower_left = self.node_lower_left(base_node)
        self.upper_right = self.node_upper_right(base_node)
        self.child_nodes = [base_node]
        self.child_bboxes = []
        try:
            hide_input = base_node['hide_input'].getValue()
            if not hide_input:
                for i in range(base_node.inputs()):
                    self.add_child(base_node.input(i))
        except NameError as e:
            pass
        self.update_bounds()

    def __str__(self):
        return "BBox(" + str([self.lower_left, self.upper_right]) + ")"

    def node_lower_left(self, node):
        node_left = node.xpos()
        # because the DAG y axis is flipped, add instead of subtract to get lower left :/
        node_bottom = node.ypos() + node.screenHeight()
        return [node_left, node_bottom]

    def node_upper_right(self, node):
        node_right = node.xpos() + node.screenWidth()
        node_top = node.ypos()
        return [node_right, node_top]

    def width(self):
        return self.upper_right[0] - self.lower_left[0]

    def height(self):
        return self.lower_left[1] - self.upper_right[1]

    def add_child(self, node):
        new_bbox = BBox(node)
        # use max, not min for y, because DAG y-axis is flipped
        # self.lower_left = [min(self.lower_left[0], new_bbox.lower_left[0]),
        #                   max(self.lower_left[1], new_bbox.lower_left[1])]
        # use min, not max for y, because DAG y-axis is flipped
        # self.upper_right = [max(self.upper_right[0], new_bbox.upper_right[0]),
        #                     min(self.upper_right[1], new_bbox.upper_right[1])]
        # self.child_nodes.append(node)
        # self.child_nodes = self.child_nodes + new_bbox.child_nodes
        self.child_bboxes.append(new_bbox)
        # self.child_bboxes.sort(key=lambda x: x.lower_left[0])

    def update_bounds(self):
        original_bounds = (self.lower_left, self.upper_right)
        self.lower_left = self.node_lower_left(self.child_nodes[0])
        self.upper_right = self.node_upper_right(self.child_nodes[0])
        for node in self.get_nodes_recursively():
            self.lower_left = [min(self.lower_left[0], self.node_lower_left(node)[0]),
                               max(self.lower_left[1], self.node_lower_left(node)[1])]
            self.upper_right = [max(self.upper_right[0], self.node_upper_right(node)[0]),
                                min(self.upper_right[1], self.node_upper_right(node)[1])]
        for bbox in self.child_bboxes:
            bbox.update_bounds()

    def get_nodes_recursively(self):
        nodes = [node for node in self.child_nodes]
        for b in self.child_bboxes:
            nodes = nodes + get_nodes_recursively(b)
        return nodes

def get_nodes_recursively(bbox):
    nodes = [node for node in bbox.child_nodes]
    for b in bbox.child_bboxes:
       nodes = nodes + get_nodes_recursively(b)
    return nodes

def walk_bboxes_recursively(bbox, increment=0):
    r = 1 / float(increment + 1) * .25
    g = 0.18
    b = (1 - (1 / float(increment + 1))) * .25
    border = 150 * (1 - increment *.2)
    hexColour = int('%02x%02x%02x%02x' % (r*255,g*255,b*255,1),16)
    n = nuke.nodes.BackdropNode(xpos = bbox.lower_left[0] - border,
                                        bdwidth = bbox.upper_right[0] - bbox.lower_left[0] + border * 2,
                                        ypos = bbox.upper_right[1] - border,
                                        bdheight = bbox.lower_left[1] - bbox.upper_right[1] + border * 2,
                                        tile_color = hexColour,
                                        label = bbox.child_nodes[0].name(),
                                        z_order = increment)
    for b in bbox.child_bboxes:
        walk_bboxes_recursively(b, increment + 1)


def build_dict_recursively(base_bbox):
    children = {bbox.child_nodes[0].name(): build_dict_recursively(bbox) for bbox in base_bbox.child_bboxes}
    return children

def layout_children_recursively(base_bbox, increment=0, orig_base=None):
    horizontal_offset = 150
    vertical_offset = -150
    base_bbox.update_bounds()
    for i, child_bbox  in enumerate(base_bbox.child_bboxes):
        if i == 0:
            all_child_nodes = child_bbox.get_nodes_recursively()
            offset_to_apply = [base_bbox.node_lower_left(base_bbox.child_nodes[0])[0] - child_bbox.node_lower_left(child_bbox.child_nodes[0])[0], base_bbox.node_lower_left(base_bbox.child_nodes[0])[1] - child_bbox.node_lower_left(child_bbox.child_nodes[0])[1] + vertical_offset]
            for node in all_child_nodes:
                node.setXpos(node.xpos() + offset_to_apply[0])
                node.setYpos(node.ypos() + offset_to_apply[1])
            layout_children_recursively(child_bbox, increment + 1, orig_base=orig_base)
            child_bbox.update_bounds()
        else:
            all_child_nodes = child_bbox.get_nodes_recursively()
            offset_to_apply = [base_bbox.node_lower_left(base_bbox.child_nodes[0])[0] - child_bbox.node_lower_left(child_bbox.child_nodes[0])[0] + base_bbox.child_bboxes[i - 1].width() + horizontal_offset, base_bbox.node_lower_left(base_bbox.child_nodes[0])[1] - child_bbox.node_lower_left(child_bbox.child_nodes[0])[1] + vertical_offset]
            for node in all_child_nodes:
                node.setXpos(node.xpos() + offset_to_apply[0])
                node.setYpos(node.ypos() + offset_to_apply[1])
            layout_children_recursively(child_bbox, increment + 1, orig_base=orig_base)
    base_bbox.update_bounds()

cProfile.run("""base_bbox = BBox(nuke.selectedNode())
layout_children_recursively(base_bbox,orig_base=base_bbox)
walk_bboxes_recursively(base_bbox)""")

base_bbox = BBox(nuke.selectedNode())
layout_children_recursively(base_bbox,orig_base=base_bbox)
walk_bboxes_recursively(base_bbox)
