import nuke

m = nuke.menu("Nuke")
edit = m.findItem("Edit")
layout_menu = edit.addMenu("Node Layout")

layout_menu.addCommand(
    'Layout Upstream',
    "import node_layout; node_layout.layout_upstream()",
    'shift+e',
    shortcutContext=2,
)
layout_menu.addCommand(
    'Layout Selected',
    "import node_layout; node_layout.layout_selected()",
)

layout_menu.addSeparator()

# CMD-01: scheme name at end for tab-menu discoverability
layout_menu.addCommand(
    'Layout Upstream Compact', "import node_layout; node_layout.layout_upstream_compact()"
)
layout_menu.addCommand(
    'Layout Selected Compact', "import node_layout; node_layout.layout_selected_compact()"
)
layout_menu.addCommand(
    'Layout Upstream Loose', "import node_layout; node_layout.layout_upstream_loose()"
)
layout_menu.addCommand(
    'Layout Selected Loose', "import node_layout; node_layout.layout_selected_loose()"
)
layout_menu.addCommand(
    'Clear Layout State Selected',
    "import node_layout; node_layout.clear_layout_state_selected()",
)
layout_menu.addCommand(
    'Clear Layout State Upstream',
    "import node_layout; node_layout.clear_layout_state_upstream()",
)
layout_menu.addCommand(
    'Layout Selected Horizontal', "import node_layout; node_layout.layout_selected_horizontal()"
)
layout_menu.addCommand(
    'Layout Selected Horizontal (Place Only)',
    "import node_layout; node_layout.layout_selected_horizontal_place_only()",
)

layout_menu.addSeparator()

layout_menu.addCommand(
    'Shrink Selected',
    "import node_layout; node_layout.shrink_selected()",
    'ctrl+,',
    shortcutContext=2,
)
layout_menu.addCommand(
    'Expand Selected',
    "import node_layout; node_layout.expand_selected()",
    'ctrl+.',
    shortcutContext=2,
)
layout_menu.addCommand(
    'Shrink Upstream',
    "import node_layout; node_layout.shrink_upstream()",
    'ctrl+shift+,',
    shortcutContext=2,
)
layout_menu.addCommand(
    'Expand Upstream',
    "import node_layout; node_layout.expand_upstream()",
    'ctrl+shift+.',
    shortcutContext=2,
)

layout_menu.addCommand(
    'Shrink Selected Horizontal', "import node_layout; node_layout.shrink_selected_horizontal()"
)
layout_menu.addCommand(
    'Shrink Selected Vertical', "import node_layout; node_layout.shrink_selected_vertical()"
)
layout_menu.addCommand(
    'Expand Selected Horizontal', "import node_layout; node_layout.expand_selected_horizontal()"
)
layout_menu.addCommand(
    'Expand Selected Vertical', "import node_layout; node_layout.expand_selected_vertical()"
)
layout_menu.addCommand(
    'Shrink Upstream Horizontal', "import node_layout; node_layout.shrink_upstream_horizontal()"
)
layout_menu.addCommand(
    'Shrink Upstream Vertical', "import node_layout; node_layout.shrink_upstream_vertical()"
)
layout_menu.addCommand(
    'Expand Upstream Horizontal', "import node_layout; node_layout.expand_upstream_horizontal()"
)
layout_menu.addCommand(
    'Expand Upstream Vertical', "import node_layout; node_layout.expand_upstream_vertical()"
)
layout_menu.addCommand(
    'Repeat Last Scale',
    "import node_layout; node_layout.repeat_last_scale()",
    'ctrl+/',
    shortcutContext=2,
)

layout_menu.addSeparator()

layout_menu.addCommand(
    "Sort By Filename", "import util; util.sort_by_filename()", shortcutContext=2,
)
layout_menu.addCommand(
    "Select Upstream Ignoring Hidden",
    "import util; util.select_upstream_ignoring_hidden()",
    "E",
    shortcutContext=2,
)
layout_menu.addCommand(
    "Select Hidden Outputs",
    "import util; util.select_hidden_outputs()",
    shortcutContext=2,
)

layout_menu.addSeparator()

layout_menu.addCommand(
    "Make Room Above", "import make_room; make_room.make_room()", "[", shortcutContext=2,
)
layout_menu.addCommand(
    "Make Room Below",
    "import make_room; make_room.make_room(direction='down')",
    "]",
    shortcutContext=2,
)

layout_menu.addCommand(
    "Make Room Above (smaller)",
    "import make_room; make_room.make_room(amount=800)",
    "Ctrl+[",
    shortcutContext=2,
)
layout_menu.addCommand(
    "Make Room Below (smaller)",
    "import make_room; make_room.make_room(amount=800, direction='down')",
    "Ctrl+]",
    shortcutContext=2,
)

layout_menu.addCommand(
    "Make Room Left",
    "import make_room; make_room.make_room(amount=800, direction='left')",
    "{",
    shortcutContext=2,
)
layout_menu.addCommand(
    "Make Room Right",
    "import make_room; make_room.make_room(amount=800, direction='right')",
    "}",
    shortcutContext=2,
)

layout_menu.addSeparator()

layout_menu.addCommand(
    'Freeze Selected',
    "import node_layout; node_layout.freeze_selected()",
    'ctrl+shift+f',
    shortcutContext=2,
)
layout_menu.addCommand(
    'Unfreeze Selected',
    "import node_layout; node_layout.unfreeze_selected()",
    'ctrl+shift+u',
    shortcutContext=2,
)

layout_menu.addSeparator()
layout_menu.addCommand(
    "Node Layout Preferences\u2026",
    "import node_layout_prefs_dialog; node_layout_prefs_dialog.show_prefs_dialog()",
)
