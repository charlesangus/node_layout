---
phase: 16-layout-integration
verified: 2026-03-20T05:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 5/5
  note: "Previous verification predated Plans 03 and 04 (5 UAT gap-closure fixes). This re-verification covers all four plans."
  gaps_closed:
    - "Non-frozen upstream nodes unreachable through excluded freeze block members are now repositioned via second-pass BFS (Gap 1 / Plan 04 Change B)"
    - "layout_selected node_filter type mismatch fixed — set comprehension with id() now correctly excludes non-root members (Gaps 2+3 / Plan 04 Change A)"
    - "make_room import added to menu.py — Make Room commands no longer crash with NameError (Gap 4 / Plan 03)"
    - "Frozen nodes skipped as horizontal BFS replay roots in both layout_upstream and layout_selected (Gap 5 / Plan 04 Change C)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Freeze two nodes in a chain. Run Layout Upstream on a downstream node. Confirm frozen nodes did not move relative to each other; non-frozen upstream nodes above the block were repositioned above it."
    expected: "Frozen block stays rigid. Non-frozen upstreams (including those only reachable through excluded non-root members) appear above the block at correct spacing."
    why_human: "Requires a running Nuke session with live DAG positioning; place_subtree interaction with real nodes cannot be verified statically."
  - test: "Insert an unfrozen node B between two frozen nodes A and C (same group). Run Layout Selected. Read the freeze_group knob on B."
    expected: "B's freeze_group UUID matches A and C. B moves with the block."
    why_human: "Requires live Nuke node manipulation to confirm knob state was written by the auto-join path."
  - test: "Mark some nodes horizontal (Layout Selected Horizontal). Freeze a subset overlapping the horizontal spine. Run layout. Inspect whether the frozen nodes are treated as a rigid block rather than as horizontal spine members."
    expected: "Frozen nodes excluded from horizontal spine walk; freeze membership overrides stored mode=horizontal."
    why_human: "Requires live Nuke session; spine-walk behavior with mixed frozen/horizontal nodes cannot be exercised through the unit-test stub framework."
  - test: "Invoke any of the six Make Room commands (Above, Below, Left, Right, Above Smaller, Below Smaller) from the Nuke menu."
    expected: "Commands execute without NameError; nodes shift as expected."
    why_human: "Requires Nuke to evaluate the addCommand string expressions at menu invocation time."
---

# Phase 16: Layout Integration Verification Report

**Phase Goal:** Integrate freeze group preprocessing and rigid block positioning into layout_upstream and layout_selected; freeze-aware push-away; frozen block treated as rigid unit during layout
**Verified:** 2026-03-20T05:00:00Z
**Status:** passed
**Re-verification:** Yes — after Plans 03 and 04 gap closure (previous verification predated those plans)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Freeze group preprocessing detects all freeze groups before any node positioning begins | VERIFIED | `_detect_freeze_groups` called at lines 1670 (layout_upstream) and 2208 (layout_selected), inside `with current_group:` blocks, before any `place_subtree` or `find_selection_roots` call |
| 2 | A node topologically inserted between two frozen nodes in the same group auto-joins at crawl time | VERIFIED | Iterative BFS loop in `_detect_freeze_groups` (lines 1512–1603); `write_freeze_group` called at line 1583 for auto-join; 3 `TestFreezeAutoJoin` tests pass |
| 3 | Two different freeze groups bridged by an inserted node are merged into a single group with a new UUID | VERIFIED | Merge path uses `str(uuid.uuid4())` at line 1592; `test_bridging_node_merges_two_groups` and `test_merge_persists_via_write_freeze_group` pass |
| 4 | Frozen block is positioned as a unit: root placed by layout algorithm, other members repositioned via relative offsets | VERIFIED | `freeze_excluded_ids` correctly removes non-root members via id()-based set comprehension in both entry points (layout_upstream line 2027–2031, layout_selected line 2228); offsets captured before and applied after `place_subtree`; all `TestFreezeBlockPositioning` tests pass |
| 5 | Push-away treats a frozen block's full bounding box as a single rigid obstacle; entire block shifts as a unit | VERIFIED | `push_nodes_to_make_room` extended with `freeze_block_map` and `freeze_groups` params (line 1347); `already_translated_blocks` guard at lines 1370, 1385, 1403, 1417, 1422; block bbox used for overlap; called from layout_upstream (lines 2167–2168) and layout_selected (lines 2718–2719); all `TestFreezeBlockPush` tests pass |
| 6 | Non-frozen nodes upstream of a frozen block are repositioned above the anchored block | VERIFIED | Second-pass BFS after offset restoration in layout_upstream (lines 2063–2140) and layout_selected (lines 2618–2700); `test_non_frozen_upstream_nodes_repositioned_after_freeze_block` passes |
| 7 | layout_selected non-root freeze member exclusion from node_filter uses id()-based set comprehension (not object-level set difference) | VERIFIED | Line 2228: `node_filter = {n for n in node_filter if id(n) not in freeze_excluded_ids}`; `test_layout_selected_excludes_non_root_members_from_filter` confirms broken `-=` vs correct comprehension; `test_frozen_block_moves_as_unit_in_layout_selected` confirms block rigidity |
| 8 | Frozen nodes are skipped as candidates when BFS searches for a horizontal replay root | VERIFIED | Freeze guard at line 1751 in layout_upstream BFS and line 2283 in layout_selected BFS; guard continues traversal through frozen nodes without rebinding root; `test_frozen_node_not_used_as_horizontal_replay_root` passes |
| 9 | Make Room menu commands execute without NameError | VERIFIED | `import make_room` present at line 5 of menu.py; all six `addCommand` calls that reference `make_room.make_room(...)` now have the module in scope |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_freeze_layout.py` | Unit tests for all freeze layout behaviors | VERIFIED | 22 tests across 8 classes (TestFreezePreprocessing, TestFreezeAutoJoin, TestFreezeGroupMerge, TestFreezeScopeExpansion, TestFreezeBlockPositioning, TestFreezeBlockPush, TestGroupViewDotCreation, TestFreezeGapClosure); all 22 pass in 0.08s |
| `node_layout.py` — `_detect_freeze_groups` | Freeze group detection with auto-join and merge | VERIFIED | Defined at line 1484; substantive 120-line two-pass BFS algorithm; reads and writes `node_layout_state` state |
| `node_layout.py` — `_expand_scope_for_freeze_groups` | Partial selection scope expansion | VERIFIED | Defined at line 1606; scans `current_group.nodes()` with `nuke.allNodes()` fallback |
| `node_layout.py` — `_find_freeze_block_root` | Most-downstream node identification for block anchoring | VERIFIED | Defined at line 1456; uses `max(ypos())` tiebreaker |
| `node_layout.py` — `push_nodes_to_make_room` freeze params | Rigid block push-away | VERIFIED | `freeze_block_map=None, freeze_groups=None` in signature at line 1347; `already_translated_blocks` set at line 1370 |
| `node_layout.py` — `layout_upstream` integration | Preprocessing + rigid positioning + second-pass + push | VERIFIED | Preprocessing at lines 1669–1670; offset setup at lines 1675–1687; second-pass BFS at lines 2063–2140; push call with freeze params at lines 2167–2168; offset restoration before second pass |
| `node_layout.py` — `layout_selected` integration | Preprocessing + id()-based filter + scope expansion + second-pass + push | VERIFIED | Preprocessing at lines 2205–2208; id()-based filter at line 2228; second-pass BFS at lines 2618–2700; push call with freeze params at lines 2718–2719 |
| `menu.py` — `import make_room` | Make Room commands importable | VERIFIED | `import make_room` at line 5; six `addCommand` calls at lines 87–119 all reference `make_room.make_room(...)` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `node_layout.py::_detect_freeze_groups` | `node_layout_state.read_freeze_group` | reads UUID from each node in scope | WIRED | Line 1507 inside Pass 1 scan loop |
| `node_layout.py::_detect_freeze_groups` | `node_layout_state.write_freeze_group` | persists auto-join and merge UUIDs | WIRED | Lines 1583 (auto-join) and 1598 (merge) |
| `node_layout.py::layout_upstream` | `_detect_freeze_groups` | called inside undo group before positioning | WIRED | Line 1670, inside `with current_group:` |
| `node_layout.py::layout_selected` | `_detect_freeze_groups` | called inside undo group before positioning | WIRED | Line 2208, inside `with current_group:` |
| `node_layout.py::layout_upstream` | `_find_freeze_block_root` | identifies root for each freeze block | WIRED | Line 1679 in freeze block setup loop |
| `node_layout.py::layout_selected` | `_find_freeze_block_root` | identifies root for each freeze block | WIRED | Line 2216 in freeze block setup loop |
| `node_layout.py::layout_upstream` | `freeze_relative_offsets` | captures member offsets before placement, applies after | WIRED | Captured lines 1683–1684; applied after offset restoration |
| `node_layout.py::layout_selected` | `freeze_relative_offsets` | captures member offsets before placement, applies after | WIRED | Captured lines 2220–2224; applied at lines 2608–2614 |
| `node_layout.py::push_nodes_to_make_room` | `freeze_block_map` | new parameter for block-aware push translation | WIRED | Signature line 1347; used in per-node loop at line 1381 |
| `node_layout.py::push_nodes_to_make_room` | `already_translated_blocks` | guard set preventing double-translation | WIRED | Declared line 1370; checked line 1385; set lines 1403, 1417, 1422 |
| Freeze membership guard | BFS horizontal replay root search | skips frozen candidates in both BFS loops | WIRED | Line 1751 (layout_upstream BFS), line 2283 (layout_selected BFS) |
| `layout_selected::node_filter` | `freeze_excluded_ids` | id()-based comprehension (Plan 04 Change A fix) | WIRED | Line 2228: `{n for n in node_filter if id(n) not in freeze_excluded_ids}` |
| `layout_upstream` second-pass | `upstream_non_frozen` BFS | repositions non-frozen nodes above anchored block | WIRED | Lines 2063–2140; BFS from block member inputs, calls `place_subtree` above block |
| `layout_selected` second-pass | `upstream_non_frozen` BFS + `scope_ids` guard | repositions non-frozen selected nodes above anchored block | WIRED | Lines 2618–2700; `scope_ids` restricts to selection scope |
| `menu.py` Make Room commands | `make_room` module | import resolves name at menu invocation | WIRED | `import make_room` at line 5; six addCommand string expressions reference it |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| FRZE-04 | 16-01-PLAN.md | Layout crawl runs preprocessing step detecting all freeze groups before any node positioning | SATISFIED | `_detect_freeze_groups` called as first operation inside undo group in both `layout_upstream` (line 1670) and `layout_selected` (line 2208), before any `place_subtree` or `find_selection_roots` |
| FRZE-05 | 16-01-PLAN.md | Nodes topologically inserted between frozen nodes auto-join the freeze group at crawl time only | SATISFIED | Iterative BFS auto-join loop in `_detect_freeze_groups`; 3 auto-join tests pass; `write_freeze_group` persists membership; no real-time callbacks |
| FRZE-06 | 16-02-PLAN.md, 16-04-PLAN.md | Layout positions frozen block as a unit — root placed by algorithm, other members repositioned to maintain relative offsets | SATISFIED | id()-based set comprehension at line 2228 correctly excludes non-root members; offset restoration after `place_subtree` in both entry points; `test_relative_offsets_preserved` and `test_frozen_block_moves_as_unit_in_layout_selected` confirm correct behavior |
| FRZE-07 | 16-02-PLAN.md, 16-03-PLAN.md, 16-04-PLAN.md | Push-away treats frozen block's bounding box as single rigid obstacle; entire block shifts as unit | SATISFIED | `push_nodes_to_make_room` uses `compute_node_bounding_box(freeze_groups[block_uuid])` for overlap check; `already_translated_blocks` prevents double-translation; both push call sites pass freeze params; `import make_room` in menu.py unblocks all six Make Room commands |

No orphaned requirements — REQUIREMENTS.md traceability table lists FRZE-04 through FRZE-07 as Phase 16, all accounted for.

### Anti-Patterns Found

None. Scan of all new freeze code sections in `node_layout.py`, `tests/test_freeze_layout.py`, and `menu.py` found no TODO/FIXME/placeholder comments, no empty implementations, and no stub return values.

### Human Verification Required

#### 1. Freeze block rigidity and upstream repositioning in live Nuke session

**Test:** Freeze two nodes (A, B) in a chain. Wire a non-frozen node C upstream of B. Run Layout Upstream on a downstream node. Inspect the DAG after layout.
**Expected:** A and B maintain their original relative positions. C is repositioned above B at correct spacing (second-pass BFS placed it above the anchored block).
**Why human:** Requires a running Nuke session with real nodes; `place_subtree` interaction with live DAG positioning and the second-pass BFS cannot be verified statically.

#### 2. Auto-join with a newly inserted node in live Nuke session

**Test:** Freeze nodes A and C in the same group. Insert node B between them (wire A -> B -> C). Run layout. Read the `layout_state` knob on B.
**Expected:** B's freeze group UUID matches A and C (auto-join occurred at crawl time).
**Why human:** Requires live Nuke node manipulation to verify the knob state was written correctly.

#### 3. Frozen node does not become horizontal replay root in live Nuke session

**Test:** Mark some nodes as horizontal mode (Layout Selected Horizontal). Freeze a subset overlapping the horizontal spine. Run layout.
**Expected:** Frozen nodes are treated as a rigid block, not as part of the horizontal spine. Horizontal spine walk stops at frozen node boundaries.
**Why human:** Requires live Nuke session; interaction between frozen state knobs and horizontal mode knobs on real nodes.

#### 4. Make Room commands execute without NameError in live Nuke session

**Test:** Invoke any of the six Make Room commands (Above, Below, Left, Right, Above Smaller, Below Smaller) from the Nuke Edit > Node Layout menu or via keyboard shortcut.
**Expected:** Commands execute without NameError; nodes shift as expected.
**Why human:** Requires Nuke to evaluate the `addCommand` string expressions at menu invocation time — only verifiable in a live session.

### Gaps Summary

No gaps. All 9 observable truths verified, all 8 artifacts confirmed substantive and wired, all 15 key links active, all 4 requirements satisfied. Full test suite 335/335 passing with no regressions. The 5 UAT gaps from the original post-Plans-01-02 UAT have been closed by Plans 03 and 04.

---

_Verified: 2026-03-20T05:00:00Z_
_Verifier: Claude (gsd-verifier)_
