import nuke

_TOOLBAR_FOLDER_MAP = None


def _collect_toolbar_items(menu, top_level_folder_name, folder_map):
    for item in menu.items():
        if isinstance(item, nuke.Menu):
            _collect_toolbar_items(item, top_level_folder_name, folder_map)
        else:
            folder_map[item.name()] = top_level_folder_name


def _build_toolbar_folder_map():
    folder_map = {}
    nodes_menu = nuke.menu('Nodes')
    if nodes_menu is None:
        return folder_map
    for top_level_item in nodes_menu.items():
        if isinstance(top_level_item, nuke.Menu):
            _collect_toolbar_items(top_level_item, top_level_item.name(), folder_map)
    return folder_map


def _get_toolbar_folder_map():
    global _TOOLBAR_FOLDER_MAP
    if _TOOLBAR_FOLDER_MAP is None:
        _TOOLBAR_FOLDER_MAP = _build_toolbar_folder_map()
    return _TOOLBAR_FOLDER_MAP


def same_toolbar_folder(node_a, node_b):
    folder_map = _get_toolbar_folder_map()
    folder_a = folder_map.get(node_a.Class())
    folder_b = folder_map.get(node_b.Class())
    if folder_a is None or folder_b is None:
        return True
    return folder_a == folder_b


SUBTREE_MARGIN = 300  # vertical clearance between adjacent subtrees, and between a dot and the node above it


def get_dag_snap_threshold():
    try:
        return int(nuke.toNode("preferences")["dag_snap_threshold"].value())
    except Exception:
        return 8


def find_node_default_color(node):
    prefs = nuke.toNode("preferences")
    node_colour_slots = [prefs[knob_name].value().split(' ') for knob_name in prefs.knobs() if knob_name.startswith("NodeColourSlot")]
    node_colour_slots = [[item.replace("'", "").lower() for item in parent_item] for parent_item in node_colour_slots]
    node_colour_choices = [prefs[knob_name].value() for knob_name in prefs.knobs() if knob_name.startswith("NodeColourChoice")]
    for i, slot in enumerate(node_colour_slots):
        if node.Class().lower() in slot:
            return node_colour_choices[i]
    return prefs["NodeColor"].value()


def find_node_color(node):
    tile_color = node["tile_color"].value()
    if tile_color == 0:
        tile_color = find_node_default_color(node)
    return tile_color


def same_tile_color(node_a, node_b):
    return find_node_color(node_a) == find_node_color(node_b)


def vertical_gap_between(top_node, bottom_node, snap_threshold):
    if same_tile_color(top_node, bottom_node) and same_toolbar_folder(top_node, bottom_node):
        return snap_threshold - 1
    return 12 * snap_threshold


def _hides_inputs(node):
    knob = node.knob('hide_input')
    return knob is not None and knob.getValue()


def _is_mask_input(node, i):
    try:
        label = node.inputLabel(i).lower()
        if 'mask' in label or 'matte' in label:
            return True
    except Exception:
        pass
    # Fallback for nodes that have a mask channel knob but don't label the input
    if (node.knob('maskChannelInput') or node.knob('maskChannel')) and i == node.inputs() - 1:
        return True
    return False


def get_inputs(node):
    if _hides_inputs(node):
        return []
    return [node.input(i) for i in range(node.inputs()) if node.input(i) is not None]


def insert_dot_nodes(root):
    # Strategy: claim all nodes reachable via non-mask edges first (DFS),
    # deferring every mask edge into a queue. Once the non-mask DFS is fully
    # settled, drain the queue. Any mask edge whose target is already claimed
    # gets a Dot; unclaimed targets are explored the same way (non-mask DFS
    # first, mask edges deferred again). This guarantees non-mask paths always
    # win over mask paths when both reach the same node.
    visited = set()
    deferred = []  # (parent_node, input_slot) for mask connections

    def _claim(node):
        if node is None or _hides_inputs(node) or id(node) in visited:
            return
        visited.add(id(node))
        for slot in range(node.inputs()):
            inp = node.input(slot)
            if inp is None:
                continue
            if _is_mask_input(node, slot):
                deferred.append((node, slot))
            elif id(inp) in visited:
                dot = nuke.nodes.Dot()
                dot.setInput(0, inp)
                dot['hide_input'].setValue(True)
                node.setInput(slot, dot)
            else:
                _claim(inp)

    _claim(root)

    di = 0
    while di < len(deferred):
        parent, slot = deferred[di]
        di += 1
        inp = parent.input(slot)
        if inp is None:
            continue
        if id(inp) in visited:
            dot = nuke.nodes.Dot()
            dot.setInput(0, inp)
            dot['hide_input'].setValue(True)
            parent.setInput(slot, dot)
        else:
            _claim(inp)


def compute_dims(node, memo, snap_threshold):
    if id(node) in memo:
        return memo[id(node)]

    inputs = get_inputs(node)
    if not inputs:
        result = (node.screenWidth(), node.screenHeight())
    else:
        child_dims = [compute_dims(inp, memo, snap_threshold) for inp in inputs]
        n = len(inputs)
        if n == 1:
            W = max(node.screenWidth(), child_dims[0][0])
        elif n == 2:
            # input[0] sits at x (same column as node); input[1] sits at x + node_w + SUBTREE_MARGIN
            W = max(child_dims[0][0], node.screenWidth() + SUBTREE_MARGIN + child_dims[1][0])
        else:
            # n >= 3: input[0] above node (at x); inputs[1..n-1] rightward from node's right edge
            W = max(child_dims[0][0], node.screenWidth() + (n - 1) * SUBTREE_MARGIN + sum(w for w, h in child_dims[1:]))
        # Staircase formula for all n: each input gets its own vertical band.
        # Total height is sum of all child subtree heights plus per-gap values that
        # depend on the tile colors of adjacent nodes.
        gap_to_consumer = vertical_gap_between(inputs[n - 1], node, snap_threshold)
        # When there are side inputs (n > 1), a dot will be inserted for inputs[n-1].
        # Reserve at least SUBTREE_MARGIN so the dot fits without overlapping.
        if n > 1:
            gap_to_consumer = max(gap_to_consumer, SUBTREE_MARGIN)
        inter_band_gaps = (n - 1) * SUBTREE_MARGIN
        H = node.screenHeight() + sum(h for w, h in child_dims) + 2 * gap_to_consumer + inter_band_gaps
        result = (W, H)

    memo[id(node)] = result
    return result


def place_subtree(node, x, y, memo, snap_threshold):
    """
    Place `node` with its top-left corner at (x, y) and recursively position
    every upstream input above it.

    Coordinate system
    -----------------
    Nuke's DAG has positive Y pointing DOWN.  setXpos/setYpos set the node's
    top-left corner.  Inputs (upstream) therefore sit at smaller Y values
    (higher on screen) than the node they feed into.

    Y placement — vertical staircase (backward walk)
    -------------------------------------------------
    Each input receives an exclusive vertical band sized to hold its full
    subtree.  Bands are assigned so that input[n-1] occupies the band
    immediately above the root node (closest to it) and input[0] occupies the
    topmost band (farthest from root).

    Two different gaps are used:
    - node-to-consumer gap: `vertical_gap_between(inputs[n-1], node, snap_threshold)` —
      color-aware; tight when the input and consumer share an explicit tile color, larger
      otherwise.
    - inter-subtree gap: `SUBTREE_MARGIN` (fixed 300 units) — keeps adjacent subtrees
      separated, and also sets the gap between a side-input dot and the node above it.

        bottom_y[n-1] = y - vertical_gap_between(inputs[n-1], node, snap_threshold)
        for i in range(n-2, -1, -1):
            bottom_y[i] = bottom_y[i+1] - child_dims[i+1][1] - SUBTREE_MARGIN

    Within its band each input node is positioned at the band's bottom
    (closest to its consumer):

        y_for_input[i] = bottom_y[i] - inputs[i].screenHeight()

    Because each band's height equals the subtree's full compute_dims height,
    and consecutive bands are separated by SUBTREE_MARGIN, no two subtrees can
    ever overlap in Y.

    X placement
    -----------
    n == 1  : input[0] at x (directly above root, same column).
    n == 2  : input[0] at x (same column as root); input[1] one step right of
              root's right edge.
    n >= 3  : input[0] directly above root (same column); inputs[1..n-1] step
              rightward from root's right edge; input[n-1] rightmost.
    """
    node.setXpos(x)
    node.setYpos(y)

    # Build a list of (actual_slot_index, input_node) pairs so that later
    # setInput calls use the correct slot even when some slots are None.
    if _hides_inputs(node):
        input_slot_pairs = []
    else:
        input_slot_pairs = [
            (slot, node.input(slot))
            for slot in range(node.inputs())
            if node.input(slot) is not None
        ]
    if not input_slot_pairs:
        return

    actual_slots = [slot for slot, _ in input_slot_pairs]
    inputs = [inp for _, inp in input_slot_pairs]
    n = len(inputs)
    child_dims = [compute_dims(inp, memo, snap_threshold) for inp in inputs]

    # --- Y staircase: backward walk so input[n-1] is closest to root ---
    # Mirror the gap enlargement from compute_dims: when n > 1 a dot will be
    # inserted for inputs[n-1], so the gap must be at least SUBTREE_MARGIN.
    gap_closest = vertical_gap_between(inputs[n - 1], node, snap_threshold)
    if n > 1:
        gap_closest = max(gap_closest, SUBTREE_MARGIN)
    bottom_y = [0] * n
    bottom_y[n - 1] = y - gap_closest
    for i in range(n - 2, -1, -1):
        bottom_y[i] = bottom_y[i + 1] - child_dims[i + 1][1] - SUBTREE_MARGIN

    y_positions = [bottom_y[i] - inputs[i].screenHeight() for i in range(n)]

    # --- X positions ---
    if n == 1:
        x_positions = [x]
    elif n == 2:
        # input[0] directly above root; input[1] one step right of root's right edge.
        x_positions = [x, x + node.screenWidth() + SUBTREE_MARGIN]
    else:
        # n >= 3: input[0] directly above root; inputs[1..n-1] step right from root's right edge.
        x_positions = [x]
        current_x = x + node.screenWidth() + SUBTREE_MARGIN
        for i in range(1, n):
            x_positions.append(current_x)
            current_x += child_dims[i][0] + SUBTREE_MARGIN

    # --- Insert Dots for non-primary inputs that are not already Dots ---
    # Deselect all nodes before creating any dot so Nuke cannot auto-connect it.
    for selected_node in nuke.selectedNodes():
        selected_node['selected'].setValue(False)
    for i in range(1, n):
        if inputs[i].Class() != 'Dot':
            dot = nuke.nodes.Dot()
            # Disconnect any auto-connection Nuke may have made, then wire inline.
            for auto_slot in range(dot.inputs()):
                dot.setInput(auto_slot, None)
            dot.setInput(0, inputs[i])
            node.setInput(actual_slots[i], dot)
            inputs[i] = dot

    # --- Recurse ---
    for i, inp in enumerate(inputs):
        if i > 0 and inp.Class() == 'Dot' and not _hides_inputs(inp):
            # Newly inserted side-input dot (hide_input is False).
            # Place the upstream subtree at the staircase position, then
            # position the dot itself separately.
            actual_upstream = inp.input(0)
            place_subtree(actual_upstream, x_positions[i], y_positions[i], memo, snap_threshold)
            dot_center_x = x_positions[i] + actual_upstream.screenWidth() // 2
            if i == n - 1:
                # Bottom-most dot: centre it vertically beside the root node.
                dot_y = y + (node.screenHeight() - inp.screenHeight()) // 2
            else:
                # Staggered dot: SUBTREE_MARGIN below its input node.
                dot_y = y_positions[i] + actual_upstream.screenHeight() + SUBTREE_MARGIN
            inp.setXpos(dot_center_x - inp.screenWidth() // 2)
            inp.setYpos(dot_y)
        else:
            # Regular node, or a dot with hide_input=True (diamond-resolution dot).
            # Use standard placement so diamond dots keep their existing behaviour.
            place_subtree(inp, x_positions[i], y_positions[i], memo, snap_threshold)


def collect_subtree_nodes(root):
    visited_ids = set()
    nodes = []
    def _traverse(node):
        if node is None or id(node) in visited_ids:
            return
        visited_ids.add(id(node))
        nodes.append(node)
        for inp in get_inputs(node):
            _traverse(inp)
    _traverse(root)
    return nodes


def compute_node_bounding_box(nodes):
    if not nodes:
        return None
    min_x = min(n.xpos() for n in nodes)
    min_y = min(n.ypos() for n in nodes)
    max_x = max(n.xpos() + n.screenWidth() for n in nodes)
    max_y = max(n.ypos() + n.screenHeight() for n in nodes)
    return (min_x, min_y, max_x, max_y)


def push_nodes_to_make_room(subtree_node_ids, bbox_before, bbox_after):
    before_min_x, before_min_y, before_max_x, before_max_y = bbox_before
    after_min_x, after_min_y, after_max_x, after_max_y = bbox_after

    grew_up = after_min_y < before_min_y
    grew_right = after_max_x > before_max_x

    if not grew_up and not grew_right:
        return

    push_up_amount = before_min_y - after_min_y if grew_up else 0
    push_right_amount = after_max_x - before_max_x if grew_right else 0

    for node in nuke.allNodes():
        if id(node) in subtree_node_ids:
            continue

        node_left = node.xpos()
        node_right = node.xpos() + node.screenWidth()
        node_top = node.ypos()
        node_bottom = node.ypos() + node.screenHeight()

        # Skip nodes whose bounding box overlaps with the original footprint.
        # Overlap means neither rect is fully to the side/above/below the other.
        overlaps_before = (
            node_left < before_max_x and
            node_right > before_min_x and
            node_top < before_max_y and
            node_bottom > before_min_y
        )
        if overlaps_before:
            continue

        delta_x = 0
        delta_y = 0

        if grew_up and node_bottom <= before_min_y:
            delta_y = -push_up_amount

        if grew_right and node_left >= before_max_x:
            delta_x = push_right_amount

        if delta_x != 0 or delta_y != 0:
            node.setXpos(node.xpos() + delta_x)
            node.setYpos(node.ypos() + delta_y)


def layout_upstream():
    root = nuke.selectedNode()

    # Capture starting state before any changes
    original_subtree_nodes = collect_subtree_nodes(root)
    bbox_before = compute_node_bounding_box(original_subtree_nodes)

    insert_dot_nodes(root)
    memo = {}
    snap_threshold = get_dag_snap_threshold()
    compute_dims(root, memo, snap_threshold)
    place_subtree(root, root.xpos(), root.ypos(), memo, snap_threshold)

    # Capture final state (includes any newly inserted Dot nodes)
    final_subtree_nodes = collect_subtree_nodes(root)
    final_subtree_node_ids = {id(n) for n in final_subtree_nodes}
    bbox_after = compute_node_bounding_box(final_subtree_nodes)

    if bbox_before is not None and bbox_after is not None:
        push_nodes_to_make_room(final_subtree_node_ids, bbox_before, bbox_after)
