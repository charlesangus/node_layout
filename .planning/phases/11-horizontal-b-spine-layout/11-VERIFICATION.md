---
phase: 11-horizontal-b-spine-layout
verified: 2026-03-13T00:00:00Z
status: post-uat-fixes-applied
score: 10/10 code truths still hold; 3 behaviour fixes applied post-UAT-pause
re_verification: true
---

# Phase 11: Horizontal B-Spine Layout Verification Report

**Phase Goal:** Users can lay out a B-spine chain left-to-right, with the root node rightmost and each successive input(0) ancestor stepping left; this mode is stored in node state and replayed automatically by subsequent normal layout commands
**Verified:** 2026-03-12
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `tests/test_horizontal_layout.py` exists with 6 test classes and 10 test methods | VERIFIED | File exists at 569 lines; 10 tests ran and passed |
| 2 | `place_subtree_horizontal()` places root at spine_x, walks input[0] chain leftward | VERIFIED | Function at node_layout.py:403; TestHorizontalSpine 2/2 pass |
| 3 | Each spine node is step_x to the left of its downstream neighbor | VERIFIED | Two-pass algorithm in place_subtree_horizontal; test_two_node_spine_step_left passes |
| 4 | Side inputs (input[1+]) are placed above their spine node (lower Y) | VERIFIED | Lines 500-510 in node_layout.py; TestSideInputPlacement passes |
| 5 | Mask input on a spine node causes downstream spine nodes to drop by mask subtree height (cumulative kink) | VERIFIED | Kink accumulation logic at lines 470-490; TestMaskKink passes |
| 6 | `_find_or_create_output_dot()` places a Dot below root; reuses existing Dot on replay | VERIFIED | Function at node_layout.py:349; TestOutputDot 2/2 pass |
| 7 | `layout_upstream_horizontal()` and `layout_selected_horizontal()` exist as full entry points with undo wrapping | VERIFIED | Functions at lines 1148 and 1236; AST check confirms; TestHorizontalAST 3/3 pass |
| 8 | `layout_upstream()` and `layout_selected()` read stored mode and dispatch to horizontal path | VERIFIED | Dispatch branches at lines 950 and 1061; TestModeReplay passes |
| 9 | State write-back records `mode='horizontal'` on horizontal path | VERIFIED | Lines 971, 980 (layout_upstream); lines 1101-1108 (layout_selected); layout_upstream_horizontal at 1219; layout_selected_horizontal at 1309 |
| 10 | `compute_dims` memo key includes `layout_mode` to prevent cache collisions | VERIFIED | 5-tuple `(id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode)` at lines 521-522, 593 |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_horizontal_layout.py` | RED scaffold, 6 classes, 10 methods, >=200 lines | VERIFIED | 569 lines; 10 tests pass GREEN after implementation |
| `node_layout.py` | `place_subtree_horizontal`, `_find_or_create_output_dot`, `layout_upstream_horizontal`, `layout_selected_horizontal`, mode dispatch, compute_dims layout_mode param | VERIFIED | All 4 functions present; dispatch and memo key confirmed via AST |
| `menu.py` | `Layout Upstream Horizontal` and `Layout Selected Horizontal` commands | VERIFIED | Lines 29-30; both reference `node_layout.layout_upstream_horizontal` and `node_layout.layout_selected_horizontal` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_horizontal_layout.py` | `node_layout.py` | `spec_from_file_location("node_layout_horizontal", ...)` | VERIFIED | Line 208 of test file |
| `place_subtree_horizontal` | `vertical_gap_between`, `_subtree_margin`, `_center_x` | direct calls for side input/mask kink placement | VERIFIED | Lines 486, 506, 508 of node_layout.py |
| `_find_or_create_output_dot` | `nuke.nodes.Dot()` | knob check then conditional creation; `node_layout_output_dot` marker | VERIFIED | Line 379 reuse check; line 386 creation; `_OUTPUT_DOT_KNOB_NAME` constant at line 10 |
| `layout_upstream()` | `place_subtree_horizontal()` | `if root_mode == 'horizontal':` dispatch | VERIFIED | Lines 950-951 of node_layout.py |
| `layout_upstream()` | `node_layout_state.write_node_state()` | `stored_state["mode"] = layout_mode_to_write` conditional | VERIFIED | Lines 971, 980 — writes `"horizontal"` or `"vertical"` per path |
| `compute_dims` | memo dict | extended 5-tuple key `(id, scheme_multiplier, h_scale, v_scale, layout_mode)` | VERIFIED | Lines 521-522, 593 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| HORIZ-01 | 11-01, 11-02 | User can run "Layout Upstream Horizontal" — root rightmost, each input(0) ancestor steps left; output pipe extends downward | SATISFIED | `layout_upstream_horizontal()` at line 1148; `place_subtree_horizontal()` at line 403; `_find_or_create_output_dot()` at line 349; TestHorizontalSpine, TestOutputDot, TestMaskKink, TestSideInputPlacement all pass |
| HORIZ-02 | 11-01, 11-03 | User can run "Layout Selected Horizontal" — horizontal B-spine mode for selected nodes | SATISFIED | `layout_selected_horizontal()` at line 1236; registered in menu.py line 30; TestHorizontalAST (layout_selected_horizontal_exists) passes |
| HORIZ-03 | 11-01, 11-03 | Horizontal mode stored in node state; normal Layout Upstream/Selected replays horizontal automatically | SATISFIED | Mode dispatch in `layout_upstream()` at line 950 and `layout_selected()` at line 1061; state write-back writes `"horizontal"` conditionally; TestModeReplay passes |

No orphaned requirements found — all three HORIZ IDs from REQUIREMENTS.md are claimed by plans and verified in the codebase.

---

### Anti-Patterns Found

None. No TODO, FIXME, placeholder, or stub patterns detected in any of the modified files (`node_layout.py`, `menu.py`, `tests/test_horizontal_layout.py`).

---

### Human Verification Required

#### 1. Actual Nuke DAG visual layout

**Test:** Open Nuke, import a multi-node composite, select a node, run "Layout Upstream Horizontal"
**Expected:** Root node is rightmost; each successive input(0) ancestor steps to the left; side inputs appear above their spine node; a Dot appears below root connecting it to any downstream consumer
**Why human:** Test suite uses stub Nuke objects; actual Nuke DAG rendering, screen coordinates, and wire routing cannot be verified programmatically

#### 2. HORIZ-03 mode replay round-trip

**Test:** Run "Layout Upstream Horizontal" on a node, then run plain "Layout Upstream" on the same node
**Expected:** Plain "Layout Upstream" replays the horizontal layout automatically (reads mode='horizontal' from state and dispatches to horizontal path)
**Why human:** Requires live Nuke session with real state knobs; the stub tests verify the dispatch code path exists but cannot simulate a full round-trip through the real `node_layout_state` persistence layer

#### 3. Output Dot reuse across sessions

**Test:** Run "Layout Upstream Horizontal" twice in succession on a node that has a downstream consumer
**Expected:** Only one Dot is created below root after both runs; second run reuses the existing Dot rather than creating a second one
**Why human:** Requires the real `nuke.nodes.Dot()` factory and `knob()` introspection; stub test verifies the code path but real Nuke knob identity may behave differently

---

### Gaps Summary

No gaps. All 10 observable truths are verified. All 3 requirement IDs (HORIZ-01, HORIZ-02, HORIZ-03) are satisfied with direct implementation evidence. The full 10-test suite passes GREEN. No regressions were introduced — the 4 pre-existing errors in `test_scale_nodes_axis` (nuke stub missing `Undo` attribute, a known issue from Phase 10) remain unchanged and are not caused by Phase 11 changes.

---

_Verified: 2026-03-12_
_Verifier: Claude (gsd-verifier)_
