"""LeaderKeyOverlay — floating HUD widget for node_layout leader key mode.

Displays the 10 active leader-mode command keys in QWERTY keyboard geometry.
Floats over the active DAG panel without stealing keyboard focus.

Phase 19 (node_layout_leader.py) controls show()/hide() calls; this module
only defines the widget and its visual structure.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

# ---------------------------------------------------------------------------
# Module-level constants (D-09, D-10, D-17)
# Named constants allow AST tests to verify two distinct badge colors without
# importing PySide6 in the test environment.
# ---------------------------------------------------------------------------

_CHAINING_KEY_COLOR = QColor(40, 120, 160)      # teal/blue tint — sticky keys keep leader mode alive
_SINGLE_SHOT_KEY_COLOR = QColor(220, 220, 220)  # neutral white/gray — one-shot keys exit leader mode

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
    # row 2 col 1 intentionally empty — X is not in the command set
    ("C", "Clear State", 2, 2),
    ("V", "Layout",       2, 3),
]


class LeaderKeyOverlay(QWidget):
    """Floating HUD overlay displaying active leader-mode command keys.

    Inherits from QWidget and uses Qt.WindowType.Tool +
    WA_ShowWithoutActivating so the overlay never steals keyboard focus
    from the DAG panel.

    Usage (by Phase 19 event filter):
        overlay = LeaderKeyOverlay(parent=dag_widget)
        overlay.show()   # centers over dag_widget
        overlay.hide()   # fully dismisses the overlay
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # D-12, D-13: focus-safe floating tool window — must be set before first show()
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # D-01: required for semi-transparent paintEvent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()
        # Ensure rect() has real dimensions before show() runs centering math (Pitfall 4)
        self.adjustSize()

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
        # Give the empty X column (col 1, row 2) visible width matching other cells
        key_grid.setColumnMinimumWidth(1, 64)

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
            A QWidget containing the key badge and action label stacked vertically.
        """
        cell_container = QWidget()
        cell_layout = QVBoxLayout(cell_container)
        cell_layout.setContentsMargins(2, 2, 2, 2)
        cell_layout.setSpacing(3)

        # D-09/D-10: chaining keys get teal/blue badge; single-shot keys get neutral badge
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

        return cell_container

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
        """Show the overlay centered over the parent widget (D-08).

        Calls super().show() first so the native window exists before
        move() is called (avoids Pitfall 4: move before native window exists).
        """
        super().show()
        parent_widget = self.parentWidget()
        if parent_widget is not None:
            global_center = parent_widget.mapToGlobal(parent_widget.rect().center())
            self.move(global_center - self.rect().center())
