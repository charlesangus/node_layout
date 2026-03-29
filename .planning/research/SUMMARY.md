# Project Research Summary

**Project:** node_layout v1.4 — Leader Key Modal Input System
**Domain:** Nuke DAG layout plugin — Qt event filter + modal keyboard dispatch + floating overlay HUD
**Researched:** 2026-03-28
**Confidence:** HIGH

## Executive Summary

The v1.4 milestone is a pure UX layer added on top of a complete layout engine. Every command the leader key will dispatch to — layout upstream, layout selected, horizontal layout, freeze, unfreeze, clear freeze, shrink, expand — already exists and is tested. The work is: intercept Shift+E in the Nuke DAG, enter a modal state, intercept subsequent keypresses via a Qt event filter, route them to existing commands, display a floating overlay HUD, and exit cleanly. No new layout algorithms are needed.

The recommended approach is a three-component architecture: (1) a `LeaderKeyFilter(QObject)` event filter installed on `QApplication.instance()` at startup, using a single boolean fast-path when leader mode is inactive; (2) a `LeaderKeyOverlay(QWidget)` top-level frameless widget positioned via `mapToGlobal()` over the DAG, with `WA_ShowWithoutActivating` to prevent focus theft; and (3) minimal modifications to `menu.py`, `node_layout_prefs.py`, `node_layout_prefs_dialog.py`, and `node_layout.py`. Two new files carry all new logic; the existing modules are touched minimally. This decomposition matches the established codebase pattern where PySide6 code lives in dedicated files separate from the layout engine.

The dominant risks are focus and timing. The overlay must never steal keyboard focus from the DAG or leader mode breaks on show. The event filter must be deferred past Nuke's startup widget initialization or it installs on nothing. The WASD keys must only be consumed inside leader mode or they silently break Nuke's built-in shortcuts (W=Insert Write, S=Project Settings, D=Disable/Enable). The Shift+E rebind must explicitly remove the old shortcut or both handlers fire simultaneously. All four risks have documented, well-tested mitigations.

---

## Key Findings

### Recommended Stack

No new pip dependencies. All required capability exists in PySide6 (already a project dependency) and the Nuke Python API. The work is entirely API usage patterns on the existing stack.

**Core APIs and patterns:**

- `QObject.installEventFilter()` on `QApplication.instance()` — intercepts all Qt events; single boolean short-circuit when inactive; correct scope for a plugin-wide modal mode
- `QEvent.Type.KeyPress` / `QKeyEvent.key()` + `QKeyEvent.modifiers()` — standard PySide6 key introspection; `Qt.Key.Key_V` etc. are uppercase-normalized regardless of shift state
- `QKeyEvent.isAutoRepeat()` — must be used to discard OS key-repeat events during WASD chaining; without this nodes overshoot on held keys
- `QWidget` with `WA_ShowWithoutActivating`, `FramelessWindowHint`, `WindowStaysOnTopHint`, `Qt.WindowType.Tool` — standard top-level floating overlay; must be positioned with `dag_widget.mapToGlobal()`
- `QTimer.singleShot(0, install_fn)` — defers event filter installation past Nuke's startup; required because DAG widgets do not exist when `menu.py` runs
- `QPainter.drawRoundedRect` + `drawText` — sufficient for key-cap overlay; use `overlay.update()` not `repaint()` to avoid blocking the event loop
- `QApplication.instance().allWidgets()` filtered by `"DAG" in objectName()` — version-stable DAG widget discovery; works on Nuke 16+ (`QWidget`) and older (`QGLWidget`) without class-type checks
- PySide6 fully-qualified enum syntax (`QEvent.Type.KeyPress`, `Qt.WindowType.FramelessWindowHint`, `Qt.WidgetAttribute.WA_ShowWithoutActivating`) — required throughout; PySide2-style bare access raises `AttributeError` on Nuke 16+

**Confidence:** HIGH (Qt official documentation + Erwan Leroy's Nuke Qt articles + Pixelmania's real-world event filter implementation + Foundry PySide6 migration guide)

### Expected Features

All dispatched commands already exist. The v1.4 feature work is the modal mechanics and overlay.

**Must have (table stakes):**

- Leader key arms mode exactly once — Shift+E is consumed, no other action fires, next keypress is the command
- Single-shot commands (V, Z, F, C, Q, E) exit mode immediately after dispatching
- WASD stays in leader mode after each move — chaining without re-pressing Shift+E; each press is one discrete move, not held-key scroll
- Any unrecognized key cancels mode and is swallowed — prevents accidental Nuke shortcut firing mid-sequence
- Mouse click cancels mode, event propagates — the click still lands (node selection works)
- ESC cancels mode
- FocusOut cancels mode — if the DAG loses focus (user clicks Properties panel), mode exits so those keypresses are never intercepted
- Overlay disappears on every exit path (command dispatch, ESC, unrecognized key, mouse click, FocusOut)
- Overlay shows which keys are active — minimum: key letter + short label per binding, readable against the DAG
- Context-aware V dispatch — 1 selected node calls `layout_upstream()`, 2+ calls `layout_selected()`
- Context-aware F dispatch — inspects freeze state via `node_layout_state.read_freeze_group()`, calls freeze or unfreeze accordingly
- `hint_popup_delay_ms` preference (int, default 0) — gates overlay display; 0 means show immediately (synchronously), >0 uses `QTimer.singleShot`
- WASD direction correctness — W decreases Ypos (up on screen), S increases Ypos (down); Nuke's Y-axis is positive-downward
- Key-repeat guard — `QKeyEvent.isAutoRepeat()` must filter OS-generated repeats for WASD
- Guard against double-entry — treat Shift+E while already in leader mode as a no-op

**Should have (differentiators):**

- QWERTY-spatial overlay layout — WASD cluster, Q/E flanking, V/Z/F/C group, ESC de-emphasized; exploits muscle memory
- Color coding by key type — sticky/chaining keys (WASD, Q, E) in one color; single-shot keys (V, Z, F, C) in another; mirrors Hydra's red/blue head model
- Single undo group for entire WASD session — open on leader entry, close on leader exit; one Ctrl+Z undoes the full movement session

**Defer indefinitely:**

- Customizable keymap — explicitly out of scope per PROJECT.md
- Timeout-based auto-cancel — anti-feature in VFX workflows; the user may pause mid-sequence to look at the DAG
- Nested leader sequences — no benefit for the current small command set
- Visual animation or flash on key dispatch — adds noise; node movement is sufficient feedback

### Architecture Approach

Two new files (`node_layout_leader.py`, `node_layout_overlay.py`) contain all new logic. Four existing files receive minimal, well-scoped additions. The `LeaderKeyFilter` is a module-level singleton installed on `QApplication` at startup via `QTimer.singleShot(0, ...)`. Context-aware dispatch (the V and F key logic) lives entirely in `node_layout_leader.py`; the underlying command functions in `node_layout.py` are called unchanged. The overlay is a top-level window (not a child of the DAG canvas) positioned via `mapToGlobal()` to avoid the Z-ordering and `QGLWidget` compositing problems that affect child widgets on older Nuke versions.

**Major components:**

1. `node_layout_leader.py` (NEW) — `LeaderKeyFilter(QObject)` event filter, `get_leader_filter()` singleton init called from `menu.py`, `activate_leader_mode()` entry point, full keymap dispatch table, context dispatch for V and F, WASD movement logic
2. `node_layout_overlay.py` (NEW) — `LeaderKeyOverlay(QWidget)`, `WA_ShowWithoutActivating`, `FramelessWindowHint + WindowStaysOnTopHint + Tool`, `show_with_delay()`, `paintEvent` key-cap rendering
3. `menu.py` (MODIFIED) — rebind `shift+e` to `activate_leader_mode()`; remove shortcut from the `Layout Upstream` menu entry; call `get_leader_filter()` via `QTimer.singleShot(0, ...)` at startup
4. `node_layout_prefs.py` (MODIFIED) — add `"hint_popup_delay_ms": 0` to DEFAULTS
5. `node_layout_prefs_dialog.py` (MODIFIED) — new "Leader Key" section with one QLineEdit field, `>= 0` validation
6. `node_layout.py` (MODIFIED) — add `clear_freeze_selected()` public function with undo group, following the freeze/unfreeze pattern, for the C key dispatch

### Critical Pitfalls

1. **Overlay steals keyboard focus** — Without `WA_ShowWithoutActivating` and `Qt.WindowType.Tool`, `overlay.show()` transfers focus from the DAG to the overlay; the event filter stops receiving keypresses; leader mode breaks on the first visible frame. Structural test must assert these attributes in `__init__`.

2. **Event filter installed before DAG widget exists** — `menu.py` runs at Nuke startup before the Qt widget tree is initialized; `allWidgets()` returns no DAG widgets; the filter installs on nothing; leader mode never works. Fix: `QTimer.singleShot(0, install_fn)` in `menu.py`.

3. **Shift+E fires both old and new handlers** — `nuke.addMenuCommand` appends, it does not replace. If the old `'Layout Upstream'` shortcut `'shift+e'` is not explicitly removed, both commands run on Shift+E. The layout fires immediately, before leader mode activates.

4. **WASD consumed outside leader mode** — The event filter must return `False` unconditionally when `_active is False`. Any `True` return outside leader mode permanently breaks the corresponding Nuke built-in shortcut (W=Insert Write, S=Project Settings, D=Disable/Enable, F=Fit View, C=Insert ColorCorrect, Q=Script Info).

5. **Overlay invisible due to incorrect parenting** — Parenting the overlay as a child of the DAG canvas risks it being obscured by the DAG's own painting, especially on older Nuke versions where the DAG used `QGLWidget`. The overlay must be a top-level window positioned with `mapToGlobal()`, not a child widget.

6. **WASD key-repeat causes nodes to overshoot** — The OS generates repeated `KeyPress` events while a key is held. Without checking `QKeyEvent.isAutoRepeat()` and discarding those events, each held WASD key triggers dozens of move operations.

7. **WASD undo explosion** — `setXpos`/`setYpos` creates one undo entry per node per call. Five WASD presses on a 10-node selection creates 50 undo entries. Wrap the entire leader session in a single `nuke.Undo.begin()` / `nuke.Undo.end()` group, following the existing try/except/else undo pattern in the codebase.

---

## Implications for Roadmap

The build order is driven by three constraints: (a) the overlay must exist before the filter references it; (b) the prefs key must exist before any code reads it; (c) the `menu.py` rebind is the highest-impact one-way activation step and must come last.

### Phase 1: Prefs + Dialog Foundation

**Rationale:** The `hint_popup_delay_ms` pref key must exist before any other component reads it. This is a pure data change with no Qt runtime dependency — fully testable with AST/structural tests. No risk of regressions; fully isolated.

**Delivers:** `hint_popup_delay_ms` in DEFAULTS, new "Leader Key" section in the prefs dialog with one QLineEdit field, populate/save wiring, `>= 0` validation.

**Files:** `node_layout_prefs.py`, `node_layout_prefs_dialog.py`

**Avoids:** Pitfall 16 (PySide6 enum syntax must be used throughout the dialog)

### Phase 2: Overlay Widget

**Rationale:** The overlay is independently testable without a Nuke runtime. Building it before the event filter lets the filter reference a stable overlay API. The critical correctness properties (window flags, `WA_ShowWithoutActivating`, no focus steal) can be verified via structural tests before any Nuke integration.

**Delivers:** `node_layout_overlay.py` with `LeaderKeyOverlay` class. Top-level frameless window with `WA_ShowWithoutActivating`, all window flags in a single `setWindowFlags()` call, `WA_TranslucentBackground`, `show_with_delay()`, `paintEvent` key-cap rendering with QWERTY-spatial grouping.

**Implements:** Architecture component 2

**Avoids:** Pitfall 7 (focus steal via `WA_ShowWithoutActivating`), Pitfall 8 (invisible child widget — use top-level + `mapToGlobal()`), Pitfall 9 (stale position — recalculate at each activation), Pitfall 10 (flag ordering — single `setWindowFlags()` call before `show()`), Pitfall 13 (use `update()` not `repaint()`; keep `paintEvent` minimal), Pitfall 15 (`QDesktopWidget` is removed in PySide6 — use `QWidget.screen()`)

### Phase 3: Event Filter + Core Dispatch

**Rationale:** Depends on overlay (Phase 2) and prefs (Phase 1). This is the core integration: the `LeaderKeyFilter` singleton, `activate_leader_mode()`, and dispatch for all non-WASD keys (V, Z, F, C, Q, E, ESC, unrecognized key, mouse click, FocusOut). WASD movement is deferred to Phase 4 so the core state machine is stable before new node-position logic is added.

**Delivers:** `node_layout_leader.py` with full state machine (active/inactive), context dispatch for V and F, single-shot exit for V/Z/F/C/Q/E, cancellation for ESC/unrecognized/mouse/FocusOut.

**Implements:** Architecture component 1 (minus WASD)

**Avoids:** Pitfall 1 (find DAG by `objectName()`, not class type), Pitfall 2 (deferred install via `QTimer.singleShot(0, ...)`), Pitfall 3 (handle `MouseButtonPress` and `FocusOut` as cancel triggers), Pitfall 4 (widget-level focus guard; cancel on `FocusOut`), Pitfall 5 (gate all consumption behind `_active` check), Pitfall 12 (removeEventFilter before installEventFilter; singleton reuse), Pitfall 17 (install on all visible DAG widgets at leader mode entry, not only root DAG)

### Phase 4: WASD Movement + C Command

**Rationale:** WASD movement involves new node-position delta logic (`setXpos`/`setYpos` with `get_dag_snap_threshold()`) that is independent of the event filter structure. Adding it after the filter is stable makes it an incremental extension to the dispatch table. The C command requires a new `node_layout.py` function — a small addition with its own undo group, following the established freeze/unfreeze pattern.

**Delivers:** WASD dispatch in `node_layout_leader.py` (stays-in-mode, key-repeat guard, single undo session group), `clear_freeze_selected()` in `node_layout.py`.

**Implements:** Architecture component 1 (WASD completion), Architecture component 6

**Avoids:** Pitfall 5 (WASD only consumed in leader mode), Pitfall 6 (W decreases Ypos, S increases Ypos — test direction explicitly against Nuke's positive-Y-downward coordinate system), Pitfall 16 (PySide6 enum syntax), Pitfall 18 (single undo group for full session)

**Open question for this phase:** Q and E (shrink/expand) — ARCHITECTURE.md marks these as "stays in leader mode (TBD — check spec)." Confirm with PROJECT.md whether Q/E are single-shot exits or chaining keys before implementing. The decision affects whether the WASD undo group encompasses Q/E presses.

### Phase 5: Menu Wiring + Activation

**Rationale:** This is the one-way activation step. All prior phases must be validated before this change goes in. The only change is `menu.py`: rebind `shift+e`, remove old shortcut from `Layout Upstream`, call `get_leader_filter()` via deferred timer. Once committed, Shift+E no longer runs `layout_upstream` directly.

**Delivers:** `shift+e` bound to `activate_leader_mode()`; old `Layout Upstream` entry retained without shortcut; filter singleton initialized at startup.

**Files:** `menu.py`

**Avoids:** Pitfall 11 (explicitly remove the shortcut from `Layout Upstream` before registering leader entry under the same key; verify no duplicate binding via Nuke Script Editor startup warnings)

### Phase Ordering Rationale

- Phases 1 and 2 have no inter-dependency and could be parallelized, but sequencing keeps each phase focused and independently verifiable before the next builds on it.
- Phase 3 must follow 1 and 2: the filter reads the delay pref and references the overlay class.
- Phase 4 adds WASD to the Phase 3 module without touching its core state machine — incremental and low-risk.
- Phase 5 is always last because it activates the system in the live Nuke UI; all correctness testing happens in Phases 1–4.

### Research Flags

Phases with standard patterns (skip research-phase during planning):

- **Phase 1 (Prefs + Dialog):** Well-established pattern in this codebase; identical to existing QLineEdit field additions.
- **Phase 5 (Menu Wiring):** Two-line change to `menu.py`; the pattern is used for every other menu command.

Phases that warrant careful implementation review (flag for UAT):

- **Phase 2 (Overlay Widget):** Focus safety is subtle. Structural test for `WA_ShowWithoutActivating` is mandatory. UAT must confirm: show overlay, immediately press a recognized leader key, verify mode did not break.
- **Phase 3 (Event Filter):** The FocusOut cancellation path and multi-DAG install (Group DAGs) need explicit test cases. UAT must cover: click into the Properties panel while in leader mode; verify cancellation.
- **Phase 4 (WASD + C):** Undo group scope for Q/E (single-shot vs. chaining) needs spec confirmation before implementation. WASD direction must be verified in actual Nuke (positive Y is down; W must decrease Ypos).

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All APIs verified via Qt official docs + Foundry migration guide + real Nuke community implementations. No new dependencies. |
| Features | HIGH | Dispatch table and all existing commands confirmed in codebase. UX model well-documented via Vim/Hydra/Blender analogues. |
| Architecture | HIGH | Based on direct codebase analysis + verified Qt patterns. Component boundaries are clean and dependency graph is unambiguous. |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls 1–11 are HIGH confidence (Qt docs + Nuke community). Pitfalls 12, 17, 18 are MEDIUM (reasoning from established patterns; need test confirmation). |

**Overall confidence:** HIGH

### Gaps to Address

- **Q/E sticky vs single-shot:** ARCHITECTURE.md marks this as "TBD — check spec." Before Phase 4 implementation, confirm from PROJECT.md whether Q (shrink) and E (expand) keep leader mode active or exit after dispatch. This determines whether the WASD undo group encompasses Q/E presses.

- **Group DAG overlay positioning:** The overlay must be positioned over the focused DAG, which may be a Group DAG (`"DAG.GroupName"`) when the user is inside a Group. Confirm the overlay positioning logic correctly identifies the focused Group DAG widget at activation time, not always the root `"DAG"` widget.

- **FocusOut cancellation on Linux/X11:** PITFALLS.md notes that on Linux, `Qt.WidgetAttribute.WA_X11DoNotAcceptFocus` may also be needed on the overlay. This is a MEDIUM confidence finding; validate during UAT on the target platform.

- **Overlay corner position:** Research recommends bottom-left or bottom-right as default. Check PROJECT.md for a specified corner preference before locking in the `paintEvent` geometry constants.

---

## Sources

### Primary (HIGH confidence)

- Qt for Python official documentation — `QObject.installEventFilter()`, `QEvent.Type`, `QKeyEvent.isAutoRepeat()`, `QWidget.WA_ShowWithoutActivating`, `Qt.WindowType`, `QPainter`
- Foundry — Q100715: How to address Python PySide issues in Nuke 16+ (PySide6 migration, enum access)
- Foundry — Nuke 16.0v1 Release Notes (PySide6 adoption, QWidget DAG)
- Foundry — Nuke Python API Reference: `nuke.addMenuCommand`, `shortcutContext` parameter
- Foundry — Nuke Keyboard Shortcuts (W/S/D/F/C/Q DAG single-key bindings)
- Direct codebase analysis — `node_layout.py`, `node_layout_prefs.py`, `node_layout_prefs_dialog.py`, `node_layout_state.py`, `menu.py` (2026-03-28)

### Secondary (MEDIUM-HIGH confidence)

- Erwan Leroy — "Nuke Node graph utilities using Qt/PySide2" — DAG widget objectName pattern, `allWidgets()` enumeration
- Erwan Leroy — "Updating Your Python Scripts for Nuke 16 and PySide6" — DAG QWidget migration, Group DAG naming
- Pixelmania — "Fixing an annoying Nuke feature" — per-widget `installEventFilter` on Nuke DAG, `return True` consumption verified in practice
- herronelou/nuke_nodegraph_utils (GitHub) — overlay parenting and DAG utility patterns, prior art

### Secondary (MEDIUM confidence)

- folke/which-key.nvim, abo-abo/hydra — leader key UX model: delay-before-popup, sticky vs single-shot head types, foreign-key pass-through behavior
- Nuke Python mailing list — `QTimer.singleShot(0)` pattern for deferred widget access post-startup
- Qt Forum — `WA_ShowWithoutActivating` for focus-safe overlays; `WindowStaysOnTopHint` flag ordering

---

*Research completed: 2026-03-28*
*Ready for roadmap: yes*
