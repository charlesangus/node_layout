---
phase: 11-horizontal-b-spine-layout
verified: 2026-03-15T17:00:00Z
status: passed
score: 13/13 truths verified
re_verification:
  previous_status: post-uat-fixes-applied
  previous_score: 10/10 (initial) + 3 behaviour fixes applied post-UAT pause
  gaps_closed:
    - "id()-based identity in _place_output_dot_for_horizontal_root — no duplicate Dot on replay"
    - "Right-of-consumer horizontal anchor in layout_upstream (screenWidth + horizontal_gap formula)"
    - "Right-of-consumer horizontal anchor in layout_selected (same formula, original_selected_root save)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run 'Layout Selected Horizontal' on a chain, scramble, select a downstream node, run 'Layout Upstream'"
    expected: "Horizontal chain appears to the RIGHT of the downstream node at the same Y level — not above it"
    why_human: "Requires live Nuke session with real proxy wrapper objects; the id() fix and anchor formula are verified by code inspection and AST tests, but the actual on-screen result can only be confirmed in Nuke"
  - test: "Run 'Layout Selected Horizontal' twice on the same chain"
    expected: "Only one output Dot exists below root after both runs — no duplicate created"
    why_human: "Requires real Nuke knob introspection; stub tests confirm the id()-based detection path but real Nuke proxy wrapper identity may differ from CPython object identity"
  - test: "Run 'Layout Selected Horizontal (Place Only)', scramble, run 'Layout Upstream' on a downstream node"
    expected: "Horizontal replay fires and places chain to the right of the downstream node"
    why_human: "Confirms Place Only writes mode='horizontal' and the downstream anchor formula works end-to-end in a live Nuke session"
---

# Phase 11: Horizontal B-Spine Layout Verification Report

**Phase Goal:** Users can lay out a B-spine chain left-to-right, with the root node rightmost and each successive input(0) ancestor stepping left; this mode is stored in node state and replayed automatically by subsequent normal layout commands
**Verified:** 2026-03-15
**Status:** PASSED
**Re-verification:** Yes — re-verification after plan-05 gap closure (duplicate Dot fix and downstream anchor formula fix)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `place_subtree_horizontal()` exists, places root at spine_x, walks input(0) chain leftward | VERIFIED | Function at node_layout.py:513; TestHorizontalSpine passes |
| 2 | Each spine node is step_x to the left of its downstream neighbor | VERIFIED | Two-pass algorithm in place_subtree_horizontal; test_two_node_spine_step_left passes |
| 3 | Side inputs (input[1+]) are placed above their spine node (lower Y) | VERIFIED | node_layout.py side-input block; TestSideInputPlacement passes |
| 4 | Mask input on a spine node causes downstream spine nodes to drop by mask subtree height | VERIFIED | Kink accumulation logic in place_subtree_horizontal; TestMaskKink passes |
| 5 | `_find_or_create_output_dot()` places a Dot below root; `_place_output_dot_for_horizontal_root()` orchestrates it | VERIFIED | Functions at node_layout.py:350 and 413; TestOutputDot 2/2 pass |
| 6 | `_place_output_dot_for_horizontal_root` uses id() comparisons with is-not-None guards — no duplicate Dot on replay | VERIFIED | Lines 449 and 453: `node.input(x) is not None and id(node.input(x)) == id(root)`; TestPlaceOutputDotForHorizontalRootReplay 2/2 pass |
| 7 | `layout_selected_horizontal()` and `layout_selected_horizontal_place_only()` exist as full entry points with undo wrapping | VERIFIED | Functions at node_layout.py:1649 and 1663; TestHorizontalAST 3/3 pass |
| 8 | Both entry points call `_place_output_dot_for_horizontal_root` after `place_subtree_horizontal` | VERIFIED | Line 1623 in `_layout_selected_horizontal_impl`; `_place_output_dot_for_horizontal_root` call present |
| 9 | `layout_upstream()` and `layout_selected()` read stored mode and dispatch to horizontal path | VERIFIED | Dispatch branches at lines 1296 and 1459; TestModeReplay passes |
| 10 | When BFS ancestor walk rebinds root in layout_upstream, chain is placed RIGHT of downstream consumer: `spine_x = original_selected_root.xpos() + original_selected_root.screenWidth() + horizontal_gap` | VERIFIED | Lines 1313-1316; TestDownstreamReplayAnchor 3/3 pass |
| 11 | When BFS ancestor walk rebinds root in layout_selected, same right-of-consumer formula applied via original_selected_root save | VERIFIED | `original_selected_root = root` at line 1428; anchor block at lines 1474-1477 |
| 12 | State write-back records mode='horizontal' on spine nodes on both horizontal paths (recursive and place_only) | VERIFIED | Lines 1352-1353 (layout_upstream); line 1635 (_layout_selected_horizontal_impl, unconditional) |
| 13 | `compute_dims` memo key includes layout_mode as 5th element to prevent cache collisions | VERIFIED | 5-tuple `(id(node), scheme_multiplier, node_h_scale, node_v_scale, layout_mode)` at lines 833-834 |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `node_layout.py` | `place_subtree_horizontal`, `_find_or_create_output_dot`, `_place_output_dot_for_horizontal_root`, `layout_selected_horizontal`, `layout_selected_horizontal_place_only`, mode dispatch, id()-based identity, right-of-consumer anchor, compute_dims layout_mode param | VERIFIED | All functions present at confirmed line numbers; all key patterns confirmed via grep |
| `menu.py` | Horizontal layout commands registered | VERIFIED | Lines 29-30: `Layout Selected Horizontal` and `Layout Selected Horizontal (Place Only)`; both reference `node_layout.layout_selected_horizontal` and `node_layout.layout_selected_horizontal_place_only` |
| `tests/test_horizontal_layout.py` | 24 tests covering spine, output dot, mask kink, side input, mode replay, downstream anchor, output dot replay | VERIFIED | 24 tests, all pass GREEN (Ran 24 tests in 0.055s — OK) |

#### Architecture note: layout_upstream_horizontal

Plan 03 originally created a standalone `layout_upstream_horizontal()` function and registered `Layout Upstream Horizontal` in menu.py. This was removed in the post-UAT redesign (after the initial UAT in 11-UAT.md identified gaps). The redesigned architecture delivers HORIZ-01 through:

1. User runs `Layout Selected Horizontal` — sets mode='horizontal' on spine nodes (HORIZ-02)
2. User runs normal `Layout Upstream` on any node in or downstream of the chain — HORIZ-03 replay dispatches to the horizontal path automatically

The REQUIREMENTS.md text for HORIZ-01 ("User can run 'Layout Upstream Horizontal'") reflects the pre-redesign command name. The functional capability — "lay out the B spine right-to-left, root rightmost, each successive input(0) ancestor steps left, output pipe extends downward" — is fully delivered by the current architecture. No standalone `Layout Upstream Horizontal` command exists or is needed.

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_place_output_dot_for_horizontal_root` | existing Dot detection | `id(node.input(0)) == id(root)` | VERIFIED | Line 449; `is not None` guard present |
| `_place_output_dot_for_horizontal_root` | consumer detection | `id(node.input(slot)) == id(root)` | VERIFIED | Line 453; `is not None` guard present |
| `layout_upstream` horizontal branch | `place_subtree_horizontal` | BFS ancestor walk rebinds root; `if root_mode == "horizontal":` at line 1296 | VERIFIED | Lines 1272-1330 |
| `layout_upstream` horizontal anchor | right-of-consumer position | `spine_x = original_selected_root.xpos() + original_selected_root.screenWidth() + horizontal_gap` | VERIFIED | Lines 1314-1316 |
| `layout_selected` horizontal branch | `place_subtree_horizontal` | BFS ancestor walk at 1434-1452; `if root_mode == "horizontal":` at line 1459 | VERIFIED | Lines 1427-1480 |
| `layout_selected` horizontal anchor | right-of-consumer position | `original_selected_root = root` at line 1428; anchor block at lines 1474-1477 | VERIFIED | Lines 1474-1477 |
| `_layout_selected_horizontal_impl` | `_place_output_dot_for_horizontal_root` | direct call after `place_subtree_horizontal` inside for-root loop | VERIFIED | Line 1623 |
| `compute_dims` | memo dict | 5-tuple key with layout_mode | VERIFIED | Lines 833-834 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| HORIZ-01 | 11-01, 11-02, 11-04 | User can lay out B-spine right-to-left; root rightmost, each input(0) ancestor steps left; output pipe extends downward | SATISFIED | `place_subtree_horizontal()` at line 513; `layout_selected_horizontal()` at 1649 is the user-facing command; `_place_output_dot_for_horizontal_root()` at 413; TestHorizontalSpine, TestOutputDot, TestMaskKink, TestSideInputPlacement all pass; UAT test 2 passed |
| HORIZ-02 | 11-01, 11-03 | User can run "Layout Selected Horizontal" | SATISFIED | `layout_selected_horizontal()` at line 1649 and `layout_selected_horizontal_place_only()` at 1663; both registered in menu.py lines 29-30; TestHorizontalAST 3/3 pass |
| HORIZ-03 | 11-01, 11-03, 11-04, 11-05 | Horizontal mode stored in state; normal Layout Upstream/Selected replays horizontal automatically | SATISFIED | Mode dispatch in `layout_upstream()` at lines 1272-1330 and `layout_selected()` at lines 1427-1480; state write-back at lines 1352-1353 and 1635; TestModeReplay passes; TestDownstreamReplayAnchor 3/3 pass confirming right-of-consumer placement |

No orphaned requirements found. All three HORIZ IDs from REQUIREMENTS.md are claimed by plans and verified in the codebase.

---

### Anti-Patterns Found

None. No TODO, FIXME, placeholder, stub, or empty-implementation patterns detected in `node_layout.py` or `tests/test_horizontal_layout.py`.

---

### Plan-05 Must-Have Verification (Gap Closure)

The plan-05 frontmatter defined three specific must-haves for the UAT gap closure. All three are verified:

| Must-Have | Key Pattern | Status | Line(s) |
|-----------|------------|--------|---------|
| No duplicate Dot on replay — id() comparison in `_place_output_dot_for_horizontal_root` | `id(node.input(0)) == id(root)` | VERIFIED | 449 |
| Horizontal replay placed RIGHT of downstream node via layout_upstream | `screenWidth.*horizontal_gap` | VERIFIED | 1315 |
| Horizontal replay placed RIGHT of downstream node via layout_selected | `screenWidth.*horizontal_gap` | VERIFIED | 1476 |

---

### Test Suite Status

| Suite | Tests | Result | Notes |
|-------|-------|--------|-------|
| `tests/test_horizontal_layout.py` | 24 | PASS (0 failures, 0 errors) | Includes 5 new plan-05 tests: TestDownstreamReplayAnchor (3) and TestPlaceOutputDotForHorizontalRootReplay (2) |
| Full suite (`discover -s tests`) | 261 | 4 errors (pre-existing) | 4 errors in `test_scale_nodes_axis.TestExpandPushAway` and `TestRepeatLastScaleBehavior` are a cross-suite nuke stub contamination issue inherited from Phase 10 — `nuke.Undo` attribute missing when test_scale_nodes_axis runs after other test modules. Running `test_scale_nodes_axis` in isolation passes (15/15). Not caused by Phase 11. |

---

### Human Verification Required

#### 1. Right-of-consumer downstream replay — live Nuke

**Test:** Run "Layout Selected Horizontal" on a 4-node chain (A→B→C→D, select all). Scramble positions. Create a downstream node E with D as input. Select E. Run "Layout Upstream".
**Expected:** The horizontal chain (D leftmost, A rightmost) appears to the RIGHT of E at E's Y level — not above E.
**Why human:** Requires live Nuke session with real proxy wrapper objects and actual screen coordinates. AST tests confirm the formula, but real DAG rendering cannot be verified programmatically.

#### 2. No duplicate output Dot on re-run — live Nuke

**Test:** Run "Layout Selected Horizontal" on a chain twice in succession.
**Expected:** Only one output Dot below root after both runs. Second run repositions the existing Dot rather than creating a second one.
**Why human:** Requires real `nuke.nodes.Dot()` factory and `knob()` introspection. The id()-based detection is verified in stub tests but real Nuke proxy wrapper identity may behave differently in edge cases.

#### 3. Place Only mode replay — live Nuke

**Test:** Run "Layout Selected Horizontal (Place Only)" on a chain. Scramble. Select any spine node. Run "Layout Upstream".
**Expected:** Horizontal replay fires — layout is horizontal, chain placed right of any downstream consumer.
**Why human:** End-to-end round-trip through real Nuke state persistence layer (knob write then read). The unconditional mode write-back is verified in code, but the actual knob survival across operations requires live Nuke.

---

### Gaps Summary

No gaps. All 13 observable truths are verified. All 3 requirement IDs (HORIZ-01, HORIZ-02, HORIZ-03) are satisfied with direct implementation evidence. The 24-test suite passes GREEN. Plan-05 bug fixes are confirmed in the codebase at the exact lines specified in the plan frontmatter must_haves. No regressions were introduced.

The previous VERIFICATION.md was marked `status: post-uat-fixes-applied` as a manual progress note; this re-verification formally closes the loop after plan-05 execution.

---

_Verified: 2026-03-15_
_Verifier: Claude (gsd-verifier)_
