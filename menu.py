import nuke
import node_layout
import make_room


m = nuke.menu("Nuke")

m.addCommand(
    'Edit/Node Layout/Layout Upstream',
    node_layout.layout_upstream,
    'shift+l',
    shortcutContext=2,
)

m.addCommand("Edit/Node Layout/Make Room Above", "make_room.make_room()", "[", shortcutContext=2,)
m.addCommand("Edit/Node Layout/Make Room Below", "make_room.make_room(direction='down')", "]", shortcutContext=2,)

m.addCommand("Edit/Node Layout/Make Room Above (smaller)", "make_room.make_room(amount=800)", "Ctrl+[", shortcutContext=2,)
m.addCommand("Edit/Node Layout/Make Room Below (smaller)", "make_room.make_room(amount=800, direction='down')", "Ctrl+]", shortcutContext=2,)

m.addCommand("Edit/Node Layout/Make Room Left", "make_room.make_room(direction='left')", "{", shortcutContext=2,)
m.addCommand("Edit/Node Layout/Make Room Right", "make_room.make_room(direction='right')", "}", shortcutContext=2,)
