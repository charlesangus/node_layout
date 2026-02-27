import nuke

HORIZ_GAP = 150
VERT_GAP = 150


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


def compute_dims(node, memo):
    if id(node) in memo:
        return memo[id(node)]

    inputs = get_inputs(node)
    if not inputs:
        result = (node.screenWidth(), node.screenHeight())
    else:
        child_dims = [compute_dims(inp, memo) for inp in inputs]
        n = len(inputs)
        if n == 1:
            W = max(node.screenWidth(), child_dims[0][0])
        elif n == 2:
            # input[0] sits at x (same column as node); input[1] sits at x + node_w + HORIZ_GAP
            W = max(child_dims[0][0], node.screenWidth() + HORIZ_GAP + child_dims[1][0])
        else:
            # n >= 3: input[0] above node (at x); inputs[1..n-1] rightward from node's right edge
            W = max(child_dims[0][0], node.screenWidth() + (n - 1) * HORIZ_GAP + sum(w for w, h in child_dims[1:]))
        # Staircase formula for all n: each input gets its own vertical band,
        # so the total height is sum of all child subtree heights plus n gaps.
        H = node.screenHeight() + sum(h for w, h in child_dims) + n * VERT_GAP
        result = (W, H)

    memo[id(node)] = result
    return result


def place_subtree(node, x, y, memo):
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

        bottom_y[n-1] = y - VERT_GAP
        for i in range(n-2, -1, -1):
            bottom_y[i] = bottom_y[i+1] - child_dims[i+1][1] - VERT_GAP

    Within its band each input node is positioned at the band's bottom
    (closest to its consumer):

        y_for_input[i] = bottom_y[i] - inputs[i].screenHeight()

    Because each band's height equals the subtree's full compute_dims height,
    and consecutive bands are separated by VERT_GAP, no two subtrees can ever
    overlap in Y.

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
    child_dims = [compute_dims(inp, memo) for inp in inputs]

    # --- Y staircase: backward walk so input[n-1] is closest to root ---
    bottom_y = [0] * n
    bottom_y[n - 1] = y - VERT_GAP
    for i in range(n - 2, -1, -1):
        bottom_y[i] = bottom_y[i + 1] - child_dims[i + 1][1] - VERT_GAP

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
        place_subtree(inp, x_positions[i], y_positions[i], memo)


def layout_upstream():
    root = nuke.selectedNode()
    insert_dot_nodes(root)
    memo = {}
    compute_dims(root, memo)
    place_subtree(root, root.xpos(), root.ypos(), memo)
