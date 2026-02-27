import nuke

HORIZ_GAP = 150

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


SUBTREE_GAP = 300  # vertical clearance between adjacent subtrees (bottom of one to top of next)


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
            # input[0] sits at x (same column as node); input[1] sits at x + node_w + HORIZ_GAP
            W = max(child_dims[0][0], node.screenWidth() + HORIZ_GAP + child_dims[1][0])
        else:
            # n >= 3: input[0] above node (at x); inputs[1..n-1] rightward from node's right edge
            W = max(child_dims[0][0], node.screenWidth() + (n - 1) * HORIZ_GAP + sum(w for w, h in child_dims[1:]))
        # Staircase formula for all n: each input gets its own vertical band.
        # Total height is sum of all child subtree heights plus per-gap values that
        # depend on the tile colors of adjacent nodes.
        gap_to_consumer = vertical_gap_between(inputs[n - 1], node, snap_threshold)
        inter_band_gaps = (n - 1) * SUBTREE_GAP
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
    - inter-subtree gap: `SUBTREE_GAP` (fixed 300 units) — keeps adjacent subtrees well
      separated regardless of color.

        bottom_y[n-1] = y - vertical_gap_between(inputs[n-1], node, snap_threshold)
        for i in range(n-2, -1, -1):
            bottom_y[i] = bottom_y[i+1] - child_dims[i+1][1] - SUBTREE_GAP

    Within its band each input node is positioned at the band's bottom
    (closest to its consumer):

        y_for_input[i] = bottom_y[i] - inputs[i].screenHeight()

    Because each band's height equals the subtree's full compute_dims height,
    and consecutive bands are separated by SUBTREE_GAP, no two subtrees can
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

    inputs = get_inputs(node)
    if not inputs:
        return

    n = len(inputs)
    child_dims = [compute_dims(inp, memo, snap_threshold) for inp in inputs]

    # --- Y staircase: backward walk so input[n-1] is closest to root ---
    bottom_y = [0] * n
    bottom_y[n - 1] = y - vertical_gap_between(inputs[n - 1], node, snap_threshold)
    for i in range(n - 2, -1, -1):
        bottom_y[i] = bottom_y[i + 1] - child_dims[i + 1][1] - SUBTREE_GAP

    y_positions = [bottom_y[i] - inputs[i].screenHeight() for i in range(n)]

    # --- X positions ---
    if n == 1:
        x_positions = [x]
    elif n == 2:
        # input[0] directly above root; input[1] one step right of root's right edge.
        x_positions = [x, x + node.screenWidth() + HORIZ_GAP]
    else:
        # n >= 3: input[0] directly above root; inputs[1..n-1] step right from root's right edge.
        x_positions = [x]
        current_x = x + node.screenWidth() + HORIZ_GAP
        for i in range(1, n):
            x_positions.append(current_x)
            current_x += child_dims[i][0] + HORIZ_GAP

    # --- Recurse ---
    for i, inp in enumerate(inputs):
        place_subtree(inp, x_positions[i], y_positions[i], memo, snap_threshold)


def layout_upstream():
    root = nuke.selectedNode()
    insert_dot_nodes(root)
    memo = {}
    snap_threshold = get_dag_snap_threshold()
    compute_dims(root, memo, snap_threshold)
    place_subtree(root, root.xpos(), root.ypos(), memo, snap_threshold)
