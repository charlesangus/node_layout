"""Shared stub Nuke module + scenario builders for the compare_engines harness.

Imported at module-load time by ``compare_engines.py`` so that ``import nuke``
inside ``node_layout`` resolves to this stub. Provides just enough surface for
the layout pipeline to run end-to-end on synthetic graphs.

Stub design
-----------
Each scenario creates a fresh ``Universe`` containing a list of nodes. The
universe is registered as the live Nuke graph so that ``nuke.allNodes``,
``nuke.selectedNode``, ``nuke.lastHitGroup().nodes()`` all return the right
list. Nodes can be wired with ``setInput``; ``inputs()`` returns the highest
slot index + 1, mirroring real Nuke behaviour.

Coordinate convention
---------------------
Positive Y is DOWN in Nuke's DAG (CLAUDE.md). Inputs sit at smaller Y values
than the nodes they feed.
"""
from __future__ import annotations

import json
import os
import sys
import types
import uuid
from typing import Optional

# ---------------------------------------------------------------------------
# Stub primitives
# ---------------------------------------------------------------------------

class _Knob:
    def __init__(self, val=0, name=""):
        self._val = val
        self.name = name

    def value(self):
        return self._val

    def getValue(self):
        return self._val

    def setValue(self, value):
        self._val = value

    def setFlag(self, flag):
        pass


class _IntKnob(_Knob):
    pass


class _StringKnob(_Knob):
    def __init__(self, name="", label=""):
        super().__init__(val="", name=name)


class _TabKnob:
    def __init__(self, name="", label=""):
        self.name = name

    def setFlag(self, flag):
        pass


class _Node:
    """Stub for a Nuke Node with x/y, knobs, inputs, name, class."""
    def __init__(
        self,
        node_class: str = "Grade",
        name: Optional[str] = None,
        width: int = 80,
        height: int = 28,
        xpos: int = 0,
        ypos: int = 0,
        max_inputs: int = 1,
    ):
        self._class = node_class
        self._name = name or f"{node_class}_{id(self)}"
        self._width = width
        self._height = height
        self._xpos = xpos
        self._ypos = ypos
        self._inputs: list[Optional["_Node"]] = [None] * max_inputs
        self._knobs: dict = {
            "tile_color": _Knob(0, "tile_color"),
            "selected": _Knob(False, "selected"),
        }

    # Geometry
    def screenWidth(self): return self._width
    def screenHeight(self): return self._height
    def xpos(self): return self._xpos
    def ypos(self): return self._ypos
    def setXpos(self, v): self._xpos = int(v)
    def setYpos(self, v): self._ypos = int(v)
    def setXYpos(self, x, y):
        self._xpos = int(x)
        self._ypos = int(y)

    # Class / name
    def Class(self): return self._class
    def name(self): return self._name
    def setName(self, n): self._name = n
    def fullName(self): return self._name

    # Inputs
    def inputs(self): return len(self._inputs)
    def input(self, i):
        if 0 <= i < len(self._inputs):
            return self._inputs[i]
        return None

    def setInput(self, i, node):
        while len(self._inputs) <= i:
            self._inputs.append(None)
        self._inputs[i] = node

    def inputLabel(self, i):
        # Default merge-like labelling so _is_mask_input recognises slot 2.
        if self._class in ("Merge2", "Dissolve"):
            return ["B", "A", "mask"][i] if i < 3 else f"A{i - 1}"
        return ""

    # Knobs
    def knob(self, name):
        return self._knobs.get(name)

    def addKnob(self, knob):
        kn = getattr(knob, "name", None)
        if kn:
            self._knobs[kn] = knob

    def removeKnob(self, knob):
        kn = getattr(knob, "name", None)
        if kn and kn in self._knobs:
            del self._knobs[kn]

    def __getitem__(self, name):
        if name not in self._knobs:
            self._knobs[name] = _Knob(0, name)
        return self._knobs[name]

    def knobs(self):
        return self._knobs


class _PreferencesNode(_Node):
    def __init__(self):
        super().__init__(node_class="Preferences", name="preferences")
        self._knobs["dag_snap_threshold"] = _Knob(8, "dag_snap_threshold")
        self._knobs["NodeColor"] = _Knob(0, "NodeColor")


# ---------------------------------------------------------------------------
# Universe — the active stub-Nuke "session"
# ---------------------------------------------------------------------------

class Universe:
    """Holds the active node list, selection, and group context for a scenario."""

    def __init__(self):
        self.nodes: list[_Node] = []
        self.selected: list[_Node] = []
        self.preferences = _PreferencesNode()

    def add(self, node: _Node) -> _Node:
        self.nodes.append(node)
        return node

    def select(self, *nodes):
        for n in self.nodes:
            n["selected"].setValue(False)
        for n in nodes:
            n["selected"].setValue(True)
        self.selected = list(nodes)


_active_universe: Universe = Universe()


def set_universe(u: Universe):
    global _active_universe
    _active_universe = u


def get_universe() -> Universe:
    return _active_universe


# ---------------------------------------------------------------------------
# Stub nuke module
# ---------------------------------------------------------------------------

class _Undo:
    name_ = ""
    @staticmethod
    def name(label):
        _Undo.name_ = label
    @staticmethod
    def begin(): pass
    @staticmethod
    def end(): pass
    @staticmethod
    def cancel(): pass


class _GroupContext:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def nodes(self):
        return list(_active_universe.nodes)


class _Nodes:
    def Dot(self):
        dot = _Node(node_class="Dot", width=12, height=12, max_inputs=1)
        _active_universe.add(dot)
        return dot


def _all_nodes(*args, **kwargs):
    return list(_active_universe.nodes)


def _selected_nodes():
    return [n for n in _active_universe.nodes if n["selected"].getValue()]


def _selected_node():
    sn = _selected_nodes()
    return sn[0] if sn else None


def _to_node(name):
    if name == "preferences":
        return _active_universe.preferences
    for n in _active_universe.nodes:
        if n.name() == name:
            return n
    return None


def install_nuke_stub():
    """Install the stub nuke module into sys.modules."""
    nuke_stub = types.ModuleType("nuke")
    nuke_stub.Node = _Node
    nuke_stub.allNodes = _all_nodes
    nuke_stub.selectedNodes = _selected_nodes
    nuke_stub.selectedNode = _selected_node
    nuke_stub.toNode = _to_node
    nuke_stub.menu = lambda name: None
    nuke_stub.Undo = _Undo
    nuke_stub.INVISIBLE = 0x01
    nuke_stub.lastHitGroup = lambda: _GroupContext()
    nuke_stub.Tab_Knob = _TabKnob
    nuke_stub.String_Knob = _StringKnob
    nuke_stub.Int_Knob = _IntKnob
    nuke_stub.nodes = _Nodes()
    nuke_stub.createNode = lambda cls, inpanel=False: _active_universe.add(
        _Node(node_class=cls)
    )
    sys.modules["nuke"] = nuke_stub
    return nuke_stub


# ---------------------------------------------------------------------------
# Helpers for scenarios
# ---------------------------------------------------------------------------

def set_node_state(node, mode="vertical", scheme="normal", freeze_group=None,
                   h_scale=1.0, v_scale=1.0):
    """Write a node_layout_state knob directly (no nuke calls needed)."""
    state = {
        "mode": mode,
        "scheme": scheme,
        "h_scale": h_scale,
        "v_scale": v_scale,
        "freeze_group": freeze_group,
    }
    state_knob = _StringKnob("node_layout_state", "")
    state_knob.setValue(json.dumps(state))
    node._knobs["node_layout_state"] = state_knob
    node._knobs["node_layout_tab"] = _TabKnob("node_layout_tab", "")


def collect_all_node_positions(universe: Universe) -> dict[str, dict]:
    """Map node-name -> {xpos, ypos, class, width, height}."""
    out = {}
    for n in universe.nodes:
        out[n.name()] = {
            "xpos": n.xpos(),
            "ypos": n.ypos(),
            "class": n.Class(),
            "width": n.screenWidth(),
            "height": n.screenHeight(),
        }
    return out


# ---------------------------------------------------------------------------
# Scenario builders. Each returns (root_node, selected_list, universe).
# ---------------------------------------------------------------------------

def _make_chain(universe, classes, base_x=0, base_y=0, step=60):
    """Helper: vertical chain Read -> ... -> Write."""
    nodes = []
    y = base_y
    prev = None
    for idx, cls in enumerate(classes):
        n = _Node(node_class=cls, name=f"{cls}_{idx}", xpos=base_x, ypos=y)
        universe.add(n)
        if prev is not None:
            n.setInput(0, prev)
        prev = n
        nodes.append(n)
        y += step
    return nodes


def scenario_vertical_chain():
    """Read -> Grade -> Blur -> Write."""
    u = Universe()
    nodes = _make_chain(u, ["Read", "Grade", "Blur", "Write"])
    write = nodes[-1]
    u.select(write)
    return write, [write], u


def scenario_vertical_3input_merge():
    """3 reads feeding a Merge3 (fan mode trigger)."""
    u = Universe()
    r0 = u.add(_Node(node_class="Read", name="R0", xpos=0, ypos=0))
    r1 = u.add(_Node(node_class="Read", name="R1", xpos=200, ypos=0))
    r2 = u.add(_Node(node_class="Read", name="R2", xpos=400, ypos=0))
    merge = u.add(_Node(node_class="Merge2", name="Merge", xpos=200, ypos=200,
                        max_inputs=3))
    merge.setInput(0, r0)
    merge.setInput(1, r1)
    merge.setInput(2, r2)
    write = u.add(_Node(node_class="Write", name="Write", xpos=200, ypos=300))
    write.setInput(0, merge)
    u.select(write)
    return write, [write], u


def scenario_vertical_with_mask():
    """Read -> Grade -> (B); Read -> Mask -> (mask slot of Merge2)."""
    u = Universe()
    r0 = u.add(_Node(node_class="Read", name="R0", xpos=0, ypos=0))
    r1 = u.add(_Node(node_class="Read", name="R1", xpos=200, ypos=0))
    grade = u.add(_Node(node_class="Grade", name="Grade", xpos=0, ypos=60))
    grade.setInput(0, r0)
    mask = u.add(_Node(node_class="Grade", name="MaskGrade", xpos=200, ypos=60))
    mask.setInput(0, r1)
    merge = u.add(_Node(node_class="Merge2", name="Merge", xpos=0, ypos=120,
                        max_inputs=3))
    merge.setInput(0, grade)
    merge.setInput(2, mask)  # mask slot
    write = u.add(_Node(node_class="Write", name="Write", xpos=0, ypos=180))
    write.setInput(0, merge)
    u.select(write)
    return write, [write], u


def scenario_freeze_basic():
    """Read -> Grade* -> Blur* -> Write; Grade and Blur frozen together."""
    u = Universe()
    nodes = _make_chain(u, ["Read", "Grade", "Blur", "Write"])
    grade, blur = nodes[1], nodes[2]
    write = nodes[-1]
    g = str(uuid.uuid4())
    set_node_state(grade, freeze_group=g)
    set_node_state(blur, freeze_group=g)
    u.select(write)
    return write, [write], u


def scenario_freeze_with_side():
    """Read -> Grade* -> Merge* (B); Read -> CC -> Merge (A); Merge -> Write.
    Grade and Merge frozen together."""
    u = Universe()
    r1 = u.add(_Node(node_class="Read", name="R1", xpos=0, ypos=0))
    grade = u.add(_Node(node_class="Grade", name="Grade", xpos=0, ypos=60))
    grade.setInput(0, r1)
    r2 = u.add(_Node(node_class="Read", name="R2", xpos=150, ypos=0))
    cc = u.add(_Node(node_class="ColorCorrect", name="CC", xpos=150, ypos=60))
    cc.setInput(0, r2)
    merge = u.add(_Node(node_class="Merge2", name="Merge", xpos=0, ypos=120,
                        max_inputs=2))
    merge.setInput(0, grade)
    merge.setInput(1, cc)
    write = u.add(_Node(node_class="Write", name="Write", xpos=0, ypos=180))
    write.setInput(0, merge)
    g = str(uuid.uuid4())
    set_node_state(grade, freeze_group=g)
    set_node_state(merge, freeze_group=g)
    u.select(write)
    return write, [write], u


def scenario_freeze_two_groups():
    """Two parallel frozen branches feed into a Merge."""
    u = Universe()
    r1 = u.add(_Node(node_class="Read", name="R1", xpos=0, ypos=0))
    g1 = u.add(_Node(node_class="Grade", name="G1", xpos=0, ypos=60))
    g1.setInput(0, r1)
    b1 = u.add(_Node(node_class="Blur", name="B1", xpos=0, ypos=120))
    b1.setInput(0, g1)
    r2 = u.add(_Node(node_class="Read", name="R2", xpos=150, ypos=0))
    g2 = u.add(_Node(node_class="Grade", name="G2", xpos=150, ypos=60))
    g2.setInput(0, r2)
    b2 = u.add(_Node(node_class="Blur", name="B2", xpos=150, ypos=120))
    b2.setInput(0, g2)
    merge = u.add(_Node(node_class="Merge2", name="Merge", xpos=0, ypos=180,
                        max_inputs=2))
    merge.setInput(0, b1)
    merge.setInput(1, b2)
    write = u.add(_Node(node_class="Write", name="Write", xpos=0, ypos=240))
    write.setInput(0, merge)
    set_node_state(g1, freeze_group=str(uuid.uuid4()))
    set_node_state(b1, freeze_group=g1.knob("node_layout_state").value() and
                   json.loads(g1["node_layout_state"].getValue())["freeze_group"])
    # Re-read g1's UUID to match
    g1_uuid = json.loads(g1["node_layout_state"].getValue())["freeze_group"]
    set_node_state(b1, freeze_group=g1_uuid)
    g2_uuid = str(uuid.uuid4())
    set_node_state(g2, freeze_group=g2_uuid)
    set_node_state(b2, freeze_group=g2_uuid)
    u.select(write)
    return write, [write], u


def scenario_horizontal_chain():
    """Three-node horizontal chain with selected vertical consumer downstream."""
    u = Universe()
    n = u.add(_Node(node_class="Read", name="N", xpos=0, ypos=0))
    m2 = u.add(_Node(node_class="Grade", name="M2", xpos=80, ypos=0))
    m2.setInput(0, n)
    m1 = u.add(_Node(node_class="Write", name="M1", xpos=400, ypos=0))
    m1.setInput(0, m2)
    set_node_state(m2, mode="horizontal")
    set_node_state(n, mode="horizontal")
    u.select(m1)
    return m1, [m1], u


def scenario_diamond():
    """Diamond: A -> B -> D and A -> C -> D (A reaches D via two paths)."""
    u = Universe()
    a = u.add(_Node(node_class="Read", name="A", xpos=0, ypos=0))
    b = u.add(_Node(node_class="Grade", name="B", xpos=0, ypos=60))
    b.setInput(0, a)
    c = u.add(_Node(node_class="Blur", name="C", xpos=200, ypos=60))
    c.setInput(0, a)
    d = u.add(_Node(node_class="Merge2", name="D", xpos=0, ypos=120,
                    max_inputs=2))
    d.setInput(0, b)
    d.setInput(1, c)
    write = u.add(_Node(node_class="Write", name="Write", xpos=0, ypos=180))
    write.setInput(0, d)
    u.select(write)
    return write, [write], u


SCENARIO_BUILDERS = {
    "vertical_chain": scenario_vertical_chain,
    "vertical_3input_merge": scenario_vertical_3input_merge,
    "vertical_with_mask": scenario_vertical_with_mask,
    "freeze_basic": scenario_freeze_basic,
    "freeze_with_side": scenario_freeze_with_side,
    "freeze_two_groups": scenario_freeze_two_groups,
    "horizontal_chain": scenario_horizontal_chain,
    "diamond": scenario_diamond,
}


# ---------------------------------------------------------------------------
# Bbox / overlap sanity
# ---------------------------------------------------------------------------

def find_overlapping_node_pairs(universe: Universe) -> list[tuple[str, str]]:
    """Return list of (name_a, name_b) for any pair of distinct nodes whose
    tile rectangles overlap. Used as a sanity check."""
    pairs = []
    nodes = universe.nodes
    for i in range(len(nodes)):
        a = nodes[i]
        a_l = a.xpos()
        a_t = a.ypos()
        a_r = a_l + a.screenWidth()
        a_b = a_t + a.screenHeight()
        for j in range(i + 1, len(nodes)):
            b = nodes[j]
            b_l = b.xpos()
            b_t = b.ypos()
            b_r = b_l + b.screenWidth()
            b_b = b_t + b.screenHeight()
            if a_l < b_r and b_l < a_r and a_t < b_b and b_t < a_b:
                pairs.append((a.name(), b.name()))
    return pairs


# Avoid linter complaints about unused imports
_ = (os, Optional)
