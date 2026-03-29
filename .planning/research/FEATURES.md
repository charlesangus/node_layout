# Feature Landscape

**Domain:** Nuke DAG layout plugin — v1.4 Leader Key modal input system
**Researched:** 2026-03-28
**Milestone context:** Subsequent milestone adding modal leader-key dispatch and keyboard overlay to an existing plugin with all underlying commands already implemented.

---

## Context: What Already Exists

Every command this milestone dispatches to is already implemented and tested:

- `layout_upstream()` / `layout_selected()` — vertical layout
- `layout_selected_horizontal()` — horizontal B-spine layout
- Freeze / unfreeze / clear freeze group
- Move selected nodes (W/A/S/D directions)
- Shrink / expand selected (Q/E)

The v1.4 milestone is purely a **UX layer**: intercept a trigger key, enter modal state, dispatch to existing functions, display an overlay, exit cleanly. No new layout engine work is needed.

---

## Analogous Systems in the Wild

### Vim + which-key.nvim (highest relevance)

The canonical leader-key pattern. A prefix key (`<leader>`) arms the input system; the next key dispatches a command. The which-key.nvim plugin adds a timed hint popup. Key design decisions from this ecosystem:

- **Delay before popup, not before dispatch.** The keystroke dispatches instantly. The hint overlay only appears if the user pauses (configurable, default 200 ms in which-key, 0 ms is valid for always-show). This means fast users never see the overlay; slow or learning users always do. Confidence: HIGH (confirmed in which-key.nvim docs).
- **Foreign key behavior is a critical design choice.** Vim leader mode exits immediately on any unrecognized key. The unrecognized key is then executed as a normal Nuke shortcut (pass-through). The alternative (swallow the key and flash an error) is universally disliked. Confidence: HIGH (Vim behavior is well-documented; community consensus is strong).
- **Sticky vs single-shot keys.** In which-key/Hydra terminology: single-shot keys exit the mode after executing; sticky/repeating keys keep the mode alive. WASD movement is the canonical sticky case — the user presses W several times without re-pressing the leader. All other commands in this milestone are single-shot (one dispatch, mode exits). Confidence: HIGH (Hydra README explicitly models this as "red" vs "blue" heads).

### Emacs Hydra / Transient (high relevance for WASD chaining)

Hydra is the Emacs equivalent of what this milestone needs:

- **Red heads (sticky):** After calling, mode stays active. The user presses W/A/S/D multiple times, moving nodes one step at a time. Mode stays until an explicit exit or a non-WASD key is pressed.
- **Blue heads (single-shot):** V, Z, F, C, Q, E — each dispatches once and drops back to normal mode.
- **Foreign keys on a sticky hydra exit cleanly and pass through.** This prevents the user from getting "stuck" if they absentmindedly type something unrelated.
- **Hint display at session start.** Hydra shows hints immediately (or after a timer) at the bottom of the screen. For VFX tools, positioning in a fixed corner of the DAG is the equivalent.
- Confidence: HIGH (Hydra README and Emacs repeat-mode documentation confirm these patterns).

### Blender Modal Operators (medium relevance)

Blender's modal operator pattern is the closest analogue in a creative tool:

- Modal operators receive all keyboard events while active. Any event not handled explicitly by the operator passes through or cancels it.
- ESC cancels. Right-click cancels. Any unhandled key type cancels and passes through (similar to Vim foreign key behavior).
- Status bar text updates to show available keys while modal is active — this is Blender's equivalent of the overlay.
- Confidence: MEDIUM (Blender Python API docs confirmed; exact behavior slightly version-dependent).

### Maya Hotbox / W_hotbox for Nuke (directly relevant UX precedent)

W_hotbox is a modal context menu for Nuke modeled on Maya's hotbox:

- Press-and-hold trigger: overlay appears while key is depressed, dismisses on release. This is a different trigger model than a leader key (toggle vs hold), but the visual layer architecture is the same.
- The overlay is a selection-aware context menu positioned under the cursor.
- The design principle: overlay appears near the cursor, not at a fixed screen edge, because the user's attention is already on the cursor.
- For the node_layout leader key, the overlay is not cursor-positioned (it's a fixed panel) because the commands apply to the entire selection, not the hovered node. A bottom-of-DAG or top-of-DAG fixed position is more appropriate.
- Confidence: MEDIUM (W_hotbox behavior observed from Nukepedia and community tutorials; not official Foundry documentation).

---

## Table Stakes

Features users expect from a leader-key modal input system. Missing or broken = the feature feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Leader key arms mode exactly once | The Shift+E press is consumed, nothing else executes; next keypress is the command key. Mode is active from leader press to command dispatch (or cancel). | Low | Must intercept the Shift+E event before Nuke's own shortcut handler sees it — requires QApplication.installEventFilter or equivalent. |
| Single-shot commands exit mode immediately | V, Z, F, C, Q, E each dispatch their command and drop back to normal mode. User is never "stuck" in leader mode after a single-shot command. | Low | State flag `_in_leader_mode` reset after dispatch. |
| WASD stays in leader mode after each move | Each W/A/S/D keypress executes the move and keeps mode alive. The user can press WASD in any order repeatedly without re-pressing Shift+E. | Low-Medium | State flag NOT reset after WASD dispatch. Different code path from single-shot keys. |
| Any unrecognized key cancels mode | Typing a letter not in the keymap (e.g., pressing T) cancels leader mode. The T is consumed (not passed to Nuke). Rationale: passing through the unrecognized key risks triggering unrelated Nuke commands mid-sequence. | Low | This is the standard behavior for a fixed keymap. Note: Vim passes through foreign keys; for a small fixed keymap, swallowing is safer to avoid e.g. accidentally opening a node panel. |
| Mouse click cancels mode | Clicking in the DAG cancels leader mode. The mouse event is not consumed — the click still lands (e.g., to select a node). | Low | installEventFilter must intercept mouse events on the DAG and cancel mode, then let the event propagate normally. |
| ESC cancels mode | Users expect Escape to be a universal cancel in any modal state. | Low | Map ESC key event to mode cancel. |
| Overlay appears immediately on leader press (when delay = 0) | With default pref "hint popup delay" = 0, the overlay is visible from the moment the user presses Shift+E. No separate delay step needed for the default case. | Low | If delay > 0: use QTimer to defer overlay display; the overlay still must appear before the user could press a second key at a normal typing speed (200 ms window). |
| Overlay disappears on mode exit | Whether the user executes a command or cancels, the overlay is removed from the DAG before any command runs (or at latest on the same UI update tick). | Low | Call overlay.hide() (or overlay.close()) immediately on any exit path: command dispatch, foreign key, ESC, mouse click. |
| Overlay shows exactly which keys are active | Users must be able to read the available keybindings while in leader mode. Minimum: key letter + short label per binding. No extraneous information. | Medium | The set of keys is fixed (V, Z, F, C, W, A, S, D, Q, E, ESC); labels should be derived from the same source of truth as the dispatch table to avoid drift. |
| Commands run inside undo groups | V (layout), Z (horizontal layout), F (freeze toggle), C (clear freeze) must each be wrapped in a Nuke undo group, consistent with all other node_layout commands. | Low | The underlying commands already do this; the leader key dispatcher just calls them. No extra undo wrapping needed at the dispatch layer unless the overlay itself modifies state. |
| Mode does not fire if nothing is selected for selection-required commands | V with 2+ nodes selected runs layout_selected; V with 1 node runs layout_upstream; V with 0 nodes selected should cancel mode and do nothing (existing fail-silent contract). | Low | Existing commands already handle this; no change needed at dispatch layer. |

---

## Differentiators

Features that meaningfully improve the UX above the minimum viable leader key.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Context-aware V dispatch (1 node → upstream, 2+ → selection) | Instead of two separate menu commands, one key handles both cases intelligently. Power users don't need to think about which layout command to invoke. | Low | Already specified in PROJECT.md; the dispatch logic is a single `len(nuke.selectedNodes())` check. |
| F as freeze/unfreeze toggle (not two separate keys) | Reduces cognitive load. Single mnemonic (F = freeze) covers both directions. | Low | Needs to inspect current freeze state of selection to determine direction. Existing freeze/unfreeze commands cover both paths. |
| Hint popup delay configurable to 0 | Experienced users can set delay=0 to always see the overlay; they can also set delay=500 or higher to never see it during fast operation. This matches the which-key.nvim mental model exactly. | Low | One new pref key: `leader_hint_delay_ms` (int, default 0). Stored in node_layout_prefs.json. |
| Overlay positioned at a fixed corner of the DAG | Users know exactly where to look without hunting. Fixed-corner positioning is less disorienting than cursor-relative positioning for a command dispatch overlay (vs a context menu). | Low-Medium | The DAG widget's geometry is accessible via Qt; overlay can be parented to the DAG widget and anchored to e.g. top-left or bottom-right corner with a fixed margin. |
| Icon-style keyboard layout in overlay (not a flat list) | Arranging keys in a rough QWERTY-row layout makes spatial memory possible. WASD appears as a cluster; Q/E flank it. V/Z appear in a separate group. Users remember positions, not just labels. | Medium | Requires custom QWidget layout rather than a plain QLabel or QTextEdit. A QGridLayout or manual paintEvent drawing with key-shaped boxes. |
| Overlay key highlighting while WASD chaining | While in leader mode with WASD active, the W/A/S/D keys in the overlay are visually distinct (e.g., highlighted or brighter) to reinforce that the user is still in the mode. | Medium | Requires the overlay widget to have mutable visual state (not a static label). The same mechanism would highlight ESC as always-available. |

---

## Anti-Features

Features to explicitly avoid in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Timeout to auto-cancel leader mode | Which-key has a timeout option; Vim does not. For a VFX tool where the user might pause mid-sequence to think or look at the DAG, a timeout creates false cancellations that feel like bugs. The overlay makes it obvious you are in leader mode. | No timeout. Only explicit cancellation: command dispatch (single-shot), ESC, unrecognized key, mouse click. |
| Nested leader sequences (leader → sub-mode → command) | Two-level sequences (e.g., Shift+E → G → something) increase cognitive load with no benefit given the small command set. All commands are reachable in one key from leader. | Keep the keymap flat: leader + one key = command. |
| Visual feedback for each WASD press (flash / animation) | Animating the overlay or flashing nodes on each WASD movement adds visual noise and frame budget cost. Move commands already provide instant spatial feedback via node position change. | Let node position change be the feedback. The overlay persisting is sufficient signal that mode is still active. |
| Auditory feedback (beep on invalid key) | Nuke doesn't use audio feedback; introducing it would be jarring and inconsistent with the host application. | Silently swallow the unrecognized key and cancel mode. |
| Customizable keymap in prefs | Explicitly out of scope per PROJECT.md. Conflict probability is low; document fixed bindings in README. | Document all leader key bindings in README. |
| Overlay that steals keyboard focus from the DAG | If the overlay widget gains keyboard focus, key events go to it rather than being intercepted at the application level. Mode breaks immediately on overlay display. | Overlay must have Qt.WindowDoesNotAcceptFocus + Qt.FramelessWindowHint flags. Never call overlay.setFocus() or overlay.activateWindow(). |
| Per-command undo granularity at the leader-key layer | The dispatcher is a thin routing layer. It must not add any undo wrapping beyond what the underlying commands already implement. Double-wrapping undo groups breaks Nuke's undo stack. | Call existing commands directly, without additional undo wrapping at the dispatch layer. |

---

## Feature Dependencies

```
Shift+E intercept (QApplication eventFilter)
  → arms _in_leader_mode flag
  → triggers overlay display (immediate, or after QTimer(delay))

Overlay widget
  → parented to DAG widget (requires find_dag_widget() helper)
  → positioned at fixed corner via Qt geometry
  → must NOT steal keyboard focus (WindowDoesNotAcceptFocus flag)
  → hidden on any mode-exit path

Leader mode dispatch table
  → V: layout_upstream() if 1 selected, layout_selected() if 2+ selected
  → Z: layout_selected_horizontal()
  → F: freeze_selected() if unfrozen, unfreeze_selected() if frozen
  → C: clear_freeze_group()
  → W/A/S/D: move_selected_nodes(direction) + keep mode alive
  → Q: shrink_selected()
  → E: expand_selected()
  → ESC / unrecognized / mouse: cancel mode, hide overlay

Mode exit cleanup
  → overlay.hide()
  → _in_leader_mode = False
  → unrecognized key: swallow event (do not propagate)
  → mouse click: cancel mode, propagate event

New pref: leader_hint_delay_ms
  → read at leader-key press time
  → 0 = overlay shows immediately
  → >0 = QTimer delays overlay display; if mode exits before timer fires, cancel timer

find_dag_widget() helper
  → iterate QApplication.instance().allWidgets()
  → match objectName() == "DAG" for root context
  → objectName() == "DAG.GroupName" for group context (Nuke 16+)
  → Nuke 11–15: DAG was a QOpenGLWidget; Nuke 16+: DAG is a standard QWidget
  → helper must handle both cases (check by objectName, not class type)
```

---

## UX Expectations by Area

### Modal Entry and Exit

**Entry:** Shift+E is consumed. No other action fires. Leader mode becomes active. The overlay appears (immediately or after delay). The status bar text (if accessible) is not used — the overlay is the sole feedback mechanism.

**Single-shot exit:** User presses V, Z, F, C, Q, or E. Command runs. Overlay hides. Mode exits. Net result: one keystroke beyond the leader dispatches one command. The user is immediately back in normal Nuke operation.

**Chained exit:** User presses W, A, S, or D one or more times. Each keypress moves nodes and keeps mode alive. User presses ESC, any non-WASD key, or clicks to exit. Overlay hides. Mode exits.

**Cancellation:** User presses ESC, an unrecognized key, or clicks in the DAG. Mode exits. The cancellation event is consumed (not passed to Nuke) to avoid side effects.

**Re-entry:** After any exit, the user can press Shift+E again to re-enter leader mode. No cooldown.

### WASD Chaining Feel

The expected UX is identical to how users navigate in a game with arrow keys, or how they nudge objects in Adobe Illustrator / After Effects. Each keypress is one discrete move (not a held-key scroll). The move increment must be large enough to be visually useful but not so large that precise placement becomes impossible — the existing `move_selected_nodes()` increment applies. The user holds no keys; they type individual keypresses.

**Critical pitfall to avoid:** If the keydown event fires a move, and the key-repeat mechanism in the OS then fires additional events while the key is held, nodes will overshoot. The event filter must dispatch on the first key event for a given key and discard subsequent key-repeat events for that key (`QKeyEvent.isAutoRepeat()` returns True for OS-generated repeats). Confidence: HIGH (Qt QKeyEvent.isAutoRepeat() is documented; this is a real and common pitfall).

### Overlay Design

**Information hierarchy:**
1. The keys that dispatch commands (primary) — shown large with a key-cap visual style
2. The label for each command (secondary) — short, shown directly on or below each key cap
3. The ESC / cancel path (tertiary) — shown but visually de-emphasized

**Density:** The keymap is small (10 action keys + ESC). There is no need for scrolling, sections, or a search box. The entire overlay should fit in a ~250×150 px panel.

**Key grouping (QWERTY spatial layout):**
```
[Q]   [W]   [E]
[A]   [S]   [D]

      [V]   [Z]
      [F]   [C]

            [ESC]
```
This layout exploits existing muscle memory: WASD as a movement cluster (identical to gaming), Q/E flanking as scale-down/up. V/Z/F/C are grouped separately as they are single-shot structural commands.

**Color coding (optional differentiator):**
- WASD and Q/E in one color (sticky / repeating mode)
- V/Z/F/C in another color (single-shot exit mode)
- ESC in a neutral/muted color

This directly mirrors Hydra's color coding for head types and gives users an immediate visual cue about which keys exit vs. persist the mode.

**Font and contrast:** Text must be readable against the DAG background, which varies by user theme. A semi-transparent dark background panel with light text is the safest default (used by W_hotbox and similar tools in the Nuke ecosystem).

**No decorative elements.** No animation, no border glow, no gradient. Power users find decoration distracting; clarity is the value.

### Overlay Focus Safety

This is the most critical technical constraint for the overlay. If the overlay widget receives keyboard focus, all subsequent key events go to it rather than being processed by the event filter. The leader mode input system breaks entirely.

Required Qt flags on the overlay window:
- `Qt.WindowDoesNotAcceptFocus` — window never gets keyboard focus
- `Qt.FramelessWindowHint` — no window chrome
- `Qt.ToolTip` or `Qt.SubWindow` with explicit `setAttribute(Qt.WA_ShowWithoutActivating)` — prevents activation on show

Never call `.show()` via `QDialog.exec_()` or any blocking show method. Use `QWidget.show()` only. Confidence: HIGH (Qt documentation on focus policies is authoritative; this is a documented requirement for non-focus overlay windows).

---

## Edge Cases to Handle

| Edge Case | Expected Behavior | Risk if Not Handled |
|-----------|-------------------|---------------------|
| No DAG widget found (e.g., running headless or in a group context with a different name) | Leader mode enters but overlay silently does not display. Commands still dispatch normally. Log a warning at most. | No overlay → user confusion, but commands still work. Acceptable degradation. |
| Multiple DAG panels open (Nuke allows tiling multiple DAGs) | Event filter intercepts keys for the DAG that had focus when Shift+E was pressed. Overlay appears on that DAG. Other DAGs are unaffected. | Incorrect DAG gets overlay, or event filter intercepts keys on wrong DAG. Must track which DAG received the arming keypress. |
| Shift+E pressed while a dialog is open | QApplication event filter fires for all events. Must check if a Nuke dialog or property panel has focus and NOT arm leader mode in that case. Otherwise typing in a dialog field triggers the leader key mid-text-entry. | Catastrophic — interrupts user typing in dialogs. Must be guarded. |
| Key-repeat events for WASD | OS generates repeated keydown events when a key is held. These must be discarded (`QKeyEvent.isAutoRepeat() == True`). Only the initial press triggers a move. | Nodes fly across the DAG while the key is held. Very bad UX. |
| Unrecognized key is a Nuke built-in shortcut | If the user accidentally presses a Nuke shortcut key (e.g., Tab to open the node browser), that key is swallowed by the leader mode event filter. It does not reach Nuke. Mode cancels. The user must re-press Tab after mode exits. | Minor confusion. Acceptable given the small keymap and the clarity of the overlay. Alternative (pass through) risks executing unintended Nuke commands mid-leader-sequence. |
| Nuke undo stack interaction | V, Z, F, C, Q, E each produce one undo entry (their existing undo groups). Pressing WASD 5 times produces 5 undo entries. The leader mode itself produces no undo entry (it is not a state change, only a UI mode). | If the leader key itself were wrapped in an undo group, Ctrl+Z after a WASD session would undo the entire session as one block — unexpected behavior. |
| Shift+E pressed while already in leader mode | Treat as a no-op or as a cancel. Do not create nested leader modes. | Double-entry: two overlays, two event filters. Must guard with `if _in_leader_mode: return`. |
| Nuke 11–15 vs Nuke 16+ DAG widget type | In Nuke 11–15, the DAG is a QGLWidget/QOpenGLWidget. In Nuke 16+, it is a standard QWidget. The find_dag_widget() helper must use objectName-based detection (works in both versions) rather than class-type detection (breaks in one version). | Widget not found → no event filter installed → leader key press reaches Nuke's default handler (currently Layout Upstream) instead of entering leader mode. |
| V with 0 nodes selected | Do nothing and cancel mode. Existing commands fail silently; leader mode should mirror that. | No breakage; just confirm silence is the contract. |
| F with a mixed selection (some frozen, some not) | Existing freeze/unfreeze commands handle this. Leader key dispatch does not need to add logic. Pass through to existing command. | No edge case at the leader layer; ensure the existing command's behavior is acceptable. |

---

## MVP Recommendation for v1.4

**Phase 1 (core modal mechanics, no overlay):**
1. `find_dag_widget()` helper — needed before any DAG-targeted behavior
2. QApplication event filter — intercepts Shift+E, arms leader mode, intercepts subsequent keys, cancels on ESC/mouse/unrecognized
3. Dispatch table — routes keys to existing commands; WASD does not exit, all others do
4. New pref key: `leader_hint_delay_ms` (int, default 0) — pref infrastructure only, no overlay yet

**Phase 2 (overlay):**
5. Overlay widget — QWidget with no focus, parented to DAG, positioned at fixed corner
6. Key-cap layout — QWERTY-style grid with WASD cluster and single-shot group
7. Delay logic — QTimer gates overlay appearance when delay > 0

**Ship together:** Both phases are in scope for v1.4. Phase 1 is the foundation; Phase 2 is small once the overlay widget is wired to the existing mode flag.

**Defer indefinitely:**
- Color-coded key types in overlay (nice-to-have; add in a future polish pass)
- Overlay key highlighting during WASD chaining (same)
- Any form of keyboard shortcut customization

---

## Complexity Summary

| Component | Estimated Complexity | Confidence |
|-----------|---------------------|------------|
| QApplication event filter (Shift+E intercept) | Low-Medium | HIGH — well-documented Qt pattern, used in Nuke community tools |
| find_dag_widget() across Nuke versions | Low | HIGH — objectName "DAG" approach confirmed for Nuke 16+; works in older versions too |
| Dispatch table with sticky/single-shot distinction | Low | HIGH — simple state machine with `_in_leader_mode` flag |
| Key-repeat guard (QKeyEvent.isAutoRepeat) | Low | HIGH — Qt API; straightforward |
| Overlay widget (no focus, parented to DAG) | Medium | HIGH — Qt focus flags well-documented; DAG overlay pattern has prior art (Erwan Leroy's nuke_nodegraph_utils) |
| Overlay key-cap layout (custom QWidget) | Medium | MEDIUM — requires custom painting or QGridLayout; no prior art in node_layout codebase |
| Dialog-focus guard (prevent Shift+E in text fields) | Low-Medium | MEDIUM — requires checking QApplication.focusWidget() class type at event filter time |
| New pref key + dialog field | Low | HIGH — follows existing Labelmaker/node_layout prefs pattern exactly |
| QTimer for hint delay | Low | HIGH — standard Qt pattern |

---

## Sources

- Vim leader key and which-key.nvim hint popup delay: [folke/which-key.nvim GitHub](https://github.com/folke/which-key.nvim), [vim-which-key liuchengxu](https://liuchengxu.github.io/vim-which-key/), [DEV Community — Leader keys and keyboard sequences](https://dev.to/stroiman/leader-keys-and-mapping-keyboard-sequences-3ehm)
- Emacs Hydra sticky vs single-shot head types: [abo-abo/hydra GitHub](https://github.com/abo-abo/hydra), [Persistent prefix keymaps — Karthinks](https://karthinks.com/software/persistent-prefix-keymaps-in-emacs/)
- Blender modal operator event handling: [Blender Python API — Operator](https://docs.blender.org/api/current/bpy.types.Operator.html), [Modal Addon Keymaps — Blender Developer Forum](https://devtalk.blender.org/t/modal-addon-keymaps/17444)
- W_hotbox Nuke press-and-hold overlay pattern: [W_hotbox — Nukepedia](https://www.nukepedia.com/tools/python/ui/w_hotbox/), [melMass/W_hotbox GitHub](https://github.com/melMass/W_hotbox)
- Nuke DAG widget finding (objectName approach, Nuke 16 QWidget migration): [Erwan Leroy — Updating for Nuke 16 and PySide6](https://erwanleroy.com/updating-your-python-scripts-for-nuke-16-and-pyside6/), [Erwan Leroy — Nuke Node Graph Utilities](https://erwanleroy.com/nuke-node-graph-utilities-using-qt-pyside2/), [herronelou/nuke_nodegraph_utils GitHub](https://github.com/herronelou/nuke_nodegraph_utils)
- Qt event filter and focus management: [Qt Keyboard Focus in Widgets](https://doc.qt.io/qt-6/focus.html), [Qt QKeyEvent](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QKeyEvent.html), [Qt Event System](https://doc.qt.io/qtforpython-6.8/overviews/qtcore-eventsandfilters.html)
- Qt overlay window without focus: [Qt QWidget documentation](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html), Qt WindowDoesNotAcceptFocus flag
- NN/G instructional overlay guidelines: [NN/G — Instructional Overlays and Coach Marks](https://www.nngroup.com/articles/mobile-instructional-overlay/)
- Focus stealing as a mode error: [Focus stealing — Wikipedia](https://en.wikipedia.org/wiki/Focus_stealing)

**Confidence notes:**
- Event filter pattern for Nuke DAG keyboard intercept: HIGH — multiple community implementations confirm; Qt API is authoritative
- QKeyEvent.isAutoRepeat() for key-repeat guard: HIGH — Qt API, well-documented
- Qt.WindowDoesNotAcceptFocus for overlay: HIGH — Qt API, well-documented
- Overlay parenting to DAG widget: MEDIUM — prior art from nuke_nodegraph_utils; exact API calls need verification against Nuke 11–15 vs 16+ DAG widget type differences
- Dialog-focus guard approach (focusWidget() class check): MEDIUM — standard Qt idiom; exact implementation needs testing in Nuke
- Blender modal operator exact cancellation behavior: MEDIUM — derived from Blender Python API docs; minor version variation possible
