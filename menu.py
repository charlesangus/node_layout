import nuke
import node_layout

nuke.menu('Nuke').addCommand(
    'Edit/Layout Upstream',
    node_layout.layout_upstream,
    'shift+l',
    shortcutContext=2,
)
