"""LeaderKeyOverlay — floating HUD widget for node_layout leader key mode.

Displays the 10 active leader-mode command keys in QWERTY keyboard geometry.
Floats over the active DAG panel without stealing keyboard focus.

Phase 19 (node_layout_leader.py) controls show()/hide() calls; this module
only defines the widget and its visual structure.

TASKBAR ALERT ROOT CAUSE (260331-axc):
Qt's WA_ShowWithoutActivating and WindowDoesNotAcceptFocus flags are applied
correctly but Qt's own WM_ACTIVATE / WM_SETFOCUS handling and the ShowWindow()
call still trigger Windows' activation machinery in some Qt/Nuke configurations.

CONFIRMED FIX (Task 3):
  - Override showEvent() and call _apply_no_activate_win32() after the native
    window is created (winId() is valid inside showEvent).
  - _apply_no_activate_win32() uses ctypes to set WS_EX_NOACTIVATE |
    WS_EX_TOOLWINDOW directly on the HWND via SetWindowLongPtrW, then calls
    SetWindowPos with SWP_NOACTIVATE | SWP_FRAMECHANGED to apply the new style
    without reactivating the window.
  - After showEvent, immediately call SetForegroundWindow() on the parent
    (Nuke's main window) to restore focus in case Windows briefly granted it
    to the overlay.

WHY Qt FLAGS ALONE ARE INSUFFICIENT:
  Qt sets WS_EX_NOACTIVATE via CreateWindowExW flags at window creation time.
  However, if the overlay is re-shown after being hidden (second arm() call),
  Qt calls ShowWindow(hwnd, SW_SHOW) without re-creating the native window.
  On some Windows versions, ShowWindow() ignores the existing WS_EX_NOACTIVATE
  flag and activates the window anyway. The ctypes approach re-asserts the flag
  unconditionally on every showEvent(), before and after the native window exists.
"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter
from PySide6.QtWidgets import QDialog, QGridLayout, QLabel, QVBoxLayout, QWidget

# ---------------------------------------------------------------------------
# Windows-specific activation suppression via ctypes (260331-axc Task 3)
# ---------------------------------------------------------------------------

def _apply_no_activate_win32(hwnd):
    """Set WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW on *hwnd* using raw Win32 API.

    Called from LeaderKeyOverlay.showEvent() after the native window exists.
    This is more reliable than Qt flags alone because ShowWindow() on a
    previously-hidden window can ignore WS_EX_NOACTIVATE set at creation time
    on certain Windows builds.

    The SetWindowPos() call with SWP_FRAMECHANGED forces Windows to re-read the
    extended style bits without moving, resizing, or activating the window.

    Args:
        hwnd: Integer window handle (from widget.winId()).

    No-op (silent) on non-Windows platforms or if ctypes is unavailable.
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes
        import ctypes.wintypes

        # Extended window style constants
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOOLWINDOW = 0x00000080

        # SetWindowPos flags — update frame without activating or moving
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        # Retrieve current extended style and OR-in the noactivate/toolwindow bits
        current_ex_style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        new_ex_style = current_ex_style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new_ex_style)

        # Force Windows to re-read the extended style without activating
        user32.SetWindowPos(
            hwnd,
            0,  # HWND_TOP placeholder — ignored due to SWP_NOZORDER
            0, 0, 0, 0,  # x, y, cx, cy — ignored due to SWP_NOMOVE | SWP_NOSIZE
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )
    except Exception:  # noqa: BLE001
        # Never crash Nuke due to a cosmetic Win32 call failing
        pass


def _apply_linux_hints(widget):
    """Apply X11/Wayland window property hints on Linux to prevent taskbar activation.

    Called from LeaderKeyOverlay.__init__() after adjustSize() to set properties
    that tell the X11/Wayland window manager this is a temporary overlay, not a
    top-level application window.

    Uses setProperty() to set _NET_WM_STATE_SKIP_TASKBAR and _NET_WM_STATE_SKIP_PAGER
    hints, which instruct X11 to exclude this window from the taskbar and pager,
    preventing autohide taskbar reveal and icon highlighting on Linux.

    Args:
        widget: The QWidget (LeaderKeyOverlay) to apply hints to.

    No-op (silent) on non-Linux platforms or if property system unavailable.
    """
    if not sys.platform.startswith("linux"):
        return

    try:
        # Set X11/Wayland window properties to prevent taskbar integration
        widget.setProperty("_NET_WM_STATE_SKIP_TASKBAR", True)
        widget.setProperty("_NET_WM_STATE_SKIP_PAGER", True)
    except Exception:  # noqa: BLE001
        # Never crash Nuke due to a cosmetic property hint failing
        pass


def _restore_nuke_focus(parent_widget):
    """Re-activate the Nuke parent window via Win32 SetForegroundWindow().

    Called after showEvent() as a secondary guard against activation bleed-through.
    If Windows grants the overlay focus despite WS_EX_NOACTIVATE (which can
    happen on the first show or in edge cases), this call immediately hands
    focus back to the Nuke window, collapsing any autohide taskbar reveal and
    clearing any taskbar icon highlight.

    Uses the parent_widget's HWND so we re-activate the exact window that had
    focus before the overlay appeared.  Falls back to QApplication.activeWindow()
    if parent_widget is None.

    Args:
        parent_widget: The QWidget that is parent of the overlay, or None.

    No-op (silent) on non-Windows platforms or if ctypes is unavailable.
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes

        from PySide6.QtWidgets import QApplication

        focus_target = parent_widget
        if focus_target is None:
            focus_target = QApplication.activeWindow()
        if focus_target is None:
            return

        target_hwnd = int(focus_target.winId())
        ctypes.windll.user32.SetForegroundWindow(target_hwnd)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Module-level constants (D-09, D-10, D-17)
# Named constants allow AST tests to verify two distinct badge colors without
# importing PySide6 in the test environment.
# ---------------------------------------------------------------------------

# Teal/blue tint — sticky keys keep leader mode alive
_CHAINING_KEY_COLOR = QColor(40, 120, 160)
# Neutral white/gray — one-shot keys exit leader mode
_SINGLE_SHOT_KEY_COLOR = QColor(220, 220, 220)

# Keys that keep leader mode active after being pressed (WASD / QE) — D-09
CHAINING_KEYS = {"W", "A", "S", "D", "Q", "E"}

# ---------------------------------------------------------------------------
# Key layout data — QWERTY grid positions (D-05, D-07)
# ---------------------------------------------------------------------------

_KEY_LAYOUT = [
    # (key_letter, action_label, row, col)
    ("Q", "Shrink",       0, 0),
    ("W", "Move Up",      0, 1),
    ("E", "Expand",       0, 2),
    ("A", "Move Left",    1, 0),
    ("S", "Move Down",    1, 1),
    ("D", "Move Right",   1, 2),
    ("F", "Freeze",       1, 3),
    ("Z", "Horiz Layout", 2, 0),
    ("X", "Sel Hidden",   2, 1),
    ("C", "Clear State", 2, 2),
    ("V", "Layout",       2, 3),
]


class ClickableKeyCell(QWidget):
    """A key cell widget that dispatches its leader key action on mouse click.

    Wraps the key badge and action label into a clickable container.
    Overrides mousePressEvent to call node_layout_leader.dispatch_key() with
    the cell's key letter, triggering the same action as pressing that key.

    The hand cursor is set in __init__ so users see a pointer on hover,
    indicating the cell is clickable.
    """

    def __init__(self, key_letter, action_label, parent=None):
        super().__init__(parent)
        self._key_letter = key_letter

        # NoFocus prevents any implicit focus grab when the cell is shown or clicked.
        # Cursor is inherited from LeaderKeyOverlay (set there to avoid WM_SETCURSOR
        # messages being sent per child widget, which can trigger activation on Windows).
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        cell_layout = QVBoxLayout(self)
        cell_layout.setContentsMargins(2, 2, 2, 2)
        cell_layout.setSpacing(3)

        # Chaining keys get teal/blue badge; single-shot keys get neutral badge.
        badge_color = _CHAINING_KEY_COLOR if key_letter in CHAINING_KEYS else _SINGLE_SHOT_KEY_COLOR
        badge_rgb = f"rgb({badge_color.red()}, {badge_color.green()}, {badge_color.blue()})"

        # Key badge — bold monospace letter
        key_badge_label = QLabel(key_letter)
        badge_font = QFont("monospace", 14, QFont.Weight.Bold)
        key_badge_label.setFont(badge_font)
        key_badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        key_badge_label.setStyleSheet(
            f"background-color: {badge_rgb}; color: #111111;"
            " border-radius: 4px; padding: 4px 12px; min-width: 28px;"
        )

        # Action label — small gray text below badge
        action_label_widget = QLabel(action_label)
        action_font = QFont()
        action_font.setPointSize(8)
        action_label_widget.setFont(action_font)
        action_label_widget.setStyleSheet("color: #999999;")
        action_label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cell_layout.addWidget(key_badge_label)
        cell_layout.addWidget(action_label_widget)

    def mousePressEvent(self, event):  # noqa: N802 — Qt naming convention
        """Dispatch the key action when this cell is clicked.

        Uses an inline import to avoid circular imports at module load time —
        the same pattern as the dispatch helpers in node_layout_leader.py.
        """
        import node_layout_leader  # noqa: PLC0415
        node_layout_leader.dispatch_key(self._key_letter)


class LeaderKeyOverlay(QDialog):
    """Floating HUD overlay displaying active leader-mode command keys.

    Inherits from QDialog (modeless popup) which has better window management
    on Linux and Windows — does not trigger taskbar activation or autohide reveal.
    Uses Qt.WindowType.Popup with setModal(False) for a non-modal floating overlay.

    Usage (by Phase 19 event filter):
        overlay = LeaderKeyOverlay(parent=dag_widget)
        overlay.show()   # centers over dag_widget
        overlay.hide()   # fully dismisses the overlay
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Use Popup window type for floating overlay; modeless (not modal) dialog.
        # QDialog as base class avoids taskbar integration on Linux and Windows.
        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setModal(False)  # Modeless — doesn't block interaction with parent
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # D-01: required for semi-transparent paintEvent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Pointing hand on the overlay so children inherit it — avoids per-child
        # WM_SETCURSOR messages that can trigger Windows activation machinery.
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()
        # Ensure rect() has real dimensions before show() runs centering math (Pitfall 4)
        self.adjustSize()
        # Apply Linux-specific X11/Wayland hints to prevent taskbar activation (260331-linux)
        _apply_linux_hints(self)

    def reparent(self, new_parent):
        """Re-parent the overlay, restoring all window flags and attributes.

        Qt's setParent() resets ALL window flags and widget attributes on the
        widget.  This method wraps setParent() and immediately re-applies the
        flags that __init__ originally set, preventing Windows from treating a
        subsequent show() as a foreground window activation request (which
        triggers taskbar icon flash and autohide taskbar reveal).
        """
        self.setParent(new_parent)
        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _build_ui(self):
        """Construct the LEADER KEY title and QWERTY key grid."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 12, 16, 16)
        main_layout.setSpacing(10)

        # D-03: "LEADER KEY" title header
        title_label = QLabel("LEADER KEY")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #cccccc;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # D-04/D-05: QWERTY grid layout
        key_grid = QGridLayout()
        key_grid.setSpacing(8)

        for key_letter, action_label, row, col in _KEY_LAYOUT:
            key_cell_widget = self._make_key_cell(key_letter, action_label)
            key_grid.addWidget(key_cell_widget, row, col)

        main_layout.addLayout(key_grid)
        self.setLayout(main_layout)

    def _make_key_cell(self, key_letter, action_label):
        """Build a 2-line key cell: bold key badge over gray action label (D-02, D-06).

        Args:
            key_letter: Single uppercase letter identifying the key (e.g. "W").
            action_label: Short action name displayed below the badge (e.g. "Move Up").

        Returns:
            A ClickableKeyCell containing the key badge and action label stacked
            vertically.  Mouse clicks on the returned widget dispatch the key action.
        """
        return ClickableKeyCell(key_letter, action_label)

    def paintEvent(self, event):
        """Draw a semi-transparent rounded-rect background (D-01).

        Uses QPainter directly rather than stylesheet background because
        stylesheet transparency depends on the parent chain, which cannot
        be guaranteed inside Nuke's embedded widget hierarchy.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(20, 20, 20, 180))       # ~70% opacity dark background
        painter.setPen(QColor(180, 180, 180, 100))       # subtle border
        painter.drawRoundedRect(self.rect(), 8, 8)

    def show(self):
        """Show the overlay at the current mouse cursor position, clamped to screen bounds.

        Position is computed and applied BEFORE super().show() so the window
        appears at the correct location on the first ShowWindow() call.  Calling
        move() on an already-visible window goes through SetWindowPos() on
        Windows, which Qt does not call with SWP_NOACTIVATE — that can trigger
        taskbar icon flash and autohide-taskbar reveal.  Moving the hidden window
        first means Qt folds the position into the ShowWindow() call, which does
        respect WA_ShowWithoutActivating.

        The old "show first so native window exists" comment applied to the
        mapToGlobal(parent.rect().center()) approach.  QCursor.pos() and
        self.width()/height() (set by adjustSize() in __init__) do not require
        a native window.

        On Linux, uses setGeometry() instead of move() to avoid triggering
        X11 ConfigureNotify events that can activate the window.

        Positioning:
          - Reads the global cursor position at the moment show() is called.
          - Centers the overlay on the cursor.
          - Clamps to screen.availableGeometry() so no part of the overlay
            extends beyond the usable screen area (excludes taskbar/dock).
        """
        cursor_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor_pos)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        x = cursor_pos.x() - self.width() // 2
        y = cursor_pos.y() - self.height() // 2

        # Clamp so the overlay stays fully within the available screen area.
        x = max(screen_geometry.left(), min(x, screen_geometry.right() - self.width()))
        y = max(screen_geometry.top(), min(y, screen_geometry.bottom() - self.height()))

        # On Linux, use setGeometry() instead of move() to avoid X11 ConfigureNotify
        # events that can trigger window activation. On other platforms, use move()
        # to maintain compatibility with existing behavior.
        if sys.platform.startswith("linux"):
            self.setGeometry(x, y, self.width(), self.height())
        else:
            self.move(x, y)
        super().show()

    def showEvent(self, event):  # noqa: N802 — Qt naming convention
        """Apply platform-specific activation suppression after the native window is created.

        Windows:
          Qt sets WS_EX_NOACTIVATE via CreateWindowExW at initial window creation.
          However, when a previously-hidden window is re-shown (second arm() call
          and beyond), Qt calls ShowWindow(hwnd, SW_SHOW) without re-creating the
          native window.  On some Windows versions this ShowWindow() call ignores
          the existing WS_EX_NOACTIVATE flag and activates the window, causing:
            - The autohide taskbar to reveal itself
            - The Nuke taskbar icon to highlight (flashing)
            - Both states persisting until the overlay is hidden

          This override re-asserts WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW on every
          show event via raw Win32 API (ctypes), which is reliable for both first
          show and subsequent re-shows.

        Linux:
          X11/Wayland window property hints (_NET_WM_STATE_SKIP_TASKBAR and
          _NET_WM_STATE_SKIP_PAGER) are applied in __init__(). Calling
          activateWindow() or raise_() would negate these hints by explicitly
          requesting focus, so we avoid focus manipulation on Linux entirely.

        Windows only gets focus restoration via Win32 API as a secondary safeguard.
        """
        super().showEvent(event)

        # Apply platform-specific activation suppression
        if sys.platform == "win32":
            # Re-assert WS_EX_NOACTIVATE on the actual HWND via Win32 API
            _apply_no_activate_win32(int(self.winId()))
            # Secondary safeguard (Windows): restore focus via Win32 API
            _restore_nuke_focus(self.parent())
