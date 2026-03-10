# Phase 7: Per-Node State Storage - Research

**Researched:** 2026-03-10
**Domain:** Nuke Python API — addKnob/String_Knob, JSON serialization, knob flags, layout engine integration
**Confidence:** HIGH

## Summary

Phase 7 embeds a hidden `String_Knob` on every node touched by a layout operation. The knob stores a JSON string recording the layout scheme, mode, and scale factors; it uses the `INVISIBLE` flag (not `DO_NOT_WRITE`) so Nuke writes it to the `.nk` file on save. All decisions are locked in CONTEXT.md — there is no design uncertainty here, only implementation sequencing.

The core integration challenge is the `scheme_multiplier=None` path in `layout_upstream()` and `layout_selected()`. Today, `None` means "use normal_multiplier". After Phase 7, `None` means "read stored scheme from each node individually." This requires collecting all subtree nodes before placement, resolving per-node schemes, and — critically — updating the `compute_dims()` memo key from `id(node)` to `(id(node), scheme_for_node)` to prevent cache collisions when a shared node appears in subtrees with different stored schemes.

The existing test strategy (AST-based structural tests + stub-based behavioral tests, both runnable with `python3.11 -m unittest discover`) applies directly to Phase 7. The new `node_layout_state.py` helper module can be tested without Nuke stubs because it operates only on plain Python dicts and strings; the knob read/write calls in `node_layout.py` are best covered by AST structural tests.

**Primary recommendation:** Implement in five discrete tasks: (1) state helpers module, (2) state-write pass in layout entry points, (3) scheme-read-and-replay in layout entry points plus memo-key fix, (4) scale state integration, (5) clear-state commands and menu registration.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**State knob structure**
- One `String_Knob('node_layout_state', 'Node Layout State')` per node, on a `node_layout_tab` tab
- Value is a JSON string: `{"scheme": "compact", "mode": "vertical", "h_scale": 0.8, "v_scale": 1.0}`
- Absent keys fall back to defaults (scheme=normal, mode=vertical, h_scale=1.0, v_scale=1.0)
- `INVISIBLE` flag set — hidden from Properties panel but NOT `DO_NOT_WRITE` (which blocks .nk persistence)
- All layout-touched nodes receive the knob, including diamond-resolution Dot nodes (no special-casing)
- Phase 7 always writes `"mode": "vertical"` — Phase 11 changes this to `"horizontal"` on affected nodes

**Scheme storage format**
- Stored as string enum: `"compact"`, `"normal"`, or `"loose"`
- Decoupled from pref multiplier values — stored scheme resolves to the current pref value at replay time
- Extensible: future state fields (e.g. `"horizontal"` mode, additional scale axes) are new JSON keys

**Scheme replay logic**
- `scheme_multiplier=None` at entry point now means: read stored scheme from each node, not "use normal"
- Each node uses its own stored scheme (per-node, not per-subtree-root)
- `compute_dims()` reads stored scheme from each node mid-recursion; memo key becomes `(id(node), scheme_for_node)` to prevent cache collisions on shared nodes
- Explicit scheme command (e.g. `layout_upstream_compact()`) overrides stored scheme AND writes the new scheme back to all affected nodes — so next unspecified re-layout replays the override
- Nodes with no stored state (first-ever layout): fall back to `normal_multiplier`

**Scale factor semantics**
- `h_scale` and `v_scale` stored separately in JSON (supporting Phase 10's axis-specific shrink/expand)
- Shrink/Expand multiplies into existing stored scale (accumulates): `0.8 × 0.8 = 0.64`
- Re-layout replays the stored scale factor alongside scheme — reproduces both compact scheme AND accumulated scale
- A fresh layout run (after clear state) starts at scale 1.0

**Clear state commands**
- Two new commands: `"Clear Layout State Selected"` and `"Clear Layout State Upstream"`
- Removes `node_layout_state` knob from each affected node; removes `node_layout_tab` tab if no other knobs remain on it
- After clear, next layout runs fresh: normal scheme, scale 1.0
- Registered in menu.py alongside existing layout commands

### Claude's Discretion
- How the JSON parse/write helpers are structured (module-level functions vs inline)
- Whether `node_layout_tab` is added fresh if absent, or assumed present on any node that already went through layout

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STATE-01 | Every node touched by a layout operation receives a hidden tab with knobs storing: layout mode, scheme (compact/normal/loose), and scale factor | Implemented via `String_Knob` with `INVISIBLE` flag on `node_layout_tab`; write pass after `place_subtree()` completes |
| STATE-02 | Hidden state knobs persist across .nk script save/close/reopen cycles | Confirmed: `INVISIBLE` flag alone does not block .nk persistence; `DO_NOT_WRITE` must NOT be set |
| STATE-03 | Re-running a layout command replays the stored scheme unless the command explicitly specifies one | Entry-point reads per-node stored scheme when `scheme_multiplier=None`; explicit entry points override and write-back |
| STATE-04 | Shrink/Expand commands update the scale factor knob on affected nodes | Scale functions read current `h_scale`/`v_scale`, accumulate the factor, write back |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `nuke` (Python API) | Nuke 11+ | `addKnob`, `removeKnob`, `String_Knob`, `Tab_Knob`, `INVISIBLE` flag | Only way to add persistent per-node data in Nuke |
| `json` (stdlib) | Python 3.x | Serialize/deserialize the state dict | Zero deps, human-readable, extensible |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ast` (stdlib) | Python 3.x | AST-based structural tests | For verifying code structure without Nuke runtime |
| `unittest` (stdlib) | Python 3.x | Test framework (no pytest installed) | All tests in this project |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `String_Knob` + JSON | Multiple `Double_Knob` / `Enumeration_Knob` fields | Multiple knobs require individual `addKnob` calls; harder to extend; JSON in one String_Knob is simpler and was explicitly decided |
| `INVISIBLE` flag | `DO_NOT_WRITE` | `DO_NOT_WRITE` blocks .nk persistence — this is explicitly the wrong choice |

**Installation:** No new packages — `nuke` and `json` are already present.

## Architecture Patterns

### Recommended Project Structure

No new files strictly required; the JSON helpers can live in a new `node_layout_state.py` module (testable without Nuke) or as private functions in `node_layout.py`. Given Claude's Discretion on this, a separate `node_layout_state.py` is recommended for testability.

```
node_layout_state.py     # pure-Python state helpers (read/write/clear JSON, resolve scheme)
node_layout.py           # integration: calls state helpers at entry points and after place_subtree
menu.py                  # registers two new Clear State commands
tests/
  test_node_layout_state.py    # pure-Python tests, no Nuke stub needed
  test_state_integration.py    # AST structural tests for node_layout.py integration points
```

### Pattern 1: Knob Add-if-Absent

The existing diamond-dot pattern (lines 252–276 in node_layout.py) sets the precedent: add a `Tab_Knob('node_layout_tab')` then the specialized knob. For state, the tab may already exist (from a prior layout run). The safe pattern is:

```python
# Source: existing insert_dot_nodes() pattern, node_layout.py lines 252–257
if node.knob('node_layout_tab') is None:
    node.addKnob(nuke.Tab_Knob('node_layout_tab', 'Node Layout'))
if node.knob('node_layout_state') is None:
    state_knob = nuke.String_Knob('node_layout_state', 'Node Layout State')
    state_knob.setFlag(nuke.INVISIBLE)
    node.addKnob(state_knob)
```

**Why:** `addKnob` on a tab that already exists silently becomes a no-op in Nuke; attempting to add a knob whose name already exists raises a RuntimeError. Guard both with `knob() is None` checks.

### Pattern 2: State Read with Defaults

```python
# node_layout_state.py — pure Python, testable without Nuke
import json

_DEFAULT_STATE = {
    "scheme": "normal",
    "mode": "vertical",
    "h_scale": 1.0,
    "v_scale": 1.0,
}

def read_node_state(node):
    """Return the state dict for node, falling back to defaults for absent keys."""
    knob = node.knob('node_layout_state')
    if knob is None:
        return dict(_DEFAULT_STATE)
    raw = knob.value()
    if not raw:
        return dict(_DEFAULT_STATE)
    try:
        stored = json.loads(raw)
    except (ValueError, TypeError):
        return dict(_DEFAULT_STATE)
    state = dict(_DEFAULT_STATE)
    state.update(stored)
    return state

def write_node_state(node, state):
    """Write state dict as JSON to the node_layout_state knob, creating knob+tab if absent."""
    import nuke
    if node.knob('node_layout_tab') is None:
        node.addKnob(nuke.Tab_Knob('node_layout_tab', 'Node Layout'))
    if node.knob('node_layout_state') is None:
        state_knob = nuke.String_Knob('node_layout_state', 'Node Layout State')
        state_knob.setFlag(nuke.INVISIBLE)
        node.addKnob(state_knob)
    node['node_layout_state'].setValue(json.dumps(state))

def clear_node_state(node):
    """Remove the node_layout_state knob (and tab if empty) from node."""
    state_knob = node.knob('node_layout_state')
    if state_knob is not None:
        node.removeKnob(state_knob)
    tab_knob = node.knob('node_layout_tab')
    if tab_knob is not None:
        # Only remove tab if no other knobs remain on it.
        # Heuristic: check for node_layout_diamond_dot as the only other known occupant.
        if node.knob('node_layout_diamond_dot') is None:
            node.removeKnob(tab_knob)

def scheme_name_to_multiplier(scheme_name, prefs):
    """Resolve a stored scheme string to its current pref multiplier value."""
    mapping = {
        "compact": "compact_multiplier",
        "normal": "normal_multiplier",
        "loose": "loose_multiplier",
    }
    pref_key = mapping.get(scheme_name, "normal_multiplier")
    return prefs.get(pref_key)

def multiplier_to_scheme_name(scheme_multiplier, prefs):
    """Map a scheme_multiplier float back to its string name for storage.

    Compares against current pref values. Falls back to 'normal' if no match.
    """
    for scheme_name, pref_key in [
        ("compact", "compact_multiplier"),
        ("normal", "normal_multiplier"),
        ("loose", "loose_multiplier"),
    ]:
        if abs(scheme_multiplier - prefs.get(pref_key)) < 1e-9:
            return scheme_name
    return "normal"
```

### Pattern 3: Per-Node Scheme Resolution at Entry Points

State reads happen ONCE at entry points, before the recursive passes. The resolved multiplier is passed down as an explicit parameter (same as today's `scheme_multiplier` thread).

```python
# In layout_upstream() — new state-read block added after insert_dot_nodes()
# and before compute_dims():
subtree_nodes = collect_subtree_nodes(root)
per_node_scheme = {}  # id(node) -> float multiplier
for subtree_node in subtree_nodes:
    if scheme_multiplier is not None:
        # Explicit command: override with the passed-in multiplier
        per_node_scheme[id(subtree_node)] = scheme_multiplier
    else:
        # Replay: read stored scheme from this node
        stored_state = node_layout_state.read_node_state(subtree_node)
        per_node_scheme[id(subtree_node)] = node_layout_state.scheme_name_to_multiplier(
            stored_state["scheme"], node_layout_prefs.prefs_singleton
        )
```

**Key constraint from CONTEXT.md:** `compute_dims()` memo key must become `(id(node), scheme_for_node)` to prevent cache collisions. When the same node appears in two subtrees with different stored schemes (e.g., a shared merge input), the current `id(node)` key would return the first-computed result for both.

### Pattern 4: State Write-Back Pass

After `place_subtree()` completes (and all Dot nodes have been inserted), walk the final subtree and write state to every node:

```python
# After place_subtree() in layout_upstream():
final_subtree_nodes = collect_subtree_nodes(root)
for subtree_node in final_subtree_nodes:
    node_scheme_multiplier = per_node_scheme.get(
        id(subtree_node),
        node_layout_prefs.prefs_singleton.get("normal_multiplier")
    )
    scheme_name = node_layout_state.multiplier_to_scheme_name(
        node_scheme_multiplier, node_layout_prefs.prefs_singleton
    )
    stored_state = node_layout_state.read_node_state(subtree_node)
    stored_state["scheme"] = scheme_name
    stored_state["mode"] = "vertical"
    node_layout_state.write_node_state(subtree_node, stored_state)
```

**Note:** h_scale and v_scale are NOT reset by a re-layout — only Shrink/Expand writes those. Re-layout reads them (for future Phase 10 replay) but preserves the existing value.

### Pattern 5: Scale State Accumulation

In `_scale_selected_nodes()` and `_scale_upstream_nodes()`, after moving nodes, write accumulated scale back:

```python
# At end of _scale_selected_nodes(scale_factor):
for node in selected_nodes:
    stored_state = node_layout_state.read_node_state(node)
    stored_state["h_scale"] = round(stored_state["h_scale"] * scale_factor, 10)
    stored_state["v_scale"] = round(stored_state["v_scale"] * scale_factor, 10)
    node_layout_state.write_node_state(node, stored_state)
```

**Rounding:** Use `round(..., 10)` to prevent floating-point drift across many accumulations.

### Anti-Patterns to Avoid

- **Reading stored state inside `compute_dims()`:** State reads are Nuke API calls. They must not happen mid-recursion inside tight loops. Read at entry points, pass as resolved values.
- **Setting `DO_NOT_WRITE` flag:** Explicitly blocks .nk persistence. Never set on state knobs.
- **Using a module-level `scheme_multiplier` global to thread per-node state:** The existing pattern threads as explicit function parameters. Per-node state follows the same approach (a `per_node_scheme` dict passed or captured in closure scope at entry points).
- **Removing `node_layout_tab` when `node_layout_diamond_dot` still exists:** Diamond-dot Dots share the tab. Only remove the tab when no other known knobs occupy it.
- **Not guarding `addKnob` with `knob() is None`:** Adding a knob that already exists raises `RuntimeError` in Nuke.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization | Custom string format (pipe-delimited, etc.) | `json.dumps` / `json.loads` | stdlib, human-readable, extensible with new keys |
| Per-node persistent storage | Module-level dict keyed by node name | `String_Knob` on the node | Module dict is lost on script reopen; knob persists in .nk |

**Key insight:** Nuke's `.nk` format is the persistence layer. Any state that must survive save/close/reopen must live on the node itself as a knob.

## Common Pitfalls

### Pitfall 1: DO_NOT_WRITE Flag Blocks Persistence

**What goes wrong:** Developer sets `nuke.DO_NOT_WRITE` thinking it only hides the knob from the UI, then discovers state is gone after save/reopen.
**Why it happens:** `DO_NOT_WRITE` is named as "do not write to .nk file" — it means exactly that.
**How to avoid:** Use `nuke.INVISIBLE` only. This hides the knob from Properties panel but still writes to .nk.
**Warning signs:** State disappears after File > Save + File > Open; knob not visible in script editor's node readout.

### Pitfall 2: Memo Key Collision on Shared Nodes

**What goes wrong:** A node (e.g. a ColorCorrect used as input to two Merges) gets computed once with "compact" scheme from the first path, but the second path (expecting "normal") gets the cached "compact" result.
**Why it happens:** The current memo uses `id(node)` as key. Different scheme values per path are invisible to the cache.
**How to avoid:** Change memo key to `(id(node), scheme_for_node)` where `scheme_for_node` is the resolved float multiplier for that specific node.
**Warning signs:** Subtree layouts look correct from one root but wrong from another when a node is shared.

### Pitfall 3: addKnob on Already-Present Knob

**What goes wrong:** `node.addKnob(nuke.String_Knob('node_layout_state', ...))` raises `RuntimeError` on second layout run.
**Why it happens:** The knob already exists from the first layout run.
**How to avoid:** Always guard with `if node.knob('node_layout_state') is None:` before adding.
**Warning signs:** RuntimeError on second or later layout invocation.

### Pitfall 4: Removing Tab That Has Other Knobs

**What goes wrong:** Clear-state command removes `node_layout_tab` even though `node_layout_diamond_dot` still lives on it (for diamond-resolution Dots).
**Why it happens:** Tab removal removes all knobs on the tab in some Nuke versions.
**How to avoid:** Only remove tab when both `node_layout_state` and `node_layout_diamond_dot` are absent after the removal of `node_layout_state`.
**Warning signs:** Diamond-dot Dots lose their marker knob; `_passes_node_filter()` stops recognizing them.

### Pitfall 5: State Written to Newly Inserted Dot Nodes

**What goes wrong:** State write-back iterates `collect_subtree_nodes(root)` BEFORE Dot insertion, missing newly created dots; OR iterates after Dot insertion and sets misleading state on ephemeral side-input Dots.
**Why it happens:** Dot insertion happens inside `place_subtree()`, changing the node graph mid-run.
**How to avoid:** Write state from `final_subtree_nodes` (after `place_subtree()` and Dot insertion). Diamond-resolution Dots and side-input Dots should receive state — the decision is: all layout-touched nodes get state (no special-casing), per CONTEXT.md.
**Warning signs:** Dot nodes missing state knobs; next re-layout fails to find stored scheme for Dots.

### Pitfall 6: Float Accumulation Drift in Scale

**What goes wrong:** Repeated Shrink operations (0.8 × 0.8 × ... n times) accumulate floating-point rounding error, so stored h_scale drifts from the mathematically exact value.
**Why it happens:** IEEE 754 float multiplication is not exact.
**How to avoid:** `round(stored_state["h_scale"] * scale_factor, 10)` — 10 decimal places is far more precision than needed but eliminates runaway drift.
**Warning signs:** Stored h_scale value has 15+ significant digits after many operations.

## Code Examples

### Existing Knob Addition Pattern (node_layout.py lines 252–257)

```python
# Source: insert_dot_nodes() in node_layout.py
dot.addKnob(nuke.Tab_Knob('node_layout_tab', 'Node Layout'))
dot.addKnob(nuke.Int_Knob('node_layout_diamond_dot', 'Diamond Dot Marker'))
dot['node_layout_diamond_dot'].setValue(1)
```

This is the established pattern. The state knob follows the same tab.

### Existing Entry Point Structure (layout_upstream, node_layout.py lines 579–615)

```python
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
            # ... layout work ...
    except Exception:
        nuke.Undo.cancel()
        raise
    else:
        nuke.Undo.end()
```

The state-write pass slots in after `place_subtree()`, still inside `with current_group:` and the `try` block.

### Existing Scheme Override Entry Points (node_layout.py lines 696–709)

```python
def layout_upstream_compact():
    layout_upstream(scheme_multiplier=node_layout_prefs.prefs_singleton.get("compact_multiplier"))

def layout_upstream_loose():
    layout_upstream(scheme_multiplier=node_layout_prefs.prefs_singleton.get("loose_multiplier"))
```

These pass explicit `scheme_multiplier` → the entry point detects `scheme_multiplier is not None` → overrides stored scheme for all nodes AND writes the new scheme back.

### Menu Registration Pattern (menu.py)

```python
# Existing pattern:
layout_menu.addCommand('Layout Upstream Compact', node_layout.layout_upstream_compact)

# New clear-state commands follow the same pattern:
layout_menu.addCommand('Clear Layout State Selected', node_layout.clear_layout_state_selected)
layout_menu.addCommand('Clear Layout State Upstream', node_layout.clear_layout_state_upstream)
```

### AST Test Pattern (used across all test files)

```python
# Source: test_group_context.py, test_undo_wrapping.py — established pattern
def _get_function_source(source, function_name):
    tree = ast.parse(source)
    for ast_node in ast.walk(tree):
        if isinstance(ast_node, ast.FunctionDef) and ast_node.name == function_name:
            return ast.get_source_segment(source, ast_node)
    return None

class TestStateWriteBackAST(unittest.TestCase):
    def test_state_write_after_place_subtree_in_layout_upstream(self):
        source = _get_function_source(self._read_source(), "layout_upstream")
        place_pos = source.find("place_subtree(")
        state_write_pos = source.find("write_node_state")
        self.assertLess(place_pos, state_write_pos,
            "State write-back must appear after place_subtree() in layout_upstream()")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `scheme_multiplier=None` → always use normal_multiplier | `scheme_multiplier=None` → read stored per-node scheme | Phase 7 | First layout of any node is unchanged (no stored state → defaults to normal); re-layout replays stored scheme |
| No persistent per-node state | `node_layout_state` String_Knob on every touched node | Phase 7 | State survives save/reopen; clear-state commands available |
| Memo key: `id(node)` | Memo key: `(id(node), scheme_for_node)` | Phase 7 | Prevents cache collision on shared nodes with different per-node schemes |

**Deprecated/outdated:**
- Hardcoded `node_layout_prefs.prefs_singleton.get("normal_multiplier")` fallback inside `layout_selected()` (lines 651–653): replaced by per-node state read.

## Open Questions

1. **`addKnob` on existing Tab_Knob behavior**
   - What we know: The existing code adds `node_layout_tab` to diamond Dots. The CONTEXT.md says "Whether `node_layout_tab` is added fresh if absent, or assumed present on any node that already went through layout" is Claude's Discretion.
   - What's unclear: Whether `node.addKnob(Tab_Knob(...))` on an already-present tab is a silent no-op or raises in all Nuke 11+ versions.
   - Recommendation: Guard with `if node.knob('node_layout_tab') is None:` regardless — safe in either case.

2. **`removeKnob` for Tab_Knob with remaining occupants**
   - What we know: Nuke's removeKnob API for Tab_Knob varies across versions regarding whether it removes occupant knobs.
   - What's unclear: Whether removing `node_layout_tab` orphans or destroys `node_layout_diamond_dot` on Diamond Dots.
   - Recommendation: In `clear_node_state()`, check `node.knob('node_layout_diamond_dot') is None` before removing the tab. Skip tab removal if diamond dot present.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (stdlib) — pytest not installed |
| Config file | none |
| Quick run command | `python3.11 -m unittest discover -s /workspace/tests -p "*.py" -q` |
| Full suite command | `python3.11 -m unittest discover -s /workspace/tests -p "*.py" -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STATE-01 | Layout-touched nodes receive `node_layout_state` String_Knob with correct JSON | unit (pure Python) | `python3.11 -m unittest tests.test_node_layout_state -q` | ❌ Wave 0 |
| STATE-01 | `write_node_state()` creates tab+knob if absent; does not duplicate if present | unit (pure Python) | `python3.11 -m unittest tests.test_node_layout_state -q` | ❌ Wave 0 |
| STATE-01 | State write-back pass appears after `place_subtree()` in `layout_upstream()` | structural (AST) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ Wave 0 |
| STATE-01 | State write-back pass appears after `place_subtree()` in `layout_selected()` | structural (AST) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ Wave 0 |
| STATE-02 | `INVISIBLE` flag set, `DO_NOT_WRITE` absent on state knob | structural (AST) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ Wave 0 |
| STATE-03 | `read_node_state()` returns defaults when knob absent | unit (pure Python) | `python3.11 -m unittest tests.test_node_layout_state -q` | ❌ Wave 0 |
| STATE-03 | `scheme_multiplier=None` path reads per-node state in `layout_upstream()` | structural (AST) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ Wave 0 |
| STATE-03 | `compute_dims()` memo key changed to `(id(node), scheme_for_node)` | structural (AST) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ Wave 0 |
| STATE-03 | Explicit scheme command overrides stored scheme and writes back | structural (AST) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ Wave 0 |
| STATE-04 | Scale factor accumulates: `0.8 × 0.8 = 0.64` stored in `h_scale` | unit (pure Python + stub) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ Wave 0 |
| STATE-04 | `_scale_selected_nodes()` writes accumulated scale to all affected nodes | structural (AST) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ Wave 0 |
| STATE-04 | `_scale_upstream_nodes()` writes accumulated scale to all affected nodes | structural (AST) | `python3.11 -m unittest tests.test_state_integration -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3.11 -m unittest discover -s /workspace/tests -p "*.py" -q`
- **Per wave merge:** `python3.11 -m unittest discover -s /workspace/tests -p "*.py" -q`
- **Phase gate:** Full suite green (currently 168 tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `/workspace/tests/test_node_layout_state.py` — covers STATE-01 (write_node_state, read_node_state, clear_node_state helpers), STATE-02 (flag checking), STATE-03 (defaults, scheme resolution), STATE-04 (scale accumulation) via pure-Python tests with Nuke stub
- [ ] `/workspace/tests/test_state_integration.py` — covers STATE-01/03/04 structural requirements via AST tests on `node_layout.py` (write-back order, memo key, entry-point read path)
- [ ] `/workspace/node_layout_state.py` — the new helper module itself (Wave 0 creates the test target)

## Sources

### Primary (HIGH confidence)
- Direct codebase reading — `node_layout.py`, `menu.py`, all test files in `/workspace/tests/`
- CONTEXT.md — all implementation decisions were gathered during `/gsd:discuss-phase` and are locked

### Secondary (MEDIUM confidence)
- Nuke Python Developer Guide (general knowledge): `String_Knob`, `Tab_Knob`, `INVISIBLE` flag, `DO_NOT_WRITE` flag, `addKnob`/`removeKnob` API — consistent with established patterns already in the codebase
- STATE.md accumulated context: "DO_NOT_WRITE flag must NOT be set on state knobs — it prevents .nk persistence — confirmed in prior research"

### Tertiary (LOW confidence)
- Exact behavior of `removeKnob(Tab_Knob)` when occupants remain — not verified empirically; guarded by defensive check in recommended implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib JSON + existing Nuke API already used in codebase
- Architecture: HIGH — all decisions locked in CONTEXT.md, code patterns fully established
- Pitfalls: HIGH — most derived from locked decisions and existing patterns in STATE.md accumulated context
- `removeKnob(Tab_Knob)` edge case: LOW — needs empirical verification in target Nuke version

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable Nuke API; JSON stdlib)
