from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

import node_layout_prefs


def _make_section_header(text):
    """Create a bold QLabel for use as a section header in the prefs dialog form layout."""
    label = QLabel(text)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label


class NodeLayoutPrefsDialog(QDialog):
    """PySide6 dialog for editing Node Layout spacing preferences.

    The dialog is organized into four sections:
      - Spacing: H-axis gaps and vertical margin values
      - Scheme Multipliers: compact / normal / loose multipliers
      - Leader Key: hint popup delay
      - Advanced: font reference size and scaling reference count

    Section headers are bold QLabel rows (no QGroupBox borders).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Node Layout Preferences")
        self.setMinimumWidth(400)
        self._build_ui()
        self._populate_from_prefs()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        # --- Section: Spacing ---
        form_layout.addRow(_make_section_header("Spacing"))

        self.horizontal_subtree_gap_edit = QLineEdit()
        form_layout.addRow("Horizontal Subtree Gap (px):", self.horizontal_subtree_gap_edit)

        self.horizontal_side_vertical_gap_edit = QLineEdit()
        form_layout.addRow(
            "Horizontal Side Vertical Gap (px):",
            self.horizontal_side_vertical_gap_edit,
        )

        self.horizontal_mask_gap_edit = QLineEdit()
        form_layout.addRow("Horizontal Mask Gap (px):", self.horizontal_mask_gap_edit)

        self.base_subtree_margin_edit = QLineEdit()
        form_layout.addRow("Base Subtree Margin (px):", self.base_subtree_margin_edit)

        self.mask_input_ratio_edit = QLineEdit()
        form_layout.addRow("Mask Input Ratio:", self.mask_input_ratio_edit)

        # --- Section: Scheme Multipliers ---
        form_layout.addRow(QLabel(""))  # vertical breathing room
        form_layout.addRow(_make_section_header("Scheme Multipliers"))

        self.compact_multiplier_edit = QLineEdit()
        form_layout.addRow("Compact Multiplier:", self.compact_multiplier_edit)

        self.normal_multiplier_edit = QLineEdit()
        form_layout.addRow("Normal Multiplier:", self.normal_multiplier_edit)

        self.loose_multiplier_edit = QLineEdit()
        form_layout.addRow("Loose Multiplier:", self.loose_multiplier_edit)

        self.loose_gap_multiplier_edit = QLineEdit()
        form_layout.addRow("Loose Gap Multiplier:", self.loose_gap_multiplier_edit)

        # --- Section: Leader Key ---
        form_layout.addRow(QLabel(""))  # vertical breathing room
        form_layout.addRow(_make_section_header("Leader Key"))

        self.hint_popup_delay_ms_edit = QLineEdit()
        form_layout.addRow("Hint popup delay (ms):", self.hint_popup_delay_ms_edit)

        # --- Section: Advanced ---
        form_layout.addRow(QLabel(""))  # vertical breathing room
        form_layout.addRow(_make_section_header("Advanced"))

        self.dot_font_reference_size_edit = QLineEdit()
        form_layout.addRow("Dot Font Reference Size:", self.dot_font_reference_size_edit)

        self.scaling_reference_count_edit = QLineEdit()
        form_layout.addRow("Scaling Reference Count:", self.scaling_reference_count_edit)

        outer_layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        outer_layout.addWidget(button_box)

    def _populate_from_prefs(self):
        prefs_instance = node_layout_prefs.prefs_singleton
        self.horizontal_subtree_gap_edit.setText(str(prefs_instance.get("horizontal_subtree_gap")))
        self.horizontal_side_vertical_gap_edit.setText(
            str(prefs_instance.get("horizontal_side_vertical_gap"))
        )
        self.horizontal_mask_gap_edit.setText(str(prefs_instance.get("horizontal_mask_gap")))
        self.base_subtree_margin_edit.setText(str(prefs_instance.get("base_subtree_margin")))
        self.mask_input_ratio_edit.setText(str(prefs_instance.get("mask_input_ratio")))
        self.compact_multiplier_edit.setText(str(prefs_instance.get("compact_multiplier")))
        self.normal_multiplier_edit.setText(str(prefs_instance.get("normal_multiplier")))
        self.loose_multiplier_edit.setText(str(prefs_instance.get("loose_multiplier")))
        self.loose_gap_multiplier_edit.setText(str(prefs_instance.get("loose_gap_multiplier")))
        self.dot_font_reference_size_edit.setText(
            str(prefs_instance.get("dot_font_reference_size"))
        )
        self.scaling_reference_count_edit.setText(
            str(prefs_instance.get("scaling_reference_count"))
        )
        self.hint_popup_delay_ms_edit.setText(
            str(prefs_instance.get("hint_popup_delay_ms"))
        )

    def _on_accept(self):
        try:
            horizontal_subtree_gap_value = int(self.horizontal_subtree_gap_edit.text())
            horizontal_side_vertical_gap_value = int(self.horizontal_side_vertical_gap_edit.text())
            horizontal_mask_gap_value = int(self.horizontal_mask_gap_edit.text())
            base_subtree_margin_value = int(self.base_subtree_margin_edit.text())
            mask_input_ratio_value = float(self.mask_input_ratio_edit.text())
            compact_multiplier_value = float(self.compact_multiplier_edit.text())
            normal_multiplier_value = float(self.normal_multiplier_edit.text())
            loose_multiplier_value = float(self.loose_multiplier_edit.text())
            loose_gap_multiplier_value = float(self.loose_gap_multiplier_edit.text())
            dot_font_reference_size_value = int(self.dot_font_reference_size_edit.text())
            scaling_reference_count_value = int(self.scaling_reference_count_edit.text())
            hint_popup_delay_ms_value = int(self.hint_popup_delay_ms_edit.text())
        except ValueError:
            return

        if horizontal_subtree_gap_value <= 0:
            return
        if horizontal_side_vertical_gap_value < 0:
            return
        if horizontal_mask_gap_value < 0:
            return
        if base_subtree_margin_value <= 0:
            return
        if dot_font_reference_size_value <= 0:
            return
        if scaling_reference_count_value < 1:
            return
        if hint_popup_delay_ms_value < 0:
            return

        prefs_instance = node_layout_prefs.prefs_singleton
        prefs_instance.set("horizontal_subtree_gap", horizontal_subtree_gap_value)
        prefs_instance.set("horizontal_side_vertical_gap", horizontal_side_vertical_gap_value)
        prefs_instance.set("horizontal_mask_gap", horizontal_mask_gap_value)
        prefs_instance.set("base_subtree_margin", base_subtree_margin_value)
        prefs_instance.set("mask_input_ratio", mask_input_ratio_value)
        prefs_instance.set("compact_multiplier", compact_multiplier_value)
        prefs_instance.set("normal_multiplier", normal_multiplier_value)
        prefs_instance.set("loose_multiplier", loose_multiplier_value)
        prefs_instance.set("loose_gap_multiplier", loose_gap_multiplier_value)
        prefs_instance.set("dot_font_reference_size", dot_font_reference_size_value)
        prefs_instance.set("scaling_reference_count", scaling_reference_count_value)
        prefs_instance.set("hint_popup_delay_ms", hint_popup_delay_ms_value)
        prefs_instance.save()
        self.accept()


def show_prefs_dialog():
    """Instantiate and display the Node Layout preferences dialog."""
    dialog = NodeLayoutPrefsDialog()
    dialog.exec()
