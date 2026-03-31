"""node_layout_leader — Leader key event filter and state machine for node_layout.

This module implements the leader key mode for the node_layout Nuke plugin.
``arm()`` is the sole public entry point: it installs a ``LeaderKeyFilter``
onto ``QApplication`` ephemerally, activates leader mode, and schedules the
overlay hint display.  The filter intercepts keypresses for single-shot
command dispatch (V, Z, F, C) and chaining commands (W/A/S/D/Q/E), cancels
on unrecognised input or a mouse click, then removes itself via ``_disarm()``.

Single-shot keys (V, Z, F, C) disarm leader mode after dispatch.  Chaining
keys (W, A, S, D, Q, E) keep leader mode active so the user can chain
movement and scale operations without re-pressing Shift+E each time.  The
overlay is hidden on the first chaining keypress and does not re-appear
until a new ``arm()`` call.

Phase 21 (menu.py) activates leader mode by adding::

    layout_menu.addCommand(
        'Layout Upstream',
        "import node_layout_leader; node_layout_leader.arm()",
        'shift+e',
        shortcutContext=2,
    )

The ``shortcutContext=2`` on the Shift+E binding ensures arm() is only called
when the Nuke DAG panel has keyboard focus (LEAD-04), so arm() itself needs
no additional focus guard.
"""
from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication

# ---------------------------------------------------------------------------
# Module-level globals — ephemeral lifecycle state (D-01, D-02, D-04)
# ---------------------------------------------------------------------------

_leader_active = False       # True while leader mode is armed and waiting for a key
_filter = None               # LeaderKeyFilter singleton — created lazily on first arm()
_overlay = None              # LeaderKeyOverlay singleton — created lazily in arm()
_overlay_timer = None        # QTimer instance used to delay overlay display; cancelled on early disarm


# ---------------------------------------------------------------------------
# LeaderKeyFilter — the QObject event filter (D-18)
# ---------------------------------------------------------------------------

class LeaderKeyFilter(QObject):
    """QObject event filter that intercepts keypresses during leader mode.

    Installed onto QApplication.instance() ephemerally by arm() and removed
    by _disarm() as soon as any key or mouse event resolves leader mode.

    The filter is a module-level singleton (D-02): one instance is created on
    the first call to arm() and reused across all subsequent arm/disarm cycles.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Named QTimer instance so it can be stopped in _disarm() (D-06/D-07).
        # QTimer.singleShot() returns None and cannot be cancelled — a named
        # instance is required here.
        self._overlay_timer = QTimer()
        self._overlay_timer.setSingleShot(True)
        # Expose timer reference in the module global so _disarm() can stop it
        # without needing to reach through the filter object.
        global _overlay_timer
        _overlay_timer = self._overlay_timer

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 — Qt naming convention
        """Intercept events when leader mode is active.

        Returns True to consume the event (suppress Nuke handling), or False
        to allow the event to propagate normally.

        When leader mode is inactive this method returns False unconditionally
        (D-15) — zero interference with Nuke's normal event handling.
        """
        global _leader_active
        if not _leader_active:
            return False

        event_type = event.type()

        # Qt sends ShortcutOverride before KeyPress; if not consumed, Nuke's shortcut
        # system matches the key (e.g., C -> ColorCorrect) before our KeyPress handler runs.
        if event_type == QEvent.Type.ShortcutOverride:
            # Accept the shortcut override to prevent Nuke's shortcut system
            # from matching this key while leader mode is active.
            event.accept()
            return True

        if event_type == QEvent.Type.KeyPress:
            # Auto-repeat guard (D-16): consume held-key repeats silently.
            if event.isAutoRepeat():
                return True

            key = event.key()
            dispatch_function = _DISPATCH_TABLE.get(key)

            if dispatch_function is not None:
                # Single-shot key: disarm first, then dispatch.
                _disarm()
                dispatch_function()
                return True

            chaining_function = _CHAINING_DISPATCH_TABLE.get(key)
            if chaining_function is not None:
                # Chaining key: dispatch and hide overlay, but stay in leader mode (D-08).
                if _overlay is not None:
                    _overlay.hide()
                chaining_function()
                return True

            # Unrecognised key: disarm and consume.
            _disarm()
            return True

        if event_type == QEvent.Type.MouseButtonPress:
            # Mouse click during leader mode: cancel cleanly but let the click
            # propagate to Nuke so the user's intended action still fires (D-14).
            _disarm()
            return False

        return False


# ---------------------------------------------------------------------------
# Dispatch helper functions — inline imports avoid circular imports at startup
# ---------------------------------------------------------------------------

def _dispatch_layout():
    """Context-aware layout dispatch for the V key (D-10, DISP-01).

    1 node selected  → layout_upstream() (single-root tree layout)
    2+ nodes selected → layout_selected() (multi-node selection layout)
    0 nodes selected  → no-op (nothing to lay out)
    """
    import nuke          # noqa: PLC0415
    import node_layout   # noqa: PLC0415

    selected_nodes = nuke.selectedNodes()
    if len(selected_nodes) == 1:
        node_layout.layout_upstream()
    elif len(selected_nodes) >= 2:
        node_layout.layout_selected()


def _dispatch_horizontal_layout():
    """Horizontal spine layout dispatch for the Z key (D-10, DISP-02)."""
    import node_layout   # noqa: PLC0415

    node_layout.layout_selected_horizontal()


def _dispatch_freeze_toggle():
    """Freeze / unfreeze toggle dispatch for the F key (D-11, DISP-03).

    Semantics — "any unfrozen means freeze all":
    - If ALL selected nodes are already frozen  → unfreeze_selected()
    - If ANY selected node is unfrozen          → freeze_selected()
    - Empty selection                           → no-op
    """
    import nuke                                          # noqa: PLC0415
    import node_layout                                   # noqa: PLC0415
    from node_layout_state import read_freeze_group      # noqa: PLC0415

    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        return

    all_frozen = all(read_freeze_group(node) is not None for node in selected_nodes)
    if all_frozen:
        node_layout.unfreeze_selected()
    else:
        node_layout.freeze_selected()


def _dispatch_clear_state():
    """Clear layout state on selected nodes for the C key."""
    import node_layout   # noqa: PLC0415

    node_layout.clear_layout_state_selected()


def _dispatch_move_up():
    """Move selected nodes up for the W key (D-01, DISP-05)."""
    import make_room  # noqa: PLC0415
    make_room.make_room()


def _dispatch_move_down():
    """Move selected nodes down for the S key (D-01, DISP-05)."""
    import make_room  # noqa: PLC0415
    make_room.make_room(direction='down')


def _dispatch_move_left():
    """Move selected nodes left for the A key (D-01, DISP-05)."""
    import make_room  # noqa: PLC0415
    make_room.make_room(amount=800, direction='left')


def _dispatch_move_right():
    """Move selected nodes right for the D key (D-01, DISP-05)."""
    import make_room  # noqa: PLC0415
    make_room.make_room(amount=800, direction='right')


def _dispatch_shrink():
    """Scale down selection for the Q key (D-03, DISP-06)."""
    import node_layout  # noqa: PLC0415
    node_layout.shrink_selected()


def _dispatch_expand():
    """Scale up selection for the E key (D-04, DISP-07)."""
    import node_layout  # noqa: PLC0415
    node_layout.expand_selected()


# ---------------------------------------------------------------------------
# Dispatch table — maps Qt key codes to handler callables (D-10)
# ---------------------------------------------------------------------------

_DISPATCH_TABLE = {
    Qt.Key.Key_V: _dispatch_layout,
    Qt.Key.Key_Z: _dispatch_horizontal_layout,
    Qt.Key.Key_F: _dispatch_freeze_toggle,
    Qt.Key.Key_C: _dispatch_clear_state,
}

# ---------------------------------------------------------------------------
# Chaining dispatch table — maps chaining key codes to handler callables (D-07)
# Chaining keys keep leader mode active after dispatch (D-08).
# ---------------------------------------------------------------------------

_CHAINING_DISPATCH_TABLE = {
    Qt.Key.Key_W: _dispatch_move_up,
    Qt.Key.Key_S: _dispatch_move_down,
    Qt.Key.Key_A: _dispatch_move_left,
    Qt.Key.Key_D: _dispatch_move_right,
    Qt.Key.Key_Q: _dispatch_shrink,
    Qt.Key.Key_E: _dispatch_expand,
}

# ---------------------------------------------------------------------------
# Letter-to-Qt-key mapping — used by dispatch_key() for click-based dispatch
# ---------------------------------------------------------------------------

_LETTER_TO_QT_KEY = {
    "V": Qt.Key.Key_V,
    "Z": Qt.Key.Key_Z,
    "F": Qt.Key.Key_F,
    "C": Qt.Key.Key_C,
    "W": Qt.Key.Key_W,
    "A": Qt.Key.Key_A,
    "S": Qt.Key.Key_S,
    "D": Qt.Key.Key_D,
    "Q": Qt.Key.Key_Q,
    "E": Qt.Key.Key_E,
}


# ---------------------------------------------------------------------------
# DAG widget discovery helper (D-08)
# ---------------------------------------------------------------------------

def _find_dag_widget():
    """Return the top-level widget that currently contains keyboard focus.

    Walks the parentWidget() chain from QApplication.focusWidget() up to the
    last non-None ancestor.  This is the Nuke DAG panel container and serves
    as the parent for the overlay so that centering math maps to the right
    screen region.

    Returns None if no widget currently holds focus (e.g. Nuke is not in the
    foreground when arm() is called).
    """
    app_instance = QApplication.instance()
    if app_instance is None:
        return None

    focus_widget = app_instance.focusWidget()
    if focus_widget is None:
        return None

    # Walk up to the top-level window-like container.
    current_widget = focus_widget
    while current_widget.parentWidget() is not None:
        current_widget = current_widget.parentWidget()
    return current_widget


# ---------------------------------------------------------------------------
# Public entry point and internal disarm
# ---------------------------------------------------------------------------

def arm():
    """Activate leader key mode.

    Installs the LeaderKeyFilter onto QApplication, schedules the overlay hint,
    and sets _leader_active = True.  All subsequent keypresses are intercepted
    by the filter until a recognised key dispatches a command, an unrecognised
    key or mouse click cancels, or arm() itself is called again (D-04 guard).

    Called by Phase 21's Shift+E menu binding.  The ``shortcutContext=2`` on
    that binding ensures arm() is only reached when the DAG panel has focus.

    Ordering (D-05): _leader_active = True and installEventFilter() are set
    BEFORE the overlay timer is started, guaranteeing all keypresses are
    intercepted from the moment arm() returns.
    """
    global _leader_active, _filter, _overlay, _overlay_timer

    # D-04: double-arm guard — idempotent if already active.
    if _leader_active:
        return

    # Lazily create the singleton filter (and its embedded timer) on first arm().
    if _filter is None:
        _filter = LeaderKeyFilter()
        # _overlay_timer module global is set inside LeaderKeyFilter.__init__

    # Discover the DAG panel for overlay parenting (D-08).
    dag_widget = _find_dag_widget()

    # Lazily create the overlay singleton on first arm(); re-parent on subsequent calls.
    if _overlay is None:
        from node_layout_overlay import LeaderKeyOverlay  # noqa: PLC0415
        _overlay = LeaderKeyOverlay(parent=dag_widget)
    elif dag_widget is not None:
        _overlay.reparent(dag_widget)

    # D-05: set active flag and install filter BEFORE scheduling overlay.
    _leader_active = True
    QApplication.instance().installEventFilter(_filter)

    # Schedule delayed overlay display using the named timer (D-06/D-07).
    # Disconnect any previous connection to avoid duplicate slots accumulating
    # across repeated arm() calls.
    import node_layout_prefs  # noqa: PLC0415
    delay_ms = node_layout_prefs.prefs_singleton.get("hint_popup_delay_ms")

    try:
        _overlay_timer.timeout.disconnect()
    except RuntimeError:
        pass  # No connections present — safe to ignore.
    _overlay_timer.timeout.connect(_overlay.show)
    _overlay_timer.start(delay_ms)


def _disarm():
    """Deactivate leader key mode and clean up.

    Removes the event filter, stops the overlay timer (cancelling any pending
    show), and hides the overlay if it is visible.  Safe to call from within
    eventFilter() — Qt explicitly supports removeEventFilter() during event
    delivery.

    Guards against double-disarm with the _leader_active check.
    """
    global _leader_active

    if not _leader_active:
        return

    _leader_active = False
    QApplication.instance().removeEventFilter(_filter)

    # Cancel pending overlay display (D-07).  stop() is a no-op if not running.
    if _overlay_timer is not None:
        _overlay_timer.stop()

    if _overlay is not None:
        _overlay.hide()


def dispatch_key(key_letter):
    """Dispatch a leader key action by letter string, as if the user pressed that key.

    Used by ClickableKeyCell in node_layout_overlay.py to wire mouse clicks to
    the same dispatch logic as keyboard input.

    Single-shot keys (V, Z, F, C): disarm leader mode, then dispatch.
    Chaining keys (W, A, S, D, Q, E): hide overlay but keep leader mode active,
    then dispatch.

    Args:
        key_letter: Single uppercase letter string (e.g. "W", "V"). Unrecognised
                    letters are silently ignored — the overlay only has valid keys.
    """
    qt_key = _LETTER_TO_QT_KEY.get(key_letter)
    if qt_key is None:
        return

    dispatch_function = _DISPATCH_TABLE.get(qt_key)
    if dispatch_function is not None:
        # Single-shot key: disarm first, then dispatch (mirrors eventFilter order).
        _disarm()
        dispatch_function()
        return

    chaining_function = _CHAINING_DISPATCH_TABLE.get(qt_key)
    if chaining_function is not None:
        # Chaining key: hide overlay but stay in leader mode, then dispatch.
        if _overlay is not None:
            _overlay.hide()
        chaining_function()
