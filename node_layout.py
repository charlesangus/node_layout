import math
import uuid

import nuke

import node_layout_prefs
import node_layout_state

_TOOLBAR_FOLDER_MAP = None

_COLOR_LOOKUP_CACHE = {}  # node.Class() -> color value; valid for one layout operation only

_OUTPUT_DOT_KNOB_NAME = "node_layout_output_dot"
_LEFTMOST_DOT_KNOB_NAME = "node_layout_leftmost_dot"


def _clear_color_cache():
    global _COLOR_LOOKUP_CACHE
    _COLOR_LOOKUP_CACHE = {}


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


def get_dag_snap_threshold():
    try:
        return int(nuke.toNode("preferences")["dag_snap_threshold"].value())
    except (KeyError, AttributeError):
        return 8


def find_node_default_color(node):
    node_class = node.Class()
    if node_class in _COLOR_LOOKUP_CACHE:
        return _COLOR_LOOKUP_CACHE[node_class]
    prefs = nuke.toNode("preferences")
    node_colour_slots = [
        prefs[knob_name].value().split(' ')
        for knob_name in prefs.knobs()
        if knob_name.startswith("NodeColourSlot")
    ]
    node_colour_slots = [
        [item.replace("'", "").lower() for item in parent_item]
        for parent_item in node_colour_slots
    ]
    node_colour_choices = [
        prefs[knob_name].value()
        for knob_name in prefs.knobs()
        if knob_name.startswith("NodeColourChoice")
    ]
    for i, slot in enumerate(node_colour_slots):
        if node_class.lower() in slot:
            result = node_colour_choices[i]
            _COLOR_LOOKUP_CACHE[node_class] = result
            return result
    result = prefs["NodeColor"].value()
    _COLOR_LOOKUP_CACHE[node_class] = result
    return result


def find_node_color(node):
    tile_color = node["tile_color"].value()
    if tile_color == 0:
        tile_color = find_node_default_color(node)
    return tile_color


def same_tile_color(node_a, node_b):
    return find_node_color(node_a) == find_node_color(node_b)


def vertical_gap_between(top_node, bottom_node, snap_threshold, scheme_multiplier=None):
    if same_tile_color(top_node, bottom_node) and same_toolbar_folder(top_node, bottom_node):
        return snap_threshold - 1
    if scheme_multiplier is None:
        scheme_multiplier = node_layout_prefs.prefs_singleton.get("normal_multiplier")
    loose_gap_multiplier = node_layout_prefs.prefs_singleton.get("loose_gap_multiplier")
    return int(loose_gap_multiplier * scheme_multiplier * snap_threshold)


def _hides_inputs(node):
    knob = node.knob('hide_input')
    return knob is not None and knob.getValue()


_MERGE_LIKE_CLASSES = frozenset({'Merge2', 'Dissolve'})


def _is_mask_input(node, i):
    if node.Class() in _MERGE_LIKE_CLASSES:
        return i == 2  # input 0=B, 1=A, 2=M (mask), 3+=A1/A2...
    try:
        label = node.inputLabel(i).lower()
        if 'mask' in label or 'matte' in label:
            return True
    except (KeyError, AttributeError):
        pass
    # Fallback for nodes that have a mask channel knob but don't label the input
    return (
        (node.knob('maskChannelInput') or node.knob('maskChannel'))
        and i == node.inputs() - 1
    )


def _dot_font_scale(node, slot):
    """Return the font multiplier for the labeled-Dot walk from node.input(slot).

    Walks consecutive Dot nodes upstream from the given slot.  Returns the font
    multiplier for the first Dot that has a non-empty label.  Returns 1.0 if no
    labeled Dot is found before the chain ends.

    Formula: min(max(font_size / reference_size, 1.0), 4.0)
    Floor at 1.0 — small fonts never shrink margins.
    Cap at 4.0 — very large fonts produce at most 4x margin.
    """
    current_prefs = node_layout_prefs.prefs_singleton
    reference_size = current_prefs.get("dot_font_reference_size")
    candidate = node.input(slot)
    while candidate is not None and candidate.Class() == 'Dot':
        try:
            label = str(candidate['label'].value())
        except (KeyError, AttributeError):
            label = ''
        if label.strip():
            try:
                font_size = int(candidate['note_font_size'].value())
            except (KeyError, AttributeError, ValueError):
                font_size = reference_size
            return min(max(font_size / reference_size, 1.0), 4.0)
        candidate = candidate.input(0)
    return 1.0


def _subtree_margin(node, slot, node_count, mode_multiplier=None):
    current_prefs = node_layout_prefs.prefs_singleton
    base = current_prefs.get("base_subtree_margin")
    if mode_multiplier is None:
        mode_multiplier = current_prefs.get("normal_multiplier")
    reference_count = current_prefs.get("scaling_reference_count")
    font_mult = _dot_font_scale(node, slot)
    effective_margin = int(
        base * mode_multiplier * math.sqrt(node_count)
        / math.sqrt(reference_count) * font_mult
    )
    if _is_mask_input(node, slot):
        ratio = current_prefs.get("mask_input_ratio")
        return int(effective_margin * ratio)
    return effective_margin


def _horizontal_margin(node, slot):
    """Return the horizontal gap (px) for the given input slot.

    H-axis margins are absolute pixel values from prefs — no sqrt scaling.
    Vertical margins still use _subtree_margin() with its sqrt formula.
    """
    current_prefs = node_layout_prefs.prefs_singleton
    font_mult = _dot_font_scale(node, slot)
    if _is_mask_input(node, slot):
        return int(current_prefs.get("horizontal_mask_gap") * font_mult)
    return int(current_prefs.get("horizontal_subtree_gap") * font_mult)


def _center_x(child_width, parent_x, parent_width):
    """Return the xpos that centers a child tile over a parent tile."""
    return parent_x + (parent_width - child_width) // 2


def _is_fan_active(input_slot_pairs, node):
    """Return True when 3+ non-mask inputs are present (fan mode trigger).

    Fan mode activates at 3+ non-mask inputs.  A standard Merge2 (B + A = 2
    non-mask inputs) is NOT affected — staircase behaviour is preserved.
    """
    non_mask_count = sum(
        1 for slot, _ in input_slot_pairs if not _is_mask_input(node, slot)
    )
    return non_mask_count >= 3


def _reorder_inputs_mask_last(input_slot_pairs, node, all_side, fan_active=False):
    """Move mask side inputs to the end so they appear rightmost when n > 2.

    In normal mode (not all_side), input[0] is the primary (above), so only the
    side inputs (index 1+) are reordered.  In all_side mode, every input is a
    side input, so the whole list is reordered.  When n <= 2 there is at most one
    side input so ordering is moot.

    When fan_active=True, mask inputs are moved to the FRONT (leftmost placement)
    so that place_subtree can position them to the left of the consumer.  Relative
    order within each group (mask vs non-mask) is preserved.
    """
    if fan_active and len(input_slot_pairs) > 2:
        # Fan mode: mask goes to the FRONT (leftmost placement).
        # Preserves relative order within mask and non-mask groups.
        if all_side:
            mask_inputs = [
                (slot, inp) for slot, inp in input_slot_pairs
                if _is_mask_input(node, slot)
            ]
            non_mask = [
                (slot, inp) for slot, inp in input_slot_pairs
                if not _is_mask_input(node, slot)
            ]
        else:
            primary = input_slot_pairs[:1]
            side = input_slot_pairs[1:]
            side_non_mask = [(slot, inp) for slot, inp in side if not _is_mask_input(node, slot)]
            side_mask = [(slot, inp) for slot, inp in side if _is_mask_input(node, slot)]
            mask_inputs = side_mask
            non_mask = primary + side_non_mask
        return mask_inputs + non_mask

    if len(input_slot_pairs) <= 2:
        return input_slot_pairs
    if all_side:
        non_mask = [(slot, inp) for slot, inp in input_slot_pairs if not _is_mask_input(node, slot)]
        mask_inputs = [(slot, inp) for slot, inp in input_slot_pairs if _is_mask_input(node, slot)]
        return non_mask + mask_inputs
    primary = input_slot_pairs[:1]
    side = input_slot_pairs[1:]
    side_non_mask = [(slot, inp) for slot, inp in side if not _is_mask_input(node, slot)]
    side_mask = [(slot, inp) for slot, inp in side if _is_mask_input(node, slot)]
    return primary + side_non_mask + side_mask


def _get_input_slot_pairs(node, node_filter=None):
    """Return (slot, input_node) pairs for connected, non-hidden inputs.

    Applies node_filter when provided. Slot indices are preserved so callers
    can query per-slot properties (e.g. mask vs primary) via the slot number.
    """
    if _hides_inputs(node):
        return []
    pairs = [(i, node.input(i)) for i in range(node.inputs()) if node.input(i) is not None]
    if node_filter is not None:
        pairs = [(slot, inp) for slot, inp in pairs if _passes_node_filter(inp, node_filter)]
    return pairs


def get_inputs(node):
    if _hides_inputs(node):
        return []
    return [node.input(i) for i in range(node.inputs()) if node.input(i) is not None]


def _passes_node_filter(node, node_filter):
    """Return True if node should be included given node_filter.

    Always returns True when node_filter is None.
    Returns True for nodes explicitly in the filter.
    Also returns True for diamond-resolution Dot nodes (hide_input=True) whose
    wrapped input is in the filter — these are created by insert_dot_nodes and
    must be traversed even though they are not in the original filter set.
    """
    if node_filter is None:
        return True
    if node in node_filter:
        return True
    return (
        node.Class() == 'Dot'
        and node.knob('node_layout_diamond_dot') is not None
        and node.input(0) is not None
        and node.input(0) in node_filter
    )


def _primary_slot_externally_occupied(node, node_filter):
    """Return True when slot 0 is connected to a node outside node_filter.

    When True, the 'directly above' position for this node is already taken by
    an external connection, so all in-filter inputs must be placed as side inputs.
    """
    if node_filter is None:
        return False
    primary_input = node.input(0)
    if primary_input is None:
        return False
    return not _passes_node_filter(primary_input, node_filter)


def insert_dot_nodes(root, node_filter=None):
    # Strategy: claim all nodes reachable via non-mask edges first (DFS),
    # deferring every mask edge into a queue. Once the non-mask DFS is fully
    # settled, drain the queue. Any mask edge whose target is already claimed
    # gets a Dot; unclaimed targets are explored the same way (non-mask DFS
    # first, mask edges deferred again). This guarantees non-mask paths always
    # win over mask paths when both reach the same node.
    #
    # When node_filter is provided, traversal stops at nodes outside the filter.
    visited = set()
    deferred = []  # (parent_node, input_slot) for mask connections

    def _claim(node):
        if node is None or _hides_inputs(node) or id(node) in visited:
            return
        if node_filter is not None and node not in node_filter:
            return
        visited.add(id(node))
        for slot in range(node.inputs()):
            inp = node.input(slot)
            if inp is None:
                continue
            if node_filter is not None and inp not in node_filter:
                continue
            if _is_mask_input(node, slot):
                deferred.append((node, slot))
            elif id(inp) in visited:
                dot = nuke.nodes.Dot()
                dot.addKnob(nuke.Tab_Knob('node_layout_tab', 'Node Layout'))
                dot.addKnob(nuke.Int_Knob('node_layout_diamond_dot', 'Diamond Dot Marker'))
                dot['node_layout_diamond_dot'].setValue(1)
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
        if node_filter is not None and inp not in node_filter:
            continue
        if id(inp) in visited:
            dot = nuke.nodes.Dot()
            dot.addKnob(nuke.Tab_Knob('node_layout_tab', 'Node Layout'))
            dot.addKnob(nuke.Int_Knob('node_layout_diamond_dot', 'Diamond Dot Marker'))
            dot['node_layout_diamond_dot'].setValue(1)
            dot.setInput(0, inp)
            dot['hide_input'].setValue(True)
            parent.setInput(slot, dot)
        else:
            _claim(inp)


def _find_or_create_output_dot(root, consumer_node, consumer_slot, current_group,
                               snap_threshold=None, scheme_multiplier=None):
    """Place a routing Dot below root, wired between root and consumer_node.

    On replay (second call with same root and consumer), the existing Dot is
    detected via its node_layout_output_dot knob and returned as-is — no
    duplicate is created.

    If consumer_node is None, returns None without creating a Dot.

    Args:
        root: The root node of the horizontal subtree.
        consumer_node: The downstream node that consumes root's output.
        consumer_slot: The input slot index on consumer_node wired to root.
        current_group: The current Nuke group context (or None for root context).
        snap_threshold: DAG snap threshold in pixels; defaults to 8 if None.
        scheme_multiplier: Layout scheme multiplier; resolved from prefs if None.
    """
    if consumer_node is None:
        return None

    if snap_threshold is None:
        snap_threshold = 8
    if scheme_multiplier is None:
        scheme_multiplier = node_layout_prefs.prefs_singleton.get("normal_multiplier")

    # Compute dot gap: always use loose gap so the dot is clearly below root and not
    # collapsed to a near-zero gap by the same-tile-color compact rule.
    loose_gap_multiplier = node_layout_prefs.prefs_singleton.get("loose_gap_multiplier")
    dot_gap = int(loose_gap_multiplier * scheme_multiplier * snap_threshold)

    # Reuse check: if what is currently wired at consumer_slot is already an
    # output Dot (has node_layout_output_dot knob), reposition it and return it.
    currently_wired = consumer_node.input(consumer_slot)
    if (currently_wired is not None
            and currently_wired.knob(_OUTPUT_DOT_KNOB_NAME) is not None):
        dot = currently_wired
        dot_x = root.xpos() + (root.screenWidth() - dot.screenWidth()) // 2
        if consumer_node is not None:
            dot_y = consumer_node.ypos() + (consumer_node.screenHeight() - dot.screenHeight()) // 2
        else:
            dot_y = root.ypos() + root.screenHeight() + dot_gap
        dot.setXpos(dot_x)
        dot.setYpos(dot_y)
        return dot

    # Deselect all nodes before creating the Dot (anti-auto-connect guard).
    for selected_node in nuke.selectedNodes():
        selected_node['selected'].setValue(False)

    dot = nuke.nodes.Dot()
    dot.addKnob(nuke.Tab_Knob('node_layout_tab', 'Node Layout'))
    dot.addKnob(nuke.Int_Knob(_OUTPUT_DOT_KNOB_NAME, 'Output Dot Marker'))
    dot[_OUTPUT_DOT_KNOB_NAME].setValue(1)
    dot.setInput(0, root)
    consumer_node.setInput(consumer_slot, dot)

    # Position the Dot: centred horizontally on root, Y aligned to consumer when present.
    # When a downstream consumer exists, the dot sits at the consumer's Y level so the
    # wire from consumer to dot is strictly horizontal (positive Y is down in Nuke DAG).
    # When no consumer is known (standalone chain), place below root at loose gap.
    dot_x = root.xpos() + (root.screenWidth() - dot.screenWidth()) // 2
    if consumer_node is not None:
        dot_y = consumer_node.ypos() + (consumer_node.screenHeight() - dot.screenHeight()) // 2
    else:
        dot_y = root.ypos() + root.screenHeight() + dot_gap
    dot.setXpos(dot_x)
    dot.setYpos(dot_y)

    return dot


def _place_output_dot_for_horizontal_root(
    root, current_group, snap_threshold=None, scheme_multiplier=None
):
    """Place or reposition an output Dot below the horizontal section root.

    Finds root's downstream consumer (a non-output-dot node whose direct input is
    root) and inserts a routing Dot between them. If root has no downstream consumer,
    no Dot is created.

    On replay, if an existing output Dot (node_layout_output_dot) already has root as
    its input, that Dot is repositioned below root's new coordinates rather than
    duplicated.

    Args:
        root: The rightmost node of the horizontal spine.
        current_group: Current Nuke group context (or None for root context).
        snap_threshold: DAG snap threshold in pixels; defaults to 8 if None.
        scheme_multiplier: Layout scheme multiplier; resolved from prefs if None.
    """
    if snap_threshold is None:
        snap_threshold = 8
    if scheme_multiplier is None:
        scheme_multiplier = node_layout_prefs.prefs_singleton.get("normal_multiplier")

    if current_group is not None:
        with current_group:
            all_nodes = nuke.allNodes()
    else:
        all_nodes = nuke.allNodes()

    # Scan nodes to find either an existing output dot (for repositioning on replay)
    # or a real downstream consumer (for creating a new dot on first run).
    existing_dot = None
    consumer_node = None
    consumer_slot = None
    for node in all_nodes:
        if node.knob(_OUTPUT_DOT_KNOB_NAME) is not None:
            # Output dot we previously created — check if it takes root as its input.
            if node.input(0) is not None and id(node.input(0)) == id(root) and existing_dot is None:
                existing_dot = node
        elif consumer_node is None:
            for slot in range(node.inputs()):
                if node.input(slot) is not None and id(node.input(slot)) == id(root):
                    consumer_node = node
                    consumer_slot = slot
                    break

    # On replay, m1 is wired to the existing dot (not to root directly): m1 → dot → root.
    # The first scan above finds existing_dot but misses consumer_node because no node has
    # root as its input.  Do a second pass looking for a non-dot node wired to the dot.
    if existing_dot is not None and consumer_node is None:
        for node in all_nodes:
            if consumer_node is not None:
                break
            if node.knob(_OUTPUT_DOT_KNOB_NAME) is None:
                for slot in range(node.inputs()):
                    if node.input(slot) is not None and id(node.input(slot)) == id(existing_dot):
                        consumer_node = node
                        consumer_slot = slot
                        break

    if existing_dot is not None:
        # Reposition the existing dot: X centred on root, Y centred on the consumer.
        # The consumer is found either via direct connection to root (first run) or via
        # connection to the dot itself (replay, after the second scan above).
        existing_dot.setXpos(root.xpos() + (root.screenWidth() - existing_dot.screenWidth()) // 2)
        if consumer_node is not None:
            existing_dot.setYpos(
                consumer_node.ypos()
                + (consumer_node.screenHeight() - existing_dot.screenHeight()) // 2
            )
        else:
            loose_gap_multiplier = node_layout_prefs.prefs_singleton.get("loose_gap_multiplier")
            dot_gap = int(loose_gap_multiplier * scheme_multiplier * snap_threshold)
            existing_dot.setYpos(root.ypos() + root.screenHeight() + dot_gap)
        return existing_dot

    if consumer_node is None:
        return None  # Root is the final output — no dot needed.

    return _find_or_create_output_dot(
        root, consumer_node, consumer_slot, current_group,
        snap_threshold=snap_threshold,
        scheme_multiplier=scheme_multiplier,
    )


def _find_or_create_leftmost_dot(leftmost_spine_node, current_group):
    """Insert a routing Dot between leftmost_spine_node and its input[0].

    The Dot is wired: upstream_root → Dot → leftmost_spine_node.  It enables
    correct wire routing when the upstream subtree is placed above-left of the
    spine: the wire drops vertically from the upstream root to the Dot (at spine
    Y), then runs horizontally to the leftmost spine node's input.

    Positioning of the Dot is handled by the caller (place_subtree_horizontal).
    On replay the existing Dot is detected via its node_layout_leftmost_dot knob
    and returned without creating a duplicate.

    Returns the Dot, or None if leftmost_spine_node has no input[0].
    """
    upstream = leftmost_spine_node.input(0)
    if upstream is None:
        return None

    # Reuse check: if input[0] is already a leftmost Dot, return it.
    if upstream.knob(_LEFTMOST_DOT_KNOB_NAME) is not None:
        return upstream

    for selected_node in nuke.selectedNodes():
        selected_node['selected'].setValue(False)

    with current_group:
        dot = nuke.nodes.Dot()
        dot.addKnob(nuke.Tab_Knob('node_layout_tab', 'Node Layout'))
        dot.addKnob(nuke.Int_Knob(_LEFTMOST_DOT_KNOB_NAME, 'Leftmost Dot Marker'))
        dot[_LEFTMOST_DOT_KNOB_NAME].setValue(1)
        dot.setInput(0, upstream)
        leftmost_spine_node.setInput(0, dot)

    return dot


def _find_freeze_block_through_dots(node, dimension_overrides):
    """Traverse through Dot nodes to find a freeze block root in *dimension_overrides*.

    On replay, layout inserts Dot routing nodes between spine nodes and their
    side-input subtrees.  The freeze block root is then one or more Dot hops
    away from the spine, so ``id(side_node) in dimension_overrides`` fails.
    This helper walks through consecutive Dot nodes until it finds a node that
    IS a freeze block root, or runs out of Dots.

    Returns the FreezeBlock if found, else None.
    """
    if not dimension_overrides:
        return None
    cursor = node
    while cursor is not None and cursor.Class() == "Dot":
        cursor = cursor.input(0)
    if cursor is not None and id(cursor) in dimension_overrides:
        return dimension_overrides[id(cursor)]
    return None


def place_subtree_horizontal(root, spine_x, spine_y, snap_threshold, node_count,
                             scheme_multiplier=None, per_node_h_scale=None,
                             per_node_v_scale=None, current_prefs=None,
                             current_group=None, memo=None,
                             spine_set=None, side_layout_mode="place_only",
                             dimension_overrides=None):
    """Lay out a B-spine subtree horizontally.

    Root is placed at (spine_x, spine_y). Each input[0] ancestor that belongs to
    the spine is placed one step to the left.

    Spine membership is controlled by spine_set: if provided (a set of node id()
    values), only nodes whose id() is in spine_set are included. The spine walk
    stops at the first input[0] that is not in spine_set. If spine_set is None,
    all input[0] ancestors are included (original behaviour).

    Side inputs are all inputs[1+] of any spine node, plus input[0] of the
    farthest spine node when that node is not a member of the spine.

    side_layout_mode controls how side inputs are handled:
    - "place_only": position the side input root node only (no recursive layout).
    - "recursive": call place_subtree() on each side input root to lay out its
      full upstream subtree vertically above the spine node.

    Mask kink: when a spine node has a mask input, all spine nodes closer to root
    (downstream, i.e. lower index in the spine list) drop by the mask subtree height
    to clear the mask subtree above that spine node. Kink applies regardless of
    side_layout_mode.

    Coordinate system: positive X is right; positive Y is down (Nuke DAG).

    Args:
        root: Rightmost node in the spine.
        spine_x: X position for the root node.
        spine_y: Baseline Y position for the spine (before any kink adjustment).
        snap_threshold: DAG snap threshold in pixels.
        node_count: Total node count for margin scaling formulas.
        scheme_multiplier: Layout scheme multiplier; resolved from prefs if None.
        per_node_h_scale: Per-node horizontal scale dict {id(node): float}, or None.
        per_node_v_scale: Per-node vertical scale dict {id(node): float}, or None.
        current_prefs: Prefs singleton override; uses prefs_singleton if None.
        current_group: Current Nuke group context, or None for root context.
        memo: Shared compute_dims memo dict; created locally if None.
        spine_set: Set of node id() values that form the spine, or None for all input[0].
        side_layout_mode: "place_only" to reposition side input root only, or
            "recursive" to recursively lay out each side input subtree vertically.
    """
    current_prefs = current_prefs or node_layout_prefs.prefs_singleton
    if scheme_multiplier is None:
        scheme_multiplier = current_prefs.get("normal_multiplier")
    if memo is None:
        memo = {}

    # Step between spine nodes: gap + the upstream node's own width.
    # Applied incrementally: after placing spine[i], the next node to the left
    # starts at cur_x - step_x - upstream_node.screenWidth().
    step_x = int(current_prefs.get("horizontal_subtree_gap") * scheme_multiplier)
    # Fixed vertical gap between spine and first node of each side subtree.
    horizontal_side_gap = current_prefs.get("horizontal_side_vertical_gap")

    # Build the spine list: [root, ancestor1, ancestor2, ...]
    # root is index 0 (rightmost); last element is farthest spine ancestor (leftmost).
    # When spine_set is provided, stop at the first input[0] not in spine_set.
    spine_nodes = []
    cursor = root
    while cursor is not None:
        if spine_set is not None and id(cursor) not in spine_set:
            break
        spine_nodes.append(cursor)
        cursor = cursor.input(0)

    # --- Pre-pass: compute side input dims and effective widths for width-aware spacing.
    # effective_widths[i] = total horizontal extent rightward from spine_node[i]'s left
    # edge, including all side subtrees placed above it (slots 1+).
    # left_extents[i] = how far side subtrees of spine_node[i] extend LEFTWARD past its
    # own left edge (only non-zero when a side subtree root is wider than the spine node).
    # Both arrays are used in the advance formula to ensure a full step_x gap between
    # the bounding boxes of adjacent spine nodes' side subtrees.
    # For "recursive" mode, we compute full subtree dims. For "place_only" we just
    # use the single node width (side inputs are translated as units, not re-laid-out).
    # input[0] of the last spine node is handled separately (placed above via a Dot)
    # and is NOT included in effective_widths or left_extents.
    side_input_counts = {}  # (id(spine_node), slot_index) -> side_node_count
    effective_widths = [sn.screenWidth() for sn in spine_nodes]
    left_extents = [0] * len(spine_nodes)

    # When a spine node IS a freeze block root, expand its effective width and left
    # extent to cover the full block bounding box.  Without this, the advance formula
    # only reserves space for the root node's own screenWidth(), and the non-root
    # block members (restored via offset after placement) overlap the adjacent spine
    # node's side subtrees.
    if dimension_overrides:
        for i, spine_node in enumerate(spine_nodes):
            if id(spine_node) in dimension_overrides:
                block = dimension_overrides[id(spine_node)]
                effective_widths[i] = max(effective_widths[i], block.right_extent)
                left_extents[i] = max(left_extents[i], block.left_overhang)

    if side_layout_mode == "recursive":
        for i, spine_node in enumerate(spine_nodes):
            for slot_index in range(1, spine_node.inputs()):
                side_node = spine_node.input(slot_index)
                if side_node is None:
                    continue
                side_count = len(collect_subtree_nodes(side_node))
                side_input_counts[(id(spine_node), slot_index)] = side_count
                side_w, _, side_root_x_offset = compute_dims(
                    side_node, memo, snap_threshold, side_count,
                    scheme_multiplier=scheme_multiplier,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                    dimension_overrides=dimension_overrides,
                )
                # When the side input is (or routes through Dots to) a freeze
                # block root, the block's restored bounding box is typically
                # wider than what compute_dims returns (which treats frozen
                # members as a normal vertical chain).  Override side_w and
                # side_root_x_offset with the block's true dimensions so the
                # advance formula reserves enough horizontal space.
                side_freeze_block = _find_freeze_block_through_dots(
                    side_node, dimension_overrides
                )
                if side_freeze_block is not None:
                    freeze_block_total_width = (
                        side_freeze_block.right_extent
                        + side_freeze_block.left_overhang
                    )
                    if freeze_block_total_width > side_w:
                        side_w = freeze_block_total_width
                        side_root_x_offset = side_freeze_block.left_overhang
                # centering_offset: displacement from spine node's left edge to side
                # node's left edge.  Negative when side node is wider than spine node
                # (side subtree extends leftward past the spine node's left edge).
                centering_offset = (spine_node.screenWidth() - side_node.screenWidth()) // 2
                # For freeze blocks, side_root_x_offset is the left overhang past the
                # root node.  The block's right edge is at centering_offset + (side_w -
                # side_root_x_offset), and its left edge extends side_root_x_offset past
                # the root.  For normal nodes side_root_x_offset=0, so the formulas
                # reduce to the original expressions.
                right_extent = centering_offset + side_w - side_root_x_offset
                effective_widths[i] = max(effective_widths[i], right_extent)
                left_past_spine = side_root_x_offset - centering_offset
                if left_past_spine > 0:
                    left_extents[i] = max(left_extents[i], left_past_spine)
    else:
        # place_only: measure the actual current bounding box of each side subtree.
        # The subtree is translated as a rigid unit, so relative node positions are
        # preserved.  We compute how far the bbox extends right and left of the spine
        # node's left edge after the centered placement, so the advance formula uses
        # real subtree extents rather than just the spine node's own width.
        for i, spine_node in enumerate(spine_nodes):
            for slot_index in range(1, spine_node.inputs()):
                side_node = spine_node.input(slot_index)
                if side_node is None:
                    continue
                subtree_nodes = collect_subtree_nodes(side_node)
                if not subtree_nodes:
                    continue
                subtree_min_x = min(n.xpos() for n in subtree_nodes)
                subtree_max_x = max(n.xpos() + n.screenWidth() for n in subtree_nodes)
                # centering_offset: how far right from the spine node's left edge the
                # side root will land when centered above the spine node.
                centering_offset = (spine_node.screenWidth() - side_node.screenWidth()) // 2
                # right_extent_from_root: how far right the subtree bbox extends from
                # the side root's left edge (preserved under rigid translation).
                right_extent_from_root = subtree_max_x - side_node.xpos()
                effective_widths[i] = max(
                    effective_widths[i], centering_offset + right_extent_from_root
                )
                # left_extent_from_root: how far left the subtree bbox extends from
                # the side root's left edge.
                left_extent_from_root = side_node.xpos() - subtree_min_x
                leftward_past_spine = left_extent_from_root - centering_offset
                if leftward_past_spine > 0:
                    left_extents[i] = max(left_extents[i], leftward_past_spine)

    # --- First pass: walk spine from farthest ancestor toward root (reverse order).
    # Accumulate cumulative_kink_y from mask inputs encountered on each spine node.
    # Each spine node closer to root (lower index) drops by the accumulated kink
    # so that it clears the mask subtrees above nodes further upstream.
    #
    # kink_y_per_index[i] = total Y drop applied to spine_nodes[i].
    # We accumulate from the upstream end (high index) toward root (index 0).
    kink_y_per_index = [0] * len(spine_nodes)
    cumulative_kink_y = 0

    for reverse_index in range(len(spine_nodes) - 1, -1, -1):
        spine_node = spine_nodes[reverse_index]

        # Apply the kink accumulated so far (from nodes further upstream) to
        # this node's downstream neighbors. Assign cumulative kink to this node
        # BEFORE checking its own mask so that a node's own mask drops nodes
        # closer to root (lower indices), not itself.
        kink_y_per_index[reverse_index] = cumulative_kink_y

        # Check for mask inputs on this spine node; add their subtree height to
        # the cumulative kink that will affect all nodes closer to root.
        for slot_index in range(spine_node.inputs()):
            if slot_index == 0:
                continue  # primary input — handled separately
            input_node = spine_node.input(slot_index)
            if input_node is None:
                continue
            if _is_mask_input(spine_node, slot_index):
                side_count = side_input_counts.get(
                    (id(spine_node), slot_index),
                    len(collect_subtree_nodes(input_node)),
                )
                mask_dims = compute_dims(
                    input_node, memo, snap_threshold, side_count,
                    scheme_multiplier=scheme_multiplier,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                    dimension_overrides=dimension_overrides,
                )
                mask_height = mask_dims[1]
                mask_margin = _subtree_margin(
                    spine_node, slot_index, node_count,
                    mode_multiplier=scheme_multiplier,
                )
                cumulative_kink_y += mask_height + mask_margin

    # --- Second pass: place each spine node at its final X/Y position.
    # Spine nodes are spaced so that each node's side subtrees (slots 1+) fit
    # within the horizontal gap between it and the next rightward spine node.
    cur_x = spine_x
    for index, spine_node in enumerate(spine_nodes):
        cur_y = spine_y + kink_y_per_index[index]
        spine_node.setXpos(cur_x)
        spine_node.setYpos(cur_y)

        is_last_spine_node = (index == len(spine_nodes) - 1)

        # Place side inputs (slots 1+) above this spine node.
        for slot_index in range(1, spine_node.inputs()):
            side_node = spine_node.input(slot_index)
            if side_node is None:
                continue
            side_y = cur_y - horizontal_side_gap - side_node.screenHeight()
            side_x = _center_x(side_node.screenWidth(), cur_x, spine_node.screenWidth())
            if side_layout_mode == "recursive":
                side_count = side_input_counts.get(
                    (id(spine_node), slot_index),
                    len(collect_subtree_nodes(side_node)),
                )
                compute_dims(
                    side_node, memo, snap_threshold, side_count,
                    scheme_multiplier=scheme_multiplier,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                    dimension_overrides=dimension_overrides,
                )
                place_subtree(
                    side_node, side_x, side_y, memo, snap_threshold, side_count,
                    scheme_multiplier=scheme_multiplier,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                )
                # When the side input is (or routes through Dots to) a freeze
                # block root, place_subtree laid out all nodes (including
                # frozen members) in a normal vertical chain.  Now restore
                # the frozen members to their root-relative offsets and
                # translate any external inputs (non-frozen nodes that feed
                # into the block) to follow their connecting member's move.
                side_freeze_block_post = _find_freeze_block_through_dots(
                    side_node, dimension_overrides
                )
                if side_freeze_block_post is not None:
                    block = side_freeze_block_post
                    # Snapshot non-root member positions before restore
                    positions_before_restore = {}
                    for member in block.members:
                        if id(member) != block.root_id:
                            positions_before_restore[id(member)] = (
                                member.xpos(), member.ypos()
                            )
                    block.restore_positions()
                    # Re-place each external input subtree above its connecting
                    # freeze member's restored position.  A blind delta translation
                    # can land external inputs inside the block when restore_positions
                    # moves the connecting member downward.
                    for external_input, connecting_member in block.get_external_inputs(get_inputs):
                        upstream_subtree = collect_subtree_nodes(external_input)
                        upstream_filter = set(upstream_subtree)
                        upstream_count = len(upstream_subtree)
                        upstream_memo = {}
                        entry_dims = compute_dims(
                            external_input, upstream_memo, snap_threshold,
                            upstream_count, upstream_filter,
                            scheme_multiplier=scheme_multiplier,
                            per_node_h_scale=per_node_h_scale,
                            per_node_v_scale=per_node_v_scale,
                            dimension_overrides=dimension_overrides,
                        )
                        entry_x = _center_x(
                            external_input.screenWidth(),
                            connecting_member.xpos(),
                            connecting_member.screenWidth(),
                        )
                        raw_gap = vertical_gap_between(
                            external_input, connecting_member,
                            snap_threshold, scheme_multiplier=scheme_multiplier,
                        )
                        entry_y = (
                            connecting_member.ypos()
                            - max(snap_threshold - 1, raw_gap)
                            - entry_dims[1]
                        )
                        place_subtree(
                            external_input, entry_x, entry_y,
                            upstream_memo, snap_threshold, upstream_count,
                            upstream_filter,
                            scheme_multiplier=scheme_multiplier,
                            per_node_h_scale=per_node_h_scale,
                            per_node_v_scale=per_node_v_scale,
                            dimension_overrides=dimension_overrides,
                        )
            else:
                # Translate the entire side subtree as a unit (preserving its
                # internal layout) so that the subtree root lands at (side_x, side_y).
                delta_x = side_x - side_node.xpos()
                delta_y = side_y - side_node.ypos()
                for translated_node in collect_subtree_nodes(side_node):
                    translated_node.setXpos(translated_node.xpos() + delta_x)
                    translated_node.setYpos(translated_node.ypos() + delta_y)

        # For the farthest spine node, handle input[0] (non-spine upstream tree).
        if is_last_spine_node and spine_set is not None:
            raw_primary = spine_node.input(0)
            # Detect whether a leftmost Dot was already inserted by a prior recursive run.
            # Also treat any pre-existing plain Dot as a reusable leftmost dot to avoid
            # stacking a new Dot in front of one that already exists.
            if (
                raw_primary is not None
                and raw_primary.knob(_LEFTMOST_DOT_KNOB_NAME) is not None
                or (
                    raw_primary is not None
                    and raw_primary.Class() == "Dot"
                    and id(raw_primary) not in spine_set
                )
            ):
                leftmost_dot = raw_primary
                upstream_root = raw_primary.input(0)
            elif raw_primary is not None and id(raw_primary) not in spine_set:
                leftmost_dot = None
                upstream_root = raw_primary
            else:
                leftmost_dot = None
                upstream_root = None

            if upstream_root is not None:
                # Create the leftmost Dot if one does not already exist.
                # This must happen in BOTH recursive and place_only modes so that
                # the B-side wire always has a horizontal routing Dot at spine Y.
                if leftmost_dot is None:
                    leftmost_dot = _find_or_create_leftmost_dot(spine_node, current_group)

                # Position the Dot at spine Y, one step to the LEFT of the spine node.
                # dot_x = one step_x gap left of cur_x, accounting for the Dot's own width.
                # When the last spine node has side inputs with freeze blocks that
                # extend leftward past the spine node, the Dot must clear that extent
                # so the upstream subtree doesn't overlap frozen members.
                # dot_y = vertically centered on the spine node tile.
                if leftmost_dot is not None:
                    last_spine_left_extent = left_extents[index] if index < len(left_extents) else 0
                    dot_x = cur_x - step_x - leftmost_dot.screenWidth() - last_spine_left_extent
                    dot_y = cur_y + (spine_node.screenHeight() - leftmost_dot.screenHeight()) // 2
                    leftmost_dot.setXpos(dot_x)
                    leftmost_dot.setYpos(dot_y)

                # Compute the target position for the upstream (A) subtree root.
                # upstream_root is placed directly above the Dot's X column.
                # upstream_x: centered on dot_x so the wire drops vertically from
                #   upstream_root to the Dot before turning horizontal to the spine.
                # upstream_y: above the spine by horizontal_side_gap + node height.
                if leftmost_dot is not None:
                    upstream_x = (
                        dot_x
                        + (leftmost_dot.screenWidth() - upstream_root.screenWidth()) // 2
                    )
                else:
                    # Fallback (no Dot possible — spine node has no input[0]): place A
                    # to the left of the spine using the upstream root's own width.
                    upstream_x = cur_x - step_x - upstream_root.screenWidth()
                upstream_y = cur_y - horizontal_side_gap - upstream_root.screenHeight()

                if side_layout_mode == "recursive":
                    # Recursive: compute full subtree dims, then recursively place
                    # the upstream subtree at the pre-computed target position.
                    upstream_count = len(collect_subtree_nodes(upstream_root))
                    compute_dims(
                        upstream_root, memo, snap_threshold, upstream_count,
                        scheme_multiplier=scheme_multiplier,
                        per_node_h_scale=per_node_h_scale,
                        per_node_v_scale=per_node_v_scale,
                        dimension_overrides=dimension_overrides,
                    )

                    place_subtree(
                        upstream_root, upstream_x, upstream_y, memo,
                        snap_threshold, upstream_count,
                        scheme_multiplier=scheme_multiplier,
                        per_node_h_scale=per_node_h_scale,
                        per_node_v_scale=per_node_v_scale,
                    )
                else:
                    # place_only: translate the entire A upstream subtree as a unit
                    # so that the subtree root lands at (upstream_x, upstream_y),
                    # preserving the internal layout of the subtree.
                    upstream_subtree_nodes = collect_subtree_nodes(upstream_root)
                    delta_x = upstream_x - upstream_root.xpos()
                    delta_y = upstream_y - upstream_root.ypos()
                    for translated_node in upstream_subtree_nodes:
                        translated_node.setXpos(translated_node.xpos() + delta_x)
                        translated_node.setYpos(translated_node.ypos() + delta_y)

        # Advance cur_x leftward for the next upstream spine node.
        # Formula ensures a full step_x gap between the bounding boxes of adjacent
        # spine nodes' side subtrees:
        #   new_cur_x + effective_widths[i+1]  (right edge of next node's subtrees)
        #   +  step_x
        #   +  left_extents[i]                 (left edge of current node's subtrees)
        #   == cur_x
        # which rearranges to the expression below.
        if index + 1 < len(spine_nodes):
            cur_x = cur_x - step_x - effective_widths[index + 1] - left_extents[index]


def compute_dims(
    node, memo, snap_threshold, node_count,
    node_filter=None, scheme_multiplier=None,
    per_node_h_scale=None, per_node_v_scale=None,
    layout_mode="vertical", dimension_overrides=None,
):
    node_h_scale = per_node_h_scale.get(id(node), 1.0) if per_node_h_scale else 1.0
    node_v_scale = per_node_v_scale.get(id(node), 1.0) if per_node_v_scale else 1.0
    if (id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode) in memo:
        return memo[(id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode)]

    input_slot_pairs = _get_input_slot_pairs(node, node_filter)
    all_side = _primary_slot_externally_occupied(node, node_filter)
    fan_active = _is_fan_active(input_slot_pairs, node)
    input_slot_pairs = _reorder_inputs_mask_last(
        input_slot_pairs, node, all_side, fan_active=fan_active
    )
    inputs = [inp for _, inp in input_slot_pairs]
    side_margins_h = [
        int(_horizontal_margin(node, slot) * node_h_scale)
        for slot, _ in input_slot_pairs
    ]
    side_margins_v = [
        int(
            _subtree_margin(node, slot, node_count, mode_multiplier=scheme_multiplier)
            * node_v_scale
        )
        for slot, _ in input_slot_pairs
    ]

    if not inputs:
        if dimension_overrides is not None and id(node) in dimension_overrides:
            result = dimension_overrides[id(node)].leaf_dims
        else:
            result = (node.screenWidth(), node.screenHeight(), 0)
    elif all_side:
        # All in-filter inputs are side inputs; none goes directly above.
        child_dims = [
            compute_dims(
                inp, memo, snap_threshold, node_count, node_filter,
                scheme_multiplier=scheme_multiplier,
                per_node_h_scale=per_node_h_scale,
                per_node_v_scale=per_node_v_scale,
                dimension_overrides=dimension_overrides,
            )
            for inp in inputs
        ]
        n = len(inputs)
        W = node.screenWidth() + sum(side_margins_h) + sum(w for w, h, _ in child_dims)
        raw_gap = vertical_gap_between(inputs[n - 1], node, snap_threshold, scheme_multiplier)
        scaled_gap = max(snap_threshold - 1, int(raw_gap * node_v_scale))
        gap_closest = max(scaled_gap, side_margins_v[n - 1])
        inter_band_gaps = sum(side_margins_v[1:n])
        child_dims_h_sum = sum(h for w, h, _ in child_dims)
        H = node.screenHeight() + child_dims_h_sum + 2 * gap_closest + inter_band_gaps
        result = (W, H, 0)
    else:
        child_dims = [
            compute_dims(
                inp, memo, snap_threshold, node_count, node_filter,
                scheme_multiplier=scheme_multiplier,
                per_node_h_scale=per_node_h_scale,
                per_node_v_scale=per_node_v_scale,
                dimension_overrides=dimension_overrides,
            )
            for inp in inputs
        ]
        n = len(inputs)
        if n == 1:
            W = max(node.screenWidth(), child_dims[0][0])
            # Propagate left_overhang from the child so freeze block extents
            # are visible to parent allocation logic (e.g. when a Dot sits
            # between the freeze root and the Merge consuming it).
            child_left_overhang = child_dims[0][2]
        elif n == 2:
            # input[0] centered above node; input[1] sits at x + node_w + side_margins_h[1]
            W = max(child_dims[0][0],
                    node.screenWidth() + side_margins_h[1] + child_dims[1][0])
        else:
            # n >= 3: W formula differs in fan mode to exclude mask from rightward spread.
            mask_count = sum(1 for slot, _ in input_slot_pairs if _is_mask_input(node, slot))
            if fan_active and mask_count > 0:
                # Fan mode with mask: mask is placed LEFT; W measures rightward (non-mask) spread.
                # B (first non-mask) is centered above consumer; if B is wider than consumer
                # it overhangs rightward past consumer's right edge by (b_w - node_w) // 2.
                # A1 must clear B's right edge.
                non_mask_dims = child_dims[mask_count:]
                b_w = non_mask_dims[0][0]
                b_right_overhang = max(0, (b_w - node.screenWidth()) // 2)
                W = max(
                    b_w,
                    node.screenWidth() + b_right_overhang
                    + sum(side_margins_h[mask_count + 1:])
                    + sum(w for w, h, _ in non_mask_dims[1:]),
                )
            elif fan_active:
                # Fan without mask: B-overhang correction needed because all
                # non-mask inputs share the same Y level and must clear B's
                # rightward extent.
                b_w = child_dims[0][0]
                b_right_overhang = max(0, (b_w - node.screenWidth()) // 2)
                W = max(
                    b_w,
                    node.screenWidth() + b_right_overhang
                    + sum(side_margins_h[1:])
                    + sum(w for w, h, _ in child_dims[1:]),
                )
            else:
                # n >= 3 non-fan staircase: input[0] is centered above the
                # consumer in a higher Y band.  Side inputs (1..n-1) step
                # rightward from the consumer's right edge and occupy lower Y
                # bands, so they do NOT need to clear input[0]'s overhang.
                W = max(
                    child_dims[0][0],
                    node.screenWidth()
                    + sum(side_margins_h[1:])
                    + sum(w for w, h, _ in child_dims[1:]),
                )

        if fan_active and n >= 3:
            # Fan mode: all non-mask inputs sit at the same Y level.
            # H is determined by the TALLEST non-mask subtree, not the sum.
            # The mask subtree is placed LEFT (outside the rightward W); exclude it from H.
            mask_count = sum(1 for slot, _ in input_slot_pairs if _is_mask_input(node, slot))
            # non-mask children follow mask(s) in list
            non_mask_child_dims = child_dims[mask_count:]
            non_mask_start = mask_count
            raw_gap_b = vertical_gap_between(
                inputs[non_mask_start], node, snap_threshold, scheme_multiplier
            )
            gap_to_fan = max(snap_threshold - 1, int(raw_gap_b * node_v_scale))
            gap_to_fan = max(gap_to_fan, side_margins_v[non_mask_start])  # ensure Dot row fits
            fan_max_child_h = (
                max(h for w, h, _ in non_mask_child_dims) if non_mask_child_dims else 0
            )
            H = node.screenHeight() + fan_max_child_h + gap_to_fan
        else:
            # Staircase formula for all n: each input gets its own vertical band.
            # Total height is sum of all child subtree heights plus per-gap values that
            # depend on the tile colors of adjacent nodes.
            raw_gap_to_consumer = vertical_gap_between(
                inputs[n - 1], node, snap_threshold, scheme_multiplier
            )
            gap_to_consumer = max(snap_threshold - 1, int(raw_gap_to_consumer * node_v_scale))
            # When there are side inputs (n > 1), a dot will be inserted for inputs[n-1].
            # Reserve at least side_margins_v[n-1] so the dot fits without overlapping.
            if n > 1:
                gap_to_consumer = max(gap_to_consumer, side_margins_v[n - 1])
            inter_band_gaps = sum(side_margins_v[1:n])
            H = (
                node.screenHeight() + sum(h for w, h, _ in child_dims)
                + 2 * gap_to_consumer + inter_band_gaps
            )
        # For n==1 chains (including routing Dots above a freeze root), propagate
        # the child's left_overhang so the parent allocation reserves the right width.
        propagated_overhang = child_left_overhang if n == 1 else 0
        result = (W, H, propagated_overhang)

    # For non-leaf freeze block roots: widen the allocation to the full block bbox and
    # set root_x_offset to left_overhang so restored members don't escape their band.
    # The leaf branch above already handles the no-inputs case via leaf_dims; this
    # covers the case where the root has in-filter external inputs that prevent the
    # leaf branch from firing, yet frozen non-root members still carry wide X offsets.
    if inputs and dimension_overrides is not None and id(node) in dimension_overrides:
        block = dimension_overrides[id(node)]
        block_total_width = block.right_extent + block.left_overhang
        w, h, root_x_off = result
        if block_total_width > w or block.left_overhang > root_x_off:
            result = (max(w, block_total_width), h, max(root_x_off, block.left_overhang))

    memo[(id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode)] = result  # noqa: E501
    return result


def place_subtree(
    node, x, y, memo, snap_threshold, node_count,
    node_filter=None, scheme_multiplier=None,
    per_node_h_scale=None, per_node_v_scale=None,
    dimension_overrides=None,
):
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
    - inter-subtree gap: `side_margins[i]` — per-slot margin (base_subtree_margin scaled
      by sqrt(node_count) for normal inputs, further reduced by mask_input_ratio for
      mask/matte slots); keeps adjacent subtrees separated.

        bottom_y[n-1] = y - vertical_gap_between(inputs[n-1], node, snap_threshold)
        for i in range(n-2, -1, -1):
            bottom_y[i] = bottom_y[i+1] - child_dims[i+1][1] - side_margins[i+1]

    Within its band each input node is positioned at the band's bottom
    (closest to its consumer):

        y_for_input[i] = bottom_y[i] - inputs[i].screenHeight()

    Because each band's height equals the subtree's full compute_dims height,
    and consecutive bands are separated by their respective side_margins, no
    two subtrees can ever overlap in Y.

    X placement
    -----------
    compute_dims returns (W, H, root_x_offset) for each child subtree.
    Each child gets an allocation band of width W.  The child's root node
    is placed at alloc_left + root_x_offset within that band.

    For normal nodes root_x_offset is 0 (root at left edge of band).
    For freeze blocks root_x_offset equals the block's left overhang so
    the full block fits within the allocated band.

    n == 1  : input[0] centered above root.
    n == 2  : input[0] centered above root; input[1] one step right of
              root's right edge.
    n >= 3  : input[0] centered above root; inputs[1..n-1] step
              rightward from root's right edge; input[n-1] rightmost.
    """
    node_h_scale = per_node_h_scale.get(id(node), 1.0) if per_node_h_scale else 1.0
    node_v_scale = per_node_v_scale.get(id(node), 1.0) if per_node_v_scale else 1.0
    node.setXpos(x)
    node.setYpos(y)

    # Build a list of (actual_slot_index, input_node) pairs so that later
    # setInput calls use the correct slot even when some slots are None.
    if _hides_inputs(node):
        input_slot_pairs = []
    else:
        raw_pairs = [
            (slot, node.input(slot))
            for slot in range(node.inputs())
            if node.input(slot) is not None
        ]
        if node_filter is not None:
            input_slot_pairs = [
                (slot, inp) for slot, inp in raw_pairs
                if _passes_node_filter(inp, node_filter)
            ]
        else:
            input_slot_pairs = raw_pairs
    if not input_slot_pairs:
        return

    all_side = _primary_slot_externally_occupied(node, node_filter)
    fan_active = _is_fan_active(input_slot_pairs, node)
    input_slot_pairs = _reorder_inputs_mask_last(
        input_slot_pairs, node, all_side, fan_active=fan_active
    )
    actual_slots = [slot for slot, _ in input_slot_pairs]
    inputs = [inp for _, inp in input_slot_pairs]
    n = len(inputs)
    child_dims = [
        compute_dims(
            inp, memo, snap_threshold, node_count, node_filter,
            scheme_multiplier=scheme_multiplier,
            per_node_h_scale=per_node_h_scale,
            per_node_v_scale=per_node_v_scale,
            dimension_overrides=dimension_overrides,
        )
        for inp in inputs
    ]
    side_margins_h = [
        int(_horizontal_margin(node, slot) * node_h_scale) for slot in actual_slots
    ]
    side_margins_v = [
        int(
            _subtree_margin(node, slot, node_count, mode_multiplier=scheme_multiplier)
            * node_v_scale
        )
        for slot in actual_slots
    ]

    # --- Y placement: fan mode (uniform row) or staircase (backward walk) ---
    if fan_active and n >= 3:
        # Fan mode: determine mask_count from reordered input_slot_pairs.
        # After reorder with fan_active=True: mask at front, non-mask inputs follow.
        mask_count = sum(1 for slot, _ in input_slot_pairs if _is_mask_input(node, slot))
        non_mask_start = mask_count  # non-mask inputs begin at this index after reorder
        # Fan Y: all non-mask inputs at the same row; use B's (first non-mask) gap formula.
        raw_gap_b = vertical_gap_between(
            inputs[non_mask_start], node, snap_threshold, scheme_multiplier
        )
        gap_to_fan = max(snap_threshold - 1, int(raw_gap_b * node_v_scale))
        gap_to_fan = max(gap_to_fan, side_margins_v[non_mask_start])
        # All non-mask roots placed at fan_y (top-left corner = fan_y).
        fan_y = y - gap_to_fan - inputs[non_mask_start].screenHeight()
        y_positions = [0] * n
        for i in range(non_mask_start, n):
            y_positions[i] = fan_y  # same Y for all non-mask inputs
        # Mask Y: own V-band, unaffected (existing _subtree_margin/mask_input_ratio logic).
        for i in range(mask_count):
            raw_gap_mask = vertical_gap_between(inputs[i], node, snap_threshold, scheme_multiplier)
            gap_mask = max(snap_threshold - 1, int(raw_gap_mask * node_v_scale))
            gap_mask = max(gap_mask, side_margins_v[i])
            y_positions[i] = y - gap_mask - inputs[i].screenHeight()
    else:
        # Staircase Y: backward walk so input[n-1] is closest to root.
        # Mirror the gap enlargement from compute_dims: when n > 1 (or all_side,
        # which always inserts a dot), the gap must be at least side_margins_v[n-1].
        raw_gap_closest = vertical_gap_between(
            inputs[n - 1], node, snap_threshold, scheme_multiplier
        )
        gap_closest = max(snap_threshold - 1, int(raw_gap_closest * node_v_scale))
        if n > 1 or all_side:
            gap_closest = max(gap_closest, side_margins_v[n - 1])
        bottom_y = [0] * n
        bottom_y[n - 1] = y - gap_closest
        for i in range(n - 2, -1, -1):
            bottom_y[i] = bottom_y[i + 1] - child_dims[i + 1][1] - side_margins_v[i + 1]
        y_positions = [bottom_y[i] - inputs[i].screenHeight() for i in range(n)]

    # --- X positions ---
    # compute_dims returns (W, H, root_x_offset) where:
    #   W = total allocation width for the subtree
    #   root_x_offset = distance from the left edge of the allocation band to the root node's x
    # Every input has an allocation band of width child_dims[i][0].
    # The root node is placed at alloc_left + child_dims[i][2].
    # For normal nodes root_x_offset = 0, so root_x = alloc_left (identical to prior behaviour).
    # For freeze blocks root_x_offset = left_overhang, so the block's left edge sits at alloc_left.
    #
    # Centering (primary input above consumer): center the ROOT NODE visually above the
    # consumer, then derive alloc_left = root_x - root_x_offset.  This prevents cascading
    # drift in chains where the allocation width exceeds the node width.

    if all_side:
        # All inputs are side inputs; step allocated bands rightward from node's right edge.
        current_alloc = x + node.screenWidth() + side_margins_h[0]
        x_positions = []
        for i in range(n):
            x_positions.append(current_alloc + child_dims[i][2])
            current_alloc += child_dims[i][0] + (side_margins_h[i + 1] if i + 1 < n else 0)
    elif n == 1:
        root_x_0 = _center_x(inputs[0].screenWidth(), x, node.screenWidth())
        x_positions = [root_x_0]
    elif n == 2:
        # input[0]: centered above consumer; input[1]: one step right of consumer's
        # right edge.  input[0] occupies a higher Y band in the staircase, so its
        # full subtree width does NOT push input[1] rightward — they cannot overlap.
        root_x_0 = _center_x(inputs[0].screenWidth(), x, node.screenWidth())
        alloc1 = x + node.screenWidth() + side_margins_h[1]
        x_positions = [root_x_0, alloc1 + child_dims[1][2]]
    elif fan_active and n >= 3:
        # Fan mode n >= 3: mask(s) placed LEFT; non-mask B centered above; A1/A2/... rightward.
        # non_mask_start is already computed in the Y section above.
        x_positions = [0] * n
        root_x_b = _center_x(inputs[non_mask_start].screenWidth(), x, node.screenWidth())
        x_positions[non_mask_start] = root_x_b
        alloc_b = root_x_b - child_dims[non_mask_start][2]
        current_alloc = (
            max(x + node.screenWidth(), alloc_b + child_dims[non_mask_start][0])
            + (side_margins_h[non_mask_start + 1] if non_mask_start + 1 < n else 0)
        )
        for i in range(non_mask_start + 1, n):
            x_positions[i] = current_alloc + child_dims[i][2]
            if i + 1 < n:
                current_alloc += child_dims[i][0] + side_margins_h[i + 1]
        # Mask(s) placed LEFT of consumer: alloc band ends at x - mask_gap_h.
        for i in range(mask_count):
            mask_gap_h = int(_horizontal_margin(node, actual_slots[i]) * node_h_scale)
            alloc_mask_left = x - mask_gap_h - child_dims[i][0]
            x_positions[i] = alloc_mask_left + child_dims[i][2]
    else:
        # n >= 3 non-fan: input[0] centered; inputs[1..n-1] step right from
        # consumer's right edge.  input[0] is in a higher Y band, so its full
        # subtree width does NOT push side inputs rightward.
        root_x_0 = _center_x(inputs[0].screenWidth(), x, node.screenWidth())
        x_positions = [root_x_0]
        current_alloc = x + node.screenWidth() + side_margins_h[1]
        for i in range(1, n):
            x_positions.append(current_alloc + child_dims[i][2])
            if i + 1 < n:
                current_alloc += child_dims[i][0] + side_margins_h[i + 1]

    # --- Insert Dots for side inputs that are not already Dots ---
    # Deselect all nodes before creating any dot so Nuke cannot auto-connect it.
    for selected_node in nuke.selectedNodes():
        selected_node['selected'].setValue(False)
    if all_side:
        # Every in-filter input is a side input; insert dots for all of them.
        for i in range(n):
            if inputs[i].Class() != 'Dot':
                dot = nuke.nodes.Dot()
                for auto_slot in range(dot.inputs()):
                    dot.setInput(auto_slot, None)
                dot.setInput(0, inputs[i])
                node.setInput(actual_slots[i], dot)
                inputs[i] = dot
    else:
        if fan_active and n >= 3:
            # Fan mode: insert Dots for ALL inputs
            # (non-mask including B at index non_mask_start, plus mask as side).
            for i in range(n):
                if inputs[i].Class() != 'Dot':
                    dot = nuke.nodes.Dot()
                    for auto_slot in range(dot.inputs()):
                        dot.setInput(auto_slot, None)
                    dot.setInput(0, inputs[i])
                    node.setInput(actual_slots[i], dot)
                    inputs[i] = dot
        else:
            # Non-fan: only non-primary inputs (i > 0) need dots.
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
        # In fan mode, ALL inputs (including B at non_mask_start) are treated as side inputs
        # and get routing Dots. The not _hides_inputs guard prevents diamond Dots from
        # being treated as routing Dots.
        is_side_dot = (
            (all_side or (fan_active and n >= 3) or i > 0)
            and inp.Class() == 'Dot'
            and not _hides_inputs(inp)
        )
        if is_side_dot:
            # Newly inserted side-input dot (hide_input is False).
            # Place the upstream subtree at the fan/staircase position, then
            # position the dot itself separately.
            actual_upstream = inp.input(0)
            place_subtree(
                actual_upstream, x_positions[i], y_positions[i],
                memo, snap_threshold, node_count, node_filter,
                scheme_multiplier=scheme_multiplier,
                per_node_h_scale=per_node_h_scale,
                per_node_v_scale=per_node_v_scale,
            )
            dot_center_x = x_positions[i] + actual_upstream.screenWidth() // 2
            if fan_active and n >= 3:
                # Fan mode: Dot row sits in gap above consumer, symmetric snap_threshold-1 margins.
                # gap_to_fan is already sized to hold the Dot; place bottom of Dot at
                # snap_threshold-1 above consumer top (y).
                # Nuke Y is positive-down so subtract to move upward.
                dot_row_y = y - (snap_threshold - 1) - inp.screenHeight()
                dot_y = dot_row_y
            elif i == n - 1:
                # Staircase: bottom-most dot centred vertically beside the root node.
                dot_y = y + (node.screenHeight() - inp.screenHeight()) // 2
            else:
                # Staircase: staggered dot placed below its input node using prefs-based margin.
                dot_y = (
                    y_positions[i] + actual_upstream.screenHeight()
                    + int(
                        _subtree_margin(
                            node, actual_slots[n - 1], node_count,
                            mode_multiplier=scheme_multiplier,
                        ) * node_v_scale
                    )
                )
            inp.setXpos(dot_center_x - inp.screenWidth() // 2)
            inp.setYpos(dot_y)
        else:
            # Regular node, or a diamond-resolution Dot
            # (hide_input=True, node_layout_diamond_dot knob).
            place_subtree(
                inp, x_positions[i], y_positions[i],
                memo, snap_threshold, node_count, node_filter,
                scheme_multiplier=scheme_multiplier,
                per_node_h_scale=per_node_h_scale,
                per_node_v_scale=per_node_v_scale,
            )
            # After recursion, reposition diamond Dots to be centered under the consumer tile.
            # The upstream subtree above the Dot is unaffected — only the Dot tile moves.
            if (inp.Class() == 'Dot'
                    and inp.knob('node_layout_diamond_dot') is not None):
                diamond_centered_x = _center_x(inp.screenWidth(), x, node.screenWidth())
                inp.setXpos(diamond_centered_x)


def collect_subtree_nodes(root, node_filter=None):
    visited_ids = set()
    nodes = []
    def _traverse(node):
        if node is None or id(node) in visited_ids:
            return
        if node_filter is not None and node not in node_filter:
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


def _collect_full_side_subtree(side_root, freeze_blocks):
    """Collect all nodes in a side-input subtree, including freeze block members
    and their external upstream chains that were placed by the post-pass."""
    nodes = collect_subtree_nodes(side_root)
    node_ids = {id(n) for n in nodes}
    # Add freeze block members and their upstream chains
    for block in freeze_blocks:
        # If any block member is already in the subtree, include all members
        if any(id(m) in node_ids for m in block.members):
            for member in block.members:
                if id(member) not in node_ids:
                    nodes.append(member)
                    node_ids.add(id(member))
                    # Also include upstream chains placed by the post-pass
                    for upstream_node in collect_subtree_nodes(member):
                        if id(upstream_node) not in node_ids:
                            nodes.append(upstream_node)
                            node_ids.add(id(upstream_node))
    return nodes


def _resolve_freeze_subtree_overlaps(root, freeze_blocks, all_non_root_ids,
                                     _unused_filter):
    """Post-layout pass: resolve overlapping side-input subtree bounding boxes.

    Walks the spine (input-0 chain from root), and for each node with side inputs,
    collects the actual bounding box of each side-input subtree (including freeze
    members and their upstream chains).  If any bbox overlaps the spine or a
    previous sibling, shifts all nodes in that subtree rightward.
    """
    # Minimum cell dimensions — in GUI mode screenWidth/screenHeight are real;
    # in headless mode they return 0, so use a floor to avoid zero-width bboxes.
    min_cell_w = 80
    min_cell_h = 20

    def _robust_bbox(nodes):
        """Bounding box using at least min_cell_w/min_cell_h per node."""
        if not nodes:
            return None
        min_x = min(n.xpos() for n in nodes)
        min_y = min(n.ypos() for n in nodes)
        max_x = max(n.xpos() + max(n.screenWidth(), min_cell_w) for n in nodes)
        max_y = max(n.ypos() + max(n.screenHeight(), min_cell_h) for n in nodes)
        return (min_x, min_y, max_x, max_y)

    # Collect spine nodes (input-0 chain)
    spine_nodes = []
    cursor = root
    while cursor is not None:
        spine_nodes.append(cursor)
        cursor = cursor.input(0)

    spine_ids = {id(n) for n in spine_nodes}
    spine_bbox = _robust_bbox(spine_nodes)
    if spine_bbox is None:
        return

    # Collect all side-input subtrees with their actual bounding boxes
    side_subtrees = []  # list of (nodes_list, bbox)
    for spine_node in spine_nodes:
        for slot in range(1, spine_node.inputs()):
            side_input = spine_node.input(slot)
            if side_input is None:
                continue
            subtree_nodes = _collect_full_side_subtree(side_input, freeze_blocks)
            # Remove any spine nodes that may have been collected
            subtree_nodes = [n for n in subtree_nodes if id(n) not in spine_ids]
            if not subtree_nodes:
                continue
            bbox = _robust_bbox(subtree_nodes)
            if bbox is not None:
                side_subtrees.append((subtree_nodes, bbox))

    # Resolve overlaps: ensure each subtree's bbox doesn't overlap the spine
    # or any previously placed subtree
    occupied_bboxes = [spine_bbox]  # start with spine as occupied

    for subtree_nodes, bbox in side_subtrees:
        shift_x = 0
        subtree_left, subtree_top, subtree_right, subtree_bottom = bbox

        for occupied_bbox in occupied_bboxes:
            occ_left, occ_top, occ_right, occ_bottom = occupied_bbox
            # Check for overlap (both X and Y ranges must intersect).
            overlaps_x = subtree_left < occ_right and occ_left < subtree_right
            overlaps_y = subtree_top < occ_bottom and occ_top < subtree_bottom
            if overlaps_x and overlaps_y:
                # Shift right by exactly the overlap amount to clear.
                needed_shift = occ_right - subtree_left
                if needed_shift > shift_x:
                    shift_x = needed_shift

        if shift_x > 0:
            for node in subtree_nodes:
                node.setXpos(node.xpos() + shift_x)
            # Update bbox after shift
            bbox = (subtree_left + shift_x, subtree_top,
                    subtree_right + shift_x, subtree_bottom)

        occupied_bboxes.append(bbox)


def push_nodes_to_make_room(subtree_node_ids, bbox_before, bbox_after, current_group=None,
                            freeze_blocks=None):
    """Push surrounding nodes to make room after a subtree grows.

    Args:
        subtree_node_ids: set of id(node) for nodes in the moved subtree (skipped).
        bbox_before: (min_x, min_y, max_x, max_y) bounding box before placement.
        bbox_after: (min_x, min_y, max_x, max_y) bounding box after placement.
        current_group: Nuke group context for node enumeration, or None for root context.
        freeze_blocks: list[FreezeBlock] for rigid block handling, or None.
    """
    before_min_x, before_min_y, before_max_x, before_max_y = bbox_before
    after_min_x, after_min_y, after_max_x, after_max_y = bbox_after

    grew_up = after_min_y < before_min_y
    grew_right = after_max_x > before_max_x

    if not grew_up and not grew_right:
        return

    push_up_amount = before_min_y - after_min_y if grew_up else 0
    push_right_amount = after_max_x - before_max_x if grew_right else 0

    # Build lookup: id(node) -> FreezeBlock for O(1) membership check
    block_lookup = {}
    if freeze_blocks:
        for block in freeze_blocks:
            for member in block.members:
                block_lookup[id(member)] = block

    already_translated_blocks = set()

    all_dag_nodes = current_group.nodes() if current_group is not None else nuke.allNodes()
    for node in all_dag_nodes:
        if id(node) in subtree_node_ids:
            continue

        # --- Freeze block handling ---
        if id(node) in block_lookup:
            block = block_lookup[id(node)]
            if block.uuid in already_translated_blocks:
                continue
            already_translated_blocks.add(block.uuid)

            block_bbox = compute_node_bounding_box(block.members)
            if block_bbox is None:
                continue
            block_left, block_top, block_right, block_bottom = block_bbox

            # Skip blocks overlapping the before-footprint
            if (block_left < before_max_x and block_right > before_min_x and
                    block_top < before_max_y and block_bottom > before_min_y):
                continue

            delta_x = 0
            delta_y = 0
            if grew_up and block_bottom <= before_min_y:
                delta_y = -push_up_amount
            if (grew_right and block_left >= before_max_x
                    and block_top < after_max_y and block_bottom > after_min_y):
                delta_x = push_right_amount

            if delta_x != 0 or delta_y != 0:
                for block_member in block.members:
                    block_member.setXpos(block_member.xpos() + delta_x)
                    block_member.setYpos(block_member.ypos() + delta_y)
            continue

        # --- Standard (non-frozen) node handling ---
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

        # Only push right if vertically overlapping with the subtree footprint.
        # Nodes fully above or below the subtree cannot collide horizontally.
        if (grew_right and node_left >= before_max_x
                and node_top < after_max_y and node_bottom > after_min_y):
            delta_x = push_right_amount

        if delta_x != 0 or delta_y != 0:
            node.setXpos(node.xpos() + delta_x)
            node.setYpos(node.ypos() + delta_y)


class FreezeBlock:
    """Encapsulates all freeze state for a single rigid block of nodes."""

    def __init__(self, root, members, uuid):
        self.root = root
        self.members = members
        self.uuid = uuid
        self.member_ids = {id(m) for m in members}
        self.root_id = id(root)

        # Compute bounding box
        block_min_x = min(m.xpos() for m in members)
        block_max_x = max(m.xpos() + m.screenWidth() for m in members)
        block_min_y = min(m.ypos() for m in members)
        block_max_y = max(m.ypos() + m.screenHeight() for m in members)

        # Dimensions for compute_dims leaf override (root-relative, matching current 3-tuple)
        self.right_extent = block_max_x - root.xpos()
        self.left_overhang = root.xpos() - block_min_x
        self.block_height = block_max_y - block_min_y

        # Additional height from external upstream subtrees above block members.
        # Set by _augment_freeze_block_heights() before compute_dims runs.
        self.external_height = 0

        # Root-relative offsets for position restoration
        self.offsets = {}
        for member in members:
            if id(member) != id(root):
                self.offsets[id(member)] = (
                    member.xpos() - root.xpos(),
                    member.ypos() - root.ypos(),
                )

    @property
    def non_root_ids(self):
        return self.member_ids - {self.root_id}

    @property
    def leaf_dims(self):
        """3-tuple for compute_dims leaf override: (total_w, height, left_overhang)."""
        return (self.right_extent + self.left_overhang,
                self.block_height + self.external_height,
                self.left_overhang)

    def restore_positions(self):
        """Reposition non-root members relative to root's current (post-layout) position."""
        root_x = self.root.xpos()
        root_y = self.root.ypos()
        for member in self.members:
            member_id = id(member)
            if member_id != self.root_id and member_id in self.offsets:
                delta_x, delta_y = self.offsets[member_id]
                member.setXpos(root_x + delta_x)
                member.setYpos(root_y + delta_y)

    def get_external_inputs(self, get_inputs_fn):
        """Find inputs from outside this block to any member.
        Returns list of (external_node, connecting_member) pairs."""
        result = []
        seen = set()
        for member in self.members:
            for inp in get_inputs_fn(member):
                if inp is not None and id(inp) not in self.member_ids and id(inp) not in seen:
                    seen.add(id(inp))
                    result.append((inp, member))
        return result


def _build_freeze_blocks(freeze_group_map):
    """Create FreezeBlock objects from detection results.
    Returns (blocks, dimension_overrides, all_non_root_ids, all_member_ids).
    """
    blocks = []
    dimension_overrides = {}      # id(root) -> FreezeBlock
    all_non_root_ids = set()
    all_member_ids = set()
    for group_uuid, members in freeze_group_map.items():
        block_root = _find_freeze_block_root(members)
        block = FreezeBlock(root=block_root, members=members, uuid=group_uuid)
        blocks.append(block)
        dimension_overrides[id(block_root)] = block
        all_non_root_ids |= block.non_root_ids
        all_member_ids |= block.member_ids
    return blocks, dimension_overrides, all_non_root_ids, all_member_ids


def _augment_freeze_block_heights(freeze_blocks, snap_threshold,
                                  scheme_multiplier=None,
                                  per_node_h_scale=None, per_node_v_scale=None,
                                  dimension_overrides=None):
    """Pre-compute external upstream subtree heights for each freeze block.

    The post-pass in layout_upstream places upstream subtrees above freeze block
    members.  This function computes those heights so leaf_dims reserves the
    right Y space in the staircase.
    """
    for block in freeze_blocks:
        external_inputs = block.get_external_inputs(get_inputs)
        total_external_height = 0
        for entry_node, connecting_member in external_inputs:
            upstream_subtree = collect_subtree_nodes(entry_node)
            upstream_filter = set(upstream_subtree)
            upstream_count = len(upstream_subtree)
            upstream_memo = {}
            entry_dims = compute_dims(
                entry_node, upstream_memo, snap_threshold, upstream_count,
                upstream_filter,
                scheme_multiplier=scheme_multiplier,
                per_node_h_scale=per_node_h_scale,
                per_node_v_scale=per_node_v_scale,
                dimension_overrides=dimension_overrides,
            )
            raw_gap = vertical_gap_between(
                entry_node, connecting_member, snap_threshold,
                scheme_multiplier=scheme_multiplier,
            )
            gap = max(snap_threshold - 1, raw_gap)
            total_external_height += entry_dims[1] + gap
        block.external_height = total_external_height


def _find_freeze_block_root(block_members):
    """Return the most downstream node in *block_members*.

    The root is the block member that no other block member takes as an input.
    If multiple qualify (disconnected block), pick by max ypos() as tiebreaker
    (highest Y value = lowest on screen = most downstream in Nuke DAG).
    """
    candidates = []
    for member in block_members:
        is_input_to_another_member = False
        for other in block_members:
            if id(other) == id(member):
                continue
            for slot in range(other.inputs()):
                if other.input(slot) is not None and id(other.input(slot)) == id(member):
                    is_input_to_another_member = True
                    break
            if is_input_to_another_member:
                break
        if not is_input_to_another_member:
            candidates.append(member)
    if not candidates:
        return block_members[0]  # fallback
    # Tiebreak: most downstream = highest ypos (positive Y is down in Nuke DAG)
    return max(candidates, key=lambda n: n.ypos())


def _detect_freeze_groups(scope_nodes):
    """Detect freeze groups in *scope_nodes* and resolve auto-join and group merges.

    Pass 1: Scan all scope_nodes and read freeze_group UUID from each via
    node_layout_state.read_freeze_group().  Build initial membership maps.

    Pass 2: Iteratively auto-join non-frozen nodes that have both a frozen
    ancestor AND a frozen descendant in the same group.  A node that bridges
    two different groups triggers a group merge: a new UUID is generated and
    persisted to all affected nodes via node_layout_state.write_freeze_group().

    Returns
    -------
    freeze_group_map : dict[str, list[Node]]
        Maps freeze group UUID string to the list of member nodes in scope.
    node_freeze_uuid : dict[int, str]
        Maps id(node) to UUID string for O(1) membership lookup.
    """
    # --- Pass 1: build initial membership maps ---
    freeze_group_map = {}   # uuid -> [node, ...]
    node_freeze_uuid = {}   # id(node) -> uuid

    for scope_node in scope_nodes:
        group_uuid = node_layout_state.read_freeze_group(scope_node)
        if group_uuid is not None:
            node_freeze_uuid[id(scope_node)] = group_uuid
            freeze_group_map.setdefault(group_uuid, []).append(scope_node)

    # --- Pass 2: auto-join and group merge ---
    # Build downstream_map: id(input_node) -> list of consumers in scope.
    scope_id_set = {id(n) for n in scope_nodes}
    downstream_map = {}  # id(node) -> [consumer_nodes in scope]
    for scope_node in scope_nodes:
        for input_node in get_inputs(scope_node):
            if id(input_node) in scope_id_set:
                downstream_map.setdefault(id(input_node), []).append(scope_node)

    def _collect_frozen_ancestor_uuids(start_node):
        """BFS upstream from start_node; return set of freeze UUIDs encountered."""
        found_uuids = set()
        visited_ids = {id(start_node)}
        queue = list(get_inputs(start_node))
        while queue:
            current_node = queue.pop(0)
            if id(current_node) not in scope_id_set:
                continue
            if id(current_node) in visited_ids:
                continue
            visited_ids.add(id(current_node))
            if id(current_node) in node_freeze_uuid:
                found_uuids.add(node_freeze_uuid[id(current_node)])
            else:
                for upstream_node in get_inputs(current_node):
                    if id(upstream_node) in scope_id_set and id(upstream_node) not in visited_ids:
                        queue.append(upstream_node)
        return found_uuids

    def _collect_frozen_descendant_uuids(start_node):
        """BFS downstream from start_node using downstream_map; return set of freeze UUIDs."""
        found_uuids = set()
        visited_ids = {id(start_node)}
        queue = list(downstream_map.get(id(start_node), []))
        while queue:
            current_node = queue.pop(0)
            if id(current_node) in visited_ids:
                continue
            visited_ids.add(id(current_node))
            if id(current_node) in node_freeze_uuid:
                found_uuids.add(node_freeze_uuid[id(current_node)])
            else:
                for downstream_node in downstream_map.get(id(current_node), []):
                    if id(downstream_node) not in visited_ids:
                        queue.append(downstream_node)
        return found_uuids

    # Iterative loop: keep checking until no more joins/merges happen.
    changed = True
    while changed:
        changed = False
        for candidate_node in scope_nodes:
            if id(candidate_node) in node_freeze_uuid:
                continue  # already frozen — skip

            ancestor_uuids = _collect_frozen_ancestor_uuids(candidate_node)
            if not ancestor_uuids:
                continue  # no frozen ancestors — cannot join

            descendant_uuids = _collect_frozen_descendant_uuids(candidate_node)
            if not descendant_uuids:
                continue  # no frozen descendants — cannot join (not sandwiched)

            # All UUIDs reachable from this candidate in both directions.
            all_involved_uuids = ancestor_uuids | descendant_uuids

            if len(all_involved_uuids) == 1:
                # Auto-join: candidate is sandwiched within a single group.
                join_uuid = next(iter(all_involved_uuids))
                node_freeze_uuid[id(candidate_node)] = join_uuid
                freeze_group_map.setdefault(join_uuid, []).append(candidate_node)
                node_layout_state.write_freeze_group(candidate_node, join_uuid)
                changed = True
            else:
                # Merge: candidate bridges two or more different groups.
                merged_uuid = str(uuid.uuid4())
                # Collect all members of all involved groups plus the bridging node.
                all_affected = []
                for involved_uuid in all_involved_uuids:
                    for group_member in freeze_group_map.get(involved_uuid, []):
                        all_affected.append(group_member)
                    if involved_uuid in freeze_group_map:
                        del freeze_group_map[involved_uuid]
                all_affected.append(candidate_node)
                # Write the new merged UUID to every affected node.
                for affected_node in all_affected:
                    node_layout_state.write_freeze_group(affected_node, merged_uuid)
                    node_freeze_uuid[id(affected_node)] = merged_uuid
                freeze_group_map[merged_uuid] = all_affected
                changed = True

    return freeze_group_map, node_freeze_uuid


def _expand_scope_for_freeze_groups(selected_nodes, current_group):
    """Expand *selected_nodes* to include all members of any freeze group encountered.

    Silently adds non-selected nodes that share a freeze group UUID with any
    selected node.  Scans all nodes in *current_group* (via current_group.nodes()
    if not None, else nuke.allNodes()) to find full group membership.

    Parameters
    ----------
    selected_nodes : list[Node]
        Nodes initially in scope (selected or subtree).
    current_group : context manager or None
        The active Nuke group context (from nuke.lastHitGroup()).

    Returns
    -------
    list[Node]
        Union of selected_nodes and all discovered group members (de-duplicated).
    """
    # Collect all freeze UUIDs present in the selected nodes.
    selected_uuids = set()
    for selected_node in selected_nodes:
        group_uuid = node_layout_state.read_freeze_group(selected_node)
        if group_uuid is not None:
            selected_uuids.add(group_uuid)

    if not selected_uuids:
        return list(selected_nodes)

    # Scan all group nodes for members of the found UUIDs.
    all_group_nodes = current_group.nodes() if current_group is not None else nuke.allNodes()

    expanded_id_set = {id(n) for n in selected_nodes}
    expanded_nodes = list(selected_nodes)
    for group_node in all_group_nodes:
        if id(group_node) in expanded_id_set:
            continue
        node_uuid = node_layout_state.read_freeze_group(group_node)
        if node_uuid in selected_uuids:
            expanded_nodes.append(group_node)
            expanded_id_set.add(id(group_node))

    return expanded_nodes


def layout_upstream(scheme_multiplier=None):
    global _TOOLBAR_FOLDER_MAP
    _TOOLBAR_FOLDER_MAP = None
    _clear_color_cache()
    current_group = nuke.lastHitGroup()    # MUST be the first Nuke API call
    root = nuke.selectedNode()

    nuke.Undo.name("Layout Upstream")
    nuke.Undo.begin()
    try:
        with current_group:
            # --- Freeze group preprocessing (FRZE-04, FRZE-05, FRZE-06) ---
            all_upstream_nodes = collect_subtree_nodes(root)
            freeze_scope_nodes = _expand_scope_for_freeze_groups(all_upstream_nodes, current_group)
            freeze_group_map, node_freeze_uuid = _detect_freeze_groups(freeze_scope_nodes)
            freeze_blocks, dimension_overrides, all_non_root_ids, all_member_ids = (
                _build_freeze_blocks(freeze_group_map)
            )

            # Capture starting state before any changes.
            original_subtree_nodes = collect_subtree_nodes(root)
            bbox_before = compute_node_bounding_box(original_subtree_nodes)

            subtree_nodes_for_count = collect_subtree_nodes(root)
            node_count = len(subtree_nodes_for_count)

            insert_dot_nodes(root)

            # Per-node scheme resolution — build per_node_scheme dict before compute_dims
            current_prefs = node_layout_prefs.prefs_singleton
            per_node_scheme = {}  # maps id(node) -> float scheme multiplier
            per_node_h_scale = {}  # maps id(node) -> float h_scale
            per_node_v_scale = {}  # maps id(node) -> float v_scale
            for subtree_node in subtree_nodes_for_count:
                if scheme_multiplier is not None:
                    per_node_scheme[id(subtree_node)] = scheme_multiplier
                else:
                    stored_state = node_layout_state.read_node_state(subtree_node)
                    per_node_scheme[id(subtree_node)] = node_layout_state.scheme_name_to_multiplier(
                        stored_state["scheme"], current_prefs
                    )
                # h_scale/v_scale always come from stored state (independent of scheme override)
                scale_state = node_layout_state.read_node_state(subtree_node)
                per_node_h_scale[id(subtree_node)] = scale_state["h_scale"]
                per_node_v_scale[id(subtree_node)] = scale_state["v_scale"]
            # Resolved multiplier for this root (used in compute_dims and place_subtree)
            root_scheme_multiplier = per_node_scheme.get(
                id(root), current_prefs.get("normal_multiplier")
            )

            memo = {}
            snap_threshold = get_dag_snap_threshold()

            # Pre-compute external upstream subtree heights for freeze blocks
            # so leaf_dims reserves correct Y space in the staircase.
            if freeze_blocks:
                _augment_freeze_block_heights(
                    freeze_blocks, snap_threshold,
                    scheme_multiplier=root_scheme_multiplier,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                    dimension_overrides=dimension_overrides,
                )

            # Mode dispatch: read the root's stored mode to decide horizontal vs vertical path.
            root_stored_state = node_layout_state.read_node_state(root)
            root_mode = root_stored_state.get("mode", "vertical")

            # Save the originally selected node before the ancestor walk may rebind root.
            # Used to anchor the horizontal chain above the downstream consumer.
            original_selected_root = root

            # If the selected node is downstream of a horizontal chain (its own mode is
            # vertical), BFS across all input slots to find the most-downstream ancestor
            # stored as horizontal. That ancestor becomes the effective replay root.
            # BFS (not input(0)-only walk) is required because the horizontal root may
            # be wired to any input slot of the selected node (e.g. input(1) foreground
            # on a Merge node).
            if root_mode != "horizontal":
                if not _hides_inputs(root):
                    bfs_queue = [root.input(slot) for slot in range(root.inputs())
                                 if root.input(slot) is not None]
                else:
                    bfs_queue = []
                bfs_visited = {id(root)}
                bfs_index = 0
                while bfs_index < len(bfs_queue):
                    bfs_cursor = bfs_queue[bfs_index]
                    bfs_index += 1
                    if id(bfs_cursor) in bfs_visited:
                        continue
                    bfs_visited.add(id(bfs_cursor))
                    # Frozen nodes must not become horizontal replay roots — skip as root candidate
                    # but continue BFS through their inputs so non-frozen horizontal nodes upstream
                    # can still be found.
                    if id(bfs_cursor) in all_member_ids:
                        if not _hides_inputs(bfs_cursor):
                            for bfs_slot in range(bfs_cursor.inputs()):
                                bfs_inp = bfs_cursor.input(bfs_slot)
                                if bfs_inp is not None and id(bfs_inp) not in bfs_visited:
                                    bfs_queue.append(bfs_inp)
                        continue
                    if node_layout_state.read_node_state(bfs_cursor).get("mode") == "horizontal":
                        root = bfs_cursor
                        root_mode = "horizontal"
                        break
                    if not _hides_inputs(bfs_cursor):
                        for bfs_slot in range(bfs_cursor.inputs()):
                            bfs_inp = bfs_cursor.input(bfs_slot)
                            if bfs_inp is not None and id(bfs_inp) not in bfs_visited:
                                bfs_queue.append(bfs_inp)

            # When replaying horizontal, build the spine_set by walking input[0] and
            # collecting consecutive nodes whose stored mode is "horizontal". The spine
            # ends at the first node whose mode differs.
            replay_spine_set = None
            if root_mode == "horizontal":
                # Recompute scheme multiplier for the (possibly rebound) horizontal root.
                root_scheme_multiplier = per_node_scheme.get(
                    id(root), current_prefs.get("normal_multiplier")
                )
                replay_spine_set = set()
                cursor = root
                while cursor is not None:
                    # Freeze membership overrides horizontal mode — stop spine walk at frozen node
                    # (unless it is the root itself, which may be the block root).
                    if id(cursor) in all_member_ids and id(cursor) != id(root):
                        break
                    cursor_state = node_layout_state.read_node_state(cursor)
                    if cursor_state.get("mode") != "horizontal":
                        break
                    replay_spine_set.add(id(cursor))
                    cursor = cursor.input(0)
                # Compute starting position for the chain.
                # If the ancestor walk found a different (upstream) root, anchor the chain
                # above the originally selected downstream node so the layout is
                # positioned correctly relative to the consumer, not D's scrambled coords.
                if root is not original_selected_root:
                    step_x = int(
                        current_prefs.get("horizontal_subtree_gap") * root_scheme_multiplier
                    )
                    # Walk the already-built replay_spine_set to compute full leftward extent.
                    # Each spine node beyond the root (index 1 onward) advances the chain left by
                    # step_x + that node's width.  spine_x must account for this entire extent so
                    # the leftmost spine node still clears the consumer's right edge with a clean
                    # gap. Note: left_extents (side-subtree widths) are treated as out-of-scope
                    # here —
                    # this fix addresses primary spine-node overlap; side-subtree overlap is a
                    # secondary edge case.
                    spine_nodes_ordered = []
                    cursor = root
                    while cursor is not None and id(cursor) in replay_spine_set:
                        spine_nodes_ordered.append(cursor)
                        cursor = cursor.input(0)
                    leftward_extent = sum(
                        step_x + spine_nodes_ordered[i].screenWidth()
                        for i in range(1, len(spine_nodes_ordered))
                    )
                    consumer = original_selected_root
                    loose_gap_multiplier = node_layout_prefs.prefs_singleton.get(
                        "loose_gap_multiplier"
                    )
                    dot_gap = int(loose_gap_multiplier * root_scheme_multiplier * snap_threshold)
                    spine_x = (
                        consumer.xpos() + consumer.screenWidth() + step_x + leftward_extent
                    )
                    spine_y = consumer.ypos() - dot_gap - root.screenHeight()
                else:
                    # root IS the originally selected node.  Find its downstream consumer
                    # (the node wired to root, or — on replay — wired to the output dot that
                    # sits between root and the consumer) so the chain can be anchored at the
                    # correct position relative to the consumer.
                    step_x = int(
                        current_prefs.get("horizontal_subtree_gap") * root_scheme_multiplier
                    )
                    loose_gap_multiplier = node_layout_prefs.prefs_singleton.get(
                        "loose_gap_multiplier"
                    )
                    dot_gap = int(loose_gap_multiplier * root_scheme_multiplier * snap_threshold)
                    all_group_nodes = (
                        current_group.nodes() if current_group is not None else nuke.allNodes()
                    )
                    downstream_consumer = None
                    replay_output_dot = None
                    for _candidate in all_group_nodes:
                        if _candidate.knob(_OUTPUT_DOT_KNOB_NAME) is not None:
                            if (
                                _candidate.input(0) is not None
                                and id(_candidate.input(0)) == id(root)
                            ):
                                replay_output_dot = _candidate
                        elif downstream_consumer is None:
                            for _slot in range(_candidate.inputs()):
                                if (
                                    _candidate.input(_slot) is not None
                                    and id(_candidate.input(_slot)) == id(root)
                                ):
                                    downstream_consumer = _candidate
                                    break
                    if downstream_consumer is None and replay_output_dot is not None:
                        for _candidate in all_group_nodes:
                            if (
                                _candidate.knob(_OUTPUT_DOT_KNOB_NAME) is None
                                and downstream_consumer is None
                            ):
                                for _slot in range(_candidate.inputs()):
                                    if (
                                        _candidate.input(_slot) is not None
                                        and id(_candidate.input(_slot)) == id(replay_output_dot)
                                    ):
                                        downstream_consumer = _candidate
                                        break
                    if downstream_consumer is not None:
                        spine_nodes_ordered = []
                        cursor = root
                        while cursor is not None and id(cursor) in replay_spine_set:
                            spine_nodes_ordered.append(cursor)
                            cursor = cursor.input(0)
                        leftward_extent = sum(
                            step_x + spine_nodes_ordered[i].screenWidth()
                            for i in range(1, len(spine_nodes_ordered))
                        )
                        spine_x = (
                            downstream_consumer.xpos()
                            + downstream_consumer.screenWidth()
                            + step_x + leftward_extent
                        )
                        spine_y = downstream_consumer.ypos() - dot_gap - root.screenHeight()
                    else:
                        spine_x = root.xpos()
                        spine_y = root.ypos()
                place_subtree_horizontal(
                    root, spine_x, spine_y, snap_threshold, node_count,
                    scheme_multiplier=root_scheme_multiplier,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                    current_prefs=current_prefs,
                    current_group=current_group,
                    memo=memo,
                    spine_set=replay_spine_set,
                    side_layout_mode="recursive",
                    dimension_overrides=dimension_overrides,
                )

                # Fix A: place-then-measure-then-shift clearance.
                # After place_subtree_horizontal returns, compute the actual leftmost extent of
                # the placed chain (spine + side subtrees).  If that extent is closer to the
                # consumer's right edge than horizontal_subtree_gap, translate the entire chain
                # rightward by the deficit so the gap invariant is restored.
                _chain_nodes_fix_a = collect_subtree_nodes(root)
                _actual_left = min(chain_node.xpos() for chain_node in _chain_nodes_fix_a)
                _horizontal_gap = current_prefs.get("horizontal_subtree_gap")
                if root is not original_selected_root:
                    _required_left = (
                        original_selected_root.xpos()
                        + original_selected_root.screenWidth()
                        + _horizontal_gap
                    )
                    _clearance_deficit = _required_left - _actual_left
                    if _clearance_deficit > 0:
                        for chain_node in _chain_nodes_fix_a:
                            chain_node.setXpos(chain_node.xpos() + _clearance_deficit)
                elif downstream_consumer is not None:
                    _required_left = (
                        downstream_consumer.xpos()
                        + downstream_consumer.screenWidth()
                        + _horizontal_gap
                    )
                    _clearance_deficit = _required_left - _actual_left
                    if _clearance_deficit > 0:
                        for chain_node in _chain_nodes_fix_a:
                            chain_node.setXpos(chain_node.xpos() + _clearance_deficit)

                _place_output_dot_for_horizontal_root(
                    root, current_group, snap_threshold, root_scheme_multiplier
                )

                # Fix B: compute the full horizontal chain bbox (including output dot, now placed)
                # so Phase 2 can clamp its X-anchor and avoid landing inside the chain's extent.
                _chain_all_nodes_fix_b = collect_subtree_nodes(root)
                for _fix_b_slot in range(original_selected_root.inputs()):
                    _fix_b_inp = original_selected_root.input(_fix_b_slot)
                    if (
                        _fix_b_inp is not None
                        and _fix_b_inp.knob(_OUTPUT_DOT_KNOB_NAME) is not None
                    ):
                        _chain_all_nodes_fix_b.append(_fix_b_inp)
                _chain_bbox = compute_node_bounding_box(_chain_all_nodes_fix_b)
                _chain_left_for_phase2 = _chain_bbox[0] if _chain_bbox is not None else None

                # Phase 2: when a vertical consumer (original_selected_root) triggered the
                # horizontal layout above, also run the standard vertical layout on that
                # consumer to correctly position any non-horizontal inputs it may have.
                # The horizontal block nodes are excluded from the vertical pass so they
                # are not moved from the positions set by Phase 1.
                if root is not original_selected_root:
                    horizontal_block_node_ids = {id(n) for n in collect_subtree_nodes(root)}
                    # Include the output dot in the exclusion set so place_subtree does
                    # not recurse into the horizontal chain through it.
                    for _slot in range(original_selected_root.inputs()):
                        _inp = original_selected_root.input(_slot)
                        if _inp is not None and _inp.knob(_OUTPUT_DOT_KNOB_NAME) is not None:
                            horizontal_block_node_ids.add(id(_inp))
                    # vertical_filter = every node in the original upstream tree that is
                    # NOT part of the horizontal block.
                    vertical_filter = set(
                        n for n in subtree_nodes_for_count
                        if id(n) not in horizontal_block_node_ids
                    )
                    consumer_scheme_multiplier = per_node_scheme.get(
                        id(original_selected_root), current_prefs.get("normal_multiplier")
                    )
                    if vertical_filter:
                        memo_phase2 = {}
                        phase2_w, _, _ = compute_dims(
                            original_selected_root, memo_phase2, snap_threshold, node_count,
                            node_filter=vertical_filter,
                            scheme_multiplier=consumer_scheme_multiplier,
                            per_node_h_scale=per_node_h_scale,
                            per_node_v_scale=per_node_v_scale,
                            dimension_overrides=dimension_overrides,
                        )
                        # Clamp phase2_anchor_x so Phase 2 subtree right extent doesn't enter
                        # the horizontal chain bbox.
                        # place_subtree places the root at phase2_anchor_x and side inputs step
                        # rightward from the root's right edge.  The actual rightmost extent of
                        # the Phase 2 subtree is therefore phase2_anchor_x + phase2_w.
                        # Require: phase2_anchor_x + phase2_w < chain_left - horizontal_subtree_gap
                        # (strictly less — the chain gap must not be eaten by Phase 2 nodes)
                        phase2_anchor_x = original_selected_root.xpos()
                        if _chain_left_for_phase2 is not None:
                            _max_right_for_phase2 = (
                                _chain_left_for_phase2
                                - current_prefs.get("horizontal_subtree_gap")
                            )
                            _phase2_rightmost = phase2_anchor_x + phase2_w
                            if _phase2_rightmost >= _max_right_for_phase2:
                                phase2_anchor_x = _max_right_for_phase2 - phase2_w - 1
                        place_subtree(
                            original_selected_root,
                            phase2_anchor_x, original_selected_root.ypos(),
                            memo_phase2, snap_threshold, node_count,
                            node_filter=vertical_filter,
                            scheme_multiplier=consumer_scheme_multiplier,
                            per_node_h_scale=per_node_h_scale,
                            per_node_v_scale=per_node_v_scale,
                        )
                        # Fix C: push Phase 2 vertical input nodes above the horizontal
                        # chain's topmost extent.  place_subtree starts Phase 2 inputs
                        # at original_selected_root.ypos() - gap, which can land inside
                        # the chain's Y band when the chain has side subtrees that extend
                        # above spine_y.  Shift all Phase 2 non-root nodes upward so
                        # their collective bottom sits at chain_top - side_vertical_gap.
                        if _chain_bbox is not None:
                            _chain_top_fix_c = _chain_bbox[1]
                            _phase2_side_gap = current_prefs.get("horizontal_side_vertical_gap")
                            _phase2_input_nodes = [
                                phase2_node for phase2_node in vertical_filter
                                if id(phase2_node) != id(original_selected_root)
                            ]
                            if _phase2_input_nodes:
                                _phase2_subtree_bottom = max(
                                    phase2_node.ypos() + phase2_node.screenHeight()
                                    for phase2_node in _phase2_input_nodes
                                )
                                _phase2_required_ceiling = _chain_top_fix_c - _phase2_side_gap
                                if _phase2_subtree_bottom > _phase2_required_ceiling:
                                    _phase2_shift_up = (
                                        _phase2_subtree_bottom - _phase2_required_ceiling
                                    )
                                    for phase2_node in _phase2_input_nodes:
                                        phase2_node.setYpos(phase2_node.ypos() - _phase2_shift_up)
            else:
                # Build the vertical node filter excluding non-root freeze block members.
                # Non-root members will be repositioned via offset after place_subtree.
                if all_non_root_ids:
                    vertical_freeze_filter = set(
                        n for n in subtree_nodes_for_count
                        if id(n) not in all_non_root_ids
                    )
                else:
                    vertical_freeze_filter = None
                compute_dims(
                    root, memo, snap_threshold, node_count,
                    node_filter=vertical_freeze_filter,
                    scheme_multiplier=root_scheme_multiplier,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                    dimension_overrides=dimension_overrides,
                )
                place_subtree(
                    root, root.xpos(), root.ypos(), memo, snap_threshold, node_count,
                    node_filter=vertical_freeze_filter,
                    scheme_multiplier=root_scheme_multiplier,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                    dimension_overrides=dimension_overrides,
                )

            # --- Apply freeze block offsets after place_subtree (FRZE-06) ---
            for block in freeze_blocks:
                block.restore_positions()

            # --- Post-pass: layout non-frozen nodes upstream of freeze blocks (Gap 1 fix) ---
            if freeze_blocks:
                for block in freeze_blocks:
                    external_inputs = block.get_external_inputs(get_inputs)
                    for entry_node, connecting_member in external_inputs:
                        upstream_subtree = collect_subtree_nodes(entry_node)
                        upstream_filter = set(upstream_subtree)
                        upstream_count = len(upstream_subtree)
                        upstream_memo = {}
                        entry_dims = compute_dims(
                            entry_node, upstream_memo, snap_threshold, upstream_count,
                            upstream_filter,
                            scheme_multiplier=per_node_scheme.get(
                                id(entry_node), current_prefs.get("normal_multiplier")
                            ),
                            per_node_h_scale=per_node_h_scale,
                            per_node_v_scale=per_node_v_scale,
                            dimension_overrides=dimension_overrides,
                        )
                        entry_x = _center_x(
                            entry_node.screenWidth(),
                            connecting_member.xpos(),
                            connecting_member.screenWidth(),
                        )
                        raw_gap = vertical_gap_between(
                            entry_node, connecting_member, snap_threshold,
                            scheme_multiplier=per_node_scheme.get(
                                id(entry_node), current_prefs.get("normal_multiplier")
                            ),
                        )
                        entry_y = (
                            connecting_member.ypos()
                            - max(snap_threshold - 1, raw_gap)
                            - entry_dims[1]
                        )
                        place_subtree(
                            entry_node, entry_x, entry_y,
                            upstream_memo, snap_threshold, upstream_count,
                            upstream_filter,
                            scheme_multiplier=per_node_scheme.get(
                                id(entry_node), current_prefs.get("normal_multiplier")
                            ),
                            per_node_h_scale=per_node_h_scale,
                            per_node_v_scale=per_node_v_scale,
                            dimension_overrides=dimension_overrides,
                        )

            # Capture final state from the originally selected node so all touched nodes
            # (horizontal chain, output dot, and consumer's vertical inputs) are included.
            final_subtree_nodes = collect_subtree_nodes(
                original_selected_root if root_mode == "horizontal" else root
            )

            # State write-back: record per-node scheme and mode on every layout-touched node.
            # For horizontal replay: spine nodes keep mode="horizontal"; side input subtrees
            # (laid out vertically) get mode="vertical".
            for state_node in final_subtree_nodes:
                stored_state = node_layout_state.read_node_state(state_node)
                node_scheme_multiplier = per_node_scheme.get(
                    id(state_node), current_prefs.get("normal_multiplier")
                )
                stored_state["scheme"] = node_layout_state.multiplier_to_scheme_name(
                    node_scheme_multiplier, current_prefs
                )
                if root_mode == "horizontal" and replay_spine_set is not None:
                    stored_state["mode"] = (
                        "horizontal" if id(state_node) in replay_spine_set else "vertical"
                    )
                else:
                    stored_state["mode"] = "vertical"
                # h_scale and v_scale are NOT reset by re-layout — preserve existing values
                node_layout_state.write_node_state(state_node, stored_state)

            final_subtree_node_ids = {id(n) for n in final_subtree_nodes}
            # Include freeze block members in bbox_after and the skip-set so
            # push_nodes_to_make_room sees the full footprint and doesn't push
            # the block's own members.
            all_bbox_after_nodes = list(final_subtree_nodes)
            for block in freeze_blocks:
                for member in block.members:
                    if id(member) not in final_subtree_node_ids:
                        all_bbox_after_nodes.append(member)
                        final_subtree_node_ids.add(id(member))
            bbox_after = compute_node_bounding_box(all_bbox_after_nodes)

            if bbox_before is not None and bbox_after is not None:
                push_nodes_to_make_room(
                    final_subtree_node_ids, bbox_before, bbox_after,
                    current_group=current_group,
                    freeze_blocks=freeze_blocks,
                )
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def find_selection_roots(selected_nodes):
    """Return the most-downstream selected nodes — those that no other selected node takes
    as an input."""
    selected_set = set(id(n) for n in selected_nodes)
    nodes_used_as_input = set()
    for node in selected_nodes:
        for inp in get_inputs(node):
            if id(inp) in selected_set:
                nodes_used_as_input.add(id(inp))
    return [n for n in selected_nodes if id(n) not in nodes_used_as_input]


def layout_selected(scheme_multiplier=None):
    global _TOOLBAR_FOLDER_MAP
    _TOOLBAR_FOLDER_MAP = None
    _clear_color_cache()
    current_group = nuke.lastHitGroup()    # MUST be the first Nuke API call
    selected_nodes = nuke.selectedNodes()
    if len(selected_nodes) < 2:
        return  # nothing to lay out relative to each other

    nuke.Undo.name("Layout Selected")
    nuke.Undo.begin()
    try:
        with current_group:
            node_filter = set(selected_nodes)
            # --- Freeze group preprocessing (FRZE-04, FRZE-05, FRZE-06) ---
            expanded_selection = _expand_scope_for_freeze_groups(list(node_filter), current_group)
            node_filter = set(expanded_selection)
            selected_nodes = list(node_filter)  # update for downstream use
            freeze_group_map, node_freeze_uuid = _detect_freeze_groups(list(node_filter))
            freeze_blocks, dimension_overrides, all_non_root_ids, all_member_ids = (
                _build_freeze_blocks(freeze_group_map)
            )

            # Capture bbox BEFORE filtering so it includes non-root freeze members.
            bbox_before = compute_node_bounding_box(selected_nodes)

            # Remove non-root block members from node_filter so place_subtree skips them.
            if all_non_root_ids:
                node_filter = {n for n in node_filter if id(n) not in all_non_root_ids}
                selected_nodes = [n for n in selected_nodes if id(n) not in all_non_root_ids]

            roots = find_selection_roots(selected_nodes)
            roots.sort(key=lambda n: n.xpos())

            node_count = len(selected_nodes)

            # Per-node scheme resolution (replaces the old resolved_scheme_multiplier block)
            current_prefs = node_layout_prefs.prefs_singleton
            per_node_scheme = {}  # maps id(node) -> float scheme multiplier
            per_node_h_scale = {}  # maps id(node) -> float h_scale
            per_node_v_scale = {}  # maps id(node) -> float v_scale
            for sel_node in selected_nodes:
                if scheme_multiplier is not None:
                    per_node_scheme[id(sel_node)] = scheme_multiplier
                else:
                    stored_state = node_layout_state.read_node_state(sel_node)
                    per_node_scheme[id(sel_node)] = node_layout_state.scheme_name_to_multiplier(
                        stored_state["scheme"], current_prefs
                    )
                # h_scale/v_scale always come from stored state (independent of scheme override)
                scale_state = node_layout_state.read_node_state(sel_node)
                per_node_h_scale[id(sel_node)] = scale_state["h_scale"]
                per_node_v_scale[id(sel_node)] = scale_state["v_scale"]

            snap_threshold = get_dag_snap_threshold()
            memo = {}
            placed_bboxes = []  # list of (left, top, right, bottom) for already-placed trees
            # Maps id(root) -> spine_set (set of node ids) for roots that replay horizontal.
            spine_sets_by_root = {}
            for root in roots:
                original_selected_root = root
                root_stored_state = node_layout_state.read_node_state(root)
                root_mode = root_stored_state.get("mode", "vertical")

                # If the selected node is downstream of a horizontal chain (its own mode is
                # vertical), BFS across all input slots to find the most-downstream ancestor
                # stored as horizontal. That ancestor becomes the effective replay root.
                if root_mode != "horizontal":
                    if not _hides_inputs(root):
                        bfs_queue = [root.input(slot) for slot in range(root.inputs())
                                     if root.input(slot) is not None]
                    else:
                        bfs_queue = []
                    bfs_visited = {id(root)}
                    bfs_index = 0
                    while bfs_index < len(bfs_queue):
                        bfs_cursor = bfs_queue[bfs_index]
                        bfs_index += 1
                        if id(bfs_cursor) in bfs_visited:
                            continue
                        bfs_visited.add(id(bfs_cursor))
                        # Frozen nodes must not become horizontal replay roots — skip as root
                        # candidate but continue BFS through their inputs so non-frozen horizontal
                        # nodes upstream can still be found.
                        if id(bfs_cursor) in all_member_ids:
                            if not _hides_inputs(bfs_cursor):
                                for bfs_slot in range(bfs_cursor.inputs()):
                                    bfs_inp = bfs_cursor.input(bfs_slot)
                                    if bfs_inp is not None and id(bfs_inp) not in bfs_visited:
                                        bfs_queue.append(bfs_inp)
                            continue
                        if (
                            node_layout_state.read_node_state(bfs_cursor).get("mode")
                            == "horizontal"
                        ):
                            root = bfs_cursor
                            root_mode = "horizontal"
                            break
                        if not _hides_inputs(bfs_cursor):
                            for bfs_slot in range(bfs_cursor.inputs()):
                                bfs_inp = bfs_cursor.input(bfs_slot)
                                if bfs_inp is not None and id(bfs_inp) not in bfs_visited:
                                    bfs_queue.append(bfs_inp)

                root_scheme_multiplier = per_node_scheme.get(
                    id(root), current_prefs.get("normal_multiplier")
                )

                if root_mode == "horizontal":
                    # Build spine_set by walking input[0] and collecting consecutive
                    # nodes whose stored mode is "horizontal".
                    root_spine_set = set()
                    cursor = root
                    while cursor is not None:
                        # Freeze membership overrides horizontal mode — stop spine walk at frozen
                        # node (unless it is the root itself, which may be the block root).
                        if id(cursor) in all_member_ids and id(cursor) != id(root):
                            break
                        cursor_state = node_layout_state.read_node_state(cursor)
                        if cursor_state.get("mode") != "horizontal":
                            break
                        root_spine_set.add(id(cursor))
                        cursor = cursor.input(0)
                    spine_sets_by_root[id(root)] = root_spine_set
                    # Compute anchor position: if the ancestor walk rebound root to an
                    # upstream horizontal node, place the chain to the RIGHT of the
                    # originally selected downstream consumer at the consumer's Y level.
                    if root is not original_selected_root:
                        step_x = int(
                            current_prefs.get("horizontal_subtree_gap") * root_scheme_multiplier
                        )
                        # Walk the already-built root_spine_set to compute full leftward extent.
                        # Each spine node beyond the root (index 1 onward) advances the chain left
                        # by step_x + that node's width. spine_x must account for this entire
                        # extent so the leftmost spine node still clears the consumer's right edge.
                        # Note: left_extents (side-subtree widths) are treated as out-of-scope here
                        # — this fix addresses primary spine-node overlap; side-subtree overlap is a
                        # secondary edge case.
                        spine_nodes_ordered = []
                        cursor = root
                        while cursor is not None and id(cursor) in root_spine_set:
                            spine_nodes_ordered.append(cursor)
                            cursor = cursor.input(0)
                        leftward_extent = sum(
                            step_x + spine_nodes_ordered[i].screenWidth()
                            for i in range(1, len(spine_nodes_ordered))
                        )
                        consumer = original_selected_root
                        loose_gap_multiplier = node_layout_prefs.prefs_singleton.get(
                            "loose_gap_multiplier"
                        )
                        dot_gap = int(
                            loose_gap_multiplier * root_scheme_multiplier * snap_threshold
                        )
                        spine_x = (
                            consumer.xpos() + consumer.screenWidth() + step_x + leftward_extent
                        )
                        spine_y = consumer.ypos() - dot_gap - root.screenHeight()
                    else:
                        # root IS the originally selected node.  Find its downstream consumer
                        # (wired to root directly, or — on replay — wired to the output dot)
                        # so the chain can be anchored correctly relative to the consumer.
                        step_x = int(
                            current_prefs.get("horizontal_subtree_gap") * root_scheme_multiplier
                        )
                        loose_gap_multiplier = node_layout_prefs.prefs_singleton.get(
                            "loose_gap_multiplier"
                        )
                        dot_gap = int(
                            loose_gap_multiplier * root_scheme_multiplier * snap_threshold
                        )
                        all_group_nodes = (
                            current_group.nodes()
                            if current_group is not None else nuke.allNodes()
                        )
                        downstream_consumer = None
                        replay_output_dot = None
                        for _candidate in all_group_nodes:
                            if _candidate.knob(_OUTPUT_DOT_KNOB_NAME) is not None:
                                if (
                                    _candidate.input(0) is not None
                                    and id(_candidate.input(0)) == id(root)
                                ):
                                    replay_output_dot = _candidate
                            elif downstream_consumer is None:
                                for _slot in range(_candidate.inputs()):
                                    if (
                                        _candidate.input(_slot) is not None
                                        and id(_candidate.input(_slot)) == id(root)
                                    ):
                                        downstream_consumer = _candidate
                                        break
                        if downstream_consumer is None and replay_output_dot is not None:
                            for _candidate in all_group_nodes:
                                if (
                                    _candidate.knob(_OUTPUT_DOT_KNOB_NAME) is None
                                    and downstream_consumer is None
                                ):
                                    for _slot in range(_candidate.inputs()):
                                        if (
                                            _candidate.input(_slot) is not None
                                            and id(_candidate.input(_slot)) == id(replay_output_dot)
                                        ):
                                            downstream_consumer = _candidate
                                            break
                        if downstream_consumer is not None:
                            spine_nodes_ordered = []
                            cursor = root
                            while cursor is not None and id(cursor) in root_spine_set:
                                spine_nodes_ordered.append(cursor)
                                cursor = cursor.input(0)
                            leftward_extent = sum(
                                step_x + spine_nodes_ordered[i].screenWidth()
                                for i in range(1, len(spine_nodes_ordered))
                            )
                            spine_x = (
                                downstream_consumer.xpos()
                                + downstream_consumer.screenWidth()
                                + step_x + leftward_extent
                            )
                            spine_y = downstream_consumer.ypos() - dot_gap - root.screenHeight()
                        else:
                            spine_x = root.xpos()
                            spine_y = root.ypos()
                    place_subtree_horizontal(
                        root, spine_x, spine_y, snap_threshold, node_count,
                        scheme_multiplier=root_scheme_multiplier,
                        per_node_h_scale=per_node_h_scale,
                        per_node_v_scale=per_node_v_scale,
                        current_prefs=current_prefs,
                        current_group=current_group,
                        memo=memo,
                        spine_set=root_spine_set,
                        side_layout_mode="recursive",
                        dimension_overrides=dimension_overrides,
                    )

                    # Fix A: place-then-measure-then-shift clearance.
                    # After place_subtree_horizontal returns, compute the actual leftmost extent of
                    # the placed chain (spine + side subtrees).  If that extent is closer to the
                    # consumer's right edge than horizontal_subtree_gap, translate the entire chain
                    # rightward by the deficit so the gap invariant is restored.
                    _chain_nodes_fix_a = collect_subtree_nodes(root)
                    _actual_left = min(chain_node.xpos() for chain_node in _chain_nodes_fix_a)
                    _horizontal_gap = current_prefs.get("horizontal_subtree_gap")
                    if root is not original_selected_root:
                        _required_left = (
                            original_selected_root.xpos()
                            + original_selected_root.screenWidth()
                            + _horizontal_gap
                        )
                        _clearance_deficit = _required_left - _actual_left
                        if _clearance_deficit > 0:
                            for chain_node in _chain_nodes_fix_a:
                                chain_node.setXpos(chain_node.xpos() + _clearance_deficit)
                    elif downstream_consumer is not None:
                        _required_left = (
                            downstream_consumer.xpos()
                            + downstream_consumer.screenWidth()
                            + _horizontal_gap
                        )
                        _clearance_deficit = _required_left - _actual_left
                        if _clearance_deficit > 0:
                            for chain_node in _chain_nodes_fix_a:
                                chain_node.setXpos(chain_node.xpos() + _clearance_deficit)

                    _place_output_dot_for_horizontal_root(
                    root, current_group, snap_threshold, root_scheme_multiplier
                )

                    # Fix B: compute the full horizontal chain bbox (including output dot, now
                    # placed) so Phase 2 can clamp its X-anchor and avoid landing inside the
                    # chain's extent.
                    _chain_all_nodes_fix_b = collect_subtree_nodes(root)
                    for _fix_b_slot in range(original_selected_root.inputs()):
                        _fix_b_inp = original_selected_root.input(_fix_b_slot)
                        if (
                            _fix_b_inp is not None
                            and _fix_b_inp.knob(_OUTPUT_DOT_KNOB_NAME) is not None
                        ):
                            _chain_all_nodes_fix_b.append(_fix_b_inp)
                    _chain_bbox = compute_node_bounding_box(_chain_all_nodes_fix_b)
                    _chain_left_for_phase2 = _chain_bbox[0] if _chain_bbox is not None else None

                    # Phase 2: when a vertical consumer triggered the horizontal layout,
                    # also run the standard vertical layout on that consumer so that any
                    # non-horizontal inputs are correctly positioned.
                    if root is not original_selected_root:
                        horizontal_block_node_ids = {id(n) for n in collect_subtree_nodes(root)}
                        for _slot in range(original_selected_root.inputs()):
                            _inp = original_selected_root.input(_slot)
                            if _inp is not None and _inp.knob(_OUTPUT_DOT_KNOB_NAME) is not None:
                                horizontal_block_node_ids.add(id(_inp))
                        vertical_filter = set(
                            n for n in node_filter
                            if id(n) not in horizontal_block_node_ids
                        )
                        consumer_scheme_multiplier = per_node_scheme.get(
                            id(original_selected_root), current_prefs.get("normal_multiplier")
                        )
                        if vertical_filter:
                            memo_phase2 = {}
                            phase2_w, _, _ = compute_dims(
                                original_selected_root, memo_phase2, snap_threshold, node_count,
                                node_filter=vertical_filter,
                                scheme_multiplier=consumer_scheme_multiplier,
                                per_node_h_scale=per_node_h_scale,
                                per_node_v_scale=per_node_v_scale,
                                dimension_overrides=dimension_overrides,
                            )
                            # Clamp phase2_anchor_x so Phase 2 subtree right extent doesn't enter
                            # the horizontal chain bbox.
                            # place_subtree places the root at phase2_anchor_x and side inputs step
                            # rightward from the root's right edge.  The actual rightmost extent of
                            # the Phase 2 subtree is therefore phase2_anchor_x + phase2_w.
                            # Require: phase2_anchor_x + phase2_w < chain_left
                            # - horizontal_subtree_gap
                            # (strictly less — the chain gap must not be eaten by Phase 2 nodes)
                            phase2_anchor_x = original_selected_root.xpos()
                            if _chain_left_for_phase2 is not None:
                                _max_right_for_phase2 = (
                                    _chain_left_for_phase2
                                    - current_prefs.get("horizontal_subtree_gap")
                                )
                                _phase2_rightmost = phase2_anchor_x + phase2_w
                                if _phase2_rightmost >= _max_right_for_phase2:
                                    phase2_anchor_x = _max_right_for_phase2 - phase2_w - 1
                            place_subtree(
                                original_selected_root,
                                phase2_anchor_x, original_selected_root.ypos(),
                                memo_phase2, snap_threshold, node_count,
                                node_filter=vertical_filter,
                                scheme_multiplier=consumer_scheme_multiplier,
                                per_node_h_scale=per_node_h_scale,
                                per_node_v_scale=per_node_v_scale,
                            )
                            # Fix C (parity): same upward shift as layout_upstream.
                            if _chain_bbox is not None:
                                _chain_top_fix_c = _chain_bbox[1]
                                _phase2_side_gap = current_prefs.get("horizontal_side_vertical_gap")
                                _phase2_input_nodes = [
                                    phase2_node for phase2_node in vertical_filter
                                    if id(phase2_node) != id(original_selected_root)
                                ]
                                if _phase2_input_nodes:
                                    _phase2_subtree_bottom = max(
                                        phase2_node.ypos() + phase2_node.screenHeight()
                                        for phase2_node in _phase2_input_nodes
                                    )
                                    _phase2_required_ceiling = _chain_top_fix_c - _phase2_side_gap
                                    if _phase2_subtree_bottom > _phase2_required_ceiling:
                                        _phase2_shift_up = (
                                        _phase2_subtree_bottom - _phase2_required_ceiling
                                    )
                                        for phase2_node in _phase2_input_nodes:
                                            phase2_node.setYpos(
                                                phase2_node.ypos() - _phase2_shift_up
                                            )
                else:
                    insert_dot_nodes(root, node_filter=node_filter)
                    tree_width, tree_height, _ = compute_dims(
                        root, memo, snap_threshold, node_count,
                        node_filter=node_filter,
                        scheme_multiplier=root_scheme_multiplier,
                        per_node_h_scale=per_node_h_scale,
                        per_node_v_scale=per_node_v_scale,
                        dimension_overrides=dimension_overrides,
                    )

                    tree_bottom = root.ypos() + root.screenHeight()
                    tree_top = tree_bottom - tree_height

                    # Resolve start_x: push right if Y ranges overlap with any already-placed tree.
                    start_x = root.xpos()
                    for _placed_left, placed_top, placed_right, placed_bottom in placed_bboxes:
                        if tree_top < placed_bottom and tree_bottom > placed_top:  # Y overlap
                            horizontal_clearance = current_prefs.get("horizontal_subtree_gap")
                            start_x = max(start_x, placed_right + horizontal_clearance)

                    place_subtree(
                        root, start_x, root.ypos(), memo, snap_threshold, node_count,
                        node_filter=node_filter,
                        scheme_multiplier=root_scheme_multiplier,
                        per_node_h_scale=per_node_h_scale,
                        per_node_v_scale=per_node_v_scale,
                        dimension_overrides=dimension_overrides,
                    )
                    placed_bboxes.append((start_x, tree_top, start_x + tree_width, tree_bottom))

            # Aggregate all horizontal spine node ids across all roots.
            all_horizontal_spine_ids = set()
            for root_spine_set in spine_sets_by_root.values():
                all_horizontal_spine_ids.update(root_spine_set)

            # State write-back: record per-node scheme and mode on every layout-touched node.
            # Spine nodes keep mode="horizontal"; all others get mode="vertical".
            all_touched_nodes = set()
            for state_root in roots:
                all_touched_nodes.update(collect_subtree_nodes(state_root, node_filter=node_filter))
            for state_node in all_touched_nodes:
                stored_state = node_layout_state.read_node_state(state_node)
                node_scheme_multiplier = per_node_scheme.get(
                    id(state_node), current_prefs.get("normal_multiplier")
                )
                stored_state["scheme"] = node_layout_state.multiplier_to_scheme_name(
                    node_scheme_multiplier, current_prefs
                )
                stored_state["mode"] = (
                    "horizontal" if id(state_node) in all_horizontal_spine_ids else "vertical"
                )
                node_layout_state.write_node_state(state_node, stored_state)

            # --- Apply freeze block offsets after all place_subtree calls (FRZE-06) ---
            for block in freeze_blocks:
                block.restore_positions()

            # --- Post-pass: layout non-frozen nodes upstream of freeze blocks (Gap 1 fix) ---
            if freeze_blocks:
                # Build scope_ids for filtering external inputs to selected scope.
                scope_ids = {id(n) for n in node_filter} | {id(n) for n in selected_nodes}
                scope_ids |= all_member_ids
                for block in freeze_blocks:
                    external_inputs = block.get_external_inputs(get_inputs)
                    for entry_node, connecting_member in external_inputs:
                        if id(entry_node) not in scope_ids:
                            continue
                        upstream_subtree = collect_subtree_nodes(entry_node)
                        upstream_filter = {
                            n for n in upstream_subtree if id(n) in scope_ids
                        }
                        if not upstream_filter:
                            continue
                        upstream_count = len(upstream_filter)
                        upstream_memo = {}
                        entry_dims = compute_dims(
                            entry_node, upstream_memo, snap_threshold, upstream_count,
                            upstream_filter,
                            scheme_multiplier=per_node_scheme.get(
                                id(entry_node), current_prefs.get("normal_multiplier")
                            ),
                            per_node_h_scale=per_node_h_scale,
                            per_node_v_scale=per_node_v_scale,
                            dimension_overrides=dimension_overrides,
                        )
                        entry_x = _center_x(
                            entry_node.screenWidth(),
                            connecting_member.xpos(),
                            connecting_member.screenWidth(),
                        )
                        raw_gap = vertical_gap_between(
                            entry_node, connecting_member, snap_threshold,
                            scheme_multiplier=per_node_scheme.get(
                                id(entry_node), current_prefs.get("normal_multiplier")
                            ),
                        )
                        entry_y = (
                            connecting_member.ypos()
                            - max(snap_threshold - 1, raw_gap)
                            - entry_dims[1]
                        )
                        place_subtree(
                            entry_node, entry_x, entry_y,
                            upstream_memo, snap_threshold, upstream_count,
                            upstream_filter,
                            scheme_multiplier=per_node_scheme.get(
                                id(entry_node), current_prefs.get("normal_multiplier")
                            ),
                            per_node_h_scale=per_node_h_scale,
                            per_node_v_scale=per_node_v_scale,
                            dimension_overrides=dimension_overrides,
                        )

            # Collect all nodes actually touched by place_subtree, including newly created
            # routing Dot nodes that are absent from the original node_filter.  Using no
            # filter here mirrors layout_upstream's collect_subtree_nodes(root) call so
            # that newly inserted routing Dots land in the skip-set for
            # push_nodes_to_make_room and are never incorrectly displaced.
            final_selected_ids = set()
            all_final_nodes_dedup = {}  # id(node) -> node, for deduplication
            for layout_root in roots:
                for post_node in collect_subtree_nodes(layout_root):  # no filter
                    node_id = id(post_node)
                    final_selected_ids.add(node_id)
                    all_final_nodes_dedup[node_id] = post_node
            # Include freeze-excluded members in bbox_after so the full footprint is
            # captured, and add them to the skip-set so they aren't pushed by
            # push_nodes_to_make_room.
            for block in freeze_blocks:
                for member in block.members:
                    node_id = id(member)
                    if node_id not in final_selected_ids:
                        all_final_nodes_dedup[node_id] = member
                        final_selected_ids.add(node_id)
            all_final_nodes = list(all_final_nodes_dedup.values())
            bbox_after = compute_node_bounding_box(all_final_nodes)

            if bbox_before and bbox_after:
                push_nodes_to_make_room(
                    final_selected_ids, bbox_before, bbox_after,
                    current_group=current_group,
                    freeze_blocks=freeze_blocks,
                )
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


SHRINK_FACTOR = 0.8
EXPAND_FACTOR = 1.25
_last_scale_fn = None   # set by every scale wrapper; called by repeat_last_scale()


def layout_upstream_compact():
    layout_upstream(scheme_multiplier=node_layout_prefs.prefs_singleton.get("compact_multiplier"))


def layout_selected_compact():
    layout_selected(scheme_multiplier=node_layout_prefs.prefs_singleton.get("compact_multiplier"))


def layout_upstream_loose():
    layout_upstream(scheme_multiplier=node_layout_prefs.prefs_singleton.get("loose_multiplier"))


def layout_selected_loose():
    layout_selected(scheme_multiplier=node_layout_prefs.prefs_singleton.get("loose_multiplier"))


def _layout_selected_horizontal_impl(scheme_multiplier, side_layout_mode, undo_label):
    """Shared implementation for layout_selected_horizontal and
    layout_selected_horizontal_place_only."""
    global _TOOLBAR_FOLDER_MAP
    _TOOLBAR_FOLDER_MAP = None
    _clear_color_cache()
    current_group = nuke.lastHitGroup()    # MUST be the first Nuke API call
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return

    nuke.Undo.name(undo_label)
    nuke.Undo.begin()
    try:
        with current_group:
            # --- Freeze group preprocessing (FRZE-04, FRZE-05) ---
            # Step 1: Expand selection for freeze groups that include selected nodes
            # (e.g., user selected a freeze member but not all siblings in the group).
            selected_nodes = _expand_scope_for_freeze_groups(selected_nodes, current_group)

            # Step 2: Build a wider detection scope that includes side-input subtrees of
            # the preliminary spine, so freeze groups that are entirely in side-input
            # subtrees (not in the user's spine selection) are also detected. These groups
            # are handled by offset restoration; they are NOT added to selected_nodes or
            # spine_set, so they don't interfere with the spine walk.
            _prelim_spine_ids = {id(n) for n in selected_nodes}
            _prelim_roots = find_selection_roots(selected_nodes)
            _side_input_nodes = []
            for _prelim_root in _prelim_roots:
                _cursor = _prelim_root
                while _cursor is not None:
                    if id(_cursor) not in _prelim_spine_ids:
                        break
                    for _slot in range(1, _cursor.inputs()):
                        _side = _cursor.input(_slot)
                        if _side is not None:
                            _side_input_nodes.extend(collect_subtree_nodes(_side))
                    _next = _cursor.input(0)
                    if _next is not None and id(_next) not in _prelim_spine_ids:
                        _side_input_nodes.extend(collect_subtree_nodes(_next))
                    _cursor = _next

            _detection_seen_ids = {id(n) for n in selected_nodes}
            _detection_scope = list(selected_nodes)
            for _extra in _side_input_nodes:
                if id(_extra) not in _detection_seen_ids:
                    _detection_seen_ids.add(id(_extra))
                    _detection_scope.append(_extra)
            _detection_scope = _expand_scope_for_freeze_groups(_detection_scope, current_group)
            freeze_group_map, node_freeze_uuid = _detect_freeze_groups(_detection_scope)

            # --- Freeze block rigid positioning setup (FRZE-06) ---
            freeze_blocks, dimension_overrides, all_non_root_ids, all_member_ids = (
                _build_freeze_blocks(freeze_group_map)
            )

            # All selected nodes (including non-root freeze members) form the spine_set so the
            # spine walk can traverse through freeze group members uninterrupted. Non-root members
            # will be repositioned by offset restoration after place_subtree_horizontal runs.
            spine_set = {id(n) for n in selected_nodes}
            roots = find_selection_roots(selected_nodes)

            bbox_before = compute_node_bounding_box(selected_nodes)
            node_count = len(selected_nodes)

            current_prefs = node_layout_prefs.prefs_singleton
            per_node_scheme = {}
            per_node_h_scale = {}
            per_node_v_scale = {}
            for sel_node in selected_nodes:
                if scheme_multiplier is not None:
                    per_node_scheme[id(sel_node)] = scheme_multiplier
                else:
                    stored_state = node_layout_state.read_node_state(sel_node)
                    per_node_scheme[id(sel_node)] = node_layout_state.scheme_name_to_multiplier(
                        stored_state["scheme"], current_prefs
                    )
                scale_state = node_layout_state.read_node_state(sel_node)
                per_node_h_scale[id(sel_node)] = scale_state["h_scale"]
                per_node_v_scale[id(sel_node)] = scale_state["v_scale"]

            snap_threshold = get_dag_snap_threshold()
            memo = {}

            for root in roots:
                root_scheme_multiplier = per_node_scheme.get(
                    id(root), current_prefs.get("normal_multiplier")
                )
                place_subtree_horizontal(
                    root, root.xpos(), root.ypos(), snap_threshold, node_count,
                    scheme_multiplier=root_scheme_multiplier,
                    per_node_h_scale=per_node_h_scale,
                    per_node_v_scale=per_node_v_scale,
                    current_prefs=current_prefs,
                    current_group=current_group,
                    memo=memo,
                    spine_set=spine_set,
                    side_layout_mode=side_layout_mode,
                    dimension_overrides=dimension_overrides,
                )
                _place_output_dot_for_horizontal_root(
                    root, current_group, snap_threshold, root_scheme_multiplier
                )

            # --- Apply freeze block offsets after horizontal placement (FRZE-06) ---
            for block in freeze_blocks:
                block.restore_positions()

            # State write-back: both recursive and place_only write mode='horizontal'
            # so that subsequent layout_upstream/layout_selected replay horizontal mode.
            # Non-root freeze members are excluded — they don't participate in the spine.
            for state_node in selected_nodes:
                if id(state_node) in all_non_root_ids:
                    continue
                stored_state = node_layout_state.read_node_state(state_node)
                node_scheme_multiplier = per_node_scheme.get(
                    id(state_node), current_prefs.get("normal_multiplier")
                )
                stored_state["scheme"] = node_layout_state.multiplier_to_scheme_name(
                    node_scheme_multiplier, current_prefs
                )
                stored_state["mode"] = "horizontal"
                # h_scale and v_scale are NOT reset by re-layout — preserve existing values
                node_layout_state.write_node_state(state_node, stored_state)

            # Include freeze-excluded members in bbox_after so the full footprint
            # is captured, and add them to the skip-set.
            all_final_nodes = list(selected_nodes)
            for block in freeze_blocks:
                for member in block.members:
                    if id(member) not in spine_set:
                        all_final_nodes.append(member)
                        spine_set.add(id(member))
            bbox_after = compute_node_bounding_box(all_final_nodes)
            if bbox_before and bbox_after:
                push_nodes_to_make_room(spine_set, bbox_before, bbox_after, current_group)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def layout_selected_horizontal(scheme_multiplier=None):
    """Lay out the selected nodes as a horizontal spine, recursively laying out
    non-spine inputs vertically above each spine node.

    The selected nodes form the spine (root rightmost, ordered by graph topology).
    Any input of a spine node that is not itself a spine node has its full upstream
    subtree laid out vertically above that spine node.

    Writes mode='horizontal' to selected nodes so that subsequent layout_selected()
    calls replay the horizontal layout automatically (HORIZ-03 mode replay).
    """
    _layout_selected_horizontal_impl(scheme_multiplier, "recursive", "Layout Selected Horizontal")


def layout_selected_horizontal_place_only(scheme_multiplier=None):
    """Lay out the selected nodes as a horizontal spine, translating attached
    subtrees without re-laying them out internally.

    Identical to layout_selected_horizontal() in spine placement, but each non-spine
    subtree is moved as a rigid unit (all its nodes translated by the same delta)
    rather than having its internal layout recomputed.  This preserves the subtrees'
    existing internal structure while snapping their roots to the correct positions
    above their respective spine nodes.

    Writes mode='horizontal' to the selected (spine) nodes so that subsequent
    layout_upstream or layout_selected replays the horizontal mode automatically.
    """
    _layout_selected_horizontal_impl(
        scheme_multiplier, "place_only", "Layout Selected Horizontal (Place Only)"
    )


def _scale_selected_nodes(scale_factor, axis="both"):
    selected_nodes = nuke.selectedNodes()
    if len(selected_nodes) < 2:
        return
    # Anchor: the most downstream selected node, determined topologically.
    # Using max(ypos) fails when side inputs (e.g. Merge A input) are positioned
    # below their consumer — topology is the reliable way to find the root.
    roots = find_selection_roots(selected_nodes)
    anchor_node = max(roots, key=lambda n: (n.ypos(), -n.xpos()))
    snap_min = get_dag_snap_threshold() - 1
    anchor_center_x = anchor_node.xpos() + anchor_node.screenWidth() / 2
    anchor_center_y = anchor_node.ypos() + anchor_node.screenHeight() / 2
    for node in selected_nodes:
        if node is anchor_node:
            continue
        node_center_x = node.xpos() + node.screenWidth() / 2
        node_center_y = node.ypos() + node.screenHeight() / 2
        dx = node_center_x - anchor_center_x
        dy = node_center_y - anchor_center_y
        new_dx = round(dx * scale_factor) if axis != "v" else round(dx)
        new_dy = round(dy * scale_factor) if axis != "h" else round(dy)
        # Enforce minimum floor: if the node is not at the same position as the anchor
        # on a given axis, it must remain at least snap_min pixels away (center-to-center).
        # Only apply the floor to the axis being scaled.
        if axis != "v" and dx != 0 and abs(new_dx) < snap_min:
            new_dx = snap_min if dx > 0 else -snap_min
        if axis != "h" and dy != 0 and abs(new_dy) < snap_min:
            new_dy = snap_min if dy > 0 else -snap_min
        new_center_x = anchor_center_x + new_dx
        new_center_y = anchor_center_y + new_dy
        node.setXpos(round(new_center_x - node.screenWidth() / 2))
        node.setYpos(round(new_center_y - node.screenHeight() / 2))
    # Scale state write-back: accumulate h_scale and v_scale on all affected nodes.
    # Only update the scale state for the axis being scaled.
    for scale_node in selected_nodes:
        stored_state = node_layout_state.read_node_state(scale_node)
        if axis != "v":
            stored_state["h_scale"] = round(stored_state["h_scale"] * scale_factor, 10)
        if axis != "h":
            stored_state["v_scale"] = round(stored_state["v_scale"] * scale_factor, 10)
        node_layout_state.write_node_state(scale_node, stored_state)


def _scale_upstream_nodes(scale_factor, axis="both"):
    root_node = nuke.selectedNode()
    upstream_nodes = collect_subtree_nodes(root_node)
    # The selected root node is always the anchor — it stays fixed while all upstream
    # nodes scale relative to it. This preserves alignment with any downstream nodes.
    anchor_node = root_node
    snap_min = get_dag_snap_threshold() - 1
    anchor_center_x = anchor_node.xpos() + anchor_node.screenWidth() / 2
    anchor_center_y = anchor_node.ypos() + anchor_node.screenHeight() / 2
    for node in upstream_nodes:
        if node is anchor_node:
            continue
        node_center_x = node.xpos() + node.screenWidth() / 2
        node_center_y = node.ypos() + node.screenHeight() / 2
        dx = node_center_x - anchor_center_x
        dy = node_center_y - anchor_center_y
        new_dx = round(dx * scale_factor) if axis != "v" else round(dx)
        new_dy = round(dy * scale_factor) if axis != "h" else round(dy)
        if axis != "v" and dx != 0 and abs(new_dx) < snap_min:
            new_dx = snap_min if dx > 0 else -snap_min
        if axis != "h" and dy != 0 and abs(new_dy) < snap_min:
            new_dy = snap_min if dy > 0 else -snap_min
        new_center_x = anchor_center_x + new_dx
        new_center_y = anchor_center_y + new_dy
        node.setXpos(round(new_center_x - node.screenWidth() / 2))
        node.setYpos(round(new_center_y - node.screenHeight() / 2))
    # Scale state write-back: accumulate h_scale and v_scale on all upstream nodes.
    # Only update the scale state for the axis being scaled.
    for scale_node in upstream_nodes:
        stored_state = node_layout_state.read_node_state(scale_node)
        if axis != "v":
            stored_state["h_scale"] = round(stored_state["h_scale"] * scale_factor, 10)
        if axis != "h":
            stored_state["v_scale"] = round(stored_state["v_scale"] * scale_factor, 10)
        node_layout_state.write_node_state(scale_node, stored_state)


def shrink_selected():
    if len(nuke.selectedNodes()) < 2:
        return
    global _last_scale_fn
    _last_scale_fn = shrink_selected
    nuke.Undo.name("Shrink Selected")
    nuke.Undo.begin()
    try:
        _scale_selected_nodes(SHRINK_FACTOR)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def expand_selected():
    current_group = nuke.lastHitGroup()    # MUST be the first Nuke API call
    selected_nodes = nuke.selectedNodes()
    if len(selected_nodes) < 2:
        return
    global _last_scale_fn
    _last_scale_fn = expand_selected
    node_ids = {id(n) for n in selected_nodes}
    bbox_before = compute_node_bounding_box(selected_nodes)
    nuke.Undo.name("Expand Selected")
    nuke.Undo.begin()
    try:
        _scale_selected_nodes(EXPAND_FACTOR)
        bbox_after = compute_node_bounding_box(selected_nodes)
        if bbox_before is not None and bbox_after is not None:
            push_nodes_to_make_room(node_ids, bbox_before, bbox_after, current_group)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def shrink_upstream():
    try:
        nuke.selectedNode()
    except ValueError:
        return
    global _last_scale_fn
    _last_scale_fn = shrink_upstream
    nuke.Undo.name("Shrink Upstream")
    nuke.Undo.begin()
    try:
        _scale_upstream_nodes(SHRINK_FACTOR)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def expand_upstream():
    current_group = nuke.lastHitGroup()    # MUST be the first Nuke API call
    try:
        root_node = nuke.selectedNode()
    except ValueError:
        return
    global _last_scale_fn
    _last_scale_fn = expand_upstream
    upstream_nodes = collect_subtree_nodes(root_node)
    upstream_node_ids = {id(n) for n in upstream_nodes}
    bbox_before = compute_node_bounding_box(upstream_nodes)
    nuke.Undo.name("Expand Upstream")
    nuke.Undo.begin()
    try:
        _scale_upstream_nodes(EXPAND_FACTOR)
        bbox_after = compute_node_bounding_box(upstream_nodes)
        if bbox_before is not None and bbox_after is not None:
            push_nodes_to_make_room(upstream_node_ids, bbox_before, bbox_after, current_group)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def shrink_selected_horizontal():
    if len(nuke.selectedNodes()) < 2:
        return
    global _last_scale_fn
    _last_scale_fn = shrink_selected_horizontal
    nuke.Undo.name("Shrink Selected Horizontal")
    nuke.Undo.begin()
    try:
        _scale_selected_nodes(SHRINK_FACTOR, axis="h")
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def shrink_selected_vertical():
    if len(nuke.selectedNodes()) < 2:
        return
    global _last_scale_fn
    _last_scale_fn = shrink_selected_vertical
    nuke.Undo.name("Shrink Selected Vertical")
    nuke.Undo.begin()
    try:
        _scale_selected_nodes(SHRINK_FACTOR, axis="v")
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def expand_selected_horizontal():
    current_group = nuke.lastHitGroup()    # MUST be first Nuke API call
    selected_nodes = nuke.selectedNodes()
    if len(selected_nodes) < 2:
        return
    global _last_scale_fn
    _last_scale_fn = expand_selected_horizontal
    node_ids = {id(n) for n in selected_nodes}
    bbox_before = compute_node_bounding_box(selected_nodes)
    nuke.Undo.name("Expand Selected Horizontal")
    nuke.Undo.begin()
    try:
        _scale_selected_nodes(EXPAND_FACTOR, axis="h")
        bbox_after = compute_node_bounding_box(selected_nodes)
        if bbox_before is not None and bbox_after is not None:
            push_nodes_to_make_room(node_ids, bbox_before, bbox_after, current_group)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def expand_selected_vertical():
    current_group = nuke.lastHitGroup()    # MUST be first Nuke API call
    selected_nodes = nuke.selectedNodes()
    if len(selected_nodes) < 2:
        return
    global _last_scale_fn
    _last_scale_fn = expand_selected_vertical
    node_ids = {id(n) for n in selected_nodes}
    bbox_before = compute_node_bounding_box(selected_nodes)
    nuke.Undo.name("Expand Selected Vertical")
    nuke.Undo.begin()
    try:
        _scale_selected_nodes(EXPAND_FACTOR, axis="v")
        bbox_after = compute_node_bounding_box(selected_nodes)
        if bbox_before is not None and bbox_after is not None:
            push_nodes_to_make_room(node_ids, bbox_before, bbox_after, current_group)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def shrink_upstream_horizontal():
    try:
        nuke.selectedNode()
    except ValueError:
        return
    global _last_scale_fn
    _last_scale_fn = shrink_upstream_horizontal
    nuke.Undo.name("Shrink Upstream Horizontal")
    nuke.Undo.begin()
    try:
        _scale_upstream_nodes(SHRINK_FACTOR, axis="h")
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def shrink_upstream_vertical():
    try:
        nuke.selectedNode()
    except ValueError:
        return
    global _last_scale_fn
    _last_scale_fn = shrink_upstream_vertical
    nuke.Undo.name("Shrink Upstream Vertical")
    nuke.Undo.begin()
    try:
        _scale_upstream_nodes(SHRINK_FACTOR, axis="v")
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def expand_upstream_horizontal():
    current_group = nuke.lastHitGroup()    # MUST be first Nuke API call
    try:
        root_node = nuke.selectedNode()
    except ValueError:
        return
    global _last_scale_fn
    _last_scale_fn = expand_upstream_horizontal
    upstream_nodes = collect_subtree_nodes(root_node)
    upstream_node_ids = {id(n) for n in upstream_nodes}
    bbox_before = compute_node_bounding_box(upstream_nodes)
    nuke.Undo.name("Expand Upstream Horizontal")
    nuke.Undo.begin()
    try:
        _scale_upstream_nodes(EXPAND_FACTOR, axis="h")
        bbox_after = compute_node_bounding_box(upstream_nodes)
        if bbox_before is not None and bbox_after is not None:
            push_nodes_to_make_room(upstream_node_ids, bbox_before, bbox_after, current_group)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def expand_upstream_vertical():
    current_group = nuke.lastHitGroup()    # MUST be first Nuke API call
    try:
        root_node = nuke.selectedNode()
    except ValueError:
        return
    global _last_scale_fn
    _last_scale_fn = expand_upstream_vertical
    upstream_nodes = collect_subtree_nodes(root_node)
    upstream_node_ids = {id(n) for n in upstream_nodes}
    bbox_before = compute_node_bounding_box(upstream_nodes)
    nuke.Undo.name("Expand Upstream Vertical")
    nuke.Undo.begin()
    try:
        _scale_upstream_nodes(EXPAND_FACTOR, axis="v")
        bbox_after = compute_node_bounding_box(upstream_nodes)
        if bbox_before is not None and bbox_after is not None:
            push_nodes_to_make_room(upstream_node_ids, bbox_before, bbox_after, current_group)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def repeat_last_scale():
    # _last_scale_fn is None if no scale command has been run this session.
    # No-op when None to avoid surprising the user with an unexpected direction.
    global _last_scale_fn
    if _last_scale_fn is None:
        return
    _last_scale_fn()


def clear_layout_state_selected():
    """Remove stored layout state from all selected nodes.

    After clear, the next layout run will use default scheme (normal) and scale (1.0).
    Wrapped in an undo group so the user can Ctrl+Z to restore state knobs.
    """
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
    nuke.Undo.name("Clear Layout State Selected")
    nuke.Undo.begin()
    try:
        for node in selected_nodes:
            node_layout_state.clear_node_state(node)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def clear_layout_state_upstream():
    """Remove stored layout state from the selected node and all upstream nodes.

    After clear, the next layout run will use default scheme (normal) and scale (1.0).
    Wrapped in an undo group so the user can Ctrl+Z to restore state knobs.
    """
    root = nuke.selectedNode()
    upstream_nodes = collect_subtree_nodes(root)
    nuke.Undo.name("Clear Layout State Upstream")
    nuke.Undo.begin()
    try:
        for node in upstream_nodes:
            node_layout_state.clear_node_state(node)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def freeze_selected():
    """Mark selected nodes as a freeze group with a shared UUID.

    All selected nodes receive the same UUID in their hidden state knob.
    No visual change occurs in the DAG.  Wrapped in an undo group.

    If any selected nodes are already frozen, they are re-assigned to the
    new group (the old UUID is replaced).
    """
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
    group_uuid = str(uuid.uuid4())
    nuke.Undo.name("Freeze Selected")
    nuke.Undo.begin()
    try:
        for node in selected_nodes:
            node_layout_state.write_freeze_group(node, group_uuid)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def unfreeze_selected():
    """Remove freeze group membership from all selected nodes.

    Each selected node's freeze_group state is set to None.
    Wrapped in an undo group.
    """
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return
    nuke.Undo.name("Unfreeze Selected")
    nuke.Undo.begin()
    try:
        for node in selected_nodes:
            node_layout_state.clear_freeze_group(node)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def arrange_selected_horizontal():
    """Align selected nodes horizontally by their top edges and distribute them evenly.

    All selected nodes are aligned to the topmost Y position.  Their X positions
    are then distributed evenly across the range from the leftmost to rightmost node.
    Wrapped in an undo group.

    If 0 or 1 nodes selected: no-op.
    """
    selected_nodes = nuke.selectedNodes()
    if len(selected_nodes) <= 1:
        return

    nuke.Undo.name("Arrange Horizontal")
    nuke.Undo.begin()
    try:
        # Sort nodes by current X position for distribution
        sorted_nodes = sorted(selected_nodes, key=lambda n: n.xpos())
        node_count = len(sorted_nodes)

        # Compute bounds
        min_x = min(node.xpos() for node in selected_nodes)
        max_x = max(node.xpos() for node in selected_nodes)
        range_x = max(max_x - min_x, node_count * 110)

        # Distribute nodes evenly across X range, aligned to min_y
        for index, node in enumerate(sorted_nodes):
            # Linear interpolation: first node at min_x, last node at max_x
            new_x = min_x + (index / (node_count - 1)) * range_x
            node.setXpos(int(new_x))
            node.setYpos(sorted_nodes[0].ypos())
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()


def arrange_selected_vertical():
    """Align selected nodes vertically by their centre Y and distribute them evenly.

    All selected nodes are aligned to the same centre X position (the x of the first
    node).  Their Y positions are then distributed evenly
    across the range from the topmost to bottommost node's centre Y.  Wrapped
    in an undo group.

    If 0 or 1 nodes selected: no-op.
    """
    selected_nodes = nuke.selectedNodes()
    if len(selected_nodes) <= 1:
        return

    nuke.Undo.name("Arrange Vertical")
    nuke.Undo.begin()
    try:
        # Sort nodes by current Y position (centre Y) for distribution
        sorted_nodes = sorted(
            selected_nodes,
            key=lambda n: n.ypos() + n.screenHeight() / 2
        )
        node_count = len(sorted_nodes)
        first_node = sorted_nodes[0]

        # Compute bounds
        min_y = min(node.ypos() for node in selected_nodes)
        max_y = max(node.ypos() for node in selected_nodes)
        range_y = max(
                max_y - min_y,
                sum([node.screenHeight() for node in sorted_nodes[:-1]])
                + 7 * len(selected_nodes)
                )

        # Calculate horizontal alignment point
        center_x = first_node.xpos() + first_node.screenWidth() / 2

        # Distribute node centres evenly across Y range, aligned to center_x
        for index, node in enumerate(sorted_nodes):
            if index == 0:
                continue

            # Linear interpolation: first node's centre at min_y, last at max_y
            centre_y = min_y + (index / (node_count - 1)) * range_y
            new_y = int(centre_y)
            new_x = int(center_x - node.screenWidth() / 2)
            node.setXpos(new_x)
            node.setYpos(new_y)
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()
