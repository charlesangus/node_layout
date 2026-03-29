# Technology Stack

**Project:** node_layout v1.4 — Leader Key Modal System
**Researched:** 2026-03-28
**Scope:** New Qt/Nuke API patterns needed for the leader key modal input system and DAG overlay widget. Existing validated stack (Python, PySide6, JSON prefs, Nuke API for node positions/knobs) is NOT repeated here.

---

## Summary of Additions

No new pip dependencies are needed. All required capabilities exist in PySide6 (already a project dependency) and the Nuke Python API. The work is entirely API-usage patterns.

---

## (1) Finding the Active Nuke DAG QWidget

### Recommended approach: objectName scan

```python
from PySide6.QtWidgets import QApplication

def get_visible_dag_widgets():
    """Return all visible DAG QWidgets by objectName convention."""
    result = []
    for widget in QApplication.instance().allWidgets():
        if "DAG" in widget.objectName() and widget.isVisible():
            result.append(widget)
    return result

def get_active_dag_widget():
    """Return the DAG widget that currently has keyboard focus, or the first visible one."""
    visible = get_visible_dag_widgets()
    for widget in visible:
        if widget.hasFocus():
            return widget
    return visible[0] if visible else None
```

### Object name conventions

| Nuke Version | Root DAG objectName | Group DAG objectName |
|---|---|---|
| Nuke 11–15 | `"DAG"` | Unnamed (QGLWidget child) |
| Nuke 16+ | `"DAG"` | `"DAG.Group1"`, `"DAG.Group2"`, etc. |

**Confidence: MEDIUM-HIGH.** The `objectName() == "DAG"` pattern is confirmed by multiple community sources and Erwan Leroy's widely-cited 2024 article on Nuke Qt utilities. The Group DAG naming convention is documented in Foundry's Nuke 16 release context. The exact string has not changed for the root DAG since at least Nuke 11.

### Nuke version context for this project

The project targets Nuke 11+ and the codebase already uses PySide6, meaning the effective runtime is Nuke 16+. On Nuke 16+, the DAG is a standard `QWidget` (not `QGLWidget`) because Qt6 deprecated `QOpenGLWidget` for this use. This is an advantage: no OpenGL widget introspection needed.

**Do NOT** use the older pattern of finding widgets by `windowTitle() == "Node Graph"` and then calling `findChild(QtOpenGL.QGLWidget)` — that approach worked on Nuke 15 and earlier, breaks on Nuke 16+, and the `QtOpenGL` module has changed.

### Timing: DAG widget availability

The DAG widget may not exist yet when `menu.py` runs at startup. Do not call `get_active_dag_widget()` at module import time. Call it at the moment the leader key is pressed (i.e., inside the Shift+E handler function). By the time any user presses a key, the DAG is fully initialized.

**Confidence: HIGH** (consistent across all sources; standard deferred-init pattern).

---

## (2) Intercepting Key Events in the DAG: installEventFilter on the DAG Widget

### Recommended approach: per-widget event filter, installed at leader-key entry

The leader key system needs to intercept subsequent key presses after Shift+E is pressed, routing them to plugin commands before Nuke processes them. The right tool is `QObject.installEventFilter()` installed on the active DAG widget.

```python
from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QApplication

class LeaderKeyFilter(QObject):
    """Event filter installed on the DAG widget during leader mode.

    Intercepts QEvent.KeyPress events before Nuke processes them.
    Returns True to consume the event (preventing Nuke from acting on it),
    or False to pass it through.
    Removes itself from the DAG widget when leader mode exits.
    """

    def __init__(self, dag_widget, dispatch_fn, cancel_fn):
        super().__init__(parent=dag_widget)
        self._dag_widget = dag_widget
        self._dispatch_fn = dispatch_fn
        self._cancel_fn = cancel_fn
        dag_widget.installEventFilter(self)

    def eventFilter(self, watched_object, event):
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            consumed = self._dispatch_fn(key, modifiers)
            if consumed:
                return True   # stop Nuke from processing this key
            else:
                self._cancel_fn()
                return False  # pass through unrecognized keys
        if event.type() == QEvent.Type.MouseButtonPress:
            self._cancel_fn()
            return False      # let mouse clicks through, but cancel leader mode
        return False          # pass all other events through

    def remove(self):
        """Uninstall the filter. Call when exiting leader mode."""
        self._dag_widget.removeEventFilter(self)
```

### Why per-widget, not QApplication-level

Installing on `QApplication.instance()` filters every event in the entire application. Qt's own documentation warns this "slows down event delivery of every single event." For a modal input mode that is active only briefly, installing on the DAG widget is correct: it filters only the target surface, has zero overhead when not in leader mode, and is automatically scoped to that specific DAG panel.

**Confidence: HIGH** (Qt documentation; consistent with all Nuke community examples found; Pixelmania's MouseEventGrabber uses this exact per-widget pattern).

### Event consumption: returning True stops Nuke

Returning `True` from `eventFilter()` stops the event from reaching the target widget (and any later filters). Returning `False` passes it through. This is the standard Qt mechanism for event interception. For the leader key system: return `True` for recognized keys (consume them, execute command instead), return `False` for mouse clicks (let them through but exit leader mode), return `False` for unrecognized keys (let Nuke handle them, and exit leader mode).

**Confidence: HIGH** (official Qt documentation; confirmed across multiple independent sources).

### Install/remove lifecycle

Install the filter at the moment Shift+E is pressed (beginning of leader mode). Remove it when leader mode exits (recognized command executed, unrecognized key pressed, or mouse click). Never leave a dangling filter: a filter pointing to a dead Python object causes segfaults in Qt.

```python
# Entry point (called by Shift+E menu command)
def enter_leader_mode():
    dag = get_active_dag_widget()
    if dag is None:
        return
    # Create filter; it installs itself in __init__
    _state.active_filter = LeaderKeyFilter(dag, _dispatch, _exit_leader_mode)
    _state.in_leader_mode = True
    _show_overlay(dag)

# Exit point
def _exit_leader_mode():
    if _state.active_filter is not None:
        _state.active_filter.remove()
        _state.active_filter = None
    _state.in_leader_mode = False
    _hide_overlay()
```

### Nuke-specific constraint: shortcutContext and the event filter

When Nuke's menu system registers a shortcut with `shortcutContext=2` (DAG), Nuke processes it via its internal Qt shortcut system. An event filter on the DAG widget intercepts `QEvent.KeyPress` events *before* Nuke's shortcut dispatcher sees them. This means that for single-character keys in leader mode (V, Z, F, C, W, A, S, D, Q, E), the filter will consume them before Nuke's own shortcut bindings fire. This is intentional and correct. When leader mode is not active (filter not installed), all existing shortcuts continue to work normally.

**Confidence: MEDIUM** (logical inference from Qt event processing order; confirmed in principle by the Pixelmania example where `return True` successfully prevents Nuke's default middle-click zoom behavior).

---

## (3) DAG Overlay Widget: Translucent Floating Child Widget

### Recommended approach: child QWidget with custom paintEvent

The overlay should be a `QWidget` created as a **child of the DAG widget**, not a separate top-level window. This gives it automatic Z-ordering above the DAG, automatic visibility with the DAG, and no separate window-manager frame.

```python
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QFont

class LeaderModeOverlay(QWidget):
    """Translucent keyboard hint overlay displayed over the Nuke DAG during leader mode.

    Created as a child of the DAG widget so it floats over it automatically.
    Positioned in a corner via geometry; resizes are handled by the caller.
    Does not consume mouse events (setAttribute WA_TransparentForMouseEvents).
    """

    def __init__(self, dag_widget):
        super().__init__(parent=dag_widget)
        # Required for transparency on all platforms
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Do not intercept mouse events — let them fall through to the DAG
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._position_in_dag(dag_widget)
        self.show()

    def _position_in_dag(self, dag_widget):
        """Position the overlay in the bottom-left corner of the DAG."""
        dag_size = dag_widget.size()
        overlay_width = 320
        overlay_height = 200
        margin = 16
        self.setGeometry(
            margin,
            dag_size.height() - overlay_height - margin,
            overlay_width,
            overlay_height,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Semi-transparent dark background panel
        painter.setBrush(QColor(20, 20, 20, 200))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)
        # Key labels (draw text for each key binding)
        painter.setPen(QColor(220, 220, 220, 255))
        font = QFont("Monospace", 11)
        painter.setFont(font)
        # ... draw key label rows here ...
        painter.end()

    def remove(self):
        self.hide()
        self.setParent(None)
        self.deleteLater()
```

### Why child widget over top-level window

| Approach | Pros | Cons |
|---|---|---|
| Child widget of DAG | Automatic DAG-relative Z-order; no separate OS window; no focus issues | Must reposition on DAG resize (add to DAG's resizeEvent or poll) |
| Top-level frameless window (Qt.Tool) | Easy absolute positioning | Requires `mapToGlobal()` math; may appear under DAG on some platforms; separate OS window means possible focus steal |
| QPainter on DAG directly | Zero widget overhead | Requires subclassing or monkeypatching the DAG widget — not possible without access to Nuke's C++ DAG class |

Child widget is the correct choice. The overlay gist pattern (PyQt, 2014) uses exactly this: `overlay(parent=self.editor)`, `self.overlay.resize(event.size())`.

**Confidence: HIGH** (child widget transparency is a standard Qt pattern, documented in Qt6 official docs; `WA_TranslucentBackground` on a child widget requires no `FramelessWindowHint` because child widgets don't have OS window decorations).

### WA_TransparentForMouseEvents is critical

Without `WA_TransparentForMouseEvents`, the overlay widget will absorb mouse clicks intended for the DAG (node selection, panning, etc.). Always set this attribute on the overlay so all mouse events pass through to the DAG beneath.

**Confidence: HIGH** (Qt6 official documentation; this attribute exists precisely for HUD/overlay use cases).

### Overlay positioning and DAG resize

If the user resizes the Nuke panel while in leader mode, the overlay position will be stale. Two options:

1. **Poll on show**: Position once when leader mode is entered. Leader mode is very short (seconds at most); a one-time position is acceptable.
2. **Install a second event filter on the DAG**: Watch for `QEvent.Resize` and call `_position_in_dag()` again. Adds code complexity but keeps the overlay in the correct corner.

Recommendation: start with option 1 (simpler). If UAT reveals positioning issues, add option 2.

### Hint popup delay preference

The new `hint_popup_delay_ms` preference (default 0) controls how long after entering leader mode before the overlay appears. Implement with `QTimer.singleShot(delay_ms, overlay.show)`. At delay=0, the overlay appears synchronously (next Qt event loop cycle). This is standard QTimer usage and requires no new dependencies.

```python
from PySide6.QtCore import QTimer

# In enter_leader_mode():
delay_ms = node_layout_prefs.prefs_singleton.get("hint_popup_delay_ms")
overlay = LeaderModeOverlay(dag_widget)
overlay.hide()   # start hidden
QTimer.singleShot(delay_ms, overlay.show)
```

**Confidence: HIGH** (QTimer.singleShot is a core PySide6 API; behavior at delay=0 is documented — the callback fires after the current call stack unwinds).

---

## (4) PySide6 Version Considerations

### Enum access in PySide6 (vs PySide2)

PySide6 uses fully qualified enum access. PySide2 allowed bare access from instances; PySide6 does not.

| What | PySide2 | PySide6 |
|---|---|---|
| Qt flags | `Qt.FramelessWindowHint` | `Qt.WindowType.FramelessWindowHint` |
| Widget attributes | `Qt.WA_TranslucentBackground` | `Qt.WidgetAttribute.WA_TranslucentBackground` |
| Event types | `QEvent.KeyPress` | `QEvent.Type.KeyPress` |
| Painter hints | `QPainter.Antialiasing` | `QPainter.RenderHint.Antialiasing` |
| Mouse buttons | `Qt.LeftButton` | `Qt.MouseButton.LeftButton` |

The codebase already uses PySide6 (confirmed by `node_layout_prefs_dialog.py` imports). Use the PySide6 fully-qualified enum form throughout the new leader key code.

**Confidence: HIGH** (Foundry official migration guide; confirmed by Erwan Leroy's Nuke 16 PySide6 article).

### Nuke version and PySide version mapping

| Nuke Version | PySide Version | DAG widget type |
|---|---|---|
| 11–12 | PySide2 | QGLWidget |
| 13–15 | PySide2 | QGLWidget |
| 16+ | PySide6 | QWidget (non-GL) |

Since this project already imports `from PySide6.QtWidgets import ...` (confirmed in `node_layout_prefs_dialog.py`), it is already Nuke 16+. No version guard needed. Do not add a `NUKE_VERSION_MAJOR` check — it would be dead code.

**Confidence: HIGH** (codebase inspection; Foundry Nuke 16 release notes).

### QKeyEvent: key() and modifiers()

```python
from PySide6.QtCore import QEvent
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt

# Inside eventFilter:
if event.type() == QEvent.Type.KeyPress:
    key = event.key()           # int, e.g. Qt.Key.Key_V
    modifiers = event.modifiers()  # Qt.KeyboardModifier flags

    # Check for specific keys:
    if key == Qt.Key.Key_V and modifiers == Qt.KeyboardModifier.NoModifier:
        ...
    elif key == Qt.Key.Key_W and modifiers == Qt.KeyboardModifier.NoModifier:
        ...
```

Note: `Qt.Key.Key_V` has value 86 (ASCII 'V'). The `event.key()` for lowercase 'v' in the DAG is still `Qt.Key.Key_V` — key codes are uppercase-normalized. Modifiers distinguish Shift+V from V. For WASD movement, check `modifiers == Qt.KeyboardModifier.NoModifier` to avoid accidentally firing on Ctrl+W etc.

**Confidence: HIGH** (Qt6 official documentation; QKeyEvent is unchanged between PySide2 and PySide6 in semantics).

---

## (5) Nuke-Specific Constraints and Gotchas

### Constraint: Nuke processes Shift+E via addMenuCommand before the event filter sees it

When Shift+E is registered as a `shortcutContext=2` menu command, Nuke intercepts it as a Qt shortcut action on the DAG. The handler function (`enter_leader_mode`) fires. At the point it fires, the event filter has NOT been installed yet. Install the filter inside `enter_leader_mode` before returning. Subsequent key presses (the leader key dispatch) will then be intercepted by the filter.

This is the correct sequencing: the Shift+E key press triggers `enter_leader_mode`, which installs the filter, which then handles the next key.

### Constraint: WASD and E conflict with existing Nuke shortcuts

Nuke uses W, A, S, D, E (and many other single letters) for its built-in shortcuts in the DAG. With the event filter returning `True` for recognized leader-mode keys, these will be consumed before Nuke sees them. This is by design: during leader mode only, these keys are remapped. Because the filter is only installed when in leader mode, all keys behave normally outside leader mode.

The E key is special: it is currently bound to "Select Upstream Ignoring Hidden" (`shortcutContext=2`). In leader mode, E should mean "scale up (expand)". The event filter will consume E (returning True) before Nuke's shortcut fires. This is correct.

Shift+E must be re-registered as the leader key entry point (replacing the existing "Layout Upstream" shortcut, which is the intent per PROJECT.md v1.4 requirements).

### Constraint: DAG widget may be None if called before Nuke fully loads

Guard `get_active_dag_widget()` with a None check. If the DAG widget cannot be found (e.g., called from a script context with no GUI), fail gracefully:

```python
def enter_leader_mode():
    dag = get_active_dag_widget()
    if dag is None:
        return  # no DAG visible; nothing to do
    ...
```

### Constraint: No nuke.executeInMainThread needed

All Qt widget operations (show, hide, paint, install event filter) must occur on the main thread. Since `addMenuCommand` callbacks and Shift+E fire on the main thread, there is no threading concern here. Do NOT use `nuke.executeInMainThread` wrappers — they add unnecessary indirection.

### Constraint: Do not reparent the overlay after creation

Setting `setParent(None)` and later re-parenting to a different DAG widget causes the overlay to lose its FramelessWindowHint. Create a fresh `LeaderModeOverlay` instance each time leader mode is entered. The overhead is negligible (short-lived widget).

### Constraint: Nuke's ScriptLoad callback vs DAG widget lifetime

If the user opens a new script, the existing DAG widget is destroyed and a new one is created. The event filter is installed on the old widget, which will be destroyed. Qt automatically removes event filters when the filtered object is destroyed (since the filter's parent is the DAG widget, Qt's parent-child ownership will call deleteLater on the filter too). However, the `_state.active_filter` reference in Python will be stale. Clear `_state.active_filter = None` in `_exit_leader_mode()` and guard against double-remove.

**Confidence: MEDIUM** (inferred from Qt parent-child ownership semantics; not directly confirmed by Nuke-specific documentation).

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|---|---|---|---|
| Event interception | `installEventFilter` on DAG widget | `QApplication.installEventFilter` (global) | Global filter fires for every event in all Nuke UI panels; documented performance cost; unnecessary scope |
| Event interception | `installEventFilter` on DAG widget | Subclass the DAG widget | DAG widget is a Nuke-internal C++ class; cannot subclass it from Python |
| Event interception | `installEventFilter` on DAG widget | `nuke.addMenuCommand` with single-letter shortcuts in DAG context | Cannot be dynamically installed/removed; cannot implement stateful dispatch (WASD chaining stays in leader mode); conflicts with other registered shortcuts |
| Overlay widget type | Child `QWidget` with `paintEvent` | Top-level `Qt.Tool` frameless window | Requires `mapToGlobal()` positioning math, separate OS window, risks appearing under the DAG; more complex lifecycle |
| Overlay widget type | Child `QWidget` with `paintEvent` | `QLabel` with stylesheet | Limited to rectangular colored boxes; cannot draw custom key icons; stylesheet backgrounds fight with WA_TranslucentBackground |
| Overlay widget type | Child `QWidget` with `paintEvent` | Nuke's built-in panel/dock system | No support for transient floating overlays; panels require user docking/undocking |
| DAG widget discovery | `objectName() contains "DAG"` | `windowTitle() == "Node Graph"` + `findChild(QGLWidget)` | The `QGLWidget` approach breaks on Nuke 16+ where DAG is a standard QWidget |
| State storage | Module-level `_state` object | Class-level singleton | Module-level is simpler; the leader key controller is effectively a singleton by nature; matches the prefs singleton pattern already used in the codebase |

---

## No New Dependencies

All patterns here use only:
- `PySide6.QtWidgets` (QWidget, QApplication) — already in project
- `PySide6.QtCore` (QObject, QEvent, QTimer, Qt) — already in project
- `PySide6.QtGui` (QPainter, QColor, QFont, QKeyEvent) — already in project

No new pip installs. No new library files. The changes are API usage patterns only.

---

## Sources

- [Nuke Node graph utilities using Qt/PySide2 — Erwan Leroy](https://erwanleroy.com/nuke-node-graph-utilities-using-qt-pyside2/) — `get_dag_widgets` objectName pattern, overlay geometry, HIGH confidence
- [Updating Your Python Scripts for Nuke 16 and PySide6 — Erwan Leroy](https://erwanleroy.com/updating-your-python-scripts-for-nuke-16-and-pyside6/) — PySide6 migration, DAG widget non-GL change, "DAG.Group1" naming, MEDIUM-HIGH confidence
- [Fixing an annoying Nuke "feature" — Pixelmania](https://pixelmania.se/fixing-an-annoying-nuke-feature/) — Real-world per-widget installEventFilter on Nuke DAG, `return True` consumption, MEDIUM confidence
- [Q100715: How to address Python PySide issues in Nuke 16+ — Foundry](https://support.foundry.com/hc/en-us/articles/25604028087570-Q100715-How-to-address-Python-PySide-issues-in-Nuke-16) — Official Foundry guidance on PySide6 migration, HIGH confidence
- [The Event System — Qt for Python](https://doc.qt.io/qtforpython-5/overviews/eventsandfilters.html) — installEventFilter semantics, return True consumption, application-level performance warning, HIGH confidence
- [PySide6.QtWidgets.QWidget — Qt for Python](https://doc.qt.io/qtforpython-6.8/PySide6/QtWidgets/QWidget.html) — WA_TranslucentBackground, WA_TransparentForMouseEvents, child widget behavior, HIGH confidence
- [PySide6.QtGui.QKeyEvent — Qt for Python](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QKeyEvent.html) — key(), modifiers() API, HIGH confidence
- [Widget overlay pattern — GitHub Gist (zhanglongqi)](https://gist.github.com/zhanglongqi/78d7b5cd24f7d0c42f5d116d967923e7) — child QWidget overlay with transparent palette and resizeEvent, MEDIUM confidence (PyQt4 era but pattern is stable)
- [nuke.MenuBar — Nuke Python API Reference](https://learn.foundry.com/nuke/developers/140/pythonreference/_autosummary/nuke.MenuBar.html) — shortcutContext parameter values (0=Window, 1=Application, 2=DAG), HIGH confidence
- [Nuke 16.0v1 Release Notes — Foundry](https://learn.foundry.com/nuke/content/release_notes/16.0/nuke_16.0v1_releasenotes.html) — PySide6 adoption, Qt6 upgrade, HIGH confidence
