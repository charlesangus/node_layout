# External Integrations

**Analysis Date:** 2026-03-03

## APIs & External Services

**None detected.**

This is a standalone Nuke plugin with no external API integrations or third-party service calls.

## Data Storage

**Databases:**
- None - Plugin operates entirely within Nuke's in-memory DAG and does not persist data

**File Storage:**
- Local filesystem only - Plugin reads node file paths when sorting by filename (`util.sort_by_filename()` accesses the `file` knob on Read nodes), but does not write files

**Caching:**
- None - All operations work directly on Nuke's live node graph

## Authentication & Identity

**Auth Provider:**
- Not applicable - Plugin runs within Nuke's user session context with no separate authentication

## Monitoring & Observability

**Error Tracking:**
- None - Plugin uses basic try/except for error handling in specific locations like `get_dag_snap_threshold()` in `node_layout.py:46-49`

**Logs:**
- Print to console only - Limited debug output via `print()` in `util.sort_by_filename()` at `util.py:13`

## CI/CD & Deployment

**Hosting:**
- Local user machine or shared studio network path
- No remote hosting or deployment pipeline

**CI Pipeline:**
- Not applicable

## Environment Configuration

**Required env vars:**
- None

**Secrets location:**
- Not applicable - Plugin does not handle secrets

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Nuke-Specific Integration Points

**Menu System:**
Integration via Nuke's Edit menu:
- `nuke.menu('Nuke')` - Access to main Nuke menu (`menu.py:7`)
- `edit.addMenu('Node Layout')` - Creates submenu under Edit (`menu.py:9`)
- `layout_menu.addCommand()` - Registers commands with keyboard shortcuts (`menu.py:11-33`)

**DAG Manipulation:**
- `nuke.selectedNode()` - Get current selection for layout operations (`node_layout.py:522`)
- `nuke.selectedNodes()` - Get multiple selected nodes (`node_layout.py:555`)
- `nuke.allNodes()` - Access all nodes in graph for collision detection (`node_layout.py:487`)
- `nuke.nodes.Dot()` - Create Dot nodes for automatic diamond resolution (`node_layout.py:211`)
- `nuke.toNode('preferences')` - Read Nuke preferences for snap threshold and colors (`node_layout.py:47`)
- `nuke.createNode()` and `nuke.delete()` - Temporary node creation for cursor position detection (`make_room.py:26-28`)

**Node Properties:**
- `node.knob()` - Query node knobs (hide_input, tile_color, maskChannel, file) throughout codebase
- `node.input()`, `node.inputs()` - Query node connections
- `node.setInput()` - Modify connections
- `node.xpos()`, `node.ypos()` - Query/set node positions
- `node.screenWidth()`, `node.screenHeight()` - Query node dimensions
- `node.Class()` - Get node type for logic decisions

---

*Integration audit: 2026-03-03*
