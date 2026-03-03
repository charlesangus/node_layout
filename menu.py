import nuke
import node_layout
import make_room
import util


m = nuke.menu("Nuke")
edit = m.findItem("Edit")
layout_menu = edit.addMenu("Node Layout")

layout_menu.addCommand(
    'Layout Upstream',
    node_layout.layout_upstream,
    'shift+e',
    shortcutContext=2,
)
layout_menu.addCommand('Layout Selected', node_layout.layout_selected)

layout_menu.addSeparator()

layout_menu.addCommand("Sort By Filename", "util.sort_by_filename()", shortcutContext=2,)
layout_menu.addCommand("Select Upstream Ignoring Hidden", "util.select_upstream_ignoring_hidden()", "E", shortcutContext=2,)

layout_menu.addSeparator()

layout_menu.addCommand("Make Room Above", "make_room.make_room()", "[", shortcutContext=2,)
layout_menu.addCommand("Make Room Below", "make_room.make_room(direction='down')", "]", shortcutContext=2,)

layout_menu.addCommand("Make Room Above (smaller)", "make_room.make_room(amount=800)", "Ctrl+[", shortcutContext=2,)
layout_menu.addCommand("Make Room Below (smaller)", "make_room.make_room(amount=800, direction='down')", "Ctrl+]", shortcutContext=2,)

layout_menu.addCommand("Make Room Left", "make_room.make_room(amount=800, direction='left')", "{", shortcutContext=2,)
layout_menu.addCommand("Make Room Right", "make_room.make_room(amount=800, direction='right')", "}", shortcutContext=2,)
