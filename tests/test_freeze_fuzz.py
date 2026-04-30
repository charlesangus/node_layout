"""Property-based fuzz tests for freeze block geometry.

Each test runs a parameterised loop with a seeded PRNG over many random
freeze-block configurations.  On any failed assertion we surface the seed
plus the offending configuration in the error message so a single broken
case can be replayed deterministically.

This file is the structural counterpart to the FreezeProxy refactor: the
proxy collapses every "is this node a freeze block root?" check in the
horizontal layout pipeline into a single helper (``effective_node_dims``).
The fuzz tests below assert that the proxy stays consistent and that the
horizontal pipeline never lands a non-frozen node on top of a frozen block,
across a wide variety of generated graphs.

Properties under test
---------------------
1. ``effective_node_dims`` mirrors the FreezeBlock bbox triple for direct
   freeze-block roots and for nodes that route to one through a chain of Dots.
2. ``compute_dims`` for a freeze-block *leaf* root equals the proxy triple.
3. ``compute_dims`` for a freeze-block *non-leaf* root has width at least the
   block's full bbox width and root_x_offset at least the left overhang.
4. After ``place_subtree_horizontal`` + ``restore_positions`` on a randomly
   shaped horizontal spine that contains freeze blocks, the bounding box of
   every freeze block is disjoint from every non-block node and from every
   other block.  This is the "wide frozen blocks must not overlap adjacent
   subtrees" guarantee the refactor was built to enforce.
"""
import importlib.util
import os
import random
import sys
import types
import unittest

NODE_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout.py")
NODE_LAYOUT_PREFS_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_prefs.py")
NODE_LAYOUT_STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "node_layout_state.py")


# ---------------------------------------------------------------------------
# Minimal Nuke stubs (mirrors the pattern in test_freeze_layout.py)
# ---------------------------------------------------------------------------


class _StubKnob:
    def __init__(self, val=0):
        self._val = val

    def value(self):
        return self._val

    def getValue(self):
        return self._val

    def setValue(self, value):
        self._val = value

    def setFlag(self, flag):
        pass


class _StubNode:
    def __init__(self, width=80, height=28, xpos=0, ypos=0, node_class="Grade",
                 knobs=None):
        self._width = width
        self._height = height
        self._xpos = xpos
        self._ypos = ypos
        self._class = node_class
        self._knobs = knobs if knobs is not None else {"tile_color": _StubKnob(0)}
        self._inputs = []

    def screenWidth(self):
        return self._width

    def screenHeight(self):
        return self._height

    def xpos(self):
        return self._xpos

    def ypos(self):
        return self._ypos

    def setXpos(self, value):
        self._xpos = value

    def setYpos(self, value):
        self._ypos = value

    def Class(self):
        return self._class

    def inputs(self):
        return len(self._inputs)

    def input(self, index):
        if 0 <= index < len(self._inputs):
            return self._inputs[index]
        return None

    def setInput(self, index, node):
        while len(self._inputs) <= index:
            self._inputs.append(None)
        self._inputs[index] = node

    def knob(self, name):
        return self._knobs.get(name)

    def addKnob(self, knob_obj):
        knob_name = getattr(knob_obj, 'name', None) or getattr(knob_obj, '_name', None)
        if knob_name and knob_name not in self._knobs:
            self._knobs[knob_name] = knob_obj

    def __getitem__(self, name):
        if name in self._knobs:
            return self._knobs[name]
        return _StubKnob(0)

    def inputLabel(self, slot):
        return ""


def _make_preferences_node():
    node = _StubNode(node_class="Preferences")
    node._knobs = {
        "dag_snap_threshold": _StubKnob(8),
        "NodeColor": _StubKnob(0),
    }
    node.knobs = lambda: node._knobs
    return node


class _StubUndo:
    @staticmethod
    def name(label):
        pass

    @staticmethod
    def begin():
        pass

    @staticmethod
    def end():
        pass

    @staticmethod
    def cancel():
        pass


class _StubContextManager:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def nodes(self):
        return []


class _StubTab_Knob:
    def __init__(self, name='', label=''):
        self.name = name

    def setFlag(self, flag):
        pass


_nuke_stub = types.ModuleType("nuke")
_nuke_stub.Node = _StubNode
_nuke_stub.allNodes = lambda: []
_nuke_stub.selectedNodes = lambda: []
_nuke_stub.selectedNode = lambda: _StubNode()
_nuke_stub.toNode = lambda name: _make_preferences_node() if name == "preferences" else None
_nuke_stub.menu = lambda name: None
_nuke_stub.Undo = _StubUndo
_nuke_stub.INVISIBLE = 0x01
_nuke_stub.lastHitGroup = lambda: _StubContextManager()
_nuke_stub.Tab_Knob = _StubTab_Knob
_nuke_stub.String_Knob = lambda name='', label='': _StubKnob(0)
sys.modules["nuke"] = _nuke_stub

if "node_layout_prefs" in sys.modules:
    # Another test module loaded prefs first (typical under unittest discover);
    # reuse that handle so module-level globals stay consistent.
    _node_layout_prefs_module = sys.modules["node_layout_prefs"]
else:
    _prefs_spec = importlib.util.spec_from_file_location(
        "node_layout_prefs", NODE_LAYOUT_PREFS_PATH
    )
    _node_layout_prefs_module = importlib.util.module_from_spec(_prefs_spec)
    sys.modules["node_layout_prefs"] = _node_layout_prefs_module
    _prefs_spec.loader.exec_module(_node_layout_prefs_module)

if "node_layout_state" in sys.modules:
    _node_layout_state_module = sys.modules["node_layout_state"]
else:
    _state_spec = importlib.util.spec_from_file_location(
        "node_layout_state", NODE_LAYOUT_STATE_PATH
    )
    _node_layout_state_module = importlib.util.module_from_spec(_state_spec)
    sys.modules["node_layout_state"] = _node_layout_state_module
    _state_spec.loader.exec_module(_node_layout_state_module)

# Use a module name that does not collide with test_freeze_layout's alias.
_spec = importlib.util.spec_from_file_location("node_layout_fuzz", NODE_LAYOUT_PATH)
_nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_nl)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Number of random configurations per fuzz test.  Big enough to cover a wide
# variety of geometries (block widths, overhang signs, sibling counts, multi-
# block trees) but small enough that the full suite stays sub-second on a
# laptop.  Bump locally if you suspect a regression slipped through.
DEFAULT_FUZZ_ITERATIONS = 80


def _wire(upstream_node, downstream_node, slot=0):
    """Connect *upstream_node* as input *slot* of *downstream_node*."""
    while len(downstream_node._inputs) <= slot:
        downstream_node._inputs.append(None)
    downstream_node._inputs[slot] = upstream_node


def _make_freeze_block_with_geometry(member_widths, member_x_offsets, member_y_offsets,
                                     uuid_str="fuzz-block"):
    """Build a freeze block whose members sit at the requested geometry.

    The first member is treated as the block root.  Subsequent members are
    wired as ``member[i] -> member[i-1]`` so the root is the most-downstream
    node — this matches the contract of ``_find_freeze_block_root``.

    All offsets are relative to the root (which is placed at xpos=0, ypos=0)
    so the FreezeBlock constructor sees the geometry we asked for.

    Returns the FreezeBlock object plus the list of member nodes (root first).
    """
    assert len(member_widths) == len(member_x_offsets) == len(member_y_offsets)
    members = []
    for member_index, (member_w, x_off, y_off) in enumerate(
        zip(member_widths, member_x_offsets, member_y_offsets, strict=True)
    ):
        member_node = _StubNode(width=member_w, height=28, xpos=x_off, ypos=y_off)
        members.append(member_node)
        if member_index > 0:
            _wire(member_node, members[member_index - 1])
    block = _nl.FreezeBlock(root=members[0], members=list(members), uuid=uuid_str)
    return block, members


def _bbox(node):
    """Top-left / bottom-right bbox for a single node."""
    return (
        node.xpos(),
        node.ypos(),
        node.xpos() + node.screenWidth(),
        node.ypos() + node.screenHeight(),
    )


def _bboxes_overlap(box_a, box_b, tolerance=0):
    """Return True if rectangles *box_a* and *box_b* overlap by more than *tolerance*."""
    a_min_x, a_min_y, a_max_x, a_max_y = box_a
    b_min_x, b_min_y, b_max_x, b_max_y = box_b
    if a_max_x - tolerance <= b_min_x:
        return False
    if b_max_x - tolerance <= a_min_x:
        return False
    if a_max_y - tolerance <= b_min_y:
        return False
    return not b_max_y - tolerance <= a_min_y


def _block_bbox(block):
    """Bounding box of all members of a FreezeBlock at their current positions."""
    return (
        min(m.xpos() for m in block.members),
        min(m.ypos() for m in block.members),
        max(m.xpos() + m.screenWidth() for m in block.members),
        max(m.ypos() + m.screenHeight() for m in block.members),
    )


# ---------------------------------------------------------------------------
# Property 1 — effective_node_dims is consistent with FreezeBlock geometry.
# ---------------------------------------------------------------------------


class TestEffectiveNodeDimsFuzz(unittest.TestCase):
    """``effective_node_dims`` is the single proxy used by the horizontal layout.
    Every other freeze-aware site goes through it, so its consistency is the
    foundation the rest of the refactor stands on."""

    def test_fuzz_proxy_returns_block_bbox_for_block_root(self):
        """For every freeze block, ``effective_node_dims(root, overrides)`` returns
        ``(right_extent + left_overhang, block_height, left_overhang)``."""
        seed = 0xF1A5C0
        rng = random.Random(seed)
        for iteration in range(DEFAULT_FUZZ_ITERATIONS):
            num_members = rng.randint(1, 5)
            member_widths = [rng.randint(40, 240) for _ in range(num_members)]
            member_x_offsets = [rng.randint(-200, 200) for _ in range(num_members)]
            member_y_offsets = [rng.randint(-300, 300) for _ in range(num_members)]
            # First member is the root by construction (placed at 0,0).
            member_x_offsets[0] = 0
            member_y_offsets[0] = 0
            block, members = _make_freeze_block_with_geometry(
                member_widths, member_x_offsets, member_y_offsets,
                uuid_str=f"fuzz-{iteration}",
            )
            dimension_overrides = {id(block.root): block}
            try:
                proxy_w, proxy_h, proxy_left_overhang = _nl.effective_node_dims(
                    block.root, dimension_overrides
                )
                self.assertEqual(
                    proxy_w, block.right_extent + block.left_overhang,
                    "proxy width must equal block bbox width",
                )
                self.assertEqual(
                    proxy_h, block.block_height,
                    "proxy height must equal block bbox height",
                )
                self.assertEqual(
                    proxy_left_overhang, block.left_overhang,
                    "proxy left_overhang must equal block.left_overhang",
                )
            except AssertionError:
                raise AssertionError(  # noqa: B904 - chained traceback adds noise here
                    f"seed={seed:#x} iter={iteration} "
                    f"widths={member_widths} x_offs={member_x_offsets} "
                    f"y_offs={member_y_offsets}"
                )

    def test_fuzz_proxy_returns_screen_dims_for_normal_node(self):
        """For a non-frozen node the proxy must return ``(screenWidth, screenHeight, 0)``."""
        seed = 0xF1A5C1
        rng = random.Random(seed)
        for iteration in range(DEFAULT_FUZZ_ITERATIONS):
            tile_w = rng.randint(40, 240)
            tile_h = rng.randint(20, 60)
            normal_node = _StubNode(width=tile_w, height=tile_h)
            try:
                proxy_w, proxy_h, proxy_left_overhang = _nl.effective_node_dims(
                    normal_node, {}
                )
                self.assertEqual(proxy_w, tile_w)
                self.assertEqual(proxy_h, tile_h)
                self.assertEqual(proxy_left_overhang, 0)
            except AssertionError:
                raise AssertionError(  # noqa: B904 - chained traceback adds noise here
                    f"seed={seed:#x} iter={iteration} w={tile_w} h={tile_h}"
                )

    def test_fuzz_proxy_walks_through_dot_chain(self):
        """The proxy walks through any chain of Dot nodes feeding into a
        freeze block root and still returns the block triple."""
        seed = 0xF1A5C2
        rng = random.Random(seed)
        for iteration in range(DEFAULT_FUZZ_ITERATIONS):
            num_members = rng.randint(2, 4)
            member_widths = [rng.randint(40, 240) for _ in range(num_members)]
            member_x_offsets = [0] + [rng.randint(-200, 200) for _ in range(num_members - 1)]
            member_y_offsets = [0] + [rng.randint(-300, 300) for _ in range(num_members - 1)]
            block, _members = _make_freeze_block_with_geometry(
                member_widths, member_x_offsets, member_y_offsets,
                uuid_str=f"dot-chain-{iteration}",
            )
            dimension_overrides = {id(block.root): block}

            num_dots = rng.randint(1, 5)
            chain_head = block.root
            for _ in range(num_dots):
                next_dot = _StubNode(width=12, height=12, node_class="Dot")
                _wire(chain_head, next_dot)
                chain_head = next_dot

            try:
                proxy_w, proxy_h, proxy_left_overhang = _nl.effective_node_dims(
                    chain_head, dimension_overrides
                )
                self.assertEqual(proxy_w, block.right_extent + block.left_overhang)
                self.assertEqual(proxy_h, block.block_height)
                self.assertEqual(proxy_left_overhang, block.left_overhang)
            except AssertionError:
                raise AssertionError(  # noqa: B904 - chained traceback adds noise here
                    f"seed={seed:#x} iter={iteration} num_dots={num_dots}"
                )


# ---------------------------------------------------------------------------
# Property 2 — compute_dims agrees with the proxy.
# ---------------------------------------------------------------------------


class TestComputeDimsFreezeFuzz(unittest.TestCase):
    """``compute_dims`` is the dimension oracle used everywhere except the
    horizontal spine pre-pass.  It must agree with the proxy for both leaf
    and non-leaf freeze block roots, otherwise downstream spacing math
    silently disagrees with the proxy."""

    def test_fuzz_compute_dims_leaf_freeze_root_equals_proxy(self):
        """A freeze block root with no in-filter inputs is treated as a leaf;
        its compute_dims result must equal the proxy triple exactly."""
        seed = 0xC0DE01
        rng = random.Random(seed)
        for iteration in range(DEFAULT_FUZZ_ITERATIONS):
            num_members = rng.randint(1, 5)
            member_widths = [rng.randint(40, 240) for _ in range(num_members)]
            member_x_offsets = [0] + [rng.randint(-200, 200) for _ in range(num_members - 1)]
            member_y_offsets = [0] + [rng.randint(-300, 300) for _ in range(num_members - 1)]
            block, members = _make_freeze_block_with_geometry(
                member_widths, member_x_offsets, member_y_offsets,
                uuid_str=f"leaf-{iteration}",
            )
            dimension_overrides = {id(block.root): block}
            # Filter members so only the root is in-filter — non-root members are
            # excluded from the layout-visible graph (the same trick layout_upstream
            # uses to make the block look like a leaf to compute_dims).
            node_filter = {block.root}
            memo = {}
            try:
                computed = _nl.compute_dims(
                    block.root, memo, snap_threshold=8, node_count=len(members),
                    node_filter=node_filter,
                    dimension_overrides=dimension_overrides,
                )
                proxy = _nl.effective_node_dims(block.root, dimension_overrides)
                self.assertEqual(
                    computed, proxy,
                    "compute_dims for a leaf freeze root must equal proxy triple",
                )
            except AssertionError:
                raise AssertionError(  # noqa: B904 - chained traceback adds noise here
                    f"seed={seed:#x} iter={iteration} widths={member_widths} "
                    f"x_offs={member_x_offsets} y_offs={member_y_offsets}"
                )

    def test_fuzz_compute_dims_nonleaf_freeze_root_widens_to_block(self):
        """A freeze block root WITH in-filter external inputs gets a non-leaf
        compute_dims result.  That result must still be at least as wide as
        the block bbox and carry a root_x_offset at least the left overhang —
        otherwise the surrounding layout reserves too little space."""
        seed = 0xC0DE02
        rng = random.Random(seed)
        for iteration in range(DEFAULT_FUZZ_ITERATIONS):
            num_members = rng.randint(2, 5)
            member_widths = [rng.randint(40, 240) for _ in range(num_members)]
            # Force at least one member to extend left of the root so left_overhang > 0
            # in many iterations — exercises the asymmetric overhang path.
            member_x_offsets = [0] + [
                rng.randint(-200, 200) for _ in range(num_members - 1)
            ]
            member_y_offsets = [0] + [
                rng.randint(-300, 300) for _ in range(num_members - 1)
            ]
            block, members = _make_freeze_block_with_geometry(
                member_widths, member_x_offsets, member_y_offsets,
                uuid_str=f"nonleaf-{iteration}",
            )
            dimension_overrides = {id(block.root): block}

            # Add an external (non-frozen) input feeding the block root so the
            # non-leaf branch of compute_dims fires.
            external_input = _StubNode(width=rng.randint(40, 240), height=28)
            _wire(external_input, block.root, slot=1)
            node_filter = {block.root, external_input}

            memo = {}
            block_bbox_w = block.right_extent + block.left_overhang
            try:
                computed_w, computed_h, computed_root_x_off = _nl.compute_dims(
                    block.root, memo, snap_threshold=8, node_count=len(members) + 1,
                    node_filter=node_filter,
                    dimension_overrides=dimension_overrides,
                )
                self.assertGreaterEqual(
                    computed_w, block_bbox_w,
                    "compute_dims width must be widened to at least the block bbox",
                )
                self.assertGreaterEqual(
                    computed_root_x_off, block.left_overhang,
                    "compute_dims root_x_offset must cover the block's left overhang",
                )
            except AssertionError:
                raise AssertionError(  # noqa: B904 - chained traceback adds noise here
                    f"seed={seed:#x} iter={iteration} widths={member_widths} "
                    f"x_offs={member_x_offsets} y_offs={member_y_offsets} "
                    f"left_overhang={block.left_overhang} right_extent={block.right_extent}"
                )


# ---------------------------------------------------------------------------
# Property 3 — wide frozen blocks never overlap adjacent subtrees.
# ---------------------------------------------------------------------------


def _build_horizontal_spine_with_freeze_blocks(rng, iteration_id):
    """Construct a random horizontal-spine fixture for the no-overlap test.

    Layout
    ------
    Spine: ``spine[0]`` (rightmost / output) <- ``spine[1]`` <- ... ``spine[n-1]``,
    each connected via input(0).  Each spine node may have one or two side
    inputs (slots 1+).  Each side input is either a normal small subtree or a
    freeze-block root.  Some spine nodes are themselves freeze-block roots.

    Frozen blocks are constructed with deliberately wide and asymmetric
    geometry so that overlap regressions show up.

    Returns
    -------
    spine_root : _StubNode
        The rightmost spine node — call ``place_subtree_horizontal`` on this.
    all_blocks : list[FreezeBlock]
        Every freeze block in the fixture (spine and side).  Tests must invoke
        ``restore_positions`` on each to mirror what ``layout_upstream`` does
        in production.
    dimension_overrides : dict
        ``id(root) -> FreezeBlock`` for every block (the contract used by
        ``place_subtree_horizontal``).
    description : str
        Human-readable description for failure reports.
    """
    spine_length = rng.randint(2, 5)
    spine_nodes = []
    all_blocks = []
    dimension_overrides = {}

    description_parts = [f"iter={iteration_id} spine_len={spine_length}"]

    # Build the spine (rightmost first).
    previous_spine_node = None
    for spine_index in range(spine_length):
        spine_node_width = rng.randint(60, 140)
        # 25% chance the spine node is a freeze-block root.
        is_frozen_spine = rng.random() < 0.25
        if is_frozen_spine:
            # Build a wide, asymmetric block for this spine node.
            num_extra_members = rng.randint(1, 3)
            # Members extend both left and right of the root.
            extra_widths = [rng.randint(60, 200) for _ in range(num_extra_members)]
            extra_x_offsets = [
                rng.choice([
                    rng.randint(-300, -60),  # leftward overhang
                    rng.randint(spine_node_width + 20, spine_node_width + 240),  # rightward
                ])
                for _ in range(num_extra_members)
            ]
            extra_y_offsets = [rng.randint(-200, -30) for _ in range(num_extra_members)]
            block, members = _make_freeze_block_with_geometry(
                [spine_node_width] + extra_widths,
                [0] + extra_x_offsets,
                [0] + extra_y_offsets,
                uuid_str=f"spine-{iteration_id}-{spine_index}",
            )
            spine_node = members[0]  # the root
            all_blocks.append(block)
            dimension_overrides[id(spine_node)] = block
            description_parts.append(
                f"spine[{spine_index}]=FROZEN(W={block.right_extent + block.left_overhang},"
                f"L={block.left_overhang})"
            )
        else:
            spine_node = _StubNode(width=spine_node_width, height=28)
            description_parts.append(f"spine[{spine_index}]=normal({spine_node_width})")

        # Wire as input(0) of the previous (more downstream) spine node.
        if previous_spine_node is not None:
            _wire(spine_node, previous_spine_node, slot=0)
        spine_nodes.append(spine_node)
        previous_spine_node = spine_node

    spine_root = spine_nodes[0]

    # Add at most one side input per spine node.  ``place_subtree_horizontal``
    # places every side input of a given spine node centered above it at the
    # same Y band, so two non-mask side inputs on the same spine node always
    # collide regardless of freeze handling — that's an orthogonal layout
    # constraint, not a freeze-block bug, so the fuzz harness keeps to one
    # side input per spine node to isolate the property under test.
    for spine_index, spine_node in enumerate(spine_nodes):
        num_side_inputs = rng.randint(0, 1)
        for slot_offset in range(num_side_inputs):
            slot_index = 1 + slot_offset
            # 30% chance this side input is itself a freeze block root.
            is_frozen_side = rng.random() < 0.30
            if is_frozen_side:
                num_members = rng.randint(2, 4)
                root_w = rng.randint(60, 140)
                widths = [root_w] + [rng.randint(60, 200) for _ in range(num_members - 1)]
                x_offsets = [0] + [
                    rng.choice([
                        rng.randint(-300, -60),
                        rng.randint(root_w + 20, root_w + 240),
                    ])
                    for _ in range(num_members - 1)
                ]
                y_offsets = [0] + [rng.randint(-200, -30) for _ in range(num_members - 1)]
                block, members = _make_freeze_block_with_geometry(
                    widths, x_offsets, y_offsets,
                    uuid_str=f"side-{iteration_id}-{spine_index}-{slot_index}",
                )
                side_root = members[0]
                all_blocks.append(block)
                dimension_overrides[id(side_root)] = block
                _wire(side_root, spine_node, slot=slot_index)
                description_parts.append(
                    f"side[{spine_index},{slot_index}]=FROZEN("
                    f"W={block.right_extent + block.left_overhang},"
                    f"L={block.left_overhang})"
                )
            else:
                # Plain side input — a single tile (place_only mode just
                # translates it as a unit).
                side_node = _StubNode(width=rng.randint(60, 140), height=28)
                _wire(side_node, spine_node, slot=slot_index)

    return spine_root, all_blocks, dimension_overrides, " | ".join(description_parts)


class TestHorizontalLayoutNoOverlapFuzz(unittest.TestCase):
    """End-to-end overlap property: after horizontal layout + restore, no
    frozen-block bbox intersects any other node bbox or any other block.

    This is the property the proxy refactor was built to enforce.  Failure
    here directly reproduces the user-reported bug class ("wide frozen node
    blocks overlapping adjacent subtrees") with a concrete fixture string.
    """

    def test_fuzz_no_overlap_after_horizontal_layout(self):
        seed = 0x0A1B2C3D
        rng = random.Random(seed)
        for iteration in range(DEFAULT_FUZZ_ITERATIONS):
            spine_root, all_blocks, dimension_overrides, description = (
                _build_horizontal_spine_with_freeze_blocks(rng, iteration)
            )

            # Run horizontal layout in place_only mode (no Dot creation, no
            # recursive vertical layout — keeps the fuzz harness independent
            # of Nuke runtime calls while still exercising every override site
            # touched by the proxy refactor).
            try:
                _nl.place_subtree_horizontal(
                    spine_root,
                    spine_x=0, spine_y=0,
                    snap_threshold=8,
                    node_count=20,
                    side_layout_mode="place_only",
                    dimension_overrides=dimension_overrides,
                )
                # Mirror layout_upstream's post-pass: restore non-root members
                # of every freeze block whose root was placed by the spine walk.
                for block in all_blocks:
                    block.restore_positions()
            except Exception as layout_exc:
                raise AssertionError(
                    f"layout raised on seed={seed:#x} iter={iteration}: "
                    f"{layout_exc!r} | {description}"
                ) from layout_exc

            # Collect bbox-of-interest objects:
            #   (a) one bbox per freeze block (spans all members)
            #   (b) one bbox per non-frozen node touched by layout
            block_member_ids = set()
            for block in all_blocks:
                for member in block.members:
                    block_member_ids.add(id(member))

            block_bboxes = [(_block_bbox(block), block) for block in all_blocks]

            non_frozen_node_bboxes = []
            for node in _nl.collect_subtree_nodes(spine_root):
                if id(node) in block_member_ids:
                    continue
                non_frozen_node_bboxes.append((_bbox(node), node))

            # No frozen block bbox overlaps any non-frozen node bbox.
            for block_bbox, block_obj in block_bboxes:
                for node_bbox, _node_obj in non_frozen_node_bboxes:
                    if _bboxes_overlap(block_bbox, node_bbox):
                        raise AssertionError(
                            f"FROZEN_NODE_OVERLAP seed={seed:#x} iter={iteration}\n"
                            f"  block uuid={block_obj.uuid} bbox={block_bbox}\n"
                            f"  node bbox={node_bbox}\n"
                            f"  fixture: {description}"
                        )

            # No two frozen blocks overlap each other.
            for outer_index in range(len(block_bboxes)):
                for inner_index in range(outer_index + 1, len(block_bboxes)):
                    box_a, block_a = block_bboxes[outer_index]
                    box_b, block_b = block_bboxes[inner_index]
                    if _bboxes_overlap(box_a, box_b):
                        raise AssertionError(
                            f"FROZEN_BLOCK_OVERLAP seed={seed:#x} iter={iteration}\n"
                            f"  block_a uuid={block_a.uuid} bbox={box_a}\n"
                            f"  block_b uuid={block_b.uuid} bbox={box_b}\n"
                            f"  fixture: {description}"
                        )


# ---------------------------------------------------------------------------
# Property — compute_horizontal_chain_extents is consistent with the
# place_subtree_horizontal pre-pass.
# ---------------------------------------------------------------------------


class TestHorizontalChainExtents(unittest.TestCase):
    """``compute_horizontal_chain_extents`` is the pre-placement helper that
    ``layout_upstream`` and ``layout_selected`` use to size spine_x.  These
    unit tests pin the helper's contract on representative fixtures with
    hand-computed expected values so a regression in either the helper or
    the proxy lookup it uses surfaces immediately.

    Coverage:
      * Empty / singleton spine — zero extent.
      * Multi-node spine of plain nodes — matches the legacy screen-width sum.
      * Spine with a wide freeze block on an intermediate node — extent
        widens by the block's right_extent (replacing screenWidth) and by
        the block's left_overhang (added separately).
      * Spine with a side input — extent widens by the side input's
        contribution past the spine node.

    The pure unit-test approach was chosen over a property/fuzz test
    because the latter has to reconstruct the full pre-pass logic in the
    fixture, which loops back to "two implementations of the same math"
    — exactly what the helper exists to prevent.
    """

    def setUp(self):
        self.prefs = _node_layout_prefs_module.prefs_singleton
        self.snap_threshold = 8
        self.scheme_multiplier = self.prefs.get("normal_multiplier")
        self.step_x = int(
            self.prefs.get("horizontal_subtree_gap") * self.scheme_multiplier
        )

    def _call_helper(self, spine_nodes_ordered, dimension_overrides=None):
        return _nl.compute_horizontal_chain_extents(
            spine_nodes_ordered, self.snap_threshold, node_count=10,
            scheme_multiplier=self.scheme_multiplier,
            current_prefs=self.prefs,
            dimension_overrides=dimension_overrides,
        )

    def test_empty_spine_yields_zero(self):
        """An empty spine has no leftward extent past a non-existent root."""
        self.assertEqual(self._call_helper([]), 0)

    def test_single_node_spine_yields_zero(self):
        """The root contributes nothing leftward of itself."""
        single_node = _StubNode(width=80, height=28)
        self.assertEqual(self._call_helper([single_node]), 0)

    def test_two_node_spine_normal_nodes(self):
        """Two normal spine nodes: extent = step_x + spine[1].screenWidth().

        This is the legacy formula that ``layout_upstream`` previously
        inlined.  The helper must reproduce it exactly when no freeze
        blocks or side inputs are involved — otherwise plain horizontal
        chains regress.
        """
        spine_root = _StubNode(width=120, height=28)
        spine_upstream = _StubNode(width=80, height=28)
        _wire(spine_upstream, spine_root, slot=0)
        expected = self.step_x + 80
        self.assertEqual(self._call_helper([spine_root, spine_upstream]), expected)

    def test_three_node_spine_normal_nodes(self):
        """Three normal spine nodes: extent = sum(step_x + W[i]) for i=1,2."""
        spine_root = _StubNode(width=120, height=28)
        spine_mid = _StubNode(width=90, height=28)
        spine_far = _StubNode(width=70, height=28)
        _wire(spine_mid, spine_root, slot=0)
        _wire(spine_far, spine_mid, slot=0)
        expected = (self.step_x + 90) + (self.step_x + 70)
        self.assertEqual(
            self._call_helper([spine_root, spine_mid, spine_far]), expected
        )

    def test_freeze_block_on_intermediate_spine_widens_extent(self):
        """A freeze block on an intermediate spine node contributes its
        right_extent (replacing screenWidth) AND its left_overhang
        (added separately as the node's leftward bbox extent).  The helper
        must combine both to reproduce ``place_subtree_horizontal``'s
        advance formula.
        """
        spine_root = _StubNode(width=120, height=28)
        # Build a freeze block whose root is the middle spine node.  The
        # block extends 200 left of the root and 80 right of the root —
        # so right_extent = 80 (since root.W=80) and left_overhang = 200.
        block, members = _make_freeze_block_with_geometry(
            member_widths=[80, 60],
            member_x_offsets=[0, -200],   # extra member sits 200 left of root
            member_y_offsets=[0, -100],
            uuid_str="middle-block",
        )
        spine_mid_block_root = members[0]
        # Wire spine: root.input(0) = block_root.  Don't rely on block's
        # internal _wire (which would otherwise be overwritten anyway).
        _wire(spine_mid_block_root, spine_root, slot=0)
        spine_far = _StubNode(width=70, height=28)
        _wire(spine_far, spine_mid_block_root, slot=0)
        dimension_overrides = {id(spine_mid_block_root): block}

        # Expected:
        #   effective_widths = [120, max(80, right_extent=80), 70]
        #   left_extents     = [0,   max(0,  left_overhang=200), 0]
        #   intermediate_step_total = (step_x + 80) + (step_x + 70)
        #   leftward_overhang_total = 0 + 200 + 0 = 200
        expected = (self.step_x + 80) + (self.step_x + 70) + 200
        self.assertEqual(
            self._call_helper(
                [spine_root, spine_mid_block_root, spine_far],
                dimension_overrides=dimension_overrides,
            ),
            expected,
            "Freeze block left_overhang must be added to the chain's "
            "total leftward extent — without it spine_x lands too close "
            "to the consumer.",
        )

    def test_side_input_on_spine_node_widens_left_extent_when_wider_than_spine(self):
        """A side input wider than its spine node extends the chain leftward.

        ``place_subtree_horizontal`` centers a side input above its spine
        node; if the side input is wider, it overhangs both edges.  The
        leftward overhang past the spine node's left edge feeds into
        ``left_extents[i]`` and therefore into the helper's result.
        """
        spine_root = _StubNode(width=80, height=28)
        spine_upstream = _StubNode(width=80, height=28)
        _wire(spine_upstream, spine_root, slot=0)
        # Side input wider than spine — overhangs by (W_side - W_spine)/2
        # on each edge.  W_side=200, W_spine=80 → overhang = 60 each side.
        wide_side_input = _StubNode(width=200, height=28)
        _wire(wide_side_input, spine_root, slot=1)
        # Expected:
        #   effective_widths[0] = max(80, centering_offset + 200 - 0) where
        #     centering_offset = (80 - 200) // 2 = -60
        #     right_extent = -60 + 200 - 0 = 140
        #   effective_widths[0] = max(80, 140) = 140 (relevant for [1] use)
        #   left_extents[0] = max(0, 0 - (-60)) = 60
        #   intermediate_step_total = step_x + spine_upstream.W = step_x + 80
        #   leftward_overhang_total = 60 + 0 = 60
        # The side input's rightward extent only affects effective_widths[0],
        # which contributes to spacing IF there were a downstream consumer
        # — for this leftward-extent helper, only its leftward overhang
        # matters.
        expected = (self.step_x + 80) + 60
        self.assertEqual(
            self._call_helper([spine_root, spine_upstream]),
            expected,
            "Side input wider than its spine node must contribute its "
            "leftward overhang to the chain's leftward extent.",
        )


if __name__ == "__main__":
    unittest.main()
