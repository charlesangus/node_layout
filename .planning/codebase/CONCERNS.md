# Codebase Concerns

**Analysis Date:** 2026-03-03

## Tech Debt

**Global toolbar folder map caching:**
- Issue: `_TOOLBAR_FOLDER_MAP` is cached globally in `node_layout.py` (lines 3, 14-29). Once built, it never updates even if Nuke's node menus change during the session. This could cause stale categorization of nodes if plugins are loaded dynamically or menu configurations change after initial layout.
- Files: `node_layout.py` (lines 3, 25-29)
- Impact: Nodes added after first layout operation may not be recognized in toolbar folder comparisons, leading to incorrect spacing decisions (should be tight but gets loose, or vice versa).
- Fix approach: Either invalidate cache on demand, or retrieve fresh toolbar folder map per layout operation. Could also add a way to manually invalidate the cache if Nuke plugins are loaded.

**Generic exception handling in color/preference lookups:**
- Issue: Two bare `except Exception` blocks (lines 46-49 and 91-95 in `node_layout.py`) that catch all exceptions when querying Nuke preferences. These masks unexpected failures and makes debugging harder.
- Files: `node_layout.py` (lines 46-49, 91-95)
- Impact: If preferences are corrupted or unavailable, the code silently fails to fallback correctly. Errors in `find_node_default_color()` or `get_dag_snap_threshold()` won't be logged or reported to user.
- Fix approach: Catch specific exceptions (`KeyError`, `AttributeError`) instead of generic `Exception`. Log failures for debugging. Document expected fallback behavior.

**Print statement left in production code:**
- Issue: `print(start_location)` in `util.py` line 13 (`sort_by_filename()` function) is debug output that should be removed or converted to proper logging.
- Files: `util.py` (line 13)
- Impact: Clutters console output during normal operation. Not a functional bug, but unprofessional and could hide other important output.
- Fix approach: Remove the print statement or replace with proper logging if diagnostics are needed.

**Bare variable comparison with None:**
- Issue: `util.py` line 26 uses `nodes_so_far == None` instead of `nodes_so_far is None`. While functionally equivalent, it violates PEP 8 style.
- Files: `util.py` (line 26)
- Impact: Minor code style inconsistency; no functional impact but reduces code quality and consistency.
- Fix approach: Change `== None` to `is None` per PEP 8.

## Known Bugs

**make_room() direction variable scope issue:**
- Symptoms: When calling `make_room()` with `direction='left'` or `direction='right'`, the `y_amount` and `x_amount` variables may be uninitialized if neither the "up"/"down" nor "left"/"right" conditions match (e.g., invalid direction string passed).
- Files: `make_room.py` (lines 5-20)
- Trigger: Call `make_room(direction='invalid')` or similar with unrecognized direction.
- Workaround: Only call with documented directions ('up', 'down', 'left', 'right'). Currently no validation of direction parameter.
- Fix approach: Add explicit initialization of `x_amount = 0; y_amount = 0` at the start, or add validation to raise error on invalid direction.

**Node filter may reference deleted nodes:**
- Symptoms: In `layout_selected()`, `node_filter` is created as a set of node IDs (line 559). If nodes are deleted externally or garbage collected between filter creation and `place_subtree()` calls, the filter contains stale object IDs with no corresponding nodes.
- Files: `node_layout.py` (lines 554-591)
- Trigger: Rare race condition; unlikely in normal use but possible if external code deletes selected nodes during layout operation.
- Workaround: Ensure no external deletion happens during `layout_selected()` execution.
- Fix approach: Store node objects directly in filter instead of IDs, or validate filter references before using them.

## Security Considerations

**No input validation on node operations:**
- Risk: Functions like `layout_upstream()` and `layout_selected()` assume selected nodes exist and are valid. No validation that nodes are safe to manipulate (e.g., checking for read-only or locked nodes).
- Files: `node_layout.py` (lines 521-591)
- Current mitigation: Nuke itself manages node locking; unlikely to be an issue in practice.
- Recommendations: Add explicit checks for node state before modifying. Document assumption that nodes are user-selected and therefore safe to manipulate.

**No bounds checking on DAG coordinates:**
- Risk: Node coordinates can be set to arbitrary values. Very large coordinate values could cause memory issues or rendering problems in Nuke's DAG view.
- Files: All position-setting calls in `node_layout.py`, `make_room.py`
- Current mitigation: Positions derived from existing node positions, so stays within reasonable bounds.
- Recommendations: Consider adding sanity checks if external tools are integrated that could provide arbitrary coordinates.

## Performance Bottlenecks

**Full DAG traversal in push_nodes_to_make_room():**
- Problem: `push_nodes_to_make_room()` calls `nuke.allNodes()` (line 487) which iterates every node in the DAG, even when only a small subset is affected. For large DAGs (100+ nodes), this becomes noticeably slow.
- Files: `node_layout.py` (lines 474-518)
- Cause: Brute-force check of every node against bounding boxes.
- Improvement path: Cache nearby nodes or use spatial indexing. For now, acceptable for typical DAG sizes (< 200 nodes).

**Repeated preference lookups:**
- Problem: `find_node_default_color()` (lines 52-60) scans all preference knobs twice (once for color slots, once for color choices) on every call. For large preference lists, this is slow. Called for every node in tree.
- Files: `node_layout.py` (lines 52-60)
- Cause: Preference introspection is expensive; no memoization across multiple node color lookups.
- Improvement path: Cache preference structure once per layout operation, or memoize color lookups by node class.

**Recursive upstream selection creates O(n²) work:**
- Problem: `upstream_ignoring_hidden()` in `util.py` (lines 21-32) recursively walks upstream and checks membership in `nodes_so_far` set repeatedly. For deeply nested graphs, set membership checks accumulate.
- Files: `util.py` (lines 21-32)
- Cause: Set updates on every recursive call; inefficient for deep chains.
- Improvement path: Not a bottleneck for typical Nuke graphs, but could be optimized with iterative approach if needed.

## Fragile Areas

**Diamond resolution and mask path ordering:**
- Files: `node_layout.py` (lines 184-236, 107-125)
- Why fragile: Complex logic that defers mask edges and claims non-mask paths first. Relies on specific order of DFS traversal and deferred queue processing. Changes to input slot order or node connection patterns can trigger unexpected Dot insertion.
- Safe modification: Test thoroughly with multi-input nodes that have both mask and non-mask paths to the same upstream node (true diamond patterns). Verify mask inputs still appear rightmost after any changes.
- Test coverage: No explicit unit tests for diamond resolution. Tested only through integration (manual DAG construction).

**Vertical gap calculation and mask input margin:**
- Files: `node_layout.py` (lines 41-42, 74-77, 103-104, 246, 361)
- Why fragile: `vertical_gap_between()` depends on both tile color AND toolbar category matching. If toolbar folder map is stale (see Tech Debt above), gaps will be wrong. Mask input margin is hardcoded as SUBTREE_MARGIN // 3; changing SUBTREE_MARGIN could break mask spacing.
- Safe modification: Test color+category matching independently. Ensure mask margin adjustment is proportional to SUBTREE_MARGIN, not a fixed pixel value. Validate toolbar folder caching is refreshed.
- Test coverage: Logic is deterministic but not covered by automated tests. Manual verification required.

**Bounding box overlap detection:**
- Files: `node_layout.py` (lines 474-518, 464-471)
- Why fragile: Overlap detection is based on AABB (axis-aligned bounding box) logic. Edge cases exist: nodes that share exact coordinates, nodes with zero-size bounding boxes, or nodes that are processed in certain orders may behave unexpectedly.
- Safe modification: Stress-test with nodes at same positions, very small/large nodes. Verify no nodes are pushed multiple times or into inconsistent states.
- Test coverage: Bounding box logic tested only indirectly through integration tests.

**Node filter logic with hidden Dot nodes:**
- Files: `node_layout.py` (lines 148-167, 199-236)
- Why fragile: `_passes_node_filter()` treats diamond-resolution Dots (with `hide_input=True`) as transparently matching their wrapped node. This is brittle because it assumes Dots created by `insert_dot_nodes()` are the only ones with `hide_input=True`. If user manually creates such Dots, filtering behavior becomes unpredictable.
- Safe modification: Add explicit marker (e.g., custom knob) to diamond-resolution Dots instead of relying on `hide_input` flag. Document that `hide_input` flag has special meaning in this codebase.
- Test coverage: Edge case not explicitly tested.

## Scaling Limits

**Linear DAG traversal for large graphs:**
- Current capacity: Works well up to ~500 nodes in typical workflows.
- Limit: Beyond 500 nodes, traversal time becomes noticeable (several seconds per layout operation). Collision detection (push_nodes_to_make_room) scales as O(n²) in worst case.
- Scaling path: Implement spatial hashing or quadtree for bounding box queries. Use iterative traversal instead of recursive. Cache dimension computations more aggressively.

**Memory usage for dimension memoization:**
- Current capacity: Memoization cache stores one tuple per node (efficient).
- Limit: Not a practical concern; memory usage is O(n) where n = nodes in graph.
- Scaling path: No action needed for typical use.

## Dependencies at Risk

**Nuke API dependency:**
- Risk: Code tightly coupled to Nuke's node.Class(), knobs, setXpos/setYpos, and menu APIs. Nuke major version changes could break compatibility.
- Impact: If Nuke significantly changes DAG API or knob system, extensive refactoring required.
- Migration plan: Monitor Nuke release notes. Abstract Nuke API calls into a compatibility layer if major version support needed. Current codebase assumes Nuke 11+.

**No explicit Nuke version check:**
- Risk: Code assumes availability of certain knobs (e.g., `dag_snap_threshold`, `tile_color`, `hide_input`) without checking Nuke version. Older versions may not have these.
- Impact: Silent failures or exceptions if run on older Nuke.
- Migration plan: Add Nuke version check at import time. Document minimum required version clearly.

## Missing Critical Features

**No undo/redo support:**
- Problem: Layout operations modify node positions directly without wrapping in Nuke undo group. If user presses Ctrl+Z, only the last position change undoes, not the entire layout operation.
- Blocks: Users cannot safely apply layout and undo if result is unsatisfactory.
- Fix approach: Wrap all layout operations in `nuke.Undo_Begin()` / `nuke.Undo_End()` to group changes into single undo action.

**No error dialogs for invalid selections:**
- Problem: `layout_upstream()` calls `nuke.selectedNode()` without checking selection. If no node is selected, Nuke raises exception with no user-facing message.
- Blocks: Users get cryptic error messages instead of "Please select a node first".
- Fix approach: Check selection count and raise user-friendly error message, or use nuke dialog to inform user.

**No keyboard shortcut conflict detection:**
- Problem: Menu shortcuts are hardcoded (Shift+E, E, [, ], {, }). If another plugin uses same shortcuts, behavior is undefined (depends on load order).
- Blocks: Potential for non-obvious conflicts with other plugins.
- Fix approach: Use unique namespaced shortcuts, or add preference to customize shortcuts at install time.

## Test Coverage Gaps

**No unit tests for core algorithms:**
- What's not tested: `compute_dims()`, `place_subtree()`, `insert_dot_nodes()` are complex algorithms with no isolated unit tests. Only tested through end-to-end DAG manipulation.
- Files: `node_layout.py` (entire core logic)
- Risk: Refactoring is dangerous. Edge cases in dimension calculation or placement logic go undetected until user runs command.
- Priority: **High** — Core algorithm correctness is critical.

**No tests for toolbar folder matching:**
- What's not tested: `same_toolbar_folder()` caching and menu introspection.
- Files: `node_layout.py` (lines 6-38)
- Risk: Stale cache bug won't be caught until user loads new plugins mid-session.
- Priority: **Medium** — Low probability but high impact if it occurs.

**No tests for edge cases in bounding box logic:**
- What's not tested: Overlapping nodes, nodes at exact same position, very large/small nodes.
- Files: `node_layout.py` (lines 464-518)
- Risk: Collision detection may fail silently in edge cases.
- Priority: **Medium** — Rare but affects correctness of surrounding node displacement.

**No integration tests with real Nuke:**
- What's not tested: Entire workflow cannot be tested without running Nuke. No CI pipeline.
- Files: All
- Risk: Regressions not caught until user reports them.
- Priority: **High** — Would require Nuke license and headless environment to set up.

**No tests for file sorting and upstream selection:**
- What's not tested: `sort_by_filename()` and `upstream_ignoring_hidden()` have no tests.
- Files: `util.py`
- Risk: Changes to file knob handling or dependency traversal break undetected.
- Priority: **Low** — Functions are simple and rarely modified.

---

*Concerns audit: 2026-03-03*
