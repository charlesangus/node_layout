# Technology Stack

**Project:** node_layout v1.1
**Researched:** 2026-03-05
**Scope:** Nuke API patterns needed for new v1.1 features only. Existing validated stack (Python, PySide6, JSON prefs) is not repeated here.

---

## New API Surface for v1.1

### (1) Hidden Tabs and Custom Knobs on Nodes

**Purpose:** Store per-node layout mode, scheme, and scale factor so that re-running layout replays the node's previously chosen settings.

#### Pattern: Add an invisible tab plus data knobs

```python
tab = nuke.Tab_Knob('node_layout_tab', 'Node Layout')
tab.setFlag(nuke.INVISIBLE)
node.addKnob(tab)

mode_knob = nuke.String_Knob('node_layout_mode', 'Layout Mode')
mode_knob.setFlag(nuke.INVISIBLE)
mode_knob.setValue('vertical')  # or 'horizontal'
node.addKnob(mode_knob)

scheme_knob = nuke.String_Knob('node_layout_scheme', 'Layout Scheme')
scheme_knob.setFlag(nuke.INVISIBLE)
scheme_knob.setValue('normal')
node.addKnob(scheme_knob)

scale_knob = nuke.Double_Knob('node_layout_scale', 'Scale Factor')
scale_knob.setFlag(nuke.INVISIBLE)
scale_knob.setValue(1.0)
node.addKnob(scale_knob)
```

#### Reading back the stored state

```python
mode_knob = node.knob('node_layout_mode')
if mode_knob is not None:
    mode = mode_knob.value()   # .value() for String_Knob, not .getValue()
```

#### Checking existence before writing (idempotent add)

```python
if node.knob('node_layout_tab') is None:
    tab = nuke.Tab_Knob('node_layout_tab', 'Node Layout')
    tab.setFlag(nuke.INVISIBLE)
    node.addKnob(tab)
```

#### Key facts — confidence HIGH (multiple consistent community sources, cross-referenced with Foundry API docs)

- `nuke.INVISIBLE` = `0x0000000000000400`. Permanently hides the knob from the properties panel. Cannot be reversed. This is the correct flag for state-storage knobs that users should never touch.
- `nuke.HIDDEN` = `0x0000000000040000`. Also hides, but is reversible with `show()` / `hide()`. Do NOT use for permanent storage knobs — use INVISIBLE.
- `nuke.DO_NOT_WRITE` = `0x0000000000000200`. Prevents the knob from being written to the `.nk` script file. DO NOT set this flag on state-storage knobs — it would cause state to be lost on script save/reload. Leave it unset so Nuke writes the knob value into the `.nk` file.
- `nuke.NO_RERENDER` = `0x0000000000004000`. Prevents the knob from affecting the render hash. Set this on all node_layout state knobs — layout metadata should never trigger a re-cook of the node.

#### Recommended combined flags for storage knobs

```python
knob.setFlag(nuke.INVISIBLE | nuke.NO_RERENDER)
```

The tab knob only needs `nuke.INVISIBLE` (it has no render hash relevance).

#### Gotcha: UI focus shift when adding knobs

Adding a knob via `addKnob()` causes Nuke to switch the open properties panel to the newly added tab, which is visible to the user. To suppress this, set `nuke.INVISIBLE` on the Tab_Knob before calling `addKnob()`. Alternatively, after adding all knobs, touch any knob in the original tab to force focus back:

```python
# Force focus back to the node's first built-in tab after programmatic knob adds
node.knob('label').setFlag(0)
```

The approach of setting INVISIBLE before `addKnob()` is cleaner and is the recommended pattern here.

#### Gotcha: Tab_Knob must be added before its child knobs

Nuke groups knobs under whichever Tab_Knob was most recently added before them. Add the tab first, then add the data knobs under it. If the tab is not added first, Nuke creates a visible "User" tab automatically.

#### Existing precedent in this codebase

The codebase already uses this exact pattern (Tab_Knob + Int_Knob) on diamond-resolution Dot nodes:

```python
dot.addKnob(nuke.Tab_Knob('node_layout_tab', 'Node Layout'))
dot.addKnob(nuke.Int_Knob('node_layout_diamond_dot', 'Diamond Dot Marker'))
```

The v1.1 work extends this pattern: add `nuke.INVISIBLE` and `nuke.NO_RERENDER` flags, and add String_Knob / Double_Knob for mode/scheme/scale. The existing diamond-resolution Dots should also get these flags retroactively.

---

### (2) Creating Dot Nodes in the Correct Group Context

**Problem:** `nuke.nodes.Dot()` creates the node in the *current active context*, not necessarily where the connected nodes live. When the layout plugin runs from a menu while the user has a Group node open in the DAG, `nuke.nodes.Dot()` creates Dot nodes inside that Group, not at the script root — causing misconnections and orphaned nodes.

**Root cause:** Nuke tracks a "current context" that defaults to `nuke.root()` but shifts to whatever Group the user last entered. `nuke.nodes.Dot()` respects this context.

#### Pattern: Detect and match the context of the nodes being laid out

```python
def _get_node_context(node):
    """Return the Group node that owns this node, or nuke.root() if at top level."""
    full_name = node.fullName()   # e.g. "Group1.Blur1" or just "Blur1"
    parts = full_name.split('.')
    if len(parts) == 1:
        return nuke.root()
    parent_name = '.'.join(parts[:-1])
    return nuke.toNode(parent_name)
```

#### Pattern: Create a Dot node inside the same context as its connected node

```python
context = _get_node_context(inp)   # inp is the upstream node the Dot wraps
with context:
    dot = nuke.nodes.Dot()
    dot.addKnob(nuke.Tab_Knob('node_layout_tab', 'Node Layout'))
    dot.addKnob(nuke.Int_Knob('node_layout_diamond_dot', 'Diamond Dot Marker'))
    dot['node_layout_diamond_dot'].setValue(1)
    dot.setInput(0, inp)
    dot['hide_input'].setValue(True)
    node.setInput(slot, dot)
```

The `with context:` form calls `context.begin()` on entry and `context.end()` on exit automatically, matching the standard Python context manager contract. This is the recommended approach over explicit `begin()` / `end()` calls because it guarantees `end()` is called even if an exception is raised.

#### Alternative: explicit begin/end (do not prefer)

```python
context = _get_node_context(inp)
context.begin()
try:
    dot = nuke.nodes.Dot()
    ...
finally:
    context.end()
```

Use `with context:` instead. The `try/finally` form is more verbose and identical in behavior.

#### Key facts — confidence MEDIUM (official Foundry docs confirm Group.begin()/end() and context manager protocol; root-level detection pattern is community-established)

- `nuke.root()` returns the root-level Group (the script itself). It is itself a Group node and supports `begin()` / `end()` / context manager.
- `nuke.root()` used as a context manager is safe: `with nuke.root(): nuke.nodes.Dot()` creates a Dot at the top level of the script, regardless of what the user's DAG panel is showing.
- `node.fullName()` returns the dotted path from the script root, e.g. `"GroupA.GroupB.Blur1"`. Splitting on `'.'` and joining all-but-last gives the parent's name for `nuke.toNode()`.
- `nuke.thisGroup()` returns the current context group. This is only reliable inside callbacks or knob-executed scripts. Do NOT call `nuke.thisGroup()` from a menu command — it returns the wrong context.

#### Integration note

The current codebase calls `nuke.nodes.Dot()` twice in `_resolve_diamonds()` without any context guard. Both call sites must be wrapped with `with _get_node_context(inp):`.

---

### (3) Reading Font Size from a Dot Node

**Purpose:** Scale `base_subtree_margin` based on the font size of a Dot node that signals a section boundary — larger font means visually heavier section divider, which should produce larger spacing.

#### Knob name

```python
font_size = dot_node['note_font_size'].getValue()  # returns float
```

The knob name is `note_font_size`. This applies to all nodes that have a label, not just Dot nodes — but for Dot nodes it controls the size of the annotation label text displayed on the tile.

#### Nuke default

The Nuke factory default for `Dot.note_font_size` is `20` (some sources cite 22; verify with `nuke.knobDefault("Dot.note_font_size")` at runtime). Users who set larger values (e.g. 35, 48) are signaling section headers.

#### Pattern: safe read with fallback

```python
DEFAULT_FONT_SIZE = 20

def get_dot_font_size(node):
    """Return the note_font_size of a Dot node, or DEFAULT_FONT_SIZE if unavailable."""
    knob = node.knob('note_font_size')
    if knob is None:
        return DEFAULT_FONT_SIZE
    value = knob.getValue()
    if value <= 0:
        return DEFAULT_FONT_SIZE
    return value
```

#### Confidence: HIGH

Multiple independent sources confirm `note_font_size` as the knob name, and it is used in official Foundry documentation examples (`nuke.knobDefault("Dot.note_font_size", "35")`).

---

### (4) Nuke API for Horizontal Node Arrangement

**Purpose:** Horizontal B-spine layout places nodes left-to-right instead of bottom-to-top. The coordinate system and API calls are the same — only the axis assignments change.

#### Coordinate system recap (from CLAUDE.md)

- Positive Y is DOWN, negative Y is UP.
- `node.setXpos(x)` sets the left edge of the node tile.
- `node.setYpos(y)` sets the top edge of the node tile.
- `node.screenWidth()` = tile width in DAG units.
- `node.screenHeight()` = tile height in DAG units.

For vertical layout: upstream nodes get smaller Y (higher on screen).
For horizontal layout: upstream nodes get smaller X (further left on screen).

#### Axis swap for horizontal layout

| Vertical layout | Horizontal layout |
|-----------------|-------------------|
| Consumer at `(x, y)` | Consumer at `(x, y)` |
| Upstream placed at `y - gap - upstream.screenHeight()` | Upstream placed at `x - gap - upstream.screenWidth()` |
| Side inputs step in X | Side inputs step in Y |
| Width of subtree uses `screenWidth()` | Width of subtree uses `screenHeight()` |
| Height of subtree uses `screenHeight()` | Height of subtree uses `screenWidth()` |

The implementation should be a parametrized version of `compute_dims()` and `place_subtree()` where the primary axis (currently Y) can be swapped to X.

#### screenWidth/screenHeight staleness gotcha

`screenWidth()` and `screenHeight()` are lazily computed by Nuke. They may return `0` immediately after a node is created with `nuke.nodes.Dot()`. The workaround is to read `xpos()` or `ypos()` first, which forces the display geometry to update:

```python
dot = nuke.nodes.Dot()
_ = dot.xpos()          # forces screenWidth/screenHeight to be computed
w = dot.screenWidth()   # now returns the correct value (typically 12 for a Dot)
```

This is a known Nuke behavior. The existing codebase already calls `setXpos`/`setYpos` before reading `screenWidth`/`screenHeight` in most places, which incidentally avoids the problem. Be explicit about this ordering when creating new Dot nodes for horizontal layout.

#### Standard Dot node dimensions

A Dot node tile is small (approximately 12 × 12 DAG units at standard zoom). For horizontal layout, the `screenWidth()` of a Dot used as a B-spine connector will be much smaller than a regular node's width. Account for this when centering Dots beside a consumer node horizontally.

#### No new API needed

The API for horizontal layout is entirely `xpos()`, `ypos()`, `setXpos()`, `setYpos()`, `screenWidth()`, `screenHeight()` — identical to what is already used. No new Nuke API functions are required.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Knob persistence | `INVISIBLE` + data knobs written to `.nk` | `DO_NOT_WRITE` flag | DO_NOT_WRITE prevents state from surviving script save/reload — exactly wrong for this use case |
| Knob visibility | `nuke.INVISIBLE` | `nuke.HIDDEN` | HIDDEN is reversible by Python, which risks accidental exposure; INVISIBLE is permanent and appropriate for internal state |
| Group context | `with context:` | `context.begin()` / `context.end()` | `with` guarantees `end()` on exceptions; explicit begin/end risks leaving context open if an exception is raised mid-creation |
| Font size knob | `note_font_size` | Parsing `node.label()` text | Knob is a direct int/float value; label text parsing would be fragile and require regex |
| Horizontal positioning | xpos/ypos axis swap | Separate horizontal API | No separate API exists; axis swap is the correct implementation approach |

---

## No New Dependencies

All patterns in this document use the existing Nuke Python API. No new libraries, no new pip installs, no new files beyond what v1.0 already ships. The changes are API usage patterns only.

---

## Sources

- [Nuke Python API — nuke.Knob](https://learn.foundry.com/nuke/developers/150/pythondevguide/_autosummary/nuke.knob.html) — official, HIGH confidence
- [Nuke Python API — nuke.Tab_Knob](https://learn.foundry.com/nuke/developers/140/pythonreference/_autosummary/nuke.Tab_Knob.html) — official, HIGH confidence
- [Nuke Python API — nuke.Group](https://learn.foundry.com/nuke/developers/140/pythonreference/_autosummary/nuke.Group.html) — official, HIGH confidence
- [Nuke Python API — nuke.thisGroup](https://learn.foundry.com/nuke/developers/14.0/pythonreference/_autosummary/nuke.thisGroup.html) — official, HIGH confidence
- [Manipulating the Node Graph — Nuke Python API Reference](https://learn.foundry.com/nuke/developers/130/pythondevguide/dag.html) — official, HIGH confidence for xpos/ypos/screenWidth/screenHeight
- [NDK Developers Guide — Knob Flags](https://learn.foundry.com/nuke/developers/63/ndkdevguide/knobs-and-handles/knobflags.html) — official NDK docs, HIGH confidence for flag hex values
- [Nukepedia — Some Flags](http://www.nukepedia.com/python/some-flags) — community reference, MEDIUM confidence (consistent with official)
- [Add Nodes Inside A Group With Python — Conrad Olson](https://conradolson.com/add-nodes-inside-a-group-with-python) — community, MEDIUM confidence (begin/end/with pattern)
- [Re: nuke-python — Create a knob without the panel changing?](https://www.mail-archive.com/nuke-python@support.thefoundry.co.uk/msg01529.html) — community mailing list, MEDIUM confidence (tab focus workaround)
- [Re: nuke-python — node.screenHeight() not updating](https://www.mail-archive.com/nuke-python@support.thefoundry.co.uk/msg02764.html) — community mailing list, MEDIUM confidence (screenWidth staleness)
- `note_font_size` knob name: confirmed by multiple community sources citing `nuke.knobDefault("Dot.note_font_size", ...)`, HIGH confidence
