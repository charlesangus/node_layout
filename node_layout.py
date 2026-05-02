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
                _tab = nuke.Tab_Knob('node_layout_tab', 'Node Layout')
                _tab.setFlag(nuke.INVISIBLE)
                dot.addKnob(_tab)
                _marker = nuke.Int_Knob('node_layout_diamond_dot', 'Diamond Dot Marker')
                _marker.setFlag(nuke.INVISIBLE)
                dot.addKnob(_marker)
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
            _tab = nuke.Tab_Knob('node_layout_tab', 'Node Layout')
            _tab.setFlag(nuke.INVISIBLE)
            dot.addKnob(_tab)
            _marker = nuke.Int_Knob('node_layout_diamond_dot', 'Diamond Dot Marker')
            _marker.setFlag(nuke.INVISIBLE)
            dot.addKnob(_marker)
            dot['node_layout_diamond_dot'].setValue(1)
            dot.setInput(0, inp)
            dot['hide_input'].setValue(True)
            parent.setInput(slot, dot)
        else:
            _claim(inp)


def _find_or_create_leftmost_dot(leftmost_spine_node, current_group):
    """Insert a routing Dot between leftmost_spine_node and its input[0].

    The Dot is wired: upstream_root → Dot → leftmost_spine_node.  It enables
    correct wire routing when the upstream subtree is placed above-left of the
    spine: the wire drops vertically from the upstream root to the Dot (at spine
    Y), then runs horizontally to the leftmost spine node's input.

    Positioning of the Dot is handled by the bbox layout engine.
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
        _tab = nuke.Tab_Knob('node_layout_tab', 'Node Layout')
        _tab.setFlag(nuke.INVISIBLE)
        dot.addKnob(_tab)
        _marker = nuke.Int_Knob(_LEFTMOST_DOT_KNOB_NAME, 'Leftmost Dot Marker')
        _marker.setFlag(nuke.INVISIBLE)
        dot.addKnob(_marker)
        dot[_LEFTMOST_DOT_KNOB_NAME].setValue(1)
        dot.setInput(0, upstream)
        leftmost_spine_node.setInput(0, dot)

    return dot










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

        # Root-relative block extents used by the bbox layout engine.
        self.right_extent = block_max_x - root.xpos()
        self.left_overhang = root.xpos() - block_min_x
        self.block_height = block_max_y - block_min_y
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




def _bbox_engine():
    import node_layout_bbox  # noqa: PLC0415

    return node_layout_bbox.BboxEngine()


def layout_upstream(scheme_multiplier=None):
    return _bbox_engine().layout_upstream(scheme_multiplier=scheme_multiplier)


def layout_selected(scheme_multiplier=None):
    return _bbox_engine().layout_selected(scheme_multiplier=scheme_multiplier)


def layout_selected_horizontal(scheme_multiplier=None):
    return _bbox_engine().layout_selected_horizontal(
        scheme_multiplier=scheme_multiplier
    )


def layout_selected_horizontal_place_only(scheme_multiplier=None):
    return _bbox_engine().layout_selected_horizontal_place_only(
        scheme_multiplier=scheme_multiplier
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
