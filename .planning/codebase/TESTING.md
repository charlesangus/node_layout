# Testing Patterns

**Analysis Date:** 2026-03-03

## Test Framework

**Runner:**
- Not detected - No test framework present in codebase

**Assertion Library:**
- Not applicable

**Run Commands:**
- Not applicable - No test suite exists

## Test Coverage Status

**Current State:** No automated tests present

**Coverage:** Not applicable

## Why No Tests

This is a Nuke plugin codebase with inherent testing challenges:

1. **Nuke API Dependency:** Core functionality depends on the Nuke Python API (`nuke` module), which is only available within Nuke itself. Functions like `nuke.selectedNode()`, `nuke.selectedNodes()`, `nuke.allNodes()` require a running Nuke instance.

2. **GUI State Dependency:** Functions interact with Nuke's DAG (directed acyclic graph) which represents the visual node network. Testing requires:
   - A Nuke instance
   - A loaded project or script
   - Nodes with specific properties (colors, input connections, knobs)
   - Nuke menu system availability

3. **No Mock/Stub Pattern:** The codebase does not use mocking or stubbing, and the tight coupling to Nuke's C++ API makes this difficult.

## Manual Testing Approach

The codebase relies on manual testing within Nuke:

**Testing Commands via Nuke UI:**
- Commands registered in Nuke's Edit menu can be invoked manually
- Visual inspection of node layout results validates correctness
- Testing typically involves:
  1. Creating a node graph with specific patterns
  2. Selecting nodes and invoking layout commands
  3. Verifying positioning, spacing, and dot insertion matches expected behavior

**Key Test Scenarios (Manual):**

**Layout Upstream (`Shift+E`):**
- Single input: node placed directly above
- Two inputs: primary above, secondary to the right
- Three+ inputs: primary above, secondaries stepped rightward
- Mask inputs detected and placed rightmost
- Color-aware spacing (tight for matching colors, loose otherwise)
- Diamond patterns resolved with Dot insertion
- Surrounding nodes pushed when subtree grows

**Layout Selected:**
- Multiple selected nodes relative to each other
- Upstream filtering (only selected nodes and their connections)
- Horizontal spacing when subtrees overlap vertically
- Dot insertion for side inputs within selection

**Make Room:**
- Directional movement (up/down/left/right)
- Amount variations (1600px standard, 800px smaller)
- With selection: only selected nodes move
- Without selection (up/down): all nodes above/below cursor move

**Select Upstream Ignoring Hidden:**
- Traverses visible connections
- Respects hidden input flags (`hide_input=True`)
- Selects entire upstream dependency chain

**Sort By Filename:**
- Finds nodes with `file` knob
- Sorts alphabetically by file path
- Arranges in horizontal line

## Testable Functionality

The following functions are theoretically testable with Nuke mocks or within Nuke itself:

**Core Algorithm Functions** (Pure logic, minimal Nuke API):
- `_is_mask_input(node, i)` - Input classification logic
- `_hides_inputs(node)` - Input hiding detection
- `_passes_node_filter(node, node_filter)` - Filter matching logic
- `_reorder_inputs_mask_last(input_slot_pairs, node, all_side)` - Input reordering
- `compute_dims(node, memo, snap_threshold, node_filter)` - Dimension calculation (with mock node objects)
- `vertical_gap_between(top_node, bottom_node, snap_threshold)` - Gap calculation logic
- `same_tile_color(node_a, node_b)` - Color comparison (with mock nodes)
- `same_toolbar_folder(node_a, node_b)` - Toolbar category comparison (with mock nodes)

**Geometry Functions** (Pure math):
- `compute_node_bounding_box(nodes)` - Bounding box calculation (testable with mock nodes)
- Positioning calculations within `place_subtree()` and `layout_upstream()`

**Graph Traversal** (with Nuke API calls):
- `insert_dot_nodes(root, node_filter)` - Creates nodes; requires Nuke instance
- `collect_subtree_nodes(root, node_filter)` - Traverses graph; requires Nuke instance

**Main Entry Points** (Requires Nuke):
- `layout_upstream()` - Orchestrates the full layout process
- `layout_selected()` - Multi-root layout orchestration

## Recommended Testing Strategy

**For Future Test Implementation:**

1. **Unit Test Possibility:**
   - Create mock node objects that implement the Nuke node interface
   - Test pure logic functions independently: `_is_mask_input()`, `_passes_node_filter()`, gap calculations
   - Test positioning math without requiring a Nuke instance

2. **Integration Testing:**
   - Create a Nuke plugin test harness that:
     - Launches Nuke in headless mode (if possible)
     - Creates test node graphs programmatically
     - Invokes layout functions
     - Validates final positions and connections
   - Example test patterns could verify:
     - Correct node counts after Dot insertion
     - Bounding box dimensions match computed values
     - Spacing matches configured margins

3. **Manual Test Checklist:**
   - Maintain a markdown checklist of scenarios to test manually before release
   - Document expected outputs for various node graph patterns
   - Include edge cases: single node, circular references (with diamonds), many inputs, mask-only inputs

## Code Quality without Tests

Despite lacking automated tests, the code demonstrates quality through:

1. **Clear Intent:** Function names express exactly what they do
2. **Documented Algorithms:** Complex logic sections have detailed comments explaining strategy
3. **Defensive Programming:** Checks for None values, missing knobs, empty lists before operating on them
4. **Graceful Degradation:** Exception handling provides sensible defaults (e.g., `get_dag_snap_threshold()` returns 8 if preferences unavailable)
5. **Encapsulation:** Helper functions are private (underscore-prefixed), limiting public API surface
6. **Modularity:** Each file has focused responsibility, reducing coupling

## Testing Challenges Specific to Nuke Plugins

1. **C++ Bridge:** Nuke's Python API bridges to C++ implementations; behavior may differ across versions
2. **State Persistence:** Nuke maintains mutable scene state; tests would need careful setup/teardown
3. **No Standard Test Framework:** Unlike standalone Python projects, Nuke plugins don't use unittest/pytest without special setup
4. **Version Compatibility:** Plugin targets Nuke 11.x+; testing against multiple versions requires multiple Nuke installations

---

*Testing analysis: 2026-03-03*
