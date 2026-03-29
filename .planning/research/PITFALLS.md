# Domain Pitfalls — node_layout v1.4 Leader Key

**Domain:** Nuke DAG auto-layout plugin — adding modal leader key + Qt overlay widget to existing plugin
**Researched:** 2026-03-28
**Scope:** Integration pitfalls for adding a Qt event-filter-based modal "leader key" system and
floating translucent overlay HUD to the existing node_layout plugin. Covers event filter
installation, overlay widget setup, leader mode state management, keyboard conflict
handling, focus management, and performance.

---

## Critical Pitfalls

Mistakes that cause rewrites, stuck UI state, broken Nuke input, or overlay that never appears.

---

### Pitfall 1: Event Filter Installed on Wrong Widget — Keypresses Never Received

**What goes wrong:**
The event filter is installed on the wrong widget in Nuke's Qt hierarchy. Keypresses directed
at the DAG are not delivered to the filter because events go to the widget that has keyboard
focus, not necessarily the widget you installed the filter on. A filter on a parent container
that does not actually receive `KeyPress` events (because its child has focus) silently misses
every keypress.

**Why it happens:**
Qt delivers `KeyPress` events to the focused widget. In Nuke's DAG, keyboard focus belongs to
the specific viewport widget (the DAG canvas) — found by `objectName() == "DAG"` (or
`"DAG.GroupName"` for Group DAGs in Nuke 16+). Installing the filter on Nuke's main window or
a parent panel instead of the exact DAG canvas widget means the filter receives `QEvent.Enter`
and `QEvent.Leave` but not `QEvent.KeyPress`.

Additionally, in Nuke 15 and earlier the DAG canvas was a `QGLWidget`; in Nuke 16+ it is a
plain `QWidget`. Code that finds the DAG by class type (`isinstance(w, QGLWidget)`) breaks on
Nuke 16. Code that finds it by `objectName()` works on both.

**Consequences:**
- Leader mode never activates despite Shift+E being pressed.
- No error is raised — the filter simply never fires.
- Debugging is difficult because `eventFilter` appears installed correctly per Python object identity.

**Prevention:**
- Find the DAG widget by `objectName()`, not by class type:
  ```python
  for w in QApplication.instance().allWidgets():
      if w.objectName() == "DAG" and w.isVisible():
          w.installEventFilter(leader_filter)
  ```
- After installing, verify by calling `w.objectName()` and confirming it returns `"DAG"`.
- Do not install on the parent `NodeGraph` panel; install on the innermost canvas widget.
- If multiple DAGs exist (Groups open in separate panels), install on all of them.

**Detection:**
Print from inside `eventFilter`. If nothing prints when keys are pressed in the DAG, the
filter is on the wrong widget. Check `QApplication.focusWidget().objectName()` while the DAG
has focus.

**Phase that must address this:** Leader key implementation phase (event filter installation).

---

### Pitfall 2: Event Filter Not Installed at Startup — DAG Widget Not Yet Created

**What goes wrong:**
The event filter installation runs during `menu.py` execution at Nuke startup. At that point,
Nuke's widget tree is not fully initialized — the DAG widget does not yet exist in
`QApplication.instance().allWidgets()`. The installation loop finds zero DAG widgets and
silently installs nothing. Leader mode never works.

**Why it happens:**
Nuke's UI widgets are created lazily after the Python init scripts run. `menu.py` is executed
very early in startup, before Nuke renders its main window. This is a confirmed timing issue:
the Pixelmania DAG event filter article explicitly notes "The DAG widgets aren't fully created
when the loading code gets run, hence the install of the event filter doesn't work."

**Consequences:**
- No event filter is installed. Leader mode never activates.
- No error or warning is shown.
- The bug may appear intermittent (sometimes the DAG loads before the install runs, sometimes not).

**Prevention:**
Defer the event filter installation using `QTimer.singleShot(0, install_fn)`. A timer with
0ms delay defers execution until the Qt event loop has completed one full cycle, by which
point Nuke's widget tree including the DAG is fully constructed:
```python
from PySide6.QtCore import QTimer
QTimer.singleShot(0, _install_dag_event_filter)
```
Place this call at the bottom of `menu.py`, not at the top-level import.

Alternatively, use `nuke.addOnScriptLoad` to (re-)install the filter each time a script
is opened, catching the case where the DAG widget is first created on first script open.

**Detection:**
Print the count of DAG widgets found during installation. If it prints 0, installation is
running too early. Compare with the same print deferred by `QTimer.singleShot(0, ...)`.

**Phase that must address this:** Leader key implementation phase (startup timing).

---

### Pitfall 3: Leader Mode Gets Stuck — No Cancellation Path for Mouse Events

**What goes wrong:**
The leader mode state machine responds to recognized keys (V/Z/F/C/W/A/S/D/Q/E) and cancels
on unrecognized keys. But mouse clicks in the DAG are `QEvent.MouseButtonPress` events, not
key events. If the event filter only listens for `QEvent.KeyPress`, any mouse click during
leader mode leaves the mode active. The user expects clicking to cancel leader mode but it
does not. The overlay remains visible indefinitely.

**Why it happens:**
An event filter that returns `False` for non-key events lets them propagate normally to Nuke
but does not cancel leader mode. The mode state variable stays `True` and the overlay widget
stays visible. The only escape becomes an unrecognized keypress — which users may not
discover.

**Consequences:**
- Leader mode becomes permanently active after a mouse click.
- The overlay HUD stays on screen, blocking the DAG visually.
- WASD keys continue moving nodes when the user intends to use them for other purposes.
- Escape key and Ctrl+Z may not be mapped as cancellation triggers unless explicitly handled.

**Prevention:**
In `eventFilter`, handle ALL event types that should cancel leader mode, not just
`QEvent.KeyPress`:
```python
CANCEL_EVENT_TYPES = {
    QEvent.Type.MouseButtonPress,
    QEvent.Type.MouseButtonDblClick,
    QEvent.Type.FocusOut,
}
if event.type() in CANCEL_EVENT_TYPES:
    _cancel_leader_mode()
    return False  # let the event propagate normally
```
Also handle `QEvent.KeyPress` for Escape explicitly as a cancellation trigger regardless of
whether it is otherwise mapped.

**Detection:**
Enter leader mode. Click in the DAG. Verify the overlay disappears and mode is cancelled.
Enter leader mode. Press Escape. Verify cancellation.

**Phase that must address this:** Leader key implementation phase (cancellation contract).

---

### Pitfall 4: Event Filter Breaks Nuke's Own Keyboard Handling — Text Entry Fields Stop Working

**What goes wrong:**
The event filter is installed on the DAG widget and returns `True` (consuming the event) for
keys that should be dispatched to leader mode commands. However, when the user has clicked on
a node name field, a Properties panel text input, or the expression editor in the DAG, those
widgets have keyboard focus. The filter — installed on the DAG canvas — should not receive
focus-directed events for those child text inputs. But if the filter is accidentally installed
on a parent widget that contains text inputs, it intercepts typing and breaks text entry.

Additionally, even with the filter correctly on the DAG canvas, `QApplication.focusWidget()`
must be checked before consuming any keypress. If focus has shifted away from the DAG (e.g.,
to a Properties panel), returning `True` for a keypress that was directed at a `QLineEdit`
elsewhere corrupts the user's text input.

**Why it happens:**
Qt delivers events to the focused widget. A widget-level filter on the DAG canvas only fires
for events delivered to the DAG canvas itself — so if focus is on a `QLineEdit`, the DAG
canvas filter never fires for those events. However, if an application-level filter is used
instead (installed on `QApplication`), it fires for ALL widgets everywhere, including text
inputs.

The subtle case is `FocusOut`: when the DAG loses focus (user clicks Properties panel), the
event filter must detect `QEvent.FocusOut` on the DAG and cancel leader mode, so that
subsequent keypresses in the Properties panel are never intercepted.

**Consequences:**
- If application-level filter is used: typing in any Nuke text field dispatches to leader mode.
- If `FocusOut` is not handled: leader mode remains active while the user types in Properties panel; keypresses in Properties are silently consumed by the filter.

**Prevention:**
- Install the filter at widget level on the DAG canvas only, never on `QApplication`.
  (Application-level filters process every event in the entire application and cause
  significant performance degradation per Qt documentation.)
- Handle `QEvent.FocusOut` on the DAG widget: cancel leader mode immediately when the
  DAG loses focus.
- Before consuming any keypress in `eventFilter`, assert `watched is dag_widget` — if an
  unrelated widget is somehow watched, do not consume.

**Detection:**
Enter leader mode. Click on a node's Properties panel. Type letters. Verify text appears in
the Properties field and leader mode is cancelled. Verify pressing `V` in a Properties text
field does not trigger layout.

**Phase that must address this:** Leader key implementation phase (scope of interception).

---

### Pitfall 5: WASD Conflicts with Existing Nuke Single-Key DAG Shortcuts

**What goes wrong:**
In leader mode, W/A/S/D are mapped to node movement. Outside leader mode they are standard
Nuke DAG shortcuts: W inserts a Write node, S opens Project Settings, D disables/enables a
node. The leader key system must NOT intercept W/A/S/D outside of leader mode. If the event
filter returns `True` for W/A/S/D at any time, those Nuke built-in shortcuts stop working.

Additionally, Q is mapped to "Show named script info" in Nuke's DAG, and C inserts a
ColorCorrect node, and F fits the view. All of these are mapped to leader mode keys. Inside
leader mode the plugin's meaning takes over; outside leader mode the built-in meaning must be
completely preserved.

**Why it happens:**
An event filter that returns `True` for a keypress unconditionally (regardless of leader mode
state) permanently disables that key's built-in Nuke function. Even returning `True` only to
re-dispatch the command via `nuke.addMenuCommand` still removes the keypress from Nuke's
normal event pipeline, potentially missing timing or context that Nuke's internal handling
depends on.

**Consequences:**
- W no longer inserts Write nodes (permanently broken, not mode-dependent).
- S no longer opens Project Settings.
- D no longer toggles node disabled state.
- F no longer fits the DAG view.
- Users discover broken shortcuts unrelated to node layout — high credibility cost.

**Prevention:**
The event filter must check the leader mode state variable before consuming any keypress.
When NOT in leader mode, the filter must return `False` for all keypresses (letting Nuke
handle them normally). Only when `leader_mode_active is True` should recognized keys be
consumed and dispatched to plugin commands.

```python
def eventFilter(self, watched, event):
    if event.type() != QEvent.Type.KeyPress:
        if leader_mode_active and event.type() in CANCEL_EVENT_TYPES:
            _cancel_leader_mode()
        return False
    if not leader_mode_active:
        return False  # never intercept outside leader mode
    key = event.key()
    if key in LEADER_KEY_MAP:
        _dispatch(LEADER_KEY_MAP[key])
        return True  # consume: prevent Nuke from also acting on this key
    else:
        _cancel_leader_mode()
        return False  # let Nuke handle unrecognized key normally
```

**Detection:**
Without entering leader mode, press W, S, D, F, C, Q. Verify each performs its standard Nuke
function. Then enter leader mode and press the same keys — verify plugin commands execute.

**Phase that must address this:** Leader key implementation phase (mode-gated interception).

---

### Pitfall 6: WASD — No Confirmed Built-in DAG Navigation Conflict, but W/S/D are Bound

**What goes wrong:**
The project spec says WASD is for moving selected nodes. Research confirms Nuke does NOT use
WASD for DAG panning/navigation (unlike game engines). However, W, S, and D each have
existing single-key DAG bindings (Insert Write, Project Settings, Disable/Enable respectively)
that will conflict with leader mode dispatch unless properly guarded by Pitfall 5 above.

A subtle secondary risk: if a future Nuke version adds WASD navigation, the event filter
consuming those keys in leader mode would break it. This risk is LOW confidence (no evidence
in current Nuke 11–16 documentation) but worth noting.

**Why it matters:**
The spec says WASD movement chains ("stays in leader mode between move steps"). This means
after pressing W to move a node up, leader mode remains active. The user may press W again
to move further. During this chain, every W press must be consumed in leader mode while NOT
breaking the built-in "Insert Write" when not in leader mode.

**Prevention:**
- Guard all WASD consumption strictly within leader mode state (see Pitfall 5).
- Map W/A/S/D to node position delta commands (e.g., shift selected nodes by
  `nuke.selectedNodes()` using `setXpos`/`setYpos`) not to any Nuke built-in API calls
  that could conflict.
- Confirm with actual Nuke testing that W/A/S/D move the correct direction given Nuke's
  coordinate system (positive Y is DOWN — so "move node up" means decreasing Ypos, i.e.,
  W should decrease Ypos, not increase it).

**Detection:**
In leader mode, press W. Verify selected nodes move up (lower Ypos). Press S. Verify nodes
move down (higher Ypos). Outside leader mode, press W. Verify Write node is inserted.

**Phase that must address this:** Leader key implementation phase (WASD movement commands).

---

### Pitfall 7: Overlay Widget Steals Keyboard Focus — Nuke Loses All Keyboard Input

**What goes wrong:**
The floating overlay widget is shown with `show()` using default window flags. Qt's default
behavior for a top-level `QWidget` is to accept keyboard focus when shown. When the overlay
appears, keyboard focus shifts from the DAG widget to the overlay. The event filter on the
DAG receives no more keypresses. The overlay cannot be dismissed with keyboard input (because
no key handler is on the overlay), and Nuke's keyboard shortcuts stop working entirely until
the user manually clicks back on the DAG.

**Why it happens:**
By default, `QWidget.show()` activates the window and transfers keyboard focus. This is the
correct behavior for dialogs but wrong for a HUD overlay that is display-only.

**Consequences:**
- The overlay appears but immediately breaks leader mode (DAG loses focus).
- The very keypress that triggered leader mode may be received, but subsequent keypresses
  go to the overlay (which does nothing with them).
- Nuke appears frozen to the user until they click the DAG.

**Prevention:**
Before `show()`, set two attributes on the overlay widget:
```python
overlay.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
overlay.setWindowFlags(
    Qt.WindowType.FramelessWindowHint |
    Qt.WindowType.WindowStaysOnTopHint |
    Qt.WindowType.Tool  # Tool windows do not steal focus from their owner
)
```
`WA_ShowWithoutActivating` prevents the widget from taking focus when shown. The `Tool`
window type additionally signals to the window manager that this window should not be
activated. On Linux, also set `Qt.WidgetAttribute.WA_X11DoNotAcceptFocus`.

Do NOT set `Qt.WidgetAttribute.WA_TransparentForMouseEvents` unless the overlay should be
click-through — for a keyboard-driven HUD this may be acceptable and would further ensure
no accidental focus transfer.

**Detection:**
Show the overlay. Immediately press a recognized leader mode key. If nothing happens
(because DAG lost focus), focus stealing occurred. `QApplication.focusWidget()` will return
the overlay widget, not the DAG.

**Phase that must address this:** Overlay widget implementation phase.

---

### Pitfall 8: Overlay Widget Not Visible — Parented Incorrectly or Behind DAG

**What goes wrong:**
The overlay widget is created with `parent=dag_widget`. Qt renders a child widget clipped to
its parent's geometry and under the parent's normal painting. Since the DAG canvas paints its
own content (the node graph), the overlay child widget may be obscured. In Nuke 15 and earlier
where the DAG used `QGLWidget`, child widgets painted over an OpenGL surface were frequently
invisible because the OpenGL context was composited separately from the Qt widget layer.
Even in Nuke 16 with a plain QWidget DAG, z-ordering of child widgets is not guaranteed to
render on top.

**Why it happens:**
Child widgets are rendered in the parent's local coordinate system and may be clipped.
`QGLWidget` (pre-Nuke 16) was particularly hostile to overlaid children because it used a
separate GL context composited independently of the Qt paint engine.

**Consequences:**
- The overlay widget exists in Python but is invisible to the user.
- No error or warning is shown.
- The leader mode appears to work (commands dispatch) but the HUD does nothing visually.

**Prevention:**
Make the overlay a TOP-LEVEL window (no parent, or parent set to Nuke's main window) and
position it manually over the DAG:
```python
overlay = LeaderOverlay(parent=None)
overlay.setWindowFlags(
    Qt.WindowType.FramelessWindowHint |
    Qt.WindowType.WindowStaysOnTopHint |
    Qt.WindowType.Tool
)
overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
overlay.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
# Position over DAG:
dag_global_pos = dag_widget.mapToGlobal(dag_widget.rect().topLeft())
overlay.setGeometry(dag_global_pos.x(), dag_global_pos.y(),
                    dag_widget.width(), dag_widget.height())
overlay.show()
```

Position calculation must use `mapToGlobal()` on the DAG widget to convert its local
top-left corner to screen coordinates, then set the overlay's global geometry accordingly.

**Detection:**
Show the overlay. Print `overlay.isVisible()` — should be `True`. Take a screenshot and
verify the overlay content is rendered on top of the DAG.

**Phase that must address this:** Overlay widget implementation phase.

---

### Pitfall 9: Overlay Position Wrong on Multi-Monitor or When DAG Panel is Moved/Resized

**What goes wrong:**
The overlay geometry is calculated once at `show()` time using `dag_widget.mapToGlobal()`.
If Nuke's window is moved, the DAG panel is undocked/redocked, or the user is on a
multi-monitor setup where the DAG is on a non-primary display, the overlay appears at the
wrong screen position (on the primary monitor, at wrong coordinates, or off-screen entirely).

**Why it happens:**
`mapToGlobal()` converts widget-local coordinates to global screen coordinates at the moment
of the call. It does not stay synchronized as the window moves. A top-level overlay with
`WindowStaysOnTopHint` but no position tracking will visually separate from the DAG if the
window moves during a leader mode session.

**Consequences:**
- On multi-monitor setups, the overlay appears on the wrong screen.
- If the user moves Nuke's window during leader mode, the overlay detaches and floats at
  the old position.
- On HiDPI/Retina displays, if device pixel ratio is not accounted for, the overlay may be
  half-sized or double-sized.

**Prevention:**
- Keep leader mode sessions short by design (no timeout, but any non-movement key exits).
  Movement keys (WASD) chain, but the mode duration is typically under 2 seconds of use.
- At the start of each leader mode activation, recalculate the overlay geometry fresh from
  `dag_widget.mapToGlobal()`. Do not cache position across activations.
- The overlay is shown for the duration of one leader mode session only. Recalculating once
  per activation is sufficient and cheap.
- For HiDPI: use `dag_widget.devicePixelRatioF()` if overlay content needs to match physical
  pixels. For a simple text/icon HUD, logical pixels are sufficient.

**Detection:**
On a two-monitor setup, move Nuke to the secondary monitor. Enter leader mode. Verify overlay
appears on the secondary monitor over the DAG, not on the primary.

**Phase that must address this:** Overlay widget implementation phase.

---

### Pitfall 10: WindowStaysOnTopHint and FramelessWindowHint Order — Overlay Has Unexpected Border

**What goes wrong:**
Setting `WindowStaysOnTopHint` and `FramelessWindowHint` in the wrong order or combination
produces a window with a border (stays on top but framed) or a borderless window that does
not stay on top. The flags interact platform-specifically.

**Why it happens:**
On Windows, `WindowStaysOnTopHint` only takes effect for frameless or full-screen windows in
some configurations. On Linux/X11, the window manager may ignore certain hint combinations.
The safe combination documented by Qt is to set ALL required flags at once in a single
`setWindowFlags()` call, not in separate calls.

**Consequences:**
- Overlay shows with a title bar, looking like an unwanted dialog.
- Overlay is hidden behind the Nuke window despite `WindowStaysOnTopHint`.

**Prevention:**
Set all flags in one call:
```python
overlay.setWindowFlags(
    Qt.WindowType.FramelessWindowHint |
    Qt.WindowType.WindowStaysOnTopHint |
    Qt.WindowType.Tool
)
overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
```
Call `setWindowFlags` before `show()`, never after. Calling `setWindowFlags` on an already-
visible widget hides it (Qt behavior) — call `show()` again after any flag change.

**Detection:**
Show the overlay. Verify no title bar is present. Verify it appears above the Nuke DAG.

**Phase that must address this:** Overlay widget implementation phase.

---

### Pitfall 11: Shift+E Replacing the Existing Menu Command — Old Shortcut Persists

**What goes wrong:**
The current `menu.py` registers `'Layout Upstream'` with shortcut `'shift+e'` and
`shortcutContext=2`. The v1.4 plan replaces this with leader mode entry. Simply registering
a new command with `shift+e` does NOT remove the old binding — Nuke may fire both, or fire
whichever was registered last. The old "Layout Upstream" may run immediately when Shift+E is
pressed, before leader mode can activate.

**Why it happens:**
`nuke.addMenuCommand` appends a new shortcut association. If the old `'Layout Upstream'`
command retains its `shift+e` binding, Nuke processes both bindings. The behavior depends
on registration order and whether Nuke deduplicates shortcut bindings on the same context.

**Consequences:**
- Pressing Shift+E runs "Layout Upstream" immediately AND tries to activate leader mode.
- Layout runs before any leader key is pressed, which is not the intended UX.
- The user sees layout happen with no leader mode prompt.

**Prevention:**
In `menu.py`, change the `'Layout Upstream'` command to have no shortcut (remove the
`'shift+e'` argument entirely), and register the leader mode entry point under `'shift+e'`
separately:
```python
layout_menu.addCommand('Layout Upstream',
    "import node_layout; node_layout.layout_upstream()")
# No shortcut — leader mode entry replaces it

layout_menu.addCommand('Enter Leader Mode',
    "import node_layout_leader; node_layout_leader.enter_leader_mode()",
    'shift+e',
    shortcutContext=2)
```
Verify by checking the Nuke Script Editor for "shortcut conflict" warnings on startup.

**Detection:**
Press Shift+E. Verify layout does NOT run. Verify leader mode is activated instead (overlay
appears or mode state becomes True).

**Phase that must address this:** Leader key implementation phase (menu registration).

---

## Moderate Pitfalls

Mistakes that cause degraded UX or subtle behavioral bugs, but not complete failure.

---

### Pitfall 12: Leader Mode State Not Reset on Script Open or Nuke Restart

**What goes wrong:**
The leader mode active state is a Python module-level variable. If Nuke crashes or a script
is force-closed while leader mode is active, on next launch the module variable is reset
(Python re-imports), so this is not a persistent problem. However, if Nuke's `nuke.scriptOpen`
callback re-imports modules, the event filter may be re-registered on a new DAG widget while
the old filter reference is orphaned. Result: multiple event filters installed, each firing
for the same DAG, executing commands twice per keypress.

**Why it happens:**
`QTimer.singleShot(0, install_fn)` is called once at startup. When a new script is loaded,
the DAG widget itself may be replaced (new Group DAGs opened), but the old install call is
not re-run. Additionally, if `install_fn` is called again (via `addOnScriptLoad`) without
first removing the old filter, duplicate filters accumulate.

**Prevention:**
Before installing a new event filter, always remove any previously installed filter:
```python
def _install_dag_event_filter():
    dag = _find_dag_widget()
    if dag is None:
        return
    dag.removeEventFilter(_leader_filter_instance)  # no-op if not installed
    dag.installEventFilter(_leader_filter_instance)
```
Use a module-level singleton for the filter object. Never create a new filter instance on
each install — always reuse or remove first.

**Detection:**
Register an install via `addOnScriptLoad`. Open a script. Open another script. Press a leader
mode key. Verify the command executes exactly once, not twice.

**Phase that must address this:** Leader key implementation phase (filter lifecycle).

---

### Pitfall 13: Overlay `paintEvent` Triggered on Every Keypress in a Busy DAG

**What goes wrong:**
The overlay widget repaints on every leader mode keypress because WASD chaining causes
`update()` or `repaint()` calls. In a large DAG (hundreds of nodes), Nuke's own rendering
is already heavy. Each `QWidget.repaint()` on the overlay — even a small frameless widget —
triggers a compositor roundtrip. If the overlay's `paintEvent` is expensive (uses gradient
fills, drop shadows, or many `QPainter` operations), combined with Nuke's DAG updates on
node movement, the interaction may stutter.

**Why it happens:**
`QWidget.update()` schedules an asynchronous repaint for the next event loop cycle, which is
efficient. `QWidget.repaint()` forces a synchronous repaint immediately, blocking the event
loop. In a keypress handler, calling `repaint()` holds the event loop until painting completes
— during which Nuke cannot process other events including node position updates.

**Consequences:**
- Perceptible lag between WASD key press and node movement in large DAGs.
- Stutter when chaining multiple WASD presses quickly.
- Risk of event queue backlog if keypresses arrive faster than painting + node movement can complete.

**Prevention:**
- Use `overlay.update()`, not `overlay.repaint()`, throughout the leader mode code.
- Keep `paintEvent` minimal: a simple semi-transparent rectangle with text rendered via
  `QPainter.drawText()` is fast. Avoid `QGraphicsDropShadowEffect` and complex gradients.
- The overlay content does not change during WASD chaining — do not call `update()` on node
  movement keypresses; only call it when entering/exiting leader mode or when displayed
  key labels change.

**Detection:**
In a DAG with 300+ nodes, enter leader mode and rapidly press WASD 20 times. Measure frame
time. If node movement lags behind keypresses by more than one cycle, painting is the bottleneck.

**Phase that must address this:** Overlay widget implementation phase.

---

### Pitfall 14: Hint Popup Delay Preference — Zero Delay Still Shows Overlay After Command Dispatches

**What goes wrong:**
The spec includes a "hint popup delay (ms)" pref with default 0. The intent is: show the
overlay immediately (0ms delay) when leader mode is entered. But if delay=0 and a recognized
key is pressed immediately (before any event loop cycle), the overlay is shown and immediately
hidden in the same event loop cycle because the command dispatches synchronously before the
overlay paints. The user never sees the overlay.

**Why it happens:**
At delay=0, `QTimer.singleShot(0, overlay.show)` fires on the next event loop cycle.
If the user's next keypress arrives in the same cycle (e.g., held-key repeat), the command
dispatches, leader mode exits (or stays for WASD), and the overlay hides — all before the
deferred `show()` has run.

The simpler case: if `overlay.show()` is called synchronously in the leader mode entry
function (not deferred), and the command also dispatches synchronously, the overlay may be
shown and hidden in the same Python call stack before Qt gets to paint it.

**Prevention:**
- For delay=0, call `overlay.show()` synchronously (not via timer) at the START of leader
  mode entry, before returning from the entry function. Qt will paint on the next event loop
  cycle while waiting for the user's next keypress.
- Only use `QTimer.singleShot(delay_ms, overlay.show)` for delay > 0.
- For WASD chaining, keep the overlay visible throughout the chain. Only hide on mode exit.

**Detection:**
Set hint delay to 0. Enter leader mode. Pause for 500ms without pressing any key. Verify
overlay appears. Then press a key and verify overlay disappears on mode exit.

**Phase that must address this:** Overlay widget implementation phase.

---

### Pitfall 15: `QDesktopWidget` Removed in PySide6 — Overlay Screen Geometry Lookup Breaks

**What goes wrong:**
Code that uses `QDesktopWidget` to find the geometry of the screen containing the DAG widget
(for multi-monitor positioning) fails on PySide6 / Nuke 16+. `QDesktopWidget` was removed
in Qt6. Code that imports it raises `ImportError` on Nuke 16.

**Why it happens:**
`QDesktopWidget` was deprecated in Qt 5.14 and removed in Qt 6. It was commonly used to get
screen geometry for positioning floating windows. PySide6 equivalent is
`QGuiApplication.instance().primaryScreen()` or `QWidget.screen()`.

**Prevention:**
Use the PySide6-compatible API for screen geometry:
```python
screen = overlay.screen()  # returns QScreen for the screen the widget is on
screen_rect = screen.availableGeometry()
```
Or before the widget exists:
```python
from PySide6.QtGui import QGuiApplication
screen = QGuiApplication.instance().primaryScreen()
```
Since this codebase already uses PySide6 throughout, do not use `QDesktopWidget` anywhere
in the leader key / overlay code.

**Detection:**
Run on Nuke 16. Import the leader module. If no `ImportError` or `AttributeError` is raised,
the PySide6 API is being used correctly.

**Phase that must address this:** Overlay widget implementation phase.

---

## Minor Pitfalls

---

### Pitfall 16: Enum Access Pattern — PySide6 Requires Class-Level Enum Access

**What goes wrong:**
PySide6 removed instance-level enum access. Code written in PySide2 style — e.g.,
`event.type() == QEvent.KeyPress` — raises `AttributeError` on PySide6. The correct form
is `event.type() == QEvent.Type.KeyPress`.

This applies throughout the event filter and overlay code: `Qt.FramelessWindowHint` must
become `Qt.WindowType.FramelessWindowHint`; `Qt.WA_ShowWithoutActivating` must become
`Qt.WidgetAttribute.WA_ShowWithoutActivating`.

**Prevention:**
Always use fully-qualified enum paths in PySide6:
```python
# Wrong (PySide2 style):
QEvent.KeyPress
Qt.FramelessWindowHint
Qt.WA_TranslucentBackground
# Correct (PySide6 style):
QEvent.Type.KeyPress
Qt.WindowType.FramelessWindowHint
Qt.WidgetAttribute.WA_TranslucentBackground
```

**Detection:**
Run any code path that uses Qt enums. Any `AttributeError` on a Qt enum constant indicates
the PySide2-style access is being used.

**Phase that must address this:** All phases touching PySide6 code.

---

### Pitfall 17: Group DAG Event Filters — Filter Not Installed on Group-Interior DAGs

**What goes wrong:**
When the user opens a Group node (double-clicks into it), Nuke creates a new DAG widget with
`objectName() == "DAG.GroupName"` (Nuke 16+). The event filter installed at startup on the
root `"DAG"` widget is not on this new widget. Leader mode does not work inside Group DAGs.

**Why it happens:**
Each Group interior has its own DAG canvas widget. The startup-time install only targets
the root DAG. Group DAG widgets are created dynamically on demand.

**Prevention:**
Either:
1. When entering leader mode, find ALL visible DAG widgets (using `"DAG" in objectName()`)
   and install the filter on all of them at that moment.
2. Use `nuke.addOnScriptLoad` and a periodic widget-scan to re-install filters on newly
   created DAG widgets.

Option 1 is simpler for the v1.4 scope. Option 2 is more thorough but adds complexity.
Given the existing `layout_upstream` function already operates on the current context
(which handles Groups), consistency requires leader mode to work in Group DAGs too.

**Detection:**
Double-click into a Group node. Enter leader mode (Shift+E). Verify the overlay appears and
keypresses are intercepted.

**Phase that must address this:** Leader key implementation phase (filter installation scope).

---

### Pitfall 18: Leader Mode Interaction with Nuke's Undo — Multiple Undo Steps from WASD Chaining

**What goes wrong:**
Each WASD movement in leader mode calls `setXpos`/`setYpos` on selected nodes. If each
movement is NOT wrapped in a single undo group, the user gets one undo entry per node per
keypress. A chain of 5 WASD presses on a 10-node selection creates 50 undo entries. The
user must press Ctrl+Z 50 times to undo the movement session.

**Why it happens:**
`setXpos`/`setYpos` creates individual undo entries in Nuke's undo stack. Without an explicit
`nuke.Undo.begin()` / `nuke.Undo.end()` wrapper, each positional change is a separate entry.

**Prevention:**
Two options:
1. Open a single undo group when leader mode is activated and close it when leader mode
   exits. All node movements during the leader session become one undoable step.
2. Open a new undo group per keypress and close it before returning from the keypress handler.
   Each keypress is its own undo step, but that is still cleaner than per-node entries.

Option 1 is recommended for UX: the user expects one Ctrl+Z to undo "the leader key session."
Note the existing codebase uses `try/except/else` for undo groups (not `finally`) per the
project's established pattern — follow the same idiom here.

**Detection:**
Enter leader mode. Press W three times to move a node. Exit leader mode. Press Ctrl+Z once.
Verify all three movements are undone in a single step.

**Phase that must address this:** Leader key implementation phase (undo semantics).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Event filter installation | Filter on wrong widget — no events received (Pitfall 1) | Find widget by `objectName() == "DAG"`; verify by printing from inside `eventFilter` |
| Event filter installation | DAG not created yet at startup (Pitfall 2) | Defer with `QTimer.singleShot(0, install_fn)` in `menu.py` |
| Event filter installation | Duplicate filters after script reopen (Pitfall 12) | Always `removeEventFilter` before `installEventFilter`; use singleton filter object |
| Event filter installation | Group DAGs not covered (Pitfall 17) | At leader mode entry, install on all visible `"DAG.*"` widgets |
| Leader mode dispatch | Stuck mode after mouse click (Pitfall 3) | Handle `MouseButtonPress` and `FocusOut` as cancellation triggers |
| Leader mode dispatch | Keypresses intercepted in Properties panel (Pitfall 4) | Widget-level filter only; cancel mode on `FocusOut` |
| Leader mode dispatch | WASD/W/S/D built-in shortcuts broken (Pitfall 5) | Gate ALL consumption behind `leader_mode_active` state check |
| Leader mode dispatch | WASD direction vs Nuke Y-axis (Pitfall 6) | W decreases Ypos; S increases Ypos; verify direction in tests |
| Leader mode dispatch | Shift+E fires both Layout Upstream and leader mode (Pitfall 11) | Remove shortcut from Layout Upstream command; re-register under leader entry |
| Leader mode dispatch | WASD chaining creates too many undo entries (Pitfall 18) | Wrap full leader session in single undo group |
| Overlay widget | Steals keyboard focus (Pitfall 7) | `WA_ShowWithoutActivating` + `Qt.WindowType.Tool` flags |
| Overlay widget | Invisible due to incorrect parenting (Pitfall 8) | Top-level window with `mapToGlobal()` positioning, not child of DAG canvas |
| Overlay widget | Wrong position on multi-monitor or after window move (Pitfall 9) | Recalculate geometry fresh at each leader mode activation |
| Overlay widget | Border present or not staying on top (Pitfall 10) | Set all window flags in single `setWindowFlags()` call before `show()` |
| Overlay widget | Slow repaint in large DAGs (Pitfall 13) | Use `update()` not `repaint()`; keep `paintEvent` minimal; skip updates during WASD moves |
| Overlay widget | Zero-delay hint never paints before command dispatches (Pitfall 14) | For delay=0, call `overlay.show()` synchronously before returning from entry function |
| Overlay widget | `QDesktopWidget` import error on Nuke 16 (Pitfall 15) | Use `QGuiApplication.primaryScreen()` or `QWidget.screen()` |
| PySide6 code | Enum `AttributeError` (Pitfall 16) | Use `QEvent.Type.KeyPress`, `Qt.WindowType.X`, `Qt.WidgetAttribute.X` throughout |

---

## Sources

- Erwan Leroy — Nuke Node Graph utilities (DAG widget discovery, `objectName()` pattern):
  https://erwanleroy.com/nuke-node-graph-utilities-using-qt-pyside2/
- Erwan Leroy — Updating scripts for Nuke 16/PySide6 (DAG widget architecture change, enum access pattern, `QDesktopWidget` removal):
  https://erwanleroy.com/updating-your-python-scripts-for-nuke-16-and-pyside6/
- Pixelmania — Fixing Nuke middle-click behavior (event filter timing/deferred install, `QGLWidget` to QWidget):
  https://pixelmania.se/fixing-an-annoying-nuke-feature/
- Qt Documentation — The Event System (filter return values, QApplication vs widget-level filters, performance):
  https://doc.qt.io/qt-6/eventsandfilters.html
- Qt Documentation — QWidget (WA_ShowWithoutActivating, WA_TranslucentBackground, setWindowFlags):
  https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html
- Qt Forum — Prevent Always On Top Window From Stealing Keyboard Focus:
  https://forum.qt.io/topic/83098/prevent-always-on-top-window-from-stealing-keyboard-focus
- Foundry Nuke Keyboard Shortcuts — DAG single-key bindings (W=Write, S=Settings, D=Disable, F=Fit, C=ColorCorrect, Q=ScriptInfo):
  https://learn.foundry.com/nuke/content/misc/hotkeys_studio.html
- Foundry Nuke — addMenuCommand shortcutContext parameter (0=Window, 1=Application, 2=DAG):
  https://learn.foundry.com/nuke/developers/140/pythonreference/_autosummary/nuke.MenuBar.html
- Nuke Python mailing list — QTimer.singleShot(0) pattern for deferred widget access:
  https://www.mail-archive.com/nuke-python@support.thefoundry.co.uk/msg02230.html
- Qt Forum — WA_TransparentForMouseEvents and transparent overlays:
  https://forum.qt.io/topic/156324/how-to-create-a-partially-transparent-overlay-widget
- Confidence levels: Pitfalls 1–11, 13, 15–16 are MEDIUM–HIGH (Qt official docs + Nuke community sources). Pitfalls 12, 14, 17, 18 are MEDIUM (Qt docs + reasoning from established Nuke undo/event patterns in this codebase).
