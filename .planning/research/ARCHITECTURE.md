# Architecture Patterns

**Project:** node_layout v1.4 — Leader Key Modal Input System
**Researched:** 2026-03-28
**Confidence:** HIGH (based on direct codebase analysis + verified Qt/Nuke API patterns)

---

## Context: Existing Architecture

Before documenting new integration points, the existing module boundaries matter:

| Component | Responsibility | LOC |
|-----------|---------------|-----|
| `node_layout.py` | Layout algorithm, scale, freeze, all public command functions | ~3,200 |
| `node_layout_state.py` | Per-node hidden knob state helpers | ~140 |
| `node_layout_prefs.py` | JSON-backed singleton at `~/.nuke/node_layout_prefs.json` | ~50 |
| `node_layout_prefs_dialog.py` | PySide6 QDialog for editing prefs | ~170 |
| `menu.py` | `nuke.addMenuCommand` registrations and DAG shortcuts | ~185 |
| `node_layout_util.py` | Standalone DAG helpers (sort, select upstream, select hidden outputs) | ~100 |
| `make_room.py` | Manual push-room utility | ~100 |

The existing command model is straightforward: `menu.py` maps keyboard shortcuts (e.g., `shift+e`) directly to Python strings that call module-level functions. There is no intermediate dispatch layer. The leader key system introduces one.

---

## New System Overview

The leader key system adds three new concerns:

1. **Event interception** — detect when Shift+E is pressed in the DAG, enter leader mode, and intercept subsequent keypresses before Nuke sees them.
2. **Overlay display** — show a floating, semi-transparent keyboard hint widget over the DAG while in leader mode.
3. **Context-aware dispatch** — when a command key arrives, inspect selection count and node state to call the correct existing command function.

These map to three new components and modifications to two existing ones.

---

## New Components

### Component 1: `node_layout_leader.py` — Event Filter + Dispatch (NEW FILE)

**Why a new file:** The event filter is stateful (active/inactive mode, DAG widget reference), PySide6-heavy, and has no overlap with the pure-layout logic in `node_layout.py`. Separating it keeps `node_layout.py` importable without side effects (no Qt objects created at import time). This matches the existing pattern where PySide6 code lives in `node_layout_prefs_dialog.py`, not in `node_layout.py`.

**Class: `LeaderKeyFilter(QObject)`**

Subclass of `QObject` (not `QWidget`). Installed as an event filter on the active DAG widget. This is the correct Qt pattern for intercepting events on a widget you do not own — `installEventFilter()` on the target widget, override `eventFilter(watched, event)` on the filter object.

```python
class LeaderKeyFilter(QObject):
    def eventFilter(self, watched, event) -> bool:
        # Returns True to consume the event (suppress from Nuke)
        # Returns False to let Nuke process it normally
        ...
```

**State:**
- `_active: bool` — whether leader mode is currently engaged
- `_dag_widget: QWidget | None` — the DAG widget this filter is installed on
- `_overlay: LeaderKeyOverlay | None` — the overlay widget; created once and reused

**Lifecycle (critical):**
- The filter object is created **once at Nuke startup** (during `menu.py` import) and stored as a module-level singleton.
- `installEventFilter()` is called on the DAG widget when leader mode is entered, **not at startup**. This avoids the cost of processing every DAG event at all times.
- Alternatively: install on `QApplication.instance()` at startup for global coverage, then gate on DAG focus. Installing on `QApplication` means every event in the whole application goes through `eventFilter()` — acceptable for a two-state (active/inactive) filter that returns `False` immediately when not active, but installation on the DAG widget is cleaner and more targeted.
- **Recommended lifecycle:** install on `QApplication.instance()` at startup (one-time, global). When not in leader mode, `eventFilter()` returns `False` immediately after a single boolean check — negligible overhead. This avoids the complexity of finding and re-installing on the DAG widget on each leader key press.

**Finding the DAG widget (for overlay positioning):**

```python
from PySide6.QtWidgets import QApplication

def _find_active_dag_widget():
    for widget in QApplication.instance().allWidgets():
        if "DAG" in widget.objectName() and widget.isVisible():
            if widget.hasFocus():
                return widget
    # Fallback: first visible DAG
    for widget in QApplication.instance().allWidgets():
        if "DAG" in widget.objectName() and widget.isVisible():
            return widget
    return None
```

The DAG widget objectName is `"DAG"` for the primary DAG, `"DAG.Group1"` etc. for Group DAGs. This was established in Nuke 16 (PySide6 transition) and works reliably across all visible DAGs. (MEDIUM confidence — verified against Erwan Leroy's Nuke DAG utility article and Foundry's Nuke 16 PySide6 migration guide.)

**Keymap (leader mode only):**

| Key | Action | Context rule |
|-----|--------|-------------|
| V | layout_upstream or layout_selected | 1 selected node → upstream; 2+ → selected |
| Z | layout_selected_horizontal | no context rule |
| F | freeze_selected or unfreeze_selected | freeze_group present on any selected node → unfreeze; else → freeze |
| C | clear_freeze_group on all selected nodes | no context rule |
| W | move selected nodes up | stays in leader mode after execution |
| A | move selected nodes left | stays in leader mode after execution |
| S | move selected nodes down | stays in leader mode after execution |
| D | move selected nodes right | stays in leader mode after execution |
| Q | shrink_selected | stays in leader mode after execution (TBD — check spec) |
| E | expand_selected | stays in leader mode after execution (TBD — check spec) |
| Escape | cancel leader mode | — |
| any other key | cancel leader mode | — |
| mouse click | cancel leader mode | — |

**Cancellation:** On any unrecognized key or mouse button press, the filter calls `_deactivate()` and returns `False` (lets the event proceed to Nuke). On recognized keys it calls the command function and returns `True` (consumes the event so Nuke does not also act on it). Exception: WASD/QE keys return `True` and keep `_active = True` so the user can chain movement/scale commands without re-pressing Shift+E.

**Module-level singleton:**
```python
_leader_filter_singleton = None

def get_leader_filter():
    global _leader_filter_singleton
    if _leader_filter_singleton is None:
        _leader_filter_singleton = LeaderKeyFilter()
        QApplication.instance().installEventFilter(_leader_filter_singleton)
    return _leader_filter_singleton
```

`get_leader_filter()` is called once from `menu.py` at import time to install the filter.

---

### Component 2: `node_layout_overlay.py` — Keyboard Hint Overlay Widget (NEW FILE)

**Why a new file:** The overlay widget is a PySide6 QWidget subclass with custom `paintEvent`. It has no dependency on the layout engine or prefs system at runtime (it only needs the keymap data, which can be passed in as a dict or defined as a constant). Keeping it separate makes it independently testable via AST/structural tests and avoids further inflating `node_layout.py` or `node_layout_leader.py`.

**Class: `LeaderKeyOverlay(QWidget)`**

**Widget flags and attributes:**
```python
self.setWindowFlags(
    Qt.Tool |
    Qt.FramelessWindowHint |
    Qt.WindowStaysOnTopHint
)
self.setAttribute(Qt.WA_TranslucentBackground)
self.setAttribute(Qt.WA_ShowWithoutActivating)  # critical: don't steal focus from DAG
```

`Qt.WA_ShowWithoutActivating` is the key flag: it allows the widget to be visible without taking keyboard focus away from the DAG. Without this, `show()` would transfer focus to the overlay, immediately breaking the leader mode event filter (the DAG widget would lose focus and Nuke would stop routing keyboard events through the filter). (HIGH confidence — standard Qt pattern, verified in Qt documentation.)

`Qt.Tool` is used instead of `Qt.Window` so the overlay does not appear in the OS taskbar and has correct layering relative to the Nuke main window.

**Positioning:** The overlay is positioned over the DAG widget using the DAG widget's global geometry:
```python
dag_rect = dag_widget.rect()
global_top_left = dag_widget.mapToGlobal(dag_rect.topLeft())
self.setGeometry(global_top_left.x(), global_top_left.y(),
                 dag_rect.width(), dag_rect.height())
```

The overlay covers the full DAG widget area. It draws key labels in a corner/panel region using `paintEvent`, with the rest fully transparent.

**Hint popup delay:** The overlay is shown immediately when leader mode activates if `hint_popup_delay_ms == 0` (default). If delay > 0, a `QTimer.singleShot(delay_ms, self.show)` is used. The timer is cancelled if leader mode deactivates before the timer fires. This keeps the delay pref fully decoupled from the filter logic — the filter activates leader mode and calls `overlay.show_with_delay(delay_ms)`.

**paintEvent:** Draws a semi-translucent rounded rectangle in one corner of the DAG with key/label pairs. Does not use any Qt widget children (pure `QPainter`) to avoid layout complexity. The key visual uses a "keyboard key cap" appearance: small rounded rectangles with the key letter, followed by a label string.

**Reuse:** The overlay object is created once (when the filter singleton is created) and reused. `show()` / `hide()` toggle visibility. This avoids the cost of widget construction/destruction on every leader key press.

---

## Modified Components

### `node_layout_prefs.py` — Add `hint_popup_delay_ms` (MODIFIED)

**Change:** Add one new entry to `DEFAULTS`:
```python
"hint_popup_delay_ms": 0,
```

No behavioral change. The delay value is read by `node_layout_leader.py` (via `prefs_singleton.get("hint_popup_delay_ms")`) when activating the overlay.

This is the only change needed in `node_layout_prefs.py`. The singleton pattern, `get()` / `set()` / `save()` / `reload()` interface, and JSON file location all remain unchanged.

### `node_layout_prefs_dialog.py` — Add Hint Popup Delay Field (MODIFIED)

**Change:** Add a new "Leader Key" section (bold QLabel header, per existing convention) with one `QLineEdit` field for "Hint Popup Delay (ms):". The field is an `int` with constraint `>= 0` (zero is valid — means show immediately).

The section goes at the bottom of the form, after "Advanced", following the existing pattern:
- New `QLabel("")` spacer row for breathing room
- New `_make_section_header("Leader Key")` row
- New `self.hint_popup_delay_edit = QLineEdit()` row

`_populate_from_prefs()` and `_on_accept()` get corresponding `setText` / `int()` parse / `prefs_instance.set()` additions. Validation: `hint_popup_delay_ms_value >= 0`.

### `menu.py` — Replace Shift+E with Leader Entry Point (MODIFIED)

**Change:** The existing `shift+e` binding:
```python
layout_menu.addCommand(
    'Layout Upstream',
    "import node_layout; node_layout.layout_upstream()",
    'shift+e',
    shortcutContext=2,
)
```

...is replaced with:
```python
layout_menu.addCommand(
    'Leader Key',
    "import node_layout_leader; node_layout_leader.activate_leader_mode()",
    'shift+e',
    shortcutContext=2,
)
```

The old `Layout Upstream` command remains in the menu without a shortcut so it is still accessible via Tab menu search. The direct `shift+e` binding moves to leader key entry.

The filter singleton is initialized at `menu.py` import time:
```python
import node_layout_leader
node_layout_leader.get_leader_filter()  # installs QApplication event filter
```

This must happen at startup (menu.py import), not lazily, because `QApplication.instance()` must be available and the filter must be registered before any key events are processed.

---

## Data Flow Between Components

```
[Nuke startup]
  → menu.py imported
  → node_layout_leader.get_leader_filter() called
  → LeaderKeyFilter created, installed on QApplication.instance()
  → LeaderKeyOverlay created (hidden)

[User presses Shift+E in DAG]
  → Nuke menu command fires: node_layout_leader.activate_leader_mode()
  → LeaderKeyFilter._active = True
  → DAG widget found via _find_active_dag_widget()
  → LeaderKeyOverlay positioned over DAG, show_with_delay(hint_popup_delay_ms) called

[User presses V in DAG while leader mode active]
  → QApplication event filter fires: eventFilter(dag_widget, KeyPressEvent(V))
  → LeaderKeyFilter recognizes V
  → Context check: len(nuke.selectedNodes()) == 1 → call node_layout.layout_upstream()
  → event consumed (return True)
  → LeaderKeyFilter._active = False
  → LeaderKeyOverlay.hide()

[User presses W (move up) while leader mode active]
  → eventFilter recognizes W as a chaining key
  → Calls move-up action (node position delta)
  → event consumed (return True)
  → LeaderKeyFilter._active remains True (leader mode persists)
  → Overlay stays visible

[User presses unknown key or clicks mouse]
  → eventFilter does not recognize key
  → LeaderKeyFilter._active = False
  → LeaderKeyOverlay.hide()
  → event NOT consumed (return False — Nuke processes normally)
```

---

## Context-Aware Dispatch Logic

The V and F keys require context inspection before calling commands. This lives entirely in `node_layout_leader.py` — the existing command functions in `node_layout.py` are called unchanged.

**V — vertical layout:**
```python
selected = nuke.selectedNodes()
if len(selected) == 1:
    node_layout.layout_upstream()
else:
    node_layout.layout_selected()
```

No new function signatures needed in `node_layout.py`. The leader layer is purely a dispatch shim.

**F — freeze/unfreeze toggle:**
```python
selected = nuke.selectedNodes()
any_frozen = any(node_layout_state.read_freeze_group(n) is not None for n in selected)
if any_frozen:
    node_layout.unfreeze_selected()
else:
    node_layout.freeze_selected()
```

Uses the existing `read_freeze_group()` from `node_layout_state.py`. No changes to either module.

**C — clear freeze group:**
The PROJECT.md spec says "C — clear freeze group". There is no existing `clear_freeze_group_selected()` public function in `node_layout.py`. This is a new thin wrapper needed in `node_layout.py` (or can be implemented inline in `node_layout_leader.py` using `node_layout_state.clear_freeze_group()`). Recommended: add a `clear_freeze_selected()` public function to `node_layout.py` for consistency with the existing `freeze_selected()` / `unfreeze_selected()` pattern, then call it from the leader dispatch.

**WASD — node movement:**
There are no existing move-node functions in `node_layout.py`. These are new operations. The simplest implementation moves each selected node by a fixed delta (e.g., one snap grid increment, read from `get_dag_snap_threshold()`). This is new logic that belongs in `node_layout_leader.py` (not `node_layout.py`) because it is specific to the leader key UX and not a general layout operation. Alternatively, it can go in `node_layout_util.py` as a standalone helper. The leader module is recommended to keep utility.py focused on its existing DAG selection utilities.

---

## Build Order

Dependencies determine ordering. The overlay has a delay-pref dependency; the filter needs the overlay; `menu.py` needs the filter singleton initialized.

### Phase 1: Prefs + Dialog (foundation, no Qt complexity)

**Deliverable:** `hint_popup_delay_ms` pref key in DEFAULTS, new field in dialog.

**Why first:** Both the overlay (needs delay value) and the dialog (needs to expose it) depend on this pref existing. Building it first gives a clean, testable base. No Qt runtime needed — fully testable with AST/structural tests.

**Files changed:** `node_layout_prefs.py`, `node_layout_prefs_dialog.py`
**New files:** none
**Tests:** extend `tests/test_node_layout_prefs.py`, `tests/test_node_layout_prefs_dialog.py`

### Phase 2: Overlay Widget (visual layer, no event logic)

**Deliverable:** `node_layout_overlay.py` with `LeaderKeyOverlay` class. Shows/hides correctly, renders key labels, respects `WA_ShowWithoutActivating`.

**Why second:** The overlay is testable in isolation (no Nuke runtime needed for structural tests; the paint logic can be stub-tested). Building it before the event filter allows the filter implementation to reference a stable overlay API.

**Files changed:** none
**New files:** `node_layout_overlay.py`
**Tests:** new `tests/test_node_layout_overlay.py` (AST-based: check flags, attributes, paintEvent presence)

### Phase 3: Event Filter + Dispatch (leader key logic)

**Deliverable:** `node_layout_leader.py` with `LeaderKeyFilter`, `get_leader_filter()`, `activate_leader_mode()`. Dispatch to all command keys except WASD (movement — deferred to Phase 4).

**Why third:** Depends on overlay (Phase 2) and prefs (Phase 1). This is the core integration phase.

**Files changed:** none
**New files:** `node_layout_leader.py`
**Tests:** new `tests/test_node_layout_leader.py` (Nuke-stub based: keymap table coverage, context dispatch logic for V and F, cancellation behavior)

### Phase 4: WASD Movement + C Command (new operations)

**Deliverable:** Node movement via WASD in leader mode, `clear_freeze_selected()` in `node_layout.py` for the C key.

**Why fourth:** WASD involves new node-movement logic that is independent of the event filter structure. Building it after the filter is stable means it can be added as an incremental dispatch addition. The C command requires a new `node_layout.py` function — small but requires its own undo group.

**Files changed:** `node_layout_leader.py` (add WASD dispatch), `node_layout.py` (add `clear_freeze_selected()`)
**New files:** none
**Tests:** extend `tests/test_node_layout_leader.py`, add `test_clear_freeze_selected` to freeze tests

### Phase 5: menu.py Wiring (activation)

**Deliverable:** Shift+E bound to leader mode entry; `get_leader_filter()` called at startup; `Layout Upstream` retains menu entry without shortcut.

**Why last:** This is a one-way integration — once Shift+E is rebound, the old behavior is gone. All prior phases should be validated before this phase executes. The menu change is the smallest possible change but the highest visible impact.

**Files changed:** `menu.py`
**New files:** none
**Tests:** extend `tests/test_menu.py` (or AST-check that `shift+e` is bound to leader, not layout_upstream)

---

## Component Dependency Graph

```
node_layout_prefs.py       (Phase 1 — no deps on new code)
    ↓
node_layout_prefs_dialog.py (Phase 1 — depends on prefs)

node_layout_overlay.py     (Phase 2 — depends on prefs for delay value)

node_layout_leader.py      (Phase 3+4 — depends on overlay, prefs, node_layout, node_layout_state)

menu.py                    (Phase 5 — depends on leader module existing)
```

`node_layout.py` and `node_layout_state.py` are called from `node_layout_leader.py` as imports. They are not modified except for `clear_freeze_selected()` addition (Phase 4) and the `Layout Upstream` shortcut removal from `menu.py` (Phase 5).

---

## New vs. Modified Files Summary

| File | Status | What Changes |
|------|--------|-------------|
| `node_layout_leader.py` | NEW | `LeaderKeyFilter` QObject event filter, `get_leader_filter()` singleton init, `activate_leader_mode()`, full keymap dispatch, WASD movement logic |
| `node_layout_overlay.py` | NEW | `LeaderKeyOverlay` QWidget, frameless/translucent flags, `WA_ShowWithoutActivating`, `show_with_delay()`, `paintEvent` for key cap rendering |
| `node_layout_prefs.py` | MODIFIED — minor | Add `"hint_popup_delay_ms": 0` to `DEFAULTS` dict |
| `node_layout_prefs_dialog.py` | MODIFIED — minor | New "Leader Key" section header, one `QLineEdit` field, populate/save wiring, `>= 0` validation |
| `menu.py` | MODIFIED — minor | Rebind `shift+e` to `activate_leader_mode()`; call `get_leader_filter()` at import; retain `Layout Upstream` without shortcut |
| `node_layout.py` | MODIFIED — minimal | Add `clear_freeze_selected()` public function (new undo-wrapped command for C key) |
| `node_layout_state.py` | NOT MODIFIED | Used as-is from leader dispatch |
| `node_layout_util.py` | NOT MODIFIED | No changes required |
| `make_room.py` | NOT MODIFIED | No changes required |

---

## Critical Design Decisions

### Decision 1: QApplication-level event filter, installed at startup

**Rationale:** Installing on `QApplication.instance()` at startup (one-time) is simpler and more robust than finding-and-installing on the DAG widget on each Shift+E press. When not in leader mode, the filter returns `False` immediately — a single boolean check, negligible overhead. Re-installing on the DAG widget each time requires finding the widget, managing install/uninstall across Group DAGs, and handling edge cases where the active widget changes. The QApplication approach avoids all of this complexity.

**Trade-off accepted:** Slightly broader event scope (all Qt events pass through `eventFilter()` when leader mode is inactive, but the inactive fast-path is a single `if not self._active: return False`).

### Decision 2: Overlay as separate file, not embedded in leader module

**Rationale:** Keeps the visual layer independently testable. The overlay's correctness (correct window flags, `WA_ShowWithoutActivating`, `paintEvent`) can be verified with AST/structural tests without a Nuke runtime. If the leader module imported and instantiated the overlay inline, these structural checks would require importing the whole leader module.

### Decision 3: WA_ShowWithoutActivating is mandatory

**Rationale:** Without this flag, `overlay.show()` steals focus from the DAG widget. The event filter is installed on `QApplication`, so it receives events regardless of focus — but Nuke's own keyboard shortcut system is focus-based. If the DAG loses focus, other Nuke shortcuts may misfire. `WA_ShowWithoutActivating` prevents this entirely.

### Decision 4: Context dispatch lives in leader module, not in node_layout.py

**Rationale:** The context-aware "1 node → upstream, 2+ nodes → selected" distinction is a UI/UX concern introduced by the leader key system. The command functions `layout_upstream()` and `layout_selected()` have well-defined, unconditional behavior that tests depend on. Embedding context dispatch in them would add branching that tests do not cover and that is irrelevant to the layout algorithm. The leader module is the correct place for UX-layer dispatch logic.

### Decision 5: No clear_freeze_group_selected in node_layout_leader.py directly

**Rationale:** Direct `node_layout_state.clear_freeze_group()` calls without an undo group would leave the operation un-undoable. Adding `clear_freeze_selected()` to `node_layout.py` with a proper `nuke.Undo()` group follows the established pattern for all command functions in that module and makes it accessible from the menu as well.

---

## Pitfall Alerts for Roadmapper

| Phase | Pitfall | Mitigation |
|-------|---------|-----------|
| Phase 2 (overlay) | `WA_ShowWithoutActivating` missing → DAG loses focus, leader mode breaks immediately on overlay show | Structural test: assert attribute is set in `__init__` |
| Phase 2 (overlay) | Overlay not parented to Nuke main window → may appear behind on some OSes | Use `nuke.thisParent()` or find Nuke main window as parent, or use `Qt.WindowStaysOnTopHint` |
| Phase 3 (filter) | Event filter not returning `True` for consumed keys → Nuke also processes them (double action) | Test: verify return value for each recognized key |
| Phase 3 (filter) | Event filter installed before `QApplication.instance()` is available → `None` dereference at startup | Check: `get_leader_filter()` must be called after Qt is initialized; `menu.py` import at Nuke startup is safe timing |
| Phase 5 (menu) | `shift+e` still bound to Layout Upstream somewhere after rebind → two handlers fire | Remove old binding explicitly; verify with AST test on menu.py |
| All phases | WASD movement delta — what unit? snap grid vs. fixed pixels | Use `get_dag_snap_threshold()` from `node_layout.py` for consistency with existing layout behavior |

---

## Sources

- Direct analysis of `/workspace/node_layout.py`, `node_layout_prefs.py`, `node_layout_prefs_dialog.py`, `node_layout_state.py`, `menu.py` (2026-03-28)
- `.planning/PROJECT.md` — v1.4 target features and constraints
- Erwan Leroy, "Nuke Node graph utilities using Qt/PySide2" — DAG widget objectName pattern (`"DAG"`, `"DAG.Group1"`), `allWidgets()` enumeration approach
- Erwan Leroy, "Updating Your Python Scripts for Nuke 16 and PySide6" — DAG widget change from OpenGL to standard QWidget in Nuke 16; named widget approach
- Qt for Python documentation — `QWidget.WA_ShowWithoutActivating`, `Qt.Tool`, `Qt.FramelessWindowHint`, `Qt.WA_TranslucentBackground`, `installEventFilter()` behavior
- Qt Event System documentation — event filter ordering, `return True` to consume vs. `return False` to pass through
